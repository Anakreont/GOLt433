// T433 - tracker 433 MHz z kamera - oprogramowanie LITE v0.6 (21.11.2026) - plytka T433 lite v1.0 (ESP32-S3-MINI-1U)
//
// v0.6 (21.11.2026 20:15, po potwierdzeniu wznawiania na sprzecie; "korekta softu ile mozna"):
//   - licznik zdjec bez GPS zapisywany we flashu (/licz.bin) - numery 240..255 nie zaczynaja sie od 240 po kazdym restarcie
//   - POZYCJA_MIN_WYS_M: ponizej tej wysokosci zamiast ramki pozycji idzie status ">T433 x.xxV alt ..m sat .. img .. loc KO00"
//     (bez wspolrzednych) - dokladne miejsce startu / domu nie trafia na aprs.fi
//   - zegar procesora 80 MHz poza robieniem zdjecia (mniejszy pobor pradu przy GPS i nadawaniu)
//   - FOTO_ODWROC / FOTO_LUSTRO - obrot obrazu w konfiguracji
//   - przerwa miedzy pakietami 0,8 s (bylo 1,5 s)
//   - stan zdjecia zapisywany tylko wtedy, gdy zdjecie na pewno jest we flashu
//
// v0.5 (21.11.2026 19:45, prosba autora: "wartosciowe jest pelne zdjecie, niewazne kiedy"):
//   - WZNAWIANIE ZDJECIA: JPEG i numer nastepnego pakietu sa zapisywane w pamieci flash (LittleFS: /zdj.jpg, /stan.bin).
//     Po restarcie (zanik zasilania z paneli) tracker nie robi nowego zdjecia, tylko dosyla reszte starego - bez czekania na GPS,
//     od pakietu o jeden wczesniejszego niz ostatnio wyslany. Po WZNOWIEN_MAX wznowieniach zdjecie jest porzucane.
//     Po dokonczeniu wznowionego zdjecia od razu nowy cykl. Status przy wznowieniu: ">T433 x.xxV wznowienie img n".
//   - CZEKANIE NA SLONCE: VSC < VSC_CZEKAJ miedzy pakietami -> radio uspione, lekkie uspienie procesora, az VSC >= VSC_DALEJ
//     (max CZEKANIE_MAX_S, potem uspienie na CYKL_S - zdjecie zostaje do wznowienia). Po przerwie > 20 s dwie ramki rozgrzewki.
//
// v0.4 (21.11.2026 19:30): ROZGRZEWKA - ramka pozycji/statusu ROZGRZEWKA_RAMEK razy na poczatku cyklu. Test v0.3: bledy CRC mialy
//   dwie pierwsze ramki (status 48 B i pakiet 0 zdjecia), mimo wylaczonego GPS - przyczyna jest dryf zimnego kwarcu E22
//   (odchylka -706 -> -573 -> -151 -> +132 Hz co 10 s), nie GPS. Klatka 640x480 i reszta v0.3 - potwierdzone na sprzecie.
//
// Zmiany v0.3 wzgledem v0.2 (decyzje autora 21.11.2026 po pierwszym zdjeciu):
//   - zdjecie 640x480 BEZ napisu (bylo 320x240 z napisem na gorze i na dole); gdy kamera nie da 640x480 - 320x240
//   - pozycja PUBLICZNIE zwykla ramka APRS z czasem fixu ("/GGMMSSh...O kurs/predkosc /A=wysokosc T433 ...V sat .. img ..")
//     -> bramki LoRa APRS -> APRS-IS (aprs.fi); powtarzana co POZYCJA_CO_PAKIETOW pakietow zdjecia; ramka prywatna wylaczona
//   - GPS wylaczany przed nadawaniem (oszczednosc pradu; hipoteza, ze to on psul pierwsza ramke, NIE potwierdzila sie)
//   - radio od razu bez TCXO (E22-400MM22S ma kwarc)
//   - numer zdjecia z czasu GPS (godzina*10 + minuta/6), zeby po restarcie z braku zasilania numery sie nie powtarzaly;
//     bez fixu: 240 + licznik
//   - VSC > VSC_BEZ_SNU: bez uspienia, od razu nastepny cykl (ochrona diody Zenera przy 8 ogniwach)
//   - watchdog (WATCHDOG_S bez postepu = restart), limit MAX_PAKIETOW
//
// Cykl:
//   1. pomiar VSC   2. GPS: wlaczenie, czekanie na fix, wylaczenie
//   3. LoRa APRS 433,775: ramka pozycji (albo status "brak GPS")
//   4. zdjecie 640x480 -> JPEG -> SSDV w pakietach LoRa APRS "{{I" + base91 (format Pecan Pico)
//   5. uspienie CYKL_S
//
// Bez szyfrowania (przepisy krotkofalarskie). Znak w kazdej ramce.
// Arduino: plytka "ESP32S3 Dev Module", PSRAM: QSPI PSRAM, Flash 4MB, USB CDC On Boot: Enabled.

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include <TinyGPSPlus.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "esp_sleep.h"
#include "esp_task_wdt.h"
#include <LittleFS.h>
#include "config.h"
extern "C" {
#include "ssdv.h"
#include "base91.h"
}

static SPIClass spiLora(FSPI);
static SX1268 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_NRST, PIN_LORA_BUSY, spiLora);
static TinyGPSPlus gps;
static HardwareSerial GPSSerial(1);

static uint8_t nr_zdjecia = 0;                 // v0.3: z czasu GPS (patrz cykl); bez fixu 240 + licznik z flasha (v0.6)
RTC_DATA_ATTR static uint32_t nr_cyklu = 0;

static bool radio_ok = false;
static bool radio_tryb_aprs = true;

// fix zapamietany na caly cykl (GPS jest wylaczany przed nadawaniem)
static struct { bool ok; double lat, lon; float alt, kurs, wezly; uint8_t h, m, s; unsigned sat; } fx;

static inline void pies() { esp_task_wdt_reset(); }

// ---------------------------------------------------------------- stan zdjecia w pamieci flash (wznawianie po restarcie)
struct StanZdj { uint32_t magia; uint8_t img; uint8_t wznowien; uint16_t nastepny; uint32_t dl; };
#define STAN_MAGIA 0x54343335UL
static bool fs_ok = false;
static bool wznowienie = false;      // ten cykl dosyla stare zdjecie
static bool po_wznowieniu = false;   // wznowione zdjecie dokonczone -> od razu nowy cykl
static StanZdj st;

static bool stan_aktywny = false;    // v0.6: zdjecie jest we flashu i stan mozna zapisywac

// v0.6: licznik zdjec bez GPS we flashu - po restarcie numeracja idzie dalej
static uint8_t licznik_bez_fixu_nastepny() {
  uint8_t n = 0;
  if (!fs_ok) return (uint8_t)(esp_random() & 15);
  File f = LittleFS.open("/licz.bin", "r");
  if (f) { f.read(&n, 1); f.close(); }
  f = LittleFS.open("/licz.bin", "w");
  if (f) { uint8_t k = n + 1; f.write(&k, 1); f.close(); }
  return n & 15;
}

static void lokator4(double lat, double lon, char *wy) {      // duzy kwadrat, np. KO00
  lon += 180.0; lat += 90.0;
  wy[0] = 'A' + (int)(lon / 20); wy[1] = 'A' + (int)(lat / 10);
  wy[2] = '0' + (int)(fmod(lon, 20.0) / 2); wy[3] = '0' + (int)fmod(lat, 10.0); wy[4] = 0;
}

static void stan_zapisz() {
  if (!fs_ok || !stan_aktywny) return;
  File f = LittleFS.open("/stan.bin", "w");
  if (f) { f.write((const uint8_t *)&st, sizeof(st)); f.close(); }
}
static void stan_usun() { if (fs_ok) LittleFS.remove("/stan.bin"); }
static bool stan_wczytaj() {
  if (!fs_ok) return false;
  File f = LittleFS.open("/stan.bin", "r");
  if (!f) return false;
  bool ok = f.read((uint8_t *)&st, sizeof(st)) == sizeof(st) && st.magia == STAN_MAGIA;
  f.close();
  if (!ok) return false;
  File z = LittleFS.open("/zdj.jpg", "r");
  if (!z) return false;
  ok = z.size() == st.dl && st.dl > 0;
  z.close();
  return ok;
}
static bool zdj_zapisz(const uint8_t *jpg, size_t dl) {
  if (!fs_ok) return false;
  stan_usun();                                   // najpierw stary stan, zeby nie wskazywal na nowy plik
  File f = LittleFS.open("/zdj.jpg", "w");
  if (!f) return false;
  size_t n = 0;
  while (n < dl) { size_t k = f.write(jpg + n, (dl - n) > 4096 ? 4096 : (dl - n)); if (!k) break; n += k; pies(); }
  f.close();
  return n == dl;
}
static uint8_t *zdj_wczytaj(size_t dl) {
  File f = LittleFS.open("/zdj.jpg", "r");
  if (!f) return nullptr;
  uint8_t *b = (uint8_t *)ps_malloc(dl);
  if (b && f.read(b, dl) != dl) { free(b); b = nullptr; }
  f.close();
  return b;
}

// ---------------------------------------------------------------- zasilanie
static float vsc() {
  uint32_t mv = 0;
  for (int i = 0; i < 8; i++) mv += analogReadMilliVolts(PIN_VSC_ADC);
  return (mv / 8.0f) / 1000.0f * VSC_DZIELNIK;
}

// ---------------------------------------------------------------- LoRa
static bool lora_aprs() {
  int16_t st;
  if (!radio_ok) {
    spiLora.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
    st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, LORA_MOC_DBM, 8, LORA_TCXO_V, false);
    if (st != RADIOLIB_ERR_NONE) { Serial.printf("LoRa: begin blad %d\n", st); return false; }
    radio.setDio2AsRfSwitch(true);                         // DIO2 -> TXEN modulu E22
    radio.setRfSwitchPins(PIN_LORA_RXEN, RADIOLIB_NC);     // RXEN z GPIO7
    radio.setCRC(true);
    radio_ok = true; radio_tryb_aprs = true;
    return true;
  }
  if (!radio_tryb_aprs) {
    radio.setFrequency(APRS_FREQ); radio.setSpreadingFactor(APRS_SF); radio.setBandwidth(APRS_BW); radio.setCodingRate(APRS_CR);
    radio_tryb_aprs = true;
  }
  return true;
}

static bool lora_pryw() {
  if (!lora_aprs()) return false;
  radio.setFrequency(PRYW_FREQ); radio.setSpreadingFactor(PRYW_SF); radio.setBandwidth(PRYW_BW); radio.setCodingRate(PRYW_CR);
  radio_tryb_aprs = false;
  return true;
}

// ramka LoRa APRS: "<\xff\x01" + naglowek TNC2 + tresc
static bool wyslij_aprs(const char *tresc, size_t dl) {
  if (!lora_aprs()) return false;
  static uint8_t buf[256];
  char nag[40];
  int n = snprintf(nag, sizeof(nag), "%s-%d>%s%s%s:", ZNAK, SSID, APRS_DEST, strlen(APRS_PATH) ? "," : "", APRS_PATH);
  if (3 + n + dl > 255) { Serial.println("APRS: za dluga ramka"); return false; }
  buf[0] = '<'; buf[1] = 0xFF; buf[2] = 0x01;
  memcpy(buf + 3, nag, n); memcpy(buf + 3 + n, tresc, dl);
  int16_t st = radio.transmit(buf, 3 + n + dl);
  if (st != RADIOLIB_ERR_NONE) Serial.printf("APRS: blad nadawania %d\n", st);
  return st == RADIOLIB_ERR_NONE;
}

// ---------------------------------------------------------------- GPS
static void gps_wlacz(bool on) {
  pinMode(PIN_GPS_EN_N, OUTPUT); digitalWrite(PIN_GPS_EN_N, on ? LOW : HIGH);
  if (on) GPSSerial.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
}

static bool gps_fix(uint32_t timeout_s) {
  uint32_t t0 = millis();
  while (millis() - t0 < timeout_s * 1000UL) {
    while (GPSSerial.available()) gps.encode(GPSSerial.read());
    pies();
    if (gps.location.isValid() && gps.location.age() < 2000 && gps.altitude.isValid() && gps.satellites.value() >= 4) return true;
    delay(20);
  }
  return false;
}

// ---------------------------------------------------------------- kamera
static bool kamera_start(framesize_t rozm) {
  pinMode(PIN_CAM_EN, OUTPUT); digitalWrite(PIN_CAM_EN, HIGH); delay(50);   // LDO 2,8 V / 1,2 V
  camera_config_t c = {};
  c.pin_pwdn = CAM_PWDN; c.pin_reset = -1; c.pin_xclk = CAM_XCLK;
  c.pin_sccb_sda = CAM_SIOD; c.pin_sccb_scl = CAM_SIOC;
  c.pin_d7 = CAM_Y9; c.pin_d6 = CAM_Y8; c.pin_d5 = CAM_Y7; c.pin_d4 = CAM_Y6;
  c.pin_d3 = CAM_Y5; c.pin_d2 = CAM_Y4; c.pin_d1 = CAM_Y3; c.pin_d0 = CAM_Y2;
  c.pin_vsync = CAM_VSYNC; c.pin_href = CAM_HREF; c.pin_pclk = CAM_PCLK;
  c.xclk_freq_hz = 20000000; c.ledc_timer = LEDC_TIMER_0; c.ledc_channel = LEDC_CHANNEL_0;
  c.pixel_format = PIXFORMAT_RGB565; c.frame_size = rozm;
  c.jpeg_quality = 12; c.fb_count = 1; c.fb_location = CAMERA_FB_IN_PSRAM; c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t e = esp_camera_init(&c);
  if (e != ESP_OK) { Serial.printf("Kamera: blad init 0x%x\n", e); return false; }
  sensor_t *s = esp_camera_sensor_get();
  if (s) { s->set_whitebal(s, 1); s->set_exposure_ctrl(s, 1); s->set_gain_ctrl(s, 1); s->set_vflip(s, FOTO_ODWROC); s->set_hmirror(s, FOTO_LUSTRO); }
  for (int i = 0; i < 5; i++) { camera_fb_t *fb = esp_camera_fb_get(); if (fb) esp_camera_fb_return(fb); delay(100); pies(); }  // ustalenie ekspozycji
  return true;
}

static void kamera_stop() {
  esp_camera_deinit();
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, HIGH);
  digitalWrite(PIN_CAM_EN, LOW);
}

// zdjecie -> JPEG (bufor zwalnia wywolujacy: free())
static bool zdjecie_rozm(framesize_t rozm, uint8_t **jpg, size_t *jpg_len) {
  if (!kamera_start(rozm)) { kamera_stop(); return false; }
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { Serial.println("Kamera: brak klatki"); kamera_stop(); return false; }
  pies();
  bool ok = frame2jpg(fb, FOTO_JAKOSC, jpg, jpg_len);
  Serial.printf("Kamera: %dx%d -> JPEG %u B\n", fb->width, fb->height, ok ? (unsigned)*jpg_len : 0);
  esp_camera_fb_return(fb);
  kamera_stop();
  return ok;
}

static bool zdjecie(uint8_t **jpg, size_t *jpg_len) {
  setCpuFrequencyMhz(240);                                // zdjecie i kompresja JPEG na pelnym zegarze
  bool ok = zdjecie_rozm(FOTO_ROZM, jpg, jpg_len);
  if (!ok) {
    Serial.println("Kamera: duzy rozmiar nieudany, probuje mniejszy");
    delay(200); pies();
    ok = zdjecie_rozm(FOTO_ROZM_ZAPAS, jpg, jpg_len);
  }
  setCpuFrequencyMhz(CPU_MHZ_PRACA);
  return ok;
}

// ---------------------------------------------------------------- pozycja APRS (publicznie) albo status "brak GPS"
// "/GGMMSShDDMM.mmN/DDDMM.mmEOkkk/ppp/A=ssssss T433 x.xxV sat n img n" - czas fixu UTC, kurs, predkosc w wezlach, wysokosc w stopach
static void pozycja_aprs(float v) {
  char t[120];
  int n;
  if (fx.ok && fx.alt < POZYCJA_MIN_WYS_M) {               // v0.6: nisko - bez wspolrzednych
    char lok[5]; lokator4(fx.lat, fx.lon, lok);
    n = snprintf(t, sizeof(t), ">T433 %.2fV alt %.0fm sat %u img %u loc %s", v, fx.alt, fx.sat, nr_zdjecia, lok);
  } else if (fx.ok) {
    long la = lround(fabs(fx.lat) * 6000.0), lo = lround(fabs(fx.lon) * 6000.0);     // setne czesci minuty
    long stopy = lround(fx.alt * 3.28084f); if (stopy < 0) stopy = 0; if (stopy > 999999) stopy = 999999;
    int kurs = (int)lround(fx.kurs) % 360; if (kurs == 0) kurs = 360;
    int wez = (int)lround(fx.wezly); if (wez > 999) wez = 999;
    n = snprintf(t, sizeof(t), "/%02u%02u%02uh%02ld%02ld.%02ld%c%c%03ld%02ld.%02ld%c%c%03d/%03d/A=%06ld T433 %.2fV sat %u img %u",
                 fx.h, fx.m, fx.s, la / 6000, (la % 6000) / 100, la % 100, fx.lat >= 0 ? 'N' : 'S', APRS_TABELA,
                 lo / 6000, (lo % 6000) / 100, lo % 100, fx.lon >= 0 ? 'E' : 'W', APRS_SYMBOL, kurs, wez, stopy, v, fx.sat, nr_zdjecia);
  } else if (wznowienie) {
    n = snprintf(t, sizeof(t), ">T433 %.2fV wznowienie img %u nr %u od pakietu %u", v, nr_zdjecia, st.wznowien, st.nastepny);
  } else {
    n = snprintf(t, sizeof(t), ">T433 %.2fV brak GPS img %u", v, nr_zdjecia);
  }
  Serial.printf("APRS: %s\n", t);
  wyslij_aprs(t, n);
}

// ---------------------------------------------------------------- ramka prywatna z pozycja
static void pozycja_pryw(float v) {
#if PRYW_WLACZ
  if (!fx.ok || !lora_pryw()) return;
  char t[120];
  int n = snprintf(t, sizeof(t), "%s-%d T433 %04d%02d%02d%02d%02d%02d %.5f %.5f %.0f %.2f %u",
                   ZNAK, SSID, gps.date.year(), gps.date.month(), gps.date.day(), gps.time.hour(), gps.time.minute(), gps.time.second(),
                   gps.location.lat(), gps.location.lng(), gps.altitude.meters(), v, (unsigned)gps.satellites.value());
  int16_t st = radio.transmit((uint8_t *)t, n);
  Serial.printf("Pryw: %s (%d)\n", t, st);
  lora_aprs();
#endif
}

// ---------------------------------------------------------------- czekanie na slonce (v0.5)
// true = mozna nadawac dalej; false = za dlugo ciemno (zdjecie zostaje we flashu do wznowienia)
static bool czekaj_na_slonce() {
  if (vsc() >= VSC_CZEKAJ) return true;
  Serial.println("VSC niskie - czekam na slonce");
  Serial.flush();
  radio.sleep();
  uint32_t t0 = millis(); bool ok = false;
  while (millis() - t0 < CZEKANIE_MAX_S * 1000UL) {
    esp_sleep_enable_timer_wakeup(2000000ULL);
    esp_light_sleep_start();
    pies();
    if (vsc() >= VSC_DALEJ) { ok = true; break; }
  }
  radio.standby();
  if (ok && millis() - t0 > 20000UL) {            // kwarc ostygl - dwie ramki rozgrzewki
    for (int i = 0; i < 2; i++) { pozycja_aprs(vsc()); pies(); delay(ROZGRZEWKA_PRZERWA_MS); }
  }
  return ok;
}

// ---------------------------------------------------------------- SSDV przez APRS
// od_pakietu > 0: wznowienie - koder przechodzi zdjecie od poczatku, ale pakiety o numerach < od_pakietu nie sa nadawane
// zwraca true, gdy zdjecie wyslane do konca
static bool wyslij_ssdv(const uint8_t *jpg, size_t len, uint16_t od_pakietu) {
  ssdv_t s;
  static uint8_t pkt[SSDV_PKT_SIZE];
  static uint8_t b91[BASE91LEN(174) + 4];
  ssdv_enc_init(&s, SSDV_TYPE_PADDING, (char *)SSDV_ZNAK, nr_zdjecia, SSDV_JAKOSC);
  ssdv_enc_set_buffer(&s, pkt);
  size_t bi = 0; int pid = 0, nadane = 0; char c;
  while (true) {
    pies();
    while ((c = ssdv_enc_get_packet(&s)) == SSDV_FEED_ME) {
      size_t r = (len - bi) < 128 ? (len - bi) : 128;
      if (r == 0) { Serial.println("SSDV: koniec pliku przed EOI"); return true; }
      ssdv_enc_feed(&s, jpg + bi, r); bi += r;
    }
    if (c == SSDV_EOI) break;
    if (c != SSDV_OK) { Serial.printf("SSDV: blad %d\n", c); return true; }
    if (pid < od_pakietu) { pid++; continue; }             // wznowienie: te pakiety juz poszly
    if (!czekaj_na_slonce()) { Serial.println("SSDV: brak slonca, zdjecie zostaje do wznowienia"); return false; }
    // jak Pecan Pico: bez bajtu synchronizacji, typu i znaku (znak jest w naglowku APRS), bez CRC i FEC
    memset(b91, 0, sizeof(b91));
    base91_encode(&pkt[6], b91, 174);
    static char tresc[300];
    int n = snprintf(tresc, sizeof(tresc), "{{I%s", (char *)b91);
    wyslij_aprs(tresc, n);
    pid++; nadane++;
    st.nastepny = pid; stan_zapisz();                      // postep do flasha po kazdym pakiecie
    if (nadane % POZYCJA_CO_PAKIETOW == 0) { delay(PRZERWA_PAKIET_MS); pozycja_aprs(vsc()); }
    if (pid >= MAX_PAKIETOW) { Serial.println("SSDV: limit pakietow, przerywam"); break; }
    if (vsc() < VSC_MIN_NADAJ) { Serial.println("SSDV: za niskie VSC, zdjecie zostaje do wznowienia"); return false; }
    delay(PRZERWA_PAKIET_MS);
  }
  Serial.printf("SSDV: zdjecie %u wyslane, pakietow %d (nadanych teraz %d)\n", nr_zdjecia, pid, nadane);
  return true;
}

// ---------------------------------------------------------------- cykl
static void cykl() {
  float v = vsc();
  Serial.printf("Cykl %lu, VSC %.2f V\n", (unsigned long)nr_cyklu, v);
  if (v < VSC_MIN_NADAJ) return;

  // v0.5: niedokonczone zdjecie we flashu -> dosylamy reszte zamiast robic nowe
  if (stan_wczytaj() && st.wznowien < WZNOWIEN_MAX) {
    wznowienie = true; fx.ok = false; stan_aktywny = true;
    nr_zdjecia = st.img; st.wznowien++;
    uint16_t od = st.nastepny > 0 ? st.nastepny - 1 : 0;     // pakiet nadawany w chwili zaniku raczej nie doszedl
    stan_zapisz();
    Serial.printf("WZNOWIENIE zdjecia %u (%u B) od pakietu %u, wznowienie nr %u\n", st.img, (unsigned)st.dl, od, st.wznowien);
    uint8_t *jpg = zdj_wczytaj(st.dl);
    if (jpg) {
      for (int i = 0; i < ROZGRZEWKA_RAMEK; i++) { pozycja_aprs(vsc()); pies(); delay(ROZGRZEWKA_PRZERWA_MS); }
      bool koniec = wyslij_ssdv(jpg, st.dl, od);
      free(jpg);
      if (koniec) { stan_usun(); po_wznowieniu = true; }
      return;
    }
    Serial.println("WZNOWIENIE: nie moge wczytac zdjecia - robie nowe");
  }
  stan_usun(); wznowienie = false; stan_aktywny = false;

  gps_wlacz(true);
  fx.ok = gps_fix(GPS_FIX_TIMEOUT_S);
  if (fx.ok) {
    fx.lat = gps.location.lat(); fx.lon = gps.location.lng(); fx.alt = gps.altitude.meters();
    fx.kurs = gps.course.isValid() ? gps.course.deg() : 0; fx.wezly = gps.speed.isValid() ? gps.speed.knots() : 0;
    fx.h = gps.time.hour(); fx.m = gps.time.minute(); fx.s = gps.time.second(); fx.sat = gps.satellites.value();
    nr_zdjecia = fx.h * 10 + fx.m / 6;                    // 0..239, niepowtarzalny w ciagu doby
  } else {
    nr_zdjecia = 240 + licznik_bez_fixu_nastepny();
  }
  Serial.printf("GPS: fix %d sat %u\n", fx.ok, (unsigned)gps.satellites.value());
  gps_wlacz(false);             // GPS wylaczony na czas nadawania i zdjecia (prad)
  delay(300); pies();

  for (int i = 0; i < ROZGRZEWKA_RAMEK; i++) {      // rozgrzewka kwarcu: pierwsze ramki po zimnym starcie sa stracone
    pozycja_aprs(vsc()); pies();
    delay(ROZGRZEWKA_PRZERWA_MS);
  }
  if (fx.ok) pozycja_pryw(v);

  if (vsc() >= VSC_MIN_FOTO) {
    uint8_t *jpg = nullptr; size_t jl = 0;
    if (zdjecie(&jpg, &jl)) {
      st.magia = STAN_MAGIA; st.img = nr_zdjecia; st.wznowien = 0; st.nastepny = 0; st.dl = jl;
      if (zdj_zapisz(jpg, jl)) { stan_aktywny = true; stan_zapisz(); }   // od teraz zdjecie da sie wznowic po restarcie
      if (wyslij_ssdv(jpg, jl, 0)) stan_usun();
      free(jpg);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  pinMode(PIN_CAM_EN, OUTPUT); digitalWrite(PIN_CAM_EN, LOW);
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, HIGH);
  pinMode(PIN_GPS_EN_N, OUTPUT); digitalWrite(PIN_GPS_EN_N, HIGH);
  analogReadResolution(12);
  Serial.printf("T433 lite v0.6 %s-%d start, PSRAM %u B\n", ZNAK, SSID, (unsigned)ESP.getPsramSize());
  esp_task_wdt_config_t wc = {};
  wc.timeout_ms = WATCHDOG_S * 1000UL; wc.idle_core_mask = 0; wc.trigger_panic = true;
  if (esp_task_wdt_reconfigure(&wc) != ESP_OK) esp_task_wdt_init(&wc);
  esp_task_wdt_add(NULL);
  setCpuFrequencyMhz(CPU_MHZ_PRACA);
  fs_ok = LittleFS.begin(true);                            // pierwsze uruchomienie: formatowanie (kilkanascie sekund)
  if (!fs_ok) Serial.println("LittleFS: blad - bez wznawiania zdjec");
  pies();
  nr_cyklu++;
  cykl();
  if (radio_ok) radio.sleep();
  float v = vsc();
  uint32_t sen = (v > VSC_BEZ_SNU || po_wznowieniu) ? 3 : CYKL_S;          // wysokie napiecie: nie usypiaj na dlugo (Zener D2)
  Serial.printf("VSC %.2f V, uspienie na %lu s\n", v, (unsigned long)sen);
  Serial.flush();
  esp_task_wdt_delete(NULL);
  esp_sleep_enable_timer_wakeup((uint64_t)sen * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}
