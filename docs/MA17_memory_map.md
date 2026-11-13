# MA17 Memory Map (draft)

Objetivo rápido: consolidar o que já sabemos da RAM interna (0x00–0x7F) e da XRAM paginada em 0xF8xx, destacando buracos a preencher antes de portar o firmware para C++.

## Notas de endereçamento
- **IRAM**: 256 B; 0x00–0x7F (acesso direto), 0x80–0xFF só via indireto. Região bit-addressable em 0x20–0x2F.
- **XRAM**: acessada com `MOVX @R0/@R1`; o firmware carrega `P2 = 0xF8` antes dos acessos, portanto os endereços efetivos são 0xF8xx (janela de 256 B). Rotinas de reset em 0x0850/0x0883 também varrem essa página com padrões AA/55.

## IRAM — mapeado
**Buffers de resposta**
- 0x00  Ponteiro do buffer (aponta para 0x10).
- 0x10  Tipo de resposta (`0x03/0x04/0x0B/0x0D/0xFE`).
- 0x12–0x14 Cabeçalho/códigos do frame.

**Flags e estado de protocolo**
- 0x21  Flags de sessão (timeout, pronto, RX/TX, erro).
- 0x22  Flags auxiliares do protocolo.
- 0x2A  Máquina de estados K-line (bits 0–3) + enable/aux.
- 0x2B  Flags de erro/condição.
- 0x2D  Gate de comunicação (bit 2 bloqueia o handler de Timer0).
- 0x2E  Flags de falha (bit 7 = erro XRAM na inicialização).
- 0x2F  Safety flags (e.g., motor ligado).

**Contadores / temporização**
- 0x30  Service counter (decrementado no IEX3).
- 0x31  Comprimento da resposta em bytes.
- 0x33–0x34 Contadores de frames/seq.
- 0x36  Tick periódico (incrementado em `diagnostic_periodic_tick`).
- 0x3E  Retry budget; 0x3F watchdog curto (~5‑baud window).
- 0x40  Registrador shift do slow‑init; 0x41 bit counter (20→0).
- 0x42  Fase do handshake/protocolo.
- 0x47  RPM calculado (copiado da XRAM) / último byte lido.
- 0x50–0x51 Variáveis gerais de máquina de estados/timeout.
- 0x52–0x55 Capturas de período/largura (Timer2) + valores anteriores.
- 0x56  Tick de Timer2 (10 ms cadenciado).
- 0x6B  Contador de pulsos INT0 (djnz/inc no vetor 0x0003).

**Sensores (resumo)**
- 0x46 Nominal revs; 0x47 Engine RPM.
- 0x60/0x66/0x6F/0x70 Eixos de borboleta (trilhos 1/2 e razão).
- 0x62 Ar; 0x63 Água; 0x65 Lambda; 0x69 Avanço; 0x7D Bateria.
- Defaults aplicados em 0x0AC1–0x0AD0: 0x66=0x80, 0x60=0x0D, 0x7D=0xC0, 0x62=0xE7, 0x63=0xE7, 0x65=0x32.

## IRAM — lacunas prioritárias
- 0x15–0x1B  Campos auxiliares do buffer/ADC (não descritos).
- 0x23–0x29  Bits de status além dos já mapeados (28/29 citados, falta detalhar por bit).
- 0x44–0x4F  Zona tocada por reset (ex.: 0x4A/0x4B = 0xFF) sem papel definido.
- 0x57–0x5F  Espaço entre capturas e blocos de sensor ainda não atribuído.
- 0x68/0x6A e 0x71–0x7C  Dados de sensor/diagnóstico não correlacionados a frames.

## XRAM 0xF8xx — mapeado
> Todos acessos via `MOVX` com `P2=0xF8`; onde o alto byte não estiver confirmado, gravar o valor de P2 no emulador para validar.

- **0xF8C4**  Latch de estado da IEX3 (valores 1/2/4 usados para sequenciar a rotina de captura e desbloqueio de `RAM_2A`).
- **0xF8F8**  Marca/RPM externo: lido em 0x01AD → `RAM_47`; zerado no handler de Timer0 em 0x0DF2. Mantém cópias em 0xF89B/0xF89C.
- **0xF89B / 0xF89C**  Scratch/backup do último byte lido (copiados em 0x01B2–0x01B5 e também zerados em 0x0DF5/0x0DF8).
- **0xF89E**  Índice de erro/diagnóstico (`kline_compute_indices_from_flags` e recovery @0x5639); inicializado na rotina de reset.
- **0xF891**  Estado de erro auxiliar (lido em rotinas de timeout/recovery @0x0883/0x5639).
- **0xF893–0xF896**  Bloco inicializado no reset (0x93/0x92/0x95 zerados; 0x94 recebe 0x3C; 0x96 recebe tabela via `movc`). Função ainda não correlacionada a frames/sensores.
- **0xF8A9**  Zerada no reset; provável acumulador/adaptação de injeção (a confirmar).
- **0xF8D6–0xF8D8**  Zerados condicionalmente (quando `T2CON.1` = 0) no reset; possivelmente contadores de watchdog longo.

## XRAM — buracos a mapear
- 0xF800–0xF88F  Não referenciados nas análises existentes; checar padrões de teste em `reset_xram_tests_and_read_marker`.
- 0xF8A0–0xF8B0  Escritas parciais (ex.: 0xF8A8) mas sem associação funcional clara.
- 0xF8C0–0xF8C3 / 0xF8C5–0xF8F7  Provável área de estado/K-line; capturar trace de `MOVX` em `kline_serial_state_machine`.

## Próximos passos sugeridos
1) Instrumentar o emulador para logar `P2` e `MOVX` durante reset/Timer0/IEX3, confirmando se todos acessos usam a página 0xF8xx.
2) Marcar em trace os bytes que mudam entre slow‑init (0x4C34/0x4C44) e `diagnostic_serial_service` para preencher as lacunas 0xF8C0–0xF8FF.
3) Completar o detalhamento bit‑a‑bit de 0x28/0x29/0x2E/0x2F e dos bytes 0x57–0x5F correlacionando com tabelas de sensores e flags de atuadores.
4) Documentar os efeitos das rotinas de autoteste de XRAM (0x0850/0x0883/0x55C6/0x5739) sobre a janela 0xF800–0xF8FF.
