#!/bin/bash
# Complete test script for K-line handshake with emu8051

set -euo pipefail

cd "$(dirname "$0")"
mkdir -p build/ma17-analysis/pty
LOG=build/ma17-analysis/pty/run-full-test.log

echo "===================================="
echo "EMU8051 K-LINE HANDSHAKE TEST"
echo "===================================="
echo

# Start emulator in background
echo "[1/4] Starting emulator..."
./build/emu8051-tty FiatTipo_MA17_dump_27c256.bin --8052 > "$LOG" 2>&1 &
EMU_PID=$!
trap 'kill -INT "$EMU_PID" 2>/dev/null || true; wait "$EMU_PID" 2>/dev/null || true' EXIT

# Wait for PTY to be created
echo "[2/4] Waiting for PTY creation..."
sleep 2

# Extract PTY path from log
PTY_PATH=$(grep -oP "PTY pronto em: \K/dev/pts/\d+" "$LOG" | head -1 || true)

if [ -z "$PTY_PATH" ]; then
    echo "[ERROR] Could not detect PTY"
    echo "Emulator output:"
    cat "$LOG"
    exit 1
fi

echo "[3/4] PTY detected: $PTY_PATH"
echo

# Run Python K-line handshake test
echo "[4/4] Running K-line handshake test..."
echo
DIAGNOSTIC_ARGS=(--diagnostics-once)
if [ -n "${MA17_EXPECT_FAULT_TRIPLET:-}" ]; then
    DIAGNOSTIC_ARGS+=("--expect-fault-triplet=$MA17_EXPECT_FAULT_TRIPLET")
fi
if .venv/bin/python test_pty.py "$PTY_PATH" "${DIAGNOSTIC_ARGS[@]}"; then
    TEST_STATUS=0
else
    TEST_STATUS=$?
fi

echo
if [ $TEST_STATUS -eq 0 ]; then
    echo "===================================="
    echo "TEST PASSED!"
    echo "===================================="
else
    echo "===================================="
    echo "TEST FAILED!"
    echo "===================================="
fi

exit $TEST_STATUS
