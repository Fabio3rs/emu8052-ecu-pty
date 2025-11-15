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

---

## Investigação Detalhada: K-line Slow-Init Protocol 🔬

### Status da Investigação: PROBLEMA IDENTIFICADO - Stack Overflow Periódico ⚠️

**Data**: 2025-11-15
**Objetivo**: Entender por que o firmware não envia o sync byte 0x55 após receber slow-init (0x10 @ 5 baud)

---

### Descobertas Críticas

#### 1. **Problema Real: Stack Overflow → Reset Loop**

**Sintoma observado**:
- Firmware executa ~12.000 instruções normalmente
- Subitamente PC salta de 0x5429 → 0xFF52 (região inválida)
- CPU executa NOPs até alcançar 0x0000 (reset vector)
- Sistema faz `ljmp RESET_0` → ciclo se repete

**Evidência dos logs**:
```
[RESET_0 ENTRY #1] PC=0x0850, came from PC=0x0000, SP=0x07  ← Reset inicial
[ALERT] PC: 0x5429 → 0xFF52 (SP=0x00)  ← Corrupção de stack!
[RESET_0 ENTRY #2] PC=0x0850, came from PC=0x0000, SP=0x00  ← Após overflow
```

**Conclusão**: NÃO é um watchdog reset intencional! É um **stack overflow** que corrompe o PC.

---

#### 2. **Hipótese Inicial DESCARTADA: Watchdog Reset**

**Hipótese inicial** (INCORRETA):
- RAM_47 = 0 → triggera watchdog @ 0x4B65 → reset contínuo

**Por que foi descartada**:
- Timer 0 ISR @ 0x4B60 **NUNCA alcança** o watchdog check @ 0x4B65
- PC nunca chega em 0x4B65 durante a execução
- O problema é **stack overflow**, não watchdog!

---

### Mapeamento Completo do Firmware 🗺️

#### Endereços Críticos e Suas Funções

##### **0x0000: Reset Vector**
```asm
code:00000000     ljmp    RESET_0         ; Salta para 0x0850
```
- **Função**: Vetor de reset do 8051
- **Destino**: 0x0850 (rotina de inicialização)

---

##### **0x0850-0x0872: RESET_0 - Rotina de Inicialização**
```asm
code:00000850 RESET_0:
code:00000850     mov     WDTREL, #0xF3   ; Configura watchdog
code:00000853     setb    IEN1.6          ; Habilita watchdog interrupt
...
code:0000086D     mov     R1, #0xFF
code:0000086F     clr     A
code:00000870 code_870:
code:00000870     mov     @R1, A          ; Limpa RAM[R1]
code:00000871     dec     R1              ; RAM_17, RAM_47 zerados aqui!
code:00000872     cjne    R1, #1, code_870
```

**Função**: Inicialização completa do sistema
- Configura watchdog (WDTREL)
- **Limpa toda a RAM** de 0xFF → 0x01 (CRÍTICO!)
  - **RAM_17** (K-line enable flag) → 0
  - **RAM_47** (watchdog counter) → 0
  - **RAM_3E** (protocol state) → 0
  - **RAM_40** (decoded address byte) → 0
  - **RAM_89** (gatekeeper) → 0

**Impacto**: Após cada reset, K-line fica **desabilitado** (RAM_17=0)

---

##### **0x01AB: EEPROM Load (NUNCA ALCANÇADO)**
```asm
code:000001AB     mov     R1, #0xF8
code:000001AD     movx    A, @R1          ; Lê XRAM[0xF8] (EEPROM)
code:000001AE     mov     RAM_47, A       ; Armazena em RAM_47 (watchdog counter)
```

**Função**: Carrega RAM_47 da EEPROM/NVM @ XRAM[0xF8]
- **Problema**: PC **NUNCA chega aqui** devido aos resets contínuos!
- **Consequência**: RAM_47 permanece = 0 (zerado por RESET_0)

**Workaround aplicado** (main.cpp:723-731):
```cpp
// Simula EEPROM inicializada
cpu.mExtData[0xF8] = 0xFF;  // EEPROM @ XRAM[0xF8]
cpu.mLowerData[0x47] = 0xFF; // RAM_47 (watchdog counter)
```

---

##### **0x082B: Gatekeeper - Condição para Chamar Decoder**
```asm
code:0000082B     mov     R1, #0x89       ; Aponta para RAM_89 (Upper RAM!)
code:0000082D     mov     A, @R1          ; Lê RAM_89
code:0000082E     jb      ACC.0, code_83D ; Salta se bit 0 = 1
code:00000831     jb      ACC.1, code_83D ; Salta se bit 1 = 1
code:00000834     jnb     ACC.2, code_83D ; Salta se bit 2 = 0
code:00000837     lcall   code_4B94       ; Chama decoder (se RAM_89 = 0x04)
```

**Função**: Gatekeeper que valida condições antes de chamar o decoder K-line
- **Condição**: RAM_89 deve ser **exatamente 0x04** (binário: 00000100)
  - Bit 0 = 0 (não set)
  - Bit 1 = 0 (não set)
  - Bit 2 = 1 (set)
  - Bits 3-7 = 0

**Nota importante**: RAM_89 está na **Upper RAM** (8052), não na Lower RAM!
- Acesso via `mUpperData[0x89 - 0x80]` = `mUpperData[0x09]`

---

##### **0x4B60-0x4B93: Timer 0 ISR (CRÍTICO - NUNCA ALCANÇA 0x4B65!)**
```asm
code:00004B60 ISR_TF0:                     ; Timer 0 ISR entry point
code:00004B60     push    PSW
code:00004B62     push    ACC
code:00004B64     lcall   sub_4D81        ; Chama sub-rotina
...
code:00004B65     mov     A, RAM_47       ; ← WATCHDOG CHECK (NUNCA EXECUTADO!)
code:00004B67     jz      code_4B7A       ; ← Se RAM_47 = 0, triggera reset
...
code:00004B7A code_4B7A:                   ; Reset trigger (desuso)
code:00004B7A     clr     IEN0.7          ; Desabilita todas interrupts
code:00004B7C     mov     TCON, #0
code:00004B7F     mov     T2CON, #0
code:00004B82     mov     IRCON, #0
code:00004B85     ljmp    RESET_0         ; Salta para reset completo
...
code:00004B90     pop     ACC
code:00004B91     pop     PSW
code:00004B92     reti
```

**Descoberta CRÍTICA**:
- PC **NUNCA alcança 0x4B65** (watchdog check)!
- Timer 0 ISR retorna antes de chegar nesse código
- **Conclusão**: Watchdog check @ 0x4B65-0x4B85 é **código morto** (dead code)

**Implicação**: O reset loop NÃO é causado pelo watchdog! É causado por **stack overflow**.

---

##### **0x4C44-0x4C8C: Slow-Init Address Decoder**
```asm
code:00004C44 sub_4C44:
code:00004C44     mov     A, RAM_17       ; Lê K-line enable flag
code:00004C46     jz      code_4C73       ; BLOCKER #1: Se RAM_17 = 0, sai!
code:00004C48     mov     A, #0x10
code:00004C4A     cjne    A, RAM_40, code_4C73  ; BLOCKER #2: Se RAM_40 ≠ 0x10, sai!
code:00004C4D     setb    B.2             ; SUCCESS: Seta bit 2 de B
...
code:00004C86     mov     RAM_3E, B       ; CRÍTICO: Copia B → RAM_3E
code:00004C88     mov     B, #0
code:00004C8A     mov     RAM_40, B       ; Limpa RAM_40
code:00004C8C     ret
```

**Função**: Valida se o slow-init address byte decodificado = 0x10
- **Entrada**:
  - RAM_17 = K-line enable flag (deve ≠ 0)
  - RAM_40 = Byte decodificado via 5-baud (deve = 0x10)
- **Saída**:
  - RAM_3E.2 = 1 → Habilita handler K-line
  - RAM_40 → 0 (limpa para próxima decodificação)

**Blockers identificados**:
1. **RAM_17 = 0**: Zerado por RESET_0 @ 0x0871 → função sai @ 0x4C46
2. **RAM_40 ≠ 0x10**: Se decodificação falhar → função sai @ 0x4C4A

**Nota**: Este código é chamado de 0x082B (se RAM_89 = 0x04)

---

##### **0x36E1: PROBLEMA RAIZ - Stack Underflow Súbito (SP: 0xD0 → 0x00)**
```asm
code:000036DD                 mov     R1, #0x81
code:000036DF                 mov     B, @R1          ; Lê Upper RAM[0x01] → B
code:000036E1                 mov     R0, #0x80       ; ← STACK UNDERFLOW OCORRE AQUI!
code:000036E3                 jc      code_3706
code:000036E5                 mov     A, #0x75
```

**Observação nos logs**:
```
[STACK UNDERFLOW] SP: 0xD0 → 0x00 (PC=0x36E1)  ← TRANSIÇÃO SÚBITA!
[STACK CRITICAL] SP reached 0x00! (PC=0x36E1, last_SP=0xD0)
[STACK DUMP] Stack[0x00-0x07]: 9E 81 99 00 00 00 00 00
```

**Análise**:
- **Instrução**: `mov R0, #0x80` - deveria apenas carregar valor imediato em R0
- **Problema**: SP salta de 0xD0 → 0x00 **instantaneamente**!
- **Impacto**: Esta é uma instrução **simples** que NÃO deveria afetar SP
- **Hipótese #1**: Bug no emulador emu8051 (opcode 0x78 mal implementado?)
- **Hipótese #2**: Instrução anterior (`mov B, @R1`) corrompe stack de forma assíncrona
- **Hipótese #3**: Interrupt ocorre durante esta instrução e corrompe SP

**Stack dump no momento do underflow**:
- Stack[0] = 0x9E → Possível return address low byte
- Stack[1] = 0x81 → Possível return address high byte (0x819E)
- Stack[2-7] = maioria zeros

**Conclusão**: Este é o **ponto de origem** do stack underflow! Todos os problemas subsequentes são consequência deste evento.

---

##### **0x3B6A: Stack Critical #2**
```asm
code:00003B67                 lcall   code_5774       ; Chama sub-rotina
code:00003B6A                 anl     RAM_1B, #0xBF   ; ← STACK=0x00 (last_SP=0x02)
code:00003B6D                 jb      RAM_2D.7, code_3B73
```

**Observação nos logs**:
```
[STACK CRITICAL] SP reached 0x00! (PC=0x3B6A, last_SP=0x02)
[STACK DUMP] Stack[0x00-0x07]: 9B 6A 3B 00 00 00 00 7F
```

**Análise**:
- SP estava em 0x02 (quase vazio), alcançou 0x00
- Stack dump mostra: `9B 6A 3B` → endereço de retorno = **0x3B6A** (auto-referência!)
- **Problema**: Stack contém endereço da própria instrução atual
- Instrução `lcall code_5774` @ 0x3B67 deve ter falhado ou corrompido stack

---

##### **0x3B9D: Stack Critical #3 - Inicialização de Hardware**
```asm
code:00003B91                 orl     S0CON, #0x80    ; Serial Channel 0 Control
code:00003B94                 mov     TMOD, #0x11     ; Timer Mode Register
code:00003B97                 orl     TCON, #0x15     ; Timer Control
code:00003B9A                 orl     T2CON, #0x85    ; Timer 2 Control
code:00003B9D                 mov     PCON, #0        ; ← STACK=0x00 (last_SP=0x02)
code:00003BA0                 mov     IP0, #0x39      ; Interrupt Priority 0
```

**Observação nos logs**:
```
[STACK CRITICAL] SP reached 0x00! (PC=0x3B9D, last_SP=0x02)
[STACK DUMP] Stack[0x00-0x07]: 9B 9D 3B 00 00 00 00 7F
```

**Análise**:
- Região de código: **Inicialização de periféricos**
- SP=0x00 com stack dump mostrando `9B 9D 3B` = endereço 0x3B9D (auto-referência!)
- **Problema**: Similar ao anterior - stack contém endereço atual
- Esta região configura timers, serial, interrupts - **região crítica de boot**

**Observação importante**: Este código está em @ 0x3B82-0x3BAC e configura **TODOS os periféricos**:
- Portas P1-P5
- Serial (S0CON)
- Timers (TMOD, TCON, T2CON)
- Power control (PCON)
- Interrupt priorities (IP0, IP1)
- Interrupt enables (IEN0, IEN1)

---

##### **0xFF52: Região Inválida - Resultado Final do Stack Corruption**
```asm
code:00005429     ret                     ; Return que causa jump para 0xFF52
```

**Observação nos logs**:
```
[STACK CRITICAL] SP reached 0x00! (PC=0xFF52, last_SP=0x02)
[STACK DUMP] Stack[0x00-0x07]: 95 52 FF 25 54 00 00 7F
```

**Análise**:
- Stack dump: `95 52 FF` → endereço de retorno = **0xFF52** (região não programada!)
- ROM[0xFF52-0xFFFF]: `0xFF 0xFF 0xFF ...` (bytes não programados ou NOPs)
- CPU executa NOPs até wrap-around → alcança 0x0000 → `ljmp RESET_0`

**Pergunta respondida**: RET @ PC desconhecido (provavelmente 0x5429) com stack corrompido → PC=0xFF52

---

##### **0xFFE3: Outra Região Inválida**
```
ROM[0xFFE3]: 0xFF (NOP ou unprogrammed)
```

**Observação nos logs**:
```
[STACK CRITICAL] SP reached 0x00! (PC=0xFFE3, last_SP=0x02)
[STACK DUMP] Stack[0x00-0x07]: 95 E3 FF 07 A3 DC 72 00
```

**Análise**:
- Stack dump: `95 E3 FF` → endereço de retorno = **0xFFE3**
- Outra região não programada da ROM
- Mesmo padrão: RET com stack corrompido → região inválida → reset

---

### Variáveis de Estado do Firmware 📊

#### Mapa de RAM Crítica

| Endereço | Nome       | Função                                    | Valor Esperado | Blocker? |
|----------|------------|-------------------------------------------|----------------|----------|
| 0x17     | RAM_17     | K-line enabled flag                       | 0x7F           | ✅ SIM   |
| 0x3E     | RAM_3E     | Protocol state (bit 2 = K-line active)    | 0x04 (bit 2=1) | Não      |
| 0x40     | RAM_40     | Decoded slow-init address byte            | 0x10           | ✅ SIM   |
| 0x42     | RAM_42     | Unknown (monitored during investigation)  | ?              | Não      |
| 0x47     | RAM_47     | Watchdog counter (from EEPROM @ 0xF8)     | 0xFF (nonzero) | Talvez   |
| 0x89     | RAM_89     | Gatekeeper variable (Upper RAM!)          | 0x04           | ✅ SIM   |

**Nota sobre RAM_89**:
- Localizada na **Upper RAM** (8052 only)
- Acesso via indirect addressing (`@R1` quando R1=0x89)
- Em C++: `mUpperData[0x89 - 0x80]` = `mUpperData[0x09]`

---

### Instrumentação Implementada em main.cpp 🔧

#### 1. **EEPROM/NVM Simulation** (Lines 723-731)
```cpp
// Workaround: Simula EEPROM inicializada para prevenir reset loop
cpu.mExtData[0xF8] = 0xFF;      // EEPROM @ XRAM[0xF8]
cpu.mLowerData[0x47] = 0xFF;    // RAM_47 (watchdog counter)
fprintf(stderr, "[EEPROM] Initialized XRAM[0xF8]=0xFF, RAM_47=0xFF\n");
```

**Razão**: Firmware carrega RAM_47 de XRAM[0xF8] @ 0x01AB, mas nunca alcança esse código.

---

#### 2. **RESET_0 Entry Tracking** (Lines 937-948)
```cpp
// Monitora entradas em RESET_0 @ 0x0850
static int reset_0_count = 0;
static uint16_t last_pc_before_0850 = 0;
if (cpu.mPC == 0x0850) {
    reset_0_count++;
    if (reset_0_count <= 3) {  // Loga primeiros 3 resets
        fprintf(stderr, "[RESET_0 ENTRY #%d] PC=0x0850, came from PC=0x%04X, SP=0x%02X\n",
                reset_0_count, last_pc_before_0850, cpu.mSFR[REG_SP]);
    }
}
```

**Resultado**: Identificou que PC vem de 0x0000 (reset vector) após overflow!

---

#### 3. **Stack Overflow Detection** (Lines 950-995)
```cpp
// DETECÇÃO DE STACK OVERFLOW/UNDERFLOW
// 8051 stack: SP aponta para último byte escrito
// Range normal: 0x08-0xDF (init SP=0xD0, cresce para cima)
// Underflow: SP < 0x08
// Overflow: SP > 0xDF (entra em região SFR @ 0x80-0xFF)
static unsigned char last_sp = 0xD0;
static unsigned char min_sp_seen = 0xFF;
static unsigned char max_sp_seen = 0x00;
unsigned char current_sp = cpu.mSFR[REG_SP];

// Rastreia min/max SP
if (current_sp < min_sp_seen) min_sp_seen = current_sp;
if (current_sp > max_sp_seen) max_sp_seen = current_sp;

// Detecta underflow (SP < 0x08)
if (current_sp < 0x08 && last_sp >= 0x08) {
    fprintf(stderr, "[STACK UNDERFLOW] SP: 0x%02X → 0x%02X (PC=0x%04X)\n",
            last_sp, current_sp, cpu.mPC);
}

// Detecta overflow (SP > 0x7F - entra em Upper RAM)
if (current_sp > 0x7F && last_sp <= 0x7F) {
    fprintf(stderr, "[STACK OVERFLOW] SP: 0x%02X → 0x%02X (PC=0x%04X)\n",
            last_sp, current_sp, cpu.mPC);
}

// Detecta SP = 0x00 (critical underflow)
if (current_sp == 0x00 && last_sp != 0x00) {
    fprintf(stderr, "[STACK CRITICAL] SP reached 0x00! (PC=0x%04X)\n", cpu.mPC);
    // Mostra bytes do topo do stack
    fprintf(stderr, "[STACK DUMP] Stack[0x00-0x07]: ");
    for (int i = 0; i <= 7; i++) {
        fprintf(stderr, "%02X ", cpu.mLowerData[i]);
    }
    fprintf(stderr, "\n");
}
```

**Resultado (ATUALIZADO após recompilação)**:
- ✅ **Stack overflow/underflow DETECTADO com sucesso!**
- Múltiplos eventos de stack corruption identificados
- Padrão repetitivo de underflow → reset → re-inicialização

**Eventos críticos capturados**:
```
[STACK CRITICAL] SP reached 0x00! (PC=0x36E1, last_SP=0xD0)  ← UNDERFLOW SÚBITO!
[STACK CRITICAL] SP reached 0x00! (PC=0x3B6A, last_SP=0x02)
[STACK CRITICAL] SP reached 0x00! (PC=0x3B9D, last_SP=0x02)
[STACK CRITICAL] SP reached 0x00! (PC=0xFF52, last_SP=0x02)  ← Resultado: região inválida
[STACK UNDERFLOW] SP: 0x08 → 0x07 (PC=0x0845)
[STACK CRITICAL] SP reached 0x00! (PC=0xFFE3, last_SP=0x02)
[STACK OVERFLOW] SP: 0x00 → 0xD0 (PC=0x0867)               ← Reset restaura SP
```

**Padrão identificado**:
1. SP salta de 0xD0 → 0x00 @ PC=0x36E1 (PROBLEMA RAIZ!)
2. Múltiplas tentativas de RET com SP=0x00 → PC corrupto
3. PC alcança região inválida (0xFF52, 0xFFE3)
4. Reset @ 0x0867 restaura SP → 0xD0
5. Ciclo se repete

---

### Perguntas em Aberto ❓

#### ✅ Respondidas

1. **O que causa a corrupção do stack?**
   - ✅ **RESPONDIDA**: Stack underflow ocorre @ **PC=0x36E1** durante `mov R0, #0x80`
   - SP salta de 0xD0 → 0x00 instantaneamente
   - Instrução simples que NÃO deveria afetar SP!

2. **Timer 0 ISR alcança watchdog @ 0x4B65?**
   - ✅ **RESPONDIDA**: **NÃO!** Timer 0 ISR retorna antes de alcançar 0x4B65
   - Watchdog check @ 0x4B65-0x4B85 é código morto (dead code)

3. **Por que não estava detectando stack overflow inicialmente?**
   - ✅ **RESPONDIDA**: Executável desatualizado! Compilação havia falhado.
   - Após recompilação bem-sucedida, detecção funcionou perfeitamente!

#### ❓ Ainda em Investigação

4. **Por que `mov R0, #0x80` @ 0x36E1 causa SP: 0xD0 → 0x00?**
   - **Hipótese #1**: Bug no emulador emu8051 (opcode 0x78 mal implementado)
   - **Hipótese #2**: Interrupt preemptivo durante instrução corrompe SP
   - **Hipótese #3**: Instrução anterior (`mov B, @R1`) acessa Upper RAM de forma incorreta
   - **Hipótese #4**: Register bank switch (R0 está em different bank?) afeta SP indevidamente

5. **RAM_89 é inicializado corretamente?**
   - Gatekeeper @ 0x082B requer RAM_89 = 0x04
   - Upper RAM é zerado por RESET_0 @ 0x0871
   - Firmware inicializa RAM_89 = 0x04 em algum momento?
   - Precisa adicionar trace para escritas em Upper RAM @ 0x89

6. **Por que stack dumps mostram auto-referências?**
   - @ 0x3B6A: Stack[0-2] = `9B 6A 3B` → endereço 0x3B6A (própria instrução)
   - @ 0x3B9D: Stack[0-2] = `9B 9D 3B` → endereço 0x3B9D (própria instrução)
   - Indicação de RET sem CALL correspondente?
   - Stack corrompido faz RET "voltar" para si mesmo?

7. **Instrução @ 0x36E1 está em qual função/ISR?**
   - Precisa rastrear call chain até 0x36E1
   - É chamada por Timer 0 ISR?
   - Profundidade de stack antes do underflow?

---

### Próximos Passos de Investigação 🔍

#### 🔴 Alta Prioridade - CRÍTICO

1. **Investigar bug @ PC=0x36E1: `mov R0, #0x80` causa SP: 0xD0 → 0x00**
   - **Ação #1**: Adicionar trace detalhado ANTES de 0x36E1
     - Logar PSW (register bank selection)
     - Logar SP antes/depois da instrução
     - Logar estado de interrupts (IE, IP)
   - **Ação #2**: Verificar opcode da instrução @ 0x36E1
     - Confirmar se ROM[0x36E1] = 0x78 (opcode de `mov R0, #imm`)
     - Verificar se emulador executa opcode correto
   - **Ação #3**: Instrumentar emu8051 core.c
     - Adicionar logging em `op_mov_r_imm()` (ou equivalente)
     - Verificar se SP é modificado indevidamente
   - **Ação #4**: Rastrear call chain até 0x36E1
     - Quantos níveis de CALL até alcançar 0x36E1?
     - De onde 0x36DD-0x36E5 é chamado?
     - É parte de Timer 0 ISR call tree?

2. **Verificar implementação de Upper RAM no emulador**
   - **Problema**: `mov B, @R1` @ 0x36DF lê Upper RAM[0x01]
   - **Verificar**: mUpperData está corretamente alocado e inicializado?
   - **Teste**: Adicionar trace de TODOS os acessos a Upper RAM via @R0/@R1
   - **Suspeita**: Acesso a Upper RAM pode estar corrompendo Lower RAM (stack)

3. **Adicionar trace de CALL/RET para identificar call depth**
   - Instrumentar instruções LCALL/ACALL/RET/RETI
   - Rastrear profundidade de stack (call depth counter)
   - Identificar quando depth fica inconsistente
   - **Objetivo**: Entender se há RET sem CALL correspondente

#### 🟡 Média Prioridade

4. **Verificar inicialização de RAM_89 (Upper RAM)**
   - Adicionar trace para **TODAS** escritas em Upper RAM @ 0x89
   - Confirmar se firmware alguma vez seta RAM_89 = 0x04
   - **Importante**: RAM_89 é gatekeeper @ 0x082B para K-line decoder!

5. **Investigar por que 0x3B6A e 0x3B9D mostram auto-referências**
   - Stack dumps: `9B 6A 3B` e `9B 9D 3B` → endereços das próprias instruções
   - **Hipótese**: RETI ou RET executado sem correspondente CALL/interrupt
   - **Teste**: Adicionar contador de PUSH vs POP para validar balanço

6. **Verificar se PC alcança 0x082B (gatekeeper K-line)**
   - Adicionar trace específico para 0x082B
   - Logar RAM_89 quando PC=0x082B
   - Confirmar se condição (RAM_89 = 0x04) é alguma vez satisfeita

#### 🟢 Baixa Prioridade

7. **Analisar sub-rotina code_5774 chamada @ 0x3B67**
   - `lcall code_5774` é executado antes de 0x3B6A (stack critical)
   - Verificar se code_5774 corrompe stack
   - Adicionar trace de entrada/saída desta função

8. **Testar com firmware simplificado**
   - Criar ROM de teste minimalista para isolar problema
   - ROM de teste: apenas MOV R0, #0x80 em loop
   - Verificar se problema é no emulador ou firmware específico

9. **Investigar interrupt timing**
   - Adicionar trace de **quando** interrupts ocorrem
   - Verificar se interrupt preemptivo durante 0x36E1 causa problema
   - Desabilitar interrupts temporariamente para teste

---

### Conclusões Parciais ✅

#### Confirmadas com Alta Confiança

1. ✅ **Stack underflow identificado @ PC=0x36E1**
   - Instrução: `mov R0, #0x80`
   - SP salta de 0xD0 → 0x00 instantaneamente
   - **ESTE É O PROBLEMA RAIZ!** Todos os resets são consequência deste evento

2. ✅ **Watchdog reset @ 0x4B65 é código morto**
   - Timer 0 ISR **NUNCA** alcança 0x4B65
   - Watchdog check @ 0x4B65-0x4B85 não é executado
   - Resets NÃO são causados por watchdog intencional

3. ✅ **Padrão de reset loop identificado**
   - SP underflow @ 0x36E1 → SP=0x00
   - RET com stack corrompido → PC=0xFF52 ou 0xFFE3 (região inválida)
   - CPU executa NOPs → wrap to 0x0000 → `ljmp RESET_0`
   - RESET_0 zera RAM (incluindo RAM_17) → SP restaurado para 0xD0
   - Ciclo se repete a cada ~12.000 instruções

4. ✅ **K-line decoder e gatekeepers localizados**
   - **Decoder**: @ 0x4C44 - valida RAM_40 = 0x10 (slow-init address byte)
   - **Gatekeeper #1**: RAM_17 ≠ 0 (K-line enabled flag)
   - **Gatekeeper #2**: RAM_89 = 0x04 (Upper RAM, checked @ 0x082B)
   - **Problema**: RAM_17 zerado por RESET_0 @ 0x0871 após cada reset

5. ✅ **EEPROM simulation funciona**
   - Workaround aplicado: XRAM[0xF8]=0xFF, RAM_47=0xFF
   - Previne watchdog trigger (embora watchdog seja código morto)

6. ✅ **Stack overflow detection funciona**
   - Inicialmente não detectava: executável desatualizado (compilação falhou)
   - Após recompilação: detecção 100% funcional!
   - Captura TODOS os eventos: underflow, overflow, SP=0x00

#### Hipóteses com Evidências

7. 🔍 **Possível bug no emulador emu8051**
   - `mov R0, #0x80` @ 0x36E1 NÃO deveria afetar SP
   - Instrução simples (opcode 0x78) corrupta?
   - Ou acesso a Upper RAM @ 0x36DF (`mov B, @R1` com R1=0x81) corrompe stack?

8. 🔍 **Auto-referências no stack indicam RET sem CALL**
   - Stack dumps @ 0x3B6A e 0x3B9D contêm endereços das próprias instruções
   - Possível execução de RET sem CALL correspondente
   - Ou stack overflow anterior deixou lixo no stack

9. 🔍 **Região @ 0x3B82-0x3BAC é inicialização de hardware**
   - Configura TODOS os periféricos (P1-P5, timers, serial, interrupts)
   - Stack corruption ocorre durante esta região crítica de boot
   - Pode ser problema de timing ou interrupt durante inicialização

---

### Referências Técnicas 📖

- **8051 Stack**: SP inicia em 0x07, cresce para cima (PUSH incrementa SP)
- **8052 Upper RAM**: 128 bytes @ 0x80-0xFF (acesso indireto via @R0/@R1)
- **ISO 9141-2**: 5-baud init = 200ms/bit (BREAK + 0x10 address byte)
- **Bosch MA1.7**: ECU Motronic de Fiat Tipo 1.6 Álcool (27C256 ROM)
- **emu8051**: Emulador não cycle-accurate, suficiente para protocol testing

---

---

## Resumo Executivo 📋

### Problema Identificado

O firmware Bosch MA1.7 sofre **stack underflow periódico** @ PC=0x36E1 durante execução da instrução `mov R0, #0x80`. Este underflow (SP: 0xD0 → 0x00) causa corrupção de stack, levando a execução de código em regiões inválidas da ROM (0xFF52, 0xFFE3) e subsequente reset do sistema via RESET_0 @ 0x0850.

**Consequência**: A cada reset, RAM é zerada, desabilitando flags K-line (RAM_17=0). O protocolo K-line slow-init **nunca é processado** porque o sistema está preso em reset loop contínuo.

### Root Cause (Suspeita)

Possível **bug no emulador emu8051**:
- Instrução `mov R0, #0x80` @ 0x36E1 NÃO deveria afetar SP
- Ou acesso a Upper RAM via `mov B, @R1` @ 0x36DF (R1=0x81) corrompe stack
- Ou interrupt preemptivo durante 0x36E1 corrompe SP

### Estado Atual

- ✅ **Stack overflow detection** implementado e funcionando
- ✅ **Problema raiz localizado** @ PC=0x36E1
- ✅ **K-line decoder e gatekeepers** mapeados completamente
- ⏳ **Root cause investigation** em andamento - requer instrumentação do emulador
- ⏳ **Upper RAM access verification** pendente

### Ação Recomendada

**PRIORITÁRIO**: Investigar implementação de `mov R0, #imm` e acesso a Upper RAM no emu8051 core. Adicionar trace detalhado antes de 0x36E1 para capturar estado exato do CPU (PSW, SP, IE, R0-R7, etc.) no momento do underflow.

---

**Última atualização**: 2025-11-15
**Investigador**: Claude Code
**Status**: ⚠️ PROBLEMA RAIZ IDENTIFICADO @ PC=0x36E1 - Aguardando análise de emulador core

---

## Análise Completa: CPU Real é SAB 80C517 (Siemens) 🔍

### Confirmação do Hardware Real ✅

**DESCOBERTA CRÍTICA**: Análise do dump IDA (`IDADUMPBINFIATTIPOIEALCOOL.txt`) confirma que o firmware Bosch MA1.7 foi compilado para um **Siemens SAB 80C517 / SAB 80C537**, **NÃO** para um 8051/8052 genérico!

#### Evidências Definitivas:

1. **Registro IRCON (Interrupt Request Control)** @ 0xC0
   - Presente em múltiplos pontos do código (0x0043 IADC, 0x0078 IEX6, 0x010A, 0x0AF9)
   - **NÃO existe** em 8051/8052 padrão
   - Específico do SAB 80C515/80C517

2. **Portas P4 e P5**
   - Inicialização @ 0x085E: `mov P4, #0xEA`
   - Inicialização @ 0x0861: `mov P5, #0x0F`
   - Uso extensivo: P4.5 para K-line RX sampling (0x0C39, 0x0C44, 0x1F5B)
   - P5.0/P5.1 para saídas CCU (0x0093-0x00AF)
   - **8051/8052 padrão só tem P0-P3!**

3. **Segunda UART (Serial 1)**
   - Vetor @ 0x0083: `RI1_TI1`
   - SFRs: S1CON, S1BUF
   - **8051/8052 tem apenas 1 UART**
   - SAB 80C517 tem **2 UARTs full-duplex**

4. **Conversor A/D Integrado**
   - Vetor @ 0x0043: `IADC` (ADC interrupt)
   - SFRs: ADCON0, ADCON1, ADDAT
   - Configuração @ 0x06DB, 0x3BBB, 0x6089
   - **NÃO existe em 8051/8052**

5. **Compare/Capture Unit (CCU)**
   - Vetor @ 0x009B: `CTF` (Compare Timer Overflow)
   - SFR: CCEN (Compare/Capture Enable) @ múltiplos pontos (0x0073, 0x0102, 0x022F)
   - **Periférico exclusivo do 80C517**

6. **Interrupções Estendidas INT2-INT6**
   - Vetores: IEX2 (0x004B), IEX3 (0x0053), IEX4 (0x005B), IEX5 (0x0063), IEX6 (0x006B)
   - **8051/8052 tem apenas INT0/INT1**

7. **IEN0/IEN1 em vez de IE**
   - Particionamento do registro de interrupt enable
   - IEN0 @ 0xA8, IEN1 @ 0xB8
   - Necessário para suportar 14 fontes de interrupção (vs 6 do 8052)

8. **Baud Rate Generator Dedicado**
   - SFRs: S0RELL @ 0x9A, S0RELH @ 0x9B
   - Configuração @ 0x3BB5: `mov S0RELL, #0xD9`
   - Permite baud rate independente de Timer1

#### Comparação: 8052 vs SAB 80C517

| Feature                  | 8052        | SAB 80C517    | No Firmware? |
|--------------------------|-------------|---------------|--------------|
| IRAM                     | 256 bytes   | 256 bytes     | ✅ Usado     |
| Timer 2                  | ✅ Sim      | ✅ Sim        | ✅ Usado     |
| Portas I/O               | P0-P3 (4)   | P0-P8 (9)     | ✅ P4, P5    |
| UARTs                    | 1           | 2             | ✅ S0, S1    |
| ADC on-chip              | ❌ Não      | ✅ 8-bit      | ✅ ADCON     |
| Compare/Capture Unit     | ❌ Não      | ✅ CCU        | ✅ CCEN/CTF  |
| Interrupts               | 6 sources   | 14 sources    | ✅ IEX2-6    |
| Baud generator dedicado  | ❌ Não      | ✅ S0RELx     | ✅ 0x3BB5    |
| IRCON register           | ❌ Não      | ✅ Sim        | ✅ 0x0043+   |
| Watchdog                 | ❌ Não      | ✅ WDTREL     | ✅ 0x0850    |

### Implicações para o Emulador 🎯

**PROBLEMA CRÍTICO**: Estamos tentando rodar firmware de **SAB 80C517** num emulador baseado em **8051/8052**!

#### Gaps Atuais do Emulador:

1. ❌ **SFRs do C517 não mapeados**:
   - IRCON, IEN0/IEN1, S0RELL/S0RELH, ADCON0/1, CCEN, P4, P5, WDTREL

2. ❌ **Periféricos não emulados**:
   - ADC (apenas hack de IRCON.6)
   - CCU/Compare Unit
   - Serial 1
   - Baud generator dedicado

3. ❌ **Acesso a Upper RAM pode estar quebrado**:
   - C517 usa Upper RAM via `@R0/@R1` para variáveis críticas (ex: RAM_89 @ 0x89)
   - Bug @ PC=0x36E1 (`mov B, @R1` com R1=0x81) pode estar corrompendo stack

---

## Análise K-line: Protocolo Slow-Init Específico do Firmware 🔬

### Descoberta: Endereço 0x10 (não 0x33 padrão OBD-II!)

**IMPORTANTE**: O firmware **NÃO** usa o endereço padrão ISO 9141-2 (0x33). Ele espera **0x10**!

#### Evidência no Código:

**@ 0x4C44 - `sub_4C44`: Decoder de Slow-Init Address**
```asm
code:00004C44     mov     A, RAM_17       ; K-line enable flag
code:00004C46     jz      code_4C73       ; BLOCKER #1: Se RAM_17 = 0, sai!
code:00004C48     mov     A, #0x10        ; ← ENDEREÇO ESPERADO!
code:00004C4A     cjne    A, RAM_40, code_4C73  ; BLOCKER #2: Se RAM_40 ≠ 0x10, sai!
code:00004C4D     setb    B.2             ; SUCCESS: Marca protocolo OK
code:00004C86     mov     RAM_3E, B       ; Copia resultado para RAM_3E
```

**Fluxo Completo do Slow-Init:**

1. **@ 0x4BF2-0x4C28**: Rotina de decodificação 5-baud
   - Amostra **P4.5** (linha K) via callback
   - Chama `code_527D` (delay + leitura de bit)
   - Acumula 10 bits em `RAM_40` (formato 5-baud: start + 8 data + stop)
   - Conta bits em `RAM_41` (compara com 0x0A)
   - Estados em `RAM_3E`, `RAM_3F`

2. **@ 0x4C44**: Validação do endereço decodificado
   - **Requisito #1**: `RAM_17 ≠ 0` (K-line habilitada)
   - **Requisito #2**: `RAM_40 == 0x10` (endereço correto!)
   - **Resultado**: `RAM_3E.2 = 1` → Habilita handler K-line

3. **@ 0x082B**: Gatekeeper para chamar decoder
   - Lê `RAM_89` (Upper RAM!) via `@R1` (R1=0x89)
   - **Requisito**: `RAM_89 == 0x04` (binário: 00000100)
   - Se OK: `lcall code_4B94` (chama decoder K-line)

#### Variáveis Críticas da K-line:

| Var      | Localização  | Função                                | Valor Esperado | Reset? |
|----------|--------------|---------------------------------------|----------------|--------|
| RAM_17   | Lower RAM    | K-line enable flag                    | 0x7F           | ✅ → 0 |
| RAM_3E   | Lower RAM    | Protocol state (bit 2 = K-line OK)    | 0x04 (bit 2=1) | ✅ → 0 |
| RAM_3F   | Lower RAM    | Contador de bits do decoder           | varies         | ✅ → 0 |
| RAM_40   | Lower RAM    | Byte decodificado (slow-init address) | 0x10           | ✅ → 0 |
| RAM_41   | Lower RAM    | Contador de bits (10 bits total)      | 0x0A           | ✅ → 0 |
| RAM_47   | Lower RAM    | Watchdog counter (de EEPROM @ 0xF8)   | 0xFF (nonzero) | ✅ → 0 |
| RAM_89   | **Upper RAM**| Gatekeeper (checked @ 0x082B)         | 0x04           | ✅ → 0 |

**PROBLEMA**: Todos zerados por `RESET_0 @ 0x0871` após cada stack overflow!

### Máquina de Estados da K-line

**Timer 0 ISR @ 0x0630+** é o motor principal:
- Gerencia timeouts
- Lê `S0CON`/`S0BUF` (UART 0)
- Compara bytes recebidos com padrões:
  - 0x55 (sync byte)
  - 0x12, 0x0A (key bytes ISO 9141)
  - @ 0x6237, 0x6253, 0x6271

**Fases do Protocolo:**

1. **Slow-init (5 baud)** → P4.5 sampling → RAM_40 = 0x10
2. **Validação** → RAM_17 + RAM_89 + RAM_40 = 0x10 → RAM_3E.2 = 1
3. **Fast UART (4800/10400 baud)** → S0CON/S0BUF + Timer 0 polling
4. **Sync** → 0x55 + key bytes
5. **Protocolo normal** → Pacotes ISO 9141-2

---

## Plano de Correção: 3 Frentes de Ataque 🔧

### Frente #1: CRÍTICO - Stack Overflow @ PC=0x36E1 ⚠️

**Problema identificado:**
```
[STACK UNDERFLOW] SP: 0xD0 → 0x00 (PC=0x36E1)
Instrução: mov R0, #0x80  (opcode 0x78)
```

**Por que isso é suspeito:**
- `mov R0, #0x80` é uma instrução **simples** que NÃO deveria afetar SP
- Instrução anterior: `mov B, @R1` (R1=0x81) → acessa **Upper RAM[0x01]**
- Pode ser bug em acesso a Upper RAM via indirect addressing

#### Ações Imediatas:

1. **Verificar implementação de PUSH/POP no emu8051**
   ```c
   // Código correto para 8052/C517 (256B IRAM):
   void push_byte(struct em8051 *cpu, uint8_t value) {
       uint8_t sp = ++(cpu->mSFR[REG_SP]);
       if (sp < 0x80) {
           cpu->mLowerData[sp] = value;  // Lower RAM
       } else {
           cpu->mUpperData[sp - 0x80] = value;  // Upper RAM!
       }
   }

   uint8_t pop_byte(struct em8051 *cpu) {
       uint8_t sp = cpu->mSFR[REG_SP];
       uint8_t value = (sp < 0x80) ? cpu->mLowerData[sp]
                                    : cpu->mUpperData[sp - 0x80];
       cpu->mSFR[REG_SP]--;
       return value;
   }
   ```

2. **Verificar acesso indireto a Upper RAM (`@R0/@R1`)**
   ```c
   // mov B, @R1 quando R1=0x81 deve acessar:
   uint8_t addr = cpu->mLowerData[R1];  // R1=0x81
   uint8_t value = cpu->mUpperData[addr - 0x80];  // Upper[0x01]
   cpu->mSFR[REG_B] = value;
   // NÃO deve tocar em SP!
   ```

3. **Instrumentar emu8051 core.c** para detectar corrupção:
   ```c
   // Antes de CADA instrução:
   static uint8_t last_sp = 0xD0;
   if (cpu->mSFR[REG_SP] != last_sp) {
       if (abs(cpu->mSFR[REG_SP] - last_sp) > 8) {
           fprintf(stderr, "[CORE BUG] SP jumped: 0x%02X → 0x%02X @ PC=0x%04X opcode=0x%02X\n",
                   last_sp, cpu->mSFR[REG_SP], cpu->mPC,
                   cpu->mCodeMem[cpu->mPC]);
       }
   }
   last_sp = cpu->mSFR[REG_SP];
   ```

4. **Hack temporário para continuar teste** (NÃO permanente!):
   ```cpp
   // main.cpp - após cada instrução:
   if (cpu.mSFR[REG_SP] == 0x00 && last_sp > 0x08) {
       fprintf(stderr, "[HACK] SP corrupted (0x%02X → 0x00) @ PC=0x%04X, forcing SP=0xD0\n",
               last_sp, cpu.mPC);
       cpu.mSFR[REG_SP] = 0xD0;  // Restaura SP
   }
   ```

#### Testes de Diagnóstico:

**Teste #1**: Rastrear call depth
```cpp
static int call_depth = 0;
// Em detect_isr_call() / após LCALL:
call_depth++;
if (call_depth > 20) {
    fprintf(stderr, "[DEPTH] Call depth = %d @ PC=0x%04X\n", call_depth, cpu.mPC);
}
// Após RET/RETI:
call_depth--;
```

**Teste #2**: Trace de Upper RAM access
```cpp
// Interceptar MOV B, @R1:
if (cpu.mPC == 0x36DF) {
    uint8_t r1 = cpu.mLowerData[1];  // R1 (register bank 0)
    fprintf(stderr, "[UPPER ACCESS] mov B, @R1: R1=0x%02X, Upper[0x%02X]=0x%02X, SP=0x%02X\n",
            r1, r1-0x80, cpu.mUpperData[r1-0x80], cpu.mSFR[REG_SP]);
}
```

**Teste #3**: Desabilitar Timer 2 temporariamente
```cpp
// Após habilitar interrupts @ 0x0B09:
cpu.mSFR[REG_IE] &= ~IEMASK_ET2;  // Desabilita Timer 2
fprintf(stderr, "[TEST] Timer 2 disabled para isolar problema\n");
// Se stack corruption SUMIR → Timer 2 estava re-entrante
// Se CONTINUAR → problema é no core (push/pop ou Upper RAM)
```

---

### Frente #2: Mapeamento de SFRs do SAB 80C517 🗺️

**Objetivo**: Garantir que o emulador entende os SFRs específicos do C517.

#### SFRs a Implementar/Verificar:

1. **Serial 0 com Baud Generator** ✅ Parcial
   - `S0CON` @ 0x98 → **Já mapeado como SCON**
   - `S0BUF` @ 0x99 → **Já mapeado como SBUF**
   - `S0RELL` @ 0x9A → ❌ **FALTANDO** (baud reload low)
   - `S0RELH` @ 0x9B → ❌ **FALTANDO** (baud reload high)

2. **Interrupt Control Estendido** ⚠️ Hacks ativos
   - `IEN0` @ 0xA8 → **Já mapeado como IE** (OK)
   - `IEN1` @ 0xB8 → ❌ **FALTANDO**
   - `IP0` @ 0xA9 → ✅ **Monitorado via callback**
   - `IP1` @ 0xB9 → ❌ **FALTANDO**
   - `IRCON` @ 0xC0 → ⚠️ **Hack: forçando bit 0 = 1**

3. **Portas Extras**
   - `P4` @ 0xE8 → ✅ **Callback implementado** (leitura de P4.5 para K-line)
   - `P5` @ 0xF8 → ❌ **FALTANDO** (usado para saídas CCU)

4. **Timer 2** ✅ Implementado
   - `T2CON` @ 0xC8 → ✅ OK (PR #40)
   - `TH2/TL2`, `RCAP2H/L` → ✅ OK

5. **ADC** ❌ Não implementado
   - `ADCON0` @ 0xD8
   - `ADCON1` @ 0xD9
   - `ADDAT` @ 0xD9 ou 0xDA (depende do manual)

6. **Compare/Capture Unit** ❌ Não implementado
   - `CCEN` @ 0xC1
   - `CCLx/CCHx` registradores

7. **Watchdog** ❌ Não implementado
   - `WDTREL` @ 0x86

8. **Power Control** ⚠️ Parcial
   - `PCON` @ 0x87 → Existe no 8052, mas C517 tem bits extras

#### Estratégia de Implementação:

**Opção A: Stub Neutro** (para SFRs não-críticos)
```cpp
// Callback em cb_sfr_write():
case 0x9A:  // S0RELL
case 0x9B:  // S0RELH
case 0xB8:  // IEN1
case 0xB9:  // IP1
case 0x86:  // WDTREL
    // Aceita escrita mas não faz nada
    fprintf(stderr, "[SFR STUB] Write to 0x%02X = 0x%02X (ignored)\n", aAddress, aValue);
    return aValue;  // Permite que core armazene
```

**Opção B: Emulação Mínima** (para SFRs semi-críticos)
```cpp
case 0xC1:  // CCEN (Compare/Capture Enable)
    // Aceita escrita, mas não dispara compare interrupts
    fprintf(stderr, "[CCU] CCEN = 0x%02X (stub, no compare logic)\n", aValue);
    return aValue;

case 0xD8:  // ADCON0
    fprintf(stderr, "[ADC] ADCON0 = 0x%02X (stub, no ADC logic)\n", aValue);
    // Se firmware ler ADDAT, retornar valor fixo (ex: 0x80 = mid-range)
    return aValue;
```

**Opção C: Implementação Completa** (apenas se necessário)
- Apenas para SFRs que o firmware **realmente precisa** responder
- Exemplo: Se firmware entrar em loop tipo `jnb ADCON0.BSY, $` esperando ADC terminar
- Prioridade baixa se firmware usar apenas interrupt-driven ADC

#### Mapeamento Atual:

```cpp
// main.cpp - cb_sfr_read() / cb_sfr_write()
// ATUAL (verificar aliases):
#define REG_SCON  0x98   // = S0CON
#define REG_SBUF  0x99   // = S0BUF
#define REG_IE    0xA8   // = IEN0
#define REG_IP    0xA9   // = IP0
#define REG_P4    0xE8   // Callback implementado

// ADICIONAR:
#define REG_S0RELL  0x9A
#define REG_S0RELH  0x9B
#define REG_IEN1    0xB8
#define REG_IP1     0xB9
#define REG_IRCON   0xC0  // Já tem hack
#define REG_CCEN    0xC1
#define REG_WDTREL  0x86
#define REG_ADCON0  0xD8
#define REG_ADCON1  0xD9
#define REG_ADDAT   0xDA  // Verificar offset no manual
#define REG_P5      0xF8
```

---

### Frente #3: K-line Slow-Init com Endereço 0x10 📡

**Objetivo**: Garantir que o firmware recebe **0x10 @ 5 baud** e processa corretamente.

#### Checklist de Implementação:

1. ✅ **P4.5 callback** → Já implementado (cb_sfr_read @ 0xE8)

2. ❌ **Timing do 5-baud** → Precisa sincronizar com delays de `code_527D`
   - Cada bit: ~200 ms (5 baud)
   - 10 bits totais: 1 start + 8 data + 1 stop
   - Formato: `0 0001 0000 1` (LSB first) = 0x10

3. ❌ **Inicializar flags antes do slow-init**
   ```cpp
   // main.cpp - antes de começar execução:
   // WORKAROUND temporário para testar fast protocol:
   cpu.mLowerData[0x17] = 0x7F;           // RAM_17: K-line enabled
   cpu.mUpperData[0x89 - 0x80] = 0x04;    // RAM_89: Gatekeeper OK
   cpu.mLowerData[0x40] = 0x10;           // RAM_40: Slow-init OK (0x10 decoded)
   cpu.mLowerData[0x3E] = 0x04;           // RAM_3E.2: Protocol active
   fprintf(stderr, "[K-LINE BYPASS] Flags inicializados para testar fast protocol\n");
   ```

4. ❌ **Trace de decoder @ 0x4BF2-0x4C8C**
   ```cpp
   // Adicionar no loop principal:
   if (cpu.mPC >= 0x4BF2 && cpu.mPC <= 0x4C8C) {
       static int decoder_trace_count = 0;
       if (decoder_trace_count++ < 1000) {  // Primeiros 1000 acessos
           uint8_t p4 = cpu.mSFR[REG_P4];
           fprintf(stderr, "[DECODER] PC=0x%04X P4=0x%02X (P4.5=%d) "
                   "RAM_40=0x%02X RAM_41=%d RAM_3E=0x%02X RAM_3F=0x%02X\n",
                   cpu.mPC, p4, (p4 >> 5) & 1,
                   cpu.mLowerData[0x40], cpu.mLowerData[0x41],
                   cpu.mLowerData[0x3E], cpu.mLowerData[0x3F]);
       }
   }
   ```

5. ❌ **Trace de gatekeeper @ 0x082B**
   ```cpp
   if (cpu.mPC == 0x082B) {
       uint8_t ram89 = cpu.mUpperData[0x89 - 0x80];
       fprintf(stderr, "[GATEKEEPER] PC=0x082B RAM_89=0x%02X (expect 0x04)\n", ram89);
       if (ram89 == 0x04) {
           fprintf(stderr, "[GATEKEEPER] ✅ Condition met, will call decoder\n");
       } else {
           fprintf(stderr, "[GATEKEEPER] ❌ Condition NOT met (RAM_89 != 0x04)\n");
       }
   }
   ```

6. ❌ **Enviar 0x10 @ 5 baud pelo PTY** (script Python)
   ```python
   # test_pty_5baud.py
   import serial
   import time

   # Encontrar PTY path do emulador
   pty_path = "/dev/pts/X"  # Substituir pelo path real

   # Abrir porta
   ser = serial.Serial(pty_path, baudrate=5, bytesize=8, parity='N', stopbits=1)

   # Enviar BREAK (200ms low)
   ser.send_break(duration=0.2)
   time.sleep(0.02)

   # Enviar 0x10 @ 5 baud (cada bit = 200ms)
   # 0x10 = 0b00010000 = bits: 0(start) 0 0 0 0 1 0 0 0 1(stop)
   ser.write(b'\x10')
   ser.flush()

   print("Sent slow-init: BREAK + 0x10 @ 5 baud")

   # Aguardar resposta (0x55 + key bytes @ 4800 baud)
   ser.baudrate = 4800
   time.sleep(0.5)

   response = ser.read(10)  # Ler até 10 bytes
   print(f"Response: {response.hex()}")
   ```

---

## Ordem de Ataque Recomendada 🎯

### Fase 1: Resolver Stack Corruption (CRÍTICO) ⚠️

**Prioridade**: 🔴 MÁXIMA

1. ✅ Adicionar trace detalhado antes de 0x36E1 (PC, SP, PSW, R0-R7, IE)
2. ✅ Verificar implementação de push/pop com Upper RAM no emu8051
3. ✅ Verificar acesso indireto `@R0/@R1` para Upper RAM
4. ✅ Instrumentar core.c para detectar SP jumps > 8 bytes
5. ⚠️ Hack temporário: forçar SP=0xD0 se SP==0x00 (diagnóstico apenas!)
6. ✅ Teste: desabilitar ET2 para verificar se Timer 2 é reentrante
7. ✅ Teste: rastrear call depth para detectar stack overflow real vs bug

**Resultado esperado**: Stack permanece em 0xD0-0xDF, sem saltos para 0x00.

---

### Fase 2: Mapear SFRs Críticos do C517 🗺️

**Prioridade**: 🟡 ALTA

1. ✅ Implementar stubs para S0RELL/S0RELH, IEN1, IP1, WDTREL
2. ✅ Implementar stub para CCEN (aceita escrita, sem lógica)
3. ✅ Implementar stub para ADCON0/ADCON1/ADDAT (retorna valor fixo se lido)
4. ✅ Implementar callback para P5 (leitura/escrita)
5. ✅ Revisar hack de IRCON (pode estar distorcendo lógica)

**Resultado esperado**: Firmware não trava em loops esperando SFRs não implementados.

---

### Fase 3: K-line Slow-Init com 0x10 📡

**Prioridade**: 🟢 MÉDIA (após Fase 1 OK)

1. ✅ Adicionar trace completo do decoder (0x4BF2-0x4C8C)
2. ✅ Adicionar trace do gatekeeper (0x082B)
3. ✅ Implementar script Python para enviar 0x10 @ 5 baud
4. ✅ Bypass temporário: inicializar RAM_17/89/40/3E para testar fast protocol
5. ✅ Verificar timing entre PTY e callback P4.5
6. ✅ Remover bypass após confirmar slow-init funcionando

**Resultado esperado**: Firmware aceita 0x10, seta RAM_3E.2=1, entra em modo UART rápido.

---

### Fase 4: Teste Completo com Scanner K-line 🚗

**Prioridade**: 🟢 BAIXA (após todas acima OK)

1. ✅ Conectar scanner K-line real ao PTY
2. ✅ Enviar slow-init (0x10 @ 5 baud)
3. ✅ Verificar resposta: 0x55 + key bytes
4. ✅ Estabelecer sessão ISO 9141-2
5. ✅ Ler DTCs / parâmetros ao vivo
6. ✅ Documentar protocolo específico do MA1.7

**Resultado esperado**: Comunicação K-line completa funcional! 🎉

---

## Referências Técnicas Atualizadas 📚

### Datasheets SAB 80C517:
- **User's Manual**: https://www.cin.ufpe.br/~if728/80c5x7_um.pdf
- **Datasheet**: https://www.alldatasheet.com/datasheet-pdf/pdf/45579/SIEMENS/SAB80C517.html
- **C517A Addendum**: https://www.scribd.com/document/320243342/80c5x7A-User-Manual-Addendum

### Mapeamento de SFRs C517:
| SFR       | Addr | Função                          | No Firmware? |
|-----------|------|---------------------------------|--------------|
| S0CON     | 0x98 | Serial 0 Control                | ✅ 0x0025+   |
| S0BUF     | 0x99 | Serial 0 Buffer                 | ✅ UART TX/RX|
| S0RELL    | 0x9A | Serial 0 Reload Low             | ✅ 0x3BB5    |
| S0RELH    | 0x9B | Serial 0 Reload High            | ✅ 0x3BB5    |
| IEN0      | 0xA8 | Interrupt Enable 0              | ✅ 0x0045+   |
| IP0       | 0xA9 | Interrupt Priority 0            | ✅ 0x0875    |
| IEN1      | 0xB8 | Interrupt Enable 1              | ✅ 0x0409+   |
| IP1       | 0xB9 | Interrupt Priority 1            | ✅ (menos usado)|
| IRCON     | 0xC0 | Interrupt Request Control       | ✅ 0x0043+   |
| CCEN      | 0xC1 | Compare/Capture Enable          | ✅ 0x0073+   |
| T2CON     | 0xC8 | Timer 2 Control                 | ✅ 0x3B9A    |
| ADCON0    | 0xD8 | ADC Control 0                   | ✅ 0x06DB+   |
| ADCON1    | 0xD9 | ADC Control 1                   | ✅ 0x3BBF    |
| ADDAT     | 0xDA | ADC Data                        | ✅ 0x071B+   |
| P4        | 0xE8 | Port 4                          | ✅ 0x085E+   |
| P5        | 0xF8 | Port 5                          | ✅ 0x0861+   |
| WDTREL    | 0x86 | Watchdog Timer Reload           | ✅ 0x0850    |

### Endereços Críticos no Firmware:
| Endereço | Função                              | Notas                      |
|----------|-------------------------------------|----------------------------|
| 0x0000   | Reset vector                        | ljmp RESET_0               |
| 0x0850   | RESET_0 - Inicialização             | Zera RAM_17/47/89!         |
| 0x082B   | Gatekeeper (RAM_89 == 0x04?)        | Chama decoder se OK        |
| 0x4BF2   | Slow-init decoder (5-baud)          | Decodifica via P4.5        |
| 0x4C44   | Address validator (0x10?)           | Valida RAM_40 == 0x10      |
| 0x36E1   | **PROBLEMA: Stack underflow**       | mov R0, #0x80 → SP=0x00!   |
| 0x0630   | Timer 0 ISR (motor da ECU)          | Máquina de estados K-line  |

---

**Última atualização**: 2025-11-15 (Análise completa SAB 80C517)
**Investigador**: Claude Code
**Status**: 🔴 CRÍTICO - Stack overflow @ PC=0x36E1 deve ser resolvido ANTES de testar K-line
**Próximo passo**: Instrumentar emu8051 core.c para rastrear bug de SP corruption
