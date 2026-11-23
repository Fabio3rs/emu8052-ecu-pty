// UI-26: the retained snapshot history must cover long (thermal) windows
// without gaps larger than the 250 ms the scopes treat as a break.
#include "lab/SimSession.hpp"

#include <chrono>
#include <cstdlib>
#include <cstdio>
#include <thread>

namespace {

#define CHECK(condition)                                                      \
    do {                                                                      \
        if (!(condition)) {                                                   \
            std::fprintf(stderr, "CHECK failed: %s (line %d)\n", #condition,  \
                         __LINE__);                                           \
            return 1;                                                         \
        }                                                                     \
    } while (false)

} // namespace

int main(int argc, char **argv) {
    if (argc < 2 || argc > 3)
        return 2;
    // Simulated seconds (default 30); 300 s is the longest scope window.
    const long long seconds = argc == 3 ? std::atoll(argv[2]) : 30;
    if (seconds < 1)
        return 2;
    const long long kStop = seconds * 990000;
    lab::SimSession session({"lab_session_retention", argv[1], "--physical-crank",
                             "--stop-ticks", std::to_string(kStop),
                             "--starter-ticks", "495000"});
    session.set_speed(16.0);
    session.start();
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(60 + 2 * seconds);
    while (!session.finished() && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    CHECK(session.finished());
    CHECK(!session.faulted());

    const auto window = session.snapshot_window(0);
    CHECK(window.size() > 100);
    long long largest_gap = 0;
    for (std::size_t i = 1; i < window.size(); ++i) {
        CHECK(window[i].tick > window[i - 1].tick); // strictly increasing
        largest_gap = std::max(largest_gap, window[i].tick - window[i - 1].tick);
    }
    const auto retention = session.snapshot_retention();
    std::printf("[LAB-RETENTION] samples=%zu first=%lld last=%lld largest_gap=%lld "
                "raw_evicted=%zu archive_evicted=%zu\n",
                window.size(), window.front().tick, window.back().tick,
                largest_gap, retention.raw_evicted, retention.archive_evicted);
    // Nothing the thermal groups need may have been evicted in 30 s, the
    // series starts at the beginning, and no gap exceeds the break threshold.
    CHECK(retention.archive_evicted == 0);
    CHECK(window.front().tick <= 2 * 990000);
    CHECK(window.back().tick >= kStop - 2 * 990000);
    // The retained series (raw + archive) covers the whole run, not just a tail.
    CHECK(window.back().tick - window.front().tick >= kStop - 4 * 990000);
    CHECK(largest_gap <= 247500);
    // A later first_tick returns exactly the tail of the same series.
    const auto tail = session.snapshot_window(window[window.size() / 2].tick);
    CHECK(!tail.empty() && tail.front().tick >= window[window.size() / 2].tick);
    CHECK(tail.back().tick == window.back().tick);
    lab::SimSession::SnapshotWindowCache cache;
    for (const long long start : {0LL, kStop / 2, kStop - 99000, kStop + 1, 0LL}) {
        const auto cached = session.snapshot_window(start, cache);
        const auto expected = session.snapshot_window(start);
        CHECK(cached.size() == expected.size());
        for (std::size_t i = 0; i < expected.size(); ++i)
            CHECK(cached[i].tick == expected[i].tick && cached[i].rpm == expected[i].rpm);
    }
    return 0;
}
