#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de handshake K-line (Bosch MA1.7) num PTY do emu8051.

- Em PTY: bits '0' são enviados como triplete PARMRK (FF 00 00);
  bits '1' apenas aguardam 200 ms (MARK). Isso casa com o seu harness,
  que detecta PARMRK e ajusta rxd_line_state.
- Em serial real: usa break_condition do pySerial.

Também ignora o eco K-line após cada byte enviado.
"""

import os, sys, time, serial, fcntl

BIT_MS = 200  # 5 baud => 200 ms/bit


def is_pty_path(path: str) -> bool:
    try:
        return os.path.realpath(path).startswith("/dev/pts/")
    except Exception:
        return False


def sleep_ms(ms):
    time.sleep(ms / 1000.0)


def send_5baud_init(ser: serial.Serial, value: int, pty_mode: bool,
                    bit_ms: float = BIT_MS):
    print(f"\n[INIT] 5-baud init: 0x{value:02X} (PTY mode: {pty_mode}, "
          f"bit={bit_ms:.2f} ms)")

    # start + 8 data (LSB first) + stop
    bits = [0] + [(value >> i) & 1 for i in range(8)] + [1]
    print(f"[INIT] Bits: {bits}")

    if pty_mode:
        # Send every bit level explicitly; a MARK must release the prior BREAK.
        for b in bits:
            ser.write(b"\xff\x00\xff" if b else b"\xff\x00\x00")
            sleep_ms(bit_ms)
    else:
        # Porta serial real: use break_condition
        # (obs.: alguns drivers exigem pequeno gap entre bits)
        for b in bits:
            ser.break_condition = b == 0  # SPACE=LOW quando 0
            sleep_ms(bit_ms)
        ser.break_condition = False  # idle alto

    print("[INIT] 5-baud concluído")


packet_counter = 0x00


def read_byte_with_timeout(ser, timeout_ms=1000, desc="", ignore_echo=None):
    """Lê 1 byte com timeout; se ignore_echo!=None, descarta o primeiro byte igual ao eco."""
    deadline = time.time() + (timeout_ms / 1000.0)
    skipped_echo = False

    # DEBUG: Show buffer state and what we expect
    if ignore_echo is not None:
        print(
            f"[DEBUG] Esperando eco=0x{ignore_echo:02X}, buffer={ser.in_waiting} bytes"
        )

    while time.time() < deadline:
        if ser.in_waiting > 0:
            b = ser.read(1)[0]

            # DEBUG: Show what we read
            if ignore_echo is not None:
                print(
                    f"[DEBUG] Leu 0x{b:02X}, esperava eco=0x{ignore_echo:02X}, match={b==ignore_echo}"
                )

            # descartar 1 eco (half-duplex)
            if ignore_echo is not None and not skipped_echo and b == ignore_echo:
                print(f"[DEBUG] ✓ Eco descartado: 0x{b:02X}")
                skipped_echo = True
                continue
            print(f"[RX] {desc}0x{b:02X}; AS CHAR {chr(b) if 32 <= b <= 126 else '.'}")
            return b
        time.sleep(0.001)

    # DEBUG: Timeout
    if ignore_echo is not None:
        print(f"[DEBUG] ✗ TIMEOUT aguardando eco=0x{ignore_echo:02X}")
    return None


def ecu_write(ser, byte):
    """
    Envia byte e valida eco físico (half-duplex K-line).
    Implementa ECUWrite() do scanner C++ de referência.
    """
    ser.write(bytes([byte]))
    ser.flush()

    # Aguarda eco físico (deve chegar instantaneamente)
    deadline = time.time() + 0.1  # 100ms timeout
    while time.time() < deadline:
        if ser.in_waiting > 0:
            echo = ser.read(1)[0]
            if echo == byte:
                print(f"[TX-ECHO] 0x{byte:02X} → eco OK")
                return True  # ✓ Eco validado
            else:
                print(
                    f"[ERRO] Eco incorreto: enviou 0x{byte:02X}, recebeu 0x{echo:02X}"
                )
                return False
        time.sleep(0.001)

    print(f"[ERRO] Timeout aguardando eco de 0x{byte:02X}")
    return False


def send_ecu_packet(ser, frame_id, data=None, counter=0):
    """
    Envia pacote formatado para a ECU.

    Estrutura:
    - SIZE: 3 + len(data)
    - COUNTER: Contador incremental
    - FRAME_ID: Tipo do frame (0x09=ACK, 0x07=ler erros, etc.)
    - DATA: Bytes de dados opcionais
    - END: Sempre 0x03

    Cada byte (exceto END) recebe ACK (byte invertido).
    Retorna True em sucesso, False em erro.
    """
    if data is None:
        data = []

    # Calcula SIZE
    size = 3 + len(data)

    # Monta pacote completo
    packet_bytes = [size, counter, frame_id] + data

    # Envia cada byte exceto END, validando ACK
    for i, byte_val in enumerate(packet_bytes):  # Todos exceto END
        print(f"[TX] Byte[{i}]: 0x{byte_val:02X}")
        ser.write(bytes([byte_val]))

        # Aguarda ACK invertido
        ack = read_byte_with_timeout(
            ser, 200, f"ACK[{byte_val:02X}]: ", ignore_echo=byte_val
        )
        expected_ack = (~byte_val) & 0xFF

        if ack is None:
            print(f"[ERRO] Timeout aguardando ACK para byte 0x{byte_val:02X}")
            return False

        if ack != expected_ack:
            print(
                f"[ERRO] ACK incorreto: esperava 0x{expected_ack:02X}, recebeu 0x{ack:02X}"
            )
            return False

    # Envia END (sem aguardar ACK)
    ser.write(bytes([0x03]))
    read_byte_with_timeout(ser, 200, "END sent: 0x03")
    return True


def read_ecu_packet(ser, timeout_ms=1000):
    """
    Lê e decodifica um pacote completo da ECU.

    Retorna dict com:
    - 'size': Tamanho do pacote
    - 'counter': Contador do pacote
    - 'frame_id': ID do frame (0x09=ACK, 0xF6=Identificação, etc.)
    - 'data': Lista de bytes de dados
    - 'raw': Sequência raw de bytes

    Retorna None em caso de timeout ou erro.
    """
    packet = {}

    # Lê SIZE
    size_byte = read_byte_with_timeout(ser, timeout_ms, "SIZE: ")
    if size_byte is None:
        return None
    packet["size"] = size_byte
    ser.write(bytes([(~size_byte) & 0xFF]))  # ACK
    read_byte_with_timeout(ser, 200, f"ACK sent for SIZE: 0x{(~size_byte) & 0xFF}")

    # Lê COUNTER
    counter = read_byte_with_timeout(ser, timeout_ms, "COUNTER: ")
    if counter is None:
        return None
    packet["counter"] = counter
    ser.write(bytes([(~counter) & 0xFF]))  # ACK
    read_byte_with_timeout(ser, 200, f"ACK sent for COUNTER: 0x{(~counter) & 0xFF}")

    # Lê FRAME ID
    frame_id = read_byte_with_timeout(ser, timeout_ms, "FRAME_ID: ")
    if frame_id is None:
        return None
    packet["frame_id"] = frame_id
    ser.write(bytes([(~frame_id) & 0xFF]))  # ACK
    read_byte_with_timeout(ser, 200, f"ACK sent for FRAME_ID: 0x{(~frame_id) & 0xFF}")

    # Lê DATA (SIZE - 3 bytes)
    data_len = max(0, size_byte - 3)
    data = []
    for i in range(data_len):
        b = read_byte_with_timeout(ser, timeout_ms, f"DATA[{i}]: ")
        if b is None:
            return None
        data.append(b)
        ser.write(bytes([(~b) & 0xFF]))  # ACK cada byte de dados
        read_byte_with_timeout(ser, 200, f"ACK sent for DATA[{i}]: 0x{(~b) & 0xFF}")

    packet["data"] = data

    # Lê END (sem ACK!)
    end_byte = read_byte_with_timeout(ser, timeout_ms, "END: ")
    if end_byte is None:
        return None

    if end_byte != 0x03:
        print(f"[ERRO] Byte END inválido: 0x{end_byte:02X}, esperado 0x03")
        return None

    packet["raw"] = bytes([size_byte, counter, frame_id] + data + [end_byte])
    return packet


def process_incoming_packet(packet):
    """Processa e loga pacote recebido da ECU."""
    if packet is None:
        return

    fid = packet["frame_id"]
    data = packet["data"]
    counter = packet["counter"]

    if fid == 0xF6 and data:
        # Banner/Identificação da ECU
        try:
            ident = bytes(data).decode("ascii", "ignore")
            print(f"[ECU-IDENT] Banner: {ident}")
        except Exception:
            print(f"[ECU-IDENT] Raw: {' '.join(f'{b:02X}' for b in data)}")

    elif fid == 0x09:
        # ACK frame
        print(f"[ECU-ACK] Recebido (counter={counter:02X})")

    elif fid == 0xFC:
        # Dados de erro
        print(f"[ECU-ERROR] Pacote de erro: {' '.join(f'{b:02X}' for b in data)}")

    elif fid == 0xFE:
        # Memory read response; the physical meaning depends on the address.
        print(f"[ECU-MEMORY] Dados: {' '.join(f'{b:02X}' for b in data)}")

    elif fid == 0xF4:
        print(f"[ECU-COLLECTION] Dados: {' '.join(f'{b:02X}' for b in data)}")

    else:
        # Frame desconhecido
        print(
            f"[ECU-PACKET] Frame=0x{fid:02X}, Data={' '.join(f'{b:02X}' for b in data)}"
        )


"""

bool ECUMonomotronic::ECUWritePacket(uint8_t frameid,
                                     const std::vector<uint8_t> &data) {
    int packetSize = 3 + data.size();

    if (!ECUWriteResponse(packetSize)) {
        return false;
    }

    if (!ECUWriteResponse(++ECUPacketCounter)) {
        return false;
    }

    if (!ECUWriteResponse(frameid)) {
        return false;
    }

    if (data.size() > 0) {
        ECUWriteSequential(data);
    }

    if (!ECUWrite(0x03)) {
        return false;
    }

    return true;
}

"""


def ecu_write_packet(ser, frame_id, data=None, counter=0):
    return send_ecu_packet(ser, frame_id, data, counter)


def ecu_handshake(ser, pty_mode: bool, skip_5baud: bool = False,
                  bit_ms: float = BIT_MS):
    global packet_counter
    print("\n" + "=" * 60)
    print("INICIANDO HANDSHAKE K-LINE")
    print("=" * 60)

    # Limpa qualquer lixo prévio
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    sleep_ms(50)

    # 1) 5-baud init (0x10 para MA1.7)
    if not skip_5baud:
        send_5baud_init(ser, 0x10, pty_mode, bit_ms)

    # 2) The Fiat emulator sends five keys after sync; hardware may differ.
    print("\n[HANDSHAKE] Aguardando resposta da ECU...")
    sync = read_byte_with_timeout(ser, 3000 if skip_5baud else 2000,
                                  "Sync: ")
    if sync is None:
        print("[ERRO] Timeout aguardando 0x55")
        return False
    if sync != 0x55:
        print(f"[ERRO] Esperava 0x55, recebeu 0x{sync:02X}")
        return False

    key1 = read_byte_with_timeout(ser, 1000, "Key1: ")
    key2 = read_byte_with_timeout(ser, 1000, "Key2: ")
    key3 = read_byte_with_timeout(ser, 1000, "Key3: ")
    key4 = read_byte_with_timeout(ser, 1000, "Key4: ")
    key5 = read_byte_with_timeout(ser, 1000, "Key5: ") if pty_mode else None
    if None in (key1, key2, key3, key4) or (pty_mode and key5 is None):
        print("[ERRO] Timeout aguardando keys")
        return False

    keys = f"{key1:02X} {key2:02X} {key3:02X} {key4:02X}"
    if key5 is not None:
        keys += f" {key5:02X}"
    print(f"[HANDSHAKE] Keys: {keys}")

    # 3) Responde ~key2 (seguindo padrão do scanner C++ de referência)
    resp = (~key2) & 0xFF
    print(f"[TX] ~Key2: 0x{resp:02X}")

    # Limpa buffer e envia IMEDIATAMENTE (sem delay entre)
    sleep_ms(30)
    while ser.in_waiting > 0:
        print(f"[DEBUG] Descartando {ser.in_waiting} bytes ANTES de enviar ~key2")
        ser.reset_input_buffer()

    # Envia ~key2 IMEDIATAMENTE após limpar (minimiza janela para bytes da ECU)
    if not ecu_write(ser, resp):
        print("[ERRO] Falha ao enviar ~key2")
        return False

    # 4) Recebe pacotes de identificação (tamanhos pequenos)
    print("\n[HANDSHAKE] Aguardando pacotes de identificação...")
    packets = 0
    for _ in range(16):
        size_b = read_byte_with_timeout(ser, 1200, "Size: ")
        if size_b is None:
            break
        # ACK de cada byte (Protocol ACK - seguindo padrão C++)
        ack_byte = (~size_b) & 0xFF
        print(f"[TX] ACK SIZE: 0x{ack_byte:02X}")
        if not ecu_write(ser, ack_byte):
            print("[ERRO] Falha ao enviar ACK de SIZE")
            break

        cnt = read_byte_with_timeout(ser, 200, "Cnt: ")
        if cnt is None:
            break
        ack_cnt = (~cnt) & 0xFF
        print(f"[TX] ACK CNT: 0x{ack_cnt:02X}")
        if not ecu_write(ser, ack_cnt):
            print("[ERRO] Falha ao enviar ACK de CNT")
            break

        packet_counter = cnt  # Sincroniza contador de pacotes

        fid = read_byte_with_timeout(ser, 200, "FrameID: ")
        if fid is None:
            break
        ack_fid = (~fid) & 0xFF
        print(f"[TX] ACK FID: 0x{ack_fid:02X}")
        if not ecu_write(ser, ack_fid):
            print("[ERRO] Falha ao enviar ACK de FID")
            break

        data_len = max(0, size_b - 3)
        print(f"[HANDSHAKE] Esperando {data_len} bytes de dados...")
        data = []
        for i in range(data_len):
            b = read_byte_with_timeout(ser, 300, f"D[{i}]: ")
            if b is None:
                print(f"[ERRO] Timeout aguardando byte D[{i}]")
                break
            data.append(b)
            ack_data = (~b) & 0xFF
            print(f"[TX] ACK D[{i}]: 0x{ack_data:02X}")
            if not ecu_write(ser, ack_data):
                print(f"[ERRO] Falha ao enviar ACK de D[{i}]")
                break

        endb = read_byte_with_timeout(ser, 200, "End: ")
        if endb is None:
            print("[ERRO] Timeout aguardando byte END")
            break
        if endb != 0x03:
            print(f"[ERRO] Byte END inválido: 0x{endb:02X}, esperado 0x03")
            break

        packets += 1

        if fid == 0xF6 and data:
            try:
                ident = bytes(data).decode("ascii", "ignore")
            except Exception:
                ident = data
            print(f"[IDENT] {ident}")

        if fid == 0x09:
            print("\n[HANDSHAKE] ACK final recebido — handshake completo!")
            return True

        packet_counter = (packet_counter + 1) & 0xFF
        print(
            f"\n[HANDSHAKE] Enviando ACK para o pacote anterior (counter={packet_counter:02X})..."
        )
        if not send_ecu_packet(ser, frame_id=0x09, counter=packet_counter):
            print("[ERRO] Falha ao enviar keep-alive ACK")
            return False

    print(f"\n[HANDSHAKE] Recebidos {packets} pacotes")
    return packets > 0


"""

    // Source: http://www.nailed-barnacle.co.uk/coupe/startrek/startrek.html
    enum ECU_FRAMES_ID {
        ECU_DATA_MEMORY_READ = 0x01,
        ECU_REQ_ACTUATOR = 0x04,
        ECU_CLEAR_ERRORS_CODE = 0x05,
        ECU_REQ_DIAGNOSIS_END = 0x06,
        ECU_READ_ERRORS_CODE = 0x07,
        ECU_ACK_CODE = 0x09,
        ECU_NOT_ACK_CODE = 0x0A,
        ECU_INIT_STRING = 0xF6,
        ECU_REQUEST_ADC_CODE = 0xFB,
        ECU_ERROR_DATA_CODE = 0xFC,
        ECU_READ_DATA_CODE = 0xFE
    };


"""

sent_read_errors = False


def request_data(ser, frame_id, data=None):
    global packet_counter

    packet_counter = (packet_counter + 1) & 0xFF
    if not send_ecu_packet(ser, frame_id=frame_id, data=data, counter=packet_counter):
        print("[ERRO] Falha ao enviar pedido")
        return None

    responses = []
    while True:
        response = read_ecu_packet(ser, timeout_ms=500)
        if response is None:
            print("[ERRO] Pedido sem quadro final da ECU")
            return None
        responses.append(response)
        print("[REQUEST] Pacote recebido:")
        process_incoming_packet(response)

        packet_counter = response["counter"]
        if response["frame_id"] == 0x09:
            return responses

        packet_counter = (packet_counter + 1) & 0xFF
        print(f"\n[REQUEST] Enviando ACK (counter={packet_counter:02X})...")

        # Envia pacote ACK: SIZE=0x03, COUNTER, FRAME_ID=0x09, END=0x03
        if not send_ecu_packet(ser, frame_id=0x09, counter=packet_counter):
            print("[ERRO] Falha ao enviar ACK")
            return None


def read_memory_byte(ser, selector, address):
    return request_data(ser, frame_id=0x01, data=[0x01, selector, address])


def read_iram_byte(ser, address):
    return read_memory_byte(ser, 0x00, address)

def keep_alive_loop(ser, pty_mode, timeout_ms=1000, keep_alive_interval_ms=300):
    global packet_counter, sent_read_errors
    """
    Mantém conexão com a ECU através de pacotes ACK periódicos.

    - Envia ACK a cada 500ms para prevenir timeout
    - Recebe e processa pacotes recebidos
    - Detecta e trata respostas da ECU
    - Sai em caso de erro ou timeout

    Retorna False em caso de erro, não retorna em operação normal (loop infinito).
    """
    last_packet_time = time.time()

    print("\n" + "=" * 60)
    print("ENTRANDO NO LOOP DE KEEP-ALIVE")
    print("=" * 60)
    print(f"[KEEP-ALIVE] Enviando ACK a cada {keep_alive_interval_ms}ms")
    print(f"[KEEP-ALIVE] Timeout de desconexão: {timeout_ms}ms")
    print("\nPressione Ctrl+C para sair\n")

    try:
        while True:
            now = time.time()
            elapsed_ms = (now - last_packet_time) * 1000

            if not sent_read_errors:
                sent_read_errors = True
                last_packet_time = now
                request_data(ser, frame_id=0x07)

                read_iram_byte(ser, address=0x63)
                last_packet_time = time.time()
                read_iram_byte(ser, address=0x62)

            # Envia keep-alive ACK se passou o intervalo
            if elapsed_ms > keep_alive_interval_ms:
                packet_counter = (packet_counter + 1) & 0xFF
                print(f"\n[KEEP-ALIVE] Enviando ACK (counter={packet_counter:02X})...")

                # Envia pacote ACK: SIZE=0x03, COUNTER, FRAME_ID=0x09, END=0x03
                if not send_ecu_packet(ser, frame_id=0x09, counter=packet_counter):
                    print("[ERRO] Falha ao enviar keep-alive ACK")
                    return False

                last_packet_time = now

                # Aguarda resposta ACK da ECU
                print(f"[KEEP-ALIVE] Aguardando resposta ACK da ECU...")
                ack_response = read_ecu_packet(ser, timeout_ms=1000)

                if ack_response is None:
                    print("[ERRO] Sem resposta ACK da ECU (timeout)")
                    return False

                packet_counter = ack_response["counter"]
                if ack_response["frame_id"] != 0x09:
                    print(
                        f"[AVISO] Esperava ACK (0x09), recebeu Frame ID 0x{ack_response['frame_id']:02X}"
                    )
                    process_incoming_packet(ack_response)
                else:
                    print(
                        f"[KEEP-ALIVE] ✓ ACK confirmado pela ECU (counter={ack_response['counter']:02X})"
                    )

                last_packet_time = time.time()

            # Verifica se há dados chegando enquanto aguarda
            if ser.in_waiting > 0:
                print(f"\n[KEEP-ALIVE] Dados disponíveis ({ser.in_waiting} bytes)...")

                # Tenta ler um pacote completo
                packet = read_ecu_packet(ser, timeout_ms=500)

                if packet:
                    last_packet_time = time.time()
                    print(
                        f"[KEEP-ALIVE] Pacote recebido: Frame=0x{packet['frame_id']:02X}"
                    )
                    process_incoming_packet(packet)

                    # Se não for ACK, responde com ACK
                    if packet["frame_id"] != 0x09:
                        packet_counter = (packet_counter + 1) & 0xFF
                        print(
                            f"[KEEP-ALIVE] Respondendo com ACK (counter={packet_counter:02X})..."
                        )
                        if not send_ecu_packet(
                            ser, frame_id=0x09, counter=packet_counter
                        ):
                            print("[ERRO] Falha ao responder com ACK")
                            return False
                else:
                    print("[AVISO] Falha ao ler pacote completo")

            # Detecta timeout de desconexão
            if elapsed_ms > timeout_ms:
                print(
                    f"\n[ERRO] Timeout de conexão! Sem atividade por {elapsed_ms:.0f}ms"
                )
                return False

            # Sleep curto para evitar uso excessivo de CPU
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n[KEEP-ALIVE] Interrompido pelo usuário")
        return True


def main():
    modes = {"--handshake-only", "--diagnostics-once", "--faults-once",
             "--frame38-probe"}
    options = sys.argv[2:]
    skip_5baud = "--skip-5baud" in options
    clock_options = [arg for arg in options if arg.startswith("--cpu-ticks-per-second=")]
    fault_options = [arg for arg in options if arg.startswith("--expect-fault-triplet=")]
    mode_options = [arg for arg in options if arg in modes]
    if (len(sys.argv) < 2 or len(fault_options) > 1 or len(mode_options) > 1 or
            len(clock_options) > 1 or
            len(options) != len(fault_options) + len(mode_options) + skip_5baud +
            len(clock_options) or
            (fault_options and mode_options not in
             (["--diagnostics-once"], ["--faults-once"]))):
        print("Uso: python3 test_pty.py /dev/pts/X|/dev/ttyUSB0 "
              "[--handshake-only|--diagnostics-once|--faults-once|--frame38-probe "
              "[--expect-fault-triplet=02061B] [--skip-5baud] "
              "[--cpu-ticks-per-second=N]]")
        return False
    bit_ms = BIT_MS
    if clock_options:
        try:
            tick_rate = float(clock_options[0].split("=", 1)[1])
        except ValueError:
            return False
        if not 100000 <= tick_rate <= 2000000:
            return False
        bit_ms = 198000000.0 / tick_rate
        print(f"[INIT] CPU observado: {tick_rate:.0f} ticks/s; "
              f"5-baud PTY: {bit_ms:.2f} ms/bit")
    expected_triplet = None
    if fault_options:
        try:
            expected_triplet = bytes.fromhex(fault_options[0].split("=", 1)[1])
        except ValueError:
            return False
        if len(expected_triplet) != 3:
            return False

    dev = sys.argv[1]
    handshake_only = "--handshake-only" in sys.argv[2:]
    diagnostics_once = "--diagnostics-once" in sys.argv[2:]
    faults_once = "--faults-once" in sys.argv[2:]
    frame38_probe = "--frame38-probe" in sys.argv[2:]
    pty_mode = is_pty_path(dev)

    print(f"Conectando a {dev} @ 4800 8N1 (PTY: {pty_mode})...")
    try:
        ser = serial.Serial(
            port=dev,
            baudrate=4800,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
            write_timeout=0.2,
        )

        # CRITICAL: Disable Python buffering for immediate byte delivery
        if hasattr(ser.fd, "fileno"):
            fd = ser.fd if hasattr(ser, "fd") else ser.fileno()
            # Set O_SYNC flag to bypass kernel buffering
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_SYNC)

        print("Conectado!\n")
        time.sleep(0.2)

        ok = ecu_handshake(ser, pty_mode, skip_5baud, bit_ms)
        if ok:
            print("\n" + "=" * 60)
            print("HANDSHAKE CONCLUÍDO COM SUCESSO!")
            print("=" * 60)
            if handshake_only:
                return True
            if frame38_probe:
                responses = request_data(ser, frame_id=0x38)
                print(f"[FRAME38] transport {'complete' if responses else 'failed'}; "
                      "firmware branch requires PC/RAM trace confirmation")
                return responses is not None
            if faults_once:
                faults = request_data(ser, frame_id=0x07)
                valid = bool(faults) and any(
                    frame["frame_id"] == 0xFC and len(frame["data"]) == 3 and
                    (expected_triplet is None or
                     bytes(frame["data"]) == expected_triplet)
                    for frame in faults)
                print(f"[FAULTS] {'PASS' if valid else 'FAIL'}: 07h"
                      + (f", FC={expected_triplet.hex().upper()}" if
                         expected_triplet is not None else ""))
                return valid
            if diagnostics_once:
                faults = request_data(ser, frame_id=0x07)
                sensor_63 = read_iram_byte(ser, address=0x63)
                sensor_62 = read_iram_byte(ser, address=0x62)
                rpm_47 = read_iram_byte(ser, address=0x47)
                xram_0c = read_memory_byte(ser, selector=0xF8, address=0x0C)
                collection = request_data(ser, frame_id=0x12)
                complete = all((faults, sensor_63, sensor_62, rpm_47,
                                xram_0c, collection))
                readings = (sensor_63, sensor_62, rpm_47, xram_0c)
                snapshot = next((frame["data"] for frame in collection
                                 if frame["frame_id"] == 0xF4 and
                                 len(frame["data"]) == 10), None) if complete else None
                values = [next((frame["data"][0] for frame in frames
                                if frame["frame_id"] == 0xFE and
                                len(frame["data"]) == 1), None)
                          for frames in readings] if complete else []
                valid = complete and any(
                    frame["frame_id"] == 0xFC and len(frame["data"]) == 3
                    for frame in faults
                ) and all(
                    any(frame["frame_id"] == 0xFE and len(frame["data"]) == 1
                        for frame in frames)
                    for frames in readings
                ) and snapshot is not None and values == [
                    snapshot[0], snapshot[3], snapshot[2], snapshot[4]]
                if expected_triplet is not None:
                    valid = valid and any(
                        frame["frame_id"] == 0xFC and
                        bytes(frame["data"]) == expected_triplet
                        for frame in faults)
                print(f"[DIAGNOSTICS] {'PASS' if valid else 'FAIL'}: "
                      "07h faults, IRAM 63h/62h/47h, MOVX 0Ch and 12h collection"
                      + (f", FC={expected_triplet.hex().upper()}" if
                         expected_triplet is not None else ""))
                return valid

            # Entra no loop de keep-alive para manter a conexão
            keep_alive_result = keep_alive_loop(ser, pty_mode)

            if keep_alive_result:
                print("\n[INFO] Conexão encerrada normalmente")
            else:
                print("\n[ERRO] Conexão perdida!")
            return keep_alive_result
        else:
            print("\n[ERRO] Handshake falhou!")
            return False

    except KeyboardInterrupt:
        print("\nEncerrando...")
        return False
    except Exception as e:
        print("Erro:", e)
        import traceback

        traceback.print_exc()
        return False
    finally:
        try:
            ser.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
