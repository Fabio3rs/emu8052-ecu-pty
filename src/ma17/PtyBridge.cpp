#include "ma17/PtyBridge.hpp"

#include <cstdio>
#include <ctime>
#include <fcntl.h>
#include <iostream>
#include <pty.h>
#include <termios.h>
#include <unistd.h>

namespace ma17 {

PtyBridge::~PtyBridge() {
    if (mfd >= 0)
        close(mfd);
    if (sfd >= 0)
        close(sfd);
}

long long PtyBridge::now_ms() {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec * 1000LL + now.tv_nsec / 1000000LL;
}

bool PtyBridge::ignore_parmark() {
    if (last_tx_time == std::chrono::steady_clock::time_point{})
        return false;
    return last_tx_time + std::chrono::milliseconds(1000) >
           std::chrono::steady_clock::now();
}

bool PtyBridge::is_receiving_packets() {
    if (last_tx_time == std::chrono::steady_clock::time_point{})
        return false;
    return last_tx_time + std::chrono::milliseconds(800) >
           std::chrono::steady_clock::now();
}

bool PtyBridge::open_pty_4800_8N1() {
    char namebuf[128] = {0};
    struct termios tio {};

    fprintf(stderr, "[DEBUG] Tentando abrir PTY...\n");
    fflush(stderr);
    if (openpty(&mfd, &sfd, namebuf, nullptr, nullptr) < 0) {
        perror("openpty");
        return false;
    }

    fprintf(stderr, "[DEBUG] PTY aberto: %s (mfd=%d, sfd=%d)\n", namebuf, mfd,
            sfd);
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
    cfsetispeed(&tio, B9600);
    cfsetospeed(&tio, B9600);
#endif
    tio.c_cflag &= static_cast<tcflag_t>(~static_cast<tcflag_t>(PARENB));
    tio.c_cflag &= static_cast<tcflag_t>(~static_cast<tcflag_t>(CSTOPB));
    tio.c_cflag &= static_cast<tcflag_t>(~static_cast<tcflag_t>(CSIZE));
    tio.c_cflag |= CS8;
    tio.c_cflag |= CLOCAL | CREAD;

    // PARMRK exposes K-line BREAK as FF 00 00.
    tio.c_iflag &=
        static_cast<tcflag_t>(~static_cast<tcflag_t>(IGNBRK | BRKINT));
    tio.c_iflag |= PARMRK;
    tio.c_cc[VMIN] = 1;
    tio.c_cc[VTIME] = 0;
    if (tcsetattr(sfd, TCSANOW, &tio) < 0) {
        perror("tcsetattr");
        return false;
    }

    tcflush(sfd, TCIOFLUSH);
    tcflush(mfd, TCIOFLUSH);
    int flags = fcntl(mfd, F_GETFL, 0);
    fcntl(mfd, F_SETFL, flags | O_NONBLOCK);

    slave_path = namebuf;
    fprintf(stderr, "[DEBUG] Configuração PTY concluída com sucesso\n");
    fflush(stderr);
    return true;
}

void PtyBridge::tx(unsigned char byte) {
    last_tx_time = std::chrono::steady_clock::now();
    if (mfd >= 0) {
        ssize_t written = write(mfd, &byte, 1);
        fprintf(stderr, "[PTY-TX] Byte 0x%02X written to PTY (result=%zd)\n",
                byte, written);
        fflush(stderr);
    }
}

int PtyBridge::rx_try() {
    if (rx_queue.empty())
        return -1;
    unsigned char byte = rx_queue.front();
    rx_queue.pop();
    fprintf(stderr, "[RX-QUEUE] Dequeued 0x%02X (queue size was %zu)\n", byte,
            rx_queue.size() + 1);
    fflush(stderr);
    return static_cast<int>(byte);
}

void PtyBridge::read_and_process() {
    unsigned char byte = 0;
    if (read(mfd, &byte, 1) != 1)
        return;

    if (ignore_parmark()) {
        break_detect_idx = 0;
        break_detect_buffer[0] = 0;
        break_detect_buffer[1] = 0;
        break_detect_buffer[2] = 0;
        last_tx_time = std::chrono::steady_clock::now();
        (void)!write(mfd, &byte, 1);
        on_byte(byte);
        return;
    }

    if (break_detect_idx == 0) {
        if (byte == 0xFF && !ignore_parmark()) {
            break_detect_buffer[0] = byte;
            break_detect_idx = 1;
            std::cout << "[BREAK-DETECT] Possible BREAK detected" << std::endl;
            return;
        }

        last_tx_time = std::chrono::steady_clock::now();
        (void)!write(mfd, &byte, 1);
        on_byte(byte);
        rxd_line_state = true;
        return;
    }

    if (break_detect_idx == 1) {
        break_detect_buffer[1] = byte;
        if (byte == 0x00) {
            break_detect_idx = 2;
            return;
        }
        if (byte == 0xFF) {
            unsigned char ff = 0xFF;
            (void)!write(mfd, &ff, 1);
            on_byte(ff);
            rxd_line_state = true;
            break_detect_idx = 0;
            return;
        }

        (void)!write(mfd, break_detect_buffer, 2);
        on_byte(break_detect_buffer[0]);
        on_byte(byte);
        rxd_line_state = true;
        break_detect_idx = 0;
        return;
    }

    if (break_detect_idx == 2) {
        break_detect_buffer[2] = byte;
        if (byte == 0x00 || byte == 0xFF) {
            rxd_line_state = byte == 0xFF;
            long long now = now_ms();
            low_until_ms = rxd_line_state ? 0 : now + 250;
            fprintf(stderr,
                    "[K-LINE] BREAK detected (RXD=%s, hold until +%lld ms)\n",
                    (rxd_line_state ? "HIGH" : "LOW"),
                    rxd_line_state ? 0LL : low_until_ms - now);
            fflush(stderr);
        } else {
            (void)!write(mfd, &byte, 1);
            on_byte(byte);
            rxd_line_state = true;
        }
        break_detect_idx = 0;
    }
}

} // namespace ma17
