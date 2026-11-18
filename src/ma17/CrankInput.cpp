#include "ma17/CrankInput.hpp"

#include "CrankshaftSimulator.hpp"
#include "engine/CrankDynamics.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cstdio>
#include <cstdlib>

namespace ma17 {
namespace {

void capture_edge(em8051 *cpu, bool rising) {
    // P1.0 pin and latch are not separate here; physical wiring is unverified.
    if (((cpu->mSFR[0xC8 - 0x80] & 0x40u) != 0) != rising)
        return; // T2CON.I3FR selects the active INT3/CC0 edge.
    if ((cpu->mSFR[0xC1 - 0x80] & 0x03u) == 0x01u) {
        cpu->mSFR[0xCA - 0x80] = cpu->mSFR[0xCC - 0x80];
        cpu->mSFR[0xCB - 0x80] = cpu->mSFR[0xCD - 0x80];
    }
    cpu->mSFR[0xC0 - 0x80] |= 0x04u;
}

} // namespace

static void process_crank_falling_edge(em8051 *cpu, long long tick,
                                       CrankshaftSimulator &sim) {
    // Capture only physical teeth, not the two missing positions.
    if (!sim.gap_detected && !sim.capture_done_this_pulse) {
        unsigned char p1 = cpu->mSFR[0x90 - 0x80];
        static int traced_edges = 0;
        if (getenv("MA17_TRACE_PC") && traced_edges++ < 8) {
            fprintf(stderr,
                    "[CRANK-EDGE] instr=%lld tooth=%d PC=%04X EA=%d "
                    "P1=%02X CCEN=%02X T2CON=%02X IEN1=%02X "
                    "IRCON=%02X C4=%02X TH2:TL2=%02X:%02X\n",
                    tick, sim.current_tooth, cpu->mPC,
                    (cpu->mSFR[0xA8 - 0x80] & 0x80u) != 0, p1,
                    cpu->mSFR[0xC1 - 0x80], cpu->mSFR[0xC8 - 0x80],
                    cpu->mSFR[0xB8 - 0x80], cpu->mSFR[0xC0 - 0x80],
                    cpu->mUpperData[0xC4 - 0x80], cpu->mSFR[0xCD - 0x80],
                    cpu->mSFR[0xCC - 0x80]);
        }
        cpu->mSFR[0x90 - 0x80] = p1 & 0xFEu;
        capture_edge(cpu, false);
        sim.capture_done_this_pulse = true;
    }

    sim.pulse_active = false;
    sim.int0_fired_this_pulse = false;
    sim.capture_done_this_pulse = false;
}

static void process_crank_rising_edge(em8051 *cpu, long long tick,
                                      CrankshaftSimulator &sim) {
    sim.current_tooth = (sim.current_tooth + 1) % sim.POSITIONS_TOTAL;
    sim.gap_detected = sim.is_in_gap();
    static int teeth_in_revolution = 0;
    static int gaps_in_revolution = 0;
    static int revolutions = 0;
    if (sim.current_tooth == 0) {
        // Fiat 60-2 reference for phase plots; 4T stroke phase is unknown.
        if (std::getenv("MA17_TRACE_CRANK_PHASE"))
            fprintf(stderr, "[CRANK-PHASE] tick=%lld tooth=0 rpm=%d\n",
                    tick, sim.target_rpm);
        // The first wrap omits the initial position 0.
        if (revolutions++ > 0 && std::getenv("MA17_TRACE_PC") &&
            revolutions <= 129)
            fprintf(
                stderr,
                "[CRANK-REV] rpm=%d teeth=%d gaps=%d ticks_per_tooth=%lld\n",
                sim.target_rpm, teeth_in_revolution, gaps_in_revolution,
                sim.pulse_interval_instrs);
        teeth_in_revolution = 0;
        gaps_in_revolution = 0;
    }

    // Positions 58 and 59 have no physical tooth or capture event.
    if (sim.gap_detected) {
        ++gaps_in_revolution;
        sim.pulse_active = true;
        sim.pulse_end_instr = tick + sim.pulse_width_instrs;
        sim.last_pulse_instr = tick;
        sim.int0_fired_this_pulse = true;
        return;
    }

    ++teeth_in_revolution;
    cpu->mSFR[0x90 - 0x80] |= 0x01u;
    capture_edge(cpu, true);
    sim.int0_fired_this_pulse = true;
    sim.pulse_active = true;
    sim.pulse_end_instr = tick + sim.pulse_width_instrs;
    sim.last_pulse_instr = tick;
}

void tick_crank_input(em8051 *cpu, long long tick, CrankshaftSimulator &sim) {
    if (sim.should_pulse_go_low(tick)) {
        process_crank_falling_edge(cpu, tick, sim);
        return;
    }
    if (sim.should_pulse_go_high(tick))
        process_crank_rising_edge(cpu, tick, sim);
}

void tick_physical_crank_input(em8051 *cpu, engine::CrankDynamics &crank,
                               PhysicalCrankInput &input,
                               bool starter_engaged,
                               double combustion_torque_nm,
                               double load_torque_nm,
                               bool sensor_connected,
                               engine::Drivetrain *drivetrain) {
    const bool crossed =
        crank.step(starter_engaged, combustion_torque_nm, load_torque_nm,
                   0.0, drivetrain);
    if (crossed &&
        crank.wheel_position() >= engine::CrankDynamics::physical_teeth) {
        ++input.missing_positions;
        input.last_missing_position = crank.wheel_position();
    }
    if (!sensor_connected) {
        // Open wire: the wheel still turns, but no tooth edge reaches CC0.
        cpu->mSFR[0x90 - 0x80] &= 0xFEu;
        input.high = false;
        return;
    }
    if (crossed &&
        crank.wheel_position() < engine::CrankDynamics::physical_teeth) {
        cpu->mSFR[0x90 - 0x80] |= 0x01u;
        capture_edge(cpu, true);
        input.high = true;
        ++input.rising_edges;
    }
    constexpr double half_position_rad =
        3.14159265358979323846 / engine::CrankDynamics::wheel_positions;
    if (input.high && crank.wheel_phase_rad() >= half_position_rad) {
        cpu->mSFR[0x90 - 0x80] &= 0xFEu;
        capture_edge(cpu, false);
        input.high = false;
        ++input.falling_edges;
    }
}

} // namespace ma17
