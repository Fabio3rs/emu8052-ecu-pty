#pragma once

struct CrankshaftSimulator {
    // Fiat Tipo MA1.7 harness only: 11.88 MHz and P1.0 crank stimulus.
    // Renault MA1.7 hardware and clock require a separately verified profile.
    // Historical *_instrs names below denote emulated machine-cycle ticks.
    static constexpr int TEETH_COUNT = 58;
    static constexpr int POSITIONS_TOTAL = 60;
    static constexpr double DEGREES_PER_POSITION = 6.0;
    // Pulse width is calculated dynamically as 50% of pulse_interval
    // (set in update_pulse_interval based on RPM)
    long long pulse_width_instrs = 500; // Default, updated dynamically

    // Fiat profile startup delay: 5 seconds at 990,000 ticks/s.
    long long startup_delay_instrs = 5LL * 990000LL;

    int target_rpm = 1000;
    long long last_pulse_instr = 0;
    long long pulse_interval_instrs = 0;
    long long pulse_end_instr = 0; // When to pull signal LOW
    int current_tooth = 0;
    bool gap_detected = false;
    bool pulse_active = false;            // Track if pulse is HIGH
    bool int0_fired_this_pulse = false;   // Track if INT0 already fired
    bool capture_done_this_pulse = false; // Track if falling edge capture done
    bool enabled = false;                 // Delay before starting pulses
    bool startup_message_shown = false;   // Show message only once

    // =======================================================================
    // Debug Logging Rate-Limiting
    // =======================================================================
    // NOTE: IRCON.2 is now set on EVERY capture (required for firmware polling).
    // This rate-limiting is ONLY for debug logging to avoid console spam.
    //
    // IRCON.2 behavior:
    // - Set on EVERY falling edge capture (hardware behavior)
    // - Firmware Timer0 ISR polls IRCON.2 at 0x07CE to advance state machine
    // - State: 0x00 → 0x10 (after seeing IRCON.2=1) → 0x20 → normal processing
    //
    // Rate = 10: Log every 10th capture (~97 logs/sec at 1000 RPM)
    // =======================================================================
    int iex3_fire_interval = 10;  // Log every N pulses (1=every pulse)
    int pulses_since_iex3 = 0;    // Counter for rate-limiting

    // Check if we should log this capture (rate-limited for console readability)
    // NOTE: IRCON.2 is set in main.cpp for EVERY capture, regardless of this
    bool should_fire_iex3() {
        pulses_since_iex3++;
        if (pulses_since_iex3 >= iex3_fire_interval) {
            pulses_since_iex3 = 0;
            return true;
        }
        return false;
    }

    void update_pulse_interval(long long cpu_freq_hz) {
        pulse_interval_instrs =
            (60LL * cpu_freq_hz) / (target_rpm * POSITIONS_TOTAL);
        // 50% duty cycle: pulse HIGH for half the interval
        pulse_width_instrs = pulse_interval_instrs / 2;
    }

    // Check if startup delay has elapsed and enable if so
    bool check_and_enable(long long current_instr) {
        if (!enabled && current_instr >= startup_delay_instrs) {
            enabled = true;
            last_pulse_instr = current_instr; // Start timing from now
            return true; // Just enabled
        }
        return false;
    }

    bool should_pulse_go_high(long long current_instr) {
        if (!enabled) return false;
        return (current_instr - last_pulse_instr) >= pulse_interval_instrs &&
               !pulse_active;
    }

    bool should_pulse_go_low(long long current_instr) {
        if (!enabled) return false;
        return pulse_active && (current_instr >= pulse_end_instr);
    }

    bool is_in_gap() { return (current_tooth >= 58); }
};
