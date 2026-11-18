#pragma once

struct CrankshaftSimulator;
struct em8051;
namespace engine {
class CrankDynamics;
class Drivetrain;
}

namespace ma17 {

void tick_crank_input(em8051 *cpu, long long tick, CrankshaftSimulator &sim);

struct PhysicalCrankInput {
    bool high = false;
    unsigned long long rising_edges = 0;
    unsigned long long falling_edges = 0;
    unsigned long long missing_positions = 0;
    int last_missing_position = -1;
};

void tick_physical_crank_input(em8051 *cpu, engine::CrankDynamics &crank,
                               PhysicalCrankInput &input, bool starter_engaged,
                               double combustion_torque_nm = 0.0,
                               double load_torque_nm = 0.0,
                               bool sensor_connected = true,
                               engine::Drivetrain *drivetrain = nullptr);

} // namespace ma17
