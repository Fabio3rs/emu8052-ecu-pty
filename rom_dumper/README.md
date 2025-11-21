# EPROM TMS27C256 Dumper (Arduino Mega 2560)

**Status:** Personal research code. No production guarantees. Use at your own risk.

## ⚠️ Disclaimer

This is backup code from a personal electronics project. The implementation is:
- **Not tested** with all EPROM variants
- **Without error correction** or verification
- **Timing-dependent** (no cycle-accurate guarantees)
- **For advanced users only** with electronics knowledge

**Hardware damage is possible.** Incorrect wiring can damage the Arduino, EPROM, or power supply. Always verify connections with a multimeter before powering on.

---

## Prerequisites

**Required Electronics Knowledge:**
- Digital logic basics (TTL, CMOS voltage levels)
- EPROM operation (chip enable, output enable, address/data buses)
- Serial communication (UART, baud rates)
- Breadboard wiring and wire gauge selection

**Required Skills:**
- Safe soldering and breadboard connections
- Multimeter usage for voltage/continuity verification
- Serial port debugging (minicom, PuTTY, or equivalent)
- Ability to troubleshoot timing issues if they occur

**Not recommended for beginners.** Understand the schematics before connecting anything.

---

## Hardware Requirements

| Component | Purpose |
|-----------|---------|
| Arduino Mega 2560 | Microcontroller for address/data control |
| TMS27C256 (DIP-28) | 32 KB EPROM chip to dump |
| 5V regulated power | VCC for EPROM and Arduino |
| 100 nF capacitor | Decoupling between VCC/GND |
| Breadboard | For safe, non-destructive connections |
| Jumper wires (22 AWG) | Pin connections (use appropriate gauge) |
| Multimeter | Verify connections before power-on |
| Serial cable/adapter | USB to Arduino Mega (usually included) |

**Voltage:** All connections are 5V TTL. Do NOT use 3.3V components—they are incompatible.

---

## 1. TMS27C256 Pinout (DIP-28, Top View)

**Source:** TI TMS27C256 Datasheet. Read/mode operation (VCC = VPP = 5V).

| Pin | Signal | Description |
|-----|--------|-------------|
| 1 | VPP | Programming voltage (5V for read mode only) |
| 2–3, 4–7, 8–10 | A12, A7, A6–A4, A3–A1, A0 | Address lines (15 total: A0–A14) |
| 11–13, 15–19 | DQ0–DQ2, DQ3–DQ7 | Data output lines (8 bits) |
| 14 | GND | Ground |
| 20 | E (CE) | Chip Enable (active low) |
| 21–27 | A10, G(OE), A11, A9, A8, A13, A14 | Address/control lines |
| 28 | VCC | +5V power |

**Read Mode:** VCC=5V, VPP=5V, E=LOW, G=LOW → data on DQ0–DQ7

---

## 2. Wiring Diagram (EPROM ↔ Arduino Mega)

### Power Connections

- EPROM **pin 28 (VCC)** → **5V** (Arduino or external PSU)
- EPROM **pin 1 (VPP)** → **5V** (same as VCC for read mode)
- EPROM **pin 14 (GND)** → **GND** (common ground)
- Add **100 nF ceramic capacitor** between VCC and GND near EPROM pins

### Control Signals

| Function | EPROM Pin | Arduino Mega Pin | Logic |
|----------|-----------|-----------------|-------|
| Output Enable (OE) | 22 (G) | 18 | LOW = enabled |
| Chip Enable (CE) | 20 (E) | GND | Tied LOW (always enabled) |

### Data Bus (DQ0–DQ7) 

Connected to **PORTF (A0–A7)** for atomic byte reads:

| Data Line | EPROM Pin | Arduino A-Pin | PORTF Bit |
|-----------|-----------|---------------|-----------|
| DQ0 | 11 | A0 | 0 |
| DQ1 | 12 | A1 | 1 |
| DQ2 | 13 | A2 | 2 |
| DQ3 | 15 | A3 | 3 |
| DQ4 | 16 | A4 | 4 |
| DQ5 | 17 | A5 | 5 |
| DQ6 | 18 | A6 | 6 |
| DQ7 | 19 | A7 | 7 |

### Address Bus (A0–A14)

Standard digital I/O pins in order:

| Address | EPROM Pin | Arduino Pin |
|---------|-----------|-------------|
| A0 | 10 | D2 |
| A1 | 9 | D3 |
| A2 | 8 | D4 |
| A3 | 7 | D5 |
| A4 | 6 | D6 |
| A5 | 5 | D7 |
| A6 | 4 | D8 |
| A7 | 3 | D9 |
| A8 | 25 | D10 |
| A9 | 24 | D11 |
| A10 | 21 | D12 |
| A11 | 23 | D13 |
| A12 | 2 | D21 |
| A13 | 26 | D20 |
| A14 | 27 | D19 |

---

## 3. Arduino Mega Firmware

The sketch reads the entire 32 KB address space (0x0000–0x7FFF) sequentially:

1. Set address lines (A0–A14) to the current address
2. Assert output enable (G = LOW)
3. Read all 8 data lines simultaneously via PORTF register (`PINF`)
4. Deassert output enable (G = HIGH)
5. Transmit byte as hexadecimal over serial (115200 baud, 8N1)
6. Increment address and repeat

**Important Timing Notes:**
- Address setup → OE assert → read → OE deassert sequence takes ~10 µs
- No explicit delays needed; PORTF reads are immediate
- Serial I/O (sprintf) is the bottleneck (~100+ bytes/sec)

**Code Location:** `DumperEPROM/DumperEPROM.ino`

Key implementation details:
- Data pins (DQ0–DQ7) connected to PORTF (A0–A7) for atomic 8-bit reads
- Address pins distributed across digital lines 2–13, 19–21
- OE pin (18) controls read enable
- CE (pin 20) tied to GND for continuous chip selection

---

## 4. Saving Dump Data to PC

### Option A: Arduino Serial Monitor

1. Open Arduino IDE → **Tools → Serial Monitor** (set speed to 115200 baud)
2. Press **RESET** on Mega after wiring is complete
3. Wait for dump to complete (~15 seconds for 32 KB)
4. Select all output, copy, and paste into a text file (e.g., `eprom_dump.hex`)

### Option B: Command-Line (Recommended)

Use `cli/dumper.py` to automate serial capture:

```bash
python3 cli/dumper.py /dev/ttyACM0 > eprom_dump.hex
```

or if using USB-to-serial adapter:

```bash
python3 cli/dumper.py /dev/ttyUSB0 > eprom_dump.hex
```

This captures raw hex output directly from the serial port and saves to file in one step.

**Note:** Port may vary depending on your system and USB adapter type. Check available ports with `ls /dev/ttyACM* /dev/ttyUSB*`

---

## 5. CLI Tools

### dumper.py – Serial Capture & Automation

**Purpose:** Automates hex dump collection from serial port.

**Usage:**
```bash
python3 cli/dumper.py /dev/ttyACM0
```

or

```bash
python3 cli/dumper.py /dev/ttyUSB0
```

**Serial Port Detection:**
- **Arduino Mega 2560 (native USB):** Typically `/dev/ttyUSB0` (or `/dev/ttyUSB1` if multiple devices)
- Arduino with external USB-to-serial adapter: `/dev/ttyACM0`
- Discover available ports: `ls /dev/ttyACM* /dev/ttyUSB*`

### dump.py – Binary Conversion

**Purpose:** Converts hex dump to raw binary format.

**Usage:**
```bash
python3 cli/dump.py eprom_dump.hex -o firmware.bin
```

**Features:**
- Parses hex text format (space-separated bytes)
- Validates checksum (optional)
- Outputs raw 32 KB binary suitable for disassembly or analysis

### dumper.cpp – C++ Alternative (Legacy)

Native C++ tool for direct serial I/O. Use if Python is not available on your system.

**Compilation:**
```bash
g++ -std=c++23 -o dumper cli/dumper.cpp
```

**Run:**
```bash
./dumper /dev/ttyACM0 dump.bin
```

or with USB-to-serial adapter:

```bash
./dumper /dev/ttyUSB0 dump.bin
```

---

## 6. Troubleshooting

### Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Serial port not found | Arduino not detected | Check USB cable, drivers; try `/dev/ttyUSB0` first, then `/dev/ttyACM*` |
| All bytes read as 0xFF | EPROM not powered or CE not LOW | Verify VCC on EPROM pin 28; tie CE (pin 20) to GND |
| Corrupted/random data | Address lines floating or misconnected | Use multimeter to verify continuity on all address pins |
| Dump never completes | OE (pin 22) not properly wired | Verify pin 18 on Mega connects to EPROM pin 22 |
| Serial hangs mid-dump | Baud rate mismatch or USB disconnection | Restart Arduino, check Serial Monitor speed (115200) |

### Verification

After successful dump, check file size:

```bash
ls -la eprom_dump.hex
wc -l eprom_dump.hex  # Should be ~2048 lines (32 KB / 16 bytes per line)
```

**Recommended: Verify data integrity by comparing multiple dumps**

To ensure reliable reads without corruption, perform the dump 2-3 times and verify all outputs are identical:

```bash
# Capture multiple dumps
python3 cli/dumper.py /dev/ttyUSB0 -o dump1.bin
python3 cli/dumper.py /dev/ttyUSB0 -o dump2.bin
python3 cli/dumper.py /dev/ttyUSB0 -o dump3.bin

# Compare checksums - all should match
sha256sum dump*.bin
```

If checksums differ, possible causes:
- Loose wiring or poor connections (check with multimeter)
- Insufficient capacitor decoupling (add 100 nF near EPROM)
- Address line timing issues (try adding small delays in firmware)
- EPROM may be damaged or failing

---

## 7. Known Limitations

- **Hardware-specific:** Only tested with TMS27C256. Other EPROM types (27C128, 27C512) are pin-compatible but untested.
- **No error detection:** Reads happen once; corrupted bytes are not detected or re-read.
- **No cycle-accuracy:** Timing is not guaranteed; relies on EPROM to stabilize data lines quickly.
- **PORTF read only:** Cannot easily adapt this design to read data from other ports.
- **Address range fixed:** 0x0000–0x7FFF (32 KB). Larger EPROMs require code modification.

---

## 8. Legal & Warranty

**No warranty.** This code is provided as-is for educational purposes only. The authors are not responsible for:
- Damage to hardware (Arduino, EPROM, power supply)
- Loss of data or incorrect firmware extraction
- Safety hazards from electrical shock or short circuits
- Infringement of copyright or intellectual property

**Use at your own risk.** Always verify connections with a multimeter before applying power.
