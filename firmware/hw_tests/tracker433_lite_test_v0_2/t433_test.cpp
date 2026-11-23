// T433 TEST v0.2 (19.11.2026) - program DIAGNOSTYCZNY "zimny start", plytka T433 lite v1.0
//
// Wynik TEST v0.1: przy radiu rozgrzewanym stopniowo wszystkie ramki przechodza, takze 17 i 22 dBm.
// v0.2 trackera psul PIERWSZA ramke po starcie (17 dBm, zimne radio, GPS wlaczony, start radia przez nieudana probe TCXO).
// Ten program odtwarza to i zdejmuje po jednym czynniku. 5 wariantow, w kazdym 3 krotkie ramki pod rzad
// (pierwsza = zimna), miedzy wariantami 150 s chlodzenia (radio uspione):
//   W1: jak v0.2 - start radia z proba TCXO, GPS wlaczony, 17 dBm, wstep 8
//   W2: start radia od razu bez TCXO, GPS wlaczony, 17 dBm, wstep 8
//   W3: bez TCXO, GPS wylaczony, 17 dBm, wstep 8
//   W4: bez TCXO, GPS wylaczony, 17 dBm, wstep 64
//   W5: bez TCXO, GPS wylaczony, 10 dBm, wstep 8
// Ramka: ">T433 ZIM w=<wariant> f=<1..3> p=<dBm> pre=<n> gps=<0|1> tcxo=<0|1> v=<V> cam=<wynik>"
// Ponizej opis z v0.1:
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

#define TEST_WERSJA "T433 TEST v0.2"

static SPIClass spiLora(FSPI);
static SX1268 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_NRST, PIN_LORA_BUSY, spiLora);
static bool radio_ok = false;
static char cam_wynik[40] = "?";
static uint32_t nr = 0;


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


struct Wariant { uint8_t nr; bool proba_tcxo; bool gps; int8_t moc; uint16_t pre; };
static const Wariant WAR[] = {
  {1, true,  true,  17, 8},
  {2, false, true,  17, 8},
  {3, false, false, 17, 8},
  {4, false, false, 17, 64},
  {5, false, false, 10, 8},
};

static bool radio_start(bool proba_tcxo) {
  spiLora.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int16_t st;
  if (proba_tcxo) {                       // dokladnie jak v0.2: najpierw z TCXO 1,8 V, po bledzie bez
    st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, 17, 8, LORA_TCXO_V, false);
    Serial.printf("TEST: LoRa begin z TCXO: %d\n", st);
    if (st != RADIOLIB_ERR_NONE) st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, 17, 8, 0, false);
  } else {
    st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, 17, 8, 0, false);
  }
  Serial.printf("TEST: LoRa begin: %d\n", st);
  if (st != RADIOLIB_ERR_NONE) return false;
  radio.setDio2AsRfSwitch(true);
  radio.setRfSwitchPins(PIN_LORA_RXEN, RADIOLIB_NC);
  radio.setCRC(true);
  return true;
}

static void gps_wlacz(bool on) { pinMode(PIN_GPS_EN_N, OUTPUT); digitalWrite(PIN_GPS_EN_N, on ? LOW : HIGH); }

static void wariant(const Wariant &w) {
  gps_wlacz(w.gps);
  if (w.gps) delay(20000);                // GPS pracuje 20 s przed nadawaniem, jak w cyklu v0.2
  if (!radio_start(w.proba_tcxo)) { Serial.println("TEST: radio nie wystartowalo"); return; }
  radio.setOutputPower(w.moc); radio.setPreambleLength(w.pre);
  for (int f = 1; f <= 3; f++) {
    static uint8_t buf[256];
    int n = snprintf((char *)buf, sizeof(buf), "<\xff\x01%s-%d>%s:>T433 ZIM w=%u f=%d p=%d pre=%u gps=%d tcxo=%d v=%.2f cam=%s", ZNAK, SSID, APRS_DEST,
                     (unsigned)w.nr, f, (int)w.moc, (unsigned)w.pre, w.gps ? 1 : 0, w.proba_tcxo ? 1 : 0, vsc(), cam_wynik);
    uint32_t t0 = millis();
    int16_t st = radio.transmit(buf, n);
    Serial.printf("TEST: w=%u f=%d dl=%d czas %lu ms wynik %d VSC %.2f V\n", (unsigned)w.nr, f, n, (unsigned long)(millis() - t0), st, vsc());
    delay(1500);
  }
  radio.sleep();
  gps_wlacz(false);
}

void setup() {
  Serial.begin(115200);
  delay(3000);
  pinMode(PIN_CAM_EN, OUTPUT); digitalWrite(PIN_CAM_EN, LOW);
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, HIGH);
  gps_wlacz(false);
  analogReadResolution(12);
  Serial.printf("TEST: %s start, VSC %.2f V\n", TEST_WERSJA, vsc());
  test_kamery();
}

void loop() {
  for (unsigned i = 0; i < sizeof(WAR) / sizeof(WAR[0]); i++) {
    wariant(WAR[i]);
    Serial.println("TEST: chlodzenie 150 s");
    delay(150000);
  }
  Serial.println("TEST: koniec serii, od nowa");
}
