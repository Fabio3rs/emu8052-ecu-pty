#include "ma17/CpuHooks.hpp"
#include "ma17/Diagnostics.hpp"

#include "ma17/AdcSimulator.hpp"
#include "ma17/InterruptTracer.hpp"
#include "ma17/PortController.hpp"
#include "ma17/UartScheduler.hpp"
#include "ma17/XramAccess.hpp"

extern "C" {
#include "emu8051.h"
}

#include <array>
#include <cassert>
#include <cstdio>
#include <cstdlib>

namespace ma17 {

CpuHooks *CpuHooks::active_ = nullptr;

CpuHooks::CpuHooks(UartScheduler &uart, PortController &ports, long long &ticks)
    : uart_(uart), ports_(ports), ticks_(ticks) {
    assert(active_ == nullptr);
    active_ = this;
}

CpuHooks::~CpuHooks() { active_ = nullptr; }

void CpuHooks::sbuf_write(em8051 *cpu, uint8_t) {
    active_->uart_.on_sbuf_write(cpu);
}

uint8_t CpuHooks::sbuf_read(em8051 *cpu, uint8_t address) {
    return active_->uart_.on_sbuf_read(cpu, address);
}

uint8_t CpuHooks::scon_read(em8051 *cpu, uint8_t address) {
    return active_->uart_.on_scon_read(cpu, address);
}

void CpuHooks::scon_write(em8051 *cpu, uint8_t address) {
    active_->uart_.on_scon_write(cpu, address);
}

uint8_t CpuHooks::port_read(em8051 *cpu, uint8_t address) {
    return active_->ports_.read(cpu, address);
}

void CpuHooks::port_write(em8051 *, uint8_t) {}

namespace {
// MA17_XRAM_WRITE_PROFILE=path: per-address write profile of the retained page (F800h..FBFFh): number of writes,
// number of value changes and up to 6 distinct writer PCs (mPC at the MOVX, +-1 instruction), written at exit.
struct XramWriteProfile {
    std::array<unsigned long long, 0x400> writes{};
    std::array<unsigned long long, 0x400> changes{};
    std::array<std::array<uint16_t, 6>, 0x400> pcs{};
    std::array<uint8_t, 0x400> pc_count{};
    std::array<int, 0x400> last{};
    const char *path = nullptr;
    XramWriteProfile() {
        path = std::getenv("MA17_XRAM_WRITE_PROFILE");
        last.fill(-1);
    }
    ~XramWriteProfile() {
        if (!path) return;
        FILE *out = std::fopen(path, "w");
        if (!out) return;
        std::fprintf(out, "address,writes,changes,pcs\n");
        for (unsigned i = 0; i < 0x400; ++i) {
            if (!writes[i]) continue;
            std::fprintf(out, "F%03X,%llu,%llu,", 0x800 + i, writes[i], changes[i]);
            for (unsigned k = 0; k < pc_count[i]; ++k)
                std::fprintf(out, "%s%04X", k ? " " : "", pcs[i][k]);
            std::fprintf(out, "\n");
        }
        std::fclose(out);
    }
};
XramWriteProfile g_xram_profile;
} // namespace

void CpuHooks::xram_write(em8051 *cpu, uint16_t address, uint8_t value) {
    if (g_xram_profile.path && address >= 0xF800 && address < 0xFC00) {
        const unsigned i = address - 0xF800u;
        ++g_xram_profile.writes[i];
        if (g_xram_profile.last[i] != value) ++g_xram_profile.changes[i];
        g_xram_profile.last[i] = value;
        const uint16_t pc = static_cast<uint16_t>(cpu->mPC);
        bool seen = false;
        for (unsigned k = 0; k < g_xram_profile.pc_count[i]; ++k) seen = seen || g_xram_profile.pcs[i][k] == pc;
        if (!seen && g_xram_profile.pc_count[i] < 6) g_xram_profile.pcs[i][g_xram_profile.pc_count[i]++] = pc;
    }
    write_xram(cpu, address, value, active_->ticks_);
}

void CpuHooks::install_uart(em8051 &cpu) {
    cpu.sfrwrite[0x99 - 0x80] = sbuf_write;
    cpu.sfrread[0x99 - 0x80] = sbuf_read;
    diagnostic_log(stderr,
            "[DEBUG] Callback registrado: SBUF (0x%02X) -> UART TX/RX\n",
            0x99u);
    fflush(stderr);

    cpu.sfrwrite[0x98 - 0x80] = scon_write;
    cpu.sfrread[0x98 - 0x80] = scon_read;
    diagnostic_log(stderr,
            "[DEBUG] Callback registrado: S0CON (0x%02X) -> Zero-latency RX "
            "injection\n",
            0x98u);
    fflush(stderr);
}

void CpuHooks::install_fiat_peripherals(em8051 &cpu) {
    cpu.sfrread[0xE8 - 0x80] = port_read;
    cpu.sfrwrite[0xE8 - 0x80] = port_write;
    diagnostic_log(stderr, "[DEBUG] Callback registrado: P4 (0x%02X) -> cb_sfr_read\n",
            0xE8u);
    fflush(stderr);

    cpu.sfrread[0xF8 - 0x80] = port_read;
    diagnostic_log(stderr,
            "[DEBUG] Callback registrado: P5 (0x%02X) -> cb_sfr_read "
            "(external-high=%s)\n",
            0xF8u, std::getenv("MA17_P5_FORCE_HIGH") ? "on" : "off");
    fflush(stderr);

    cpu.sfrwrite[0xA8 - 0x80] = trace_ie_write;
    diagnostic_log(stderr, "[DEBUG] Callback registrado: IE write monitor\n");
    fflush(stderr);

    // B8h is IEN1 on SAB80C517, not the generic 8051 priority register.
    cpu.sfrwrite[0xB8 - 0x80] = trace_ien1_write;
    diagnostic_log(stderr, "[DEBUG] Callback registrado: IEN1 (0xB8) write monitor\n");
    fflush(stderr);

    cpu.except = trace_cpu_exception;
    diagnostic_log(stderr, "[DEBUG] Callback registrado: exception handler\n");
    fflush(stderr);

    cpu.xread = read_xram;
    cpu.xwrite = xram_write;
    diagnostic_log(stderr,
            "[DEBUG] XRAM trace callbacks registrados (0xD0/0xD1 monitor)\n");
    fflush(stderr);

    // SAB80C517A User's Manual Addendum, ADC timing (p. 5-7): writing
    // ADDATL starts conversion and IRCON0.0 signals completion. Completion
    // remains immediate here; conversion latency is not yet simulated.
    cpu.mSFR[0xC0 - 0x80] = 0x01;
    cpu.sfrwrite[0xC0 - 0x80] = write_ircon;
    diagnostic_log(stderr,
            "[WORKAROUND] IRCON callback registered (fake ADC ready)\n");

    // SAB80C517A ADC registers (p. 5-6): D9h is ADDATH and DAh is
    // ADDATL, unlike the older SAB80C517 map where DAh was DAPR.
    cpu.sfrread[0xD9 - 0x80] = read_addat;
    cpu.sfrread[0xDA - 0x80] = read_addatl;
    cpu.sfrwrite[0xDA - 0x80] = start_adc_conversion;
    diagnostic_log(stderr,
            "[WORKAROUND] ADDATH/ADDATL callbacks registered "
            "(simulated 10-bit ADC values)\n");
}

} // namespace ma17
