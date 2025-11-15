// emu8051_pty_harness.cpp
// Pequeno "harness" de integração do núcleo emu8051 com um PTY
// - Carrega sua ROM crua (ex.: 27C256, 32 KiB) no espaço de código (program
// memory)
// - Liga/expõe um PTY em 4800 8N1
// - Emula UART básica via SFR SCON/SBUF (TX imediato, RX por polling) —
// suficiente para testes do scanner
// - Opcionalmente habilita recursos 8052 (Timer2, RAM extra)
//
// AVISOS IMPORTANTES:
// 1) Os nomes de funções/callbacks e campos da struct `em8051` podem variar
// entre revisões.
//    Confira exatamente em `emulator.h`/`emu8051.h` do jarikomppa/emu8051 e
//    ajuste os #defines abaixo.
// 2) Este harness não é cycle-accurate; TI é setado logo após o write em SBUF,
// e RI quando um byte chega do PTY.
//    Para testes de protocolo (ACK/eco invertido etc.) isso costuma ser
//    suficiente.
//
// ============================================================================
// WORKAROUNDS PARA FUNCIONALIDADE NÃO EMULADA (SAB80C537 ECU BOSCH)
// ============================================================================
//
// Este firmware espera hardware específico do microcontrolador SAB80C537
// (usado em ECUs Bosch Motronic MA1.7). Como o emulador jarikomppa/emu8051
// só implementa 8051/8052 básico, precisamos emular periféricos ausentes:
//
// 1. WORKAROUND: IP0 Interrupt Priority Fix (cb_sfr_write_ip0)
//    Problema: Firmware configura IP0 = 0x39 (PT2=HIGH, PT0=LOW)
//              Timer 2 (high priority) monopoliza CPU, bloqueia Timer 0
//    Impacto:  Timer 0 ISR nunca executa → sem detecção K-line 5-baud
//    Solução:  Callback força PT0=1 (ambos timers HIGH priority)
//    Arquivo:  src/main.cpp, função cb_sfr_write_ip0() linha ~334
//    Registro: IP0 = 0xB8
//
// 2. WORKAROUND: ADC Emulation (cb_sfr_write_ircon)
//    Problema: Timer 0 ISR espera flag ADC pronto (IRCON.0) em busy-wait loop
//              Loop: jbc IRCON.0, next; sjmp loop (código 0x0711-0x0714)
//    Impacto:  Timer 0 ISR trava eternamente → mInterruptActive=2 permanente
//    Solução:  Callback força IRCON.0=1 após cada escrita (simula ADC sempre
//    pronto) Arquivo:  src/main.cpp, função cb_sfr_write_ircon() linha ~467
//    Registro: IRCON = 0xC0 (SAB80C537 specific)
//
// Sem esses workarounds, o emulador trava completamente após primeira
// interrupção Timer 0, impossibilitando comunicação K-line.
//
// ============================================================================
//
// Compilar (exemplo):
//   g++ -O2 -std=c++17 emu8051_pty_harness.cpp core.c opcodes.c disasm.c
//   options.c -lutil -lpthread -o emu8051-pty
// Executar:
//   ./emu8051-pty rom.bin --8052
//   # o programa imprime o caminho do PTY (por ex. /dev/pts/12). Conecte seu
//   scanner nesse dispositivo.

extern "C" {
#include <errno.h>
#include <fcntl.h>
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

// 3) As funções do emu8051 já estão declaradas em emu8051.h, que é incluído via
// <emu8051.h> Não precisamos redeclará-las aqui

// 4) Callbacks de leitura/escrita em SFR/XRAM (nem todo fork exige; alguns
// apenas notificam) Se seu fork oferecer "hooks", exponha-os aqui. Ex.:
// set_sfr_read_cb/cb_write etc. Caso não existam, este harness fará polling
// direto nos SFRs após cada step.
struct HooksAPI {
    bool has_hooks = false;
    // ponteiros para registro de callbacks, se existirem
    void (*set_sfr_read)(em8051 *, int (*)(em8051 *, int)) = nullptr;
    void (*set_sfr_write)(em8051 *, void (*)(em8051 *, int, int)) = nullptr;
};

static HooksAPI g_hooks;

// =========================
// UART/SCON helpers (8051)
// =========================
static constexpr int SFR_SCON = 0x98; // SM0..RI
static constexpr int SFR_SBUF = 0x99; // buffer
// Bits de SCON
[[maybe_unused]] static constexpr unsigned char SCON_SM0 = 0x80;
[[maybe_unused]] static constexpr unsigned char SCON_SM1 = 0x40;
[[maybe_unused]] static constexpr unsigned char SCON_SM2 = 0x20;
static constexpr unsigned char SCON_REN = 0x10;
[[maybe_unused]] static constexpr unsigned char SCON_TB8 = 0x08;
[[maybe_unused]] static constexpr unsigned char SCON_RB8 = 0x04;
static constexpr unsigned char SCON_TI = 0x02;
static constexpr unsigned char SCON_RI = 0x01;

struct UartBridge {
    int mfd = -1; // master pty
    int sfd = -1; // slave pty
    std::string slave_path;

    // K-line BREAK detection state
    bool rxd_line_state = true; // true=MARK(idle/high), false=SPACE(break/low)
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

        if (tcsetattr(sfd, TCSANOW, &tio) < 0) {
            perror("tcsetattr");
            return false;
        }

        // Non-blocking no master
        int flags = fcntl(mfd, F_GETFL, 0);
        fcntl(mfd, F_SETFL, flags | O_NONBLOCK);

        slave_path = namebuf;
        fprintf(stderr, "[DEBUG] Configuração PTY concluída com sucesso\n");
        fflush(stderr);
        return true;
    }

    // envia byte para o terminal
    void tx(unsigned char b) {
        if (mfd >= 0)
            (void)!write(mfd, &b, 1);
    }

    // Tenta ler 1 byte da queue RX; retorna -1 se vazia
    // A queue é preenchida por read_and_process() após filtragem PARMRK
    int rx_try() {
        if (rx_queue.empty())
            return -1;
        unsigned char b = rx_queue.front();
        rx_queue.pop();
        return static_cast<int>(b);
    }

    // Read from PTY, detect BREAK, echo bytes, and queue for UART RX
    // PARMRK mode: BREAK appears as 0xFF 0x00 0x00
    // K-line protocol: ALL bytes must be echoed back (half-duplex validation)
    void read_and_process() {
        unsigned char b = 0;
        ssize_t n = read(mfd, &b, 1);
        if (n != 1)
            return;

        // PARMRK BREAK pattern detection state machine
        if (break_detect_idx == 0) {
            if (b == 0xFF) {
                // Possible BREAK or escaped 0xFF - wait for next byte
                break_detect_buffer[0] = b;
                break_detect_idx = 1;
                return;
            }
            // Normal data byte: ECHO + QUEUE + mark line as HIGH
            (void)!write(mfd, &b, 1); // K-line echo (half-duplex)
            rx_queue.push(b);
            rxd_line_state = true;
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
                (void)!write(mfd, &ff, 1); // Echo the 0xFF
                rx_queue.push(ff);
                rxd_line_state = true;
                break_detect_idx = 0;
                return;
            } else {
                // Was start of something else - echo and queue both bytes
                (void)!write(mfd, break_detect_buffer, 2);
                rx_queue.push(break_detect_buffer[0]);
                rx_queue.push(b);
                rxd_line_state = true;
                break_detect_idx = 0;
                return;
            }
        }

        if (break_detect_idx == 2) {
            break_detect_buffer[2] = b;
            if (b == 0x00) {
                // BREAK confirmed! (0xFF 0x00 0x00 pattern complete)
                rxd_line_state = false; // Line goes LOW (SPACE/BREAK)
                low_until_ms =
                    now_ms() + 190; // mantém LOW por ~200 ms (5 baud)
                fprintf(stderr, "[K-LINE] BREAK detected (RXD=LOW)\n");
                fflush(stderr);
                // Do NOT echo BREAK, do NOT queue
            } else {
                // Framing error or other pattern - treat as data
                // Echo and queue the actual byte value
                (void)!write(mfd, &b, 1);
                rx_queue.push(b);
                rxd_line_state = true;
            }
            break_detect_idx = 0;
            return;
        }
    }
};

static UartBridge g_uart;
static std::atomic<bool> g_running{true};

static void sigint_handler(int) { g_running = false; }

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
    unsigned char ip0_val = cpu->mSFR[addr - 0x80];
    static int ip0_write_count = 0;

    // HACK: ALWAYS force Timer 0 to HIGH priority to prevent Timer 2 from
    // blocking it Original firmware sets: IP0 = 0x39 = 0b00111001 (PT0=0,
    // PT2=1) We modify to:          IP0 = 0x3B = 0b00111011 (PT0=1, PT2=1) This
    // allows Timer 0 ISR to run for 5-baud P4.5 sampling
    if ((ip0_val & 0x02) == 0) { // If PT0 (bit 1) is 0
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
    }
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
    // Port 4 (P4) read - used by ROM to sample RX line state for 5-baud init
    if (addr == SFR_P4) {
        // Atualiza linha: após o tempo, volta a HIGH (MARK)
        if (g_uart.low_until_ms &&
            UartBridge::now_ms() >= g_uart.low_until_ms) {
            g_uart.rxd_line_state = true;
            g_uart.low_until_ms = 0;
        }
        // Update P4.5 based on current RX line state
        unsigned char p4 = p4_value;
        if (g_uart.rxd_line_state) {
            p4 |=
                static_cast<unsigned char>(1 << 5); // Set P4.5 high (MARK/idle)
        } else {
            p4 &= static_cast<unsigned char>(~static_cast<unsigned char>(
                1 << 5)); // Clear P4.5 low (SPACE/break)
        }

        // Only log when P4.5 bit changes (avoid flood)
        static unsigned char last_p4_value = 0xFF;
        if (p4 != last_p4_value) {
            fprintf(stderr, "[P4.5] Read: 0x%02X (RXD=%s)\n", p4,
                    g_uart.rxd_line_state ? "HIGH" : "LOW");
            fflush(stderr);
            last_p4_value = p4;
        }

        p4_value = p4;
        return p4;
    }

    // For other SFR addresses, return the value from mSFR array
    return cpu->mSFR[addr - 0x80];
}

// Estado para detectar mudanças de SBUF/SCON (polling de TX)
static unsigned char last_sbuf = 0;
static unsigned char last_scon = 0;
static bool uart_initialized = false;

// Polling de RX/TX caso não haja hooks
static inline void uart_poll_nohooks(em8051 *cpu) {
    unsigned char scon = EMU_GET_SFR(cpu, SFR_SCON);
    unsigned char sbuf = EMU_GET_SFR(cpu, SFR_SBUF);

    // Inicialização
    if (!uart_initialized) {
        last_scon = scon;
        last_sbuf = sbuf;
        uart_initialized = true;
    }

    // Debug: detecta mudanças em SCON (especialmente RI flag)
    if (scon != last_scon) {
        unsigned char ri_old = last_scon & SCON_RI;
        unsigned char ri_new = scon & SCON_RI;
        if (ri_old != ri_new) {
            fprintf(
                stderr,
                "[SCON] RI mudou: %d → %d (PC=0x%04X, SCON: 0x%02X → 0x%02X)\n",
                ri_old ? 1 : 0, ri_new ? 1 : 0, cpu->mPC, last_scon, scon);
            fflush(stderr);
        }
    }

    // TX: Detecta escrita em SBUF quando TI estava em 0
    // (Write to SBUF clears TI, then we detect it and send to PTY)
    if (sbuf != last_sbuf && !(last_scon & SCON_TI)) {
        // Byte foi escrito em SBUF, envia para PTY
        g_uart.tx(sbuf);

        // Seta TI (transmissão completa - instantânea no nosso caso)
        scon |= SCON_TI;
        EMU_SET_SFR(cpu, SFR_SCON, scon);

        fprintf(stderr, "[UART TX] 0x%02X\n", sbuf);
        fflush(stderr);
    }

    // RX: PTY -> injeta em SBUF e seta RI se REN=1
    int ch = g_uart.rx_try();
    if (ch >= 0) {
        if (scon & SCON_REN) {
            EMU_SET_SFR(cpu, SFR_SBUF, static_cast<unsigned char>(ch));
            scon |= SCON_RI;
            EMU_SET_SFR(cpu, SFR_SCON, scon);

            fprintf(stderr, "[UART RX] 0x%02X\n", static_cast<unsigned>(ch));
            fflush(stderr);
        }
    }

    // Atualiza estado anterior
    last_sbuf = sbuf;
    last_scon = scon;
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

    // Reset - agora é seguro chamar com aWipe=true
    fprintf(stderr, "[DEBUG] Chamando reset()...\n");
    fflush(stderr);
    reset(&cpu, true);

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

    // HACK: Register IRCON write callback to prevent infinite loop in Timer 0
    // ISR SAB80C537 IRCON register at 0xC0, bit 0 = IADC (ADC interrupt flag)
    // Timer 0 ISR waits for this bit at code_711: jbc IRCON.0, code_716
    // JBC clears the bit after testing - callback immediately sets it back to 1
    cpu.mSFR[0xC0 - 0x80] = 0x01;                   // Initial: IRCON.0 = 1
    cpu.sfrwrite[0xC0 - 0x80] = cb_sfr_write_ircon; // IRCON = 0xC0
    fprintf(stderr, "[ADC-HACK] IRCON write callback registered (fake ADC "
                    "ready to prevent infinite loop)\n");
    fflush(stderr);

    // SCON modo 1 (8-bit UART, variável): SM0=0, SM1=1 por padrão de muitas
    // ROMs Forçar estado limpo: Mode 1, REN=1, flags TI/RI limpos Isso evita
    // que a ROM fique presa aguardando um byte esp��rio lido durante reset
    EMU_SET_SFR(&cpu, SFR_SCON, 0x50); // 01010000 = SM1=1, REN=1, TI=0, RI=0
    EMU_SET_SFR(&cpu, SFR_SBUF, 0x00); // Limpa SBUF também

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

    fprintf(stderr, "[DEBUG] Iniciando loop principal de emulação...\n");
    fprintf(stderr, "[DEBUG] PC inicial: 0x%04X\n", cpu.mPC);
    fflush(stderr);

    // Debug: Mostra estado da UART periodicamente
    // int debug_counter = 0;  // DISABLED: not needed when verbose logging is
    // off

    // temporização: 1 MIPS (8051 real com cristal 12 MHz)
    // 8051: 12 MHz crystal / 12 cycles per instruction = 1 MIPS
    const int steps_per_tick = 500; // quantum (1 MIPS)
    struct timespec ts{0, 500000};  // 0.5 ms

    // Track last valid PC to detect jumps to invalid regions
    uint16_t last_pc = cpu.mPC;

    while (g_running.load()) {
        for (int i = 0; i < steps_per_tick; ++i) {
            // Detect if PC enters invalid region (beyond 32KB ROM)
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
            detect_isr_call(&cpu); // Detect ISR vector calls

            // DEBUG: Trace PC when stuck in high-priority ISR
            static int main_loop_counter = 0;
            static int last_trace_at = 0;
            main_loop_counter++;
            if (cpu.mInterruptActive == 2 &&
                (main_loop_counter - last_trace_at) > 500 &&
                main_loop_counter < 100000) {
                fprintf(stderr,
                        "[MAIN-TF0-TRACE] PC=0x%04X SP=0x%02X loop=%d\n",
                        cpu.mPC, cpu.mSFR[REG_SP], main_loop_counter);
                last_trace_at = main_loop_counter;
            }
        }

        // Read PTY: detect BREAK, echo bytes (K-line half-duplex), queue for
        // UART RX
        g_uart.read_and_process();

        if (!g_hooks.has_hooks)
            uart_poll_nohooks(&cpu);

        // Debug periódico (a cada ~0.5s)
        // DISABLED: Verbose logging for production testing
        /*
        if (++debug_counter >= 1) {
          debug_counter = 0;
          unsigned char scon_dbg = EMU_GET_SFR(&cpu, SFR_SCON);
          unsigned char sbuf_dbg = EMU_GET_SFR(&cpu, SFR_SBUF);

          // Special detailed logging when stuck at 0x15CA
          if (cpu.mPC == 0x15CA) {
            unsigned char acc = EMU_GET_SFR(&cpu, 0xE0);  // ACC register
            unsigned char b_reg = EMU_GET_SFR(&cpu, 0xF0); // B register
            unsigned char ie = EMU_GET_SFR(&cpu, 0xA8);    // IE (interrupt
        enable)
            // Address 0x87 via indirect addressing (@R0) accesses upper
        internal RAM
            // (mUpperData[0x87 - 0x80] = mUpperData[7]) if 8052 mode, otherwise
        undefined unsigned char ram_87 = (cpu.mUpperData != nullptr) ?
        cpu.mUpperData[0x87 - 0x80] : 0xFF; fprintf(stderr, "[DEBUG] *** STUCK
        AT 0x15CA ***\n"); fprintf(stderr, "[DEBUG]     A=0x%02X  B=0x%02X
        RAM[0x87]=0x%02X (upper RAM)\n", acc, b_reg, ram_87); fprintf(stderr,
        "[DEBUG]     IE=0x%02X  mInterruptActive=%d\n", ie,
        cpu.mInterruptActive); fprintf(stderr, "[DEBUG]     SCON=0x%02X
        SBUF=0x%02X\n", scon_dbg, sbuf_dbg); fprintf(stderr, "[DEBUG]
        mUpperData=%s\n", cpu.mUpperData ? "ALLOCATED" : "NULL");
            fflush(stderr);
          } else {
            fprintf(stderr, "[DEBUG] PC=0x%04X SCON=0x%02X SBUF=0x%02X\n",
                    cpu.mPC, scon_dbg, sbuf_dbg);
            fflush(stderr);
          }
        }
        */

        // dá um respiro para o SO e mantém o terminal responsivo
        nanosleep(&ts, nullptr);
    }

    printf("\n[emu8051-pty] Encerrando.\n");
    return 0;
}
