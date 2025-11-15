# Status do Projeto emu8051-tty

## Status Atual: Em Desenvolvimento Ativo - Progresso Significativo ✅

### O Que Funciona ✅

1. **Compilação**: Projeto compila sem erros com Clang/GCC
2. **Emulador 8052**: Core emu8051 com **suporte completo ao 8052** (Timer 2)
3. **PTY**: Pseudo-terminal criado com sucesso (`/dev/pts/X`)
4. **ROM Loading**: ROM Fiat Tipo 1.6 Alcohol (32KB) carregada em 0x0000-0x7FFF
5. **UART TX**: Polling-based transmit via SBUF → PTY funcionando
6. **UART RX**: Polling-based receive PTY → SBUF funcionando com **echo K-line**
7. **BREAK Detection**: Detecção de BREAK conditions via PARMRK (5-baud init)
8. **K-line Echo**: Half-duplex echo protocol implementado
9. **P4.5 Callback**: ROM pode amostrar linha RX para 5-baud init
10. **Execução**: Firmware executa e habilita interrupções (Timer 0, Timer 2)
11. **Timer 2**: Implementado e corrigido (não dispara mais infinitamente!)

### Descobertas Principais 🔍

#### 1. Firmware Requer Modo 8052
**Confirmado**: A ROM Bosch MA1.7 usa **Timer 2** (feature exclusiva do 8052), não do 8051 padrão.

Evidência:
- Firmware habilita ET2 (Timer 2 interrupt) em PC=0x0B09: `IE=0xA2` (EA=1, ET2=1, ET0=1)
- ISR do Timer 2 em 0x002B (`TF2_EXF2`)
- Requer 256 bytes IRAM (mUpperData)

**Solução aplicada**:
```cmake
# CMakeLists.txt
add_compile_definitions(__8052__)  # Habilita Timer 2, 6 ISRs, 256B IRAM
```

#### 2. Bug Crítico #1 no emu8051: Timer 2 ISR Vector Errado

**Descoberta**: O código original do emu8051 tinha Timer 2 apontando para o vetor **errado**!

```c
// emu8051/core.c (ANTES - BUGADO)
if (aCPU->mSFR[REG_IE] & IEMASK_ET2 && ...) {
    dest_ip = ISR_SR;  // ❌ ERRADO! Aponta para Serial (0x23)
}
```

**Problema**: Timer 2 deveria usar `ISR_TF2` (0x2B) mas estava usando `ISR_SR` (0x23), causando:
- Salto para ISR errada (Serial ao invés de Timer 2)
- Flag TF2 nunca era limpa
- Stack overflow infinito

**Solução**: Integrado **PR #40** do repositório nickburgin/emu8051 que corrige o vetor:
```c
// emu8051/core.c (DEPOIS - CORRIGIDO)
dest_ip = ISR_TF2;  // ✅ CORRETO! (0x2B)
```

#### 3. Bug Crítico #2 no emu8051: Flag TF2 Não Era Limpa

**Descoberta**: Mesmo após corrigir o vetor, Timer 2 continuava disparando infinitamente porque a **flag TF2 não era limpa** quando a ISR era invocada.

```c
// emu8051/core.c - switch (dest_ip)
case ISR_TF0:
    aCPU->mSFR[REG_TCON] &= ~TCONMASK_TF0; // Timer 0: flag limpa ✅
    break;
case ISR_TF1:
    aCPU->mSFR[REG_TCON] &= ~TCONMASK_TF1; // Timer 1: flag limpa ✅
    break;
case ISR_SR:
    aCPU->serial_interrupt_trigger = 0;     // Serial: flag limpa ✅
    break;
// ❌ FALTAVA: case ISR_TF2 para limpar TF2!
```

**Solução aplicada**:
```c
#ifdef __8052__
case ISR_TF2:
    // Clear Timer 2 overflow flag (TF2) - bit 7 of T2CON
    aCPU->mSFR[REG_T2CON] &= ~T2CONMASK_TF2;  // ✅ ADICIONADO
    break;
#endif
```

**Resultado**: Timer 2 agora dispara **apenas uma vez**, não mais em loop infinito! 🎉

#### 4. K-line Protocol Implementation

**Implementado**:
- **BREAK detection**: Via Linux termios PARMRK mode (pattern `0xFF 0x00 0x00`)
- **Half-duplex echo**: Todo byte transmitido é ecoado imediatamente (`write(mfd, &b, 1)`)
- **RX queue**: Bytes normais são enfileirados após filtrar BREAK patterns
- **P4.5 sampling**: ROM pode ler estado da linha RX via callback `cb_sfr_read()`

```cpp
// K-line echo (half-duplex)
ssize_t n = read(mfd, &b, 1);
if (n == 1) {
    write(mfd, &b, 1);  // Echo imediato
    rx_queue.push(b);    // Enfileira para UART
}
```

#### 5. Callbacks Implementados

1. **`cb_sfr_read()`**: Permite ROM amostrar P4.5 (RX line state) para 5-baud init
2. **`cb_sfr_write_ie()`**: Monitora mudanças no registro IE (interrupt enable)
3. **`cb_exception()`**: Captura exceções IRET_SP_MISMATCH/ACC_MISMATCH
4. **`detect_isr_call()`**: Loga quando ISRs são invocadas

### Bug Crítico #3 RESOLVIDO: ROM/RAM Aliasing ✅

**Sintoma**: Timer 2 executava opcodes 0x00 (NOP) ao invés do código real da ROM

**Investigação**:
```
[DEBUG] ROM[0x002B]=0xC2 (Timer 2 ISR)  ← Após carregar ROM
[T2-TRACE] opcode=0x00                  ← Durante execução!
[T2-TRACE] Dump [0x0027-0x002F]: 00 00 00 00 00 00 00 00 00
```

**Causa raiz identificada**:
O firmware Bosch MA1.7 faz escritas via `MOVX` (External Data), e no código original:
```cpp
// BUG: ROM e RAM apontavam para MESMO buffer!
cpu.mCodeMem = code_memory;
cpu.mExtData = code_memory;  // ← Aliasing fatal!
```

Quando o firmware executava `MOVX @DPTR, A` (write para External RAM), **sobrescrevia a ROM**!

**Solução aplicada**:
```cpp
// Buffers SEPARADOS para ROM (read-only) e RAM (read-write)
static unsigned char code_memory[0x10000];   // ROM
static unsigned char ext_data_memory[0x10000]; // RAM separada
cpu.mCodeMem = code_memory;
cpu.mExtData = ext_data_memory;  // ✅ FIX!
```

**Resultado**: Firmware agora executa corretamente! ✅
```
[T2-TRACE] PC=0x002B opcode=0xC2  ← CLR (correto!)
[T2-TRACE] PC=0x002D opcode=0x05  ← INC (correto!)
[T2-TRACE] PC=0x0047 opcode=0x32  ← RETI (correto!)
[T2-TRACE] RETI executed at PC=0x0047
```

### Arquitetura Implementada 🏗️

```
┌─────────────────────────────────────────────────────────────┐
│                      emu8051-tty                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌─────────────────────────────┐      │
│  │ PTY Master   │◄────►│  K-line Protocol Handler    │      │
│  │ /dev/pts/X   │      │  - BREAK detection (PARMRK) │      │
│  │ 4800 8N1     │      │  - Half-duplex echo         │      │
│  └──────────────┘      │  - RX queue                 │      │
│         │              └─────────────────────────────┘      │
│         │                           │                        │
│         ▼                           ▼                        │
│  ┌─────────────────────────────────────────────────┐        │
│  │            UART Bridge (SFR polling)            │        │
│  │  - TX: SBUF write → TI flag → PTY               │        │
│  │  - RX: PTY → RI flag → SBUF read                │        │
│  └─────────────────────────────────────────────────┘        │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────┐        │
│  │          emu8051 Core (8052 mode)               │        │
│  │  - Timer 0, Timer 1, Timer 2 (8052!)            │        │
│  │  - 256 bytes IRAM (mUpperData)                  │        │
│  │  - 6 interrupt sources                          │        │
│  │  - Callbacks: P4 read, IE write, exceptions     │        │
│  └─────────────────────────────────────────────────┘        │
│                          │                                   │
│                          ▼                                   │
│             ┌────────────────────────┐                       │
│             │  ROM: 32KB (27C256)    │                       │
│             │  Bosch MA1.7 Firmware  │                       │
│             │  0x0000 - 0x7FFF       │                       │
│             └────────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Próximos Passos 🎯

1. **Teste com scanner real K-line** 📡
   - Emulador agora executa firmwareBosch MA1.7 corretamente
   - Testar comunicação K-line com scanner OBD-II
   - Enviar 5-baud init sequence (0x33 @ 5 baud)
   - Verificar se firmware responde com 0x55 (sync byte)
   - Validar protocolo ISO 9141-2 completo

2. **Remover debug logging** 🧹
   - Remover ou condicionalizar logs de desenvolvimento (T2-TRACE, DEBUG PC)
   - Manter apenas logs essenciais de K-line e comunicação

3. **Otimização de performance** ⚡
   - Avaliar se 2-4 MIPS lógicos está adequado
   - Ajustar timing de sleep para melhor responsividade
   - Considerar cycle-accurate timing se necessário

### Logs de Debug 📋

Arquivos atualizados:
- `emu_log.txt` - Log completo (último teste)
- `emu_output.log` - Log sem sanitizers
- `emu_test.log` - Teste atual

### Build System

```bash
# Build padrão (com sanitizers e 8052 mode)
mkdir -p build && cd build
cmake ..
cmake --build . --parallel

# Build sem sanitizers (mais rápido)
cmake -DENABLE_SANITIZERS=OFF ..
cmake --build . --parallel

# Run
./build/emu8051-tty "tipo 1.6 alcool27c256.bin"
```

### Mudanças no Código ✏️

#### CMakeLists.txt
```cmake
# Modo 8052 habilitado por padrão
add_compile_definitions(__8052__)

# Clang: permite designated initializers
add_compile_options(-Wno-c99-designator)
```

#### src/main.cpp
- ✅ **ROM/RAM aliasing fix**: Buffers separados para code_memory (ROM) e ext_data_memory (RAM)
- ✅ K-line echo implementado
- ✅ BREAK detection via PARMRK
- ✅ RX queue para bytes normais
- ✅ P4.5 callback para ROM amostrar RX line
- ✅ IE write monitor
- ✅ Exception handler
- ✅ ISR detection logging
- ✅ mUpperData sempre alocado (256B)
- ✅ Timer 2 trace logging para debug

#### emu8051/core.c (submodule modificado)
- ✅ PR #40 integrado (Timer 2 completo)
- ✅ Bug fix: ISR_TF2 vector correto (0x2B ao invés de 0x23)
- ✅ Bug fix: case ISR_TF2 adicionado para limpar flag TF2

### Referências 📚

- **emu8051**: https://github.com/jarikomppa/emu8051
- **PR #40 (8052 support)**: https://github.com/jarikomppa/emu8051/pull/40
- **ISO 9141-2**: Automotive K-line diagnostic protocol
- **8052 Datasheet**: Timer 2, 256B IRAM, 6 interrupt sources
- **Bosch Monomotronic MA1.7**: ECU firmware analisado
- **ROM**: `tipo 1.6 alcool27c256.bin` (32768 bytes)
- **IDA Dump**: `IDADUMPBINFIATTIPOIEALCOOL.txt`

### Commits Pendentes 💾

Mudanças prontas para commit:
1. ✅ Modo 8052 habilitado (CMakeLists.txt)
2. ✅ K-line echo + BREAK detection (main.cpp)
3. ✅ Callbacks P4/IE/exceptions (main.cpp)
4. ✅ Bug fixes Timer 2 (emu8051 submodule)
5. ✅ ISR detection logging (main.cpp)
6. ⏳ Investigação ISRs múltiplas (em andamento)
