# Alterações no núcleo emu8051 (submódulo)

Alterações de código feitas sobre o `jarikomppa/emu8051` em `emu8051/`.
Os demais arquivos modificados no submódulo (`disasm.c`, `emulator.h`, `logicboard.c`,
`mainview.c`, `memeditor.c`, `options.c`, `popups.c`, `README.md`) têm apenas
mudanças de indentação/whitespace. Para ver só o que importa:

```bash
cd emu8051 && git diff -w --stat   # lista core.c, emu8051.h, opcodes.c
```

O projeto trabalha com o SAB80C517 (`-DENABLE_SAB80C517=ON`); os itens marcados
`[517]` só existem nesse modo.

## emu8051.h

- Novo tipo `em8051coderead` e campo `coderead` em `struct em8051`: callback
  `void (*)(struct em8051 *, uint16_t addr)` chamado em leituras de código via MOVC.

## opcodes.c

| Item | Antes | Depois |
|------|-------|--------|
| AC em `add_solve_flags` | `((v1&7)+(v2&7)+c)>>3` | `(((v1&0x0F)+(v2&0x0F)+c)>>4)&1` (carry do bit 3 para o 4) |
| `sub_solve_flags` | carry e AC por subtração com shift | carry = `v1 < v2 + cin`; AC = `(v1&0x0F) < (v2&0x0F) + cin` (borrow) |
| `MOVC A,@A+PC` | retornava 0 | retorna 1 (instrução de 2 ciclos); chama `coderead` |
| `MOVC A,@A+DPTR` | sem callback | chama `coderead` antes da leitura |

## core.c

1. **Off-by-one do `mTickDelay` em `tick()`**: antes, ao decrementar o contador o fluxo
   seguia e a próxima instrução executava no mesmo tick em que ele zerava, então toda
   instrução que devolvia N gastava N ticks em vez de N+1. Agora o `tick()` decrementa,
   avança `timer_tick`/`timer2_tick` e retorna `false`.
   **Efeito:** toda instrução multiciclo ficou ~1 ciclo mais lenta; recalibrar qualquer
   temporização baseada em ticks (ex.: `FiveBaudInjector`, 990.000 instr/s).
2. **Despacho de interrupção** (`handle_interrupts` e `handle_interrupts_80c517`):
   `mTickDelay = 2` → `1`. Com a correção acima, o LCALL de hardware dura 2 ciclos
   (1 de despacho + 1 de espera).
3. **[517] Prioridade 0**: nas fontes SR1, IADC, IEX2, IEX3, CTF, IEX4, IEX5 e IEX6 a
   condição passou a `pri > highest_priority` → `(dest_ip < 0 || pri > highest_priority)`.
   Como `highest_priority` começa em 0, uma fonte de prioridade 0 nunca era atendida.
4. **[517] Inibição de IRQ de 1 instrução**: o contador `irq_inhibit` (setado por escritas
   em IEN*/IP* e por RETI) era decrementado *antes* do teste, o que anulava a inibição.
   Agora: se `irq_inhibit == 0` trata interrupções, senão decrementa.
5. **`reset()`**:
   - guardas contra `mCodeMem`/`mExtData` nulos no `memset` com `aWipe`;
   - `coderead = NULL`. **Registre o callback depois de chamar `reset()`**, senão ele é apagado.

## Verificação pendente

Não foi feito build nem `ctest` após essas alterações. Rodar com
`-DENABLE_SAB80C517=ON` (build limpo ao alternar o modo, por causa do SFR 0xB8 IP/IEN1).
Depois de commitar dentro do submódulo, atualizar o ponteiro no repositório pai.
