#include "ma17/UartScheduler.hpp"

extern "C" {
#include "emu8051.h"
}

#include <cmath>
#include <cstdio>

namespace ma17 {

namespace {
constexpr double fiat_clock_hz = 11'880'000.0;
constexpr double uart_baud = 4800.0;
} // namespace

void UartScheduler::bind_cpu(em8051 *cpu) { cpu_ = cpu; }

void UartScheduler::reset_for_run() {
    cpu_ = nullptr;
    sbuf_tx_ = 0;
    sbuf_rx_ = 0;
    previous_scon_ = 0x50;
    scon_write_count_ = 0;
    next_sequence_ = 0;
    rx_busy_until_tick_ = 0;
    last_scon_poll_tick_ = -1;
    events_ = {};
}

void UartScheduler::reset_buffers() {
    sbuf_tx_ = 0;
    sbuf_rx_ = 0;
}

double UartScheduler::ticks_to_ms(long long ticks) {
    return static_cast<double>(ticks) / (fiat_clock_hz / 12.0) * 1000.0;
}

long long UartScheduler::bit_ticks() {
    return static_cast<long long>(
        std::llround((fiat_clock_hz / 12.0) / uart_baud));
}

void UartScheduler::schedule_tx_done() {
    const long long bit_ticks = UartScheduler::bit_ticks();
    if (bit_ticks <= 0)
        return;

    Event event{};
    event.when_tick = ticks_ + 9 * bit_ticks;
    event.sequence = next_sequence_++;
    event.kind = EventKind::TxDone;
    event.data = 0;
    events_.push(event);
}

void UartScheduler::schedule_rx_byte(uint8_t byte) {
    const long long bit_ticks = UartScheduler::bit_ticks();
    if (bit_ticks <= 0)
        return;

    const long long base_tick = std::max(ticks_, rx_busy_until_tick_);
    Event event{};
    event.when_tick = base_tick + static_cast<long long>(std::llround(
                                   9.5 * static_cast<double>(bit_ticks)));
    event.sequence = next_sequence_++;
    event.kind = EventKind::RxByte;
    event.data = byte;
    events_.push(event);
    rx_busy_until_tick_ = base_tick + 10 * bit_ticks;
}

void UartScheduler::on_scanner_byte(uint8_t byte) {
    if (!cpu_) {
        return;
    }

    const uint8_t scon = cpu_->mSFR[scon_address - 0x80];
    if ((scon & scon_ri) != 0) {
        fprintf(stderr,
                "[UART RX] OVERRUN! RI already=1, discarding new byte 0x%02X\n",
                byte);
        fflush(stderr);
        return;
    }

    schedule_rx_byte(byte);
    fprintf(stderr, "[UART] instr=%lld byte=0x%02X → scheduled RX event\n",
            ticks_, byte);
    fflush(stderr);
}

void UartScheduler::on_sbuf_write(em8051 *cpu) {
    sbuf_tx_ = cpu->mSFR[sbuf_address - 0x80];
    cpu->mSFR[sbuf_address - 0x80] = sbuf_tx_;
    bridge_.tx(sbuf_tx_);
    schedule_tx_done();
}

uint8_t UartScheduler::on_sbuf_read(em8051 *cpu, uint8_t address) const {
    if (address != sbuf_address)
        return cpu->mSFR[address - 0x80];
    return sbuf_rx_;
}

uint8_t UartScheduler::on_scon_read(em8051 *cpu, uint8_t address) {
    if (address != scon_address)
        return cpu->mSFR[address - 0x80];

    const uint8_t scon = cpu->mSFR[scon_address - 0x80];
    if ((scon & scon_ren) != 0 && (scon & scon_ri) == 0) {
        if (ticks_ != last_scon_poll_tick_) {
            last_scon_poll_tick_ = ticks_;
            bridge_.read_and_process();
        }
    }
    return scon;
}

void UartScheduler::on_scon_write(em8051 *cpu, uint8_t address) {
    if (address != scon_address)
        return;

    const uint8_t scon = cpu->mSFR[scon_address - 0x80];
    const uint8_t previous_ri = previous_scon_ & scon_ri;
    const uint8_t current_ri = scon & scon_ri;
    const uint8_t current_ren = scon & scon_ren;
    if (scon_write_count_ < 50) {
        fprintf(stderr,
                "[S0CON-WRITE] #%d PC=0x%04X S0CON: 0x%02X→0x%02X (RI: %d→%d, "
                "REN=%d)\n",
                ++scon_write_count_, cpu->mPC, previous_scon_, scon,
                previous_ri ? 1 : 0, current_ri ? 1 : 0, current_ren ? 1 : 0);
        fflush(stderr);
    }
    previous_scon_ = scon;
}

void UartScheduler::tick(em8051 *cpu, long long current_tick) {
    while (!events_.empty() && events_.top().when_tick <= current_tick) {
        const Event event = events_.top();
        events_.pop();

        uint8_t scon = cpu->mSFR[scon_address - 0x80];
        switch (event.kind) {
        case EventKind::TxDone:
            scon |= scon_ti;
            cpu->mSFR[scon_address - 0x80] = scon;
            break;

        case EventKind::RxByte:
            if ((scon & scon_ri) != 0) {
                fprintf(stderr,
                        "[UART TIMING] RX overrun: RI já=1, descartando 0x%02X "
                        "@instr=%lld [%.2f ms]\n",
                        event.data, current_tick, ticks_to_ms(current_tick));
                fflush(stderr);
                break;
            }

            scon |= scon_ri;
            cpu->mSFR[scon_address - 0x80] = scon;
            sbuf_rx_ = event.data;
            break;

        default:
            __builtin_unreachable();
        }
    }
}

} // namespace ma17
