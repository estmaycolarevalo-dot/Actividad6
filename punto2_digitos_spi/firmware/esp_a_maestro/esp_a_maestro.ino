#include <SPI.h>

const int PIN_SCK = 18;
const int PIN_MISO = 19;
const int PIN_MOSI = 23;
const int PIN_SS = 5;

const uint8_t MARCA_INICIO = 0xA5;
const uint8_t MARCA_FIN = 0x5A;

void enviarSPI(uint8_t digito, uint8_t confianza) {
  uint8_t tx[4] = {MARCA_INICIO, digito, confianza, MARCA_FIN};
  uint8_t rx[4];
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_SS, LOW);
  delayMicroseconds(100);
  SPI.transferBytes(tx, rx, 4);
  delayMicroseconds(100);
  digitalWrite(PIN_SS, HIGH);
  SPI.endTransaction();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_SS, OUTPUT);
  digitalWrite(PIN_SS, HIGH);
  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI);
  Serial.println("ESP-A maestro SPI lista");
}

void loop() {
  if (Serial.available()) {
    String linea = Serial.readStringUntil('\n');
    linea.trim();
    int coma = linea.indexOf(',');
    if (coma > 0) {
      int digito = linea.substring(0, coma).toInt();
      int confianza = linea.substring(coma + 1).toInt();
      if (digito >= 0 && digito <= 9) {
        enviarSPI(digito, constrain(confianza, 0, 100));
        Serial.printf("SPI -> digito %d (%d%%)\n", digito, confianza);
      }
    }
  }
}
