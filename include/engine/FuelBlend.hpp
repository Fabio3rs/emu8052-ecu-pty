#pragma once

#include <stdexcept>

namespace engine {

// Provisional volume blend at 20 C; gasoline properties vary by formulation.
struct FuelBlend {
    double ethanol_volume_fraction = 0.0;

    static FuelBlend from_ethanol_percent(int percent) {
        if (percent < 0 || percent > 100)
            throw std::invalid_argument("invalid ethanol percentage");
        return {static_cast<double>(percent) / 100.0};
    }

    double density_kg_m3() const {
        return (1.0 - ethanol_volume_fraction) * 740.0 +
               ethanol_volume_fraction * 789.0;
    }
    double ethanol_mass_fraction() const {
        return ethanol_volume_fraction * 789.0 / density_kg_m3();
    }
    double stoichiometric_air_fuel_ratio() const {
        const double ethanol = ethanol_mass_fraction();
        return (1.0 - ethanol) * 14.7 + ethanol * 9.0;
    }
    double lower_heating_value_j_kg() const {
        const double ethanol = ethanol_mass_fraction();
        return (1.0 - ethanol) * 44e6 + ethanol * 26.8e6;
    }
};

} // namespace engine
