// emu8051_pty_harness.cpp
// PTY harness for emu8051 core integration
// - Loads raw ROM (e.g., 27C256, 32 KiB) into program memory
// - Exposes PTY interface at 4800 8N1 baud
// - Emulates UART via SFR SCON/SBUF with cycle-accurate timing
// - Supports 8052 features (Timer2, extended RAM)
//
// IMPORTANT NOTES:
// 1) Function names and em8051 struct fields may vary between emu8051
// revisions.
//    Check emulator.h/emu8051.h from jarikomppa/emu8051 and adjust defines
//    below.
// 2) UART timing is event-driven and instruction-count based:
//    - TX: byte sent immediately to PTY, TI flag scheduled
//    - RX: byte arrival scheduled, RI flag set when event fires
//    - Matches real 8051 UART behavior for K-line protocol testing
//
// ============================================================================
// WORKAROUNDS FOR MISSING SAB80C537 PERIPHERALS (BOSCH ECU)
// ============================================================================
//
// This firmware expects SAB80C537-specific hardware (Bosch Motronic MA1.7 ECU).
// Since jarikomppa/emu8051 only implements basic 8051/8052, we emulate missing
// peripherals via SFR write callbacks:
//
// 1. WORKAROUND: ADC Emulation (cb_sfr_write_ircon)
//    Issue:    Timer 0 ISR waits for ADC ready flag (IRCON.0) in busy-wait loop
//              Loop: jbc IRCON.0, next; sjmp loop (code @ 0x0711-0x0714)
//    Impact:   Timer 0 ISR hangs forever → mInterruptActive=2 stuck
//    Solution: Callback forces IRCON.0=1 after each write (simulates ADC always
//    ready) Register: IRCON = 0xC0 (SAB80C537 specific)
//
// Without these workarounds, emulator hangs after first Timer 0 interrupt,
// making K-line communication impossible.
//

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <iostream>
extern "C" {
#include <errno.h>
#include <fcntl.h>
#include <math.h> // llround()
#include <poll.h>
#include <pty.h> // openpty()
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

// Headers do emu8051 (ajuste o include-path conforme seu projeto)
#include <emu8051.h>
#include <emulator.h>
}

#include <atomic>
#include <chrono>
#include <queue>
#include <string>
#include <vector>

// =========================
// Seção de ADAPTAÇÃO de API
// =========================
// Alguns forks expõem helpers diferentes. Ajuste estes #defines
// para casar com o que existir em "emulator.h":

// 1) Acesso SFR (Special Function Registers) dentro da struct em8051
// SFRs ocupam endereços 0x80-0xFF, mas o array mSFR[128] é indexado 0-127
#ifndef EMU_GET_SFR
#define EMU_GET_SFR(CPU, ADDR)                                                 \
    ((CPU)->mSFR[static_cast<unsigned>((ADDR) - 0x80u)])
#define EMU_SET_SFR(CPU, ADDR, VAL)                                            \
    ((CPU)->mSFR[static_cast<unsigned>((ADDR) - 0x80u)] =                      \
         static_cast<unsigned char>(VAL))
#endif

// 2) Acesso Code memory (program space, MOVC)
#ifndef EMU_GET_CODE
#define EMU_GET_CODE(CPU, ADDR) ((CPU)->mCodeMem[static_cast<unsigned>(ADDR)])
#define EMU_SET_CODE(CPU, ADDR, VAL)                                           \
    ((CPU)->mCodeMem[static_cast<unsigned>(ADDR)] =                            \
         static_cast<unsigned char>(VAL))
#endif

// =========================
// UART/SCON helpers (8051)
// =========================
static constexpr int SFR_SCON = 0x98;   // SM0..RI
static constexpr int SFR_SBUF = 0x99;   // buffer
static constexpr int SFR_ADCON0 = 0xD8; // A/D Converter Control Register 0
static constexpr int SFR_ADDAT = 0xD9;  // A/D Converter Data Register
[[maybe_unused]] static constexpr int SFR_DAPR =
    0xDA; // D/A Converter Program Register (used in debug traces)
// Bits de SCON
[[maybe_unused]] static constexpr unsigned char SCON_SM0 = 0x80;
[[maybe_unused]] static constexpr unsigned char SCON_SM1 = 0x40;
[[maybe_unused]] static constexpr unsigned char SCON_SM2 = 0x20;
static constexpr unsigned char SCON_REN = 0x10;
[[maybe_unused]] static constexpr unsigned char SCON_TB8 = 0x08;
[[maybe_unused]] static constexpr unsigned char SCON_RB8 = 0x04;
static constexpr unsigned char SCON_TI = 0x02;
static constexpr unsigned char SCON_RI = 0x01;

// Forward declaration for cycle-accurate UART timing
static void uart_on_scanner_byte(uint8_t b);

struct UartBridge {
    int mfd = -1; // master pty
    int sfd = -1; // slave pty
    std::string slave_path;

    // K-line signal injection control (SIGUSR1 mode)
    // When override_rxd=true, FiveBaudInjector controls the K-line state
    // When override_rxd=false, PTY/PARMRK mode is active (normal operation)
    bool override_rxd = false; // true = SIGUSR1 injection, false = PTY mode
    bool override_state =
        true; // Physical K-line state: true=12V(IDLE), false=0V(BREAK)

    // K-line BREAK detection state (PTY/PARMRK mode)
    // rxd_line_state represents the PHYSICAL K-line voltage:
    //   true  = 12V (IDLE/MARK)
    //   false = 0V (BREAK/SPACE)
    bool rxd_line_state = true;
    long long low_until_ms = 0;
    unsigned char break_detect_buffer[3] = {0, 0, 0};
    int break_detect_idx = 0;

    static long long now_ms() {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        return ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL;
    }

    // RX queue for bytes after PARMRK filtering (normal data bytes)
    std::queue<unsigned char> rx_queue;

    std::chrono::steady_clock::time_point last_tx_time{};

    bool ignore_parmark() {
        if (last_tx_time == std::chrono::steady_clock::time_point{}) {
            return false;
        }

        if (last_tx_time + std::chrono::milliseconds(1000) >
            std::chrono::steady_clock::now()) {
            return true;
        }
        return false;
    }

    bool is_receiving_packets() {
        if (last_tx_time == std::chrono::steady_clock::time_point{}) {
            return false;
        }

        if (last_tx_time + std::chrono::milliseconds(800) >
            std::chrono::steady_clock::now()) {
            return true;
        }
        return false;
    }

    bool open_pty_4800_8N1() {
        char namebuf[128] = {0};
        struct termios tio{};

        fprintf(stderr, "[DEBUG] Tentando abrir PTY...\n");
        fflush(stderr);

        if (openpty(&mfd, &sfd, namebuf, nullptr, nullptr) < 0) {
            perror("openpty");
            return false;
        }

        fprintf(stderr, "[DEBUG] PTY aberto: %s (mfd=%d, sfd=%d)\n", namebuf,
                mfd, sfd);
        fflush(stderr);

        if (tcgetattr(sfd, &tio) < 0) {
            perror("tcgetattr");
            return false;
        }
        cfmakeraw(&tio);
#ifdef B4800
        cfsetispeed(&tio, B4800);
        cfsetospeed(&tio, B4800);
#else
        // Fallback, se B4800 não existir
        cfsetispeed(&tio, B9600);
        cfsetospeed(&tio, B9600);
#endif
        tio.c_cflag &=
            static_cast<tcflag_t>(~static_cast<tcflag_t>(PARENB)); // N
        tio.c_cflag &=
            static_cast<tcflag_t>(~static_cast<tcflag_t>(CSTOPB)); // 1
        tio.c_cflag &= static_cast<tcflag_t>(~static_cast<tcflag_t>(CSIZE));
        tio.c_cflag |= CS8; // 8
        tio.c_cflag |= CLOCAL | CREAD;

        // K-line BREAK detection: Enable PARMRK mode
        // BREAK condition will appear as: 0xFF 0x00 0x00
        tio.c_iflag &=
            static_cast<tcflag_t>(~static_cast<tcflag_t>(IGNBRK | BRKINT));
        tio.c_iflag |= PARMRK;

        // CRITICAL: Disable all buffering for immediate byte delivery
        tio.c_cc[VMIN] = 1;  // Read 1 byte at a time
        tio.c_cc[VTIME] = 0; // No timeout

        if (tcsetattr(sfd, TCSANOW, &tio) < 0) {
            perror("tcsetattr");
            return false;
        }

        // Flush all pending data
        tcflush(sfd, TCIOFLUSH);
        tcflush(mfd, TCIOFLUSH);

        // Non-blocking no master
        int flags = fcntl(mfd, F_GETFL, 0);
        fcntl(mfd, F_SETFL, flags | O_NONBLOCK);

        slave_path = namebuf;
        fprintf(stderr, "[DEBUG] Configuração PTY concluída com sucesso\n");
        fflush(stderr);
        return true;
    }

    // envia byte para o terminal
    // K-line half-duplex: Byte é enviado ao PTY e o scanner externo recebe +
    // ecoa O echo do scanner volta pelo PTY e é capturado por
    // read_and_process() NÃO colocamos na rx_queue aqui (evita duplicação
    // quando firmware lê SBUF)
    void tx(unsigned char b) {
        last_tx_time = std::chrono::steady_clock::now();
        if (mfd >= 0) {
            ssize_t written = write(mfd, &b, 1);
            fprintf(stderr,
                    "[PTY-TX] Byte 0x%02X written to PTY (result=%zd)\n", b,
                    written);
            fflush(stderr);
        }
    }

    // Tenta ler 1 byte da queue RX; retorna -1 se vazia
    // A queue é preenchida por read_and_process() após filtragem PARMRK
    int rx_try() {
        if (rx_queue.empty())
            return -1;
        unsigned char b = rx_queue.front();
        rx_queue.pop();
        fprintf(stderr, "[RX-QUEUE] Dequeued 0x%02X (queue size was %zu)\n", b,
                rx_queue.size() + 1);
        fflush(stderr);
        return static_cast<int>(b);
    }

    // Read from PTY, detect BREAK, echo bytes, and queue for UART RX
    // PARMRK mode: BREAK appears as 0xFF 0x00 0x00
    // K-line protocol: ALL bytes must be echoed back (half-duplex validation)
    //
    // K-line BREAK/UNBREAK behavior:
    // - BREAK detection: 0xFF 0x00 0x00 sequence → rxd_line_state = false (0V)
    // - UNBREAK timer: Holds LOW state for 250ms after LAST BREAK received
    // - After timer expires: cb_sfr_read() returns line to HIGH (12V idle)
    // - This models physical line capacitance + transceiver hold time
    void read_and_process() {
        unsigned char b = 0;
        ssize_t n = read(mfd, &b, 1);
        if (n != 1)
            return;

        if (ignore_parmark()) {
            break_detect_idx = 0;
            break_detect_buffer[0] = 0;
            break_detect_buffer[1] = 0;
            break_detect_buffer[2] = 0;

            last_tx_time = std::chrono::steady_clock::now();
            /*fprintf(stderr,
                    "[PTY-RX] [%lld] Scanner sent 0x%02X, echoing back + "
                    "scheduling for firmware\n",
                    UartBridge::now_ms(), b);
            fflush(stderr);*/
            (void)!write(mfd, &b, 1); // Echo K-line para o scanner
            uart_on_scanner_byte(b);  // Agenda RX (timing-aware)
            return;
        }

        // PARMRK BREAK pattern detection state machine
        if (break_detect_idx == 0) {
            if (b == 0xFF && !ignore_parmark()) {
                // Possible BREAK or escaped 0xFF - wait for next byte
                break_detect_buffer[0] = b;
                break_detect_idx = 1;
                std::cout << "[BREAK-DETECT] Possible BREAK detected"
                          << std::endl;
                return;
            }

            last_tx_time = std::chrono::steady_clock::now();

            // Normal data byte do scanner externo:
            // 1. ECHO de volta (simula half-duplex K-line no PTY)
            // 2. RI=1 imediato (zero-latency RX, comportamento real de
            // transceiver)
            /*fprintf(stderr,
                    "[PTY-RX] [%lld] Scanner sent 0x%02X, echoing back + "
                    "scheduling for firmware\n",
                    UartBridge::now_ms(), b);
            fflush(stderr);*/
            (void)!write(mfd, &b, 1); // Echo K-line para o scanner
            uart_on_scanner_byte(b);  // Agenda RX (timing-aware)
            rxd_line_state = true;    // Physical K-line returns to 12V
            return;
        }

        if (break_detect_idx == 1) {
            break_detect_buffer[1] = b;
            if (b == 0x00) {
                // Could be BREAK (0xFF 0x00 0x00) - wait for third byte
                break_detect_idx = 2;
                return;
            } else if (b == 0xFF) {
                // Escaped 0xFF: real data byte is 0xFF
                unsigned char ff = 0xFF;
                (void)!write(mfd, &ff, 1); // Echo para o scanner
                uart_on_scanner_byte(ff);  // Agenda RX (timing-aware)
                rxd_line_state = true;
                break_detect_idx = 0;
                return;
            } else {
                // Was start of something else - echo and schedule both bytes
                (void)!write(mfd, break_detect_buffer,
                             2); // Echo para o scanner
                uart_on_scanner_byte(break_detect_buffer[0]); // Agenda RX
                uart_on_scanner_byte(b);                      // Agenda RX
                rxd_line_state = true;
                break_detect_idx = 0;
                return;
            }
        }

        if (break_detect_idx == 2) {
            break_detect_buffer[2] = b;
            if (b == 0x00 || b == 0xFF) {
                // BREAK confirmed! (0xFF 0x00 0x00 pattern complete)
                rxd_line_state =
                    b == 0xFF; // Physical K-line goes LOW (0V BREAK/SPACE)

                // UNBREAK timer strategy: Each BREAK extends the LOW period,
                // but not indefinitely In 5-baud init, BREAKs arrive ~200ms
                // apart (one per bit) We keep line LOW until 250ms after LAST
                // BREAK received This accumulates multiple BREAKs into one
                // continuous LOW period CRITICAL: Timer MUST be > 200ms to
                // avoid premature UNBREAK between consecutive bits!
                long long now = now_ms();
                long long extend_to = now + 210;

                // Only extend if new time is later (don't reset on each BREAK)
                if (extend_to > low_until_ms) {
                    low_until_ms = extend_to;
                }

                fprintf(
                    stderr,
                    "[K-LINE] BREAK detected (RXD=LOW, hold until +%lld ms)\n",
                    low_until_ms - now);
                fflush(stderr);
                // Do NOT echo BREAK, do NOT queue (BREAKs are control signals,
                // not data)
            } else {
                // Framing error or other pattern - treat as data
                (void)!write(mfd, &b, 1); // Echo para o scanner
                uart_on_scanner_byte(b);  // Agenda RX (timing-aware)
                rxd_line_state = true;
            }
            break_detect_idx = 0;
            return;
        }
    }
};

static UartBridge g_uart;
static std::atomic<bool> g_running{true};
static std::atomic<bool> g_inject_5baud{
    false}; // Trigger 5-baud init via SIGUSR1

// =========================
// UART Timing Infrastructure (Hardware-Realistic Model)
// =========================
// TX: ~9 bit times delay (cycle-accurate via event scheduler)
// RX: zero-latency (RI=1 immediately, matches K-line transceiver)
// See: KLINE_TRANSCEIVER.md for hardware behavior reference

// Cristal real do hardware (11.880 MHz)
static constexpr double FOSC_HZ = 11'880'000.0;

// Global instruction counter (moved from main() local scope)
// Tracks total emulated instructions for event scheduling
static long long g_instr_counter = 0;

// Ponteiro global para a CPU (usado pelos eventos UART)
static em8051 *g_uart_cpu = nullptr;

// ===================================================================
// DUAL SBUF REGISTERS (8051 Hardware Accurate Model)
// ===================================================================
// Real 8051 hardware has TWO separate SBUF registers at address 0x99:
// - TX buffer (write-only): Written by firmware via "mov SBUF, A"
// - RX buffer (read-only): Read by firmware via "mov A, SBUF"
//
// This separation is critical for half-duplex K-line operation:
// - Firmware writes TX → goes to g_sbuf_tx, sent to transceiver
// - Scanner ACK arrives → stored in g_sbuf_rx (does NOT overwrite TX)
// - Firmware reads SBUF → gets g_sbuf_rx (ACK), NOT the echo of g_sbuf_tx
//
// Without this model, firmware reads its own TX instead of scanner ACK,
// causing validation failures in half-duplex protocols.
// ===================================================================
static uint8_t g_sbuf_tx = 0x00; // TX buffer (firmware writes here)
static uint8_t g_sbuf_rx = 0x00; // RX buffer (firmware reads from here)

// Event types para agendar TI/RI em "instruction ticks"
enum class UartEventKind : uint8_t {
    TxDone, // TI flag should be set
    RxByte, // RI flag should be set + SBUF loaded
};

struct UartEvent {
    long long when_icount; // em unidades de instrução 8051
    UartEventKind kind;
    uint8_t data; // só usado para RxByte

    // priority_queue como min-heap (earliest event first)
    bool operator<(UartEvent const &o) const {
        return when_icount > o.when_icount;
    }
};

static std::priority_queue<UartEvent> g_uart_events;

#define BAD_VALUE 0x77

/*static uint8_t read_mem(em8051 *aCPU, uint8_t aAddress)
{
    if (aAddress > 0x7f)
    {
        if (aCPU->sfrread[aAddress - 0x80])
            return aCPU->sfrread[aAddress - 0x80](aCPU, aAddress);
        else
            return aCPU->mSFR[aAddress - 0x80];
    }
    else
    {
        return aCPU->mLowerData[aAddress];
    }
}*/

static uint8_t read_mem_indir(em8051 *aCPU, uint8_t aAddress) {
    if (aAddress > 0x7f) {
        if (aCPU->mUpperData) {
            return aCPU->mUpperData[aAddress - 0x80];
        }
    } else {
        return aCPU->mLowerData[aAddress];
    }

    return BAD_VALUE;
}

static std::array<uint16_t, 2048> g_pc_hist{};
static size_t g_pc_hist_idx = 0;

[[maybe_unused]] static const char *cpu_callstack(em8051 *cpu) {
    static char buffer[1024];
    size_t offset = 0;
    uint8_t sp = cpu->mSFR[REG_SP];
    offset += static_cast<size_t>(
        std::max<ssize_t>(0, snprintf(buffer + offset, sizeof(buffer) - offset,
                                      "Callstack (SP=0x%02X): ", sp)));

    // Stack grows upward; return addresses are pushed as LOW then HIGH.
    // Top of stack: HIGH byte at mLowerData[SP], LOW byte at mLowerData[SP-1].
    uint8_t idx = sp;
    int entries = 0;
    while (idx > 1 && offset < sizeof(buffer) - 8 && entries < 5) {
        // Stop if we've reached the conventional stack base (avoid reading
        // intrusive regions). 0x02 is typical initial lower bound; be safe.
        if (idx <= 0x02)
            break;

        uint32_t value = read_mem_indir(cpu, idx);
        uint32_t value2 = read_mem_indir(cpu, idx - 1);
        uint32_t ret_addr = (static_cast<uint32_t>(value) << 8U) |
                            static_cast<uint32_t>(value2);

        int wrote = snprintf(buffer + offset, sizeof(buffer) - offset,
                             "0x%04X ", ret_addr);
        if (wrote > 0)
            offset += static_cast<size_t>(wrote);
        else
            break;

        idx -= 2; // move to previous return address (2 bytes)
        entries++;
    }

    if (g_pc_hist_idx > 0 && offset < sizeof(buffer) - 8) {
        // Print the PC history
        int wrote =
            snprintf(buffer + offset, sizeof(buffer) - offset, "[PC HISTORY] ");
        if (wrote > 0) {
            offset += static_cast<size_t>(wrote);
        }

        constexpr size_t MAX_PC_HISTORY = 2048;

        for (size_t i = 0; i < g_pc_hist_idx && i < MAX_PC_HISTORY &&
                           offset < sizeof(buffer) - 8;
             i++) {
            wrote = snprintf(buffer + offset, sizeof(buffer) - offset,
                             "0x%04X ", g_pc_hist[g_pc_hist_idx - 1 - i]);
            if (wrote > 0) {
                offset += static_cast<size_t>(wrote);
            }
        }

        if (offset < sizeof(buffer) - 8) {
            wrote = snprintf(buffer + offset, sizeof(buffer) - offset, "\n");
            if (wrote > 0) {
                offset += static_cast<size_t>(wrote);
            }
        }

        g_pc_hist_idx = 0;
    }

    return buffer;
}

static constexpr uint16_t kXramTraceD0 = 0x00D0;
static constexpr uint16_t kXramTraceD1 = 0x00D1;

static inline uint8_t read_ext_data(em8051 *cpu, uint16_t address_masked) {
    if (!cpu->mExtData)
        return 0;
    return cpu->mExtData[address_masked];
}

static inline bool is_xram_trace_target(uint16_t address) {
    return address == kXramTraceD0 || address == kXramTraceD1;
}

static bool is_known_dtc_clear_site(uint16_t pc) {
    switch (pc) {
    /*case 0x0B5C:
    case 0x0B5F:
    case 0x42BB:
    case 0x42BE:
    case 0x4B95:
    case 0x4B98:
    case 0x5178:
    case 0x517B:
        return true;*/
    default:
        return false;
    }
}

static bool should_log_xram() {
    static std::chrono::steady_clock::time_point last_log_time =
        std::chrono::steady_clock::now() - std::chrono::milliseconds(1000);
    auto now = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        now - last_log_time);
    if (duration.count() > 400 || g_uart.is_receiving_packets()) {
        last_log_time = now;
        return true;
    }
    return false;
}

static uint8_t cb_xram_trace_read(em8051 *cpu, uint16_t address) {
    const uint16_t masked = address & cpu->mExtDataMaxIdx;
    const uint8_t value = read_ext_data(cpu, masked);

    /*if (is_xram_trace_target(address) && should_log_xram()) {
        const uint8_t psw = cpu->mSFR[REG_PSW];
        const uint8_t bank_offset =
            static_cast<uint8_t>(((psw >> 3) & 0x03u) * 8u);
        const uint8_t r0 = cpu->mLowerData[bank_offset];
        const uint8_t r1 = cpu->mLowerData[bank_offset + 1];

        fprintf(stderr,
                "[XRAM-DTC-READ] instr=%lld PC=0x%04X addr=0x%04X -> 0x%02X "
                "(P2=0x%02X R0=0x%02X R1=0x%02X)\n",
                g_instr_counter, cpu->mPC, address, value,
                cpu->mSFR[REG_P2], r0, r1);
        fflush(stderr);
    }*/

    return value;
}

static void cb_xram_trace_write(em8051 *cpu, uint16_t address, uint8_t value) {
    const uint16_t masked = address & cpu->mExtDataMaxIdx;
    // const uint8_t prev = read_ext_data(cpu, masked);

    if (cpu->mExtData) {
        cpu->mExtData[masked] = value;
    }

    if (!is_xram_trace_target(address))
        return;

    if (is_known_dtc_clear_site(cpu->mPC))
        return;

    if (!should_log_xram())
        return;

    /*const char *callstack = cpu_callstack(cpu);
    fprintf(stderr,
            "[XRAM-DTC-WRITE] instr=%lld PC=0x%04X addr=0x%04X %02X→%02X "
            "(P2=0x%02X) %s\n",
            g_instr_counter, cpu->mPC, address, prev, value,
            cpu->mSFR[REG_P2], callstack);
    fflush(stderr);*/
}

// --- Helpers de timing ---

// Calculate real-time milliseconds from instruction count
static double instr_to_ms(long long instr_count) {
    // 990,000 instructions/second @ 11.880 MHz crystal
    double instr_per_sec = FOSC_HZ / 12.0;
    return (static_cast<double>(instr_count) / instr_per_sec) * 1000.0;
}

// Calculate baud rate (fixed 4800 for K-line)
static double uart_current_baud([[maybe_unused]] const em8051 *cpu) {
    // TODO: ler de Timer1/Timer2 -> por enquanto assume 4800 fixo (K-line)
    return 4800.0;
}

// Calculate instructions per UART bit
static long long uart_instr_per_bit(const em8051 *cpu) {
    double baud = uart_current_baud(cpu);
    if (baud <= 0.0)
        return 0;
    double instr_per_sec = FOSC_HZ / 12.0;       // 990,000 instr/s
    double instr_per_bit = instr_per_sec / baud; // ~206.25 @ 4800 baud
    return static_cast<long long>(llround(instr_per_bit));
}

// Schedule TI flag setting after TX completes
// TI rises at START of stop bit (UART standard)
static void uart_schedule_tx_done(em8051 *cpu) {
    long long ipb = uart_instr_per_bit(cpu);
    if (ipb <= 0)
        return;

    UartEvent ev{};
    ev.kind = UartEventKind::TxDone;
    ev.data = 0;
    ev.when_icount = g_instr_counter + 9 * ipb; // 1 start + 8 data bits
    g_uart_events.push(ev);

    /*fprintf(stderr,
            "[UART TIMING] TX scheduled, TI will be set at instr=%lld (+%lld) "
            "[%.2f ms]\n",
            ev.when_icount, 9 * ipb, instr_to_ms(ev.when_icount));
    fflush(stderr);*/
}

// Schedule RX byte delivery + RI flag setting
// RI rises in MIDDLE of stop bit (UART standard)
// Called by uart_on_scanner_byte() when byte arrives from scanner
static void uart_schedule_rx_byte(em8051 *cpu, uint8_t b) {
    long long ipb = uart_instr_per_bit(cpu);
    if (ipb <= 0)
        return;

    UartEvent ev{};
    ev.kind = UartEventKind::RxByte;
    ev.data = b;
    // uart_timing_tick() will deliver byte and set RI=1 at scheduled time
    double ipb_double = static_cast<double>(ipb);
    ev.when_icount =
        g_instr_counter + static_cast<long long>(llround(9.5 * ipb_double));
    g_uart_events.push(ev);

    /*fprintf(stderr,
            "[UART TIMING] RX 0x%02X scheduled, RI will be set at instr=%lld "
            "(+%lld) [%.2f ms]\n",
            b, ev.when_icount,
            static_cast<long long>(llround(9.5 * ipb_double)),
            instr_to_ms(ev.when_icount));
    fflush(stderr);*/
}

// Process UART events that are due
// Called after each instruction in main loop
static void uart_timing_tick(em8051 *cpu, long long current_icount) {
    while (!g_uart_events.empty() &&
           g_uart_events.top().when_icount <= current_icount) {

        UartEvent ev = g_uart_events.top();
        g_uart_events.pop();

        uint8_t scon = EMU_GET_SFR(cpu, SFR_SCON);

        switch (ev.kind) {
        case UartEventKind::TxDone: {
            // Transmissão terminou → sobe TI
            scon |= SCON_TI;
            EMU_SET_SFR(cpu, SFR_SCON, scon);

            /*fprintf(stderr,
                    "[UART TIMING] TX done @instr=%lld [%.2f ms] (TI=1)\n",
                    current_icount, instr_to_ms(current_icount));
            fflush(stderr);*/
            break;
        }

        case UartEventKind::RxByte: {
            // K-line transceiver behavior: REN flag ignored during handshake
            // MA1.7 firmware keeps REN=0 but expects bytes to arrive anyway
            // This matches real transceiver hardware (L9637D/MC33199)

            // Check for RX overrun (RI already set = previous byte not read)
            if (scon & SCON_RI) {
                fprintf(stderr,
                        "[UART TIMING] RX overrun: RI já=1, descartando 0x%02X "
                        "@instr=%lld [%.2f ms]\n",
                        ev.data, current_icount, instr_to_ms(current_icount));
                fflush(stderr);
                break; // Discard new byte (real hardware behavior)
            }

            // Deliver byte: update buffers and set RI flag
            g_uart.rx_queue.push(ev.data);
            scon |= SCON_RI;
            EMU_SET_SFR(cpu, SFR_SCON, scon);
            g_sbuf_rx = ev.data; // Update RX SBUF (separate from TX)

            /*fprintf(stderr,
                    "[UART TIMING] RX pronto 0x%02X (RI=1, queue=%zu) "
                    "@instr=%lld [%.2f ms]\n",
                    ev.data, g_uart.rx_queue.size(), current_icount,
                    instr_to_ms(current_icount));
            fflush(stderr);*/
            break;
        }

        default:
            __builtin_unreachable(); // All enum values covered
        }
    }
}

// Helper: called when scanner byte arrives from PTY
// Schedules RX event with realistic hardware latency (~9.5 bit times)
static void uart_on_scanner_byte(uint8_t b) {
    if (!g_uart_cpu) {
        // fallback: fallback to legacy behavior if something fails
        g_uart.rx_queue.push(b);
        return;
    }

    // K-line RX path: byte arrives from scanner
    //
    // Implementation:
    // 1. Check for RX overrun (RI already set = previous byte not read)
    // 2. Schedule RX event (uart_timing_tick will update g_sbuf_rx + set RI=1)
    // 3. Firmware polls or waits for RI flag, then reads g_sbuf_rx
    //
    // K-line transceivers (L9637D/MC33199) ignore REN flag during handshake,
    // so we don't gate RX on REN being set.

    uint8_t scon = EMU_GET_SFR(g_uart_cpu, SFR_SCON);

    // Check for RX overrun (RI already set = previous byte not read yet)
    if (scon & SCON_RI) {
        fprintf(stderr,
                "[UART RX] OVERRUN! RI already=1, discarding new byte 0x%02X\n",
                b);
        fflush(stderr);
        return; // Discard new byte (real hardware behavior)
    }

    // Schedule RX event processing
    uart_schedule_rx_byte(g_uart_cpu, b);

    fprintf(stderr, "[UART] instr=%lld byte=0x%02X → scheduled RX event\n",
            g_instr_counter, b);
    fflush(stderr);
}

// Non-blocking 5-baud state machine (instruction-based timing)
// ISO 9141-2 slow-init: 5 baud = 200ms per bit (0x10 address byte, LSB-first)
// Timing calculation:
//   Crystal: 11.880 MHz
//   8051 instruction cycle: 12 clock cycles
//   Instruction rate: 11,880,000 / 12 = 990,000 instructions/second
//   5-baud bit period: 1/5 = 0.2 seconds = 200ms
//   Instructions per bit: 990,000 × 0.2 = 198,000 instructions
struct FiveBaudInjector {
    bool active = false;
    int current_bit = 0;
    long long bit_end_instruction = 0;
    const int bits[10] = {0, 0, 0, 0, 0,
                          1, 0, 0, 0, 1}; // 0x10 LSB-first + start(0) + stop(1)

    static constexpr long long INSTRUCTIONS_PER_BIT =
        198000; // See timing calculation above

    void start(long long current_instruction) {
        if (active)
            return;
        active = true;
        current_bit = 0;
        bit_end_instruction = current_instruction + INSTRUCTIONS_PER_BIT;

        // ENTRA no modo override
        g_uart.override_rxd = true;

        if (bits[0] == 0) {
            g_uart.override_state = false; // LOW
        } else {
            g_uart.override_state = true; // HIGH
        }

        fprintf(stderr, "\n[5-BAUD START] Bit 0: %s until instr=%lld\n",
                g_uart.override_state ? "MARK(HIGH)" : "BREAK(LOW)",
                bit_end_instruction);
        fflush(stderr);
    }

    void tick(long long current_instruction) {
        if (!active)
            return;
        if (current_instruction < bit_end_instruction)
            return;

        current_bit++;
        if (current_bit >= 10) {
            active = false;
            g_uart.override_state = true; // linha volta para HIGH
            g_uart.override_rxd = false;  // VOLTA pro modo normal (PTY/PARMRK)
            fprintf(stderr,
                    "[5-BAUD COMPLETE] All bits sent at instr=%lld, line "
                    "returned to HIGH\n\n",
                    current_instruction);
            fflush(stderr);
            return;
        }

        bit_end_instruction = current_instruction + INSTRUCTIONS_PER_BIT;
        g_uart.override_state = bits[current_bit] != 0;
        fprintf(stderr, "[5-BAUD] Bit %d: %s until instr=%lld\n", current_bit,
                g_uart.override_state ? "MARK(HIGH)" : "BREAK(LOW)",
                bit_end_instruction);
        fflush(stderr);
    }
};

static FiveBaudInjector g_5baud_injector;

static void sigint_handler(int) { g_running = false; }

static void sigusr1_handler(int) {
    g_inject_5baud = true;
    // Note: Don't start injector here - signal handlers should be minimal
    // Will be started in main loop when g_inject_5baud is detected
}

// P4 port handling for K-line RX bit sampling
static constexpr int SFR_P4 = 0xE8;
static unsigned char p4_value = 0xEA; // Initial value from ROM @ 0x085E

// Exception callback to catch emulator errors
static void cb_exception(em8051 *cpu, int code) {
    const char *exception_names[] = {"STACK",
                                     "ACC_TO_A",
                                     "IRET_PSW_MISMATCH",
                                     "IRET_SP_MISMATCH",
                                     "IRET_ACC_MISMATCH",
                                     "ILLEGAL_OPCODE"};
    static int exception_count = 0;
    if (exception_count < 5) { // Only log first 5 exceptions
        unsigned char sp = cpu->mSFR[REG_SP];
        fprintf(stderr,
                "[EXCEPTION] Code %d (%s) at PC=0x%04X SP=0x%02X ACC=0x%02X\n",
                code,
                (code >= 0 && code <= 5) ? exception_names[code] : "UNKNOWN",
                cpu->mPC, sp, cpu->mSFR[REG_ACC]);

        // Show stack contents to debug RETI issues
        unsigned char s1 = sp < 127 ? cpu->mLowerData[sp + 1] : 0xFF;
        unsigned char s2 = sp < 126 ? cpu->mLowerData[sp + 2] : 0xFF;
        fprintf(stderr,
                "[EXCEPTION] Stack[SP+1]=0x%02X Stack[SP+2]=0x%02X (return "
                "addr would be 0x%02X%02X)\n",
                static_cast<unsigned int>(s1), static_cast<unsigned int>(s2),
                static_cast<unsigned int>(s2), static_cast<unsigned int>(s1));
        fflush(stderr);
        exception_count++;
    }
}

// SFR write callback for IE register (interrupt enable) monitoring
static void cb_sfr_write_ie(em8051 *cpu, uint8_t addr) {
    [[maybe_unused]] unsigned char ie_val = cpu->mSFR[addr - 0x80];
    static int ie_write_count = 0;
    if (ie_write_count < 50) { // Log first 50 writes to see pattern
        fprintf(stderr,
                "[IE WRITE] PC=0x%04X IE=0x%02X (EA=%d ET2=%d ES=%d ET1=%d "
                "EX1=%d ET0=%d EX0=%d)\n",
                cpu->mPC, ie_val,
                (ie_val & 0x80) ? 1 : 0,  // EA
                (ie_val & 0x20) ? 1 : 0,  // ET2
                (ie_val & 0x10) ? 1 : 0,  // ES
                (ie_val & 0x08) ? 1 : 0,  // ET1
                (ie_val & 0x04) ? 1 : 0,  // EX1
                (ie_val & 0x02) ? 1 : 0,  // ET0
                (ie_val & 0x01) ? 1 : 0); // EX0
        fflush(stderr);
        ie_write_count++;
    }
}

// SFR write callback for IP0 register (interrupt priority) - FIX Timer 0
// priority!
static void cb_sfr_write_ip0(em8051 *cpu, uint8_t addr) {
    (void)addr;
    (void)cpu;
    // unsigned char ip0_val = cpu->mSFR[addr - 0x80];
    // static int ip0_write_count = 0;

    // HACK: ALWAYS force Timer 0 to HIGH priority to prevent Timer 2 from
    // blocking it Original firmware sets: IP0 = 0x39 = 0b00111001 (PT0=0,
    // PT2=1) We modify to:          IP0 = 0x3B = 0b00111011 (PT0=1, PT2=1) This
    // allows Timer 0 ISR to run for 5-baud P4.5 sampling
    /*if ((ip0_val & 0x02) == 0) { // If PT0 (bit 1) is 0
        ip0_val |= 0x02;         // Set PT0=1 (make Timer 0 high priority)
        cpu->mSFR[addr - 0x80] = ip0_val;
        if (ip0_write_count < 10) { // Log first 10 modifications
            fprintf(
                stderr,
                "[IP0 HACK] #%d Timer 0 priority forced to HIGH: IP0=0x%02X "
                "(PT2=%d PT0=%d)\n",
                ++ip0_write_count, ip0_val,
                (ip0_val & 0x20) ? 1 : 0,  // PT2
                (ip0_val & 0x02) ? 1 : 0); // PT0
            fflush(stderr);
        }
    }*/
}

// Callback para monitorar modificações no PC (interrupt vectors)
static uint16_t last_pc_for_isr_detection = 0;
static int timer2_trace_count = 0;
static bool timer2_active = false;

static void detect_isr_call(em8051 *cpu) {
    uint16_t pc = cpu->mPC;

    // Detect ISR vectors (0x03, 0x0B, 0x13, 0x1B, 0x23, 0x2B)
    if ((pc == 0x03 || pc == 0x0B || pc == 0x13 || pc == 0x1B || pc == 0x23 ||
         pc == 0x2B) &&
        last_pc_for_isr_detection != pc) {
        const char *isr_name = "UNKNOWN";
        switch (pc) {
        case 0x03:
            isr_name = "INT0";
            break;
        case 0x0B:
            isr_name = "TIMER0";
            break;
        case 0x13:
            isr_name = "INT1";
            break;
        case 0x1B:
            isr_name = "TIMER1";
            break;
        case 0x23:
            isr_name = "SERIAL";
            break;
        case 0x2B:
            isr_name = "TIMER2";
            timer2_active = true;
            timer2_trace_count = 0;
            break;
        default:
            break;
        }
        // DEBUG: Limited ISR logging to track Timer 0 vs Timer 2
        static int tf0_isr_count = 0;
        static int tf2_isr_count = 0;
        if (pc == 0x0B && tf0_isr_count < 20) { // Timer 0
            fprintf(stderr,
                    "[ISR-TF0] #%d Timer 0 ISR called from PC=0x%04X "
                    "(mInterruptActive=%d)\n",
                    ++tf0_isr_count, last_pc_for_isr_detection,
                    cpu->mInterruptActive);
        }
        if (pc == 0x2B && tf2_isr_count < 20) { // Timer 2
            fprintf(stderr,
                    "[ISR-TF2] #%d Timer 2 ISR called from PC=0x%04X "
                    "(mInterruptActive=%d)\n",
                    ++tf2_isr_count, last_pc_for_isr_detection,
                    cpu->mInterruptActive);
        }

        // DEBUG: Trace PC when inside Timer 0 ISR (HIGH priority)
        /*static int tf0_pc_trace_count = 0;
        static int last_tf0_trace_tick = 0;
        static int tick_counter = 0;
        tick_counter++;
        if (cpu->mInterruptActive == 2 && (tick_counter - last_tf0_trace_tick) >
        100 && tf0_pc_trace_count < 200) { fprintf(stderr, "[TF0-TRACE] #%d
        PC=0x%04X SP=0x%02X TCON=0x%02X IE=0x%02X (HIGH ISR, tick=%d)\n",
                    ++tf0_pc_trace_count, pc, cpu->mSFR[REG_SP],
        cpu->mSFR[REG_TCON], cpu->mSFR[REG_IE], tick_counter);
            last_tf0_trace_tick = tick_counter;
        }*/
        (void)isr_name; // Suppress unused variable warning
    }

    // Trace Timer 2 execution for first 30 instructions
    // DISABLED: Verbose logging for production testing
    /*
    if (timer2_active && timer2_trace_count < 30) {
      unsigned char opcode = cpu->mCodeMem[pc];
      fprintf(stderr, "[T2-TRACE] PC=0x%04X SP=0x%02X opcode=0x%02X\n",
              pc,
              cpu->mSFR[REG_SP],
              opcode);

      // If opcode is 0x00 (NOP or unexpected zero), dump surrounding bytes
      if (opcode == 0x00 && timer2_trace_count < 3) {
        fprintf(stderr, "[T2-TRACE] !!! Opcode 0x00 detected! Hex dump:\n");
        fprintf(stderr, "[T2-TRACE] mCodeMem pointer: %p\n",
    static_cast<void*>(cpu->mCodeMem)); unsigned start_addr = pc > 4 ? pc - 4 :
    0; unsigned end_addr = pc + 4; fprintf(stderr, "[T2-TRACE] Dump
    [0x%04X-0x%04X]: ", start_addr, end_addr); for (int i = -4; i <= 4; ++i) {
          unsigned addr = static_cast<unsigned>(static_cast<int>(pc) + i);
          if (addr < 0x10000u) {
            fprintf(stderr, "%02X ", cpu->mCodeMem[addr]);
          }
        }
        fprintf(stderr, "\n");
      }

      fflush(stderr);
      timer2_trace_count++;

      // Check if we reached 0x018E (problematic RETI)
      if (pc == 0x018E) {
        fprintf(stderr, "[T2-TRACE] !!! Reached problematic RETI at 0x018E
    !!!\n"); timer2_active = false;
      }

      // Detect RETI opcode (0x32)
      if (cpu->mCodeMem[pc] == 0x32) {
        fprintf(stderr, "[T2-TRACE] RETI executed at PC=0x%04X\n", pc);
        timer2_active = false;
      }
    }
    */

    last_pc_for_isr_detection = pc;
}

// SFR read callback for P4 port (K-line RX bit sampling)
// Signature MUST match em8051sfrread: uint8_t (*)(struct em8051 *aCPU, uint8_t
// aRegister)

// SFR write callback for IRCON (0xC0) - ADC emulation hack
static void cb_sfr_write_ircon(em8051 *cpu, uint8_t addr) {
    // JBC IRCON.0 will clear bit 0 after reading/testing it
    // We immediately set it back to 1 to fake continuous ADC ready state
    // This prevents infinite loop at code_711: jbc IRCON.0, code_716
    static int ircon_write_count = 0;
    if (ircon_write_count < 10) {
        fprintf(stderr, "[IRCON-WRITE] #%d IRCON=0x%02X, forcing bit 0=1\n",
                ++ircon_write_count, cpu->mSFR[addr - 0x80]);
    }
    cpu->mSFR[addr - 0x80] |= 0x01; // Force IRCON.0 = 1 always
}

static uint8_t cb_sfr_read(em8051 *cpu, uint8_t addr) {
    if (addr == SFR_P4) {

        // UNBREAK timer: Return K-line to HIGH (12V idle) after BREAK hold
        // period expires This timer is set by read_and_process() when BREAK is
        // detected (0xFF 0x00 0x00) Only active in PTY/PARMRK mode (not during
        // SIGUSR1 injection)
        if (!g_uart.override_rxd) {
            // PTY/PARMRK mode: Handle UNBREAK timer
            if (g_uart.low_until_ms &&
                UartBridge::now_ms() >= g_uart.low_until_ms) {
                if (!g_uart.rxd_line_state) {
                    fprintf(stderr,
                            "[K-LINE] UNBREAK: RXD LOW→HIGH (timer expired)\n");
                    fflush(stderr);
                }
                g_uart.rxd_line_state = true; // Physical K-line returns to 12V
                g_uart.low_until_ms = 0;      // Clear timer
            }
        }

        unsigned char p4 = cpu->mSFR[addr - 0x80];

        // K-line physical state (12V = idle/MARK, 0V = BREAK/SPACE)
        // override_rxd=true: SIGUSR1 injection mode
        // override_rxd=false: PTY/PARMRK mode
        bool kline_physical_high =
            g_uart.override_rxd ? g_uart.override_state : g_uart.rxd_line_state;

        // CRITICAL: K-line transceiver (L9637/MC33199) INVERTS the signal!
        // Physical K-line → Transceiver → P4.5 bit
        // ------------------------------------------------
        // 12V (IDLE/MARK)  →  Transceiver  →  P4.5 = 0
        // 0V (BREAK/SPACE) →  Transceiver  →  P4.5 = 1
        //
        // This inversion is standard in automotive K-line transceivers.
        // The firmware expects P4.5=1 during BREAK, P4.5=0 during idle.
        if (!kline_physical_high)
            p4 |= (1 << 5); // K-line BREAK (0V) → P4.5 = 1
        else
            p4 &= ~(1 << 5); // K-line IDLE (12V) → P4.5 = 0

        static unsigned char last_p4_value = 0xFF;
        if (p4 != last_p4_value) {
            fprintf(stderr,
                    "[P4.5] Read: 0x%02X (K-line=%s, P4.5=%d); PC=0x%04X\n", p4,
                    kline_physical_high ? "IDLE(12V)" : "BREAK(0V)",
                    (p4 >> 5) & 1, cpu->mPC);
            fflush(stderr);
            last_p4_value = p4;
        }

        p4_value = p4;
        cpu->mSFR[addr - 0x80] = p4;
        return p4;
    }

    // ADDAT: A/D Converter Data Register
    // Firmware validates ADC range: 4 <= ADDAT <= 247
    // Return simulated sensor values within valid range
    if (addr == SFR_ADDAT) {
        // Read ADCON0 to determine which ADC channel is selected
        uint8_t adcon0 = cpu->mSFR[SFR_ADCON0 - 0x80];
        uint8_t channel = adcon0 & 0x07; // Lower 3 bits = channel select

        // Simulated ADC values for different channels (8-bit)
        // Valid range: 4-247 (firmware validation @ code:0x0732)
        static const uint8_t adc_values[8] = {
            120, // Channel 0: Water temp sensor (0x62) - ~60°C
            130, // Channel 1: Air temp sensor (0x63) - ~25°C
            100, // Channel 2: TPS/Lambda (0x6C) - mid-range
            80,  // Channel 3
            90,  // Channel 4
            110, // Channel 5
            95,  // Channel 6
            105  // Channel 7
        };

        uint8_t adc_value = adc_values[channel];

        // Verbose logging disabled to reduce log noise
        // ADC callback is working correctly (confirmed by testing)
        // Uncomment below for debugging if needed:
        /*
        static uint8_t last_channel = 0xFF;
        static uint8_t last_adc_value = 0xFF;
        if (channel != last_channel || adc_value != last_adc_value) {
            fprintf(stderr, "[ADC-READ] ADDAT=0x%02X (%d) for channel %d
        (ADCON0=0x%02X); PC=0x%04X\n", adc_value, adc_value, channel, adcon0,
        cpu->mPC); fflush(stderr); last_channel = channel; last_adc_value =
        adc_value;
        }
        */

        return adc_value;
    }

    return cpu->mSFR[addr - 0x80];
}

static void cb_sfr_write(struct em8051 *aCPU, uint8_t aRegister) {
    (void)aCPU;
    (void)aRegister;
    /*if (aRegister == SFR_P4) {
        unsigned char new_p4 = aCPU->mSFR[aRegister - 0x80];
        p4_value = new_p4;
        fprintf(stderr, "[P4 WRITE] 0x%02X at PC=0x%04X\n", new_p4, aCPU->mPC);
        fflush(stderr);
    }*/
}

// Callback: firmware ESCREVEU em SBUF (TX)
// CRITICAL: K-line half-duplex hardware behavior:
// - TX byte goes to physical line via transceiver (IMMEDIATE)
// - TI flag rises after ~9 bit times (cycle-accurate timing)
// - Transceiver ECHOES the byte back to RX automatically (same SBUF!)
// - Firmware reads SBUF to validate echo, even with REN=0
// - This is how L9637D/MC33199 transceivers work in half-duplex mode
static void uart_sbuf_write_callback(em8051 *cpu, uint8_t aRegister) {
    (void)aRegister; // unused - always SFR_SBUF (0x99)

    // CRITICAL: Read from SFR array (firmware wrote to TX buffer)
    uint8_t sbuf_value = EMU_GET_SFR(cpu, SFR_SBUF);

    // Store in TX buffer (separate from RX buffer!)
    g_sbuf_tx = sbuf_value;

    // Update SFR array with TX value (for emu8051 compatibility)
    // Note: This does NOT affect g_sbuf_rx which is read-only by firmware
    EMU_SET_SFR(cpu, SFR_SBUF, g_sbuf_tx);

    //uint16_t pc = cpu->mPC;

    // TRACE: Detect critical firmware locations
    //static int tx_count = 0;
    //tx_count++;

    //const char *callstack = cpu_callstack(cpu);

    // Track packet structure bytes
    /*if (pc == 0x4DE0) {
        fprintf(stderr,
                "[TX-TRACE] #%d PC=0x4DE0: Sync byte 0x55; Callstack %s\n",
                tx_count, callstack);
    } else if (pc == 0x4D3B) {
        uint8_t ram_45 = cpu->mLowerData[0x45];
        uint8_t ram_42 = cpu->mLowerData[0x42]; // Progress counter
        uint8_t ram_3e = cpu->mLowerData[0x3E]; // Retry counter
        fprintf(stderr,
                "[TX-TRACE] #%d PC=0x4D3B: Loop TX=0x%02X (RAM_42=%d, "
                "RAM_3E=%d, RAM_45=0x%02X); Callstack %s\n",
                tx_count, g_sbuf_tx, ram_42, ram_3e, ram_45, callstack);
    } else if (tx_count >= 5 && tx_count <= 30) {
        // Trace first 30 TX after keys
        uint8_t xram_cb = cpu->mExtData[0xCB];  // Packet counter
        uint8_t ram_42 = cpu->mLowerData[0x42]; // Progress counter
        fprintf(stderr,
                "[TX-TRACE] #%d PC=0x%04X: TX=0x%02X (XRAM[0xCB]=%d, "
                "RAM_42=%d); Callstack %s\n",
                tx_count, pc, g_sbuf_tx, xram_cb, ram_42, callstack);

        // Show packet buffer every 5th TX
        if (tx_count % 5 == 0) {
            fprintf(stderr, "[TX-BUFFER] XRAM[0xB8-0xC0]: ");
            for (int i = 0xB8; i <= 0xC0; i++) {
                fprintf(stderr, "%02X ", cpu->mExtData[i]);
            }
            fprintf(stderr, "\n");
        }
    }*/

    // TX: Envia byte para PTY (scanner externo) - IMEDIATO
    g_uart.tx(g_sbuf_tx);

    // Agenda TI flag para subir após ~9 bit times (cycle-accurate)
    uart_schedule_tx_done(cpu);

    /*uint8_t scon = EMU_GET_SFR(cpu, SFR_SCON);
    scon &= ~SCON_RI; // Clear RI flag - RX byte not ready yet
    EMU_SET_SFR(cpu, SFR_SCON, scon);*/

    // CRITICAL: TX buffer is separate from RX buffer!
    // Even if firmware reads SBUF immediately after TX, it will get
    // the RX buffer value (g_sbuf_rx), NOT the TX echo (g_sbuf_tx).
    // This matches real 8051 hardware behavior.

    /*fprintf(stderr,
            "[UART TX] instr=%lld PC=0x%04X TX_BUF=0x%02X → TX imediato, TI "
            "agendado: Callstack %s\n",
            g_instr_counter, cpu->mPC, g_sbuf_tx, callstack);
    fflush(stderr);*/
}

// Callback: firmware LEU SBUF (RX)
static uint8_t uart_sbuf_read_callback(em8051 *cpu, uint8_t aRegister) {
    if (aRegister != SFR_SBUF) {
        [[unlikely]];
        return EMU_GET_SFR(cpu, aRegister); // Should not happen
    }

    // CRITICAL: Firmware ALWAYS reads from RX buffer (g_sbuf_rx)
    // Never from TX buffer (g_sbuf_tx)!
    // This matches real 8051 hardware where SBUF is TWO separate registers.

    /*uint8_t scon = EMU_GET_SFR(cpu, SFR_SCON);

    if (scon & SCON_RI) {
        // RI=1: RX data available
        if (!g_uart.rx_queue.empty()) {
            // Update RX buffer from queue
            g_sbuf_rx = g_uart.rx_queue.front();
            g_uart.rx_queue.pop();

            // Update SFR array for emu8051 compatibility
            EMU_SET_SFR(cpu, SFR_SBUF, g_sbuf_rx);

            fprintf(stderr,
                    "[UART RX-READ] instr=%lld PC=0x%04X Firmware leu "
                    "RX_BUF=0x%02X (RI=1, dequeued, queue size now %zu)\n",
                    g_instr_counter, cpu->mPC, g_sbuf_rx,
                    g_uart.rx_queue.size());
            fflush(stderr);
        } else {
            // Queue empty but RI=1? Return last RX value
            fprintf(stderr,
                    "[UART RX-READ] instr=%lld PC=0x%04X Firmware leu "
                    "RX_BUF=0x%02X (RI=1, but queue already empty!)\n",
                    g_instr_counter, cpu->mPC, g_sbuf_rx);
            fflush(stderr);
        }
    } else {
        // RI=0: No RX data ready, return whatever is in RX buffer
        // (could be old RX data or 0x00 if no RX ever occurred)
        fprintf(
            stderr,
            "[UART RX-READ] instr=%lld PC=0x%04X Firmware leu RX_BUF=0x%02X "
            "(RI=0, no new data) TX_BUF was=0x%02X\n",
            g_instr_counter, cpu->mPC, g_sbuf_rx, g_sbuf_tx);
        fflush(stderr);
    }*/

    // CRITICAL: Return RX buffer, NEVER TX buffer!
    return g_sbuf_rx;
}

static uint8_t uart_generic_read_callback(em8051 *cpu, uint8_t aRegister) {
    if (aRegister == SFR_SCON) {
        uint8_t scon = EMU_GET_SFR(cpu, SFR_SCON);

        // Poll PTY for new data (maintains backward compatibility)
        // Actual RX delivery is handled by uart_timing_tick events
        if ((scon & SCON_REN) != 0 && (scon & SCON_RI) == 0) {
            g_uart.read_and_process();
        }

        // If queue has data and RI not yet set, set it
        // (mostly for compatibility - events should already set RI)
        /*if (!g_uart.rx_queue.empty() && !(scon & SCON_RI)) {
            // Update RX buffer from queue (don't pop yet - wait for SBUF read)
            g_sbuf_rx = g_uart.rx_queue.front();

            // Set RI flag to indicate data ready
            scon |= SCON_RI;

            // Update SFR array for emu8051 compatibility
            EMU_SET_SFR(cpu, SFR_SBUF, g_sbuf_rx);
            EMU_SET_SFR(cpu, SFR_SCON, scon);
        }*/

        return scon;
    }

    // Retorna o valor atual do SFR solicitado
    uint8_t sbuf = EMU_GET_SFR(cpu, aRegister);
    return sbuf;
}

// Callback: firmware ESCREVEU em S0CON (controle UART)
// Com cycle-accurate timing, RX injection agora é controlada por eventos
// Este callback apenas monitora mudanças de configuração (REN, SM0/SM1, etc)
static void cb_sfr_write_scon(em8051 *cpu, uint8_t aRegister) {
    (void)aRegister; // unused - sempre SFR_SCON (0x98)

    if (aRegister != SFR_SCON) {
        return;
    }

    unsigned char scon_new = EMU_GET_SFR(cpu, SFR_SCON);

    // Track previous S0CON value para detectar transições
    static unsigned char scon_prev = 0x50; // Initial: Mode 1, REN=1, TI=0, RI=0

    unsigned char ri_prev = scon_prev & SCON_RI;
    unsigned char ri_new = scon_new & SCON_RI;
    unsigned char ren_new = scon_new & SCON_REN;

    // DEBUG: Log S0CON writes (primeiros 50 para ver padrão)
    static int scon_write_count = 0;
    if (scon_write_count < 50) {
        fprintf(stderr,
                "[S0CON-WRITE] #%d PC=0x%04X S0CON: 0x%02X→0x%02X (RI: %d→%d, "
                "REN=%d)\n",
                ++scon_write_count, cpu->mPC, scon_prev, scon_new,
                ri_prev ? 1 : 0, ri_new ? 1 : 0, ren_new ? 1 : 0);
        fflush(stderr);
    }

    // Update previous S0CON state para próximo callback
    scon_prev = scon_new;
}

static bool load_bin_to_code(em8051 *cpu, const char *path,
                             unsigned base = 0x0000) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror("fopen");
        return false;
    }
    std::vector<unsigned char> buf;
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (len <= 0) {
        fclose(f);
        fprintf(stderr, "ROM vazia?\n");
        return false;
    }
    buf.resize(static_cast<size_t>(len));
    if (static_cast<long>(fread(buf.data(), 1, static_cast<size_t>(len), f)) !=
        len) {
        perror("fread");
        fclose(f);
        return false;
    }
    fclose(f);

    for (size_t i = 0; i < buf.size(); ++i) {
        unsigned addr = base + static_cast<unsigned>(i);
        if (addr < 0x10000u)
            EMU_SET_CODE(cpu, addr, buf[i]);
    }
    fprintf(stderr,
            "[emu8051-pty] ROM carregada: %ld bytes em 0x%04X..0x%04X\n", len,
            base, static_cast<unsigned>(base + len - 1));
    return true;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Uso: %s <rom.bin> [--8052]\n", argv[0]);
        return 2;
    }
    const char *rompath = argv[1];
    bool want8052 = (argc >= 3 && strcmp(argv[2], "--8052") == 0);

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

    // Instancia CPU
    em8051 cpu{};

    // Aloca memórias antes de chamar reset()
    // Code memory: 64KB (0x10000 bytes) - ROM, read-only
    static unsigned char code_memory[0x10000];
    cpu.mCodeMem = code_memory;
    cpu.mCodeMemMaxIdx = 0xFFFF;

    // External data memory: 64KB - RAM separada da ROM!
    // CRITICAL FIX: ROM deve ser read-only. Firmware que faz MOVX write
    // não deve sobrescrever a ROM!
    static unsigned char ext_data_memory[0x10000];
    cpu.mExtData = ext_data_memory;
    cpu.mExtDataMaxIdx = 0xFFFF;

    // Upper data RAM: 128 bytes adicionais para 8052
    // NOTA: A firmware Bosch MA1.7 usa RAM superior mesmo não sendo 8052
    // completo! Portanto, SEMPRE alocamos (o firmware acessa RAM[0x80-0xFF] via
    // @R0/@R1)
    static unsigned char upper_data[128];
    cpu.mUpperData = upper_data; // ALWAYS allocate for Bosch MA1.7
    (void)want8052;              // Suppress unused variable warning

    // Register UART callbacks for SBUF (immediate TX/RX via SFR hooks)
    cpu.sfrwrite[SFR_SBUF - 0x80] = uart_sbuf_write_callback;
    cpu.sfrread[SFR_SBUF - 0x80] = uart_sbuf_read_callback;
    fprintf(stderr,
            "[DEBUG] Callback registrado: SBUF (0x%02X) -> UART TX/RX\n",
            static_cast<unsigned int>(SFR_SBUF));
    fflush(stderr);

    // Register S0CON write callback for zero-latency RX injection
    // Detecta quando firmware limpa RI flag = "ready for next byte"
    cpu.sfrwrite[SFR_SCON - 0x80] = cb_sfr_write_scon;
    cpu.sfrread[SFR_SCON - 0x80] = uart_generic_read_callback;
    fprintf(stderr,
            "[DEBUG] Callback registrado: S0CON (0x%02X) -> Zero-latency RX "
            "injection\n",
            static_cast<unsigned int>(SFR_SCON));
    fflush(stderr);

    // Reset - agora é seguro chamar com aWipe=true
    fprintf(stderr, "[DEBUG] Chamando reset()...\n");
    fflush(stderr);
    reset(&cpu, true);

    // EEPROM/NVM simulation: initialize calibration/config data
    // MUST be done AFTER reset() since reset() clears mExtData
    // The firmware reads XRAM[0xF8] → RAM_47 (watchdog counter)
    // If RAM_47 = 0, it triggers a system reset @ 0x4B67
    // Set to 0xFF to prevent continuous reset loop
    cpu.mExtData[0xF8] = 0xFF;   // EEPROM watchdog value
    cpu.mLowerData[0x47] = 0xFF; // Initialize RAM_47 directly
    fprintf(stderr, "[EEPROM] Initialized XRAM[0xF8]=0xFF, RAM_47=0xFF "
                    "(prevents reset loop)\n");
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
    if (!load_bin_to_code(&cpu, rompath, 0x0000))
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

    // Register SFR read callback for P4 (K-line RX bit sampling via P4.5)
    // Direct assignment to emu8051 callback array (native mechanism)
    cpu.sfrread[SFR_P4 - 0x80] = cb_sfr_read;
    cpu.sfrwrite[SFR_P4 - 0x80] = cb_sfr_write;
    fprintf(stderr, "[DEBUG] Callback registrado: P4 (0x%02X) -> cb_sfr_read\n",
            static_cast<unsigned int>(SFR_P4));
    fflush(stderr);

    // Register SFR write callback for IE register monitoring
    cpu.sfrwrite[0xA8 - 0x80] = cb_sfr_write_ie; // IE = 0xA8
    fprintf(stderr, "[DEBUG] Callback registrado: IE write monitor\n");
    fflush(stderr);

    // Register SFR write callback for IP0 register (interrupt priority
    // override)
    cpu.sfrwrite[0xB8 - 0x80] = cb_sfr_write_ip0; // IP0 = 0xB8
    fprintf(stderr,
            "[DEBUG] Callback registrado: IP0 write monitor (priority fix)\n");
    fflush(stderr);

    // Register exception callback to catch emulator errors
    cpu.except = cb_exception;
    fprintf(stderr, "[DEBUG] Callback registrado: exception handler\n");
    fflush(stderr);

    // Trace XRAM D0/D1 accesses (diagnostic flags)
    cpu.xread = cb_xram_trace_read;
    cpu.xwrite = cb_xram_trace_write;
    fprintf(stderr,
            "[DEBUG] XRAM trace callbacks registrados (0xD0/0xD1 monitor)\n");
    fflush(stderr);

    // WORKAROUND: ADC emulation - force IRCON.0=1 (ADC ready)
    // SAB80C517 IRCON @ 0xC0, bit 0 = IADC (ADC interrupt flag)
    // Timer 0 ISR busy-waits: jbc IRCON.0, code_716 @ 0x0711
    // Without ADC emulation, firmware hangs in infinite loop
    cpu.mSFR[0xC0 - 0x80] = 0x01;                   // Initial: IRCON.0 = 1
    cpu.sfrwrite[0xC0 - 0x80] = cb_sfr_write_ircon; // IRCON = 0xC0
    fprintf(stderr,
            "[WORKAROUND] IRCON callback registered (fake ADC ready)\n");

    // ADDAT: A/D Converter Data Register - return simulated sensor values
    // Firmware validates range: 4 <= ADDAT <= 247 (see code:0x0732)
    cpu.sfrread[SFR_ADDAT - 0x80] = cb_sfr_read;
    fprintf(stderr,
            "[WORKAROUND] ADDAT callback registered (simulated ADC values)\n");

    // SCON modo 1 (8-bit UART, variável): SM0=0, SM1=1 por padrão de muitas
    // ROMs Forçar estado limpo: Mode 1, REN=1, flags TI/RI limpos Isso evita
    // que a ROM fique presa aguardando um byte esp��rio lido durante reset
    EMU_SET_SFR(&cpu, SFR_SCON, 0x50); // 01010000 = SM1=1, REN=1, TI=0, RI=0

    // Initialize dual SBUF registers (TX and RX separate!)
    g_sbuf_tx = 0x00;
    g_sbuf_rx = 0x00;
    EMU_SET_SFR(&cpu, SFR_SBUF, 0x00); // SFR array init (compatibility)

    // K-line 5-baud initialization setup
    // RAM_17 @ 0x17: Enable K-line detection (must be non-zero per ROM @
    // 0x4C44)
    cpu.mLowerData[0x17] = 0x7F;
    fprintf(stderr, "[K-LINE] Habilitado detecção 5-baud (RAM_17=0x7F)\n");

    // P4 @ 0xE8: Initialize port (initial value from ROM @ 0x085E)
    EMU_SET_SFR(&cpu, SFR_P4, 0xEA);
    p4_value = 0xEA;
    fprintf(stderr, "[K-LINE] P4 inicializado (0x%02X)\n", p4_value);
    fflush(stderr);

    // Loop principal: step e serviço de UART
    signal(SIGINT, sigint_handler);
    signal(SIGUSR1, sigusr1_handler);

    fprintf(stderr, "[DEBUG] Iniciando loop principal de emulação...\n");
    fprintf(stderr,
            "[DEBUG] Send SIGUSR1 to inject 5-baud init: kill -USR1 %d\n",
            getpid());
    fprintf(stderr, "[DEBUG] PC inicial: 0x%04X\n", cpu.mPC);
    fflush(stderr);

    // Debug: Mostra estado da UART periodicamente
    // int debug_counter = 0;  // DISABLED: not needed when verbose logging is
    // off

    // temporização: 1 MIPS (8051 real com cristal 12 MHz)
    // 8051: 12 MHz crystal / 12 cycles per instruction = 1 MIPS
    const int steps_per_tick =
        500; // quantum (1 MIPS) - DO NOT CHANGE (breaks 5-baud timing!)
    struct timespec ts{0, 500000}; // 0.5 ms

    // Track last valid PC to detect jumps to invalid regions
    uint16_t last_pc = cpu.mPC;

    // Set global CPU pointer for UART timing events
    g_uart_cpu = &cpu;

    while (g_running.load()) {
        // Check if SIGUSR1 was received - start 5-baud injector
        if (g_inject_5baud.load()) {
            g_inject_5baud = false; // Reset flag
            fprintf(stderr, "\n[SIGUSR1] Received - starting 5-baud injection "
                            "(non-blocking)\n");
            fflush(stderr);
            g_5baud_injector.start(g_instr_counter);
        }

        // Process 5-baud state machine (non-blocking, instruction-synchronized)
        g_5baud_injector.tick(g_instr_counter);

        for (int i = 0; i < steps_per_tick; ++i) {
            g_instr_counter++; // Increment BEFORE tick() to match
                               // actual instruction count

            // Stack corruption bug @ PC=0x36DF was FIXED in emu8051/opcodes.c
            // (mov_mem_indir_rx now uses correct read_mem/write_mem_indir
            // functions) Detect if PC enters invalid region (beyond 32KB ROM)
            if (cpu.mPC >= 0x8000) {
                static int alert_count = 0;
                if (alert_count <
                    3) { // Only print first 3 alerts to avoid spam
                    unsigned char acc = EMU_GET_SFR(&cpu, 0xE0);
                    unsigned char psw = EMU_GET_SFR(&cpu, 0xD0);
                    unsigned char sp = EMU_GET_SFR(&cpu, 0x81);
                    unsigned char opcode = cpu.mCodeMem[cpu.mPC & 0xFFFF];
                    fprintf(stderr,
                            "\n[ALERT] PC entrou em região inválida!\n");
                    fprintf(stderr,
                            "[ALERT] last_PC=0x%04X → current_PC=0x%04X\n",
                            last_pc, cpu.mPC);
                    fprintf(stderr, "[ALERT] Opcode em 0x%04X: 0x%02X\n",
                            cpu.mPC, opcode);
                    fprintf(stderr, "[ALERT] Code memory [0xFF9B-0xFFA0]: ");
                    for (int j = 0; j < 6; j++) {
                        fprintf(stderr, "%02X ", cpu.mCodeMem[0xFF9B + j]);
                    }
                    fprintf(stderr, "\n");
                    fprintf(stderr, "[ALERT] ACC=0x%02X PSW=0x%02X SP=0x%02X\n",
                            acc, psw, sp);
                    fprintf(stderr, "[ALERT] Stack top 4 bytes: ");
                    for (int s = 0; s < 4 && sp >= s; s++) {
                        fprintf(
                            stderr, "0x%02X ",
                            cpu.mLowerData[sp - static_cast<unsigned int>(s)]);
                    }
                    fprintf(stderr, "\n");
                    fprintf(stderr, "[ALERT] IE=0x%02X, mInterruptActive=%d\n",
                            EMU_GET_SFR(&cpu, 0xA8), cpu.mInterruptActive);
                    fflush(stderr);
                    alert_count++;
                }
                // Continue execution for now to see the pattern
            }

            last_pc = cpu.mPC;
            tick(&cpu);

            // If cpu.mPC == 0x4C72 or cpu.mPC == 0x4C73 and they already are in
            // g_pc_hist, ignore because they are busy loop
            if (((cpu.mPC == 0x4C72 || cpu.mPC == 0x4C73) &&
                 std::find_if(g_pc_hist.begin(), g_pc_hist.end(),
                              [&](uint16_t pc) {
                                  return pc == 0x4C72 || pc == 0x4C73;
                              }) != g_pc_hist.end()) ||
                (cpu.mPC >= 0x51B0 && cpu.mPC < 0x51B9)) {
                // Ignore this PC value
            } else {
                if (g_pc_hist_idx < g_pc_hist.size()) {
                    g_pc_hist[g_pc_hist_idx++] = cpu.mPC;
                } else {
                    // Lets move and discard byte and push to the end
                    memmove(&g_pc_hist[0], &g_pc_hist[1],
                            (g_pc_hist.size() - 1) * sizeof(uint16_t));
                    g_pc_hist[g_pc_hist.size() - 1] = cpu.mPC;
                }
            }

            // Process cycle-accurate UART timing events
            uart_timing_tick(&cpu, g_instr_counter);

            detect_isr_call(&cpu); // Detect ISR vector calls

            // NOTE: RX injection agora é handled por eventos UART
            // (cycle-accurate: dispara após ~9.5 bit times)
            // Não precisa mais de polling ou callbacks imediatos!

            // DEBUG: Trace PC when stuck in high-priority ISR
            static int64_t main_loop_counter = 0;
            static int64_t last_trace_at = 0;
            main_loop_counter++;
            if (cpu.mInterruptActive == 2 &&
                (main_loop_counter - last_trace_at) > 500 &&
                main_loop_counter < 100000) {
                fprintf(stderr,
                        "[MAIN-TF0-TRACE] PC=0x%04X SP=0x%02X loop=%ld\n",
                        cpu.mPC, cpu.mSFR[REG_SP], main_loop_counter);
                last_trace_at = main_loop_counter;
            }

            // RAM_17 (K-line enabled flag)
            static unsigned char last_ram_17 = 0x00;
            unsigned char current_ram_17 = cpu.mLowerData[0x17];
            if (current_ram_17 != last_ram_17) {
                fprintf(stderr, "[RAM_17] 0x%02X → 0x%02X (PC=0x%04X)\n",
                        last_ram_17, current_ram_17, cpu.mPC);
                fflush(stderr);
                last_ram_17 = current_ram_17;
            }

            // K-line decoder instrumentation
            static int decoder_trace_count = 0;
            static unsigned char last_ram_40_decoder = 0xFF;

            // PC=0x4C34: Actual shift register for slow-init decoding (not
            // 0x4C3A!) 0x4C3A is just a jump to 0x4C80
            if (cpu.mPC == 0x4C34 && decoder_trace_count < 200) {
                unsigned char ram_40 = cpu.mLowerData[0x40];
                unsigned char p4 = cpu.mSFR[SFR_P4 - 0x80];
                unsigned char p4_bit5 =
                    (p4 >> 5) & 1; // Bit 5 of P4 (K-line RX)

                // Only print when RAM_40 changes to reduce spam
                if (ram_40 != last_ram_40_decoder) {
                    fprintf(
                        stderr,
                        "[DECODER-4C34] Instr=%lld RAM_40: 0x%02X → 0x%02X (0b",
                        g_instr_counter, last_ram_40_decoder, ram_40);
                    for (int bit_idx = 7; bit_idx >= 0; bit_idx--) {
                        fprintf(stderr, "%d", (ram_40 >> bit_idx) & 1);
                    }
                    fprintf(stderr, ") P4.5=%d\n", p4_bit5);
                    last_ram_40_decoder = ram_40;
                }
                decoder_trace_count++;
                fflush(stderr);
            }

            // PC=0x4C44: Check if received address == 0x10
            if (cpu.mPC == 0x4C44 && decoder_trace_count < 200) {
                fprintf(stderr,
                        "[DECODER-4C44] Entry: RAM_17=0x%02X, RAM_40=0x%02X, "
                        "A=0x%02X\n",
                        cpu.mLowerData[0x17], cpu.mLowerData[0x40],
                        cpu.mSFR[REG_ACC]);
                decoder_trace_count++;
                fflush(stderr);
            }

            // PC=0x4C48: About to compare A with 0x10
            if (cpu.mPC == 0x4C48 && decoder_trace_count < 200) {
                fprintf(stderr,
                        "[DECODER-4C48] Before cmp: A=0x%02X (expect 0x10), "
                        "RAM_40=0x%02X\n",
                        cpu.mSFR[REG_ACC], cpu.mLowerData[0x40]);
                decoder_trace_count++;
                fflush(stderr);
            }

            // PC=0x4C4A: After loading 0x10, before CJNE
            if (cpu.mPC == 0x4C4A && decoder_trace_count < 200) {
                fprintf(stderr,
                        "[DECODER-4C4A] CJNE A, RAM_40: A=0x%02X vs "
                        "RAM_40=0x%02X (need match!)\n",
                        cpu.mSFR[REG_ACC], cpu.mLowerData[0x40]);
                decoder_trace_count++;
                fflush(stderr);
            }

            // RAM_47 (watchdog counter - triggers reset if 0!)
            static unsigned char last_ram_47 = 0xFF;
            unsigned char current_ram_47 = cpu.mLowerData[0x47];
            if (current_ram_47 != last_ram_47) {
                fprintf(stderr, "[RAM_47] 0x%02X → 0x%02X (PC=0x%04X) %s\n",
                        last_ram_47, current_ram_47, cpu.mPC,
                        (current_ram_47 == 0) ? "**TRIGGERS RESET!**" : "");
                fflush(stderr);
                last_ram_47 = current_ram_47;
            }

            // Track PC @ 0x01AB (loads XRAM[0xF8] → RAM_47)
            static bool seen_01ab = false;
            if (cpu.mPC == 0x01AB && !seen_01ab) {
                fprintf(stderr,
                        "[PC=0x01AB] Loading XRAM[0xF8]=%02X → RAM_47\n",
                        cpu.mExtData[0xF8]);
                fflush(stderr);
                seen_01ab = true;
            }

            // Track all paths that lead to RESET_0 @ 0x4B85
            static bool seen_4b85 = false;
            static uint16_t last_pc_before_reset = 0;
            if (cpu.mPC == 0x4B85 && !seen_4b85) {
                fprintf(stderr,
                        "[RESET TRIGGER] PC=0x4B85 (ljmp RESET_0), came from "
                        "PC=0x%04X\n",
                        last_pc_before_reset);
                fprintf(stderr,
                        "[RESET TRIGGER] RAM_47=0x%02X, triggering full system "
                        "reset\n",
                        cpu.mLowerData[0x47]);
                fflush(stderr);
                seen_4b85 = true;
            }
            last_pc_before_reset = cpu.mPC;

            // Track when we enter Timer 0 ISR watchdog check @ 0x4B65
            static bool seen_4b65 = false;
            if (cpu.mPC == 0x4B65 && !seen_4b65) {
                fprintf(stderr, "[WATCHDOG CHECK] PC=0x4B65, RAM_47=0x%02X\n",
                        cpu.mLowerData[0x47]);
                fflush(stderr);
                seen_4b65 = true;
            }

            // Track RESET_0 entry @ 0x0850
            static int reset_0_count = 0;
            static uint16_t last_pc_before_0850 = 0;
            if (cpu.mPC == 0x0850) {
                reset_0_count++;
                if (reset_0_count <= 3) { // Log first 3 resets only
                    fprintf(stderr,
                            "[RESET_0 ENTRY #%d] PC=0x0850, came from "
                            "PC=0x%04X, SP=0x%02X\n",
                            reset_0_count, last_pc_before_0850,
                            cpu.mSFR[REG_SP]);
                    fflush(stderr);
                }
            }
            last_pc_before_0850 = cpu.mPC;

            /*{
                uint8_t ram_45 = cpu.mLowerData[0x45];

                static uint8_t last_ram_45 = ram_45;
                if (ram_45 != last_ram_45) {
                    auto *callstack = cpu_callstack(&cpu);
                    fprintf(stderr, "[RAM_45] 0x%02X → 0x%02X (PC=0x%04X) %s\n",
                            last_ram_45, ram_45, cpu.mPC, callstack);
                    fflush(stderr);
                    last_ram_45 = ram_45;
                }
            }*/

            // STACK OVERFLOW DETECTION
            // 8051 stack: SP points to last written byte
            // Normal range: 0x08-0xDF (init SP=0xD0, grows upward)
            // Underflow: SP < 0x08
            // Overflow: SP > 0xDF (enters SFR region @ 0x80-0xFF indirect
            // addressing)
            static unsigned char last_sp = 0xD0;
            static unsigned char min_sp_seen = 0xFF;
            static unsigned char max_sp_seen = 0x00;
            unsigned char current_sp = cpu.mSFR[REG_SP];

            // Track min/max SP
            if (current_sp < min_sp_seen)
                min_sp_seen = current_sp;
            if (current_sp > max_sp_seen)
                max_sp_seen = current_sp;

            // Detect underflow (SP went below safe zone)
            if (current_sp < 0x08 && last_sp >= 0x08) {
                fprintf(stderr,
                        "[STACK UNDERFLOW] SP: 0x%02X → 0x%02X (PC=0x%04X)\n",
                        last_sp, current_sp, cpu.mPC);
                fprintf(stderr, "[STACK RANGE] Min=0x%02X Max=0x%02X\n",
                        min_sp_seen, max_sp_seen);
                fflush(stderr);
            }

            // Detect overflow (SP went above Upper RAM boundary)
            // Upper RAM @ 0x80-0xFF is accessed via @R0/@R1, not stack
            // Stack overflow if SP > 0x7F
            if (current_sp > 0x7F && last_sp <= 0x7F) {
                fprintf(stderr,
                        "[STACK OVERFLOW] SP: 0x%02X → 0x%02X (PC=0x%04X)\n",
                        last_sp, current_sp, cpu.mPC);
                fprintf(stderr, "[STACK RANGE] Min=0x%02X Max=0x%02X\n",
                        min_sp_seen, max_sp_seen);
                fflush(stderr);
            }

            // Detect SP = 0x00 (critical underflow)
            if (current_sp == 0x00 && last_sp != 0x00) {
                fprintf(stderr,
                        "[STACK CRITICAL] SP reached 0x00! (PC=0x%04X, "
                        "last_SP=0x%02X)\n",
                        cpu.mPC, last_sp);
                // Show stack top bytes
                fprintf(stderr, "[STACK DUMP] Stack[0x00-0x07]: ");
                for (int j = 0; j <= 7; j++) {
                    fprintf(stderr, "%02X ", cpu.mLowerData[j]);
                }
                fprintf(stderr, "\n");
                fflush(stderr);
            }

            last_sp = current_sp;

            // K-line decoder traces disabled - enable if needed for debugging
        }

        // Read PTY: detect BREAK, echo bytes (K-line half-duplex), queue for
        // UART RX
        g_uart.read_and_process();

        // Sleep to maintain ~1-2 MIPS logical speed
        nanosleep(&ts, nullptr);
    }

    printf("\n[emu8051-pty] Encerrando.\n");
    return 0;
}
