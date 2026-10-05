#include <Keypad.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

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
LiquidCrystal_I2C lcd(0x27, 16, 2);

void mostrar(uint8_t fila, String texto) {
  lcd.setCursor(0, fila);
  lcd.print("                ");
  lcd.setCursor(0, fila);
  lcd.print(texto.substring(0, 16));
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  mostrar(0, "Tecla: -");
  mostrar(1, "Esperando...");
}

void loop() {
  char tecla = teclado.getKey();
  if (tecla) {
    Serial.println(tecla);
    mostrar(0, String("Tecla: ") + tecla);
  }

  if (Serial.available()) {
    String estado = Serial.readStringUntil('\n');
    estado.trim();
    if (estado.length() > 0) {
      mostrar(1, estado);
    }
  }
}
