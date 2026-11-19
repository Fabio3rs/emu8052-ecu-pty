#!/usr/bin/env python3
"""Fill the generated blocks of docs/SEVEL_DYNO_ROM.md and docs/SEVEL_PHYSICS_CALIBRATION.md.

Every number in the generated blocks is read from the committed CSV/JSON artifacts under
docs/dyno/ (GOAL_DYNO_ROM rule 5). Blocks sit between <!-- BEGIN:name --> and <!-- END:name -->.
LLM-written (Claude).
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs" / "dyno"


def load(path):
    with open(path) as handle:
        return list(csv.DictReader(handle))


def convergence_block():
    out = ["| Modo | RPM | dt=100 µs antes (kW) | erro vs 1 µs antes | dt=100 µs depois (kW) | erro vs 1 µs depois |",
           "|---|---|---|---|---|---|"]
    base, fix = load(D / "baseline" / "convergence.csv"), load(D / "fase1" / "convergence.csv")

    def key(rows, mode, rpm, dt):
        return next(float(r["power_kw"]) for r in rows
                    if r["mode"] == mode and int(r["rpm"]) == rpm and float(r["dt_us"]) == dt)

    worst = [0.0, 0.0]
    for mode in sorted({r["mode"] for r in base}):
        for rpm in sorted({int(r["rpm"]) for r in base if r["mode"] == mode}):
            b100, b1 = key(base, mode, rpm, 100), key(base, mode, rpm, 1)
            f100, f1 = key(fix, mode, rpm, 100), key(fix, mode, rpm, 1)
            eb, ef = (b100 / b1 - 1) * 100, (f100 / f1 - 1) * 100
            worst = [max(worst[0], abs(eb)), max(worst[1], abs(ef))]
            out.append(f"| {mode} | {rpm} | {b100:.2f} | {eb:+.2f} % | {f100:.2f} | {ef:+.2f} % |")
    out.append("")
    out.append(f"Maior |erro| de dt=100 µs contra 1 µs: **{worst[0]:.2f} %** antes, **{worst[1]:.2f} %** depois.")
    return "\n".join(out)


def vefit_block():
    fit = json.load(open(D / "fase2" / "fit_result.json"))
    summary = load(D / "fase2" / "dyno_summary.csv")
    out = [f"* Parâmetro ajustado: `hs_gain` {fit['parameters_before']['hs_gain']:.5f} → "
           f"**{fit['parameters_after']['hs_gain']:.5f}** (rampa 2500→3500 RPM); custo final "
           f"{fit['cost_final']:.4f}. {fit['note']}.", "",
           "| RPM | torque (N·m) | alvo (N·m) | desvio |", "|---|---|---|---|"]
    for p in fit["points"]:
        out.append(f"| {p['rpm']} | {p['torque_nm']:.1f} | {p['target_nm']} | {p['deviation_pct']:+.1f} % |")
    out += ["", "| Etanol | Pico de potência | Pico de torque | Erro de forma máx. 2000–6000 |", "|---|---|---|---|"]
    for r in summary:
        out.append(f"| E{r['ethanol_percent']} | {float(r['peak_power_kw']):.2f} kW "
                   f"({float(r['peak_power_cv']):.1f} cv) a {r['peak_power_rpm']} RPM | "
                   f"{float(r['peak_torque_nm']):.2f} N·m a {r['peak_torque_rpm']} RPM | "
                   f"{float(r['max_abs_shape_error_pct_2000_6000']):.1f} % |")
    return "\n".join(out)


def point_block():
    p = json.load(open(D / "rom" / "point_3000.json"))
    keys = [("state", "estado"), ("mean_rpm", "rotação média (RPM)"), ("window_s", "janela (s)"),
            ("brake_mean_nm", "freio médio (N·m)"), ("brake_peak_nm", "freio de pico (N·m)"),
            ("brake_saturated_s", "tempo saturado (s)"), ("shaft_power_kw", "potência no eixo (kW)"),
            ("shaft_torque_nm", "torque no eixo (N·m)"), ("kinetic_over_brake", "|ΔE_cin|/W_freio"),
            ("energy_residual_rel", "resíduo de energia"), ("adv_mean_deg", "avanço médio (°)"),
            ("adv_min_deg", "avanço mín (°)"), ("adv_max_deg", "avanço máx (°)"),
            ("adv_std_deg", "desvio do avanço (°)"), ("lambda", "λ"), ("ram69_end", "RAM[69h] bruto (fim)"),
            ("inj_width_ms", "largura do pulso (ms)"), ("inj_freq_hz", "frequência dos pulsos (Hz)"),
            ("inj_duty", "duty do bico"), ("sparks", "centelhas na janela")]
    out = ["| Grandeza | Valor |", "|---|---|"]
    for k, name in keys:
        v = p[k]
        out.append(f"| {name} | {v if isinstance(v, str) else format(v, '.6g')} |")
    out.append(f"\nCódigo `{p['code_sha'][:10] or 'n/d'}`, ROM SHA-256 `{p['rom_sha256'][:16]}…`.")
    return "\n".join(out)


def sweep_block():
    rom = D / "rom"
    out = [(rom / "sweep_table.md").read_text().rstrip(), ""]
    for tdc in (117, 120, 123):
        rows = [r for r in load(rom / f"sweep_tdc{tdc}.csv") if r["state"] == "ACCEPTED"]
        p = max(rows, key=lambda r: float(r["shaft_power_kw"]))
        t = max(rows, key=lambda r: float(r["shaft_torque_nm"]))
        out.append(f"* PMS {tdc}°: {len(rows)}/10 pontos ACCEPTED; pico de potência "
                   f"{float(p['shaft_power_kw']):.2f} kW a {float(p['mean_rpm']):.0f} RPM; pico de torque "
                   f"{float(t['shaft_torque_nm']):.1f} N·m a {float(t['mean_rpm']):.0f} RPM.")
    return "\n".join(out)


def gap_block():
    iso = {int(float(r["rpm"])): r for r in load(D / "fase2" / "dyno_wot_e22.csv")}
    rows = load(D / "rom" / "sweep_tdc120.csv")
    out = ["| RPM | indicado ROM (N·m) | indicado isolado (N·m) | avanço ROM (°) | MBT isolado (°) | "
           "acessórios ROM (N·m) | eixo ROM (N·m) | freio isolado (N·m) |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        rpm = int(round(float(r["target_rpm"])))
        i = iso.get(rpm)
        if not i or r["state"] != "ACCEPTED":
            continue
        out.append(f"| {rpm} | {float(r['indicated_nm']):.1f} | {float(i['indicated_nm']):.1f} | "
                   f"{float(r['adv_mean_deg']):.1f} | {float(i['mbt_deg']):.1f} | "
                   f"{float(r['accessory_nm']):.1f} | {float(r['shaft_torque_nm']):.1f} | "
                   f"{float(i['torque_nm']):.1f} |")
    return "\n".join(out)


BLOCKS = {"CONV": convergence_block, "VEFIT": vefit_block, "POINT": point_block,
          "SWEEP": sweep_block, "GAP": gap_block}


def fill(path):
    text = Path(path).read_text()
    for name, fn in BLOCKS.items():
        pattern = re.compile(rf"(<!-- BEGIN:{name} -->\n).*?(<!-- END:{name} -->)", re.S)
        if pattern.search(text):
            text = pattern.sub(lambda m: m.group(1) + fn() + "\n" + m.group(2), text)
    Path(path).write_text(text)


if __name__ == "__main__":
    for target in sys.argv[1:] or [str(ROOT / "docs" / "SEVEL_DYNO_ROM.md")]:
        fill(target)
