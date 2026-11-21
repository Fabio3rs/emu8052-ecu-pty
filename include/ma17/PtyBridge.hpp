#pragma once

#include "Lifetime.hpp"

#include <array>
#include <chrono>
#include <cstdint>
#include <string>

namespace ma17 {

struct PtyBridge {
    using ReceiveCallback = void (*)(uint8_t);
    explicit PtyBridge(ReceiveCallback receive_callback EMU_LIFETIMEBOUND)
        : on_byte(receive_callback) {}
    ~PtyBridge();
    PtyBridge(const PtyBridge &) = delete;
    PtyBridge &operator=(const PtyBridge &) = delete;

    ReceiveCallback on_byte = nullptr;
    int mfd = -1;
    int sfd = -1;
    std::string slave_path;

    // SIGUSR1 injector overrides the PTY's physical K-line state.
    bool override_rxd = false;
    bool override_state = true;
    bool rxd_line_state = true;
    long long emulated_tick = 0;
    long long low_until_tick = 0;
    std::array<unsigned char, 3> break_detect_buffer{};
    int break_detect_idx = 0;
    std::chrono::steady_clock::time_point last_tx_time{};
    std::array<unsigned char, 64> ingress_buffer_{};
    size_t ingress_head_ = 0;
    size_t ingress_count_ = 0;

    bool ignore_parmark();
    bool is_receiving_packets();
    bool open_pty_4800_8N1();
    void tx(unsigned char byte);
    void read_and_process();
    void process_byte(unsigned char byte);
};

} // namespace ma17
