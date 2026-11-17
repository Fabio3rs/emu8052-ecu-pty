#pragma once

#include "ma17/PtyBridge.hpp"

#include <cstdint>
#include <queue>

struct em8051;

namespace ma17 {

// Models the Fiat MA1.7 UART's separate SBUF paths and tick-delayed TI/RI.
class UartScheduler {
  public:
    UartScheduler(PtyBridge &pty_bridge, long long &emulated_ticks)
        : bridge_(pty_bridge), ticks_(emulated_ticks) {}

    void bind_cpu(em8051 *cpu);
    void reset_for_run();
    void reset_buffers();
    void on_scanner_byte(uint8_t byte);
    void on_sbuf_write(em8051 *cpu);
    uint8_t on_sbuf_read(em8051 *cpu, uint8_t address) const;
    uint8_t on_scon_read(em8051 *cpu, uint8_t address);
    void on_scon_write(em8051 *cpu, uint8_t address);
    void tick(em8051 *cpu, long long current_tick);

  private:
    enum class EventKind : uint8_t { TxDone, RxByte };
    struct Event {
        long long when_tick;
        EventKind kind;
        uint8_t data;

        bool operator<(const Event &other) const {
            return when_tick > other.when_tick;
        }
    };

    static constexpr uint8_t scon_address = 0x98;
    static constexpr uint8_t sbuf_address = 0x99;
    static constexpr uint8_t scon_ren = 0x10;
    static constexpr uint8_t scon_ti = 0x02;
    static constexpr uint8_t scon_ri = 0x01;

    static long long bit_ticks();
    void schedule_tx_done();
    void schedule_rx_byte(uint8_t byte);
    static double ticks_to_ms(long long ticks);

    PtyBridge &bridge_;
    long long &ticks_;
    em8051 *cpu_ = nullptr;
    uint8_t sbuf_tx_ = 0;
    uint8_t sbuf_rx_ = 0;
    uint8_t previous_scon_ = 0x50;
    int scon_write_count_ = 0;
    std::priority_queue<Event> events_;
};

} // namespace ma17
