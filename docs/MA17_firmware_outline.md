# Inventario inicial para reescrita do firmware MA17 (C++20)

Fonte: `FiatTipo_MA17_dump_27c256.asm` (base 0x0000, 32 KiB) e rótulos de `firmware_labels.txt`. Objetivo: separar blocos lógicos para portar em C++ seguindo CppCoreGuidelines.

Estado atual
- Feito: leitura macro do dump e marcação dos pontos criticos; mapa abaixo.
- Falta: detalhar fluxo interno de cada rotina e mapear estruturas de dados (XRAM, flags) antes de escrever C++.

Blocos a transformar em C++ (endereco ROM -> responsabilidade -> nota de reescrita)

Boot / memoria / autotestes
- 0x0850 `reset_system_init`: configura watchdog/portas/SP, zera IRAM e roda autoteste de XRAM; modelar como `ResetManager` com inicializacao idempotente.
- 0x0883 `reset_xram_tests_and_read_marker` (+0x08B1/0x08B8/0x092E): marcadores e assinatura de XRAM, seta flags de erro; propor struct `XramSelfTest` com enum de resultado.
- 0x55C6 `ext_ram_pattern_write_verify` e 0x5739 `xram_copy_and_verify`: testes de padrao e copia; reutilizar utilitario de memoria com `std::span<uint8_t>`.
- 0x6395 `copy_flash_block_to_ram_buffer` / 0x4DC6 `copy_code_to_xram` / 0x4EAF `serial_table_copy_to_xram`: pipelines ROM↔XRAM; mapear para `copy_block(src, dst, size)` com checagem de limites.

Temporizacao e interrupcoes
- 0x000B `TF0` -> 0x0630 dispatcher; 0x185F/0x2FF4/0x319B/0x454F: agenda periodica e flags de overflow; encapsular em `Timer0Scheduler` com callbacks registrados.
- 0x002B `TF2_EXF2` e 0x6320 `timer2_init_for_boot`: tick de 10 ms para timeouts; expor como `Timer2Tick` que incrementa contadores e dispara expiração.
- 0x0043 `IADC` e 0x6441 `adc_collect_8_samples`: sinaliza fim de conversao e coleta round-robin; modelar `AdcSampler` que retorna vetor de 8 canais.
- 0x00B0 `IEX3` captura periodo/largura (0x565A-0x56A2); traduzir para classe `CaptureUnit` com medidas em microsegundos usando `std::chrono`.

Linha K / diagnostico
- 0x4AD1 `kline_detect_slow_baud_and_boot` + 0x4C34/0x4C44 decodificador 5-baud: handshake ISO 9141-2; implementar estado `SlowInit` com amostragem de pino e validacao do byte 0x10.
- 0x4BDE `kline_serial_state_machine` & 0x4CDC `error_retry_point` & 0x4D01 `serial_error_clear`: FSM principal de RX/TX/erro; mapear para `KLineSession` com enum de estados e filas de TX/RX.
- 0x63A9 `serial0_service_handler` e 0x61D8 `diagnostic_serial_service`: servico cooperativo da UART0, valida checksum e despacha handlers de frame; traduzir para laço chamado pelo tick.
- 0x6004 `diag_mode_init` & 0x60BA `diag_prepare_boot_response` & 0x6269/0x6271 handlers de frames 0x12/0x0A: inicializacao do modo diagnostico e respostas padrao; estruturar handlers registrados em `std::array<FrameHandler, N>`.
- 0x63C4 `diagnostic_periodic_tick` e 0x51C1/0x51F1 atualizacao de timeouts: manutencao de sessao; encapsular contadores com tipos fortes.

Sensores e tabelas
- 0x06E1 `timer0_lookup_table_movc`: seleciona canal ADC; converter em tabela `constexpr std::array<uint8_t, ...>`.
- 0x0AC1 `sensor_init_default_values`: valores iniciais de sensores; mapear para struct `SensorState` com inicializador.
- 0x645D `read_multi_port`: empacotamento de bits de portas/flags; reimplementar com mascaras explicitas e testes unitarios.
- 0x6E7A `sensor_lookup_table`: mapa de IDs K-line -> offsets de RAM; gerar tabela `constexpr` e validar tamanhos.

Math/uteis compartilhados
- 0x5205 `mul16x16_to_32`, 0x5246 `mul_signed_a_by_b_16bit`, 0x5259 `mul_u16_by_u8_to_u24`, 0x536D `arith_div16_restoring`, 0x5389 `timer0_update_24bit_clamped`, 0x5419 `timer0_sat_add_thresh_chk`, 0x54CF `mul_table_entry_shr4_saturate`: agrupar em namespace `math` com testes focados em overflow/saturacao (usar `std::uintXX_t`).
- 0x5228 `load_dptr_from_code_table`, 0x527C `find_table_segment_and_4bit_fraction`, 0x545D `timer_set_flags_load_rom_entry14`: rotinas de tabela/interpolacao; mapear para helpers `lookup_table(idx)` com checagem de limites e retorno de `std::optional`.

Estado de progresso
- Feito: inventario inicial de blocos e enderecos criticos do firmware (fonte: `FiatTipo_MA17_dump_27c256.asm` + `firmware_labels.txt`).
- Falta: extrair variaveis globais (RAM_2x, offsets em XRAM) e definir interfaces C++ (tipos fortes para flags e buffers) antes de codificar.
- Falta: validar suposicoes de temporizacao (tick de 10 ms, 5-baud) com logs existentes e anotar invariantes para testes.

Proximos passos sugeridos
1) Mapear layout de RAM/XRAM e publicar em `docs/MA17_memory_map.md`.
2) Esbocar headers C++ (`include/ma17/*.hpp`) com interfaces minimas para Timer, KLine e ADC.
3) Escolher convencao de scheduler (loop cooperativo vs. interrupcoes simuladas) e provar com teste GoogleTest para `Timer0Scheduler`.
