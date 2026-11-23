// T433 RX v0.1 (19.11.2026) - ODBIORNIK na plytce T433 lite v1.0 (ESP32-S3-MINI-1U + E22-400MM22S / SX1268)
//
// Druga plytka T433 jako odbiornik do testow trackera (tracker433_lite_v0_2):
//   - slucha LoRa APRS 433,775 MHz (SF12 BW125 CR4/5, sync 0x12) - te same ustawienia co tracker (config.h),
//   - kazda odebrana ramke wypisuje po USB w jednej linii (do skryptu t433_usb_odbior.py):
//       T433RX;<ms>;<A|P>;<rssi dBm>;<snr dB>;<blad czestotliwosci Hz>;<dlugosc>;<crc 1|0>;<ramka szesnastkowo>
//     a pod nia czytelna kopie tekstowa zaczynajaca sie od "# ",
//   - NIC NIE NADAJE (brak wywolan transmit), kamera i GPS wylaczone.
//
// Polecenia po USB (jeden znak): a = tryb APRS 433,775 (domyslny), p = tryb ramki prywatnej (PRYW_FREQ, SF10),
//                                ? = stan.
// Arduino: plytka "ESP32S3 Dev Module", Flash 4MB, USB CDC On Boot: Enabled. RadioLib 7.1.2.

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include "config.h"

#define RX_WERSJA "T433RX v0.1"

static SPIClass spiLora(FSPI);
static SX1268 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_NRST, PIN_LORA_BUSY, spiLora);

static volatile bool jest_ramka = false;
static bool radio_ok = false;
static bool tcxo = true;
static char tryb = 'A';
static uint32_t licznik = 0, bledy_crc = 0, ost_zycie = 0;

static void ARDUINO_ISR_ATTR przerwanie() { jest_ramka = true; }

static bool ustaw_tryb(char t) {
  int16_t st = RADIOLIB_ERR_NONE;
  radio.standby();
  if (t == 'P') {
    st |= radio.setFrequency(PRYW_FREQ); st |= radio.setSpreadingFactor(PRYW_SF);
    st |= radio.setBandwidth(PRYW_BW);   st |= radio.setCodingRate(PRYW_CR);
  } else {
    st |= radio.setFrequency(APRS_FREQ); st |= radio.setSpreadingFactor(APRS_SF);
    st |= radio.setBandwidth(APRS_BW);   st |= radio.setCodingRate(APRS_CR);
  }
  tryb = t;
  jest_ramka = false;
  int16_t sr = radio.startReceive();
  Serial.printf("T433RX;INFO;tryb %c %.3f MHz, ustawienie %d, odbior %d\n", tryb, t == 'P' ? (double)PRYW_FREQ : (double)APRS_FREQ, st, sr);
  return st == RADIOLIB_ERR_NONE && sr == RADIOLIB_ERR_NONE;
}

static bool radio_start() {
  spiLora.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int16_t st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, 0, 8, LORA_TCXO_V, false);
  if (st != RADIOLIB_ERR_NONE && LORA_TCXO_V > 0) {
    Serial.printf("T433RX;INFO;begin z TCXO blad %d, probuje bez TCXO\n", st);
    tcxo = false;
    st = radio.begin(APRS_FREQ, APRS_BW, APRS_SF, APRS_CR, LORA_SYNC, 0, 8, 0, false);
  }
  if (st != RADIOLIB_ERR_NONE) { Serial.printf("T433RX;BLAD;LoRa begin %d\n", st); return false; }
  radio.setDio2AsRfSwitch(true);                         // DIO2 -> TXEN modulu E22 (nieuzywane, nie nadajemy)
  radio.setRfSwitchPins(PIN_LORA_RXEN, RADIOLIB_NC);     // RXEN z GPIO7
  radio.setCRC(true);
  radio.setRxBoostedGainMode(true);                      // wieksza czulosc odbioru
  radio.setPacketReceivedAction(przerwanie);
  return ustaw_tryb('A');
}

static void stan() {
  Serial.printf("T433RX;STAN;%s;radio %d;tcxo %d;tryb %c;ramek %lu;bledow_crc %lu;czas %lu s\n",
                RX_WERSJA, radio_ok, tcxo, tryb, (unsigned long)licznik, (unsigned long)bledy_crc, (unsigned long)(millis() / 1000));
}

static void odbierz() {
  static uint8_t buf[256];
  size_t dl = radio.getPacketLength();
  if (dl > 255) dl = 255;
  int16_t st = radio.readData(buf, dl);
  float rssi = radio.getRSSI(), snr = radio.getSNR(), fe = radio.getFrequencyError();
  bool crc_ok = (st == RADIOLIB_ERR_NONE);
  if (st != RADIOLIB_ERR_NONE && st != RADIOLIB_ERR_CRC_MISMATCH) {
    Serial.printf("T433RX;BLAD;readData %d\n", st);
  } else {
    if (crc_ok) licznik++; else bledy_crc++;
    Serial.printf("T433RX;%lu;%c;%.1f;%.1f;%.0f;%u;%d;", (unsigned long)millis(), tryb, rssi, snr, fe, (unsigned)dl, crc_ok ? 1 : 0);
    for (size_t i = 0; i < dl; i++) Serial.printf("%02X", buf[i]);
    Serial.println();
    // czytelna kopia: w trybie APRS bez 3 bajtow naglowka LoRa APRS ("<\xff\x01")
    size_t od = (dl >= 3 && buf[0] == '<' && buf[1] == 0xFF && buf[2] == 0x01) ? 3 : 0;
    Serial.print("# ");
    for (size_t i = od; i < dl && i < od + 90; i++) Serial.write(buf[i] >= 32 && buf[i] < 127 ? buf[i] : '.');
    if (dl > od + 90) Serial.print("...");
    Serial.println();
  }
  jest_ramka = false;
  radio.startReceive();
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  pinMode(PIN_CAM_EN, OUTPUT); digitalWrite(PIN_CAM_EN, LOW);      // kamera wylaczona
  pinMode(CAM_PWDN, OUTPUT); digitalWrite(CAM_PWDN, HIGH);
  pinMode(PIN_GPS_EN_N, OUTPUT); digitalWrite(PIN_GPS_EN_N, HIGH); // GPS wylaczony
  Serial.printf("T433RX;INFO;%s start (odbiornik, nic nie nadaje)\n", RX_WERSJA);
  radio_ok = radio_start();
  stan();
}

void loop() {
  if (!radio_ok) {                       // ponawiaj co 5 s, zeby blad byl widoczny takze po pozniejszym otwarciu portu
    delay(5000);
    radio_ok = radio_start();
    stan();
    return;
  }
  if (jest_ramka) odbierz();
  while (Serial.available()) {
    int c = Serial.read();
    if (c == 'a' || c == 'A') ustaw_tryb('A');
    else if (c == 'p' || c == 'P') ustaw_tryb('P');
    else if (c == '?') stan();
  }
  if (millis() - ost_zycie > 30000) { ost_zycie = millis(); stan(); }
  delay(5);
}
