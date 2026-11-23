// T433 - tracker 433 MHz z kamera, konfiguracja
// Plytka T433 v2.3 (ESP32-S3FH4R2, E22-400MM22S / SX1268, ATGM336H, OV2640)
#pragma once

// ---------- znak i APRS ----------
#define ZNAK            "N0CALL"      // znak obowiazkowy (pasmo amatorskie 70 cm)
#define SSID            11
#define APRS_DEST       "APZ433"      // APZxxx = oprogramowanie eksperymentalne
#define APRS_PATH       ""            // bez WIDE1-1 - balon slyszy wiele bramek naraz, nie zasmiecamy sieci
#define SSDV_ZNAK       "N0CALL"      // znak w naglowku SSDV (max 6 znakow)

// ---------- LoRa APRS (publicznie, EU: 433,775 MHz SF12 BW125 CR4/5) ----------
#define APRS_FREQ       433.775
#define APRS_SF         12
#define APRS_BW         125.0
#define APRS_CR         5
#define LORA_MOC_DBM    17            // 50 mW; E22 max 22 dBm (wiecej pradu z paneli)
#define LORA_TCXO_V     1.8           // E22-400MM22S ma TCXO zasilane z DIO3 (1,8 V); 0 = kwarc
#define LORA_SYNC       0x12          // LoRa APRS uzywa "private" sync word 0x12

// ---------- ramka prywatna z dokladna pozycja (tylko nasze odbiorniki) ----------
#define PRYW_WLACZ      1
#define PRYW_FREQ       434.500       // do ustalenia z planem pasma
#define PRYW_SF         10
#define PRYW_BW         125.0
#define PRYW_CR         5

// ---------- harmonogram ----------
#define CYKL_S              600       // co ile sekund nowy cykl (status + pozycja + zdjecie)
#define GPS_FIX_TIMEOUT_S   180       // max czekanie na fix GPS w cyklu
#define PRZERWA_PAKIET_MS   1500      // przerwa miedzy pakietami zdjecia
#define STATUS_CO_PAKIETOW  20        // status APRS (bez pozycji) co tyle pakietow zdjecia

// ---------- kamera / zdjecie ----------
#define FOTO_ROZM       FRAMESIZE_QVGA   // 320x240 (SSDV: wymiary wielokrotnoscia 16)
#define FOTO_JAKOSC     40               // jakosc JPEG 0-100 (mniej = mniej pakietow)
#define SSDV_JAKOSC     4                // jakosc SSDV 0-7 (przekodowanie w SSDV)
#define NAPIS_SKALA     2                // powiekszenie czcionki 5x7 na zdjeciu
#define NAPIS_DOL       1                // powtorz pasek z pozycja na dole zdjecia

// ---------- zasilanie ----------
#define VSC_MIN_FOTO    3.60             // ponizej: bez zdjecia (tylko status + pozycja)
#define VSC_MIN_NADAJ   3.30             // ponizej: nic nie nadawaj, uspij
#define VSC_DZIELNIK    2.0              // R3/R4 1M/1M

// ---------- piny (mapa GPIO plytki T433 lite v1.0, modul ESP32-S3-MINI-1U-N4R2) ----------
#define PIN_LORA_DIO1   11    // v1.0 po poprawce 9.11 (bylo IO1)
#define PIN_LORA_SCK    40    // v1.0 po poprawce 9.11 (bylo IO2)
#define PIN_LORA_NSS    3
#define PIN_LORA_MOSI   4
#define PIN_LORA_MISO   5
#define PIN_LORA_BUSY   6
#define PIN_LORA_RXEN   7
#define PIN_LORA_NRST   8
#define PIN_VSC_ADC     9     // ADC1_CH8, dzielnik 1M/1M
#define PIN_CAM_EN      10    // stan wysoki = LDO kamery 2,8 V i 1,2 V wlaczone (R10 100k do masy)
#define PIN_GPS_EN_N    39    // stan niski = GPS wlaczony (Q2 SI2301, R16 100k do 3,3 V)
#define PIN_GPS_RX      41    // ESP RX  <- TXD GPS
#define PIN_GPS_TX      42    // ESP TX  -> RXD GPS
#define CAM_SIOD        12
#define CAM_SIOC        13
#define CAM_VSYNC       14
#define CAM_PWDN        15
#define CAM_HREF        16
#define CAM_Y9          17
#define CAM_XCLK        18
#define CAM_Y8          21
#define CAM_Y7          47
#define CAM_PCLK        33
#define CAM_Y6          34
#define CAM_Y2          48
#define CAM_Y5          35
#define CAM_Y3          36
#define CAM_Y4          37
