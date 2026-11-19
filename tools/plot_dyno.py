#!/usr/bin/env python3
"""Plot the sevel-dyno full-load sweep with the goal targets overlaid.

Usage: plot_dyno.py docs/dyno_wot_e22.csv docs/dyno_wot_e0.csv docs/dyno_wot.png
Targets (GOAL_SEVEL_FISICA s.8): 133 N.m near 3000 rpm (125-133 band), 60.3 kW +-5 %
at 5750-6000 rpm, CEE power x1.1 +-8 % between 2000 and 6000 rpm. LLM-written (Claude).
"""
import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    with open(path) as handle:
        return list(csv.DictReader(handle))


e22, e0, out = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
col = lambda rows, key: [float(r[key]) for r in rows]
rpm = col(e22, "rpm")
fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))

ax[0].plot(rpm, col(e22, "torque_nm"), label="E22 (sim)", lw=2)
ax[0].plot(rpm, col(e0, "torque_nm"), "--", label="E0 (sim)")
ax[0].plot(rpm, col(e22, "expected_torque_nm"), ":", color="gray", label="CEE x1.1")
ax[0].fill_between([2750, 3250], 125, 133, color="green", alpha=0.2, label="alvo 125-133")
ax[0].set(title="Torque", xlabel="RPM", ylabel="N.m")

ax[1].plot(rpm, col(e22, "power_kw"), label="E22 (sim)", lw=2)
ax[1].plot(rpm, col(e0, "power_kw"), "--", label="E0 (sim)")
ax[1].plot(rpm, col(e22, "expected_power_kw"), ":", color="gray", label="CEE x1.1")
ax[1].fill_between([5750, 6000], 60.3 * 0.95, 60.3 * 1.05, color="green", alpha=0.25,
                   label="alvo 60,3 kW +-5 %")
ax[1].set(title="Potencia (82 cv = 60,3 kW)", xlabel="RPM", ylabel="kW")

ax[2].plot(rpm, col(e22, "ve_ambient"), label="VE ref. ambiente", lw=2)
ax[2].fill_between([2750, 3250], 0.90, 0.95, color="green", alpha=0.2,
                   label="F-24 perto de 3000 (0,90-0,95)")
ax[2].fill_between([5750, 6000], 0.76, 0.79, color="orange", alpha=0.35,
                   label="F-24 a 5750-6000 (0,76-0,79)")
ax[2].set(title="Eficiencia volumetrica", xlabel="RPM", ylabel="eta_v")

for a in ax:
    a.grid(alpha=0.3)
    a.legend(fontsize=8)
fig.suptitle("SEVEL 1.6 SPI - plena carga (sevel-dyno), planta calibrada")
fig.tight_layout()
fig.savefig(out, dpi=110)
print("wrote", out)
