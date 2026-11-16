# Inventário semântico do Fiat Tipo MA1.7 — checkpoint inicial

O alvo é `FiatTipo_MA17_dump_27c256.bin`, SHA-256
`a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
Endereços, labels, tempos e associações de portas neste inventário pertencem
ao **Fiat Tipo**. As comparações com o dump **Renault Clio** são pistas de
homologia de código, não equivalências de hardware ou temporização.
O listing `FiatTipoIDAFullDump_27c256.asm` declara o mesmo hash. Seus nomes
foram indexados como evidência de análise anterior, sem aceitar automaticamente
as descrições: por exemplo, `WATER_TEMP_RAM` aparece como label no vetor 0063h.

**Nota sobre os ensaios dinâmicos históricos:** o emulador implementava
`MOV direct,@R0/@R1` (opcodes `86h/87h`) com a direção de transferência
invertida. Isso alterava a execução real da ROM, inclusive a leitura da
RAM superior `87h` em `1558h`. As tabelas de largura CC3, valores de
`RAM[14h:15h]`, fases e afirmações de correção lambda medidas antes da
correção abaixo são registros históricos e não devem fundamentar novas
inferências. Os ensaios refeitos com o opcode corrigido estão em
`MA17_FIRMWARE_VARIANTS_ANALYSIS.md`, com dados estruturados em
`build/ma17-analysis/variants/experiments_opcode86_fixed/` e
`build/ma17-analysis/variants/lambda_opcode86_fixed/`. A análise estática
dos bytes da ROM não depende desse defeito.

## Reproduzir os artefatos

```sh
python3 tools/roundtrip_8051.py FiatTipo_MA17_dump_27c256.bin
python3 tools/inventory_ma17.py
python3 tools/modularize_ma17.py
./run_full_test.sh
cmake -S . -B build -DENABLE_TESTS=ON
cmake --build build
python3 tools/trace_ma17.py
python3 -m unittest discover -s tests -p 'test_roundtrip_8051.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_pty_protocol.py' -v
```

Os testes PTY usam `pyserial` no `.venv` (`.venv/bin/python -m pip install
pyserial`) e executam o emulador com o dump Fiat e `--8052`.

O inventário por endereço, instrução, chamada, desvio, operando de IRAM e SFR
fica em `build/ma17-analysis/inventory.json`. Ele também lista cargas
imediatas de `DPTR`, extraídas dos bytes de opcode `90h`; seus destinos são
endereços carregados, não referências de leitura comprovadas. Cada instrução
e referência aponta para uma linha do listing IDA. Esse arquivo é um índice,
não uma atribuição automática de propriedade de cada bloco a uma função; o
IDA usa
funções com chunks não contíguos. Os arquivos de montagem ficam em
`build/ma17-analysis/modular/`: `ma17.asm` inclui `registers.inc` e seis
módulos ordenados por endereço. Os limites foram escolhidos em fronteiras de
instrução ou lacunas `ORG`; os nomes dos módulos indicam o tema predominante,
pois alguns contêm código misto ou ainda não identificado. A fonte geradora
e o cadastro de aliases ficam versionáveis em `tools/` e
`asm/ma17/semantic_labels.tsv`.
Para inspecionar ou versionar os módulos gerados em outro diretório, use
`python3 tools/modularize_ma17.py --output-dir asm/ma17/generated`; o relatório
e o binário de validação são gravados no mesmo diretório escolhido.
Após editar um `*.inc`, monte diretamente o `ma17.asm` no diretório dos
módulos, por exemplo:

```sh
(cd build/ma17-analysis/modular && ../../../asm51/asm51 -n -f bin -o ma17.modified.bin ma17.asm)
```

Reexecutar `modularize_ma17.py` gera novamente os includes no diretório de
saída escolhido. O teste `test_modular_assembly_edits_change_only_selected_bytes`
gera uma cópia temporária, muda um imediato de código em 0852h e um byte da
tabela de falhas em 6E4Dh e um endereço da tabela de sensores em 6E79h;
confirma que a montagem altera apenas esses três offsets.

| Métrica | Valor atual | Interpretação |
| --- | ---: | --- |
| Entradas de função no IDA | 106 | 102 com alias de código e 4 em vetores apagados |
| Aliases com evidência de código | 127 | Preservam labels originais e identificam entradas sem `jump_XXXX` |
| Aliases de tabelas confirmadas | 7 | Preservam labels `dptr_XXXX` e identificam as duas entradas de RPM/bateria |
| Entradas restantes sem revisão | 0 | Cento e dois aliases de código são entradas IDA; vinte e cinco são blocos internos |
| Entradas IDA em vetores apagados | 4 | Marcadas `confirmed_erased`, sem alias de código |
| Entradas nomeadas apenas como hipótese | 0 | Nomes incertos do IDA ficam não revisados |
| Instruções indexadas do IDA | 12.469 | Linhas de instrução, não bytes |
| Referências de fluxo | 3.476 | Chamadas e desvios diretos |
| Cargas imediatas de `DPTR` | 212 | 126 valores distintos; 207 apontam para bytes classificados como dados |
| Leituras `MOVC A,@A+PC` | 3 | Nenhuma pode alcançar 5269h ou 53DAh pelo deslocamento de oito bits |
| Referências sem destino textual | 0 | Dois `nullsub` vieram de funções compactadas |
| Endereços IRAM referenciados | 104 | Ocorrências indexadas por endereço |
| Nomes SFR referenciados | 42 | Ocorrências indexadas por nome |
| Inícios em múltiplos fluxos de função | 9.222 | Fluxos se sobrepõem; não representam limites exclusivos |
| Inícios fora de todo fluxo direto | 37 | Linhas do IDA que decodificam vetores `FFh` apagados |
| Código / dados / `FF` omitidos | 23.420 / 4.117 / 5.231 bytes | Classificação do `disasm51` após preservar `FF` com label |
| Código / dados / `FF` no assembly modular | 23.420 / 4.120 / 5.228 bytes | Três `FFh` adicionais da tabela de falhas são `DB` explícitos |
| Regiões `FF` omitidas na saída bruta | 44 | Maiores: 64A2h..6DFFh (2.398 B), 58D8h..5FFFh (1.832 B) |
| Faixas `DB` com hipótese explícita de código | 2 / 79 bytes | 5269h..5278h e 53DAh..5418h; nenhuma entrada confirmada |

O campo `flow_reachable_instruction_starts` de cada entrada percorre saltos
diretos, condicionais e fallthrough até `RET`/`RETI`; chamadas permanecem na
rotina chamadora apenas pelo endereço de retorno. Não modela saltos indiretos,
alteração da pilha nem fronteiras de chunks do IDA. Os 9.222 inícios
compartilhados mostram que esses conjuntos não podem ser usados como
propriedade exclusiva de função. Três funções compactadas (`IEX3` e dois
`nullsub`) não têm linha de instrução expandida no listing, embora os bytes
originais existam na ROM.
O campo `analysis_priority` ordena entradas ainda não revisadas pelo número
de chamadas diretas recebidas. A contagem prioriza inspeção; não
confirma os nomes semânticos dados pelo IDA.

Cinco cargas de `DPTR` apontam para quatro bytes `FFh` com label de dados:
0B33h→7FF5h, 1CF1h→7109h, 383Dh→7163h e
42C9h/4329h→6E27h. Em 0B36h, `MOVC` lê diretamente o primeiro byte
`FFh` em 7FF5h e o compara com `55h`; em 6E27h há dois `FFh` antes dos
registros de diagnóstico que começam em 6E29h. O `disasm51` agora emite
esses quatro bytes como `DB 0FFh` para que os labels e valores sejam
editáveis; outros `FFh` contíguos continuam implícitos nas lacunas `ORG`.
As cargas de 7109h e 7163h passam `DPTR` à rotina
5314h, que lê dois bytes da tabela por `MOVC` em 532Fh e 5333h; a execução
de um índice que alcance os `FFh` iniciais ainda não foi observada. A carga
de 6E27h em 4329h chega ao `MOVC` de 4338h após calcular o índice em `A`.

Uma auditoria dos inícios de instrução do assembly remontável não encontrou
`JMP @A+DPTR` (opcode `73h`). Há 71 bytes `73h` na ROM, mas nenhum inicia
uma instrução classificada como código; os que aparecem dentro desse código
são operandos. Isso não exclui entradas ainda desconhecidas em regiões de
dados. As escritas explícitas em `SP` são duas inicializações imediatas;
630Fh lê `SP` para testar seu bit 7. Os `PUSH`/`POP` identificados salvam e
restauram registradores; ainda não há evidência de um `RET` com endereço de
retorno construído na pilha.
O uso de `MOVC A,@A+PC` em 06E1h é busca de byte na ROM, não transferência
de controle.

O manual SAB80C517, tabela 8-2, lista 14 vetores, incluindo `IEX3=0053h`,
`IEX5=0063h` e `CTF=009Bh`. Neste dump, os espaços de `IE1=0013h`,
`IEX2=004Bh`, `IEX4=005Bh` e `RI1/TI1=0083h` contêm somente `FFh` até
o próximo código conhecido. Forçar esses endereços como pontos de entrada
fazia o desassemblador exibir 37 bytes apagados como `MOV R7,A`. Eles agora
ficam como lacunas `ORG` preservadas por `FFh`. `CTF=009Bh` é entrada
adicional e já se encontra dentro do fluxo que começa em 0090h; sua
atividade real ainda depende da habilitação da interrupção.

## Conclusões com evidência direta

| Endereço | Alias | Evidência | Limite |
| --- | --- | --- | --- |
| 0000h | `reset_vector_to_0850` | `LJMP 0850h` no vetor de reset; boot observado no emulador | As etapas após o salto são analisadas na entrada 0850h |
| 0003h | `ext0_decrement_iram6b_skip_zero` | Vetor `IE0`; `DJNZ RAM[6Bh]` seguido de `INC RAM[6Bh]` quando o decremento chega a zero; termina em `RETI` | Não há prova de uso físico de `INT0` nesse caminho |
| 000Bh | `timer0_vector_to_0630` | Vetor `TF0`; `ORL TH0,#F8h`, `PUSH ACC`, `LJMP 0630h` | O serviço completo continua em 0630h |
| 001Bh | `timer1_vector_to_p5_toggle` | Vetor `TF1`; limpa `TR1` e faz `AJMP 0090h` | Destino físico de `P5.0/P5.1` ainda não confirmado |
| 0023h | `serial0_disable_es0_set_s0con70` | Vetor `RI0/TI0`; limpa `ES0`, grava `S0CON=70h` e retorna por `RETI` | Condições de habilitação e significado da configuração dependem do contexto |
| 002Bh | `timer2_vector_begin_service` | Vetor `TF2/EXF2`; limpa `EAL`, incrementa `RAM[56h]` e entra em lógica de estado que pode seguir até 0043h | Há desvio para 58BCh; o nome não atribui função física ao contador |
| 0043h | `clear_tf2_enable_eal_reti` | Vetor `IADC` e cauda também alcançada desde 0041h; limpa `TF2`, liga `EAL` e executa `RETI` | O vetor compartilha código com a cauda do serviço Timer 2 |
| 0053h | `iex3_vector_to_00b0` | Vetor `IEX3`; `LJMP 00B0h` | A rotina grande em 00B0h ainda exige revisão semântica integral |
| 0063h | `iex5_vector_to_05e4_bank0` | Vetor `IEX5`; empilha `PSW`, seleciona banco 0 e salta para 05E4h | O rótulo `WATER_TEMP_RAM` do IDA não decorre desses opcodes |
| 006Bh | `iex6_vector_p13_ccen_service` | Vetor `IEX6`; testa `RAM[2Eh].3` e `P1.3`, pode alterar `CCEN` e limpar `IEX6`; retorna com `EAL` ativo | O destino elétrico de `P1.3` ainda não está confirmado |
| 0090h | `timer1_p5_output_toggle` | Vetor TF1 em 001Bh salta para 0090h; alterna `P5.0` e `P5.1` com estado em `RAM[2Ah].3` | Destino elétrico desses pinos ainda desconhecido |
| 009Bh | `p5_output_1_toggle_branch` | Ramo de 0090h para `P5.1`; a rotina também pode limpar `P5.0/1` | O nome descreve o ramo, não a função física |
| 00B0h | `iex3_capture_sync_state_machine` | Vetor `IEX3` em 0053h salta para cá; o serviço usa o estado em RAM indireta C4h, captura do Timer 2, comparações de intervalo e controle de Timer 1/CCEN; PC observado em rastros de RPM | Os ramos internos de sincronismo e seus efeitos físicos ainda não foram mapeados integralmente |
| 035Dh | `shared_reti_at_035d` | `RETI` após a restauração de registradores também recebe `LCALL` em 0397h; o endereço de retorno empilhado permite continuar em 039Ah após liberar o nível ativo de interrupção | O IDA compacta o byte como `nullsub_1`; o efeito sobre prioridade deve ser considerado ao interpretar o restante do serviço |
| 045Bh | `derive_timer1_reload_32_33` | Multiplica por `22h` e `RAM[36h:37h]`, grava `RAM[32h:33h]`, depois usado em `TL1/TH1` em 0298h | Escala temporal e papel físico ainda não confirmados |
| 04E5h | `derive_timer1_reload_34_35` | Caminho análogo grava `RAM[34h:35h]`, usado em `TL1/TH1` em 0286h | Os bytes também são reutilizados no serviço de diagnóstico |
| 058Eh | `schedule_cc3_from_iram14_15` | Lê `RAM[14h:15h]`, programa `CCL3/CCH3`, comuta `P1.3` e habilita `CCEN.7` | Papel físico de `P1.3` não confirmado |
| 06E1h | `lookup_tf0_adc_pattern_by_r6_nibble` | `R6&0Fh` entra em `MOVC A,@A+PC`; o endereço base é 06E2h, de modo que índice zero lê o opcode `RET=22h`, e índices 1..15 leem a tabela 06E3h..06F1h | O IDA chama `DAh` de `DAPR`; no C517A é `ADDATL`, escrito para iniciar a conversão |
| 0721h | `route_adc_sample_to_iram_or_upper_a8` | Redireciona o alvo `63h` para RAM superior `A8h`; para `62h`, trata valores fora de `04h..F7h`; por fim grava via `@R1`. Teste dos opcodes originais confirma cinco canais | O valor em `RAM[63h]` é elaborado depois em 4756h; identidades físicas dos canais não foram demonstradas |
| 084Fh | `shared_reti_at_084f` | `RETI` após a restauração de registradores também recebe `LCALL` em 0823h; a execução continua em 0826h após liberar o nível ativo de interrupção | O IDA compacta o byte como `nullsub_2`; a rotina chamadora prossegue no serviço TF0 |
| 0850h | `reset_entry` | `LJMP 0850h` no vetor 0000h; execução observada em log local | Finalidade de cada etapa da inicialização ainda não auditada |
| 092Eh | `compare_xram_byte_with_rom_and_flag_mismatch` | Compara `MOVX @R0` com `MOVC @DPTR` e seta `RAM[2Eh].7` na divergência | Política posterior para a flag ainda não revisada |
| 0A0Ch | `compute_min_copy_count_for_xram_00_40` | Calcula em `R6` o menor entre `4Bh−40h` e `31h−00h`, resultando `0Bh`; `R5=31h`. Os dois chamadores copiam entre XRAM 00h e 40h | Cálculo constante confirmado por código; a entrada não foi observada no rastro atual |
| 0A23h | `compute_min_copy_count_for_xram_7f_40` | Calcula em `R6` o menor entre `4Bh−40h` e `FEh−7Fh`, também `0Bh`; `R5=7Fh`. Os chamadores copiam entre XRAM 7Fh e 40h | PC observado; o motivo dos limites de memória ainda depende da configuração da ECU |
| 0AA9h | `copy_rom_byte_at_dptr_to_xram_r0` | `MOVC` em `DPTR` seguido de `MOVX @R0`; chamado dez vezes na inicialização | Semântica dos bytes copiados depende dos chamadores |
| 0E5Fh | `store_calculated_value_in_rpm_byte` | Grava `A` em `RAM[47h]` e `RAM[6Ch]`, depois escreve valores derivados em XRAM com `P2=F9h` | O caminho de entrada que produz `A` ainda não foi executado no rastro atual |
| 185Fh | `set_2c2_217_then_multiply_iram5b` | Ativa `RAM[2Ch].2` e `RAM[21h].7`, depois cai em 1863h sem `RET`; duas chamadas no controle do motor | O IDA a separa como função apenas de flags; o papel físico dessas flags segue aberto |
| 1863h | `multiply_iram5b_by_32_to_r5r4` | Multiplica `RAM[5Bh]` por `20h` e devolve os bytes alto e baixo em `R5:R4`; duas chamadas diretas e entrada por 185Fh | A unidade de `RAM[5Bh]` depende dos chamadores |
| 1E02h | `scale_r3r2_by_rom_bc_stage_iram9fa0` | Fluxo de 1DDEh, 1DE7h ou fallthrough chama 561Ah, que aplica `ROM[DPTR+BCh]` a `R3:R2`; guarda `R5:R4` em RAM superior `9Fh:A0h` com `EAL` limpo; PC observado | O papel físico do par intermediário ainda não está estabelecido |
| 1ED3h | `publish_cc3_interval_from_r3r2` | Desabilita interrupções e grava `R3:R2` em `RAM[14h:15h]`; 058Eh lê o par, dobra-o e soma a `CCL3/CCH3` antes de ativar `CCEN.7`; o rastro registrou os valores nas entradas de 058Eh | O intervalo é confirmado no código e na execução; a ligação física de `CC3/P1.3` ao bico continua hipótese |
| 2FF4h | `classify_xram_r1_against_rom_thresholds_6a_6b` | Lê `XRAM[@R1]`; se `x≤ROM[DPTR+6Bh]`, ativa `F0` e retorna o limite em `A`. Caso contrário, limpa `F0` e retorna `min(x,ROM[DPTR+6Ah])`; teste dos opcodes originais confirmou as fronteiras | Dois chamadores; a grandeza comparada ainda não foi identificada fisicamente |
| 319Bh | `dispatch_xram_c8_state_1_to_8` | Chamador em 3195h passou `XRAM[C8h]` em `R2` quando `RAM[@8Ah].0=1`; a rotina distingue estados `01h..08h` e muda flags em `RAM[@8Ah/@8Bh]`, `XRAM[CAh]` e às vezes `P1.3`; `06h` e valores fora da faixa caem no `RET` sem trabalho de caso | O significado físico do estado permanece aberto; bytes 326Bh..3278h, semelhantes a instruções, não têm entrada confirmada e permanecem dados |
| 3B06h | `update_cc3_guard_from_xram_dd` | Lê `XRAM[XPAGE:DDh]`, compara com `AAh`, `55h` e `1Ah` e atualiza `RAM[2Bh].5`; o rastro confirmou `XPAGE=F8h` | Significado físico do valor e condição que libera a saída ainda não confirmados |
| 4095h | `gate_r4_r2_by_iram63_70_47` | Testa `63h<1Ah`, XRAM 88h=0, `70h≥2Fh`, `47h≥50h` e outras flags antes de ligar `R4.6/.7` e `R2.0`; teste dos opcodes originais cobriu fronteiras | Scanner chama `63h` de água e `70h` de ângulo de borboleta; unidade e finalidade final das flags seguem abertas |
| 41F3h | `snapshot_iram28_and_update_xram4f_5f` | `R6=XRAM[85h]&RAM[28h]` em 4081h..4085h; 41F3h..4207h guarda `RAM[28h]` em XRAM 85h, `R6` em 4Fh e atualiza 5Fh | A página XRAM e a persistência dos bits dependem do contexto |
| 4329h | `copy_fault_triplet_indexed_by_r3_r7` | Calcula `3×R3+R7` sobre a tabela 6E27h, lê três bytes com `MOVC` e grava XRAM CDh..CFh quando `T2I1=0` | Índices efetivos dependem dos bits de falha e do estado prévio de `R7` |
| 44BBh | `copy_fault_triplet_indexed_by_r6_r7_mark_bit7` | Calcula `3×R6+R7`, lê três bytes e liga `ACC.7` no terceiro antes da gravação condicionada em XRAM CDh..CFh | O byte gravado pode diferir do valor literal da ROM |
| 454Fh | `increment_upper_iram_a7` | `MOV R1,#A7h; MOV A,@R1; INC A; MOV @R1,A; RET` | Papel de `A7h` no sistema ainda não confirmado |
| 4A05h | `check_six_xram40_45_against_rom_bounds` | Com `DPTR=7300h`, `R1=05h` e `R2=06h`, chama 5887h para XRAM 40h..45h; os limites na ROM são 65h e 9Ch. Teste dos opcodes originais confirma carry em 64h/9Dh e ausência em 65h/9Ch | Os três primeiros valores fora da faixa saltam a 4A83h; os três seguintes a 4A8Bh. Ambos os ramos substituem o byte inválido por 80h nesta ROM; teste original confirma os dois. Página XRAM e grandeza física dependem do contexto |
| 4AB7h | `restart_control_loop` | Limpa EA, TCON e T2CON, depois salta para 0850h; o teste de `RAM[47h]=0` em 4AA2h chega aqui | Há outros caminhos que também levam a 4AB7h |
| 4AD1h | `kline_5baud_input_service` | Caminho amostra `P4.5`, usa contador `41h`; PC observado durante handshake PTY completo com endereço 10h, sincronismo 55h e identificação da ECU | O rastro confirma o percurso no emulador, não o circuito elétrico real |
| 4BCAh | `initialize_xram_ac_af_pattern_when_t2i1_clear` | Com `T2I1=0`, escreve `01 0A 00 14` em XRAM ACh..AFh; `4BD2h..4BDDh` também é alcançado por 4BB0h com `R1=ACh`; PC observado em três rastros de RPM | A página XRAM depende de `P2`; o IDA dá ao trecho compartilhado aparência de propriedade exclusiva da rotina |
| 4BDEh | `service_serial0_state_machine_from_xram` | Chamada pelo serviço TF0 em 083Ah; lê XRAM ACh e, com bit 2 ativo, copia B0h..B7h para RAM 3Eh..45h, amostra `RI0` em `F0` e despacha por `RAM[41h/42h]`; oito entradas observadas a 1.000 RPM tinham `P2=XPAGE=F8h` | O caminho elétrico da K-Line e os estados de recepção ainda exigem execução dirigida |
| 4C72h | `transmit_iram45_via_s0buf` | Após atraso, escreve IRAM 45h em `S0BUF` e liga `ES0`; teste de opcodes originais observa o primeiro byte `06h` | Saída elétrica e demais bytes do frame não verificados |
| 4C7Eh | `stop_serial0_and_store_session_status` | Programa `S0CON=40h`, limpa `ES0`, eleva `TXD`, guarda `B` em `RAM[3Eh]` e solicita cópia de um byte a XRAM ACh | A cópia XRAM é condicionada por `T2I1`; a rotina não apareceu no rastro atual |
| 4DC6h | `copy_rom_to_xram_after_r1_count_r4` | Copia `R4` bytes de `DPTR` para XRAM a partir de `R1+1`, incrementando `DPTR` e `R1`; duas chamadas diretas e um salto de cauda em 4D2Ah | Com `R4=0`, `DJNZ` faria 256 iterações; o salto de cauda depende do valor preparado pelo chamador |
| 4DFBh | `stage_fc_fault_triplet_response` | Após o despacho de `R2=07h` para estado `42h=09h`, usa `write_xram_b8_triplet` para montar `06,contador,FC` e copia XRAM CDh..CFh a BBh..BDh; 4C4Ch acrescenta `03h` | A cópia depende de `T2I1=0`; IRAM `89h.4=1` desvia antes da montagem |
| 4E2Eh | `stage_fe_memory_read_response_by_space_selector` | Para pedido `01h` e estado `42h=05h`, aceita comprimento de XRAM BBh entre 1 e 12, lê a partir do endereço baixo em BDh: seletor BCh=`00h` usa IRAM, qualquer valor não zero usa `MOVX` com a página atual de `P2/XPAGE`. Monta `comprimento+3,contador,FE,dados,03`; comprimento 0 ou ≥13 monta `04,contador,0A,contador anterior,03`. Teste original confirma seletores `00h/F8h/01h` e comprimentos 0/13 | O nome `addressHigh` do scanner não significa página XRAM escolhida por esse byte neste caminho; a página vem do estado anterior |
| 4E67h | `prepare_sensor_collection_f4` | Prepara dez itens e `R3=F4h`; `B3h.0` escolhe 6E8Ch, senão `B3h.1` escolhe 6E78h; teste com ambos ligados confirma prioridade de `B3h.0` | O pedido PTY `12h` usou 4ECBh, não esta entrada; condições de execução de 4E67h ainda pendentes |
| 4EAFh | `copy_selected_memory_to_xram` | Lê dez pares da ROM com `MOVC`: primeiro byte zero seleciona IRAM, valor não zero seleciona `MOVX`; segundo byte é endereço; teste dos opcodes originais confirma ambos os modos | Página XRAM depende de `P2/XPAGE`, não é escrita pela rotina |
| 4ECBh | `stage_f4_collection_from_b3_without_flag_update` | O pedido PTY `12h` visitou 4ECBh, 4EAFh e 4C72h e retornou `F4h` com dez bytes `51 60 28 65 80 00 00 07 83 00`, compatíveis com a tabela 6E78h; testes isolados também cobrem seleção da tabela 6E8Ch e payload zero | A identidade física de cada item e os outros estados de seleção seguem em análise |
| 4F5Bh | `write_xram_pair_r2_r3_at_r1` | Grava `R2` em `MOVX @R1`, incrementa `R1` e grava `R3`; cinco chamadas na máquina de estados K-Line | Página XRAM e significado dos dois bytes dependem do chamador |
| 4FA3h | `load_next_tx_byte_from_xram_r44` | Lê XRAM no ponteiro de IRAM 44h para IRAM 45h, avança o ponteiro e segue ao serviço serial; com 44h=B8h, o teste de opcodes originais observa `S0BUF=06h` | O ensaio entra nesse bloco com estado controlado, sem handshake completo |
| 5058h | `validate_kline_counter_terminator_and_dispatch` | No estado serial `06h`, exige `XRAM[B9h]−1=RAM[40h]` e `XRAM[RAM[44h]]=03h` antes de carregar o ID de XRAM BAh em `R2`. Teste dos opcodes originais confirma `11h→42h=0Ah`, `12h→42h=0Bh` e rejeição de contador ou terminador incorreto para `42h=04h` | Página XRAM e posição do terminador vêm do contexto da recepção; o ensaio inicia nesse bloco com estado preparado |
| 50E0h | `dispatch_kline_request_07_05_06_12` | Com ID em `R2`, `07h` escolhe `RAM[42h]=09h`, `05h` chama 515Bh e escolhe `03h`, `06h` encerra serial0, `12h` escolhe `0Bh`, e outros IDs nesse ramo escolhem `04h`. Teste dos opcodes originais confirmou `07h`, `05h`, `12h` e `13h`, inclusive a limpeza de bytes de falha por `05h` | Entrada interna após recepção do quadro; o ensaio não demonstra handshake completo nem transmissão da resposta |
| 5137h | `write_xram_b8_triplet` | Com `T2I1=0`, grava `A`, `++RAM[40h]` e `R3` em XRAM B8h..BAh; no frame FC esses valores são `06,contador,FC` | Papel de outros valores de `A` e `R3` depende dos chamadores |
| 5147h | `clear_xram_b0_cc_and_write_02_18_header` | Com `T2I1=1`, limpa 29 bytes de XRAM B0h..CCh e depois grava `02h` em B0h e `18h` em B1h; uma chamada em 4BADh | A página XRAM e o papel do cabeçalho ainda dependem do chamador |
| 515Bh | `clear_error_state_xram_on_command_05` | O ramo `R2=05h` em 50E8h chama esta entrada; o scanner local chama `05h` de `ECU_CLEAR_ERRORS_CODE`. Com `T2I1=0`, zera XRAM 4Eh..60h, 84h..86h e D0h..D1h, pode zerar 77h e o nibble baixo de 76h, e ativa `RAM[20h].6` | Página XRAM e associação completa dos bytes a falhas dependem do contexto; entrada ainda não observada em execução |
| 51B0h | `copy_iram_r1_to_xram_r0_when_t2i1_clear` | Lê `R5` bytes por `@R1` e escreve em `MOVX @R0` somente com `T2I1=0`, incrementando ambos os ponteiros | Página XRAM depende do estado de `P2` |
| 51BAh | `copy_xram_r0_to_iram_r1_count_r5` | Copia `R5` bytes por `MOVX @R0` para `@R1`, avançando ambos os ponteiros; PC observado no rastro | Página XRAM depende de `P2`/`XPAGE` |
| 51C1h | `update_serial_timeout_c8_and_event_ca` | Se `RAM[@8Ah].0=0`, zera esse byte e carry. Senão, preserva só o bit 0, decrementa ou recarrega `XRAM[C8h]`, marca `R7=1` ao expirar, retorna carry ligado e limpa `XRAM[CAh]` quando `T2I1=0` | Uma chamada no serviço K-Line; unidade temporal e sentido dos eventos ainda não confirmados |
| 51F1h | `clear_xram_c8_event_and_mask_iram8a` | Se XRAM C8h não é zero, limpa esse byte quando `T2I1=0` e preserva apenas bit 0 da RAM indireta 8Ah | Papel do byte de evento ainda não comprovado |
| 51FEh | `mask_upper_iram8a_to_bit0` | Mantém apenas o bit 0 da RAM indireta `@8Ah` e retorna; uma chamada direta em 51CCh e entrada por 51F1h | O IDA o separa como função; há também entrada por fallthrough e por desvio condicional |
| 5205h | `multiply_u16_r3r2_by_u16_r7r5_shift8` | Multiplica `R3:R2` por `R7:R5` sem sinal, descarta o byte baixo do produto e devolve os 24 bits restantes em `A:R2:R7`; teste de seis pares nos opcodes originais confirma carries e extremos | Cinco chamadas no controle do motor; unidade dos operandos depende de cada chamador |
| 5228h | `load_dptr_from_be_pointer_table_index_iram57` | Faz `RL` em `RAM[57h]` para escolher um par de bytes da ROM apontada por `DPTR`, lê byte alto e baixo com `MOVC` e atualiza `DPTR`; duas chamadas e PC observado | `RL` faz rotação de 8 bits; com índice ≥80h o bit 7 entra no bit 0, então não equivale a uma multiplicação comum por dois |
| 5238h | `load_dptr_from_be_codeword` | Dois `MOVC` consecutivos carregam byte alto e baixo em `DPH:DPL` | Uso da tabela apontada pelo novo `DPTR` depende do chamador |
| 5246h | `multiply_i8_a_by_u8_b_to_i16_ab` | Multiplica `A` com sinal por `B` sem sinal e retorna produto de 16 bits com byte alto em `A` e baixo em `B`; trata sinal por complemento de dois e foi executada no rastro | Os chamadores determinam a escala do produto |
| 5259h | `multiply_u16_r3r2_by_u8_a` | Dois `MUL AB` e propagação do carry calculam `A:R3:R2 = (R3:R2) × A_in` | Contexto físico dos operandos depende do chamador |
| 5279h | `find_table_segment_from_be_pointer` | Chama a leitura do ponteiro big-endian da ROM em 5238h e cai diretamente no corpo em 527Ch; doze chamadas e ambos os PCs observados no rastro | A grandeza medida depende do ponteiro de tabela fornecido pelo chamador |
| 527Ch | `find_cumulative_table_segment_and_fraction` | Lê endereço IRAM e contagem da tabela, soma incrementos da ROM para localizar segmento em `R3` e calcula fração de quatro bits no nibble alto de `A` | O IDA o separa como função, mas 5279h também entra por fallthrough; escala e sentido da tabela variam |
| 52CDh | `find_table_segment_index_from_be_pointer` | Resolve ponteiro big-endian da ROM, percorre os incrementos da tabela e devolve índice em `R3`, sem calcular fração | O valor físico da variável lida indiretamente da IRAM depende da tabela |
| 52F2h | `interpolate_cumulative_table_from_be_pointer` | Lê ponteiro e segmento como 5279h, guarda a fração em `R6`, calcula índice em `R5` e salta à interpolação de bytes adjacentes em 532Fh | A unidade e a curva específica dependem do ponteiro recebido |
| 5313h | `interpolate_rom_pair_from_packed_r5` | `MOV A,R5` cai diretamente em 5314h, que separa índice e fração e entra na interpolação compartilhada em 532Fh; chamada direta no controle do motor e PC observado em três rastros de RPM | O IDA encerra incorretamente a procedure em 5313h após o `MOV`, sem uma instrução `RET` |
| 5314h | `interpolate_rom_pair_from_packed_a` | Faz `SWAP`/`RR` em `A`, separa índice `R5` e fração `R6`, limpa `R4` e entra na interpolação em 532Fh | O formato da entrada foi identificado pelas operações de bits; a escala física depende da tabela |
| 5321h | `clear_r4_then_interpolate_indexed_code_table` | Zera `R4` e cai em 5323h; três chamadas diretas; PC observado no rastro de 1.000 RPM | O IDA a separa como função que apenas zera `R4`, mas não há `RET` antes de 5323h |
| 5323h | `interpolate_indexed_code_table_using_r4` | Seleciona um ponteiro big-endian da ROM por `RAM[57h]`, coloca `R5` em `A` e entra no interpolador compartilhado em 532Fh sem limpar `R4`; três chamadas diretas e PC observado | O significado físico da tabela depende de `DPTR` e do índice do chamador |
| 5329h | `interpolate_adjacent_code_table_bytes` | Lê dois bytes vizinhos por `R5`, multiplica a diferença por `R6` e retorna valor interpolado em `A` | Escala e significado da tabela variam por chamador |
| 532Bh | `interpolate_rom_table_from_be_pointer` | Resolve ponteiro big-endian e usa `R5/R6/R4` no interpolador compartilhado; `R4` pode habilitar segunda etapa em 5349h | Os chamadores controlam se a operação é unidimensional ou em duas etapas |
| 5367h | `compute_q8_ratio_a_over_r5` | Zera `R3/R4` e entra na divisão por restauração; execução dos opcodes originais no emulador confirmou `floor(256 × A_in/R5)` quando `A_in<R5` e `FFh` quando `A_in≥R5` nos seis casos testados | Divisor zero não foi caracterizado; entradas em 536Bh e 536Dh preservam convenções diferentes |
| 536Bh | `divide_u16_a_r3_by_r4_r5_eight_steps` | Define `R1=8` e cai no núcleo de divisão; quatro casos executados com os opcodes originais confirmaram `floor((A:R3)/(R4:R5))` em `A` | Resultado em excesso de oito bits e divisor zero ainda precisam de caracterização |
| 536Dh | `restoring_divide_with_r1_steps` | Núcleo de divisão por restauração com `R1` etapas; um caso com nove etapas devolveu 20 para 100/10, enquanto a entrada em 536Bh devolveu 10 | O chamador em 0E89h usa nove etapas; carry e registradores auxiliares de retorno ainda não foram especificados |
| 5387h | `clear_r4_then_update_xram24` | Zera `R4` e cai em 5389h; quatro chamadas diretas em 3F24h..4018h | O IDA a rotula como rotina que só zera `R4`; falta `RET` entre as duas entradas; ainda não observada no rastro |
| 5389h | `update_xram24_by_r4r3r2_and_flags` | Lê três bytes consecutivos de XRAM por `R1`, soma ou subtrai `R4:R3:R2` conforme `F0`, aplica limites por `OV`, sinal e `B`, marca saturação em `F1` e regrava os três bytes; uma chamada direta mais a entrada por 5387h | A faixa numérica e a unidade dependem de `B` e dos chamadores; `ET0` é religado na escrita; sem prova dinâmica atual |
| 5419h | `accumulate_signed_sample_and_check_thresholds` | Soma `A` ao acumulado em `R2`, limita overflow com sinal a `7Fh` ou `81h` e testa o total contra `R1/R3/R7`; seis chamadas em 1A9Dh..1AB5h e execução observada no rastro de 1.000 RPM | O significado físico dos limiares ainda depende dos chamadores |
| 545Dh | `set_flags_and_load_rom_offset14_to_iram5e` | Ativa `RAM[2Ch].1` e `RAM[25h].5/.6`, lê `ROM[DPTR+14h]` e grava `RAM[5Eh]`; sete chamadas e PC observado no rastro | O significado das três flags e do byte de tabela ainda não foi estabelecido |
| 5469h | `schedule_cc3_from_r2_r3` | Usa `R2:R3` em cálculo temporizado, programa `CCL3/CCH3` e comuta `P1.3` | Chamadores em 1B1Ch e 2036h ainda precisam de análise de entradas |
| 54CFh | `scale_a_by_rom_offset0f_shr4_saturate` | Multiplica `A` por `ROM[DPTR+0Fh]` e retorna `min(255, floor(produto/16))`; uma chamada em 2B5Eh | Fórmula deduzida dos opcodes, sem execução específica dessa entrada; unidade do produto desconhecida |
| 54E8h | `consume_up_to_five_xram3e_into_iram1f` | Com `RAM[20h].5=0`, subtrai de `XRAM[3Eh]` até cinco unidades e grava o valor consumido em `RAM[1Fh]` e `A`; com o bit ligado, preserva XRAM e devolve 5 se o byte era não zero, senão 0; PC observado | Papel físico e unidade desse contador ainda desconhecidos |
| 54FEh | `decrement_xram3e_unless_205_and_update_iram1f` | Se XRAM 3Eh não é zero, decrementa e grava o contador quando `RAM[20h].5=0`; grava `05h` em `RAM[1Fh]`; se zero, grava `00h` | Unidade do contador e papel físico desse estado ainda desconhecidos |
| 550Dh | `update_packed_xram_r0_state_from_r2` | Cinco chamadas em 2AB4h..2C07h com `R0=39h`; separa o byte em `XRAM[@R0]` em dois nibbles, compara `XRAM[35h]` com `R2`, atualiza o contador e as flags do estado, eventualmente regrava `XRAM[35h]` e o estado compactado; devolve o nibble baixo em `A` | PC observado no trace G de 15 milhões de ticks; papel físico do estado desconhecido |
| 5571h | `write_xram3e_and_set_r0_low_nibble` | Três chamadas em 2AC4h..2B1Ah com `R0=39h`; grava `A` em `XRAM[3Eh]` e força o nibble baixo de `XRAM[@R0]` a `Fh` | Conclusão estática; unidade de `XRAM[3Eh]` e papel físico do estado desconhecidos |
| 5579h | `adjust_xram_r1_using_rom_offset25` | Lê `ROM[DPTR+25h]` e `XRAM[@R1]`; se o byte XRAM tem bit 7 limpo, devolve-o; caso contrário, subtrai o byte da ROM e aceita a diferença apenas sem empréstimo e com bit 7 ainda ligado, devolvendo `80h` nos outros casos; chamadas em 255Eh e 257Ah | Conclusão estática; papel físico do limite desconhecido |
| 558Ah | `test_xram_range_55aa_r0_to_b` | Escreve e verifica `55h` e `AAh` entre `R0` e `B` exclusivo; marca `RAM[2Bh].1` em divergência e `F0` para intervalo inválido; PC observado na inicialização | O teste altera o conteúdo da faixa; a restauração depende do chamador |
| 55B9h | `copy_xram_r1_to_xram_r0_count_r6` | Copia `R6` bytes de `MOVX @R1` para `MOVX @R0`, incrementando ambos os ponteiros; retorna sem cópia se `R6=0`; seis chamadas na inicialização e execução observada no rastro | A página XRAM depende de `P2`/`XPAGE` no momento da chamada |
| 55C6h | `test_xram_block_55aa_count_r6` | Escreve e verifica `55h` e `AAh` em `R6` bytes desde `R0`; marca `RAM[2Bh].1` em divergência; PC observado na inicialização | A página XRAM depende do estado de `P2`/`XPAGE` |
| 55EBh | `subtract_r0_from_a_floor_zero_and_set_f0` | Devolve `max(A−R0,0)` e seta `F0` se houve underflow; quatro chamadas no ajuste das faixas de memória | O caminho sem underflow preserva o valor anterior de `F0` |
| 55F4h | `adjust_r2_by_bounded_rom_delta` | Com `F0=0`, soma `min(ROM[DPTR+A],B)` a `R2` saturando em `FFh`; com `F0=1`, subtrai `min(ROM[DPTR+R4],B)` com piso zero; duas chamadas no controle do motor | Fórmula deduzida dos opcodes, ainda sem execução observada dessa entrada; tabelas e unidades dependem dos chamadores |
| 561Ah | `scale_u16_r3r2_by_rom_offsetbc_round_q8` | Multiplica `R3:R2` por `ROM[DPTR+BCh]` e devolve em `R5:R4` o produto dividido por 256 com arredondamento ao meio para cima; teste executou os opcodes originais, inclusive com entradas máximas | PC observado em rastro; finalidade física do coeficiente ainda desconhecida |
| 5639h | `select_packed_table_indices_from_xram91_or_iram4e` | Escolhe `XRAM[91h]` quando alguma das flags `RAM[28h].3/.4/.5` ou `RAM[29h].3` está ativa e `XRAM[9Eh]` não é zero; senão lê `RAM[4Eh]`. Devolve nibble alto original em `R6` e nibble baixo em `R5`, somando quatro antes da máscara baixa só no caminho XRAM; três chamadas no controle de tabelas e PC observado | O IDA sugere K-Line no nome antigo, mas os chamadores estão no controle do motor; o significado físico do byte de origem segue aberto |
| 565Ah | `save_timer2_capture_triplet_to_iram_r1` | Nas duas chamadas de `IEX3`, com `R1=C3h`, grava `CRCL`, `CRCH` e `RAM[56h]` em RAM indireta C3h..C1h; incrementa o último byte se `TF2=1` e `CRCH.7=0`; PC observado | O ajuste de overflow foi identificado por código; a escala temporal completa depende do modelo do Timer 2 |
| 566Ch | `capture_timer2_elapsed_to_iram` | Subtrai captura anterior de `CRCL/CRCH` da atual, grava o intervalo de 16 bits em endereço IRAM escolhido pelo chamador e devolve em `A` a diferença do byte superior | O ajuste por `TF2` e sinal de `CRCH` exige validação temporal para interpretar a unidade do byte superior |
| 5693h | `compare_half_interval54_55_to_52_53` | Compara `(RAM[54h:55h] >> 1)` com `RAM[52h:53h]` por `RRC` e `SUBB`; carry indica que o primeiro valor é menor; executada em rastros de 750, 1.000 e 2.000 RPM | Uso exato do resultado na classificação de pulsos ainda requer análise dos ramos |
| 56A2h | `compare_half_interval52_53_to_54_55` | Faz a comparação inversa, dividindo `RAM[52h:53h]` por dois antes de subtrair `RAM[54h:55h]`; chamada duas vezes em `IEX3` | Não foi observada nos rastros atuais; sem prova dinâmica do ramo |
| 56B1h | `load_dptr_7200_via_jump` | Carrega `DPTR=F900h`, executa dois `NOP` e salta a 571Dh, que troca `DPTR` para `7200h` antes de retornar; ambas as entradas observadas em rastros de RPM | Os bytes intermediários parecem um bloco de cópia, mas a rota confirmada salta sobre ele |
| 5739h | `test_xram_range_55aa_preserve_with_fe_ff` | Chamada no reset em 0893h com `P2=F9h`, `R1=8Ch`, `B=8Dh`. Usa XRAM FEh como marcador e FFh para salvar bytes, testa FFh e a faixa `R1..B` com `55h/AAh` e restaura os bytes na rota de sucesso; mismatch registra máscara da página em RAM indireta 93h | A rota de falha pode deixar um teste incompleto; ainda não foi exercitada dinamicamente |
| 57B9h | `test_xram_r1_through_b_with_55_aa` | Exige `B>R1`, senão entra em `SJMP $`; testa `55h` e `AAh` por leitura após escrita de `R1` até `B`, incluindo ambos, e deixa zero em cada posição ao passar; falha salta a 57A3h para registrar máscara de erro de `XPAGE` na RAM indireta 93h | O teste modifica a XRAM; região e página efetivas dependem da inicialização do chamador |
| 5878h | `compare_xram_r0_to_rom_bound_reversed_subtraction` | Se `MOVX @R0` tem bit 7 ligado, calcula XRAM menos `ROM[DPTR+R1]`; caso contrário, calcula `ROM[DPTR+R2]` menos XRAM. O chamador testa carry após três chamadas; PC observado | A subtração segue sentidos opostos aos de 5887h; sensores e limites físicos ainda não identificados |
| 5887h | `compare_xram_r0_to_rom_bound_by_sign` | Se `MOVX @R0` tem bit 7 limpo, calcula XRAM menos `ROM[DPTR+R1]`; caso contrário, calcula `ROM[DPTR+R2]` menos XRAM; o chamador testa carry em seis chamadas sucessivas | O significado dos limites da tabela em 7300h ainda não foi identificado |
| 5896h | `xor_xram_r0_with_rom_dptr` | Lê `MOVX @R0` e `MOVC @DPTR`, devolve o XOR em `A` e preserva o byte XRAM em `R2`; nove chamadas consecutivas em 4A36h..4A78h | A política do teste de igualdade depende do chamador |
| 589Ch | `accumulate_rom32_to_iram3b3a_if_227` | Se `RAM[22h].7` está ativo, soma 32 bytes de ROM desde `DPTR` ao acumulador de 16 bits `RAM[3Bh:3Ah]`, avança `DPTR` e limpa a flag quando `DPH=80h`; em todos os caminhos salta para a guarda diagnóstica em 630Fh | Uma chamada em 62F1h; o estado inicial do acumulador vem do chamador e esse modo não apareceu no rastro |
| 6004h | `enter_diagnostic_mode_after_slow_baud_guard` | Chamada em 4B7Eh após receber `7Ch`; exige ainda `P4.6=0`, `RAM[17h]=0`, `RAM[16h]=74h` e `XRAM[EEh]≥09h`. Configura pilha, verifica IRAM/XRAM, prepara serial0 e Timer 2, e entra no laço em 62BEh | Nenhum rastro atual passou pela entrada; a sequência de handshake e os ramos posteriores ainda não foram validados dinamicamente |
| 60BAh | `prepare_diag_response_buffer_by_state` | Consome `RAM[21h].2`, despacha por `RAM[21h].0`, `R3` e outras flags, prepara `RAM[10h..31h]` com constantes ou bytes da ROM e termina pela guarda em 630Fh; três chamadas | Conclusão estática; o rastro atual não executou esta entrada nem demonstrou transmissão completa |
| 61D8h | `diag_timer2_serial_tx_rx_service` | No modo diagnóstico alternativo iniciado em 6004h, exige `TF2`; em 6237h transmite `@R0` por `S0BUF`; em 6253h recebe com `RI0`, incrementa `R4` e devolve o complemento do byte. Teste dos opcodes originais confirma o eco para `34h` e `12h`; este último ativa `RAM[21h].3` quando `R4` se torna `03h` | O protocolo completo desse modo e sua relação com o scanner K-Line principal não foram demonstrados |
| 630Fh | `diag_guard_marker57_sp_and_disable_ea` | Limpa `EAL`, exige `RAM[57h]=5Ah` e bit 7 de `SP` limpo; falha entra em `SJMP $` em 631Dh | Guarda observada por código; o rastro atual não percorreu esse modo |
| 6320h | `configure_timer2_d8ef_for_diag_mode` | Zera `T2CON` e `CCEN`, limpa `TF2`, carrega `D8EFh` em `TH2:TL2` e `CRCH:CRCL`, depois define `T2CON=11h`; uma chamada antes de preparar a resposta | Conclusão estática; tempo e modo efetivos dependem do modelo C517 do Timer 2 |
| 633Ah | `test_xram_pages_f8_to_fb_with_aa55` | Percorre as páginas `P2=F8h..FBh`, escrevendo e conferindo `AAh` e depois `55h` em 256 posições por página; marca `RAM[20h].1` em falha, atende watchdog e sai com `P2=FCh` | Autoteste destrutivo: após sucesso, as posições testadas contêm `55h`; não observado no rastro atual |
| 636Eh | `set_diag_state5_and_prepare_buffer` | Define `RAM[05h]=1`, ativa `RAM[21h].2`, chama 60BAh, depois limpa `RAM[04h]`, ativa `RAM[21h].1` e entra na guarda | Conclusão estática; motivo do valor 1 em `RAM[05h]` ainda aberto |
| 637Eh | `delay_a_loops_toggle_p57_and_feed_watchdog` | Usa `A` como contador externo, executa duas esperas de `R2=F7h` por iteração, alterna `P5.7` e aciona `WDT/SWDT`; três chamadas entre escritas em `S0BUF` | A espera foi identificada por código; duração elétrica e propósito de `P5.7` não validados |
| 6395h | `copy_rom_to_iram13_with_diag_guard` | Copia `RAM[31h]` bytes de `DPTR` para RAM indireta desde 13h, escreve `03h` após a cópia, define `RAM[12h]=F6h` e salta à guarda de 630Fh | Conteúdo copiado depende dos três chamadores do modo diagnóstico |
| 63A9h | `clear_diag_flag215_on_serial_timer_window` | Com `RI0=1`, `TI0=0`, `TH2≤FBh` e `TF2=0`, limpa `RAM[21h].5`; nos demais caminhos apenas entra na guarda | Duas chamadas no laço diagnóstico; significado da flag e janela temporal ainda pendentes |
| 63C4h | `periodic_session_counter` | Incrementa `36h` e testa `RI0` | Unidade temporal exata pendente |
| 6411h | `diagnostic_mirror_p1_p4_inputs_to_outputs` | Após serviços serial e guarda em 630Fh, espelha `P1.0` em `P1.1/P1.3/P1.7/T0` e `P4.7` em `P5.1/P5.3/P1.5/P5.4`, com complementos em outros bits | Aparece no laço de diagnóstico; destino elétrico desses pinos não demonstrado |
| 6441h | `adc_collect_eight_samples` | Oito iterações com leitura de `ADDAT` | Mapeamento físico dos canais pendente |
| 645Dh | `pack_port_bits_and_226_into_iram_r1` | Usa `RLC` para formar um byte com `P4.1`, `P4.3`, `P4.4`, `P4.5`, `INT0` e três cópias de `RAM[22h].6`; o segundo tem seis cópias dessa flag nos bits baixos e zeros nos dois altos. Grava via `@R1`, incrementa diretamente `RAM[01h]` e salta à guarda diagnóstica | O nome descreve apenas os bits lidos; associação a entradas físicas ainda não validada |

Os bytes testados em 4A05h participam também da inicialização: 55B9h copia
`R6` bytes de `MOVX @R1` para `MOVX @R0`. Os chamadores em 094Ah, 095Bh,
09B7h, 09CDh, 09ECh e 0A02h passam ponteiros que movem blocos entre os
endereços baixos XRAM 00h, 40h e 7Fh, conforme o ramo de partida. Essa
procedência mostra que a checagem de 4A05h age sobre um bloco de estado
copiado; não identifica por si só uma medição direta de sensor.

As doze chamadas de `5279h` usam ponteiros big-endian em `7002h`, `7044h`,
`7046h`, `7054h`, `7056h`, `7058h`, `708Eh`, `7090h`, `70A8h`, `70AAh`,
`70ACh` e `70C4h`. A primeira posição da tabela apontada contém o endereço
IRAM lido por `MOV A,@R0`; a segunda contém a contagem usada no laço. Os
cabeçalhos foram conferidos diretamente no dump original:

| Ponteiro ROM | Tabela ROM | IRAM de entrada | Contagem |
| ---: | ---: | ---: | ---: |
| 7002h | 73D4h | 63h | 0Ah |
| 7044h | 7569h | 6Fh | 05h |
| 7046h | 7570h | 47h | 0Fh |
| 7054h | 7824h | 70h | 05h |
| 7056h | 782Bh | 47h | 04h |
| 7058h | 7970h | 0Dh | 08h |
| 708Eh | 73C0h | 62h | 06h |
| 7090h | 7992h | 47h | 0Ah |
| 70A8h | 7B28h | AEh | 08h |
| 70AAh | 7B32h | 47h | 0Ah |
| 70ACh | 7B3Eh | 7Dh | 06h |
| 70C4h | 7F8Dh | 0Fh | 07h |

`RAM[47h]`, associada ao RPM no rastro, alimenta quatro dessas tabelas.
As demais entradas ainda não têm atribuição física confirmada. Em `135Ch`,
o ponteiro pode ser `7044h` ou `7046h`, conforme o ramo anterior.
As seis chamadas de `52F2h` usam ponteiros em `7068h→7952h` (`RAM[63h]`),
`706Ah→7958h`, `70D6h→79C4h` e `709Ah→79A8h` (`RAM[47h]`), além de
`706Ch→7960h` e `706Eh→7968h` (`RAM[7Dh]`). Os cabeçalhos apontados têm,
respectivamente, contagens `02h`, `03h`, `04h`, `03h`, `03h` e `03h`.
Essa associação é uma leitura direta dos bytes da ROM; ela ainda não
identifica o significado físico de cada curva.
Para `7068h→7952h`, a comparação G em `1282h` usa a curva como limite
contra `RAM[47h]`: trocar somente o retorno de `MOVC 532Fh/7956h`
de `10h` para `80h` inverteu o ramo em 33 passagens do ensaio. `RAM[63h]`
vem de ADC3 no perfil emulado; `ADC3` é um canal lógico, não uma
identificação do pino do encapsulamento ou do sensor na placa Fiat.
Na curva `705Eh→78F9h`, `3D28h` escreve o carry em `RAM[25h].3`.
Uma troca controlada do retorno `MOVC` alterou esse bit quando as
guardas `2Eh.6/28h.1` estavam limpas. `25h.3` é bit de RAM interna,
não `P2.5`, nem outro pino físico identificado.
As matrizes `7060h→78FDh` e `7062h→7911h` alimentam, respectivamente,
RAM superior `B1h` via `MOV @R1,A` em `3DAAh` e RAM baixa `58h` via
`MOV 58h,A` em `3DB1h`. São endereços internos do SAB80C517A,
não pinos. O código G lê `B1h` em `1893h/1915h` para testar o sinal;
uma intervenção na matriz alcançou o ramo `1897h`. `58h` pode ser
copiado para o contador `3Ch` em `18FDh/1906h`, ainda sem visita nos
três boots testados. A ligação a qualquer circuito externo está aberta.
A curva `706Ah→7958h` usa RAM `47h` como eixo de RPM e alimenta o
cálculo G em `15B2h..15CFh`, que pode alterar RAM `59h` em `1644h`.
Uma intervenção `MOVC` confirmou a mudança inicial de `59h=05h→01h`;
`59h` é RAM baixa, não um pino. A rota posterior até o agendador CC3
precisa ser separada de outras entradas antes de atribuir um atuador.
No ensaio G a 1.000 RPM, a mesma intervenção reduziu as três primeiras
larguras baixas do **pino modelado** `P1.3/CC3` de 5381/5380/5380 para
4373/4372/4372 ticks. Fornecer `59h=05h` e `5Ah=00h` somente às leituras
`MOV R3,59h`/`MOV R2,5Ah` em 1D5Ch/1D5Eh não restaurou essas larguras.
O assembly revela leituras anteriores: `MOV R7,59h` em 1C99h e
`MOV R5,5Ah` em 1C9Bh, seguidas da multiplicação em 1C9Dh. Fornecer
`05h/00h` **nessas duas leituras** restaurou exatamente as três primeiras
larguras nativas de CC3. Fornecer somente `59h=05h` produziu
5397/5396/5396 ticks; somente `5Ah=00h`, 4357/4356/4356 ticks.
Na primeira publicação em 1ED3h após a estabilização de `RAM63h`, o par
`R3:R2` foi `05:44` nativo, `04:48` com a curva doada, `05:48` com
apenas a leitura 59h restaurada, `04:44` com apenas 5Ah e `05:44` com
ambas. Isso estabelece mediação digital nas leituras de 1C99h/1C9Bh
para esse estado emulado. O latch, o pino do encapsulamento e o terminal
físico do bico continuam evidências distintas.
O contraste nos primeiros pulsos também apareceu a 750, 1.500 e
3.000 RPM com ADC fixo. A 3.000 RPM, o resgate antecipado restaurou
`5381/5381/5381` ticks frente a `4373/4373/4373` no braço doador;
o controle nativo com o mesmo fornecimento manteve os três valores.
Com `ADC1=40` a 1.000 RPM, o mesmo resgate antecipado restaurou
`6309/6308/6308` ticks frente a `5301/5300/5300` do braço doador.
`ADC1` aqui designa somente o canal estimulado no harness; esse teste
não identifica seu terminal no encapsulamento nem a carga de `P1.3`.
Os resgates também reproduziram os três primeiros pulsos nativos com
`ADC3=40` (`6405/6404/6404`) e `ADC6=180` (`6901/6900/6900`), usando
os pares estabilizados `RAM59h:5Ah=06:00` e `06:7C`. Os controles
nativos preservaram essas larguras. O fornecimento constante alcança
também a primeira leitura durante o boot, portanto a neutralidade
comprovada aqui se refere aos pulsos observados, não ao estado inteiro.

A faixa `5269h..5278h` permanece **ambígua** e está preservada como `DB`.
O assembly modular marca a faixa com um comentário `ambiguous DB`; o
`report.json` registra seu endereço e tamanho em `ambiguous_db_regions`.
Se tomada como ponto de entrada, decodifica uma sequência coerente de
instruções com dois `MUL AB` e `RET`; os mesmos 16 bytes aparecem em
`6972h..6981h` no dump Renault Clio MA1.7. Ambos os listings do IDA a
tratam como bytes. Não há chamada ou salto direto para `5269h` no índice
do Fiat, nem execução desse PC no rastro de 1.000 RPM. A semelhança sugere
uma rotina de biblioteca não utilizada ou alcançada indiretamente, mas não
prova código executável; esses 16 bytes continuam contados entre os dados.

A faixa `53DAh..5418h` também permanece como `DB`. O IDA a marcou como
suposta tabela de 63 bytes, mas a decodificação desde `53DAh` forma blocos
coerentes com `MUL AB`, desvios condicionais e `RET` em `53FFh`, `5403h`
e `5418h`. O índice atual não encontrou chamada ou salto direto para essa
faixa, e os rastros disponíveis não a visitaram. A forma dos bytes contesta
a descrição de tabela, sem demonstrar que essas entradas são alcançáveis;
a classificação binária e a finalidade da região seguem em aberto.
O índice contém três instruções `MOVC A,@A+PC` em toda a ROM, nenhuma a até
255 bytes antes do início de qualquer dessas duas faixas. Portanto, a leitura
direta por tabela relativa ao PC não oferece um caminho para elas. Esse teste
não exclui `DPTR` calculado nem alteração de endereço de retorno. Os 5.231
bytes omitidos no assembly bruto foram conferidos contra a ROM: todos são
`FFh`; já estas duas faixas não apagadas estão explicitamente representadas
por `DB` e são uma incerteza de interpretação, não de conteúdo binário.

Uma busca de sequências exatas no dump Clio MA1.7 de 64 KiB
(`cf0c841d924bfc740ffbe825d7b87d9df22cfa7f3bfcfa4eafe7765e03795412`)
encontrou um único correspondente para cada bloco abaixo. Os bytes
imediatamente anteriores também coincidem. Em especial, `5269h` e `53DAh`
estão deslocados pelo mesmo valor, `+1709h`, na ROM Clio. Isso sustenta a
origem compartilhada desses blocos, mas não prova que sejam chamados em
nenhuma das duas variantes; ambos os listings IDA os deixam como dados.

| Fiat | Clio | Tamanho | Interpretação atual |
| --- | --- | ---: | --- |
| 326Bh..3278h | 433Fh..434Ch | 14 B | Dados sem entrada confirmada |
| 5269h..5278h | 6972h..6981h | 16 B | Código possível, sem entrada confirmada |
| 53DAh..5418h | 6AE3h..6B21h | 63 B | Código possível, sem entrada confirmada |
| 56B9h..571Ch | CE08h..CE6Bh | 100 B | Bloco saltado por `LJMP` em ambas as variantes |

Os aliases são definições adicionais no mesmo endereço; os labels originais
continuam válidos. O arquivo TSV registra a evidência para cada alias.
`fault_bit_indexed_triplet_table` em 6E27h cobre 27 grupos de três bytes até
6E77h. O código em 430Eh..4324h escolhe um bit de XRAM 4Eh..50h; em
4329h..4340h calcula `3×R3+R7`, lê três bytes com `MOVC` e pode copiá-los
para XRAM CDh..CFh. O primeiro grupo é `FF FF 88`; o último, `03 03 03`.
O gerador modular apresenta cada grupo em uma linha `DB` com o endereço,
o valor `code_le16` e o terceiro byte anotados. Por exemplo, os bytes
`02 04 1E` em 6E2Dh representam o código numérico `0402h` e o status
`1Eh`, pois o scanner calcula `data[0] | (data[1] << 8)`; a escrita do
valor numérico não é a ordem dos bytes na ROM ou no pacote. Ele valida os bytes
explícitos da saída bruta antes de agrupar e remonta a ROM inteira; os
três `FFh` antes implícitos nessa faixa passam a ser editáveis.
Os ramos auditados atribuem `R7=0,3,6,9`, deslocamentos de triplas; o estado
também é recuperado de XRAM D1h em 42C1h e persistido em 45DBh. Na segunda
varredura, 44A4h..44A9h calcula `R6=R3−17h`; 44BBh..44D5h usa
`3×R6+R7` e força o bit 7 do terceiro byte com `SETB ACC.7` quando `R4=1`.
Assim, o status transmitido nesse caminho pode diferir do byte literal da
tabela. Ainda não há prova de que todas as 27 triplas sejam selecionáveis.

O teste de bits em 431Dh e 44AFh parte de `80h` e executa `RL A` tantas
vezes quanto o índice (`R3` ou `R6`), selecionando os bits 0..7 em ordem.
Os limites e a escolha de `R0` em 42EBh..430Ah e 4470h..4496h dão este mapa
estático dos dois bancos de falhas:

| Varredura | Índice | Byte XRAM | Bits testados | Tripla base na ROM |
| --- | --- | --- | --- | --- |
| Primeira | `R3=01h..08h` | `4Eh` | 0..7 | 1..8 |
| Primeira | `R3=09h..10h` | `4Fh` | 0..7 | 9..16 |
| Primeira | `R3=11h..17h` | `50h` | 0..6 | 17..23 |
| Segunda | `R3=18h..1Fh`, `R6=01h..08h` | `5Eh` | 0..7 | 1..8 |
| Segunda | `R3=20h..27h`, `R6=09h..10h` | `5Fh` | 0..7 | 9..16 |
| Segunda | `R3=28h..2Eh`, `R6=11h..17h` | `60h` | 0..6 | 17..23 |

A tripla 0 é `FF FF 88` e pode ser copiada pelo ramo 4433h..446Fh quando
`R3=0` e os bytes `5Eh..60h` estão zerados. Nas demais leituras, o índice
efetivo é a tripla base mais `R7/3`, chegando no máximo à tripla 26 com
os valores de `R7` atribuídos pelos ramos auditados. A ROM também recupera
`R7` de XRAM D1h; este mapa não prova que todo estado recuperado seja válido
nem que cada combinação de bit e deslocamento ocorra em operação real.
Um ensaio de quatro segundos com `python3 tools/trace_ma17.py --seconds 4
--inject-after 0.5 --crank-immediate --output-dir
build/ma17-analysis/kline-fault-probe` registrou a entrada K-Line em 4AD1h,
mas nenhum PC em 42BFh..45D4h. Esse ensaio inicial não alcançou o
diagnóstico; a sessão PTY posterior descrita abaixo alcançou. Um teste isolado em
`tests/test.cpp` carrega os 32.768 bytes da ROM original no núcleo, entra
diretamente em 4329h ou 44BBh com `R7=0/9` e observa XRAM CDh..CFh. Em
4329h, os índices 1, 2 e 9 produziram `02 04 1D`, `02 04 1E` e
`02 06 1F`; em 44BBh,
com `R6=2/9` e `DPTR=6E27h`, produziram `02 04 9E` e `02 06 9F`.
Isso confirma a leitura `MOVC`, o deslocamento de tripla e a ligação do bit
7 do status nessas entradas controladas. O mesmo teste continua em 4DFBh
sem reinicializar XRAM e confirma os cinco buffers `B8h..BEh`:
`06 01 FC 02 04 1D 03`, `06 01 FC 02 04 1E 03`, `06 01 FC 02 06 1F 03`,
`06 01 FC 02 04 9E 03` e `06 01 FC 02 06 9F 03`.
O byte `01h` é o contador `RAM[40h]` incrementado por 5137h. O ensaio
confirma o encadeamento das rotinas com estado inicial controlado; não prova
as condições naturais que levam a elas nem a transmissão na sessão K-Line.
Partindo em seguida de 4FA3h com `RAM[41h]=1`, `RAM[44h]=B8h` e `R0=3Fh`,
o teste lê `XRAM[B8h]=06h` para `RAM[45h]`, avança o ponteiro a `B9h` e
executa 4C72h..4C7Ch; `S0BUF` termina com `06h`. Isso confirma o primeiro
byte entregue ao registrador serial nos quatro casos isolados. Os bytes
seguintes, a temporização real e a saída elétrica permanecem não verificados.

Uma sessão PTY completa com a ROM G original, `MA17_P4_6_FORCE_LOW=1`,
`MA17_ADC_CH0=40`, `MA17_ADC_CH6=220`, `MA17_ADC_CH3=40`,
`MA17_ADC_CH5=40`, `MA17_ADC_CH7=63` e `MA17_CRANK_IMMEDIATE=1`
observou `29D5h` ligar `27h.0` no tick 1.187.188, `41E5h` publicar
`F84Eh=01h` no tick 1.384.046, e a execução alcançar `4329h` e `4DFBh`.
O cliente PTY recebeu o frame `FCh` com payload `02 04 1D` e terminou
com `DIAGNOSTICS PASS`. Reprodução: adicionar
`MA17_EXPECT_FAULT_TRIPLET=02041D` às variáveis acima e executar
`./run_full_test.sh`. Captura em
`build/ma17-analysis/pty/kline-idle-fault-bit0-40-220.txt`. O código
numérico é `0402h` em little endian; a interpretação física descrita
pelo scanner e a fiação de `P4.6` continuam hipóteses.

Com `R7=0`, os bits da primeira varredura apontam para estas triplas base.
Na segunda varredura, substitua XRAM `4Eh..50h` por `5Eh..60h` na mesma
posição de bit; nesse caminho, o código liga o bit 7 do terceiro byte antes
da gravação. Outros valores de `R7` deslocam o índice da tripla, portanto
esta tabela não identifica isoladamente o pacote que será transmitido.

| Bit XRAM | Tripla base | ROM | Código numérico LE16 | Status literal |
| --- | ---: | --- | --- | --- |
| `4Eh.0` | 1 | `6E2Ah` | `0402h` | `1Dh` |
| `4Eh.1` | 2 | `6E2Dh` | `0402h` | `1Eh` |
| `4Eh.2` | 3 | `6E30h` | `0402h` | `1Eh` |
| `4Eh.3` | 4 | `6E33h` | `1A01h` | `1Bh` |
| `4Eh.4` | 5 | `6E36h` | `3102h` | `0Ah` |
| `4Eh.5` | 6 | `6E39h` | `3102h` | `09h` |
| `4Eh.6` | 7 | `6E3Ch` | `1902h` | `0Bh` |
| `4Eh.7` | 8 | `6E3Fh` | `1902h` | `08h` |
| `4Fh.0` | 9 | `6E42h` | `0602h` | `1Bh` |
| `4Fh.1` | 10 | `6E45h` | `0602h` | `1Bh` |
| `4Fh.2` | 11 | `6E48h` | `0602h` | `1Ch` |
| `4Fh.3` | 12 | `6E4Bh` | `0602h` | `1Fh` |
| `4Fh.4` | 13 | `6E4Eh` | `0602h` | `1Dh` |
| `4Fh.5` | 14 | `6E51h` | `0602h` | `1Eh` |
| `4Fh.6` | 15 | `6E54h` | `0A02h` | `1Eh` |
| `4Fh.7` | 16 | `6E57h` | `0A02h` | `1Dh` |
| `50h.0` | 17 | `6E5Ah` | `0A02h` | `9Eh` |
| `50h.1` | 18 | `6E5Dh` | `0B02h` | `1Eh` |
| `50h.2` | 19 | `6E60h` | `0B02h` | `1Dh` |
| `50h.3` | 20 | `6E63h` | `0D02h` | `03h` |
| `50h.4` | 21 | `6E66h` | `0302h` | `03h` |
| `50h.5` | 22 | `6E69h` | `FFFFh` | `00h` |
| `50h.6` | 23 | `6E6Ch` | `0A02h` | `1Bh` |

### Origem dos bits associados ao atuador de lenta

Os códigos atribuídos pelo scanner ao atuador são `0402h` (interruptor)
e `1A01h` (motor/atuador, descrição incerta). Na ROM, os bytes de código
estão em ordem little endian: `02 04` em `6E2Ah/6E2Dh/6E30h` e
`01 1A` em `6E33h`. Com `R7=0`, esses quatro registros correspondem
aos bits 0..3 de `XRAM[F84Eh]`. Em `407Dh` o firmware mascara
`IRAM[27h]` com `XRAM[F884h]`; `41E5h` publica os bits ativos em
`XRAM[F84Eh]`. Portanto, a tabela sozinha não indica que uma falha
esteja ativa. O caminho até o pacote depende ainda do índice `R7`,
dos bits de habilitação e da varredura diagnóstica.

| Bit de `F84Eh` (`R7=0`) | Tripla ROM | Código | Ponto que arma `RAM[27h]` | Condição local comprovada pelos opcodes |
| --- | --- | --- | --- | --- |
| 0 | `6E2Ah`: `02 04 1D` | `0402h` | `29D5h` liga `27h.0` | `P4.6=0`, `24h.4=1`, `RAM[70h]>4Ah` e `MOVX F83Ch=0`, entre outras guardas de `29B6h..29D4h` |
| 1 | `6E2Dh`: `02 04 1E` | `0402h` | `2B42h` liga `27h.1` | Leitura `F839h`: `ACC.6=0` e `ACC.5=1` |
| 2 | `6E30h`: `02 04 1E` | `0402h` | `316Ch` liga `27h.2` | `RAM[24h].0=0` |
| 3 | `6E33h`: `01 1A 1B` | `1A01h` | `2B49h` ou `2C0Ch` liga `27h.3` | Em `2B49h`, adicionalmente `ACC.7=0`; em `2C0Ch`, contador `F83Bh=0` evita a limpeza imediata |

O comparador final do bit 0 (`29CBh..29D6h` em G/S88, deslocado
`+1Ch` em A/A+/S37/S36) foi executado nas seis ROMs originais:
`70h=4Ah` não passa, `70h=4Bh` passa somente com `F83Ch=00h`.
Nos boots G com P4.6 baixo, `RAM[70h]` estabilizou em `1Bh` para
TPS 40/95 e `37h` para TPS 120/180; `29D0h` foi atingido, mas
`29D2h` não. O teste `IdleFaultBitZeroRequiresThrottleThresholdAndZeroXramInSixRoms`
confirma as duas guardas finais, sem simular o circuito do interruptor.
Com ADC0/6=40/220, as duas execuções G chegaram a `6Fh=1Bh` em
`11B6h` e `70h=53h` em `11C0h`, o ramo alternativo que soma `38h`.
O controle com P4.6 alto seguiu `29F5h` e publicou `F84Eh=04h`;
com a leitura experimental de P4.6 baixa, `29D5h` ligou `27h.0`
no tick 1.187.188 e `41E5h` publicou `F84Eh=01h` no tick 1.384.046.
Esse contraste isola o caminho digital no harness; não valida a
plausibilidade elétrica de ADC6=220 nem a ligação física de P4.6.
Teste `test_tps_derived_bit_zero_fault_needs_experimental_low_p46`;
capturas `idle_fault_bit0_tps_40_220*/`.

Os três registros `0402h` têm bytes de estado diferentes ou origens
internas diferentes; o texto do scanner não identifica qual circuito
produz cada bit. `41CDh` espelha `27h` em `F884h`; a publicação em
`F84Eh` ocorre depois da máscara e das guardas em `41CFh..41E5h`.

Na inicialização, `0CB7h` lê `XRAM[F847h]`: `0CBAh` copia o bit 0 em
`27h.1`, e `0CBEh` copia o bit 1 em `27h.3`. No ramo observado,
`0C85h` inicializa antes `F847h=80h`; essa cópia não prova retenção
de falhas entre partidas. Em `2D21h..2D56h`,
o firmware copia esses dois bits de volta para `F847h[0..1]`, junto
com outros estados. Em `0CD2h`, ele atribui `27h.0` e pode ligá-lo
em `29D5h` quando `XRAM[3Ch]` é zero sob guardas anteriores; `27h.1`
liga em `2B42h` após testar `XRAM[@R0]` com `ACC.6=0` e `ACC.5=1`;
`27h.3` liga em `2B49h` quando, além disso, `ACC.7=0`, ou em `2C0Ch`
por outro ramo com temporizador. `27h.2` liga em `316Ch` quando
`24h.0=0`. Os bits são limpos por caminhos próprios, inclusive
`2D16h` para 0/1/3 e `315Bh` para 2. Esses PCs e condições são
relações digitais; ainda não identificam o pino do interruptor ou os
terminais da ponte H.

O trace da ROM G com 1.000 RPM, ADC3/5/7=40/40/63 e TPS
ADC0/6=40/95 mostrou `27h.2` ligado em `316Ch` no tick 10.078,
publicado como `F84Eh=04h` em `41E5h` no tick 157.419. Depois,
`2B42h` e `2B49h` ligaram 1 e 3 nos ticks 1.238.640/1.238.643;
`41E5h` publicou `F84Eh=0Eh` no tick 1.386.856. Com TPS
20/70 ocorreu a mesma sequência; com TPS 120/180 somente o bit 2
foi publicado nos 2,4 milhões de ticks observados. A diferença
depende do estímulo TPS nesse modelo, mas não comprova a interpretação
elétrica dos códigos nem que um pacote de erro foi transmitido.
Reproduzir: `MA17_TRACE_IDLE_FAULT=1` com `tools/trace_ma17.py`;
capturas em `build/ma17-analysis/variants/idle_fault_tps_*/`.

O ramo específico em `2B38h` lê `XRAM[F839h]`; com TPS 40/95, esse
byte chega a `2Eh` no tick 1.238.627. A subrotina `550Dh..556Fh`
combina um nibble de estado e um contador no mesmo byte: `55A1h`
é apenas autoteste, `0CA7h` inicializa `F839h=0Fh`, `555Bh` reduz
o contador e `5577h` recarrega o nibble baixo. Assim, `2Eh` não deve
ser interpretado diretamente como leitura do interruptor físico.
No ramo `2B39h..2B49h`, bit 6 ligado desvia antes das falhas; bit 5
ligado com bit 6 desligado liga `27h.1`; bit 7 desligado liga também
`27h.3`. Com TPS 120/180, `F839h` ficou em `0Fh` e `2B38h` não foi
alcançado nos mesmos 2,4 milhões de ticks.

Contrafactuais G forneceram outro valor somente ao `MOVX` de
`2B38h/F839h`, mantendo o byte armazenado em `2Eh` e o SHA-256 da ROM:
`0Eh` (bit 5 limpo) e `6Eh` (bit 6 ligado) mantiveram `F84Eh=04h`;
`AEh` (bits 5/7 ligados, 6 desligado) produziu `F84Eh=06h`, sem o
bit 3. O controle original publicou `0Eh`. Isso demonstra os três
testes de bit no caminho emulado, sem ainda identificar o circuito
elétrico ou validar a descrição física de `0402h/1A01h` do scanner.
Capturas em `idle_fault_xram_tps_*/` e `idle_fault_override_*/`.

Forçar experimentalmente a leitura de `P4.6` em zero, com a trava de
saída preservada, manteve `F839h=0Fh` após a inicialização e impediu
`2B38h` nos 2,4 milhões de ticks observados. Nesse caso, `2C0Ch`
ligou `27h.3` transitoriamente. O contador `F83Bh` começou em `32h`
por `0CAFh` e foi decrementado em `2C1Bh`: enquanto não zerou,
`2C19h` limpou o bit novamente. Após `01h→00h` no tick 664.994,
o bit permaneceu ligado na passagem seguinte (`2C0Ch`, tick 675.388);
`2D56h` salvou `F847h=C6h` e `41E5h` publicou `F84Eh=08h` perto
do tick 873 mil, tanto com TPS 40/95 quanto 120/180. P4.6 também
afeta outras rotas e pode exercer a função CM6 do C517A. O teste
`test_experimental_p46_low_changes_idle_fault_source_path` protege
o contraste digital; a conexão elétrica do interruptor continua aberta.
O ramo temporizado tem os mesmos opcodes nas seis ROMs: `2C0Ch` em
G/S88 corresponde a `2C28h` em A/A+/S37/S36. A inicialização
`0CABh..0CAFh` do contador `F83Bh=32h` também é idêntica.

O scanner local identifica a requisição `07h` e a resposta `FCh` como
operações de leitura de erros. Seu `errorPacketToString` interpreta os dois
primeiros bytes dos dados como código little-endian e o terceiro como status.
Com essa ordem, 25 das 27 triplas têm código presente em
`ECUMonomotronic.cpp::kErrorDescriptions`; as exceções são as duas triplas
`02 19 0B` e `02 19 08` (código `1902h`, ausente da lista). O log histórico
`pythonpty.log` registra quatro respostas `FCh` com dados `02 04 1E`,
`02 06 1F`, `02 0A 1D` e `02 0B 1D`, idênticos às triplas em 6E2Dh,
6E4Bh, 6E57h e 6E60h. O log não contém hash do firmware ou versão do
emulador, então essa correspondência é evidência histórica de execução,
não uma reprodução atual. O scanner marca como `present` apenas status
`1Eh` ou `03h`; os pacotes históricos com `1Dh` e `1Fh` resultariam em
`present=false` nessa implementação. O significado físico de cada status
e a cobertura dos demais códigos ainda precisam de confirmação.

O parser do scanner lê o quadro na ordem tamanho, contador, ID, dados e
terminador `03h`. No buffer do firmware, B8h, B9h e BAh guardam os três
primeiros campos. O ramo 5058h compara `B9h−1` com `RAM[40h]`, testa o
terminador no ponteiro `RAM[44h]` e só então carrega o ID de BAh em `R2`.
O teste isolado confirma a aceitação de `11h`/`12h` e a rejeição de contador
ou terminador inválido; a recepção byte a byte ainda não foi reproduzida.

As duas tabelas de dez pares em 6E78h..6E9Fh coincidem byte a byte com
`kCollectionTable1` e `kCollectionTable2` em
`src/ECUSerial/KlineCollectionTables.h` do scanner local. Cada par na ROM
está armazenado como `(seletor, endereço)`; o scanner declara `(ID,
subcomando)`, com os mesmos bytes em ordem inversa. Em 4EAFh, `00h`
seleciona leitura de IRAM e `F8h`, por ser não zero, seleciona `MOVX @R0`.
Esse byte não é escrito em `P2` ou `XPAGE` pela rotina: a página XRAM vem
do contexto do chamador. O código em 4E92h e 4EE5h carrega `DPTR=6E78h`,
fornecendo referências diretas à primeira tabela. Em 4E67h, `B3h.0` tem
prioridade e seleciona a segunda tabela; se estiver limpo, `B3h.1`
seleciona a primeira. O bloco 4ECBh..4EF5h usa a mesma ordem de testes.
Um teste com a ROM original, `P2/XPAGE=F8h` e valores distintos em IRAM e
XRAM executou 4EAFh para ambas as tabelas e confirmou os dez bytes copiados
em XRAM F8BBh..F8C4h. Continuando por 4ECBh, confirmou `0D 01 F4` em
F8B8h..F8BAh, os dez valores selecionados em F8BBh..F8C4h e `03h` em
F8C5h para as duas tabelas. Com o ponteiro de envio em B8h, 4FA3h/4C72h
escreveu o primeiro byte `0Dh` em `S0BUF`. O mesmo teste executou 4E67h
com `B3h=01h`, `02h`
e `03h`, confirmando seleção 6E8Ch, 6E78h e 6E8Ch, respectivamente. O
ensaio repetido em 4ECBh confirmou a mesma prioridade sem alterar `B3h`.
Com pedido `12h`, o teste passou de `42h=0Bh` pelo despacho em 4C06h até
4ECBh e observou `0D 01 F4`, dez zeros e o terminador `03h` quando
`B3h=00h`. Os nomes físicos dos sensores no scanner não foram validados
por esses testes.
O gerador modular agora apresenta cada par em uma linha `DB` com endereço,
modo `IRAM`/`MOVX` e seletor. Antes de agrupar, ele confere todos os 40
bytes explícitos das duas tabelas contra a ROM; um teste rejeita fonte com
byte ausente. Os labels e os endereços das tabelas permanecem iguais.

Na tabela 6E78h, estes são os dez campos em ordem de transmissão. Os pares
`seletor:endereço` vêm dos bytes da ROM; os valores vêm de uma coleta PTY.
As descrições físicas são as hipóteses atuais de `KlineCollectionTables.h`
do scanner, não identificações demonstradas pela igualdade dos bytes:

| Posição | Fonte ROM | Valor observado | Descrição no scanner |
| ---: | --- | --- | --- |
| 0 | IRAM 63h | 51h | Temperatura da água |
| 1 | IRAM 66h | 60h | Trilha 1 do TPS |
| 2 | IRAM 47h | 28h | RPM |
| 3 | IRAM 62h | 65h | Temperatura do ar |
| 4 | MOVX 0Ch, página corrente | 80h | Estado interno; scanner chama de "integrador lambda" (não confirmado) |
| 5 | MOVX 6Ch, página corrente | 00h | Correção de combustível de longo prazo |
| 6 | MOVX 6Fh, página corrente | 00h | Aditivo de combustível de marcha lenta |
| 7 | MOVX 3Dh, página corrente | 07h | Posição do atuador de marcha lenta |
| 8 | IRAM 61h | 83h | Tensão de bateria |
| 9 | MOVX 69h, página corrente | 00h | Adaptação de purga EVAP |

### Registro de pinos candidatos (ROM Fiat G)

Os nomes abaixo são **pinos do SAB80C517 ou latches de porta**, não
terminais identificados no conector da ECU. Os PCs são da ROM Fiat G;
as revisões Renault não herdam automaticamente esse mapa. Uma escrita no
latch também não prova o nível elétrico quando a função alternativa do
pino está habilitada.

A curva `70D6h→79C4h` escreve em `F8:E1h` no ensaio G. `P2=F8h` nesse
acesso `MOVX @R0,A` seleciona a página de XRAM; `F8:E1h` é endereço de
memória, não um novo pino ou saída física identificada. O código lê o byte
em `35D1h` antes de ajustar `R2`; seu destino posterior ainda é aberto.

| Pino | Origem no firmware ou no modelo | Observação e hipótese | Pendente |
| --- | --- | --- | --- |
| `P2/XPAGE` | `MOVX @R0,A` em `35C2h` acessa `F8:E1h` no trace G; `35E0h` depois escreve `P2=F9h` | O manual SAB80C517 descreve a página de `MOVX @Ri` via `P2/XPAGE`; aqui `F8h` é parte do endereço de XRAM, não identificação de saída de atuador | Confirmar a multiplexação elétrica de P2/XPAGE na placa antes de inferir níveis nos terminais |
| `P4.5` | Leitura de `P4` pelo caminho serial; `PortController` injeta o nível do transceptor K-Line | O modelo inverte o nível da linha K; é uma associação do harness, não uma medição na placa Fiat | Confirmar trilha e transceptor da ECU |
| `P4.3/CM3` | `2374h` e `4991h` testam o bit; G/S88 `49ADh..49C8h` e família A `4A70h..4A8Bh` copiam seu nível para bit 2 de `XRAM[F8E2h]` | No boot G com TPS 40/95, nível baixo mudou `F8E2h` de `57h/77h` para `53h/73h`, sem mudar os resumos modelados de CC3 e saídas. `7375h..7377h=09 03 05` bloqueia o efeito do pino em `2374h` para `RAM57h=0/1/2`; o manual permite CM3 | Identificar modo e ligação elétrica; não atribuir ainda o contato de lenta |
| `P4.6/CM6` | `2D57h/2D60h` leem o bit para `24h.4/2Fh.0`; `481Ah` usa `2Fh.0` para escolher a curva de `RAM[4Fh]` | Forçar entrada baixa no emulador muda a curva e o cálculo de CC3; o manual permite função alternativa CM6 | Determinar origem elétrica e modo CM6 na placa |
| `P4.7/CM7` | `21D4h` e `2206h` amostram o bit; `48ECh/4951h` o usam em limites de curva | Entrada candidata a uma condição operacional; a associação ao pedido de A/C é hipótese | Rastrear circuito e estados em que `22h.5` libera a rota |
| `P5.3` | `220Fh` escreve o complemento da condição calculada em `22h.4` | Com TPS `40/95`, o latch fica alto nas 230 passagens iniciais; após `A6h` zerar, fornecer `0Eh` à leitura `F8:39h` gera 439 amostras baixas. Com TPS `100/155` e `ADC3=20`, a ROM G alcança 439 amostras baixas sem essa intervenção. São níveis do latch modelado, sem identificação do atuador | Medir nível físico e correlacionar com embreagem do A/C |
| `P5.0/P5.1` | Vetor TF1 `001Bh→0090h`; escritas em `0090h..00AFh` e `0252h..027Bh` | Pulsos alternados a cada meia volta, compatíveis com os dois canais wasted spark | Identificar drivers, polaridade e ligação aos primários |
| `P1.7/T2` | O manual SAB80C517 o define como entrada externa ou de habilitação do Timer 2 quando `T2I1=1`; o código classificado das seis ROMs inicia `T2CON=85h` e não contém escrita que ligue `T2I1` | A busca nos bytes das seis ROMs não encontrou `CLR/SETB/CPL/MOV bit,C` para `T2I1` (`C9h`). O aparente `JBC C9h` em `5690h` (G/S88) ou `5753h` (A/A+/S37/S36) atravessa `POP 10h; XCH A,R1`. As curvas guardadas por `T2I1=1` foram selecionadas apenas em execução isolada; não há sinal de `P1.7` medido na ECU | Verificar código ainda não classificado, outras formas de escrever `T2CON` e conexão do terminal físico antes de atribuir função |
| `P1.3/CC3` | `058Eh..05DBh` programa `CCL3/CCH3` e comuta o latch; comparação Timer 2 modelada | Pulso separado de P5.0/1. No degrau TPS G a 3.000 RPM, doar `7520h=6Fh` mudou o pulso iniciado no tick 907.122 de 8.156 para 9.488 ticks; zerar `78h` em `1D4Bh` removeu essa diferença. A curva `7958h` alterou três pulsos iniciais a 1.000 RPM; fornecer os valores nativos de RAM 59h/5Ah nas leituras em 1C99h/1C9Bh restaurou os três. Candidato à temporização de outro atuador, possivelmente bico | Confirmar estágio de potência e terminal físico do injetor |
| `P1.1` | `0352h` liga e `0433h` desliga o latch | Período de meia volta no perfil testado; função física indeterminada | Medir sinal elétrico e rastrear consumidores |

No cenário físico Fiat com parada por carga, `P5.4` mudou em
`317Ah` (alto, 572.953 ticks) e `3176h` (baixo, 35.686.123 ticks).
Sua guarda lê `RAM[2Dh].0` e `XRAM[F881h]`; a queda ocorreu cerca de
25 s após zerar a RPM. A sequência baixo sem partida → alto em marcha
→ baixo tardiamente após parar é compatível com uma lâmpada de aviso,
mas a ligação ao terminal 31 da ECU não foi demonstrada. `P1.7`
mudou 15 vezes no mesmo ensaio, em `06CAh`, acompanhando `RAM[1Dh]`
e `T2CON.1`; a cadência não identifica relé, bomba ou outra carga.
Ambos permanecem sinais brutos sem binding ao terminal 28.

**Luz de avaria (observação do veículo):** o terminal 31 do conector é
identificado como luz de avaria na tabela de aplicação. Segundo a observação
do proprietário, ela acende com a ignição ligada antes da partida e também
em algumas condições com DTC presente. Sequência proposta para observar no
veículo:

| Estado | Comportamento a observar |
| --- | --- |
| Ignição desligada | Lâmpada apagada |
| Ignição ligada, motor parado | Lâmpada acesa |
| Motor de partida acionado | Registrar se e quando ocorre transição |
| Motor funcionando | Lâmpada apaga após as condições previstas pela ECU, sem prazo ainda medido |

Esta sequência orienta a simulação do painel, mas ainda falta medir a
polaridade do comando e confirmar qual pino da CPU chega ao terminal 31.
A transição de `P5.4` acima é uma pista, não prova do circuito da lâmpada.
Também não está estabelecido se um DTC apenas histórico, sem falha presente,
mantém a luz acesa.

**Pista estática na ROM Fiat G:** o reset em `0C25h` arma `2Dh.0` e zera
`F8:81h`. No Timer 0, `316Eh–317Ah` põe `P5.4` baixo somente quando
`2Dh.0=1` e `F8:81h=0`; em qualquer outro caso põe o latch alto.
Em `4140h–4167h`, o código só limpa `2Dh.0` depois de verificar
`RAM28h[4:0]`, `RAM29h[6:0]`, `RAM2Bh.0` e algumas condições de
temporização. Em `419Ah`, outra rota rearma `2Dh.0` e grava `F5h`
em `F8:81h`; `314Eh` decrementa esse byte quando `T2CON.1=0` e
`2Dh.5=1`. Isso combina com lâmpada ativa em nível baixo, autoteste
antes da partida e eventual atraso para acender após falha. A função
dos indicadores internos e a escala de tempo do contador ainda exigem
validação; não se pode concluir que todo DTC acenda a lâmpada.

O byte `ROM[5720h+R3]` controla essa seleção: no laço `4172h–41C5h`,
`R3=1..8` examina falhas qualificadas de `RAM27h`, `9..16` de `RAM28h`
e `17..23` de `RAM29h`. Somente uma posição ativa cujo byte da tabela
tenha o bit 2 ligado pode rearmar `2Dh.0` em `419Ah`. O cruzamento com
as triplas de diagnóstico acima resulta em:

| Bits examinados | Bit 2 da tabela | Códigos base na tabela `6E27h` |
| --- | --- | --- |
| `27h.0..5` | 0 | `0402h`, `1A01h`, `3102h` |
| `27h.6..7` | 1 | `1902h` |
| `28h.0..4` | 1 | `0602h` |
| `28h.5..7` | 0 | `0602h`, `0A02h` |
| `29h.0..6` | 1 | `0A02h`, `0B02h`, `0D02h`, `0302h`, `FFFFh` |

O laço aplica ainda máscaras de habilitação (`F8:84h..86h`) e guardas
especiais antes de usar esses bits. Os códigos acima são entradas base,
não prova de que cada DTC seja alcançável ou acenda a lâmpada. Em
`4140h–4167h`, a limpeza examina falhas correntes em `RAM27h/28h/29h`
e `2Bh.0`; os bancos históricos `F8:5Eh..60h` não aparecem nessa
decisão direta.

Contraste com a ROM original no motor físico condicional, 40 milhões de
ticks: sem falha, `P5.4` subiu no tick 572.953 e ficou alto; TPS1
elevado desde 10 milhões publicou `F84Eh=08h` até o fim, mas não fez
`P5.4` cair; ECT aberto desde 10 milhões publicou `RAM28h/F84Fh=08h`
e fez `P5.4` cair no tick 35.276.447. Em outro ensaio, ECT voltou no
tick 40 milhões; `P5.4` subiu no tick 40.099.515, enquanto o banco
histórico `F85Fh=08h` persistiu até 54,45 milhões. Isso sustenta a
seleção por tipo de falha corrente e um atraso na ativação, sem medir a
polaridade elétrica da lâmpada nem estabelecer prazo universal.

O modelo de hardware expõe `Ma17DiagnosticLamp::lamp_on()` e o campo
`lamp_on_candidate` na telemetria `diagnostic`. Ambos amostram `P5.4`
como comando ativo em nível baixo; representam a hipótese observacional,
não uma medição de tensão no terminal 31. Antes da primeira amostra da
CPU, o getter retorna falso, pois a alimentação desligada ainda não é
simulada como estado independente.

### Alimentação permanente, chave e início da CPU

O mapa de aplicação atribui o terminal 16 da ECU à linha 30 (bateria)
e o 17 à linha 15 (chave); a continuidade nesta placa ainda não foi
medida. A ROM preserva indícios de estado entre inicializações: em
`088Fh..08C7h`, testa a escrita em `XRAM F8:FFh` e classifica o valor
anterior (`01h`, `80h`, `FFh`, zero ou outro); em `08CFh..0929h`,
compara outros bytes de XRAM com constantes da EPROM. Isso é compatível
com RAM mantida pela linha 30, mas não identifica qual circuito recebe
essa alimentação, nem prova que o núcleo da CPU permaneça energizado.

A observação do proprietário é que alguns segundos sem a bateria apagam
as adaptações. No [datasheet oficial do SAB80C515A](https://www.infineon.com/assets/row/public/documents/10/57/infineon-d80515a-ds-v08-95-en.pdf),
a XRAM interna `F800h..FBFFh` preserva conteúdo em reset e em *hardware
power down* enquanto VCC continuar presente, mas seu estado após remover
a alimentação é indefinido. O mesmo documento atribui ao PLCC-68:

| Terminal da CPU candidata | Função no 80C515A | Uso a verificar nesta ECU |
| ---: | --- | --- |
| 37 / 38 | VCC / VSS | Alimentação lógica contínua e massa |
| 68 | `/HWPD`, ativo em baixo | Possível comando de repouso pela linha 15; **no 80C515 anterior é VCC** |
| 10 | `/RESET`, ativo em baixo | Circuito de reset, separado de `/HWPD` |
| 4 | `PE/SWD` | Habilita modos de economia por software; não comanda `/HWPD` |
| 66 / 67 | `P5.1 / P5.0` | Saídas candidatas das duas bobinas |

No 80C515A, `/HWPD=0` para a CPU e os osciladores e inicia um reset
interno; `/HWPD=1` reativa osciladores e reinicia o programa. A XRAM
permanece se VCC não cair. Essa é uma explicação de arquitetura coerente
com a observação, **não** uma identificação elétrica do B58371 nem da
trilha da chave. Prioridade de bancada: confirmar 37/38 pelos planos de
alimentação, depois seguir 68 e 10 até o circuito de entrada; comparar
o estado dessas redes com chave desligada/ligada sem presumir que 68
aceite tensão de bateria. A distinção 515A/515 torna 68 especialmente
sensível a uma identificação errada.

O harness atual chama `reset(&cpu, true)` uma vez na partida e não modela
linha 15, desligamento, retenção seletiva de RAM ou saída de standby.
Para simular uma futura transição da chave sob a hipótese `/HWPD`, a
XRAM deveria sobreviver ao reset de execução; uma remoção de bateria
deveria invalidá-la. O ensaio opcional `MA17_WARM_REBOOT_TICK=N` reinicia
CPU e periféricos no primeiro limite de lote após o tick N sem zerar
RAM/ROM; o log `WARM-REBOOT` mostra o marcador `F8:FFh` antes/depois.
O reset inicial representa bateria recém ligada quando não há arquivo;
ao carregar XRAM salva, o bit `PCON.POF` é limpo para representar reset
com alimentação mantida. O evento é instantâneo e ainda não simula a duração da chave
desligada nem a tensão física em `/HWPD`.
Para ensaios que atravessam processos, `MA17_XRAM_STATE_FILE=/caminho/estado.bin`
carrega e salva os 1.024 bytes modelados de XRAM `F800h..FBFFh`.
Arquivo ausente inicia com zeros; formato inválido causa erro. A gravação
usa arquivo temporário seguido de renomeação. Cada ECU/ROM de ensaio
deve usar seu próprio caminho: o arquivo não vincula automaticamente a
imagem de firmware. Sem essa opção, as execuções continuam isoladas.
Na própria ROM, o reset em `0850h` escreve `P4=EAh` e `P5=0Fh`; a rotina
iniciada em `0AC1h` escreve `PCON=00h`. Nenhuma dessas escritas identifica uma
entrada física de chave. `ADC1` é usado no modelo como monitor de tensão
de bateria, sem ligação comprovada à linha 15. `P5.0/P5.1` são saídas
candidatas das duas bobinas wasted spark, não entradas de alimentação.

O bit que o emulador mantém alto para evitar uma espera infinita é
`IRCON.0`, indicação interna de conversão ADC concluída: a ROM espera
por ele em `0711h` e `644Dh`. Ele não representa um pino de power-on.
`MA17_P5_FORCE_HIGH` é estímulo opcional de comparação e não participa
da inicialização normal. O antigo retorno repetido ao vetor de reset
foi atribuído ao defeito de `MOV @R1,B` que corrompia o stack pointer,
documentado em `BUG_FIXED_SUCCESS.md`; a hipótese de um pino de energia
forçado para evitar esse retorno não é sustentada pelo código atual.

O [manual de reparos MA1.7 da Alfatest](https://pt.scribd.com/document/656677219/Alfatest-Bosch-MA-1-7)
identifica no **conector da ECU**, não na CPU: terminal 8 como contato
de lenta aterrado ao fechar; 9/10 como massa/sinal da sonda; 28 como
comando do relé da bomba; 32/34 como motor DC do batente; 35 como
injetor. A saída 87 do relé da bomba alimenta o aquecedor da sonda
por fusível de 10 A; sua resistência nominal é indicada como 4–8 Ω.
Esses dados reforçam a topologia externa e delimitam os bindings ainda
abertos. Em particular, terminal 8→`P4.6` e terminal 28→pino da CPU
continuam hipóteses, sem trilha da placa identificada.

Para `P5.0/P5.1`, há agora uma intervenção adicional na ROM G: com
`RAM[57h]=1/2` **forçada**, doar somente as células de `7BBEh`/`7C36h`
de S88 altera `RAM[69h]` e as larguras dos pulsos P5 modelados; no
modo 1, cruzar `RAM[69h]` no leitor Timer 1 `043Bh` reproduz ou quase
restaura essas medianas. Isso documenta uma rota digital de temporização
sob estado preparado. Os níveis elétricos, drivers e terminais das duas
bobinas wasted spark continuam sem identificação na placa Fiat.

Para `P1.3/CC3`, a tabela constante `7036h→7AE0h` alimenta XRAM
`F8:7Fh`; a leitura em `480Dh` medeia, no ensaio G com ADC3 variável,
uma alteração de 68 ticks na largura baixa modelada de CC3.
`F8:7Fh` não é pino, e esse resultado não identifica o terminal do
bico monoponto nem a polaridade do seu estágio de potência.

`ADC6` é por enquanto um **canal no modelo**, não um pino do encapsulamento
ou terminal da ECU identificado. Na ROM G/S88, a leitura alimenta `66h`
em `0744h`; o caminho `11D1h→1255h..125Eh→19DEh..1A38h` alcança a
guarda de `78h`. O degrau de 10 bits `409→410` abriu essa guarda no
estado ensaiado a 1.000 RPM. Falta associar o canal ao pino analógico,
à trilha do TPS e à tensão física; não atribuir a ele um nome de pino
até verificar o esquema ou a placa.

Outra rota de `P1.3/CC3` passa pelo leitor `MOVX A,@R0` em `2027h`,
com `R0=A3h` e página `P2=F8h` no ensaio Fiat. `45F8h` escreve essa
posição a partir da curva ROM `79A8h`; alterar só o retorno do `MOVC`
em `79ADh` mudou um pulso baixo modelado de 233 para 57 ticks antes
da chamada `2036h→5469h`. Fornecer `FFh` apenas à leitura `2027h`
restaurou os 233 ticks com `F8:A3h` ainda armazenando `40h`.
Esse é um vínculo digital entre tabela,
XRAM e pino modelado; falta verificar a fiação e a função física.
O leitor `2027h` depende de um contador: com `ADC0/6=120/95`,
`2011h` desvia para `203Dh`, `204Fh` incrementa `F8:A2h` de `00h`
para `01h`, `2016h` lê `01h` e `203Ah` limpa o contador após agendar
CC3. Com `ADC0/6=120/180`, a leitura em `2016h` permanece `00h` e
`2027h` não é alcançado nos seis milhões de ticks testados. Em `2011h`
o primeiro caso tinha `PSW.F0=1` e `IRAM23h=2Fh`. A instrução
`SETB 23h.3` em `142Eh` só foi alcançada nesse primeiro perfil; seu
ramo começa em `1427h`, compara `R4` com `05h` e lê ROM via `MOVC`.
Ainda falta demonstrar qual condição de entrada levou a esse estado.
A associação de `P1.3`
ao terminal físico do bico continua hipótese, não identificação.

Segundo a descrição do hardware fornecida pelo usuário, esta ECU tem um
bico monoponto e duas bobinas wasted spark para quatro cilindros em quatro
tempos. O atuador de lenta é um motor DC com engrenagem sem-fim e ponte H:
ele move o batente mínimo da borboleta, e o interruptor integrado indica
quando ela encosta no batente. Isso orienta a busca por uma entrada discreta,
controle das duas direções do motor e realimentação pelo TPS. Ainda
não há identificação elétrica dessas três conexões no firmware Fiat.
O usuário também informa uma saída física para liberar o acoplamento do
ar-condicionado. A hipótese de que a ECU exija operação estável do motor
antes de ativá-la ainda carece de rastreamento de entrada, condição e pino;
nenhum nome do IDA ou do scanner foi tomado como prova dessa associação.
Um candidato verificável está em `21D4h..220Fh`: a ROM lê `P4.7`, usa
`DPTR=7200h` para consultar `72C3h=0Eh` e `72C4h/72C5h=0Dh/0Eh`,
compara o limite escolhido com `RAM[63h]`, e escreve o complemento do
carry resultante em `P5.3`. Antes da escrita, `C` é a conjunção da
comparação `ROM[72C4h/72C5h] < RAM[63h]`, `P4.7=1`, `22h.5=0` e
`PSW.5=1`; `22h.4` guarda a mesma condição. Em duas partidas G a
1.000 RPM/2,4 milhões de ticks, com `P4.7` padrão ou forçado baixo,
o probe `MA17_TRACE_P53_GATE=1` registrou 230 passagens por `220Fh`
em cada caso. A mudança de `P4.7` alterou `PSW.5` na rota anterior,
mas `22h.5` permaneceu ligado nas 230 passagens e `P5.3` ficou alto.
Num trace da rota produtora, `21C6h` (que liga `22h.5`) foi visitado
230 vezes e `21CAh` (que o limpa) nenhuma; em 229 passagens por
`21C6h`, `28h.1=1`. Os opcodes `2174h..2180h` incluem `28h.1` na
condição que segue para `21C6h`. Isso identifica uma guarda ativa no
estado testado, sem estabelecer a função física de `28h.1`. Com TPS
experimental `ADC0/6=40/95`, `28h=00h` nas 230 visitas, mas `21C6h`
continuou a ligar `22h.5`: `2Eh.0=1` desviou diretamente de `216Ah`
nas primeiras 21, e as outras 209 passaram por `21C2h` antes de
`21C6h`. Nestas 209, RAM superior `9Eh.6=1` e o contador em RAM
superior `A6h` permaneceu não zero (`64h..50h`); `2167h` desviou da
checagem de `28h.1` em `2174h`. `2Dh.5` só decidiu se o contador seria
decrementado antes de `21C6h`. Logo, limpar `28h.1` isoladamente não
libera essa saída.
Assim, o ensaio identifica a dependência digital e o bloqueio neste
estado, sem demonstrar que `P4.7` seja o pedido de A/C nem que `P5.3`
seja a saída física da embreagem. A associação com estabilidade do motor
depende de rastrear os produtores de `22h.5` e medir outros estados.
Num ensaio G de 15 milhões de ticks, `A6h` zerou por volta do tick
10.505.322; `27h.1/.3` continuaram bloqueando a saída. Ao substituir
somente a leitura XRAM `F8:39h` por `0Eh` e usar `ADC3=20`, o código
limpou `22h.5` e o latch P5.3 ficou baixo em 439 amostras. Isso
confirma uma rota digital sob intervenção, sem identificar o terminal
da ECU nem a polaridade elétrica do eventual driver.
Com TPS `ADC0/6=100/155` e `ADC3=20`, o mesmo perfil G alcançou
`21CAh` 440 vezes e registrou 439 amostras de P5.3 baixo **sem**
substituir a leitura `F8:39h`. Nesse estado, `27h=04h`, `28h=00h` e
`746Ch` foi lida 922 vezes. A origem elétrica das duas pistas TPS e a
ligação física de P5.3 continuam sem confirmação.
Há também uma leitura de `P4.7` em `48ECh`: no estado G testado,
ela decide se a curva ROM `74A8h` recebe um piso antes de gravar
`RAM46h` em `48FFh`. Com o pino modelado alto, o valor `22h` virou
`25h`; com o pino forçado baixo, permaneceu `22h`. Uma intervenção
somente no `MOVC 532Fh/74A8h` que entregou `42h` resultou em `42h`
nos dois estados. O ramo alternativo `T2CON.1=1` seleciona
`7010h→74C6h` com `IRAM57h=0`, ou `7012h/7014h` com
`IRAM57h=1/2`, e pula esse piso mesmo com `P4.7` alto. Com
`T2CON.1=0`, os seletores `1/2` usam `700Ch/700Eh` e ainda passam
pela guarda de `P4.7`. Esses estados foram preparados na execução
isolada dos opcodes originais das seis ROMs; sua seleção natural não
foi demonstrada. Essa segunda dependência digital de `P4.7` não
identifica a função do terminal na ECU; consulte o manual SAB80C517
para o pino multifunção e meça a placa antes de associá-lo ao A/C.
Em uma intervenção tardia somente no `MOVC 532Fh/74A8h`, o valor
armazenado em `RAM46h` passou de `25h` para `42h` e a guarda `23AFh`
da rota de posição de lenta mudou de carry zero para um, impedindo
`23B9h`. Fornecer `25h` somente à leitura `MOV A,46h` em `2307h`
restaurou `231Ch` (`CLR 20h.3`) e `23B9h`, mesmo com `RAM46h`
armazenando `42h`. A subtração em `23A1h` deixou carry zero nos
quatro braços; `20h.3` explica a diferença posterior em `23AFh`.
Isso estabelece a mediação digital de `RAM46h` nessa guarda, mas
não isola a leitura de `P4.7` até o atuador: `IRAM20h/24h` também
mudaram; este ensaio não demonstrou alteração de `XRAM[F8:3Dh]`
nem incluiu medição física do pino.
O scanner chama o campo `MOVX` de endereço baixo `3Dh` de posição do
atuador (`F8:3Dh` na hipótese de página); isto **não é** o mesmo
endereço que a `IRAM[3Dh]` usada pelo código em `30F0h` para definir
`29h.0`. A própria ROM escreve `IRAM[3Dh]` em `0C48h` e `187Fh..1910h`,
na rota que lê `ROM[7221h]` para a correção lambda. O nome do IDA
`IDLE_RPM_REGULATOR` em `003Dh` também é enganoso: esse `LJMP 58BCh`
chega a um trecho que limpa `TR1`, liga `P5.0/P5.1` e zera `47h`,
compatível com o serviço do Timer 2/RPM, sem prova de acionamento da
ponte H. A leitura do interruptor e as saídas do motor seguem em aberto.

O estímulo `MA17_TRACE_IDLE_POSITION=1` registra mudanças de `XRAM[F83Dh]`
com PC e tick, sem alterar o valor lido ou escrito. Em três boots G
de 1,6 milhão de ticks a 1.000 RPM, `ADC0/6=20/70`, `40/95` e
`120/180`, apareceram apenas quatro mudanças: autoteste da XRAM em
`55A1h` (`00→55→AA`), limpeza em `0A51h` (`AA→00`) e inicialização
em `0C8Dh` (`00→07`). O caso `40/95` continuou até 12 milhões de
ticks sem nova mudança. Portanto, esses perfis ainda não demonstram
um laço fechado do atuador; falta estimular e identificar o interruptor
e observar os sinais de comando da ponte H. Capturas:
`build/ma17-analysis/variants/idle_position_tps_{20_70,40_95,120_180}/`
e `idle_position_tps_40_95_12m/`.

Há outro escritor efetivo em `2494h`: ele copia `R4` para `F83Dh`.
`2378h` lê o valor atual para `R4`, e os ramos `23CEh..2490h`
podem incrementá-lo ou decrementá-lo antes da escrita. A busca por
endereços literais também aponta os escritores condicionais `2258h`,
`22EFh` e `281Fh`; endereçamento calculado ainda não foi excluído.
`MA17_TRACE_IDLE_POSITION_ALL=1` inclui escritas sem mudança de valor.
Em oito cenários G (TPS 40/95 ou 120/180; ADC2=40/160;
ADC3=4/80), `2494h` escreveu `07h→07h` de 117 a 230 vezes em
2,4 milhões de ticks. Cinco rotações de 750 a 4.000 RPM produziram
107 a 114 dessas escritas, todas `07h→07h`. Forçar experimentalmente
P4.7 baixo em TPS 40/95 ou 120/180 tampouco mudou o byte. P4.7 pode
ser a saída alternativa CM7 no C517A; o ensaio não identifica sua
ligação na ECU. Capturas `idle_position_grid_*/`,
`idle_position_rpm_*/` e `idle_position_p47low_*/`.

O bloco original `23CEh..2494h` comprova que `F83Dh` pode mudar sob
outros estados. Com `DPTR=7300h`, `R4=07h` e XRAM `F840h..F845h=66h`,
uma execução isolada dos opcodes das seis ROMs produziu `F83Dh=06h`
ou `08h` conforme o carry de entrada. No mesmo bloco, `7305h=65h`
limita a redução de `F840h..F845h`, `7306h=9Ch` limita o aumento,
e `7301h=33h` limita o incremento de `R4`; os quatro casos de borda
foram testados. Nas ROMs A/A+/S37/S36, a entrada homóloga é `23EAh`
(G/S88: `23CEh`). São caminhos digitais com estado preparado; nenhum
boot sem alteração do estado intermediário demonstrou ainda `F83Dh`
subir ou descer.

O salto em `23AFh` bloqueia a entrada nesse bloco quando qualquer uma
das guardas anteriores deixa carry ligado. Com TPS 40/95 e ADC3=4,
`63h=04h` já estava abaixo de `ROM[7358h]=18h`, mas o trace em
`23AFh` ainda mostrou carry 1, `20h.3=1`, `24h.4=0` e `2Dh.4=0`.
As três últimas condições, cada qual presente na cadeia de `ORL C`,
impediam o ramo. Isso explica por que reduzir só o ADC3 não mudou
`F83Dh`; as condições físicas correspondentes ainda são incertas.

Em um boot G de 12,3 milhões de ticks, com ADC3=4, TPS 120/180 e
`P4.6` lido em zero somente a partir do tick 12.200.000, `20h.3`
já havia sido limpo em `231Ch` no tick 12.030.846. Em `23AFh`, no
tick 12.287.229, o carry foi zero e as guardas externas passaram.
Sem intervenção em `R4`, a comparação viu `R4=R5=07h` e não houve
mudança de `F83Dh`. Em dois contrafactuais com a mesma ROM original,
alterar somente `R4` em `23B1h` para `05h` ou `09h` fez as
instruções originais em `2494h` escreverem `07h→06h` ou `07h→08h`.
O estímulo `MA17_OVERRIDE_IDLE_POSITION_R4` não modela um sensor
físico; demonstra a causalidade digital depois que a guarda abre.
Capturas `idle_position_r4_{05,09}_12_2m/`; teste lento
`test_idle_position_r4_change_steps_original_rom_in_both_directions`.

A leitura independente `01h` com bytes `[01,F8,0C]` retornou `80h`,
igual à posição 4 do quadro `F4h`. Na rotina de leitura, `F8h` seleciona
`MOVX`; a página efetiva vem de `P2/XPAGE`, portanto o pedido isolado não
prova que o segundo byte é um endereço alto. O ensaio de PTY confirmou
quatro campos por duas rotas distintas; os outros seis ainda têm apenas a
relação estrutural comprovada pelo teste isolado da rotina.
Nos ensaios da ROM G com ADC3=4, ADC5=40/200 e 2,4 milhões de ticks,
`F8:0Ch` foi escrito pela rotina de correção, mas seu único `MOVX` leitor
observado foi o autoteste da XRAM em `55A2h`. A intervenção nesse autoteste
é inválida; preservá-lo não revelou leituras posteriores do byte. Assim,
o campo é uma saída diagnóstica observada nessa janela, sem evidência de
realimentação direta do valor armazenado para o cálculo de CC3.
No fluxo atual de `src/ECUSerial/ECUSerial.cpp` do scanner, o pedido de
coleta imprime os bytes do quadro `F4h`; as descrições da tabela não são
aplicadas nessa saída. A regra de endian também depende do comando:
`errorPacketToString()` monta o código de falha como
`data[0] | (data[1] << 8)`, coerente com `02 04` → `0402h`, enquanto o
scanner combina leituras genéricas de dois bytes em ordem oposta.

A agenda ADC em 06E3h..06F1h fornece ao serviço TF0 um byte por índice
`R6=1..15`. Os três bits baixos escolhem o canal em `ADCON0`; o byte
inteiro é o alvo inicial em `R1`. Depois de `IADC`, 0721h..0747h guarda a
amostra. A ROM contém este mapa de destinos:

| Canal | Índices `R6` | Alvo inicial | Escrita observada no fluxo |
| ---: | --- | --- | --- |
| 0 | 5, 10, 15 | `60h` | IRAM `60h` |
| 1 | 3 | `61h` | IRAM `61h` |
| 2 | 8 | `62h` | IRAM `62h`, com tratamento de extremos |
| 3 | 7, 13 | `63h` | RAM superior `A8h` |
| 4 | 2 | `64h` | IRAM `64h` |
| 5 | 1, 6, 11 | `65h` | IRAM `65h` |
| 6 | 4, 9, 14 | `66h` | IRAM `66h` |
| 7 | 12 | `67h` | IRAM `67h` |

Um teste com os opcodes originais percorreu os índices 3, 4, 7, 8 e 12:
confirmou os canais 1, 6, 3, 2 e 7 e, com amostra `5Ah`, a gravação de
`5Bh` nos destinos indicados. No índice 7, `RAM[63h]` permaneceu zero;
4629h lê `A8h` e 4756h escreve um valor elaborado em `63h`. O scanner
descreve `61h` como bateria, `62h` como temperatura do ar, `63h` como
temperatura do líquido e `66h` como TPS. Este fluxo confirma as relações
com canais ADC e a etapa intermediária de `63h`; não identifica os pinos
físicos nem valida as calibrações desses sensores.
O scanner cadastra também `60h` como TPS trilha 2 e `66h` como trilha 1;
as faixas 0–24° e aproximadamente 18–90° usadas pelo decoder são hipóteses
de conversão do scanner, não uma medição elétrica feita aqui. A chamada
`readECUMemory` envia `addressHigh=00h` e `addressLow` igual ao endereço IRAM.
Em rastros Fiat de 1,5 s a 1.000 RPM, alterar separadamente os canais 0, 2,
3 e 6 para `ADDAT=40` fez `0744h` gravar `29h` em `60h`, `62h`, `A8h` e
`66h`, respectivamente; `4756h` propagou o valor de `A8h` para `63h` no
ensaio do canal 3. Com os estímulos padrão, esses destinos ficaram em
`79h`, `65h`, `51h` e `60h` após a primeira amostragem. O valor `29h`
corresponde ao `ADDAT+1` observado no caminho. Esses testes sustentam o
mapa de memória do scanner para o dump Fiat, sem comprovar a fiação externa.
Em 1047h..10B8h, a ROM lê juntas `RAM[60h]` e `RAM[66h]` e testa limites
distintos (`F0h`, `12h`, `8Dh` para `60h`; `07h`, `DCh`, `DFh`, `FAh` para
`66h`). Isso confirma tratamento conjunto das duas pistas, sem estabelecer
uma conversão angular nem a fiação do TPS. O bloco 2706h..2729h também
compara `66h` com XRAM `35h` antes de atualizar esse estado.
No caminho normal em 11C4h..11D4h, o firmware usa o valor selecionado em
`R4`, executa `SUBB A,#0Dh` com piso zero, divide por 3 e grava `RAM[70h]` em
11D1h; 11D4h grava `RAM[6Fh]`. Num ensaio histórico Fiat, anterior à
correção do ADC, de 1,2 s a 1.000 RPM,
com ADC7=63, os pares finais `(6Fh,70h)` foram `(27h,0Dh)` com entradas
padrão, `(53h,1Bh)` ao mudar somente ADC0 de 120 para 40 e `(A8h,38h)`
ao mudar somente ADC6 de 95 para 180. As escritas vieram dos mesmos PCs
nos três casos. A pista 1 baixa (`ADC6=40`) não alterou esse par nesse
estado. Esse ensaio indicava contribuição das duas pistas para os bytes
derivados, mas os valores precisam ser repetidos com o ADC corrigido;
ele não calibra o ângulo físico nem resolve toda a arbitragem.
Esta grade histórica também foi obtida antes da correção do ADC do C517A.
Uma grade de nove combinações, nas mesmas condições de 1,2 s, mostrou
os pares finais `RAM[6Fh]:RAM[70h]` abaixo. Os cabeçalhos são valores
brutos injetados em ADC0/ADC6, antes do `+1` artificial do modelo antigo
em 0744h:

| ADC0 / ADC6 | 40 | 95 | 180 |
| ---: | --- | --- | --- |
| 40 | `27:0D` | `53:1B` | `A8:38` |
| 120 | `27:0D` | `27:0D` | `A8:38` |
| 180 | `27:0D` | `27:0D` | `27:0D` |

Com o modelo ADC corrigido, a execução G a 1.000 RPM, ADC2/3=140/34,
ADC6=180 e 4 milhões de ticks deu `RAM[6Fh:70h]=A7h:37h` para
ADC0=40 e ADC0=120. `RAM[60h]` mudou de `28h` para `78h`, enquanto
`RAM[66h]=B4h` ficou constante. Esses resultados atuais não devem ser
combinados numericamente com os `A8:38` da grade histórica; as capturas
estão em `build/ma17-analysis/variants/7939_tps_factor_adc0_*_adc6_180_control/`.

Na grade histórica, o par derivado dependia da combinação das pistas,
inclusive com retorno ao par `27:0D` em combinações extremas. A grade
não representa posições reais do TPS: faltam as funções de transferência
elétrica das duas pistas e a comprovação dos limites de sobreposição.
Os relatórios ficam em `build/ma17-analysis/tps_grid_*/execution.json`.
O ramo alternativo `11A8h..11C0h` grava primeiro `6Fh` e depois
`70h=min(FFh,6Fh+38h)`. No estímulo ADC0/6=40/220, o trace G
observou `6Fh=1Bh` em `11B6h` e `70h=53h` em `11C0h`, nas duas
leituras experimentais de P4.6. Assim, `70h` tem pelo menos dois
algoritmos escritores; o ramo `11C0h` supera o limite `4Ah` da
primeira origem do código de falha `0402h`.
Os bytes `11A8h..11D4h` são idênticos nas seis ROMs. Um teste que
executa o trecho original `11A8h..11C0h` em cada imagem confirmou
`(R2,R3)=(30h,22h)→(6Fh,70h)=(1Bh,53h)`, piso em `00h/38h`
e saturação em `FFh/FFh`; isso prova a fórmula digital comum,
sem demonstrar que as seis revisões chegam ao ramo no mesmo estado.
O rastro de `1047h`, `115Fh`, `1175h` e `11C4h` mostra o mecanismo do
par repetido. Com ADC0/ADC6 em `120/95`, `40/40` ou `180/180`, a passagem
em 115Fh tinha `RAM[28h]=06h`; em 116Dh a condição `.1/.2` selecionou
`R4=34h` de `ROM[72A1h]`, e 1175h zerou `R2`. A rotina então calculou
`6Fh=27h`, `70h=0Dh`. Para `40/95` e `120/180`, `RAM[28h]=00h`, `R4`
permaneceu `60h` e `B5h`, respectivamente, e os pares finais foram
`53:1B` e `A8:38`. Assim, `27:0D` é um valor de substituição nesse
caminho observado; o significado diagnóstico das flags `.1/.2` ainda
precisa ser confirmado. Os PCs e registradores estão em
`build/ma17-analysis/tps_flow_*/emulator-trace.log`.
O rastro adicional `tps_flow_dptr_baseline/` confirmou `DPTR=7200h` antes
da busca em `DPTR+0A1h`; `ROM[72A1h]=34h` no dump original.
As flags `.1/.2` também têm um caminho de diagnóstico demonstrado pelos
opcodes originais. Com o bit previamente presente em XRAM 85h, 4081h
calcula `RAM[28h]&XRAM[85h]` e 41F3h grava o resultado em XRAM 4Fh.
Na varredura, `R3=0Ah` seleciona 4Fh.1 e a tripla `02 06 1D` em 6E4Eh;
`R3=0Bh` seleciona 4Fh.2 e `02 06 1E` em 6E51h. O scanner chama o código
little-endian `0602h` de erro TPS. O teste
`FirmwareTpsFlagsSelectFaultCode0602` confirma ambas as rotas isoladas;
o significado dos status `1Bh/1Dh/1Eh` ainda exige análise. A varredura
natural também depende de `R7`: com `R3=0Ah`, `R7=00h` indexa 6E45h
(`02 06 1B`), enquanto `R7=09h` indexa 6E4Eh (`02 06 1D`). Em
4378h..438Ch, a ROM testa `RAM[28h].2` e `B.4` antes de escolher `R7=00h`;
a origem do valor de `B` nesse caminho ainda precisa ser rastreada.
No harness Fiat, a persistência ocorreu naturalmente: com entradas padrão
ou `ADC0/ADC6=180/180`, 41F7h gravou `06h` em XRAM F885h e 4200h
propagou `06h` a F84Fh. Com `40/95` ou apenas ADC6=180, não apareceu
essa escrita em F84Fh no ensaio de 1,2–2 s. As escritas iniciais
`55h/AAh/00h` em F885h vieram do autoteste de XRAM em 55A1h/55BFh e
não são flags de falha. O relatório `fault_xram_observation` guarda os
eventos. Uma sessão PTY reproduzida com o dump original e 1.000 RPM
(`MA17_CRANK_IMMEDIATE=1`, `MA17_ADC_CH7=63`, `MA17_ADC_CH0=120`,
`MA17_ADC_CH6=95`) recebeu respostas `FCh` com `02 04 1E` e `02 06 1B`.
O rastro `MA17_TRACE_PC=1` mostrou `R3=0Ah`, `R7=00h`,
`XRAM[4Fh]=06h` em 4329h e escritas `02 06 1B` em XRAM CDh..CFh por
433Ch. Portanto, há transmissão natural do código TPS `0602h` neste
cenário; o status `1Bh` não deve ser confundido com as triplas `1Dh/1Eh`
dos ensaios isolados. O teste reproduzível é
`MA17_TRACE_PC=1 MA17_CRANK_IMMEDIATE=1 MA17_ADC_CH7=63 MA17_ADC_CH0=120 MA17_ADC_CH6=95 MA17_EXPECT_FAULT_TRIPLET=02061B ./run_full_test.sh`.
O assert opcional no cliente PTY exige a tripla exata; os eventos do
emulador ficam em `build/ma17-analysis/pty/run-full-test.log`.

Ensaio Fiat controlado: 1.000 RPM, roda 60-2 imediata, 3 s sem K-Line,
`MA17_ADC_CH7=63` em todos os casos. Cada linha altera somente o canal
indicado em relação aos padrões do harness. As medianas são de amostras
nas entradas de 058Eh e das bordas de saída capturadas pelo emulador:

| Estímulo ADC | `RAM[14h:15h]` | CC3 baixo (ticks) | P5.0 baixo (ticks) |
| --- | ---: | ---: | ---: |
| Padrão | 2690 | 10748,5 | 1861 |
| Ar, CH2: 100 → 40 | 2524 | 10084,5 | 1861 |
| Água, CH3: 80 → 40 | 2424 | 9684,5 | 1861 |
| TPS pista 2, CH0: 120 → 40 | 1444 | 5764,5 | 1861 |
| TPS pista 2, CH0: 120 → 180 | 2690 | 10749 | 1861 |
| TPS pista 1, CH6: 95 → 40 | 2690 | 10748,5 | 1861 |
| TPS pista 1, CH6: 95 → 180 | 2657 | 10616,5 | 1922 |

O caso CH6=180 foi repetido e deu as mesmas medianas. As alterações de
CH2/CH3 também ocorreram em ensaios independentes de 2 s. Esses valores
ADC afetam o estado temporizado calculado pela ROM sob as condições
testadas; o efeito não é linear nem independente de limites e flags. Antes
da publicação do par em 1ED3h, a rotina subtrai `RAM[63h]` em 1DDCh;
logo depois, em 1F06h..1F3Bh, testa `63h` e `62h` contra constantes da
ROM para outras decisões. A ligação elétrica de CC3 e P5 aos atuadores
continua não confirmada. Os relatórios completos estão em
`build/ma17-analysis/adc_compare_repeat_*/execution.json`.
Em 4095h..40D6h, outra guarda usa `RAM[63h]` (chamada de água pelo scanner):
se o valor é `1Ah` ou maior, grava `96h` em XRAM F888h e evita o ramo
especial. Com valor abaixo de `1Ah`, só considera esse ramo quando XRAM
F888h está zero; então exige ainda `RAM[70h]≥2Fh`, `RAM[47h]≥50h`,
`RAM[2Eh].0=0`, `RAM[2Fh].0/.2=0`, `RAM[29h].0=0` e XRAM F882h=0 antes de
ligar `R4.6/.7` e `R2.0`. Um teste dos opcodes originais confirmou as
fronteiras de `63h`, `70h`, `47h` e a guarda F888h. O comentário do IDA em
40CFh chama `63h≥1Ah` de motor frio, mas o desvio real entra no ramo com
`63h<1Ah`; a unidade de temperatura e a função final das flags continuam
dependentes de calibração e consumidores posteriores.
Para o índice 8 (`R1=62h`), o mesmo teste confirmou as quatro fronteiras
da substituição por `79h`. O valor ajustado é `ADDAT+1` nesse caminho:

| `ADDAT` | Ajustado | `RAM[62h]` | Flag em `RAM[28h]` |
| --- | --- | --- | --- |
| `02h` | `03h` | `79h` | bit 7 |
| `03h` | `04h` | `04h` | nenhuma |
| `F6h` | `F7h` | `F7h` | nenhuma |
| `F7h` | `F8h` | `79h` | bit 6 |

Para o canal 3, um teste isolado em 463Fh confirmou que `A8h=03h` ativa
`RAM[28h].4` e `A8h=E8h` ativa `.3`; nos dois casos, 4756h grava `11h`
em `RAM[63h]`. Esses bits passam pelo espelho `RAM[28h]`/XRAM 85h/4Fh
descrito abaixo, sujeito à persistência do bit anterior. Para `R3=0Ch`,
4414h..4427h seleciona `R7=09h`; a leitura da tabela em 4329h então usa
`3×R3+R7=2Dh` e produz `02 0A 1E` de 6E54h. Um teste dos opcodes
originais confirmou essa tripla e seu empacotamento em uma resposta `FCh`.
O scanner decodifica seus dois primeiros bytes como `0A02h` little-endian
e considera o status `1Eh` presente. A associação com o sensor físico de
temperatura do líquido vem da descrição do scanner; o caminho completo
em uma sessão K-Line ainda não foi reproduzido.
Em um ensaio isolado posterior, iniciando a segunda varredura em 4470h
com somente `XRAM[5Fh].3=1`, a ROM percorreu os índices `R3=20h..23h`,
selecionou `R6=0Ch/R7=09h` e produziu `02 0A 9E` em CDh..CFh. O teste
confirmou separadamente a montagem da mesma tripla no buffer `FCh`
quando iniciou o leitor com `R6/R7` já preparados.
O bit alto do status resulta de 44CCh. Isso liga o mesmo código numérico
ao segundo banco nesse estado controlado; não comprova ainda a transmissão
em uma sessão física nem o tempo de retenção da falha.

As flags `.6/.7` e o valor de substituição de `RAM[62h]` são fatos da execução isolada;
interpretá-los como falhas físicas do sensor requer rastrear seus consumidores.
Há dois consumidores diretos de `RAM[28h].6/.7` em 265Ch..265Fh: qualquer
bit ligado desvia para 26C5h, que zera XRAM DFh nesse caminho. O byte
`RAM[28h]` também entra no espelho de falhas: 4081h..4085h calcula
`R6=XRAM[85h]&RAM[28h]`; 41F3h..4200h grava o byte atual em XRAM 85h
e `R6` em XRAM 4Fh. Na varredura completa, 4414h..4427h atribui
`R7=09h` para `R3=0Fh/10h`, correspondentes a `4Fh.6/.7`.
Os índices resultantes `3×R3+R7` apontam para 6E5Dh (`02 0B 1E`) e
6E60h (`02 0B 1D`): código numérico `0B02h` em little-endian, que o
scanner descreve como temperatura do ar. Um teste dos opcodes originais
confirmou o caminho de `RAM[28h].6` até a tripla `02 0B 1E` com o bit
prévio em XRAM 85h e o estado da varredura preparados. O caminho natural
que estabelece esse estado e o papel físico de XRAM DFh permanecem abertos.

Uma afirmação anterior em `MA17_HIDDEN_FUNCTIONS.md` associa o controle do
injetor em `P1.3` à faixa 1247h..1269h. O assembly remontável nessa faixa
contém `MOVX`, busca de tabela com `MOVC` e comparação com `47h`, mas nenhuma
instrução que escreva `P1.3`. O manual identifica `P1.3` como pino
`INT6/CC3`; a ligação física com o injetor continua sem prova neste material.
Essa descrição anterior fica classificada como **hipótese não confirmada** e
não foi usada para renomear rotinas.
O manual do C517 mapeia `P5.0/CCM0` e `P5.1/CCM1` como saídas de comparação
concorrente. O firmware comuta esses dois bits em 0090h..00AFh e também em
0252h..027Bh, dentro do serviço associado a IEX3, que recarrega `TL1/TH1`
em 0283h..029Bh. Os valores vêm de `RAM[32h:33h]` e `RAM[34h:35h]`,
calculados em 045Bh..048Ah e 04E5h..051Eh com `RAM[36h:37h]` como entrada.
O mapa de SFRs do manual dá reset zero a `CC4EN`, `CMEN` e `CMSEL`; uma busca
nas instruções classificadas do assembly Fiat não encontrou acesso direto a
esses registradores nem a `CCL4/CCH4`. Assim, o rastro atual de `P5.0/1`
reflete as escritas GPIO no latch, com a ressalva de caminhos ainda não
classificados e da eletrônica externa. A atribuição `DATA_COMM` que aparecia
em código morto do harness foi removida por não ter evidência.
O conjunto é um candidato concreto para estudar o
sequenciamento das duas bobinas wasted spark informado pelo usuário; o
listing e o manual não mostram a fiação da ECU, então a atribuição física
continua uma hipótese. `RAM[34h:35h]` também aparece no serviço serial em
61D8h..62C4h; um nome global de "tempo de bobina" nesses endereços seria
enganoso sem delimitar o contexto e o banco de registradores.
Há uma dependência adicional verificável: 3B06h publica em `RAM[69h]` um
valor derivado da tabela em 7200h; 043Bh e 048Eh usam esse byte no cálculo
das recargas de Timer 1 em `RAM[32h:35h]`. O scanner lê o endereço 69h como
`ign_advance_deg`, mas a fórmula em graus é interpretação do scanner.
Um teste isolado dos opcodes originais em 043Bh..048Ah confirmou que mudar
`RAM[69h]` de `9Ah` para `A2h`, mantendo `RAM[36h:37h]=011Dh`, altera a
recarga em `RAM[32h:33h]`. No rastro de 1.000 RPM, o byte passou de `A2h`
para `9Ah` durante a estabilização. Essa cadeia reforça o candidato de
temporização de ignição, sem identificar a fiação nem a polaridade das bobinas.
Outro caminho temporizado programa `CCL3/CCH3` e altera `P1.3` em 058Eh e
5469h. O primeiro lê `RAM[14h:15h]`, escritas em 1ED5h..1ED9h; o segundo
recebe valores em `R2:R3`. O listing do IDA chama `RAM[14h:15h]` de tempo de
injeção, mas a ligação do pino `P1.3` ao bico monoponto não está demonstrada.
O bloco nomeado `publish_cc3_interval_from_r3r2` em 1ED3h publica
`R3:R2` nessa ordem alta/baixa. A cadeia anterior em 1E02h..1ED2h
aplica coeficientes lidos por `MOVC` em `DPTR+BCh`, `DPTR+B4h/B5h` e
`DPTR+18h/19h`, além de valores XRAM, antes de limitar o resultado.
Em 058Eh..05DCh, a ROM desloca o par um bit à esquerda e soma o valor
dobrado ao registrador `CCL3/CCH3`. Com `MA17_ADC_CH7=63`, todas as
entradas observadas em 058Eh passaram pelas guardas de 2Bh.5 e 26h.7:

| RPM estimulado | Entradas em 058Eh | `RAM[14h:15h]` mínimo / mediana / máximo |
| ---: | ---: | ---: |
| 750 | 71 | 2486 / 2843 / 6518 |
| 1.000 | 94 | 2373 / 2690 / 6518 |
| 2.000 | 191 | 2295 / 2364 / 6518 |

O scanner de referência cadastra `inj_time_ms` como leitura de dois bytes
em `addressHigh=00h`, `addressLow=14h` e calcula o inteiro como
`(data[0] << 8) | data[1]` (`SensorDecoders.cpp` e `ECUSerial.cpp`). Um teste
executando a rotina de leitura da ROM Fiat com `RAM[14h:15h]=09A7h` recebeu
`09h A7h`, confirmando endereço e ordem dos bytes. Essa ordem difere da
montagem little endian do código de falha em `errorPacketToString`.
O decoder do scanner converte o valor por `raw × 4 µs`, derivado de um clock
assumido de 12 MHz; o harness Fiat usa 11,88 MHz. A interpretação como
largura física de pulso ainda depende de validar o modo efetivo do Timer 2,
o circuito de saída e o pino do injetor.

No perfil Fiat G, substituir `ROM[73C6h]` só na leitura `MOVC` em 52A2h
mudou a mediana de `RAM[14h:15h]` entregue ao agendamento de CC3 de 1.505
para 1.491 ticks. Intervir apenas na leitura de `XRAM[F8:91h]` em 47A2h
mudou `R5:R6`, mas não essa mediana; intervir nas duas leituras confirmou
a separação. Outro teste cruzado localizou a mediação na leitura de
`XRAM[F8:91h]` em `564Ah`: fornecer `14h` ali reproduziu 1.491 ticks
com a tabela original, e fornecer `34h` ali restaurou 1.505 ticks com
a tabela experimental. É evidência digital do caminho até o registrador
CC3 e o pino multifunção `P1.3/CC3`. A leitura relevante em `564Ah`
ocorre na chamada de `129Dh` (retorno `12A0h`); as chamadas de
`154Fh` e `15D2h` não reproduziram o efeito neste estado. Isso não
revela qual conector ou carga da ECU recebe o sinal. Em um segundo
cruzamento, a leitura `MOVC` da curva `7426h` alterou a RAM superior
`[87h]` e a temporização CC3; alterar a curva `7412h` mudou
`RAM[4Ah:4Bh]` sem mudar CC3 nesse mesmo estado. A ligação digital
foi estreitada até a saída da curva `7426h`: `1562h` usa `[87h]`,
`1644h` grava `RAM[59h:5Ah]`, `1D60h` lê esse par e `1ED3h` grava
`RAM[14h:15h]`. A S88 repetiu o efeito digital sobre CC3 com a mesma
curva e a mesma leitura `MOVC`, embora seus tempos absolutos diferissem.
A substituição das duas células `742Eh:742Fh` pelos valores da A/A+
também deslocou a temporização modelada de CC3 em G e S88 sob a
condição de borda ADC3 testada. Outro par, `7429h:742Ah`, produziu
o mesmo tipo de efeito com `ADC3=80` e `RAM[28h]=00h` nas amostras
observadas; isso compara calibrações digitais,
sem identificar a carga física do pino.
Nesses contrastes de `7426h`, as larguras baixas medianas modeladas
de `P5.0` e `P5.1` permaneceram iguais entre controle e intervenção
em 750, 1.000, 1.500, 2.000, 3.000 e 4.000 RPM nas ROMs G e S88,
apesar da mudança em CC3. A fiação das
duas saídas P5 e de `P1.3/CC3` continua sem verificação elétrica.
Com rotação fixa de 1.000 RPM, contrastes adicionais nas entradas
`ADC3=40/160` selecionaram outros pares da curva `7426h`; em G/S88,
as células A/A+ mudaram CC3 sem mudar as medianas de P5.0/P5.1.
Ver `MA17_FIRMWARE_VARIANTS_ANALYSIS.md`, seção `73C0h`.

Esses números são valores do parâmetro de agendamento, não durações
elétricas medidas. A única entrada `CC3` visitada nesses ensaios foi 058Eh;
as chamadas de 5469h em 1B1Ch/2036h continuam comprovadas apenas por
fluxo estático. O modelo parcial de modo 1 não reproduz ainda todos os
efeitos de `CCEN` e do sinal interno de comparação descritos no manual.
O índice de instruções localiza 14 usos de `P1.3`: três testes `JNB` e onze
escritas (`SETB`, `CLR` ou `MOV bit,C`). Os locais de escrita são 007Dh,
05C2h, 05D3h, 05DBh, 0682h, 0686h, 3220h, 3227h, 54B1h, 54C8h e 6424h.
Esses endereços dão pontos concretos para trace e correlação com o hardware.
O scanner local, em `src/ECUSerial/ECUMonomotronic.cpp`, usa o comando `01h`
para leitura de memória e espera resposta `FEh`, com comprimento e endereço
alto/baixo. A ROM encaminha `01h` ao estado `05h` e à rotina 4E2Eh; o teste
dos opcodes originais confirmou a resposta `FEh`. O parâmetro chamado
`addressHigh` pelo scanner age como seletor IRAM/MOVX nesse bloco, sem
escolher a página XRAM. No caminho de `TF0`, o vetor 000Bh leva a 0630h:
o manipulador salva `XPAGE`, escreve `P2=F8h` e só depois chama o serviço
serial em 083Ah. Não há outra escrita direta em `P2` entre esses pontos.
Essa é a proveniência estática da página `F8h` para o ensaio; falta observá-la
durante uma leitura K-Line completa. Um rastro reproduzível com
`python3 tools/trace_ma17.py --seconds 3 --no-kline-inject --crank-immediate
--output-dir build/ma17-analysis/kline-page-probe` observou oito entradas em
4BDEh, todas com `P2=XPAGE=F8h`; o relatório JSON registra esses valores em
`kline_page_observation`. Nenhum quadro `01h` foi enviado nesse ensaio.
As tabelas de sensores do scanner também
contêm entradas marcadas como hipótese; não foram transferidas para nomes
de ROM.

No checkpoint anterior às correções do núcleo, uma execução de 5,5 segundos
do emulador compilado com o dump Fiat e `--8052`,
com `SIGUSR1` após um segundo, registrou reset em 0850h vindo de 0000h,
interrupções de Timer 0, entrada em 4AD1h e o envio dos dez bits de 5 baud.
O rastreamento opcional `MA17_TRACE_PC=1` observou 5.003 PCs distintos; não
observou 4E67h, 4EAFh, 61D8h nem 6441h nessa execução. A lista completa de
PCs está em `build/ma17-analysis/pc-hits.txt`: 48 das 106 entradas de função
do IDA foram visitadas, incluindo 4BDEh (máquina serial segundo o IDA).
Uma visita confirma execução do endereço no emulador, não a finalidade da
rotina nem equivalência elétrica com a ECU. O relatório fica em
`build/ma17-analysis/execution.json` e o log em `emulator-trace.log` no mesmo
diretório. O log não comprova handshake concluído nem resposta diagnóstica.
Nenhum estado do emulador foi usado para alterar o dump ou a montagem.

Um ensaio posterior, `MA17_TRACE_PC=1 ./run_test.sh`, executado via Native
Lab MCP, completou o handshake PTY com o endereço 10h a 5 baud: a ECU enviou
`55h`, as chaves `46 85 89 13`, três quadros de identificação `F6h`
(`0261 203 388`, `AN09I2000148`, `BOSCH MA17`) e o quadro final `09h`.
O tester respondeu com o complemento de cada byte, recebeu o ACK final e
saiu com código zero. O log em `build/ma17-analysis/pty/run-test.log` registra
5.962 PCs distintos, incluindo 4AD1h, 4BDEh e 4FA3h; 4E67h e 4EAFh não
foram visitados porque esse ensaio não enviou um comando de sensores.
O firmware reiniciou antes da resposta quando `RAM[47h]` ainda era zero:
o estímulo de roda fônica começa cinco segundos após o boot nesse modo.
Portanto o handshake prova a troca de identificação no emulador; naquele
ensaio, a sessão não foi exercitada com comandos posteriores.

O fluxo de pedidos foi conferido com o scanner local em
`src/ECUSerial/ECUMonomotronic.cpp`: `ECUReadErrors()` usa `07h`/`FCh`,
`readECUMemory()` usa `01h`/`FEh` com
`[comprimento, endereço alto, baixo]`, e `requestSensorCollection()` usa
`12h`/`F4h`.
O `test_pty.py` pulava um contador após o ACK final de cada pedido, gerando
NAK `0Ah` nos pedidos seguintes. Após corrigir o contador,
`./run_full_test.sh` concluiu handshake, leitura de falhas, três leituras de
memória e a coleta `12h`, com código de saída zero. Os quadros `FCh`
continham `02 04 1E` e `02 06 1B`; os pedidos `01h` para IRAM 63h, 62h e
47h retornaram `51h`, `65h` e `28h`; a leitura `01h` com seletor `F8h` e
endereço baixo `0Ch` retornou `80h`. O quadro `F4h` foi
`51 60 28 65 80 00 00 07 83 00`: suas posições 0, 3 e 2 repetem as
leituras independentes de IRAM, e a posição 4 repete a leitura `MOVX`.
Todos seguem os seletores da tabela 6E78h. O rastro
`MA17_TRACE_PC=1 ./run_full_test.sh` visitou 4ECBh, 4EAFh e 4C72h, mas não
4E67h. Esses valores são observados no emulador com os estímulos atuais;
não atribuem identidade física definitiva aos campos. O teste exige os
quadros finais, `FCh`, `FEh`, `F4h` e consistência dos quatro bytes; timeout
agora falha explicitamente.

O bloco pendente em `emu8051/core.c` que forçava recarga de Timer 2 em zero
foi desativado. O núcleo agora separa a lógica do Timer 2 do SAB80C517 da
lógica do 8052 genérico, com modos de entrada, prescaler e recarga baseados
na seção 7.5.1 do manual. Os demais periféricos e a temporização completa
do C517 ainda não foram validados contra hardware real.

### Verificação da roda fônica e do RPM

O simulador agora percorre 60 posições por volta, omite duas e comuta
`P1.0/INT3/CC0` a cada ciclo emulado. Na borda de descida, se `CCEN=01h` e
`T2CON.I3FR=0`, captura `TH2:TL2` em `CRCH:CRCL` e sinaliza `IRCON.IEX3`.
Removeu-se a escrita direta de `RAM[47h]`. O núcleo ganhou testes para os
índices de callbacks de interrupção, Timer 2 do C517, retorno de prioridade
em `RETI` e página `P2` de `MOVX @Ri`. O manual, seções 5 e 7.5, fundamenta
essas mudanças. Uma correção adicional implementa `XPAGE=91h` e `SYSCON=B1h`
do C517A: escritas em `P2` carregam `XPAGE`, e `MOVX @Ri` usa a página interna
quando XRAM está habilitada e `XPAGE>=F8h`. O
[datasheet da Infineon](https://www.infineon.com/assets/row/public/documents/10/57/infineon-d80517a-ds-en.pdf),
seção "Accesses to XRAM", fundamenta a correção. A ligação física das duas
bobinas wasted spark e do bico
monoponto aos pinos do microcontrolador ainda não foi demonstrada.

Antes da correção de `XPAGE`, `PUSH 91h` em 0638h salvava zero e `POP P2` em
0843h restaurava `P2=00h`. O teste em 4A36h então lia `XRAM[001Eh]=00h`,
embora a inicialização tivesse copiado `ROM[7FF7h]=48h` para `XRAM[F81Eh]`.
Esse erro levava ao ramo 4A7Eh e ao retorno a 0850h em 4AB7h com RPM zero.
O retorno é um `LJMP` do firmware, não um reset de hardware. Depois da
correção, o mesmo teste lê `XRAM[F81Eh]=48h`, sem retornar a 0850h no rastro.

`MA17_ADC_CH7=63 python3 tools/trace_ma17.py --seconds 3
--no-kline-inject --crank-immediate --rpm 1000` registrou bordas da roda a
cada 990 ciclos, capturas do Timer 2 e entrada em `IEX3`. O firmware executou
01AEh, 565Ah, 566Ch e 0EA5h; `RAM[47h]` passou de `00h` para `28h`. Na
escala do scanner (`byte × 25`), isso corresponde aos 1.000 RPM estimulados.
O relatório agora inclui todas as mudanças de `RAM[C4h]` observadas, sem
o antigo limite de 30 mensagens. A sequência inicial foi
`00→10→20→08→04→01`; em regime repetiu `01→02→04→01`.
Nos rastros de três segundos a 750, 1.000 e 2.000 RPM, o par de
transições `02→04`/`04→01` ocorreu 70/71, 93/94 e 190/191 vezes.
As duas rotas `01→02` terminam nos PCs 0156h e 0164h, alternando;
`02→04` termina em 00DAh e `04→01` em 00E5h. Esses PCs são os
endereços após a escrita, e os estados ainda não têm nomes físicos.
Os ensaios abaixo usaram o mesmo comando com `--rpm 750/2000`, `P5` sem
estímulo externo forçado e o núcleo com semântica de leitura do latch corrigida.
O tempo é expresso em ticks emulados; o harness assume 990.000 ticks/s.

| Estímulo | `RAM[47h]` | `P5.0/1`: período por canal | `P5.0/1`: baixo mediano | Intervalo entre canais |
| ---: | ---: | ---: | ---: | ---: |
| 750 RPM | `1Eh` | 79.200 ticks | 1.940 ticks (1,96 ms) | 39.600 ticks |
| 1.000 RPM | `28h` | 59.400 ticks | 1.861 ticks (1,88 ms) | 29.700 ticks |
| 2.000 RPM | `50h` | 29.700 ticks | 1.789 ticks (1,81 ms) | 14.850 ticks |

Em regime, `SETB P5.0` em 0096h e `SETB P5.1` em 009Eh encerram os
intervalos baixos; `CLR P5.0` em 00A6h e `CLR P5.1` em 00ABh os iniciam.
O vetor de Timer 1 em 001Bh chega a 0090h. O serviço `IEX3` em
0223h..0344h programa `TL1/TH1` com valores calculados em
045Bh..051Eh, enquanto 0298h usa `RAM[32h:33h]` e 0286h usa
`RAM[34h:35h]`. Os pulsos alternam entre P5.0 e P5.1 a cada meia volta.
Essa cadência e a largura quase constante são compatíveis com duas saídas
de ignição wasted spark, mas a fiação e a polaridade do estágio de potência
da ECU não foram verificadas. Os PCs de origem constam em `source_pcs` nos
relatórios `build/ma17-analysis/output-timing-fixed-{750,1000,2000}/`.

A ficha local [Double Fire Coil 2x2, Bosch 0 221 503 407](../Double_Fire_Coil_2x2_Datasheet_0221503407.pdf)
descreve uma bobina de quatro cilindros com dois primários e três pinos:
pino 1 para estágio de potência da bobina 2, pino 2 para `Ubatt`, pino 3
para estágio da bobina 1. Não há transistor integrado; a ECU precisa de
dois estágios de potência. A ficha informa 0,5 Ω por primário com fio,
corrente primária até 8 A e tempos de carga para 5 A de 2,4 ms a 12 V e
1,9 ms a 14 V. Um [catálogo Bosch de aplicações](https://www.todomecanica.com/recursos/folleto_bobinas_bosch.pdf)
lista o mesmo número para Fiat Tipo 1.6 i.e.; isso apoia a identificação
da peça, mas não comprova o número instalado no veículo deste dump.
Os 1.861 ticks baixos em P5.0/1 a 1.000 RPM correspondem a 1,88 ms na
escala do harness: mesma ordem de grandeza da tabela, mas sem corrente,
tensão de bateria, driver ou polaridade medidos não se pode chamar esse
intervalo de dwell elétrico. O alvo de verificação física é a sequência
ECU P5.0/P5.1 → dois drivers → pinos 3/1; a correspondência entre porta
e pino da bobina segue desconhecida.

O scanner chama `RAM[61h]` de tensão de bateria; a agenda ADC a alimenta
pelo canal 1. Em 4044h a ROM lê `61h`, calcula uma razão contra `64h` e
usa tabelas da ROM em 706Ch/706Eh. Num ensaio separado a 1.000 RPM, com
ADC7=63 e demais entradas fixas, a mediana baixa de P5.0 e P5.1 variou
com o estímulo ADC1: 40 → 10.334 ticks (10,44 ms), 60 → 4.541 (4,59 ms),
80 → 2.909 (2,94 ms), 100 a 160 → 1.861 (1,88 ms). Os casos 40 e 130
foram medidos por 3 s; 60 a 160, por 2 s. Essa resposta à entrada que o
scanner identifica como bateria reforça a hipótese de carga de bobina,
especialmente pela relação inversa até o patamar. A escala ADC1→volts,
o caminho completo até o Timer 1 e a corrente real seguem por confirmar.
Os rastros ficam em `build/ma17-analysis/battery_sweep_*/execution.json`
e `adc_compare_repeat_battery_*/execution.json`.
Após incluir `61h` no monitor de RAM, o log confirmou escrita em `0744h`:
ADC1=130 produziu `RAM[61h]=83h`, e ADC1=40 produziu `29h`. O PC 4044h
foi executado nos dois rastros. O Timer 1 também usa `RAM[34h:35h]` em
0286h; no início dos pulsos P5, esse par diferiu entre os ensaios, enquanto
`RAM[36h:37h]` permaneceu igual.
Com o monitor intermediário ativo por 2 s, ADC1=130 deixou `7Dh=FFh` e
`7Fh=22h`; ADC1=40 produziu `7Dh=73h` e `7Fh=96h`. As escritas ocorreram
em 404Bh e 4064h. Nesse último rastro, `31h` passou a `59h` em 32B8h,
enquanto o padrão terminou em `10h`; `34h` terminou em `C5h` versus
`8Bh`, sempre escrito por 051Ch. `35h` terminou em `FFh` nos dois casos.
O relatório `engine_ram_observation` preserva a sequência e os PCs em
`build/ma17-analysis/battery_chain_{baseline,low}/execution.json`.
A cadeia estática explica a dependência principal: 4044h calcula
`7Dh` a partir de `61h/64h`. Em 3291h, a ROM usa ponteiros big-endian
de 70AAh e 70ACh para 7B32h e 7B3Eh; o primeiro byte de cada tabela é,
respectivamente, o endereço IRAM `47h` (RPM) e `7Dh`. As duas buscas e a
interpolação por 70A2h gravam `31h` em 32B8h. Após 047Ah, o
serviço IEX3 lê `31h`, compara com a expressão baseada em `69h` e na
RAM superior `C7h`, coloca o resultado em `22h.7` e escolhe o caminho de
recarga `34h:35h` em 04E5h..051Eh. Em 0286h o mesmo serviço carrega
`TL1/TH1` desse par; o vetor TF1 chega a 0090h e alterna P5.0/P5.1.
O contraste ADC1=130/40 confirmou mudança de `7Dh`, `31h`, recarga e
largura P5 com RPM fixo. `7Fh` também mudou, mas seu papel nessa cadeia
de Timer 1 não foi demonstrado. A escala elétrica do pulso continua aberta.

O rastro antigo confundia `ORL P5,#00h` em 3B60h com uma borda de subida:
`emu8051/opcodes.c` lia o pino forçado alto, embora a seção 7.1.4.3 do
manual C517 exija leitura do latch para instruções de leitura e escrita.
O teste `PortReadModifyWriteUsesLatchWhileMovReadsPin` cobre essa distinção.
O estímulo legado `MA17_P5_FORCE_HIGH=1` continua disponível apenas para
comparação; ele suprime os caminhos `SETB P5.0/1` e não deve ser usado para
medir estes pulsos.

O contador de voltas completas do harness confirmou 58 dentes emitidos e
duas posições omitidas por volta nos dois ensaios adicionais (24 voltas a
750 RPM, 39 a 2.000 RPM). Os intervalos entre posições foram 1.320 e 495
ticks, respectivamente. A primeira volta parcial após o início é excluída.
Os relatórios anteriores em `rpm-750/` e `rpm-2000/` antecedem essa
correção de leitura de porta; use os relatórios `output-timing-fixed-*`
para a temporização das saídas.
O harness ainda força `IRCON.0=1` no callback de escrita para simular ADC
sempre pronto (`src/ma17/AdcSimulator.cpp:write_ircon`). Esse estímulo artificial
pode alterar o fluxo do firmware; o rastro atual não deve ser interpretado
como reprodução elétrica completa da ECU. O marcador legado em XRAM F8F8h
também é inicializado pelo harness, mas `RAM[47h]` é zerada pelo firmware na
rotina de 0850h, antes da primeira leitura de RPM observada.
O harness usa o perfil Fiat com clock fixo de 11,88 MHz, P4 para K-Line e
P1.0 para a roda fônica. O dump Renault Clio tem 65.536 bytes e revisão de
hardware/clock diferente; o `main.cpp` atual não seleciona um perfil Renault.
A hipótese informada para o Renault é um clock aparentemente próximo do
dobro; frequência e portas reais ainda não foram verificadas aqui. Não use
os tempos em ticks ou os nomes de pinos Fiat para interpretar o Renault.
O executável rejeita ROMs de tamanho diferente de 32 KiB antes de abrir a PTY.
`MA17_ALLOW_FOREIGN_ROM=1` permite executar outra ROM apenas como experimento
com o perfil Fiat; os timings e o mapa de portas não ficam validados por isso.
O tamanho tampouco identifica uma variante: outra ROM de 32 KiB ainda exige
conferência de hardware. A remontagem binária do Renault é separada.
O rastro dos latches não comprova o sinal elétrico na ECU.
O núcleo modela a captura de Timer 2 por escrita no byte baixo de `CRC` ou
`CC1..CC3` quando o par correspondente em `CCEN` vale `11`; um teste cobre
os quatro canais. A captura segue a seção 7.5.6 do manual C517: ignora o
byte escrito e transfere `TH2:TL2` no ciclo seguinte. Também modela a
transferência básica do latch de `P1.3/CC3` no modo de comparação 1. Captura
por borda nos demais canais, interrupções de comparação e transparência
durante o sinal interno de coincidência permanecem pendentes.
O modelo não representa a eletrônica externa da ECU.

Outras duas saídas observadas no mesmo perfil de estímulo têm esta
temporização. `P1.1` sobe em `SETB P1.1` de 0352h e desce em
`CLR P1.1` de 0433h; seu período é de meia volta nos três regimes. O
baixo mediano foi de 27.608, 20.662 e 10.292 ticks a 750, 1.000 e
2.000 RPM. A largura acompanha o período e não identifica por si só
um pulso de bico. `P1.3` tem latch baixo por quatro ticks entre
`CLR P1.3` em 05D3h e `MOV P1.3,C` em 05DBh; a captura por escrita em
`CCL3` faz o pino modelado permanecer baixo até a coincidência de Timer 2.
Esses resultados exigiram `MA17_ADC_CH7=63` para liberar a guarda em
`RAM[2Bh].5`. Não há evidência suficiente para rotular `P1.1` ou
`P1.3` como saída do injetor monoponto; a duração elétrica do bico segue
sem medição confiável.

Um pareamento das bordas baixas de CC3 e P5 no mesmo meio ciclo, com
ADC7=63, roda imediata e 2 s de execução, deu os seguintes resultados
na escala de 990.000 ticks/s do harness Fiat:

| RPM | Meio ciclo P5 = período CC3 | Pares | Baixo P5.0 | Baixo CC3 | CC3 baixo após início baixo P5 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 750 | 39.600 | 43 | 1.940 | 12.385 | 1.667 |
| 1.000 | 29.700 | 57 | 1.861 | 11.812,5 | 1.993 |
| 1.500 | 19.800 | 89 | 1.785 | 10.905 | 2.588 |
| 2.000 | 14.850 | 120 | 1.789 | 10.208 | 2.723 |

Em cada meio ciclo pareado apareceu uma borda baixa de CC3. A mediana
da fase muda com o RPM, e as larguras dos dois sinais são distintas.
Na captura histórica com ADC7=64, a guarda bloqueou CC3 enquanto P5
continuou alternando; a atualização sobre o limiar atual está abaixo.
Os relatórios estão em
`build/ma17-analysis/phase_verified_{750,1000,1500,2000}/execution.json`.
Esse padrão é compatível com um caminho de injeção separado das duas
saídas candidatas de ignição, mas não prova o pinout nem a polaridade do
driver do bico monoponto.

Em um degrau de TPS `180/247→40/95` a 3.000 RPM, o firmware G
continuou calculando `IRAM[14h:15h]` diferente de zero, mas parou de
produzir bordas em `P1.3/CC3`. O segundo teste em `0591h` (`JB 26h.7`)
desvia do agendamento quando `IRAM[26h].7=1`. Nas capturas tardias,
esse bit passou a 1 entre os ticks 2.184.194 e 2.194.094 no controle;
com `P4.6` baixo experimentalmente a partir do degrau, entre 1.877.295
e 1.887.195. O cut-off de desaceleração conhecido ocorre acima de
1.500 RPM com o interruptor de lenta pressionado, mas **P4.6 ainda não
está identificado como o contato físico**. A guarda digital de CC3 pode
acionar perto de 1.425 RPM no modelo e não determina esse limiar físico.
A observação confirma bloqueio digital de CC3;
não comprova corte físico do bico nem suficiência do TPS fechado. Detalhes
em [MA17_FIRMWARE_VARIANTS_ANALYSIS.md](MA17_FIRMWARE_VARIANTS_ANALYSIS.md).

No ensaio anterior de três segundos com ADC 7 no valor padrão 105, o PC
entrou 94 vezes em 058Eh. Em todas as entradas amostradas,
`RAM[2Bh].5=1`; a primeira instrução da rotina desvia
para 05DDh e evita programar `CCL3/CCH3`. Não houve transição observada em
`P1.3`. O bloco 3B06h leu `XRAM[F8DDh]` com `P2=XPAGE=F8h`; o firmware
gravou `55h` na inicialização, depois `19h`, e decrementou o valor até zero
no rastro. A sequência inicial `55h`/`AAh` em 559Ah..55B6h é um teste de
escrita e leitura da XRAM; 07B6h..07DFh carrega `19h` em F8DDh após a
contagem de `RAM[51h]`. Esse bloco controla o bit de guarda `RAM[2Bh].5`.
Por enquanto, o ensaio comprova que o caminho CC3 ficou bloqueado, sem
identificar a condição física que o habilitaria. O log registra as escritas em F8DDh e o
relatório `execution.json` resume as entradas em CC3.

`RAM[67h]` é escrito em 0744h pela amostragem do canal ADC 7: a tabela em
06E3h..06F1h contém `67h` e o firmware usa os três bits baixos do endereço
para selecionar `ADCON0`. O callback de ADC do harness devolve 105 nesse canal.
O antigo byte de partida em `DAh` adicionava `+1` artificial e produzia
`RAM[67h]=6Ah`; com `ADDATL` modelado, resulta `69h`. Em 3B22h, o
firmware compara esse valor com `41h` para atualizar `RAM[2Bh].5`. O sensor
físico ligado ao canal 7 ainda não foi identificado.

O ensaio `MA17_ADC_CH7=63 python3 tools/trace_ma17.py --seconds 3
--no-kline-inject --crank-immediate --output-dir
build/ma17-analysis/cc3-capture-fixed` deixou a guarda limpa nas 94 entradas
de 058Eh. O latch de software de `P1.3` teve 188 transições, e o pino
modelado, 187. A mediana entre quedas foi 29.700 ticks; o baixo mediano do
pino foi 10.801 ticks. Em 93 pulsos pareados, a largura baixa menos
`4 × RAM[14h:15h]` ficou entre −12 e −11 ticks, atraso de software entre
captura e borda. Houve 93 coincidências com o latch de software alto. Com
`MA17_ADC_CH7=64`, a guarda ficou ativa e não houve essas transições.
Essa captura precede a correção do byte ADC descrita acima. No build
atual, `RAM67h=64` deixa `2Bh.5` limpo e permite CC3; `RAM67h=65`
liga `2Bh.5` e bloqueia CC3. `PhysicalIntake.ConditionalCc3Fuel`
verifica o contraste em execução física da ROM original com pinos
ADC7 de 1,252 V e 1,260 V, respectivamente. O limiar digital é
confirmado; a função elétrica externa do canal 7 ainda é desconhecida.

Com ADC7 em 40 e 63, ambos abaixo do limiar, ensaios independentes a
1.000 RPM deram mediana `RAM[14h:15h]=2690` e largura baixa modelada de
10.748,5 ticks em ambos os casos. ADC7 liberou o caminho, mas essa variação
não alterou a duração medida. Mantendo ADC7=63 e mudando o estímulo da roda
de 1.000 para 1.500 RPM, as medianas passaram de 2.690 para 2.468 no par
de RAM e de 10.748,5 para 9.897 ticks no pino modelado; o período entre
quedas caiu de 29.700 para 19.800 ticks. Em ambos os regimes, a diferença
entre largura e `4 × RAM[14h:15h]` ficou em −12..−11 ticks. Esses ensaios
mostram dependência do estado calculado pelo firmware, sem identificar o
atuador físico ou isolar qual sensor determina o intervalo.

O resultado anterior de aproximadamente 29.691 ticks baixos vinha da falta
de captura por escrita em `CCL3` no emulador: o byte alto de `CC3` ficava
obsoleto e a coincidência era perdida. A relação atual entre intervalo
programado e pino modelado reforça a hipótese de temporização de um atuador,
mas ainda não identifica sua ligação elétrica ao bico nem a polaridade do
estágio de potência da ECU.

## Fidelidade e trabalho restante

Em `56B9h..571Ch`, a ROM contém repetições de `79 00 E7 F0 A3`, que
decodificam como `MOV R1,#00h; MOV A,@R1; MOVX @DPTR,A; INC DPTR`, seguidas
de `00h`. A entrada chamada em `56B1h` salta de `56B6h` para `571Dh` e
portanto não executa esse bloco. O IDA também o emite como bytes; nenhum
destino de fluxo direto ou PC observado entra em `56B9h..571Ch`. Ele fica
em `DB`, com interpretação de possível código alternativo ainda aberta.

O `asm51` montou `ma17.asm` por `INCLUDE`: 32.768 bytes, zero divergências,
SHA-256 idêntico ao original e sem avisos do assembler. Essa verificação roda
novamente a cada geração modular. Ainda faltam delimitação formal de funções
com chunks, referências indiretas, classificação semântica de grande parte
do código e dos dados, e validação elétrica para injeção e ignição, além de
comandos K-Line. Na saída modular, 5.228 bytes omitidos são lacunas `FF`;
os 4.120 bytes emitidos como dados não têm todos uma finalidade estabelecida.
