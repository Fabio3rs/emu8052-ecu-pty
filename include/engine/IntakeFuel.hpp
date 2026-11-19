#pragma once

#include "engine/physics/Volumetric.hpp"

namespace engine {

// Estimated mean-value parameters for the 1,580 cm³ four-stroke engine.
struct IntakeFuelParameters {
    double displacement_m3 = 0.001580;
    double manifold_volume_m3 = 0.0020;
    double ambient_pressure_pa = 100000.0;
    double ambient_temperature_c = 20.0;
    double volumetric_efficiency = 0.75;
    double throttle_max_area_m2 = 0.00030;
    double throttle_leak_area_m2 = 0.000001;
    double film_fraction = 0.25;
    // false: legacy constant volumetric_efficiency (manifold-referenced).
    // true: eta_v,m(N, p_m) = eta_v,WOT(N) * f_res(p_m)/f_res(p_WOT)  (F-18/F-22).
    bool ve_map = false;
    physics::EngineGeometry geometry{};
    physics::VeCurveParams ve_curve{};
    double wot_manifold_pressure_pa = 95000.0; // calibrado: MAP medio em plena carga
    double exhaust_pressure_pa = 100000.0;     // p_e (F-41 ligado na fase de contrapressao)
};

struct IntakeStep {
    double air_in_kg = 0.0; // Signed: negative is backflow to atmosphere.
    double air_to_cylinders_kg = 0.0;
    double fuel_to_cylinders_kg = 0.0;
};

class IntakeFuel {
  public:
    explicit IntakeFuel(IntakeFuelParameters parameters = {});

    IntakeStep step(double dt_s, double rpm, double angle_rad,
                    double air_temperature_c, double wall_temperature_c,
                    double injected_fuel_kg);

    double pressure_pa() const;
    // Four-stroke intake pumping work per crank revolution, as mean torque.
    double pumping_torque_nm() const;
    double air_mass_kg() const { return air_mass_kg_; }
    double fuel_film_kg() const { return fuel_film_kg_; }
    double fuel_vapor_kg() const { return fuel_vapor_kg_; }
    double injected_total_kg() const { return injected_total_kg_; }
    double fuel_delivered_total_kg() const { return fuel_delivered_total_kg_; }
    double air_in_total_kg() const { return air_in_total_kg_; }
    double air_delivered_total_kg() const { return air_delivered_total_kg_; }
    double initial_air_mass_kg() const { return initial_air_mass_kg_; }
    double last_air_in_kg_s() const { return last_air_in_kg_s_; }
    // Telemetry (goal section 4): air delivered to the cylinders and VE.
    double last_air_to_cylinders_kg_s() const { return last_air_cyl_kg_s_; }
    double last_ve_manifold() const { return last_ve_manifold_; }
    double last_ve_ambient() const { return last_ve_ambient_; }
    double air_temperature_c() const { return air_temperature_c_; }
    const IntakeFuelParameters &parameters() const { return parameters_; }

  private:
    IntakeFuelParameters parameters_;
    double air_temperature_c_;
    double initial_air_mass_kg_;
    double air_mass_kg_;
    double fuel_film_kg_ = 0.0;
    double fuel_vapor_kg_ = 0.0;
    double injected_total_kg_ = 0.0;
    double fuel_delivered_total_kg_ = 0.0;
    double air_in_total_kg_ = 0.0;
    double air_delivered_total_kg_ = 0.0;
    double last_air_in_kg_s_ = 0.0;
    double last_air_cyl_kg_s_ = 0.0;
    double last_ve_manifold_ = 0.0;
    double last_ve_ambient_ = 0.0;
};

} // namespace engine
