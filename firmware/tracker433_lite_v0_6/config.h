// T433 - tracker 433 MHz z kamera, konfiguracja
// Plytka T433 lite v1.0 (ESP32-S3-MINI-1U-N4R2, E22-400MM22S / SX1268, ATGM336H, OV2640) - program v0.6 (21.11.2026)
#pragma once

// ---------- znak i APRS ----------
#define ZNAK            "N0CALL"      // znak obowiazkowy (pasmo amatorskie 70 cm)
#define SSID            11
#define APRS_DEST       "APZ433"      // APZxxx = oprogramowanie eksperymentalne
#define APRS_PATH       ""            // bez WIDE1-1 - balon slyszy wiele bramek naraz, nie zasmiecamy sieci
#define APRS_TABELA     '/'           // symbol APRS: tabela podstawowa
#define APRS_SYMBOL     'O'           // "O" = balon
// v0.6: ponizej tej wysokosci (m n.p.m.) BEZ wspolrzednych w eterze - tylko status z wysokoscia i duzym kwadratem lokatora
// (4 znaki, ok. 70 x 110 km), zeby testy przy domu i sam start nie pokazywaly dokladnego miejsca na aprs.fi.
// 0 = pozycja publicznie zawsze. Zasada autora: bez dokladnego GPS domu / miejsca startu w sieci.
#define POZYCJA_MIN_WYS_M  1000
#define SSDV_ZNAK       "N0CALL"      // znak w naglowku SSDV (max 6 znakow)

// ---------- LoRa APRS (publicznie, EU: 433,775 MHz SF12 BW125 CR4/5) ----------
#define APRS_FREQ       433.775
#define APRS_SF         12
#define APRS_BW         125.0
#define APRS_CR         5
#define LORA_MOC_DBM    17            // 50 mW; E22 max 22 dBm (wiecej pradu z paneli)
#define LORA_TCXO_V     0             // 19.11.2026: E22-400MM22S ma KWARC (begin z TCXO 1,8 V dawal blad -707); 0 = kwarc
#define LORA_SYNC       0x12          // LoRa APRS uzywa "private" sync word 0x12

// ---------- ramka prywatna z dokladna pozycja (tylko nasze odbiorniki) ----------
// v0.3: pozycja idzie publicznie zwykla ramka APRS (decyzja autora 21.11.2026), ramka prywatna wylaczona
#define PRYW_WLACZ      0
#define PRYW_FREQ       434.500       // do ustalenia z planem pasma
#define PRYW_SF         10
#define PRYW_BW         125.0
#define PRYW_CR         5

// ---------- harmonogram ----------
#define CYKL_S              600       // uspienie po cyklu (pozycja + zdjecie), sekundy
#define GPS_FIX_TIMEOUT_S   180       // max czekanie na fix GPS w cyklu
#define PRZERWA_PAKIET_MS   800       // przerwa miedzy pakietami zdjecia (v0.6: bylo 1500)
// Rozgrzewka (v0.4): po zimnym starcie kwarc modulu E22 plynie ok. 40 Hz/s i przez pierwsze ok. 12 s nadawania ramki SF12
// maja blad CRC (poczatek dobry, dalej przeklamania - 19.11 i 21.11). Dlatego ramka pozycji/statusu idzie na poczatku
// kilka razy pod rzad: pierwsze sa stracone, kolejne juz dobre, a zdjecie zaczyna sie na rozgrzanym kwarcu.
#define ROZGRZEWKA_RAMEK    5         // ile razy ramka pozycji/statusu na poczatku cyklu (ok. 3 s nadawania kazda)
#define ROZGRZEWKA_PRZERWA_MS 300
#define POZYCJA_CO_PAKIETOW 20        // powtorzenie ramki pozycji (z czasem fixu) co tyle pakietow zdjecia
#define MAX_PAKIETOW        400       // bezpiecznik: najwiecej pakietow jednego zdjecia
#define WATCHDOG_S          120       // brak postepu przez tyle sekund = restart

// ---------- kamera / zdjecie ----------
#define FOTO_ROZM       FRAMESIZE_VGA    // v0.3: 640x480 (SSDV: wymiary wielokrotnoscia 16)
#define FOTO_ROZM_ZAPAS FRAMESIZE_QVGA   // gdy kamera nie da klatki 640x480 - 320x240
#define FOTO_JAKOSC     60               // jakosc JPEG z kamery 0-100 (o wielkosci decyduje SSDV_JAKOSC ponizej)
#define FOTO_ODWROC      0                // v0.6: 1 = obraz do gory nogami (kamera zamontowana odwrotnie)
#define FOTO_LUSTRO      0                //       1 = odbicie lustrzane
#define CPU_MHZ_PRACA    80               // v0.6: zegar procesora poza robieniem zdjecia (mniej pradu przy GPS i nadawaniu); zdjecie na 240 MHz
#define SSDV_JAKOSC     3                // jakosc SSDV 0-7 (przekodowanie w SSDV). Pomiar 21.11 na probkach 640x480:
                                         //   niebo z chmurami: 2 -> ok. 45 pakietow, 3 -> ok. 60; ciemny pokoj: 2 -> ok. 80, 3 -> ok. 115 (10 s na pakiet)

// ---------- zasilanie ----------
#define VSC_MIN_FOTO    3.60             // ponizej: bez zdjecia (tylko status + pozycja)
#define VSC_MIN_NADAJ   3.30             // ponizej: nic nie nadawaj, uspij
#define VSC_CZEKAJ      3.45             // v0.5: ponizej - wstrzymaj nadawanie zdjecia i czekaj na slonce (lekkie uspienie)
#define VSC_DALEJ       3.60             //       powyzej - nadawaj dalej
#define CZEKANIE_MAX_S  300              //       tyle czekania bez poprawy = uspienie; zdjecie zostaje do wznowienia
#define WZNOWIEN_MAX    8                // v0.5: po tylu wznowieniach jednego zdjecia - porzuc je i zrob nowe
#define VSC_BEZ_SNU     4.90             // powyzej: nie usypiaj (Zener 5,1 V D2 grzalby sie w uspieniu) - od razu nastepny cykl
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
