// Leitor de EPROM TMS27C256 com Arduino Mega 2560
// Ligações (DIP-28, top view):
//  VCC (28)  -> +5V do Mega
//  VPP (1)   -> +5V do Mega (somente leitura)
//  GND (14)  -> GND do Mega
//  E  (20)   -> GND
//  G  (22)   -> pino digital 18 do Mega (pinG)
//
//  Dados DQ0..DQ7 -> A0..A7 (PORTF)
//    11 (DQ0) -> A0
//    12 (DQ1) -> A1
//    13 (DQ2) -> A2
//    15 (DQ3) -> A3
//    16 (DQ4) -> A4
//    17 (DQ5) -> A5
//    18 (DQ6) -> A6
//    19 (DQ7) -> A7
//
//  Endereços A0..A14 -> pinos digitais:
//    10 (A0)  -> 2
//     9 (A1)  -> 3
//     8 (A2)  -> 4
//     7 (A3)  -> 5
//     6 (A4)  -> 6
//     5 (A5)  -> 7
//     4 (A6)  -> 8
//     3 (A7)  -> 9
//    25 (A8)  -> 10
//    24 (A9)  -> 11
//    21 (A10) -> 12
//    23 (A11) -> 13
//     2 (A12) -> 21
//    26 (A13) -> 20
//    27 (A14) -> 19

unsigned int Address;

// Dados: PORTF (A0..A7)
const byte pinD0 = A0;
const byte pinD1 = A1;
const byte pinD2 = A2;
const byte pinD3 = A3;
const byte pinD4 = A4;
const byte pinD5 = A5;
const byte pinD6 = A6;
const byte pinD7 = A7;

// Endereços
const byte pinA0  = 2;
const byte pinA1  = 3;
const byte pinA2  = 4;
const byte pinA3  = 5;
const byte pinA4  = 6;
const byte pinA5  = 7;
const byte pinA6  = 8;
const byte pinA7  = 9;
const byte pinA8  = 10;
const byte pinA9  = 11;
const byte pinA10 = 12;
const byte pinA11 = 13;
const byte pinA12 = 21;
const byte pinA13 = 20;
const byte pinA14 = 19;

// OE (G)
const byte pinG = 18;  // ativo em LOW

const byte grData[] = {
  pinD0, pinD1, pinD2, pinD3,
  pinD4, pinD5, pinD6, pinD7
};

const byte grAddr[] = {
  pinA0, pinA1, pinA2, pinA3,
  pinA4, pinA5, pinA6, pinA7,
  pinA8, pinA9, pinA10, pinA11,
  pinA12, pinA13, pinA14
};

char szStr[16];

void SetAddress(unsigned int adr)
{
  for (int i = 0; i < 15; i++) {
    digitalWrite(grAddr[i], (adr & (1 << i)) ? HIGH : LOW);
  }
}

void setup(void)
{
  unsigned char idx, databyte;

  Serial.begin(115200);

  // OE começa desativado (HIGH => saídas em Hi-Z)
  pinMode(pinG, OUTPUT);
  digitalWrite(pinG, HIGH);

  // Dados como entrada (pode ser INPUT em vez de INPUT_PULLUP se preferir)
  for (int i = 0; i < 8; i++) {
    pinMode(grData[i], INPUT_PULLUP);
  }

  // Endereços como saída
  for (int i = 0; i < 15; i++) {
    pinMode(grAddr[i], OUTPUT);
    digitalWrite(grAddr[i], LOW);
  }

  Serial.println(F("Dump da EPROM TMS27C256 iniciando..."));
  delay(500);

  Address = 0x0000;
  idx = 0;

  do {
    SetAddress(Address);

    // Habilita saída (OE = LOW)
    digitalWrite(pinG, LOW);

    // Lê todo o PORTF (A0..A7)
    databyte = PINF;

    // Desabilita saída
    digitalWrite(pinG, HIGH);

    // Imprime em HEX
    sprintf(szStr, "%02X ", databyte);
    Serial.print(szStr);

    idx++;
    if (idx == 16) {
      idx = 0;
      Serial.println();
    }

    Address++;

  } while (Address < 0x8000);  // 32 KiB

  Serial.println();
  Serial.println(F("Fim do dump."));
}

void loop(void)
{
  // Nada a fazer: o dump ocorre uma vez no setup().
}
