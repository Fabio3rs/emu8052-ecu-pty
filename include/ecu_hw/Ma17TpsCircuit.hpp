#pragma once

namespace ecu_hw {

// Provisional Fiat G electrical transfer. Only the 4-degree pair is anchored
// to an observed valid ADC0/ADC6 stimulus; slopes need bench measurements.
struct TpsCircuitParameters {
    double reference_v = 5.0;
    double rest_angle_rad = 0.0698131700797732;
    double track1_rest_v = 1.8572825024437928; // ADC6 = 95 * 4 / 1023 * 5
    double track1_slope_v_per_rad = 5.73;
    double track1_end_rad = 0.4188790204786391; // 24 degrees
    double track2_rest_v = 0.7820136852394917;  // ADC0 = 40 * 4 / 1023 * 5
    double track2_low_slope_v_per_rad = 3.93;
    double track2_transition_rad = 0.3141592653589793; // 18 degrees
    double track2_high_slope_v_per_rad = 2.23;
    double track2_overlap_end_rad = 0.4188790204786391; // 24 degrees
    double track2_wide_slope_v_per_rad = 2.23;

    // Engineering fit to published MA1.7 bench points: track 1 is about
    // 0.25 V closed, 1 V at the estimated 4-degree idle stop, and 4.65 V
    // at 24 degrees. Track 2 starts near 18 degrees and reaches 4.5 V
    // at 90 degrees. The overlap fit also gives about 0.55 V on track 2
    // when track 1 reaches 4.5 V, as reported in the bench procedure.
    // The fit is not a measurement of this particular Fiat throttle body.
    static TpsCircuitParameters bench_typical() {
        TpsCircuitParameters parameters;
        parameters.track1_rest_v = 1.0;
        parameters.track1_slope_v_per_rad = 10.456902296;
        parameters.track2_rest_v = 0.0;
        parameters.track2_low_slope_v_per_rad = 0.0;
        parameters.track2_high_slope_v_per_rad = 6.0;
        parameters.track2_wide_slope_v_per_rad = 3.361230291;
        return parameters;
    }
};

class Ma17TpsCircuit {
  public:
    explicit Ma17TpsCircuit(TpsCircuitParameters parameters = {});
    double track1_voltage(double angle_rad) const; // ADC6 → IRAM 66h
    double track2_voltage(double angle_rad) const; // ADC0 → IRAM 60h
    double reference_voltage() const { return parameters_.reference_v; }

  private:
    TpsCircuitParameters parameters_;
};

} // namespace ecu_hw
