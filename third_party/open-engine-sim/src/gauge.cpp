#include "../include/gauge.h"

#include "../include/constants.h"

#include <algorithm>
#include <climits>
#include <cmath>

Gauge::Gauge() {
    m_thetaMin = static_cast<float>(constants::pi);
    m_thetaMax = 0.0f;
    m_min = m_max = 0.0f;
    m_maxMinorTick = INT_MAX;
    m_value = 0.0f;
    m_minorStep = 1;
    m_majorStep = 10;
    m_minorTickWidth = 1.0f;
    m_majorTickWidth = 2.0f;
    m_minorTickLength = 5.0f;
    m_majorTickLength = 10.0f;
    m_outerRadius = 0.0f;
    m_renderText = false;
    m_needleInnerRadius = 0.0f;
    m_needleOuterRadius = 0.0f;
    m_needleWidth = 1.0f;
    m_needlePosition = 0.0f;
    m_needleVelocity = 0.0f;
    m_needleMaxVelocity = 2.0f;
    m_needleKs = 1000.0f;
    m_needleKd = 25.0f;
    m_gamma = 1.0f;
}

void Gauge::reset(float value) {
    m_value = value;
    m_needlePosition =
        m_max > m_min ? std::pow(std::clamp((value - m_min) / (m_max - m_min),
                                            0.0f, 1.0f),
                                 m_gamma)
                      : 0.0f;
    m_needleVelocity = 0.0f;
}

float Gauge::angleForFraction(float fraction) const {
    // Donor Gauge::render: gamma transforms a dial fraction before the sweep.
    const float s = std::pow(std::clamp(fraction, 0.0f, 1.0f), m_gamma);
    return s * m_thetaMax + (1.0f - s) * m_thetaMin;
}

bool Gauge::isMajorTick(int offset) const {
    return m_majorStep > 0 && offset % m_majorStep == 0;
}

bool Gauge::showsTick(int offset) const {
    return isMajorTick(offset) ||
           (m_minorStep > 0 &&
            static_cast<long long>(offset) + m_minorStep <= m_maxMinorTick);
}

void Gauge::update(float dt) {
    if (m_max <= m_min || !std::isfinite(m_value) ||
        !std::isfinite(dt) || dt <= 0.0f)
        return;
    const float value = std::clamp(m_value, m_min, m_max);
    const float needle_s = std::pow((value - m_min) / (m_max - m_min), m_gamma);
    if (m_needleTimeConstant > 0.0f) {
        const float alpha = -std::expm1(-dt / m_needleTimeConstant);
        m_needlePosition += alpha * (needle_s - m_needlePosition);
        m_needleVelocity = 0.0f;
        return;
    }
    dt = std::clamp(dt, 0.0f, 0.05f);
    const float force = m_needleKs * (needle_s - m_needlePosition) -
                        m_needleKd * m_needleVelocity;
    m_needleVelocity = std::clamp(m_needleVelocity + force * dt,
                                  -m_needleMaxVelocity, m_needleMaxVelocity);
    m_needlePosition =
        std::clamp(m_needlePosition + m_needleVelocity * dt, 0.0f, 1.0f);
}
