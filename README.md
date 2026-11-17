# emu8051-tty: Automotive ECU Emulator with PTY Interface

A C++20 project integrating the [emu8051](https://github.com/jarikomppa/emu8051) 8051/8052 microcontroller emulator with a PTY (pseudo-terminal) interface for testing and development of automotive K-line diagnostic protocols.

**Current Scope:** Specialized emulation for **Bosch Motronic MA1.7 ECU (Siemens SAB 80C517)** with Fiat Tipo 1.6ie firmware.

**Target Hardware:** Bosch Motronic MA1.7 (Siemens SAB 80C517)
**Supported Firmware:** Fiat Tipo 1.6ie (32KB ROM, type code 27C256)
**Protocol:** ISO 9141-2 K-line @ 4800 8N1
**Implementation:** Cycle-accurate UART timing and 5-baud slow-init support

## SEVEL MA1.7 Lab (experimental)

The optional `sevel-ma17-lab` runs the original Fiat ROM with the repository's
SEVEL physical model in one session. Its SDL3 window shows a four-cylinder
SOHC scene with imported piston and connecting rod meshes and a longitudinal
crankshaft drawing driven by the physical crank, RPM/TPS/lambda gauges, and live
CC3/P5.0/P5.1 traces. The imported Open Engine Simulator synthesizer produces
sound from the cossimulation's combustion events. The ECU ROM is user supplied
and is not included in the build.
The trace labels show the last complete high interval of each observed pin in
milliseconds; `H --` means no complete interval is available.
Pedal pull and applied resistant torque come from the physical snapshot; the
LOAD button reflects a load already active in a supplied physical scenario.
The status panel shows modeled manifold fuel film and vapor in milligrams;
these states continue to change during key-off coasting and cooldown.
Live PCM synthesis runs on a separate worker thread. Playback pauses with the
simulation and above 1× speed; the window reports dropped samples and empty
audio queue observations. The 1× session uses deadline pacing so batch CPU
work counts toward virtual time. Offline WAV capture keeps the original event
timing.
An original-ROM regression checks byte-identical idle WAVs, a stronger waveform
after a pedal step, and silence with the key off; see the Lab progress ledger.

```sh
cmake -S . -B build-lab -DENABLE_SEVEL_MA17_LAB=ON -DENABLE_TESTS=ON
cmake --build build-lab --parallel 4
./build-lab/sevel-ma17-lab path/to/FiatTipo_MA17_dump_27c256.bin --live --bench-preset
```

The Lab needs SDL3 3.2 or newer. CMake uses an installed SDL3, or fetches the
pinned 3.2.8 source. An existing local SDL3 build can be selected with
`-DSDL3_DIR=/path/to/SDL3Config-directory`. Builds with the Lab option off do
not need SDL3. For an offline headless build, add
`-DENABLE_SEVEL_MA17_LAB_GUI=OFF`. The GUI also needs ZLIB, FreeType and Python 3
for hash-checked restoration of the donor GPU shader binaries. CMake copies
the packaged donor mesh, Silkscreen font, shaders and font license into
`build-lab/assets/` beside the executable. Keep that directory with the
binary when moving the GUI build.

`--bench-preset` selects the tested warm candidate setup: ADC7 1232 mV,
P4.6 idle contact, P1.5/P1.6 idle bridge, 90 °C coolant, 5 mrad idle stop,
9 mm² throttle leak and lambda ADC gain 5. These are simulation bindings and
estimates, not a verified Fiat wiring/calibration. Explicit values for those
options override the preset; omit it to run the raw physical scenario. The
startup log prints `[LAB-BENCH]` and the window marks the candidate setup when
the preset is active. Use the same preset
for headless capture and control-trace replay. The no-load warm preset ran at
about 1,507 rpm at 12 million ticks in one regression; it is a functional
starting setup, not a calibrated 850 rpm idle. The LOAD control applies
resistant torque after the motor catches.

The live window starts with the key off: press K, then hold S to crank. Space
pauses; arrows adjust pedal pull; L toggles 24 Nm load; +/- changes speed; M
mutes audio; [ and ] adjust volume. The mouse wheel zooms the mechanical
scene, middle-button drag pans it, R resets the view, and Esc closes.
For a warm restart in the tested physical scenario, turn LOAD off while
cranking and reapply it after the engine catches.
At windows at least 900×620, the nine buttons below the engine provide key,
momentary starter, pedal, load, pause, speed and mute controls. A saved control
trace records button actions at their applied simulation ticks; replay locks
the physical controls while leaving pause, speed and mute available.
Click the CC3, P5.0 or P5.1 label in the oscilloscope to hide or restore that
ECU pin trace. These display selections do not change the saved control trace.
The starter releases if the window loses focus.
The status and candidate-lamp labels shorten in a 900×620 window.
The window shows modeled TPS1/TPS2 voltages, lambda sensor voltage, recent RPM
and lambda trends, and a candidate MA1.7 lamp indicator. A brief amber cross
marks a combustion event at its cylinder; a red cross marks a misfire. These
markers are visual afterglow from timestamped ROM/engine events, while the
oscilloscope keeps the actual pin pulse widths. `--auto-start`
restores the 495,000-tick
automatic starter demo. The Lab also
supports `--headless --capture-tick N --capture-svg frame.svg
--capture-wav audio.wav`. `--screenshot frame.png` saves one SDL frame when
libpng is available;
`--window-frames N` bounds a GUI verification run. `--live --gpu-preview` opens
the donor SDL GPU mechanical scene in a second window when a GPU backend is
available. SDL chooses the main window's renderer; the startup log prints
`[LAB-VIDEO] renderer=...`. If that renderer cannot initialize, the Lab tries
SDL software rendering and reports the error. The audio startup log prints
`[LAB-AUDIO] stream_open=1 driver=...` when SDL opens a playback stream.
On a machine with graphics and sound hardware, run the command above with
`--gpu-preview`, then press K and hold S to start. Check both windows, listen
through acceleration and deceleration, and inspect the displayed audio drop
and queue counts. `[LAB-GPU] preview_ready=1` confirms GPU initialization;
the stream log confirms opening, while audible output needs direct listening.
For repeatability checks, `--live --no-audio` skips the SDL audio stream and
`--frame-delay-ms N` sets the GUI delay (1–1000 ms, default 16). A bounded GUI
run exits when its simulation reaches `--stop-ticks`. Live and headless replay
print `[LAB-STATE]` with the final tick, physical/ECU state fingerprint,
ordered event fingerprint and overflow count; these fingerprints are diagnostic
64-bit FNV-1a values, not cryptographic hashes.

Use `--live --save-controls trace.txt` to save the applied tick, key, starter,
pedal and load commands. Run again with `--live --replay-controls trace.txt`
and the same ROM and physical scenario options to reproduce them. New traces
record the ROM size, a 64-bit content fingerprint and the physical scenario
arguments; replay rejects a mismatch before starting. Older v1 traces remain
readable but have no scenario check. Physical controls are locked during replay.
Pause and speed affect wall time only and are not stored in the trace. For a
repeatable SVG and WAV without SDL, use
`--headless --replay-controls trace.txt --capture-tick N --capture-svg frame.svg
--capture-wav audio.wav`; if supplied, `--stop-ticks` must equal N.

The current scene uses documented bore, stroke, firing order and valve timing;
rod length, valve lift and outer geometry are explicitly drawing estimates.
The donor's mechanical meshes, Silkscreen font, shader state, adapted Gauge and
Oscilloscope objects, audio filters and synthesizer are integrated. The full
donor impulse WAV is archived losslessly; the runtime uses its first 2048
samples (99.69% of the source energy). The original donor GPU backend is
available as an optional scene preview; the primary UI uses SDL's selected
2D renderer. Two labeled axial crank views show the 1/4 and 2/3 pairs at
opposed angles beside the longitudinal four-cylinder view.
See
[the Lab progress ledger](docs/SEVEL_MA17_LAB_PROGRESS.md) and
[third-party notices](THIRD_PARTY_NOTICES.md) for verified tests and provenance.

### Project Status
**Type:** Personal research and testing project
**Code Availability:** Public for backup and community contribution
**Warranty:** No guarantee of correct operation. Use at your own risk.
**Contributions:** Welcome. Please read existing documentation and test thoroughly before opening pull requests.

### Use Case
Enables K-line diagnostic software developers to test scanner firmware against the Bosch MA1.7 ECU with full system visibility, rapid iteration, and zero hardware risk.

**Limitations:** Implementation is MA1.7-specific. Adapting to other 8052-based ECUs requires new firmware binaries, SFR callbacks, and timing tuning.

---

## Table of Contents

- [Why Emulator Testing?](#why-emulator-testing)
- [Technical Achievements](#technical-achievements)
- [The Journey: Challenges Overcome](#the-journey-challenges-overcome)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Development with Claude](#development-with-claude)
- [Future Work](#future-work)
- [License](#license)

---

## Why Emulator Testing?

Developing automotive diagnostic software directly on real ECU hardware is risky, expensive, and slow. Emulator-based development enables fast iteration with full system visibility and zero hardware damage risk.

### Workflow Comparison
```
Without emulator:
  Code → Physical ECU (setup time) → Debug on real hardware → Slow iteration

With this emulator:
  Code → Emulator (fast, safe, full visibility) → Final validation on ECU
```

### Benefits

**1. Safety:** Zero risk of ECU damage. Test malformed protocols without hardware consequences.

**2. System Visibility:** Full access to CPU state, memory, registers, and timing at every instruction. Impossible on real hardware.

**3. Rapid Iteration:** Recompile and test in seconds. Deterministic behavior enables fast debugging.

**4. Reverse Engineering:** Understand ECU-specific protocol quirks (e.g., MA1.7's P4.5 GPIO-based K-line) safely.
- Week 6: Possible ECU damage, restart with new hardware

**With this emulator:**
- Week 1: Build scanner prototype
- Week 2: Test against MA1.7 emulator with full system visibility → find and fix protocol bugs
- Week 3: Add edge case handling (error conditions, timeouts)
- Week 4: Final validation on real hardware
- Total: 4 weeks vs 6+ weeks, plus zero hardware risk

---

### Technical Note: Emulator Core Bug Discovery

Testing MA1.7 firmware revealed a bug in emu8051 core (`opcodes.c:854`). The `MOV @Ri, direct` opcode incorrectly handled memory access functions, causing stack corruption after ~12k instructions. A 2-line fix resolved the issue.

---

## Technical Implementation

### Emulation Capabilities

**K-line Signal Inversion:** Real hardware uses transceiver ICs (L9637D, MC33199) that invert the K-line signal. Implemented in P4.5 read callback for correct signal handling.

**5-Baud Slow-Init:** ISO 9141-2 handshake at 5 baud (200ms/bit). Instruction-based timing generator synced to CPU execution.

**Cycle-Accurate UART Timing:** Event-based scheduler processes TI/RI flag events at appropriate instruction counts, enabling accurate protocol timing validation.

**PARMRK BREAK Detection:** PTY configured for PARMRK mode to detect K-line BREAK conditions (0xFF 0x00 0x00 sequence).

**8052 Extended Features:**
- Timer 2 (TL2, TH2, T2CON, RCAP2L, RCAP2H)
- Upper RAM (128 bytes @ 0x80-0xFF, indirect addressing)
- Ports P4 and P5
- ADC simulation (IRCON workaround)
- Dual SBUF buffers (separate TX/RX for half-duplex)

---

## Development Notes

### Known Implementation Details

**8052 Memory Allocation:** Upper RAM must be allocated before CPU reset. Addresses 0x80-0xFF are dual-use: direct addressing accesses SFR, indirect addressing accesses Upper RAM.

**MA1.7-Specific Behavior:**
- K-line RX uses P4.5 GPIO polling (not UART hardware)
- Non-standard SBUF dual-buffer model
- ADC readiness simulation via IRCON
- EEPROM watchdog initialization requirement

**Tested Execution:** Firmware runs indefinitely with stable stack pointer and correct interrupt handling. Estimated 50+ million instructions executed successfully.

---

**Root Cause:** `MOV @R1, direct` opcode incorrectly used direct addressing for indirect memory access, corrupting SP register. Address 0x81 has dual meaning (SFR when direct, Upper RAM when indirect).

**Fix:** Two-line change in `opcodes.c:854` switching to proper indirect access function. See [BUGFIXES.md](BUGFIXES.md).

**Result:** Firmware runs indefinitely (50+ million instructions tested) with stable stack pointer.

---

## Features

**MA1.7-Specific Emulation:**
- Complete 8052 instruction set with SAB 80C517 extensions
- Cycle-accurate UART timing using event-driven scheduler
- K-line protocol (ISO 9141-2) with P4.5 GPIO-based RX (non-standard UART)
- Dual SBUF buffers (separate TX/RX) for half-duplex communication
- BREAK detection via PARMRK mode
- Timer 2, Upper RAM, Ports P4/P5, ADC/EEPROM simulation

**Debugging:**
- PC-level instruction tracing with register inspection
- Memory access monitoring (RAM, ROM, SFR)
- Stack overflow detection (0x08-0xDF valid range)
- Interrupt tracking (Timer 0/1/2, UART)

**Testing:**
- 5-baud slow-init injection (SIGUSR1 signal)
- Manual PTY connection for external scanner
- 50+ million instruction execution validation

---

## Quick Start

### Prerequisites
```bash
# Debian/Ubuntu
sudo apt-get install build-essential cmake git

# Arch Linux
sudo pacman -S base-devel cmake git

# macOS
brew install cmake
```

### Building

```bash
# Clone repository
git clone <repository-url>
cd emu8051-tty

# Initialize submodule (emu8051 core)
git submodule update --init --recursive

# Build
mkdir -p build && cd build
cmake ..
make

# Run tests (optional)
ctest
```

### Running

```bash
# Basic usage
./build/emu8051-tty path/to/firmware.bin

# With 8052 features enabled
./build/emu8051-tty firmware.bin --8052
```

**Output:**
```
[emu8051-pty] PTY ready at: /dev/pts/12 (4800 8N1)
Connect your scanner to this device. Ctrl+C to exit.
[DEBUG] Send SIGUSR1 to inject 5-baud init: kill -USR1 <pid>
```

### Connecting Scanner Software

**Option 1: Manual PTY Connection**
```bash
# In another terminal, connect via screen/minicom
screen /dev/pts/12 4800

# Or use Python
import serial
ser = serial.Serial('/dev/pts/12', 4800, timeout=1)
ser.write(b'\x10')  # Send ECU address
```

**Option 2: Test 5-Baud Injection**
```bash
# Send SIGUSR1 to emulator process
kill -USR1 <pid>

# Emulator injects slow-init sequence (0x10 @ 5 baud)
# Firmware decoder validates and responds
```

### Build Options

```bash
# Disable tests
cmake -DENABLE_TESTS=OFF ..

# Disable sanitizers (faster compilation)
cmake -DENABLE_SANITIZERS=OFF ..

# Debug build
cmake -DCMAKE_BUILD_TYPE=Debug ..
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Scanner Software (Python/C++)                              │
│  Connects to: /dev/pts/N                                    │
└──────────────────┬──────────────────────────────────────────┘
                   │ 4800 8N1
                   ↓
┌─────────────────────────────────────────────────────────────┐
│  PTY Harness (UartBridge)                                   │
│  - PARMRK BREAK detection                                   │
│  - Half-duplex echo simulation                              │
│  - RX queue management                                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│  Event Scheduler (UART Timing)                              │
│  - TI/RI flag events                                        │
│  - Instruction-based timing                                 │
│  - Overrun detection                                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│  emu8051 Core (jarikomppa/emu8051)                          │
│  - 8051/8052 instruction set                                │
│  - SFR callbacks (SBUF, SCON, P4, etc.)                     │
│  - Memory management                                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│  Firmware ROM (Bosch MA1.7 - 32KB)                          │
│  - K-line protocol handler                                  │
│  - Slow-init decoder @ PC=0x4C34                            │
│  - Diagnostic services                                      │
└─────────────────────────────────────────────────────────────┘
```

### Memory Model

```
8051/8052 Address Space:
┌──────────────────────────────────────────┐
│ 0x0000 - 0xFFFF: Code Memory (ROM)       │ 64KB
│   ├─ Loaded from firmware.bin            │
│   └─ Read-only (MOVC instructions)       │
├──────────────────────────────────────────┤
│ 0x0000 - 0xFFFF: External Data (XRAM)    │ 64KB
│   ├─ Read/write (MOVX instructions)      │
│   └─ Separate from ROM!                  │
├──────────────────────────────────────────┤
│ 0x00 - 0x7F: Lower Internal RAM          │ 128 bytes
│   ├─ Register banks (R0-R7 × 4)          │
│   ├─ Bit-addressable (0x20-0x2F)         │
│   └─ General purpose RAM                 │
├──────────────────────────────────────────┤
│ 0x80 - 0xFF: Upper Internal RAM (8052)   │ 128 bytes
│   ├─ Accessed via @R0/@R1 (indirect)     │
│   └─ NOT accessible via direct addressing│
├──────────────────────────────────────────┤
│ 0x80 - 0xFF: SFR (Special Function Regs) │ 128 bytes
│   ├─ Accessed via direct addressing      │
│   ├─ SCON (0x98), SBUF (0x99)            │
│   ├─ P4 (0xE8), IE (0xA8), IP0 (0xB8)    │
│   └─ Timer 2 (T2CON, TL2, TH2, etc.)     │
└──────────────────────────────────────────┘

CRITICAL: Addresses 0x80-0xFF are DUAL-USE!
  - Direct addressing → SFR[addr - 0x80]
  - Indirect addressing → UpperData[addr - 0x80]
```

### UART Timing System

**Event-Driven Timing:**
```
Firmware writes SBUF @ instr=1000
  ↓
TX byte sent to PTY (immediate)
  ↓
Schedule TxDone event at appropriate instruction count
  ↓
... firmware continues executing ...
  ↓
When event fires: TI flag set (realistic timing)
```

**Event Priority Queue:**
```cpp
std::priority_queue<UartEvent> g_uart_events;

struct UartEvent {
    long long when_icount;  // Fire at this instruction count
    UartEventKind kind;     // TxDone or RxByte
    uint8_t data;           // RX data (if RxByte)
};
```

**Processing:**
```cpp
void uart_timing_tick(em8051 *cpu, long long current_icount) {
    while (!g_uart_events.empty() &&
           g_uart_events.top().when_icount <= current_icount) {

        UartEvent ev = g_uart_events.top();
        g_uart_events.pop();

        if (ev.kind == TxDone) {
            scon |= SCON_TI;  // Set TI flag
        } else if (ev.kind == RxByte) {
            if (scon & SCON_RI) {
                // Overrun! Discard new byte
            } else {
                g_uart.rx_queue.push(ev.data);
                g_sbuf_rx = ev.data;  // Update RX buffer
                scon |= SCON_RI;
            }
        }
    }
}
```

### SFR Callback System

**SBUF Write (TX):**
```cpp
static void uart_sbuf_write_callback(em8051 *cpu, uint8_t aRegister) {
    uint8_t sbuf_value = EMU_GET_SFR(cpu, SFR_SBUF);

    g_sbuf_tx = sbuf_value;       // Update TX buffer
    g_uart.tx(sbuf_value);        // Send to PTY immediately
    uart_schedule_tx_done(cpu);   // Schedule TI flag
}
```

**SBUF Read (RX):**
```cpp
static uint8_t uart_sbuf_read_callback(em8051 *cpu, uint8_t aRegister) {
    // Return RX buffer (separate from TX buffer!)
    return g_sbuf_rx;
}
```

**P4 Read (K-line RX):**
```cpp
static uint8_t cb_sfr_read(em8051 *cpu, uint8_t addr) {
    if (addr == SFR_P4) {
        unsigned char p4 = cpu->mSFR[addr - 0x80];

        bool kline_physical_high = g_uart.rxd_line_state;

        // Transceiver inverts signal!
        if (!kline_physical_high)
            p4 |= (1 << 5);   // BREAK → P4.5 = 1
        else
            p4 &= ~(1 << 5);  // IDLE → P4.5 = 0

        return p4;
    }
}
```

---

## Development with Claude

This project was developed with AI assistance (Claude, Anthropic), demonstrating collaborative embedded systems development.

**Key Contributions:**
- System architecture and event scheduler design
- Root cause analysis of emulator bugs
- Cycle-accurate UART timing implementation
- Documentation and code review

**Workflow:** Problem description → Architecture proposal → Implementation → Testing/Refinement → Validation

Result: Complex features (e.g., instruction-based timing, dual SBUF model) implemented efficiently through iterative collaboration.

---

## Future Work

**MA1.7 Improvements:** Dynamic baud rate, KWP2000 protocol support, full ADC/EEPROM emulation, cycle-accurate peripheral timing

**Extensibility:** Multi-model support for other 8052-based ECUs, generic firmware loading, per-ECU callback configuration

**Developer Experience:** GUI monitor for CPU state visualization, trace recording/replay, automated protocol test suite

**Community Contributions Welcome:** Bug fixes, additional firmware testing, performance optimization, tooling improvements

---

## License

**emu8051 Core:** MIT License (Jari Komppa). See `emu8051/LICENSE`.

**This Project:** MIT License - Free for research, educational, and testing purposes.

---

## Acknowledgments

- **Jari Komppa** - emu8051 core creator
- **Claude (Anthropic)** - AI assistance for development and debugging
- **ISO/Bosch** - K-line protocol and MA1.7 firmware documentation

---

## Disclaimer

**Personal research project with no warranty.** Correct operation is not guaranteed. The firmware emulation may have undiscovered bugs or incomplete features. Not affiliated with Bosch, Siemens, or Fiat.

**Use at your own risk. Test thoroughly before production use.**
