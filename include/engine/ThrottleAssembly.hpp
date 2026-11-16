#pragma once

namespace engine {

struct ThrottleParameters {
    double cable_radius_m = 0.025;
    double cable_free_play_m = 0.001;
    double maximum_angle_rad = 1.5707963267948966;
    double contact_on_gap_rad = 0.00174532925199433;  // 0.1 degree
    double contact_off_gap_rad = 0.00349065850398866; // 0.2 degree
};

// The idle switch is mounted on the actuator's movable throttle stop.
// The throttle presses it at rest; cable pull can lift the throttle away.
// Contact gap/hysteresis below are provisional, not measured on the car.
class ThrottleAssembly {
  public:
    explicit ThrottleAssembly(ThrottleParameters parameters = {});

    void set_cable_pull_m(double pull_m);
    void set_stop_angle_rad(double angle_rad);

    double cable_pull_m() const { return cable_pull_m_; }
    double cable_angle_rad() const { return cable_angle_rad_; }
    double stop_angle_rad() const { return stop_angle_rad_; }
    double angle_rad() const { return angle_rad_; }
    bool contact_closed() const { return contact_closed_; }

  private:
    void update_geometry();

    ThrottleParameters parameters_;
    double cable_pull_m_ = 0.0;
    double cable_angle_rad_ = 0.0;
    double stop_angle_rad_ = 0.0698131700797732; // 4 degrees, estimated
    double angle_rad_ = stop_angle_rad_;
    bool contact_closed_ = true;
};

} // namespace engine
