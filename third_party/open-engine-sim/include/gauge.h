#ifndef ATG_ENGINE_SIM_GAUGE_H
#define ATG_ENGINE_SIM_GAUGE_H

#include "render_math.h"
#include "ui_math.h"

#include <algorithm>
#include <cstddef>
#include <vector>

// Adapted from the donor Gauge: presentation is supplied by the Lab's SDL
// renderer, while this class retains the donor's range and needle dynamics.
class Gauge {
  public:
    struct Band {
        ysVector color = ysMath::Constants::One;
        float start = 0.0f;
        float end = 0.0f;
        float width = 0.0f;
        float radial_offset = 0.0f;
        float shorten_start = 0.0f;
        float shorten_end = 0.0f;
    };

    Gauge();
    void update(float dt);
    void reset(float value);
    float needlePosition() const { return m_needlePosition; }

    void setBandCount(int bands) {
        m_bands.resize(static_cast<std::size_t>(std::max(0, bands)));
    }
    void setBand(const Band &band, int index) {
        m_bands.at(static_cast<std::size_t>(index)) = band;
    }
    const std::vector<Band> &bands() const { return m_bands; }

    float m_value;
    float m_thetaMin;
    float m_thetaMax;
    float m_min;
    float m_max;
    int m_maxMinorTick;
    float m_gamma;
    int m_minorStep;
    int m_majorStep;
    float m_minorTickWidth;
    float m_majorTickWidth;
    float m_minorTickLength;
    float m_majorTickLength;
    float m_outerRadius;
    float m_needleInnerRadius;
    float m_needleOuterRadius;
    float m_needleWidth;
    float m_needleMaxVelocity;
    float m_needleKs;
    float m_needleKd;
    bool m_renderText;
    Point m_center;

  protected:
    float m_needlePosition;
    float m_needleVelocity;
    std::vector<Band> m_bands;
};

#endif /* ATG_ENGINE_SIM_GAUGE_H */
