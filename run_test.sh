#!/bin/bash
# Script para testar o emulador 8051 com handshake K-line
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p build/ma17-analysis/pty
LOG=build/ma17-analysis/pty/run-test.log

echo "==================================="
echo "Teste do Emulador 8051 + PTY + K-line"
echo "==================================="
echo

# Inicia o emulador em background
echo "[1/3] Iniciando emulador..."
./build/emu8051-tty FiatTipo_MA17_dump_27c256.bin --8052 > "$LOG" 2>&1 &
EMU_PID=$!
trap 'kill -INT "$EMU_PID" 2>/dev/null || true; wait "$EMU_PID" 2>/dev/null || true' EXIT

# Aguarda o PTY ser criado e captura o caminho
sleep 2

PTY_PATH=$(grep -oP "PTY pronto em: \K/dev/pts/\d+" "$LOG" | head -1 || true)

if [ -z "$PTY_PATH" ]; then
    echo "[ERRO] Não foi possível detectar o PTY"
    cat "$LOG"
    exit 1
fi

echo "[2/3] PTY detectado: $PTY_PATH"
echo

# Executa o teste Python
echo "[3/3] Executando handshake K-line..."
echo
.venv/bin/python test_pty.py "$PTY_PATH" --handshake-only

echo "Teste concluído!"
