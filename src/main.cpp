// Fiat Tipo Bosch Monomotronic MA1.7, 27C256, SAB80C517A harness.
// Renault MA1.7 uses a different clock and port wiring; no Renault runtime
// profile is configured here.

#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

extern "C" {
#include <signal.h>
#include <unistd.h>
}

#include "CrankshaftSimulator.hpp"
#include "ma17/CpuContext.hpp"
#include "ma17/CpuHooks.hpp"
#include "ma17/EmulatorConfig.hpp"
#include "ma17/EmulatorLoop.hpp"
#include "ma17/FirmwareLoader.hpp"
#include "ma17/FiveBaudInjector.hpp"
#include "ma17/PortController.hpp"
#include "ma17/PtyBridge.hpp"
#include "ma17/UartScheduler.hpp"

static constexpr int SFR_SCON = 0x98; // SM0..RI
static constexpr int SFR_SBUF = 0x99; // buffer
// The PTY transport calls this C callback, which forwards to UartScheduler.
static void uart_on_scanner_byte(uint8_t b);

using UartBridge = ma17::PtyBridge;

static UartBridge g_uart{uart_on_scanner_byte};
static std::atomic<bool> g_running{true};
static std::atomic<bool> g_inject_5baud{
    false}; // Trigger 5-baud init via SIGUSR1

// Historical name: counts tick() calls, including extra machine cycles of
// multi-cycle instructions. Timing and trace offsets use emulated ticks.
static long long g_instr_counter = 0;
static ma17::UartScheduler g_uart_scheduler{g_uart, g_instr_counter};
static std::chrono::steady_clock::time_point start;
static long long p46_low_start_tick() {
    const char *raw = std::getenv("MA17_P4_6_LOW_FROM_TICK");
    if (!raw)
        return -1;
    errno = 0;
    char *end = nullptr;
    const long long value = std::strtoll(raw, &end, 10);
    if (errno || end == raw || *end != '\0' || value < 0) {
        std::fprintf(stderr, "Invalid MA17_P4_6_LOW_FROM_TICK: %s\n", raw);
        std::exit(2);
    }
    return value;
}
// SAB80C517 Port 4 GPIO input: experimental low pin stimuli, not a claim
// about the Fiat board wiring. The P4 output latch remains untouched.
static ma17::PortController g_ports{
    g_uart, g_instr_counter, start,
    std::getenv("MA17_P4_6_FORCE_LOW") != nullptr,
    std::getenv("MA17_P4_7_FORCE_LOW") != nullptr,
    p46_low_start_tick(),
    std::getenv("MA17_P4_3_FORCE_LOW") != nullptr};

static void uart_on_scanner_byte(uint8_t byte) {
    g_uart_scheduler.on_scanner_byte(byte);
}

static ma17::FiveBaudInjector g_5baud_injector{g_uart};

static void sigint_handler(int) { g_running = false; }

static void sigusr1_handler(int) {
    g_inject_5baud = true;
    // Note: Don't start injector here - signal handlers should be minimal
    // Will be started in main loop when g_inject_5baud is detected
}

// P4 port handling for K-line RX bit sampling
static constexpr int SFR_P4 = 0xE8;

int main(int argc, char **argv) {
    const auto config = ma17::parse_emulator_config(argc, argv);
    if (!config)
        return 2;
    const char *rompath = config->rom_path;
    start = std::chrono::steady_clock::now();
    CrankshaftSimulator sim;
    sim.target_rpm = config->crank_rpm;
    sim.update_pulse_interval(990000); // 11.88 MHz / 12 = 990k ticks/sec
    if (config->crank_immediate)
        sim.startup_delay_instrs = 0;

    // Inicializa PTY
    fprintf(stderr, "[DEBUG] Iniciando abertura de PTY...\n");
    fflush(stderr);

    if (!g_uart.open_pty_4800_8N1()) {
        fprintf(stderr, "[ERRO] Falha ao abrir PTY\n");
        return 1;
    }

    fprintf(stdout, "[emu8051-pty] PTY pronto em: %s (4800 8N1)\n",
            g_uart.slave_path.c_str());
    fprintf(stdout,
            "Conecte seu scanner a esse dispositivo. Ctrl+C para sair.\n");
    fflush(stdout);

    // Keep ROM, XRAM and upper IRAM alive for all core callbacks.
    static ma17::CpuContext context;
    em8051 &cpu = context.cpu;
    ma17::CpuHooks hooks{g_uart_scheduler, g_ports, g_instr_counter};
    hooks.install_uart(cpu);

    // Reset - agora é seguro chamar com aWipe=true
    fprintf(stderr, "[DEBUG] Chamando reset()...\n");
    fflush(stderr);
    reset(&cpu, true);

    // Legacy startup marker; reset() clears XRAM before this initialization.
    // MOVX @R1 with P2=F8h addresses page F8h, not page 00h.
    // The firmware clears RAM[47h] during boot, so this does not prevent
    // its control-loop restart while RPM remains zero.
    cpu.mExtData[0xF8F8] = 0xFF; // Existing startup marker on the correct page
    cpu.mLowerData[0x47] = 0xFF; // Initialize RAM_47 directly
    fprintf(stderr, "[XRAM] Initialized XRAM[0xF8F8]=0xFF, RAM_47=0xFF "
                    "(legacy startup marker)\n");
    fflush(stderr);

    // Timer 2 support now fully implemented via PR #40
    // (https://github.com/jarikomppa/emu8051/pull/40)
    fprintf(
        stderr,
        "[8052] Timer 2 support enabled (T2CON, TL2, TH2, RCAP2L, RCAP2H)\n");
    fflush(stderr);

    // Carrega ROM sobre a memória zerada
    fprintf(stderr, "[DEBUG] Carregando ROM de: %s\n", rompath);
    fflush(stderr);
    if (!ma17::load_bin_to_code(&cpu, rompath, 0x0000))
        return 1;

    // DEBUG: Verify ROM was loaded correctly
    fprintf(stderr, "[DEBUG] ROM verification: mCodeMem=%p\n",
            static_cast<void *>(cpu.mCodeMem));
    fprintf(stderr,
            "[DEBUG] ROM[0x0000]=0x%02X ROM[0x0001]=0x%02X ROM[0x0002]=0x%02X "
            "(reset vector)\n",
            cpu.mCodeMem[0x0000], cpu.mCodeMem[0x0001], cpu.mCodeMem[0x0002]);
    fprintf(stderr,
            "[DEBUG] ROM[0x002B]=0x%02X ROM[0x002D]=0x%02X (Timer 2 ISR)\n",
            cpu.mCodeMem[0x002B], cpu.mCodeMem[0x002D]);
    fflush(stderr);

    hooks.install_fiat_peripherals(cpu);

    // SCON modo 1 (8-bit UART, variável): SM0=0, SM1=1 por padrão de muitas
    // ROMs Forçar estado limpo: Mode 1, REN=1, flags TI/RI limpos Isso evita
    // que a ROM fique presa aguardando um byte lido durante reset
    cpu.mSFR[SFR_SCON - 0x80] = 0x50; // SM1=1, REN=1, TI/RI clear

    // Initialize dual SBUF registers (TX and RX separate!)
    g_uart_scheduler.reset_buffers();
    cpu.mSFR[SFR_SBUF - 0x80] = 0x00; // SFR array init (compatibility)

    // K-line 5-baud initialization setup
    // RAM_17 @ 0x17: Enable K-line detection (must be non-zero per ROM @
    // 0x4C44)
    cpu.mLowerData[0x17] = 0x7F;
    fprintf(stderr, "[K-LINE] Habilitado detecção 5-baud (RAM_17=0x7F)\n");

    // P4 @ 0xE8: Initialize port (initial value from ROM @ 0x085E)
    cpu.mSFR[SFR_P4 - 0x80] = 0xEA;
    fprintf(stderr, "[K-LINE] P4 inicializado (0x%02X)\n",
            cpu.mSFR[SFR_P4 - 0x80]);
    fflush(stderr);

    // Loop principal: step e serviço de UART
    signal(SIGINT, sigint_handler);
    signal(SIGUSR1, sigusr1_handler);

    fprintf(stderr, "[DEBUG] Iniciando loop principal de emulação...\n");
    fprintf(stderr,
            "[DEBUG] Send SIGUSR1 to inject 5-baud init: kill -USR1 %d\n",
            getpid());
    fprintf(stderr, "[DEBUG] PC inicial: 0x%04X\n", cpu.mPC);
    fprintf(stderr,
            "[CRANKSHAFT] Waiting %lld ticks before pulse injection "
            "(RPM=%d)...\n",
            sim.startup_delay_instrs, sim.target_rpm);
    fflush(stderr);

    // Debug: Mostra estado da UART periodicamente
    // int debug_counter = 0;  // DISABLED: not needed when verbose logging is
    // off

    // Fiat clock model: 11.88 MHz / 12 = 990,000 machine-cycle ticks/s.
    constexpr int64_t machine_cycles_per_second = 990000;
    const int steps_per_tick = 500;
    constexpr std::chrono::nanoseconds tick_duration_ns =
        std::chrono::nanoseconds(std::chrono::seconds(1)) /
        (machine_cycles_per_second / steps_per_tick);

    fprintf(stderr, "[DEBUG] Emulation timing: %d steps/tick, ~%lld ns/step\n",
            steps_per_tick,
            static_cast<long long>(tick_duration_ns.count() /
                                   static_cast<long long>(steps_per_tick)));

    const bool trace_pc = getenv("MA17_TRACE_PC") != nullptr;
    ma17::EmulatorLoopContext loop{cpu,
                                   sim,
                                   g_uart,
                                   g_uart_scheduler,
                                   g_5baud_injector,
                                   g_running,
                                   g_inject_5baud,
                                   g_instr_counter,
                                   start,
                                   tick_duration_ns,
                                   steps_per_tick,
                                   trace_pc};
    ma17::run_emulator_loop(loop);

    printf("\n[emu8051-pty] Encerrando.\n");
    return 0;
}
