// T433 TEST v0.1 (19.11.2026) - program DIAGNOSTYCZNY trackera, plytka T433 lite v1.0
//
// Po co: 19.11 ramki statusu z v0.2 (17 dBm, SF12) dochodzily do odbiornika z bledem CRC - poczatek ramki dobry,
// dalej bledy (podejrzenie: plywanie czestotliwosci kwarcu E22 w czasie nadawania), a pakietow zdjecia nie bylo wcale.
// Ten program:
//   1. raz po starcie sprawdza kamere (init, klatka, JPEG) i napiecie,
//   2. w petli nadaje ramki testowe LoRa APRS 433,775 (SF12 BW125 CR4/5) z rozna MOCA i dlugoscia PREAMBULY:
//        krotka  ">T433 TEST K p=<dBm> pre=<n> nr=<k> v=<V> cam=<wynik>"
//        dluga   ">T433 TEST D p=<dBm> pre=<n> nr=<k> " + wypelnienie do 237 B (jak pakiet zdjecia)
//   Odbiornik (tracker433_lite_rx_v0_1 + t433_usb_odbior) pokazuje, ktore przeszly bez bledu CRC.
// Bez GPS, bez uspienia (USB caly czas dziala - log na 115200). Znak w kazdej ramce. Radio od razu bez TCXO.

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "config.h"

#define TEST_WERSJA "T433 TEST v0.1"

static SPIClass spiLora(FSPI);
static SX1268 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_NRST, PIN_LORA_BUSY, spiLora);
static bool radio_ok = false;
static char cam_wynik[40] = "?";
static uint32_t nr = 0;

static const int8_t  MOCE[] = { -9, 0, 5, 10, 14, 17, 22 };
static const uint16_t PREAMB[] = { 8, 64 };

static float vsc() {
  uint32_t mv = 0;
  for (int i = 0; i < 8; i++) mv += analogReadMilliVolts(PIN_VSC_ADC);
  return (mv / 8.0f) / 1000.0f * VSC_DZIELNIK;
}

static void test_kamery() {
  pinMode(PIN_CAM_EN, OUTPUT); digitalWrite(PIN_CAM_EN, HIGH); delay(50);
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
  if (e != ESP_OK) {
    snprintf(cam_wynik, sizeof(cam_wynik), "BLAD init 0x%x", (unsigned)e);
  } else {
    sensor_t *s = esp_camera_sensor_get();
    unsigned pid = s ? s->id.PID : 0;
    for (int i = 0; i < 5; i++) { camera_fb_t *fb = esp_camera_fb_get(); if (fb) esp_camera_fb_return(fb); delay(100); }
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) snprintf(cam_wynik, sizeof(cam_wynik), "BRAK klatki id%02X", pid);
    else {
      uint8_t *jpg = nullptr; size_t jl = 0;
      bool ok = frame2jpg(fb, FOTO_JAKOSC, &jpg, &jl);
      snprintf(cam_wynik, sizeof(cam_wynik), ok ? "OK id%02X %dx%d jpg%u" : "BLAD jpg id%02X %dx%d", pid, (int)fb->width, (int)fb->height, (unsigned)jl);
      if (jpg) free(jpg);
      esp_camera_fb_return(fb);
    }
    esp_camera_deinit();
  }
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, HIGH);
  digitalWrite(PIN_CAM_EN, LOW);
  Serial.printf("TEST: kamera: %s, PSRAM %u B\n", cam_wynik, (unsigned)ESP.getPsramSize());
}

static bool radio_start() {
  spiLora.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int16_t st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, 0, 8, 0, false);   // bez TCXO (E22-400MM22S ma kwarc)
  Serial.printf("TEST: LoRa begin bez TCXO: %d\n", st);
  if (st != RADIOLIB_ERR_NONE) return false;
  radio.setDio2AsRfSwitch(true);
  radio.setRfSwitchPins(PIN_LORA_RXEN, RADIOLIB_NC);
  radio.setCRC(true);
  return true;
}

static void nadaj(bool dluga, int8_t moc, uint16_t pre) {
  static uint8_t buf[256];
  int n = snprintf((char *)buf, sizeof(buf), "<\xff\x01%s-%d>%s:>T433 TEST %c p=%d pre=%u nr=%lu ", ZNAK, SSID, APRS_DEST,
                   dluga ? 'D' : 'K', (int)moc, (unsigned)pre, (unsigned long)nr);
  if (dluga) { while (n < 237) { buf[n] = '0' + (n % 10); n++; } }
  else n += snprintf((char *)buf + n, sizeof(buf) - n, "v=%.2f cam=%s", vsc(), cam_wynik);
  int16_t s1 = radio.setOutputPower(moc), s2 = radio.setPreambleLength(pre);
  uint32_t t0 = millis();
  int16_t st = radio.transmit(buf, n);
  Serial.printf("TEST: nr %lu %s p=%d pre=%u dl=%d czas %lu ms, wynik %d (moc %d, pre %d), VSC po %.2f V\n", (unsigned long)nr,
                dluga ? "DLUGA" : "krotka", (int)moc, (unsigned)pre, n, (unsigned long)(millis() - t0), st, s1, s2, vsc());
  nr++;
  delay(1500);
}

void setup() {
  Serial.begin(115200);
  delay(3000);
  pinMode(PIN_CAM_EN, OUTPUT); digitalWrite(PIN_CAM_EN, LOW);
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, HIGH);
  pinMode(PIN_GPS_EN_N, OUTPUT); digitalWrite(PIN_GPS_EN_N, HIGH);   // GPS wylaczony
  analogReadResolution(12);
  Serial.printf("TEST: %s start, VSC %.2f V\n", TEST_WERSJA, vsc());
  test_kamery();
  radio_ok = radio_start();
}

void loop() {
  if (!radio_ok) { delay(5000); radio_ok = radio_start(); return; }
  for (unsigned ip = 0; ip < sizeof(PREAMB) / sizeof(PREAMB[0]); ip++)
    for (unsigned im = 0; im < sizeof(MOCE) / sizeof(MOCE[0]); im++) {
      nadaj(false, MOCE[im], PREAMB[ip]);
      nadaj(true, MOCE[im], PREAMB[ip]);
    }
  Serial.println("TEST: koniec serii, przerwa 20 s");
  delay(20000);
}
