// T433 TEST v0.3 (19.11.2026) - DIAGNOSTYKA KAMERY, plytka T433 lite v1.0
//
// Kamera OV2640 (TY-OV2640-V1.0) wlozona stykami do plytki zglasza "init 0x105" (brak odpowiedzi) i sie grzeje.
// Program sprawdza linie zlacza kamery i nadaje wynik w jednej ramce LoRa APRS (5 dBm), powtorzonej kilka razy:
//   >T433 KAM pd=<15 znakow> pu=<15> akt=<11> i2c=<adresy|brak> init=<wynik> v=<V>
// Kolejnosc linii w pd/pu: Y2 Y3 Y4 Y5 Y6 Y7 Y8 Y9 PCLK VSYNC HREF SIOD SIOC PWDN XCLK
//   pd = stan przy wewnetrznym rezystorze do masy, pu = przy rezystorze do plusa, kamera WYLACZONA (CAM_EN = 0)
//   (pd 0 / pu 1 = linia wisi; pd 1 = cos ja ciagnie do plusa; pu 0 = cos ja ciagnie do masy)
// akt = aktywnosc linii Y2..Y9 PCLK VSYNC HREF przez 300 ms przy wlaczonej kamerze i zegarze XCLK 20 MHz:
//   0 = brak zmian, 1 = 1-9 zmian, 2 = 10-99, 3 = 100-999, 4 = 1000-9999, 5 = wiecej
// i2c = adresy odpowiadajace na magistrali SIOD/SIOC (OV2640 = 30)
// Po pomiarze kamera jest wylaczana. Bez GPS, bez uspienia.

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <RadioLib.h>
#include "esp_camera.h"
#include "soc/gpio_reg.h"
#include "config.h"

#define TEST_WERSJA "T433 TEST v0.3"

static SPIClass spiLora(FSPI);
static SX1268 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_NRST, PIN_LORA_BUSY, spiLora);

static const uint8_t LINIE[15] = { CAM_Y2, CAM_Y3, CAM_Y4, CAM_Y5, CAM_Y6, CAM_Y7, CAM_Y8, CAM_Y9, CAM_PCLK, CAM_VSYNC, CAM_HREF,
                                   CAM_SIOD, CAM_SIOC, CAM_PWDN, CAM_XCLK };
static char s_pd[16], s_pu[16], s_akt[12], s_i2c[40], s_init[24];

static float vsc() {
  uint32_t mv = 0;
  for (int i = 0; i < 8; i++) mv += analogReadMilliVolts(PIN_VSC_ADC);
  return (mv / 8.0f) / 1000.0f * VSC_DZIELNIK;
}

static inline uint64_t wejscia() { return ((uint64_t)REG_READ(GPIO_IN1_REG) << 32) | REG_READ(GPIO_IN_REG); }

static void diagnostyka() {
  // 1. stany spoczynkowe, kamera wylaczona
  pinMode(PIN_CAM_EN, OUTPUT); digitalWrite(PIN_CAM_EN, LOW);
  for (int i = 0; i < 15; i++) { pinMode(LINIE[i], INPUT_PULLDOWN); }
  delay(20);
  for (int i = 0; i < 15; i++) s_pd[i] = digitalRead(LINIE[i]) ? '1' : '0';
  for (int i = 0; i < 15; i++) { pinMode(LINIE[i], INPUT_PULLUP); }
  delay(20);
  for (int i = 0; i < 15; i++) s_pu[i] = digitalRead(LINIE[i]) ? '1' : '0';
  s_pd[15] = s_pu[15] = 0;
  for (int i = 0; i < 15; i++) pinMode(LINIE[i], INPUT);

  // 2. kamera wlaczona, PWDN = 0, XCLK 20 MHz, aktywnosc linii
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, LOW);
  digitalWrite(PIN_CAM_EN, HIGH);
  delay(50);
  bool xclk = ledcAttach(CAM_XCLK, 20000000, 1);
  ledcWrite(CAM_XCLK, 1);
  delay(200);
  uint32_t zmiany[11] = {0};
  uint64_t pop = wejscia();
  uint32_t t0 = millis();
  while (millis() - t0 < 300) {
    for (int k = 0; k < 200; k++) {
      uint64_t w = wejscia(), r = w ^ pop; pop = w;
      if (r) for (int i = 0; i < 11; i++) if (r & (1ULL << LINIE[i])) zmiany[i]++;
    }
  }
  for (int i = 0; i < 11; i++) {
    uint32_t z = zmiany[i];
    s_akt[i] = z == 0 ? '0' : z < 10 ? '1' : z < 100 ? '2' : z < 1000 ? '3' : z < 10000 ? '4' : '5';
  }
  s_akt[11] = 0;

  // 3. magistrala SIOD/SIOC
  Wire.begin(CAM_SIOD, CAM_SIOC, 100000);
  int n = 0; s_i2c[0] = 0;
  for (uint8_t a = 0x08; a < 0x78 && n < 30; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) n += snprintf(s_i2c + n, sizeof(s_i2c) - n, "%s%02X", n ? "," : "", a);
  }
  if (!n) strcpy(s_i2c, "brak");
  Wire.end();
  ledcDetach(CAM_XCLK);
  Serial.printf("TEST: pd=%s pu=%s akt=%s i2c=%s xclk=%d\n", s_pd, s_pu, s_akt, s_i2c, xclk);

  // 4. zwykly init sterownika (jak w v0.2)
  camera_config_t c = {};
  c.pin_pwdn = CAM_PWDN; c.pin_reset = -1; c.pin_xclk = CAM_XCLK;
  c.pin_sccb_sda = CAM_SIOD; c.pin_sccb_scl = CAM_SIOC;
  c.pin_d7 = CAM_Y9; c.pin_d6 = CAM_Y8; c.pin_d5 = CAM_Y7; c.pin_d4 = CAM_Y6;
  c.pin_d3 = CAM_Y5; c.pin_d2 = CAM_Y4; c.pin_d1 = CAM_Y3; c.pin_d0 = CAM_Y2;
  c.pin_vsync = CAM_VSYNC; c.pin_href = CAM_HREF; c.pin_pclk = CAM_PCLK;
  c.xclk_freq_hz = 20000000; c.ledc_timer = LEDC_TIMER_0; c.ledc_channel = LEDC_CHANNEL_0;
  c.pixel_format = PIXFORMAT_RGB565; c.frame_size = FOTO_ROZM;
  c.jpeg_quality = 12; c.fb_count = 1; c.fb_location = CAMERA_FB_IN_PSRAM; c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t e = esp_camera_init(&c);
  if (e != ESP_OK) snprintf(s_init, sizeof(s_init), "0x%x", (unsigned)e);
  else {
    sensor_t *s = esp_camera_sensor_get();
    snprintf(s_init, sizeof(s_init), "OK id%02X", s ? (unsigned)s->id.PID : 0);
    esp_camera_deinit();
  }
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, HIGH);
  digitalWrite(PIN_CAM_EN, LOW);
  Serial.printf("TEST: init=%s\n", s_init);
}

static bool radio_start() {
  spiLora.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int16_t st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, -9, 8, 0, false);
  Serial.printf("TEST: LoRa begin bez TCXO: %d\n", st);
  if (st != RADIOLIB_ERR_NONE) return false;
  radio.setDio2AsRfSwitch(true);
  radio.setRfSwitchPins(PIN_LORA_RXEN, RADIOLIB_NC);
  radio.setCRC(true);
  return true;
}

static void nadaj(int8_t moc, const char *tresc) {
  static uint8_t buf[256];
  int n = snprintf((char *)buf, sizeof(buf), "<\xff\x01%s-%d>%s:>%s", ZNAK, SSID, APRS_DEST, tresc);
  radio.setOutputPower(moc);
  int16_t st = radio.transmit(buf, n);
  Serial.printf("TEST: nadano %d B, moc %d, wynik %d\n", n, (int)moc, st);
  delay(1500);
}

void setup() {
  Serial.begin(115200);
  delay(3000);
  pinMode(PIN_GPS_EN_N, OUTPUT); digitalWrite(PIN_GPS_EN_N, HIGH);
  analogReadResolution(12);
  Serial.printf("TEST: %s start, VSC %.2f V\n", TEST_WERSJA, vsc());
  diagnostyka();
  if (!radio_start()) return;
  char t[200];
  nadaj(-9, "T433 KAM rozgrzewka");
  for (int i = 0; i < 4; i++) {
    snprintf(t, sizeof(t), "T433 KAM pd=%s pu=%s akt=%s i2c=%s init=%s v=%.2f", s_pd, s_pu, s_akt, s_i2c, s_init, vsc());
    nadaj(5, t);
  }
  radio.sleep();
  Serial.println("TEST: koniec, wylacz zasilanie");
}

void loop() { delay(1000); }
