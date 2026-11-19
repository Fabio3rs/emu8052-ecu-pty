#!/bin/sh
# Isolated plant (no ROM) at the ambient air temperature of the ROM runs; hypothesis check only.
# usage: power_gap_isolated.sh <sevel-dyno> <outdir>
mkdir -p "$2"
for amb in 20 36; do
  "$1" --ethanol 22 --rpm-min 1500 --rpm-max 6000 --rpm-step 1500 --throttle-deg 90 \
    --throttle-leak-mm2 9 --ambient-c $amb --out "$2/isolated_amb$amb.csv" >/dev/null 2>&1
done
