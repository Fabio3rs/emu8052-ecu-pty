#pragma once

namespace ecu_hw {

// Candidate P1.1 -> connector 24: two rising edges per crank revolution.
// Observes the emulated latch; external board electronics are not modeled.
class Ma17Tachometer {
  public:
    void observe(bool high, long long tick) {
        if (initialized_ && high && !high_) {
            if (last_rise_ >= 0 && tick > last_rise_ &&
                tick - last_rise_ < timeout_ticks)
                period_ = tick - last_rise_;
            else
                period_ = 0;
            last_rise_ = tick;
            ++pulses_;
        }
        initialized_ = true;
        high_ = high;
    }

    double rpm(long long tick) const {
        if (period_ <= 0 || tick < last_rise_ ||
            tick - last_rise_ >= timeout_ticks)
            return 0.0;
        return 30.0 * 990000.0 / static_cast<double>(period_);
    }
    unsigned long long pulses() const { return pulses_; }
    bool available() const { return initialized_; }

  private:
    static constexpr long long timeout_ticks = 495000; // 500 ms, Fiat clock.
    bool initialized_ = false;
    bool high_ = false;
    long long last_rise_ = -1;
    long long period_ = 0;
    unsigned long long pulses_ = 0;
};

} // namespace ecu_hw
