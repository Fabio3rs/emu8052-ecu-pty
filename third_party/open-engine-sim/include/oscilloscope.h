#ifndef ATG_ENGINE_SIM_OSCILLOSCOPE_H
#define ATG_ENGINE_SIM_OSCILLOSCOPE_H

#include "render_math.h"
#include "ui_math.h"

#include <cstddef>
#include <vector>

// Donor Oscilloscope sample window, detached from EngineSimApplication.
// The Lab passes these points to the donor GeometryGenerator path renderer.
class Oscilloscope {
  public:
    struct DataPoint {
        double x = 0.0;
        double y = 0.0;
    };

    Oscilloscope();
    void addDataPoint(double x, double y);
    void setBufferSize(std::size_t n);
    void reset();
    std::vector<Point> orderedPoints() const;
    std::size_t pointCount() const { return m_pointCount; }

    double m_xMin;
    double m_xMax;
    double m_yMin;
    double m_yMax;
    double m_dynamicallyResizeX;
    double m_dynamicallyResizeY;
    double m_lineWidth;
    bool m_drawReverse;
    bool m_drawZero;
    ysVector i_color;

  protected:
    std::vector<DataPoint> m_points;
    std::size_t m_writeIndex;
    std::size_t m_pointCount;
};

#endif /* ATG_ENGINE_SIM_OSCILLOSCOPE_H */
