#pragma once

#include "lab/DynoCurve.hpp"
#include "lab/MiniJson.hpp"

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <optional>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

namespace lab {

// Y1: RUN WOT. The lab runs the ROM crank dyno one point at a time in a child
// process (the same binary and arguments as tools/dyno_point.py) and plots each
// point when it reaches ACCEPTED; anything else is shown as INVALID with the
// binary's own reason. This is a steady-state sweep: a transient pull is a
// different measurement and is not claimed here.

inline std::vector<double> sweep_rpms(double rpm_min, double rpm_max, double step) {
    std::vector<double> rpms;
    if (step <= 0.0 || rpm_max < rpm_min)
        return rpms;
    for (double rpm = rpm_min; rpm <= rpm_max + 1e-9 && rpms.size() < 64; rpm += step)
        rpms.push_back(rpm);
    return rpms;
}

// "min:max:step" (e.g. "1500:6000:500"); empty on malformed input.
inline std::vector<double> parse_sweep_spec(const std::string &spec) {
    double a = 0, b = 0, c = 0;
    char extra = 0;
    if (std::sscanf(spec.c_str(), "%lf:%lf:%lf%c", &a, &b, &c, &extra) != 3)
        return {};
    return sweep_rpms(a, b, c);
}

struct DynoSweepRow {
    double target_rpm = 0.0;
    std::string state;
    std::string reason;
    DynoPoint point;
};

inline std::optional<DynoSweepRow> parse_dyno_point_line(const std::string &line) {
    if (line.rfind("{\"type\":\"dyno_point\"", 0) != 0)
        return std::nullopt;
    const auto json = parse_json(line);
    if (!json || !json->is_object())
        return std::nullopt;
    const auto text = [&](const char *key) {
        const Json *v = json->get(key);
        return v && v->is_string() ? v->string : std::string();
    };
    const auto number = [&](const char *key) {
        const Json *v = json->get(key);
        return v && v->type == Json::Type::Number ? v->number : std::nan("");
    };
    DynoSweepRow row;
    row.target_rpm = number("target_rpm");
    row.state = text("state");
    row.reason = text("reason");
    row.point.rpm = number("mean_rpm");
    row.point.torque_nm = number("shaft_torque_nm");
    row.point.power_kw = number("shaft_power_kw");
    row.point.advance_deg = number("adv_mean_deg");
    row.point.mbt_deg = number("mbt_mean_deg");
    row.point.lambda = number("lambda");
    if (row.state.empty() || !std::isfinite(row.target_rpm))
        return std::nullopt;
    return row;
}

struct DynoSweepState {
    std::vector<double> plan;
    std::size_t next = 0;      // index of the point to run next
    bool running = false;
    DynoCurve curve;           // ACCEPTED points only, in arrival order
    std::vector<std::string> notes; // one line per finished point

    void start(std::vector<double> rpms, DynoProvenance provenance) {
        plan = std::move(rpms);
        next = 0;
        running = !plan.empty();
        curve = DynoCurve{};
        curve.label = "RUN WOT";
        curve.provenance = std::move(provenance);
        notes.clear();
    }
    bool has_next() const { return running && next < plan.size(); }
    double current_target() const { return plan.at(next); }

    // Record the finished point and advance. Only ACCEPTED rows reach the curve.
    void on_row(const DynoSweepRow &row) {
        char note[96];
        // An ACCEPTED row without a finite rpm and torque is not a curve point.
        if (row.state == "ACCEPTED" &&
            (!std::isfinite(row.point.rpm) || !std::isfinite(row.point.torque_nm))) {
            std::snprintf(note, sizeof(note), "%.0f INVALID: bad result",
                          row.target_rpm);
            notes.push_back(note);
            advance();
            return;
        }
        if (row.state == "ACCEPTED") {
            curve.points.push_back(row.point);
            std::sort(curve.points.begin(), curve.points.end(),
                      [](const DynoPoint &a, const DynoPoint &b) { return a.rpm < b.rpm; });
            std::snprintf(note, sizeof(note), "%.0f ACC %.1f N.M", row.target_rpm,
                          row.point.torque_nm);
        } else {
            std::snprintf(note, sizeof(note), "%.0f INVALID: %s", row.target_rpm,
                          row.reason.c_str());
        }
        notes.push_back(note);
        advance();
    }
    // The child ended without a result row.
    void on_failure() {
        char note[64];
        std::snprintf(note, sizeof(note), "%.0f INVALID: no result",
                      next < plan.size() ? plan[next] : 0.0);
        notes.push_back(note);
        advance();
    }
    void cancel() {
        running = false;
        notes.push_back("CANCELLED");
    }
    void advance() {
        ++next;
        if (next >= plan.size())
            running = false;
    }
    // Lines for the view: the running point first, then the finished ones.
    std::vector<std::string> lines() const {
        std::vector<std::string> out;
        if (running && next < plan.size()) {
            char text[48];
            std::snprintf(text, sizeof(text), "%.0f STAB", plan[next]);
            out.push_back(text);
        }
        out.insert(out.end(), notes.rbegin(), notes.rend());
        return out;
    }
};

// A child process whose stdout is read without blocking.
class ChildProcess {
  public:
    ~ChildProcess() { terminate(); }

    bool start(const std::vector<std::string> &argv) {
        terminate();
        int fds[2];
        if (::pipe(fds) != 0)
            return false;
        pid_ = ::fork();
        if (pid_ < 0) {
            ::close(fds[0]);
            ::close(fds[1]);
            return false;
        }
        if (pid_ == 0) {
            ::dup2(fds[1], STDOUT_FILENO);
            const int null_fd = ::open("/dev/null", O_WRONLY);
            if (null_fd >= 0)
                ::dup2(null_fd, STDERR_FILENO);
            ::close(fds[0]);
            ::close(fds[1]);
            std::vector<char *> args;
            for (const auto &a : argv)
                args.push_back(const_cast<char *>(a.c_str()));
            args.push_back(nullptr);
            ::execv(args[0], args.data());
            ::_exit(127);
        }
        ::close(fds[1]);
        fd_ = fds[0];
        ::fcntl(fd_, F_SETFL, ::fcntl(fd_, F_GETFL) | O_NONBLOCK);
        buffer_.clear();
        return true;
    }

    // Appends what the child has printed; returns the complete lines.
    std::vector<std::string> poll_lines() {
        std::vector<std::string> lines;
        if (fd_ < 0)
            return lines;
        char chunk[4096];
        for (;;) {
            const ssize_t n = ::read(fd_, chunk, sizeof(chunk));
            if (n > 0) {
                buffer_.append(chunk, static_cast<std::size_t>(n));
                continue;
            }
            break; // EAGAIN, EOF or error
        }
        for (std::size_t pos; (pos = buffer_.find('\n')) != std::string::npos;) {
            lines.push_back(buffer_.substr(0, pos));
            buffer_.erase(0, pos + 1);
        }
        return lines;
    }

    // True once the child has exited (and its pipe is drained by the caller).
    bool exited() {
        if (pid_ <= 0)
            return true;
        int status = 0;
        const pid_t done = ::waitpid(pid_, &status, WNOHANG);
        if (done == pid_ || (done < 0 && errno == ECHILD)) {
            pid_ = -1;
            return true;
        }
        return false;
    }

    void terminate() {
        if (pid_ > 0) {
            ::kill(pid_, SIGTERM);
            int status = 0;
            ::waitpid(pid_, &status, 0);
            pid_ = -1;
        }
        if (fd_ >= 0) {
            ::close(fd_);
            fd_ = -1;
        }
    }
    bool active() const { return pid_ > 0; }

  private:
    pid_t pid_ = -1;
    int fd_ = -1;
    std::string buffer_;
};

} // namespace lab
