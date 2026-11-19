# Dinamômetro físico e bancada com a ROM MA1.7

Escrito com ajuda de LLM (Claude). Goal: `.work/GOAL_DYNO_ROM.md`. Artefatos em `docs/dyno/`.

## Fase 0 — linha de base

* Suíte completa no commit `26bae1d`: **505/505** (native_lab, `ctest -j6`).
* `sevel-dyno` ganhou `--dt-us` (padrão 100) e `--tdc-reference-deg` (padrão 120).
* `tools/dyno_convergence.py` → `docs/dyno/baseline/convergence.csv` + `manifest.json`
  (E22, leak 9 mm², 40 ciclos, dt 100/25/10/1 µs × MBT/30°/36°, 3000–6000 RPM).
  Verificação cruzada: MBT a 6000 RPM = 61,90 kW (100 µs) e 59,09 kW (1 µs), como no goal.

### Variante da ROM e combustível (0.4)

* Os testes de lenta (`PhysicalIdle.*`, `test_idle_acceptance.py`) e o Lab usam
  `FiatTipo_MA17_dump_27c256.bin`, SHA-256 `a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`
  (CMake passa `${PROJECT_SOURCE_DIR}/FiatTipo_MA17_dump_27c256.bin`).
* Em `MA17_FIRMWARE_VARIANTS_ANALYSIS.md` essa imagem é **G (gasolina)**; as imagens de álcool são A, A+, S88, S37, S36.
  O texto "IE ÁLCOOL" de `SEVEL_PHYSICS_CALIBRATION.md` estava errado e foi corrigido.
* Combustível para as Fases 5 e 6: **E22** (gasolina brasileira da época; mesmo do dyno isolado). O emulador
  usa E0 por padrão (`--ethanol-percent 0`); os cenários de dyno com a ROM fixam E22 explicitamente.
* Limitação: `FuelBlend` não modela a água do etanol hidratado. Só importaria se uma ROM de álcool (A/S*) fosse usada.

## § Bloqueios

(nenhum até agora)
