#pragma once

#include <SDL3/SDL.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <string>

namespace lab {

inline constexpr bool valid_ui_scale(int percent) {
    return percent == 0 || percent == 100 || percent == 150 || percent == 200;
}

struct LabUiPreferences {
    int scale_percent = 0;
    float left_fraction = 0.24f;
    float right_fraction = 0.66f;
    int mode = 0;
    float scope_fraction = -1.0f;
    int scope_mode = 1;
    int analog_group = 0;
    long long analog_span_ticks = 5LL * 990000;
    long long digital_span_ticks = 2LL * 990000;
    unsigned int digital_channel_mask = 15;
    int camera_saved = 0;
    int view_mode = 0;
    float shaft_zoom = 0.78f;
    float shaft_pan_x = 0.0f;
    float shaft_pan_y = 0.0f;
    float axial_zoom = 0.78f;
    float axial_pan_x = 0.0f;
    float axial_pan_y = 0.0f;
    int font_percent = 100;
    int display_units = 0;
    float camera_pane_width = 0.0f;
    float camera_scene_height = 0.0f;
};

inline bool valid_ui_preferences(const LabUiPreferences &value) {
    return valid_ui_scale(value.scale_percent) &&
           std::isfinite(value.left_fraction) &&
           std::isfinite(value.right_fraction) &&
           value.left_fraction > 0.0f && value.left_fraction < 1.0f &&
           value.right_fraction > value.left_fraction &&
           value.right_fraction < 1.0f &&
           value.mode >= 0 && value.mode <= 2 &&
           std::isfinite(value.scope_fraction) &&
           (value.scope_fraction == -1.0f ||
            (value.scope_fraction > 0.0f && value.scope_fraction < 1.0f)) &&
           value.scope_mode >= 0 && value.scope_mode <= 1 &&
           value.analog_group >= 0 && value.analog_group < 11 &&
           value.analog_span_ticks >= 990000LL &&
           value.analog_span_ticks <= 300LL * 990000LL &&
           value.digital_span_ticks >= 9900LL &&
           value.digital_span_ticks <= 4950000LL &&
           value.digital_channel_mask <= 15 &&
           value.camera_saved >= 0 && value.camera_saved <= 1 &&
           value.view_mode >= 0 && value.view_mode <= 3 &&
           std::isfinite(value.shaft_zoom) &&
           std::isfinite(value.axial_zoom) &&
           value.shaft_zoom >= 0.5f && value.shaft_zoom <= 3.0f &&
           value.axial_zoom >= 0.5f && value.axial_zoom <= 3.0f &&
           std::isfinite(value.shaft_pan_x) &&
           std::isfinite(value.shaft_pan_y) &&
           std::isfinite(value.axial_pan_x) &&
           std::isfinite(value.axial_pan_y) &&
           std::abs(value.shaft_pan_x) <= 1.0f &&
           std::abs(value.axial_pan_x) <= 1.0f &&
           std::abs(value.shaft_pan_y) <= 0.5f &&
           std::abs(value.axial_pan_y) <= 0.5f &&
           (value.font_percent == 100 || value.font_percent == 105 ||
            value.font_percent == 110) &&
           (value.display_units == 0 || value.display_units == 1) &&
           std::isfinite(value.camera_pane_width) &&
           std::isfinite(value.camera_scene_height) &&
           value.camera_pane_width >= 0.0f &&
           value.camera_pane_width <= 4096.0f &&
           value.camera_scene_height >= 0.0f &&
           value.camera_scene_height <= 4096.0f;
}

inline std::filesystem::path ui_preferences_path() {
    char *directory = SDL_GetPrefPath("Fabio3rs", "Sevel MA17 Lab");
    if (!directory)
        return {};
    const std::filesystem::path path =
        std::filesystem::path(directory) / "presentation.txt";
    SDL_free(directory);
    return path;
}

inline LabUiPreferences load_ui_preferences() {
    const auto path = ui_preferences_path();
    if (path.empty())
        return {};
    std::ifstream input(path);
    std::string version;
    LabUiPreferences value;
    std::string extra;
    if (!(input >> version >> value.scale_percent))
        return {};
    if (version == "v9" || version == "v8" || version == "v7" || version == "v6" || version == "v5" || version == "v4" || version == "v3" ||
        version == "v2") {
        if (!(input >> value.left_fraction >> value.right_fraction))
            return {};
        if ((version == "v9" || version == "v8" || version == "v7" || version == "v6" || version == "v5" || version == "v4" ||
             version == "v3") &&
            !(input >> value.mode))
            return {};
        if ((version == "v9" || version == "v8" || version == "v7" || version == "v6" || version == "v5" || version == "v4") &&
            !(input >> value.scope_fraction))
            return {};
        if ((version == "v9" || version == "v8" || version == "v7" || version == "v6" || version == "v5") &&
            !(input >> value.scope_mode >> value.analog_group >>
              value.analog_span_ticks >> value.digital_span_ticks >>
              value.digital_channel_mask))
            return {};
        if ((version == "v9" || version == "v8" || version == "v7" || version == "v6") &&
            !(input >> value.camera_saved >> value.view_mode >>
              value.shaft_zoom >> value.shaft_pan_x >> value.shaft_pan_y >>
              value.axial_zoom >> value.axial_pan_x >> value.axial_pan_y))
            return {};
        if ((version == "v9" || version == "v8" || version == "v7") &&
            !(input >> value.font_percent))
            return {};
        if ((version == "v9" || version == "v8") &&
            !(input >> value.display_units))
            return {};
        if (version == "v9" &&
            !(input >> value.camera_pane_width >> value.camera_scene_height))
            return {};
    } else if (version != "v1") {
        return {};
    }
    return valid_ui_preferences(value) && !(input >> extra) ? value
                                                             : LabUiPreferences{};
}

inline bool save_ui_preferences(const LabUiPreferences &value) {
    if (!valid_ui_preferences(value))
        return false;
    const auto path = ui_preferences_path();
    if (path.empty())
        return false;
    std::ofstream output(path, std::ios::trunc);
    output << "v9 " << value.scale_percent << ' '
           << value.left_fraction << ' ' << value.right_fraction << ' '
           << value.mode << ' ' << value.scope_fraction << ' '
           << value.scope_mode << ' ' << value.analog_group << ' '
           << value.analog_span_ticks << ' ' << value.digital_span_ticks << ' '
           << value.digital_channel_mask << ' '
           << value.camera_saved << ' ' << value.view_mode << ' '
           << value.shaft_zoom << ' ' << value.shaft_pan_x << ' '
           << value.shaft_pan_y << ' ' << value.axial_zoom << ' '
           << value.axial_pan_x << ' ' << value.axial_pan_y << ' '
           << value.font_percent << ' ' << value.display_units << ' '
           << value.camera_pane_width << ' '
           << value.camera_scene_height << '\n';
    output.flush();
    return output.good();
}

} // namespace lab
