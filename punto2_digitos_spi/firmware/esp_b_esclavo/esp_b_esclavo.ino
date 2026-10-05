#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "driver/spi_slave.h"
#include "driver/gpio.h"

const int PIN_SCK = 18;
const int PIN_MISO = 19;
const int PIN_MOSI = 23;
const int PIN_CS = 5;

const uint8_t MARCA_INICIO = 0xA5;
const uint8_t MARCA_FIN = 0x5A;

Adafruit_SSD1306 oled(128, 64, &Wire, -1);
uint8_t *bufRx;
uint8_t *bufTx;

void mostrarDigito(int digito, int confianza) {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(6);
  oled.setCursor(18, 8);
  oled.print(digito);
  oled.setTextSize(1);
  oled.setCursor(76, 18);
  oled.print("Digito");
  oled.setCursor(76, 34);
  oled.print(confianza);
  oled.print("%");
  oled.display();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("No se encontro la OLED");
    while (true) delay(1000);
  }
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.println("ESP-B esclavo SPI");
  oled.println("Esperando digito...");
  oled.display();

  spi_bus_config_t bus = {};
  bus.mosi_io_num = PIN_MOSI;
  bus.miso_io_num = PIN_MISO;
  bus.sclk_io_num = PIN_SCK;
  bus.quadwp_io_num = -1;
  bus.quadhd_io_num = -1;

  spi_slave_interface_config_t esclavo = {};
  esclavo.spics_io_num = PIN_CS;
  esclavo.flags = 0;
  esclavo.queue_size = 1;
  esclavo.mode = 0;

  gpio_set_pull_mode((gpio_num_t)PIN_SCK, GPIO_PULLUP_ONLY);
  gpio_set_pull_mode((gpio_num_t)PIN_MOSI, GPIO_PULLUP_ONLY);
  gpio_set_pull_mode((gpio_num_t)PIN_CS, GPIO_PULLUP_ONLY);

  esp_err_t err = spi_slave_initialize(SPI3_HOST, &bus, &esclavo, SPI_DMA_CH_AUTO);
  if (err != ESP_OK) {
    Serial.printf("Error iniciando SPI esclavo: %d\n", err);
    while (true) delay(1000);
  }

  bufRx = (uint8_t *)heap_caps_malloc(4, MALLOC_CAP_DMA);
  bufTx = (uint8_t *)heap_caps_malloc(4, MALLOC_CAP_DMA);
  memset(bufTx, 0, 4);
  Serial.println("ESP-B esclavo SPI lista");
}

void loop() {
  memset(bufRx, 0, 4);
  spi_slave_transaction_t t = {};
  t.length = 4 * 8;
  t.tx_buffer = bufTx;
  t.rx_buffer = bufRx;

  if (spi_slave_transmit(SPI3_HOST, &t, portMAX_DELAY) == ESP_OK) {
    if (bufRx[0] == MARCA_INICIO && bufRx[3] == MARCA_FIN && bufRx[1] <= 9) {
      Serial.printf("SPI <- digito %d (%d%%)\n", bufRx[1], bufRx[2]);
      mostrarDigito(bufRx[1], bufRx[2]);
    }
  }
}
