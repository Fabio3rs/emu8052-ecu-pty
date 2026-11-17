#pragma once

namespace ecu_hw {

// CC3/P1.3-to-injector binding and active-low polarity are candidates.
struct InjectorStageParameters {
    // Single injector for four cylinders: 940 cc/min rated at 3 bar.
    // With 1 bar rail differential this gives ~402 g/min for gasoline.
    double rated_flow_m3_s = 940e-6 / 60.0;
    double rated_delta_pa = 300000.0;
    double fuel_density_kg_m3 = 740.0;
    double rail_absolute_pa = 200000.0;
    double outlet_absolute_pa = 100000.0; // Upstream of throttle, estimated.
    double dead_time_s = 0.0008;
    double nominal_battery_v = 12.5;
    double coil_resistance_ohm = 1.75; // Bosch service value; part not verified on car.
    double ballast_resistance_ohm = 3.1;
    double coil_inductance_h = 0.010; // Estimated; no part measurement yet.
    double pull_in_current_a = 0.75; // Estimated; below nominal current at dead time.
    bool active_low = true;
};

class Ma17InjectorStage {
  public:
    explicit Ma17InjectorStage(InjectorStageParameters parameters = {});
    void set_connected(bool connected) { connected_ = connected; }
    void reset_electrical_state();
    double step(bool cc3_pin_high, double dt_s, double battery_v);
    bool energized() const { return energized_; }
    unsigned long long pulse_count() const { return pulse_count_; }
    unsigned long long energized_ticks() const { return energized_ticks_; }
    double delivered_total_kg() const { return delivered_total_kg_; }
    double coil_current_a() const { return coil_current_a_; }

  private:
    InjectorStageParameters parameters_;
    bool connected_ = true;
    bool energized_ = false;
    double energized_time_s_ = 0.0;
    double coil_current_a_ = 0.0;
    double cached_dt_s_ = -1.0;
    double current_rise_fraction_ = 0.0;
    unsigned long long pulse_count_ = 0;
    unsigned long long energized_ticks_ = 0;
    double delivered_total_kg_ = 0.0;
};

} // namespace ecu_hw
