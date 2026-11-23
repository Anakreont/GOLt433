# -*- coding: utf-8 -*-
"""Tracker 433 MHz z kamera - wersja LITE (8.11.2026).
Tansza: modul ESP32-S3-MINI-1U (zamiast ukladu + kwarcu), LDO 3,3 V (zamiast buck-boost),
2 warstwy, wszystkie elementy na gorze (JLCPCB Economic PCBA), 32 x 39 mm.
Kazdy element: ref, (biblioteka, footprint), wartosc, LCSC, x, y [mm od lewego gornego rogu], obrot, {pad: siec}
"""
STD = "/usr/share/kicad/footprints/"
LOC = "/home/claude/t433lite/lib/t433.pretty"

R0402 = (STD + "Resistor_SMD.pretty", "R_0402_1005Metric")
C0402 = (STD + "Capacitor_SMD.pretty", "C_0402_1005Metric")
C0603 = (STD + "Capacitor_SMD.pretty", "C_0603_1608Metric")
SOD123 = (STD + "Diode_SMD.pretty", "D_SOD-123")
TP15 = (STD + "TestPoint.pretty", "TestPoint_Pad_1.5x1.5mm")
TP20x = (STD + "TestPoint.pretty", "TestPoint_Pad_2.0x2.0mm")
L = lambda n: (LOC, n)

W, H = 32.0, 40.6
DX = 0.0
BOTTOM = {"TP24", "TP25"}          # na spodzie tylko gole pola superkondensatora (bez montazu)

# ---- ESP32-S3-MINI-1U: numer pinu modulu -> siec (piny: 1-15 lewa, 16-30 dol, 31-45 prawa, 46-60 gora) ----
ESP = {1: "GND", 2: "GND", 3: "+3V3",
       4: "BOOT",          # IO0
       5: None,            # IO1 wolny
       6: None,            # IO2 wolny
       7: "LORA_NSS",      # IO3 (strap JTAG - nieaktywny bez efuse)
       8: "LORA_MOSI",     # IO4
       9: "LORA_MISO",     # IO5
       10: "LORA_BUSY",    # IO6
       11: "LORA_RXEN",    # IO7
       12: "LORA_NRST",    # IO8
       13: "VSC_ADC",      # IO9 (ADC1_CH8)
       14: "CAM_EN",       # IO10 - stan wysoki = LDO kamery (2,8 V i 1,2 V) wlaczone
       15: "LORA_DIO1",    # IO11
       16: "CAM_SIOD",     # IO12
       17: "CAM_SIOC",     # IO13
       18: "CAM_VSYNC",    # IO14
       19: "CAM_PWDN",     # IO15
       20: "CAM_HREF",     # IO16
       21: "CAM_Y9",       # IO17
       22: "CAM_XCLK",     # IO18
       23: "USB_DN", 24: "USB_DP",   # IO19, IO20
       25: "CAM_Y8",       # IO21
       26: None,           # IO26 - PSRAM w module N4R2, nie uzywac
       27: "CAM_Y7",       # IO47
       28: "CAM_PCLK",     # IO33
       29: "CAM_Y6",       # IO34
       30: "CAM_Y2",       # IO48
       31: "CAM_Y5",       # IO35
       32: "CAM_Y3",       # IO36
       33: "CAM_Y4",       # IO37
       34: None,           # IO38 wolny
       35: "GPS_EN_N",     # IO39 - stan niski = GPS wlaczony
       36: "LORA_SCK",     # IO40
       37: "GPS_TXD",      # IO41 <- TXD GPS
       38: "GPS_RXD",      # IO42 -> RXD GPS
       39: None, 40: None,  # TXD0/RXD0 (log)
       41: None,           # IO45 (strap VDD_SPI) - celowo wolny
       42: "GND", 43: "GND",
       44: None,           # IO46 (strap) wolny
       45: "CHIP_PU",
       }
for _n in range(46, 66): ESP[_n] = "GND"

# ---- E22-400MM22S (SX1268, 10 x 10 mm) ----
E22 = {1: "+3V3", 2: "GND", 3: "LORA_NRST", 4: None, 5: None, 6: "LORA_ANT", 7: "GND", 8: None,
       9: "LORA_DIO2", 10: "LORA_RXEN", 11: "LORA_BUSY", 12: "LORA_MISO", 13: "LORA_MOSI",
       14: "LORA_NSS", 15: "LORA_SCK", 16: "GND", 17: None, 18: None, 19: "LORA_DIO2", 20: "LORA_DIO1"}

# ---- ATGM336H-5N31 ----
GPS = {1: "GND", 2: "GPS_TXD", 3: "GPS_RXD", 4: None, 5: "GPS_VCC", 6: "+3V3", 7: None, 8: "GPS_VCC",
       9: None, 10: "GND", 11: "GPS_ANT", 12: "GND", 13: None, 14: None, 15: None, 16: None, 17: None, 18: None}

# ---- zlacze kamery OV2640 24 pin (8 PWDN teraz z GPIO, 6 RESET do 3,3 V) ----
CAM = {1: None, 2: "GND", 3: "CAM_SIOD", 4: "CAM_2V8", 5: "CAM_SIOC", 6: "+3V3", 7: "CAM_VSYNC",
       8: "CAM_PWDN", 9: "CAM_HREF", 10: "CAM_1V2", 11: "+3V3", 12: "CAM_Y9", 13: "CAM_XCLK", 14: "CAM_Y8",
       15: "GND", 16: "CAM_Y7", 17: "CAM_PCLK", 18: "CAM_Y6", 19: "CAM_Y2", 20: "CAM_Y5", 21: "CAM_Y3",
       22: "CAM_Y4", 23: None, 24: None, 25: "GND", 26: "GND"}

PARTS = [
    ("U1", L("ESP32-S3-MINI-1U"), "ESP32-S3-MINI-1U-N4R2", "C22356044", 16.0, 24.6, 0, ESP),
    ("U2", L("E22-400MM22S"), "E22-400MM22S", "C5333984", 8.0, 8.6, 270, E22),
    ("U3", L("ATGM336H"), "ATGM336H-5N31", "C90770", 24.4, 8.6, 180, GPS),
    ("J1", L("FPC24_AFC01-S24FCA"), "AFC01-S24FCA-00 (OV2640)", "C262669", 16.0, 36.2, 0, CAM),
    ("U4", L("ME6211_SOT23-5"), "ME6211C33M5G-N (3,3V)", "C82942", 16.3, 7.6, 0,
        {1: "VSC", 2: "GND", 3: "VSC", 4: None, 5: "+3V3"}),
    ("U6", L("ME6211_SOT23-5"), "ME6211C28M5G (AVDD 2,8V)", "C53099", 2.2, 37.2, 90,
        {1: "+3V3", 2: "GND", 3: "CAM_EN", 4: None, 5: "CAM_2V8"}),
    ("U7", L("ME6211_SOT23-5b"), "ME6211C12M5G (DVDD 1,2V)", "C236672", 5.7, 37.2, 0,
        {1: "+3V3", 2: "GND", 3: "CAM_EN", 4: None, 5: "CAM_1V2"}),
    ("Q2", L("SI2301_SOT23"), "SI2301CDS (zas. GPS)", "C10487", 27.0, 22.6, 0, {1: "GPS_EN_N", 2: "+3V3", 3: "GPS_VCC"}),
    ("D2", SOD123, "BZT52C5V1 (ogr. 5,1 V)", "C173407", 18.2, 3.4, 90, {1: "VSC", 2: "GND"}),
]

PAS = [
    # zasilanie
    ("C30", C0603, "10uF", "C19702", 17.6, 10.9, 90, "VSC", "GND"),        # wejscie LDO
    ("C31", C0603, "10uF", "C19702", 15.0, 10.9, 90, "+3V3", "GND"),       # wyjscie LDO
    # ESP32 modul
    ("C1", C0603, "10uF", "C19702", 5.4, 20.0, 90, "+3V3", "GND"),
    ("C2", C0402, "100nF", "C1525", 6.8, 19.0, 90, "+3V3", "GND"),
    ("R1", R0402, "10k", "C25744", 25.4, 17.4, 0, "CHIP_PU", "+3V3"),
    ("C8", C0402, "1uF", "C52923", 25.4, 19.2, 0, "CHIP_PU", "GND"),
    # pomiar napiecia superkondensatora
    ("R3", R0402, "1M", "C26083", 7.0, 27.2, 90, "VSC", "VSC_ADC"),
    ("R4", R0402, "1M", "C26083", 7.0, 29.2, 90, "VSC_ADC", "GND"),
    ("C11", C0402, "100nF", "C1525", 5.8, 29.2, 90, "VSC_ADC", "GND"),
    # LoRa
    ("C25", C0603, "10uF", "C19702", 14.6, 4.2, 0, "+3V3", "GND"),
    ("C26", C0402, "100nF", "C1525", 14.6, 2.6, 0, "+3V3", "GND"),
    # GPS
    ("R16", R0402, "100k", "C25741", 27.0, 20.4, 0, "GPS_EN_N", "+3V3"),
    ("C22", C0402, "1uF", "C52923", 27.0, 25.2, 0, "GPS_VCC", "GND"),
    ("C23", C0402, "100nF", "C1525", 27.0, 26.3, 0, "GPS_VCC", "GND"),
    # kamera
    ("C17", C0402, "1uF", "C52923", 1.8, 34.2, 0, "CAM_2V8", "GND"),
    ("C18", C0402, "1uF", "C52923", 4.0, 34.2, 0, "+3V3", "GND"),
    ("C19", C0402, "1uF", "C52923", 6.2, 34.2, 0, "CAM_1V2", "GND"),
    ("R10", R0402, "100k", "C25741", 7.2, 31.6, 0, "CAM_EN", "GND"),     # kamera wylaczona po resecie
    ("R12", R0402, "4.7k", "C25900", 4.6, 31.2, 90, "CAM_SIOD", "+3V3"),
    ("R13", R0402, "4.7k", "C25900", 3.4, 31.2, 90, "CAM_SIOC", "+3V3"),
]

PADS = [
    ("TP23", TP15, "GND", 28.6, 38.2, "433 GND"),
    ("TP24", TP20x, "VSC", 4.0, 6.0, "SC+"),       # spod
    ("TP25", TP20x, "GND", 28.0, 6.0, "SC-"),      # spod
]
HOLES = [(1.2, 1.4), (W - 1.2, 1.4)]      # NPTH 1,0 mm na nitke
PV_HOLES = [("TP1", "VSC", 0.95, 18.5, "+"), ("TP2", "GND", 0.95, 22.5, "-"),
            ("TP3", "VSC", W - 0.95, 18.5, "+"), ("TP4", "GND", W - 0.95, 22.5, "-")]
PV_DRILL, PV_PAD = 0.6, 1.3
ANT_HOLES = [("TP22", "LORA_ANT", 3.4, 1.3, "433"), ("TP20", "GPS_ANT", 27.7, 1.3, "GPS")]
RF_NETS = ("LORA_ANT", "GPS_ANT")
TAB = dict(x0=-7.5, x1=-1.0, y0=24.6, y1=34.2)
BRIDGE = dict(y0=25.4, y1=33.4)
MOUSE = [25.9, 27.1, 28.3, 29.5, 30.7, 31.9, 33.1]
J2 = dict(x=-5.52, y=26.6, pins={1: ("BOOT", "B0"), 2: ("CHIP_PU", "EN"), 3: ("VSC", "V+"),
                                   4: ("USB_DP", "D+"), 5: ("USB_DN", "D-"), 6: ("GND", "G")})
WIRE_HOLE = (W / 2, 1.15, 0.6, 1.4)
NAPIS = "T433 lite v1.0"
