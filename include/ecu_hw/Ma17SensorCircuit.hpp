#pragma once

namespace ecu_hw {

// Scanner fit and pull-ups are provisional for the Fiat ECU board.
struct SensorCircuitParameters {
    double reference_v = 5.0;
    double air_pullup_ohm = 2661.0;
    double coolant_pullup_ohm = 3004.0;
    double battery_v = 12.5;
    double battery_divider_ratio = 0.26;
    // Scanner assumes 3.9 mV per RAM65 count; the modeled 5 V/8-bit ADC
    // gives about 19.5 mV per count without conditioning. Gain 5 is a
    // comparison hypothesis, not a measured Fiat board property.
    double lambda_adc_gain = 1.0;
};

class Ma17SensorCircuit {
  public:
    explicit Ma17SensorCircuit(SensorCircuitParameters parameters = {});

    static double ntc_resistance_ohm(double temperature_c);
    double air_voltage(double temperature_c) const;
    double coolant_voltage(double temperature_c) const;
    double supply_voltage() const { return parameters_.battery_v; }
    double battery_voltage() const;
    double lambda_adc_voltage(double sensor_v) const;

  private:
    double divider_voltage(double resistance_ohm, double pullup_ohm) const;
    SensorCircuitParameters parameters_;
};

} // namespace ecu_hw
