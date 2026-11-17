#include "lab/SevelGeometry.hpp"
#include "lab/SevelValves.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <limits>

namespace {

constexpr double pi = 3.14159265358979323846;

TEST(SevelGeometry, TopBottomAndOpposedCrankPins) {
    constexpr double radius = lab::SevelVisualGeometry::crank_radius_m;
    constexpr double rod = 0.14;
    const auto top = lab::sevel_cylinder_poses(0.0);
    EXPECT_NEAR(top[0].piston_pin_y_m, rod + radius, 1e-12);
    EXPECT_NEAR(top[3].piston_pin_y_m, rod + radius, 1e-12);
    EXPECT_NEAR(top[1].piston_pin_y_m, rod - radius, 1e-12);
    EXPECT_NEAR(top[2].piston_pin_y_m, rod - radius, 1e-12);

    const auto half_turn = lab::sevel_cylinder_poses(pi);
    EXPECT_NEAR(half_turn[0].piston_pin_y_m, rod - radius, 1e-12);
    EXPECT_NEAR(half_turn[1].piston_pin_y_m, rod + radius, 1e-12);

    const auto quarter_turn = lab::sevel_cylinder_poses(pi / 2.0);
    EXPECT_NEAR(quarter_turn[0].crank_pin_x_m, radius, 1e-12);
    EXPECT_NEAR(quarter_turn[1].crank_pin_x_m, -radius, 1e-12);
    EXPECT_NEAR(quarter_turn[0].piston_pin_y_m,
                std::sqrt(rod * rod - radius * radius), 1e-12);
}

TEST(SevelGeometry, RepeatsAcrossFullFourStrokeCycle) {
    for (double angle : {0.0, pi / 2.0, pi, 2.0 * pi - 0.001}) {
        const auto first = lab::sevel_cylinder_poses(angle);
        const auto next = lab::sevel_cylinder_poses(angle + 4.0 * pi);
        for (std::size_t i = 0; i < first.size(); ++i) {
            EXPECT_NEAR(first[i].crank_pin_x_m, next[i].crank_pin_x_m, 1e-12);
            EXPECT_NEAR(first[i].piston_pin_y_m, next[i].piston_pin_y_m, 1e-12);
            EXPECT_NEAR(first[i].rod_angle_rad, next[i].rod_angle_rad, 1e-12);
        }
    }
}

TEST(SevelGeometry, RodEndpointsAndPairPhasesRemainCoherentAcross720Degrees) {
    constexpr double rod = 0.14;
    constexpr double tolerance = 1e-12;
    for (int degree = 0; degree <= 720; ++degree) {
        const double angle = static_cast<double>(degree) * pi / 180.0;
        const auto poses = lab::sevel_cylinder_poses(angle);
        for (const auto &pose : poses) {
            const double end_x =
                pose.crank_pin_x_m + rod * std::sin(pose.rod_angle_rad);
            const double end_y =
                pose.crank_pin_y_m + rod * std::cos(pose.rod_angle_rad);
            EXPECT_NEAR(end_x, 0.0, tolerance) << degree;
            EXPECT_NEAR(end_y, pose.piston_pin_y_m, tolerance) << degree;
            EXPECT_NEAR(std::hypot(-pose.crank_pin_x_m,
                                   pose.piston_pin_y_m - pose.crank_pin_y_m),
                        rod, tolerance)
                << degree;
        }
        EXPECT_NEAR(poses[0].crank_pin_x_m, poses[3].crank_pin_x_m, tolerance);
        EXPECT_NEAR(poses[0].piston_pin_y_m, poses[3].piston_pin_y_m,
                    tolerance);
        EXPECT_NEAR(poses[1].crank_pin_x_m, poses[2].crank_pin_x_m, tolerance);
        EXPECT_NEAR(poses[1].piston_pin_y_m, poses[2].piston_pin_y_m,
                    tolerance);
    }
    const auto seam_start = lab::sevel_cylinder_poses(0.0);
    const auto seam_end = lab::sevel_cylinder_poses(4.0 * pi);
    for (std::size_t index = 0; index < seam_start.size(); ++index) {
        EXPECT_NEAR(seam_start[index].piston_pin_y_m,
                    seam_end[index].piston_pin_y_m, tolerance);
        EXPECT_NEAR(seam_start[index].rod_angle_rad,
                    seam_end[index].rod_angle_rad, tolerance);
    }
}

TEST(SevelGeometry, RejectsImpossibleDimensions) {
    lab::SevelVisualGeometry geometry;
    geometry.visual_estimate_rod_length_m = 0.02;
    EXPECT_THROW(lab::cylinder_pose(0.0, 1, geometry), std::invalid_argument);
    EXPECT_THROW(lab::cylinder_pose(std::numeric_limits<double>::quiet_NaN(), 1),
                 std::invalid_argument);
    EXPECT_THROW(lab::cylinder_pose(0.0, 5), std::invalid_argument);
}

TEST(SevelValves, FiringOrderAndManualWindows) {
    EXPECT_EQ(lab::firing_tdc_degrees[0], 0.0);
    EXPECT_EQ(lab::firing_tdc_degrees[2], 180.0);
    EXPECT_EQ(lab::firing_tdc_degrees[3], 360.0);
    EXPECT_EQ(lab::firing_tdc_degrees[1], 540.0);
    for (std::size_t cylinder = 0; cylinder < 4; ++cylinder) {
        const double tdc = lab::firing_tdc_degrees[cylinder];
        const auto lift = [cylinder](double degrees, lab::ValveKind kind) {
            return lab::valve_lift_fraction(degrees * pi / 180.0, cylinder,
                                            kind);
        };
        EXPECT_GT(lift(tdc + 250.0, lab::ValveKind::Exhaust), 0.0);
        EXPECT_EQ(lift(tdc + 250.0, lab::ValveKind::Intake), 0.0);
        EXPECT_GT(lift(tdc + 450.0, lab::ValveKind::Intake), 0.0);
        EXPECT_EQ(lift(tdc + 450.0, lab::ValveKind::Exhaust), 0.0);
        EXPECT_NEAR(lift(tdc + 450.0, lab::ValveKind::Intake),
                    lift(tdc + 1170.0, lab::ValveKind::Intake), 1e-12);
    }
}

TEST(SevelValves, FollowsConfiguredPhysicalTdcReference) {
    const double reference = 120.0 * pi / 180.0;
    const double open_angle = 570.0 * pi / 180.0;
    EXPECT_NEAR(
        lab::valve_lift_fraction(open_angle, 0, lab::ValveKind::Intake,
                                 reference),
        lab::valve_lift_fraction(450.0 * pi / 180.0, 0, lab::ValveKind::Intake),
        1e-12);
    EXPECT_EQ(lab::valve_lift_fraction(450.0 * pi / 180.0, 0,
                                       lab::ValveKind::Intake, reference),
              0.0);
    EXPECT_THROW(lab::valve_lift_fraction(
                     0.0, 0, lab::ValveKind::Intake,
                     std::numeric_limits<double>::quiet_NaN()),
                 std::invalid_argument);
}

} // namespace
