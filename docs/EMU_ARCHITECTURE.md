# Fiat MA1.7 emulator architecture

The runtime profile in `src/main.cpp` is for the Fiat Tipo 27C256 ROM at
11.88 MHz. Renault MA1.7 hardware uses different timing and port wiring.
`emu8051/` owns MCS-51 execution and the partial SAB80C517A peripheral model;
the C++ harness owns PTY, K-line stimuli, simulated ADC, crank input and logs.

## Current ownership map

| Component | Responsibility |
| --- | --- |
| `main.cpp` | Fiat profile, startup order, signal registration and component composition |
| `ma17::EmulatorConfig`, `FirmwareLoader`, `CpuContext` | Validated arguments, ROM load, owned CPU/ROM/XRAM/upper IRAM storage |
| `ma17::CpuHooks` | Plain C callback adapters for the emulator core; binds UART, ports and tick counter |
| `ma17::EmulatorLoop` | 500-tick batches, crank, CPU, UART and PTY ordering, pacing and PC coverage |
| `ma17::CrankInput` and `CrankshaftSimulator` | 60-2 crank stimulus and timer capture edges at Fiat clock timing |
| `ma17::PtyBridge` | PTY descriptors, PARMRK/BREAK parser, receive queue and callback into UART scheduling |
| `ma17::FiveBaudInjector` | SIGUSR1 slow-init bit sequence on the bridge's K-line level at Fiat tick timing |
| `ma17::UartScheduler` | Separate TX/RX SBUF bytes, TI/RI event queue, SCON callback state and emulator tick timing |
| `ma17::PortController` | Fiat P4.5 K-line voltage inversion, BREAK timeout and P5 feedback reads |
| `ma17::AdcSimulator` | ADDAT channel values and IRCON.0 ADC-ready stimulus |
| `ma17::XramAccess` | Masked MOVX reads/writes and CC3 gate write trace |
| `ma17::FirmwareProbes`, `ExecutionTracer`, `InterruptTracer` | Fiat PC probes, RAM/port/CC3 traces, stack and exception diagnostics |

`main.cpp` keeps process-level state: the signal flags `g_running` and
`g_inject_5baud`, emulated tick counter, startup timestamp, PTY bridge,
UART scheduler, port controller and five-baud injector. C signal handlers
only set atomics. `CpuHooks` holds references to UART, ports and ticks; its
single active instance bridges the core's plain C function pointers. The
loop receives all dependencies through `EmulatorLoopContext`. PTY file
descriptors are closed by the bridge destructor. `src/lib.cpp` currently
has no runtime behavior.

The startup order is observable: validate ROM size, initialize crank timing,
open PTY, allocate code/XRAM/upper IRAM, register UART hooks, call `reset`,
initialize startup bytes, load ROM, register peripheral hooks, then run ticks.
The CPU pointer supplied to UART events is set before the execution loop.
The loop services SIGUSR1, crank input, CPU ticks, UART timing, PTY input and
wall-clock pacing. `ticks` counts `tick()` calls, including extra machine
cycles, and is distinct from the number of decoded opcodes.

## Dependency flow

```text
main -> CpuContext + CpuHooks -> emu8051 C core
     -> EmulatorLoop -> CrankInput, UartScheduler, PtyBridge, FirmwareProbes, ExecutionTracer
PtyBridge -> UartScheduler -> CPU SFR callbacks
CpuHooks -> PortController, AdcSimulator, XramAccess, InterruptTracer
```

To add a peripheral callback, implement its behavior in a focused component,
register its C-compatible adapter in `CpuHooks`, and add a direct component
test plus a firmware trace or scanner test. Keep Fiat clock/port assumptions
in the Fiat profile; Renault hardware requires a separate profile.

## Baseline before moving code

Build: `cmake -S . -B build -DENABLE_TESTS=ON` and `cmake --build build -j4`
passed. `ctest --test-dir build --output-on-failure`: 25/25 passed.
Round-trip Python suite: 19/19 passed; PTY protocol unit suite: 3/3 passed.
Fiat ROM round-trip: 32768 bytes, zero mismatches, equal SHA-256
`a34734350611cf561eb39ac1a63097defcaaff642cd7780526f632dda40f8e1f`.
The PTY integration completed the five-baud handshake and diagnostic request
with `FC 02 04 1E` and `FC 02 06 1B` under `MA17_CRANK_IMMEDIATE=1`,
`MA17_ADC_CH7=63`, `MA17_ADC_CH0=120`, `MA17_ADC_CH6=95`.

Traces used `MA17_TRACE_PC=1` through `tools/trace_ma17.py`, three seconds,
immediate 60-2 crank and no K-line injection. Results and raw logs are in
ignored `build/refactor-baseline/`; PTY names, host timing and event counts
vary across runs, so compare ROM-derived RAM values and steady-state periods.

| Stimulus | RAM 47h | Teeth + gaps | P5.0 low, ticks | CC3 low, ticks |
| --- | --- | --- | ---: | ---: |
| 750 RPM, ADC7=63 | `1E` | 58 + 2 | 1940 | 11361 |
| 1000 RPM, ADC7=63 | `28` | 58 + 2 | 1861 | 10801 |
| 2000 RPM, ADC7=63 | `50` | 58 + 2 | 1789 | 9480 |
| 1000 RPM, ADC2=40, ADC7=63 | `28` | 58 + 2 | 1861 | 10084.5 |
| 1000 RPM, ADC7=64 | `28` | 58 + 2 | 1861 | no CC3 low pulse |

P5.0/P5.1 alternate; their periods were 79200, 59400 and 29700 ticks
at 750, 1000 and 2000 RPM. These are emulator outputs, not proof of the
physical ECU wiring. The CC3 model is partial; other compare modes need
separate validation if they become relevant.

## Current verification

`src/main.cpp` is 207 lines, down from 2596 in the baseline. The code now
uses explicit CMake sources. Direct tests cover UART TI/RI timing, P4.5
inversion, P5 latch reads, masked MOVX, ADC channel selection, IRCON.0 and
callback wiring. A 1000 RPM trace after the loop extraction matched all 1217
comparable baseline RAM 47h/C4h, crank, interrupt, P5, CC3, table, fault and
TPS events in order. One or two trailing events depend on the wall-clock
cutoff. The full PTY handshake and diagnostic collection passed after the
loop and callback extraction. CTest passed 34/34 under Clang and GCC.
After moving pre-tick probes into `FirmwareProbes.cpp`, a fresh 1000 RPM
trace still matched all 1217 comparable baseline events in its common prefix.
Final three-second traces at 750 and 2000 RPM and with ADC2=40 or ADC7=64
also matched every comparable baseline event in their common prefixes:
1034, 1986, 1218 and 1030 events respectively. ROM-derived RAM 47h values
were `1E`, `50`, `28` and `28`; each complete revolution had 58 teeth plus
two missing slots. The 2000 RPM whole-run CC3 median shifted because its
wall-clock cutoff included an extra pulse; the ordered common events matched.

The original ROM and canonical assembly were not altered by this refactor.
The Fiat round-trip check still reports 32768 bytes, zero mismatches and
equal SHA-256. The 8051 core is a git submodule; this C++ refactor does not
edit its contents. The core header has no include guard, so each owned C++
translation unit includes it once. GCC uses targeted warning suppressions
for the legacy core C files and fixture file; owned C++ code retains `-Werror`.

Run the checks from the repository root:

```sh
cmake -S . -B build -DENABLE_TESTS=ON
cmake --build build -j4
ctest --test-dir build --output-on-failure
cmake -S . -B build-gcc -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DENABLE_TESTS=ON
cmake --build build-gcc -j4
ctest --test-dir build-gcc --output-on-failure
python3 -m unittest discover -s tests -p 'test_roundtrip_8051.py'
python3 -m unittest discover -s tests -p 'test_pty_protocol.py'
python3 tools/roundtrip_8051.py FiatTipo_MA17_dump_27c256.bin
MA17_CRANK_IMMEDIATE=1 MA17_ADC_CH7=63 MA17_ADC_CH0=120 \
  MA17_ADC_CH6=95 MA17_EXPECT_FAULT_TRIPLET=02061B ./run_full_test.sh
clang-format --dry-run --Werror src/main.cpp include/ma17/*.hpp src/ma17/*.cpp
git diff --check
```

For dynamic RPM/ADC comparisons, use `tools/trace_ma17.py --seconds 3
--no-kline-inject --crank-immediate --rpm 1000 --output-dir build/trace-1000`
with `MA17_ADC_CH7=63 MA17_ADC_CH0=120 MA17_ADC_CH6=95`. Its PC and event
logs go under the output directory; compare deterministic tick events, not
the count at wall-clock termination. The CC3 pin model remains partial,
and these traces do not establish physical ECU output wiring.
