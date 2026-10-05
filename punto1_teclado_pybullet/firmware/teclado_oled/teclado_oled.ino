#include <Keypad.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const byte FILAS = 4;
const byte COLUMNAS = 4;
char teclas[FILAS][COLUMNAS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};
byte pinesFilas[FILAS] = {13, 14, 27, 26};
byte pinesColumnas[COLUMNAS] = {25, 33, 32, 4};

Keypad teclado = Keypad(makeKeymap(teclas), pinesFilas, pinesColumnas, FILAS, COLUMNAS);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

char ultimaTecla = '-';
String estado = "Esperando...";

void dibujar() {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.print("Tecla:");
  oled.setTextSize(4);
  oled.setCursor(0, 14);
  oled.print(ultimaTecla);
  oled.setTextSize(1);
  oled.setCursor(0, 54);
  oled.print(estado.substring(0, 21));
  oled.display();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("No se encontro la OLED");
    while (true) delay(1000);
  }
  dibujar();
}

void loop() {
  char tecla = teclado.getKey();
  if (tecla) {
    Serial.println(tecla);
    ultimaTecla = tecla;
    dibujar();
  }

  if (Serial.available()) {
    String texto = Serial.readStringUntil('\n');
    texto.trim();
    if (texto.length() > 0) {
      estado = texto;
      dibujar();
    }
  }
}
