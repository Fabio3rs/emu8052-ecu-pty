#include <array>
#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>
#include <algorithm>

#include <fcntl.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

namespace fs = std::filesystem;

// Baud rate fixo
constexpr int BAUD_RATE = B115200;
constexpr std::size_t EXPECTED_SIZE = 0x8000; // 32 KiB padrão do 27C256

// Lança std::system_error se der erro
void throw_if_neg(int ret, std::string_view msg) {
    if (ret < 0) {
        throw std::system_error(errno, std::generic_category(),
                                std::string(msg));
    }
}

int open_serial(std::string_view port) {
    int fd = ::open(port.data(), O_RDWR | O_NOCTTY | O_SYNC);
    if (fd < 0) {
        throw std::system_error(errno, std::generic_category(),
                                "Falha ao abrir porta serial");
    }

    termios tty{};
    throw_if_neg(tcgetattr(fd, &tty), "tcgetattr falhou");

    // Configura 115200 8N1, sem controle de fluxo
    cfsetospeed(&tty, BAUD_RATE);
    cfsetispeed(&tty, BAUD_RATE);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8; // 8 bits
    tty.c_cflag |= (CLOCAL | CREAD);            // habilita receiver, ignora modem
    tty.c_cflag &= ~(PARENB | PARODD);          // sem paridade
    tty.c_cflag &= ~CSTOPB;                     // 1 stop bit
    tty.c_cflag &= ~CRTSCTS;                    // sem RTS/CTS

    tty.c_iflag = 0;
    tty.c_oflag = 0;
    tty.c_lflag = 0;                            // modo "raw"

    tty.c_cc[VMIN]  = 0;    // leitura não-bloqueante completa
    tty.c_cc[VTIME] = 10;   // timeout ~1s (10 * 100 ms)

    throw_if_neg(tcsetattr(fd, TCSANOW, &tty), "tcsetattr falhou");

    // Limpa buffers da serial
    tcflush(fd, TCIFLUSH);
    tcflush(fd, TCOFLUSH);

    return fd;
}

// Reset via DTR
void reboot_arduino(int fd) {
    int status{};
    throw_if_neg(ioctl(fd, TIOCMGET, &status), "ioctl(TIOCMGET) falhou");

    // Desliga DTR
    status &= ~TIOCM_DTR;
    throw_if_neg(ioctl(fd, TIOCMSET, &status), "ioctl(TIOCMSET) falhou (clear DTR)");
    usleep(100'000); // 100 ms

    // Liga DTR
    status |= TIOCM_DTR;
    throw_if_neg(ioctl(fd, TIOCMSET, &status), "ioctl(TIOCMSET) falhou (set DTR)");

    // Espera bootloader + setup()
    sleep(2);
}

// Lê uma linha terminada em '\n'
std::string read_line(int fd) {
    std::string line;
    std::array<char, 1> buf{};

    while (true) {
        ssize_t n = ::read(fd, buf.data(), buf.size());
        if (n < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // Timeout
                break;
            }
            throw std::system_error(errno, std::generic_category(),
                                    "Erro ao ler da serial");
        }
        if (n == 0) {
            // Timeout
            break;
        }

        char c = buf[0];
        if (c == '\n') {
            break;
        }
        if (c != '\r') {
            line.push_back(c);
        }
    }

    return line;
}

bool wait_for_begin(int fd) {
    std::cout << "Aguardando início do dump...\n";
    while (true) {
        auto line = read_line(fd);
        if (line.empty()) {
            std::cout << "Timeout aguardando início...\n";
            return false;
        }
        std::cout << "RX: " << line << '\n';
        if (line.find("Dump da EPROM") != std::string::npos) {
            std::cout << ">>> Início do dump detectado.\n";
            return true;
        }
    }
}

std::vector<std::uint8_t> read_dump(int fd) {
    std::vector<std::uint8_t> data;
    data.reserve(EXPECTED_SIZE);

    while (true) {
        auto line = read_line(fd);
        if (line.empty()) {
            std::cout << "Timeout lendo dump.\n";
            break;
        }

        if (line == "" ||
            std::all_of(line.begin(), line.end(),
                        [](unsigned char c){ return std::isspace(c); })) {
            continue;
        }

        if (line.find("Fim do dump") != std::string::npos) {
            std::cout << ">>> Fim do dump encontrado.\n";
            break;
        }

        // "00 1F 3A ..." -> bytes
        std::string token;
        for (std::size_t i = 0; i <= line.size(); ++i) {
            char c = (i < line.size()) ? line[i] : ' ';
            if (!std::isspace(static_cast<unsigned char>(c))) {
                token.push_back(c);
            } else if (!token.empty()) {
                if (token.size() == 2) {
                    try {
                        std::uint8_t value =
                            static_cast<std::uint8_t>(std::stoul(token, nullptr, 16));
                        data.push_back(value);
                    } catch (...) {
                        // ignora token inválido
                    }
                }
                token.clear();
            }
        }

        if (data.size() >= EXPECTED_SIZE) {
            std::cout << ">>> Atingiu tamanho esperado de 0x"
                      << std::hex << EXPECTED_SIZE << " bytes.\n"
                      << std::dec;
            break;
        }
    }

    return data;
}

int main(int argc, char* argv[]) {
    try {
        if (argc < 2 || argc > 3) {
            std::cerr << "Uso:\n"
                      << "  " << argv[0] << " <porta_serial> [arquivo_saida]\n\n"
                      << "Exemplos:\n"
                      << "  " << argv[0] << " /dev/ttyACM0\n"
                      << "  " << argv[0] << " /dev/ttyUSB0 dump_27c256.bin\n";
            return 1;
        }

        std::string port = argv[1];
        fs::path out_path = (argc >= 3) ? fs::path{argv[2]}
                                        : fs::path{"dump_27c256.bin"};

        std::cout << "Abrindo porta " << port << " @ 115200...\n";
        int fd = open_serial(port);

        struct FdGuard {
            int fd;
            ~FdGuard() { if (fd >= 0) ::close(fd); }
        } guard{fd};

        // Resetar Arduino (opcional, mas ajuda a pegar o dump desde o início)
        reboot_arduino(fd);

        if (!wait_for_begin(fd)) {
            std::cerr << "Não foi possível encontrar o início do dump.\n";
            return 1;
        }

        auto dump = read_dump(fd);
        std::cout << "Lido " << dump.size() << " bytes.\n";

        {
            std::ofstream ofs(out_path, std::ios::binary);
            if (!ofs) {
                std::cerr << "Falha ao abrir arquivo de saída: "
                          << out_path << '\n';
                return 1;
            }
            ofs.write(reinterpret_cast<const char*>(dump.data()),
                      static_cast<std::streamsize>(dump.size()));
        }

        std::cout << "Dump salvo em: " << fs::absolute(out_path) << '\n';
        return 0;
    } catch (const std::system_error& e) {
        std::cerr << "Erro de sistema: " << e.what()
                  << " (errno=" << e.code().value() << ")\n";
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Exceção: " << e.what() << '\n';
        return 1;
    } catch (...) {
        std::cerr << "Exceção desconhecida.\n";
        return 1;
    }
}

