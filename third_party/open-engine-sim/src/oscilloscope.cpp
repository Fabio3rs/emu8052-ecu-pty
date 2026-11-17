#include "../include/oscilloscope.h"

#include <cmath>

Oscilloscope::Oscilloscope() {
    m_xMin = m_xMax = 0.0;
    m_yMin = m_yMax = 0.0;
    m_lineWidth = 1.0;
    m_writeIndex = 0;
    m_pointCount = 0;
    m_drawReverse = true;
    m_drawZero = true;
    m_dynamicallyResizeX = false;
    m_dynamicallyResizeY = true;
    i_color = ysMath::Constants::One;
}

void Oscilloscope::setBufferSize(std::size_t n) {
    m_points.assign(n, {});
    reset();
}

void Oscilloscope::reset() {
    m_writeIndex = 0;
    m_pointCount = 0;
}

void Oscilloscope::addDataPoint(double x, double y) {
    if (m_points.empty())
        return;
    m_points[m_writeIndex] = {x, y};
    m_writeIndex = (m_writeIndex + 1) % m_points.size();
    m_pointCount =
        m_pointCount >= m_points.size() ? m_points.size() : m_pointCount + 1;

    if (m_dynamicallyResizeY) {
        if (y + std::abs(0.1 * y) >= m_yMax)
            m_yMax = y + std::abs(0.1 * y);
        else if (y - std::abs(0.1 * y) <= m_yMin)
            m_yMin = y - std::abs(0.1 * y);
    }
    if (m_dynamicallyResizeX) {
        if (x + std::abs(0.1 * x) >= m_xMax)
            m_xMax = x + std::abs(0.1 * x);
        else if (x - std::abs(0.1 * x) <= m_xMin)
            m_xMin = x - std::abs(0.1 * x);
    }
}

std::vector<Point> Oscilloscope::orderedPoints() const {
    std::vector<Point> result;
    result.reserve(m_pointCount);
    if (m_points.empty())
        return result;
    const std::size_t start =
        (m_writeIndex + m_points.size() - m_pointCount) % m_points.size();
    for (std::size_t i = 0; i < m_pointCount; ++i) {
        const auto &point = m_points[(start + i) % m_points.size()];
        result.emplace_back(static_cast<float>(point.x),
                            static_cast<float>(point.y));
    }
    return result;
}
