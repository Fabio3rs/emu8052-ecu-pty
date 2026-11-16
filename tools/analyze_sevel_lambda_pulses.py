"""Summarize effective CC3 injector pulses from a physical-run JSONL stream."""

import argparse
import json
import statistics
import sys
from collections import Counter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-tick", type=int, default=0)
    args = parser.parse_args()

    pulses = []
    start = None
    for line in sys.stdin:
        if not line.startswith('{"type":"cc3_pin"'):
            continue
        edge = json.loads(line)
        if not edge["high"]:
            start = edge
        elif start is not None:
            if start["tick"] >= args.from_tick:
                pulses.append((start["tick"], edge["tick"] - start["tick"],
                               start["lambda_flags"]))
            start = None

    if len(pulses) < 22:
        parser.error("need at least 22 complete CC3 pulses in the interval")
    widths = [pulse[1] for pulse in pulses]
    differences = [widths[i] - widths[i - 1]
                   for i in range(1, len(widths))]
    nonzero_magnitudes = [abs(delta) for delta in differences if delta]
    directions = [1 if delta > 0 else -1
                  for delta in differences if delta != 0]
    residuals = [width - statistics.fmean(widths[max(0, i - 10):i + 11])
                 for i, width in enumerate(widths)]
    residual_energy = sum(value * value for value in residuals)
    lag_one = (sum(residuals[i] * residuals[i - 1]
                   for i in range(1, len(residuals))) / residual_energy
               if residual_energy else 0.0)
    result = {
        "from_tick": args.from_tick,
        "pulses": len(pulses),
        "median_period_ticks": statistics.median(
            pulses[i][0] - pulses[i - 1][0]
            for i in range(1, len(pulses))),
        "width_ticks": {"min": min(widths),
                        "median": statistics.median(widths),
                        "max": max(widths)},
        "adjacent_equal": differences.count(0),
        "adjacent_increase": sum(delta > 0 for delta in differences),
        "adjacent_decrease": sum(delta < 0 for delta in differences),
        "median_nonzero_change_ticks": (statistics.median(nonzero_magnitudes)
                                        if nonzero_magnitudes else 0),
        "changes_at_most_one_tick": sum(abs(delta) == 1
                                        for delta in differences),
        "changes_at_least_ten_ticks": sum(abs(delta) >= 10
                                          for delta in differences),
        "nonzero_direction_flips": sum(directions[i] != directions[i - 1]
                                       for i in range(1, len(directions))),
        "lag_one_local_residual": round(lag_one, 4),
        "lambda_flags": dict(sorted(Counter(pulse[2] for pulse in pulses).items())),
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
