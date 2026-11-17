#pragma once

#include "Lifetime.hpp"

#include <cstdint>

struct em8051;

namespace ma17 {

class PortController;
class UartScheduler;

// The C emulator accepts plain function pointers; this object owns their
// runtime dependencies while one ECU instance is active.
class CpuHooks {
  public:
    CpuHooks(UartScheduler &uart EMU_LIFETIMEBOUND,
             PortController &ports EMU_LIFETIMEBOUND,
             long long &ticks EMU_LIFETIMEBOUND);
    ~CpuHooks();
    CpuHooks(const CpuHooks &) = delete;
    CpuHooks &operator=(const CpuHooks &) = delete;

    void install_uart(em8051 &cpu);
    void install_fiat_peripherals(em8051 &cpu);

  private:
    static CpuHooks *active_;
    static void sbuf_write(em8051 *cpu, uint8_t address);
    static uint8_t sbuf_read(em8051 *cpu, uint8_t address);
    static uint8_t scon_read(em8051 *cpu, uint8_t address);
    static void scon_write(em8051 *cpu, uint8_t address);
    static uint8_t port_read(em8051 *cpu, uint8_t address);
    static void port_write(em8051 *cpu, uint8_t address);
    static void xram_write(em8051 *cpu, uint16_t address, uint8_t value);

    UartScheduler &uart_;
    PortController &ports_;
    long long &ticks_;
};

} // namespace ma17
