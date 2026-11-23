# -*- coding: utf-8 -*-
"""T433 - odbior przez USB z drugiej plytki T433 (program tracker433_lite_rx_v0_1) - wersja 0.5 (21.11.2026)

Czyta z portu szeregowego linie "T433RX;..." z plytki-odbiornika, pokazuje kazda ramke (sila sygnalu, typ),
sklada zdjecia SSDV i zapisuje JPEG. Nic nie wysyla do internetu (APRS-IS, SondeHub).
0.5 (21.11.2026): kazde zdjecie w osobnym pliku T433USB_RRRRMMDD_GGMMSS_NNN.jpg - ten sam numer (np. 240 bez GPS) nie nadpisuje
poprzedniego; numer pakietu cofniety o wiecej niz 5 = nowe zdjecie (takze przy odtwarzaniu --plik).
0.4 (21.11.2026): tracker v0.5 dosyla reszte przerwanego zdjecia pod tym samym numerem - pakiety sa dokladane do juz odebranych.
0.3 (21.11.2026): pokazuje ramke pozycji APRS trackera v0.3; ten sam numer zdjecia po zakonczonym zdjeciu = nowe zdjecie.
0.2 (21.11.2026): te same linie przekazuje do Della w sieci domowej (POST ADRES/t433_usb, opcja --dell), zeby zdjecia
i ramki byly tez na stronie lokalnej "LoRa 433". Dell niedostepny = skrypt dziala dalej lokalnie, a linie czekaja w kolejce.

Uzycie:
  python3 t433_usb_odbior_v0_5.py /dev/ttyACM0            (Linux / Dell)
  python   t433_usb_odbior_v0_5.py COM5                    (Windows)
Opcje:
  --katalog KAT   gdzie zapisywac (domyslnie ./t433_usb): zdj/*.jpg, ramki.log, t433_usb.json
  --dek PLIK      dekoder SSDV (domyslnie: ssdv_dek / ssdv_dek.exe obok skryptu, potem /opt/balony-json/t433/ssdv/ssdv_dek)
  --pryw          przelacz odbiornik na ramke prywatna (PRYW_FREQ) zamiast APRS 433,775
  --dell ADRES    strona lokalna na Dellu (domyslnie wylaczone); --bez-della = nic nie przekazuj
  --rx NAZWA      nazwa tego komputera na stronie (domyslnie nazwa komputera)
  --plik LOG      zamiast portu: odtworz zapisany wczesniej log (test bez sprzetu)
Wymaga: pyserial (pip install pyserial). Odczyt napisu ze zdjecia - tylko gdy obok jest napis_ocr.py (numpy, Pillow).
"""
import argparse, binascii, json, os, re, socket, subprocess, sys, threading, time, urllib.request
from datetime import datetime, timezone

TU = os.path.dirname(os.path.abspath(__file__))
ZNAK = os.environ.get("T433_ZNAK", "N0CALL-11")
SSDV_ZNAK = "N0CALL"
CISZA_S = 60            # tyle sekund bez pakietu = zdjecie skonczone albo przerwane

# ---------------------------------------------------------------- base91 (wariant APRS, jak w t433_odbior.py na Dellu)
_B91 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+,./:;<=>?@[]^_`{-}~"'
_DEC = {c: i for i, c in enumerate(_B91)}

def b91_dekoduj(s):
    v, b, n, out = -1, 0, 0, bytearray()
    for ch in s:
        if ch not in _DEC: continue
        c = _DEC[ch]
        if v < 0: v = c; continue
        v += c * 91
        b |= v << n
        n += 13 if (v & 8191) > 88 else 14
        while True:
            out.append(b & 255); b >>= 8; n -= 8
            if n <= 7: break
        v = -1
    if v + 1: out.append((b | v << n) & 255)
    return bytes(out)

def kod_znaku(z):
    x = 0
    for ch in reversed(z):
        x *= 40; c = ord(ch)
        if 65 <= c <= 90: x += c - 51
        elif 97 <= c <= 122: x += c - 83
        elif 48 <= c <= 57: x += c - 47
    return x

def pakiet_ssdv(d):
    """174 B z ramki -> pelny pakiet SSDV 256 B (typ PADDING)"""
    img, pid = d[0], (d[1] << 8) | d[2]
    h = bytes([0x66 + 2]) + kod_znaku(SSDV_ZNAK).to_bytes(4, "big") + bytes([img]) + pid.to_bytes(2, "big") + d[3:]
    h += (binascii.crc32(h) & 0xffffffff).to_bytes(4, "big")
    p = b"\x55" + h
    return img, pid, p + b"\x00" * (256 - len(p))

_RE_POZ = re.compile(r"^(?:[/@](\d{2})(\d{2})(\d{2})[hz]|[!=])(\d{2})(\d{2}\.\d{2})([NS])(.)(\d{3})(\d{2}\.\d{2})([EW])(.)(.*)$")   # ramka pozycji APRS

# ---------------------------------------------------------------- most do Della (0.2)
class Most:
    """kolejka linii T433RX -> POST <dell>/t433_usb w osobnym watku (odczyt portu nigdy na to nie czeka)"""
    def __init__(self, dell, rx):
        self.url = dell.rstrip("/") + "/t433_usb"; self.rx = rx
        self.kol = []; self.lock = threading.Lock(); self.ok = None; self.wyslane = 0
        threading.Thread(target=self.petla, daemon=True).start()

    def dodaj(self, l):
        with self.lock:
            self.kol.append(l)
            if len(self.kol) > 2000: self.kol = self.kol[-2000:]

    def petla(self):
        while True:
            time.sleep(2)
            with self.lock: paczka = self.kol[:100]
            if not paczka: continue
            try:
                req = urllib.request.Request(self.url, data=json.dumps({"rx": self.rx, "linie": paczka}).encode("utf-8"),
                                             method="POST", headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=8) as r: json.loads(r.read().decode("utf-8"))
                with self.lock: self.kol = self.kol[len(paczka):]
                self.wyslane += len(paczka)
                if self.ok is not True: print("%s  [Dell] polaczony - ramki ida tez na strone LoRa 433" % ts(), flush=True)
                self.ok = True
            except Exception as e:
                if self.ok is not False: print("%s  [Dell] niedostepny (%s) - odbior lokalny dziala dalej, ponawiam" % (ts(), str(e)[:70]), flush=True)
                self.ok = False; time.sleep(13)

# ---------------------------------------------------------------- stan
def teraz(): return datetime.now(timezone.utc)
def ts(): return teraz().strftime("%H:%M:%S")

class Odbior:
    def __init__(self, katalog, dek, most=None):
        self.kat = katalog; self.dek = dek; self.most = most
        os.makedirs(os.path.join(katalog, "zdj"), exist_ok=True)
        self.log = open(os.path.join(katalog, "ramki.log"), "a", encoding="utf-8")
        self.buf = {}; self.ost = {}; self.rssi = {}; self.nazwy = {}; self.uzyte = set()
        self.stan = {"zdjecia": [], "statusy": [], "prywatne": []}
        self.n_ok = 0; self.n_crc = 0
        self.ocr = None
        for kat in (TU, "/opt/balony-json/t433"):
            if os.path.exists(os.path.join(kat, "napis_ocr.py")):
                try:
                    sys.path.insert(0, kat); import napis_ocr; self.ocr = napis_ocr; break
                except Exception as e:
                    print("  (odczyt napisu wylaczony: %s)" % e)

    def zapisz(self):
        p = os.path.join(self.kat, "t433_usb.json")
        with open(p + ".tmp", "w", encoding="utf-8") as f: json.dump(self.stan, f, ensure_ascii=False, indent=1)
        os.replace(p + ".tmp", p)

    def zloz(self, klucz, koniec=False):
        pk = self.buf[klucz]
        plik = os.path.join(self.kat, "zdj", self.nazwy.get(klucz) or "T433USB_%s_%03d.jpg" % klucz)
        brak = [i for i in range(max(pk) + 1) if i not in pk]
        wpis = {"plik": os.path.basename(plik), "img": klucz[1], "pakietow": len(pk), "max_pid": max(pk), "brakujace": brak,
                "rssi_min": min(self.rssi[klucz]), "rssi_max": max(self.rssi[klucz]), "czas": teraz().strftime("%Y-%m-%dT%H:%M:%SZ")}
        if not self.dek:
            if koniec: print("%s  ZDJECIE %d: %d pakietow, brak dekodera SSDV - JPEG niezapisany" % (ts(), klucz[1], len(pk)))
        else:
            r = subprocess.run([self.dek], input=b"".join(pk[i] for i in sorted(pk)), capture_output=True)
            if r.returncode == 0 and r.stdout:
                with open(plik, "wb") as f: f.write(r.stdout)
                wpis["jpeg_b"] = len(r.stdout)
                if self.ocr:
                    try: wpis["ocr"] = self.ocr.odczytaj(plik)
                    except Exception as e: wpis["ocr"] = {"ok": False, "blad": str(e)}
            elif koniec:
                print("%s  ZDJECIE %d: dekoder SSDV nie zlozyl obrazu (%s)" % (ts(), klucz[1], r.stderr.decode("latin-1").strip()[:80]))
        self.stan["zdjecia"] = [z for z in self.stan["zdjecia"] if z["plik"] != wpis["plik"]] + [wpis]
        self.zapisz()
        if koniec:
            o = wpis.get("ocr") or {}
            print("%s  ZDJECIE %d GOTOWE: %d z %d pakietow%s, sygnal %.0f..%.0f dBm%s%s" % (
                ts(), klucz[1], len(pk), max(pk) + 1, (" (brak: %s)" % ",".join(map(str, brak[:15]))) if brak else "",
                wpis["rssi_min"], wpis["rssi_max"],
                (", plik %s" % plik) if "jpeg_b" in wpis else "",
                (", napis: %s" % o.get("lokator")) if o.get("ok") else ""))

    def sprzatanie(self, wszystko=False):
        for k in list(self.ost):
            if wszystko or time.time() - self.ost[k] > CISZA_S:
                self.zloz(k, koniec=True); del self.ost[k]

    def linia(self, l):
        l = l.strip()
        if not l: return
        self.log.write("%s %s\n" % (teraz().strftime("%Y-%m-%dT%H:%M:%SZ"), l)); self.log.flush()
        if l.startswith("# "): return
        if self.most and l.startswith("T433RX;"): self.most.dodaj(l)
        if not l.startswith("T433RX;"):
            print("%s  [plytka] %s" % (ts(), l)); return
        p = l.split(";")
        if p[1] in ("INFO", "STAN", "BLAD"):
            if p[1] != "STAN" or "radio 0" in l: print("%s  [odbiornik] %s" % (ts(), ";".join(p[1:])))
            return
        try:
            tryb, rssi, snr, fe, dl, crc, dane = p[2], float(p[3]), float(p[4]), float(p[5]), int(p[6]), p[7] == "1", bytes.fromhex(p[8])
        except Exception:
            print("%s  [?] %s" % (ts(), l[:100])); return
        syg = "%6.1f dBm  SNR %5.1f dB  %+5.0f Hz" % (rssi, snr, fe)
        if not crc:
            self.n_crc += 1; print("%s  %s  BLAD CRC (%d B) - ramka uszkodzona" % (ts(), syg, dl)); return
        self.n_ok += 1
        if tryb == "P":
            t = dane.decode("latin-1")
            self.stan["prywatne"].append({"t": ts(), "tekst": t, "rssi": rssi}); self.zapisz()
            print("%s  %s  PRYWATNA: %s" % (ts(), syg, t)); return
        if dane[:3] != b"<\xff\x01":
            print("%s  %s  ramka bez naglowka LoRa APRS (%d B): %r" % (ts(), syg, dl, dane[:40])); return
        t = dane[3:].decode("latin-1")
        if ":" not in t or ">" not in t:
            print("%s  %s  nie-APRS: %s" % (ts(), syg, t[:60])); return
        nag, tresc = t.split(":", 1)
        zr = nag.split(">")[0]
        if zr != ZNAK:
            print("%s  %s  obca stacja %s: %s" % (ts(), syg, zr, tresc[:50])); return
        if tresc.startswith("{{I"):
            d = b91_dekoduj(tresc[3:].strip())
            if len(d) != 174:
                print("%s  %s  ZDJECIE: zla dlugosc po base91 (%d zamiast 174)" % (ts(), syg, len(d))); return
            img, pid, pak = pakiet_ssdv(d)
            k = (teraz().strftime("%Y%m%d"), img)
            # ten sam numer po zakonczonym zdjeciu: pakiet o numerze mniejszym niz juz odebrane = nowe zdjecie; inaczej wznowienie (v0.5)
            if k in self.buf and self.buf[k] and ((k not in self.ost and pid < max(self.buf[k])) or pid < max(self.buf[k]) - 5):
                if k in self.ost: self.zloz(k, koniec=True)
                self.buf.pop(k, None); self.rssi.pop(k, None); self.ost.pop(k, None); self.nazwy.pop(k, None)
            if k not in self.nazwy:
                n = "T433USB_%s_%s_%03d" % (k[0], teraz().strftime("%H%M%S"), img); i = 2; baza = n
                while n in self.uzyte: n = "%s_%d" % (baza, i); i += 1
                self.uzyte.add(n); self.nazwy[k] = n + ".jpg"
            self.buf.setdefault(k, {})[pid] = pak; self.rssi.setdefault(k, []).append(rssi); self.ost[k] = time.time()
            print("%s  %s  ZDJECIE %d pakiet %d (mam %d)" % (ts(), syg, img, pid, len(self.buf[k])))
            if len(self.buf[k]) % 5 == 1: self.zloz(k)          # podglad czesciowy
        elif tresc.startswith(">"):
            self.stan["statusy"].append({"t": ts(), "tekst": tresc[1:], "rssi": rssi}); self.zapisz()
            print("%s  %s  STATUS: %s" % (ts(), syg, tresc[1:]))
        elif _RE_POZ.match(tresc):
            m = _RE_POZ.match(tresc)
            lat = (int(m.group(4)) + float(m.group(5)) / 60) * (-1 if m.group(6) == "S" else 1)
            lon = (int(m.group(8)) + float(m.group(9)) / 60) * (-1 if m.group(10) == "W" else 1)
            a = re.search(r"/A=(-?\d{5,6})", m.group(12)); alt = int(round(int(a.group(1)) * 0.3048)) if a else None
            kom = re.sub(r"^\d{3}/\d{3}", "", m.group(12)); kom = re.sub(r"/A=-?\d{5,6}", "", kom).strip()
            self.stan.setdefault("pozycje", []).append({"t": ts(), "lat": round(lat, 5), "lon": round(lon, 5), "alt": alt, "tekst": tresc, "rssi": rssi}); self.zapisz()
            print("%s  %s  POZYCJA: %.5f %.5f%s%s  %s" % (ts(), syg, lat, lon, (" %d m" % alt) if alt is not None else "",
                  (" fix %s:%s:%s UTC" % (m.group(1), m.group(2), m.group(3))) if m.group(1) else "", kom))
        else:
            print("%s  %s  inna ramka %s: %s" % (ts(), syg, ZNAK, tresc[:60]))

def znajdz_dek(podany):
    kand = [podany] if podany else []
    kand += [os.path.join(TU, "ssdv_dek.exe" if os.name == "nt" else "ssdv_dek"), os.path.join(TU, "ssdv", "ssdv_dek"),
             "/opt/balony-json/t433/ssdv/ssdv_dek"]
    for k in kand:
        if k and os.path.isfile(k): return k
    return None

def main():
    ap = argparse.ArgumentParser(description="T433 - odbior przez USB z plytki-odbiornika")
    ap.add_argument("port", nargs="?", help="port szeregowy, np. COM5 albo /dev/ttyACM0")
    ap.add_argument("--katalog", default=os.path.join(os.getcwd(), "t433_usb"))
    ap.add_argument("--dek"); ap.add_argument("--pryw", action="store_true"); ap.add_argument("--plik")
    ap.add_argument("--dell", default=""); ap.add_argument("--bez-della", action="store_true")
    ap.add_argument("--rx", default=socket.gethostname())
    a = ap.parse_args()
    dek = znajdz_dek(a.dek)
    most = None if (a.bez_della or a.plik or not a.dell) else Most(a.dell, a.rx)
    o = Odbior(a.katalog, dek, most)
    print("T433 odbior USB v0.5 | katalog: %s | dekoder SSDV: %s | odczyt napisu: %s | Dell: %s" % (a.katalog, dek or "BRAK (same ramki, bez JPEG)", "tak" if o.ocr else "nie", most.url if most else "nie"))
    if a.plik:
        for l in open(a.plik, encoding="utf-8", errors="replace"):
            if l[:4].isdigit() and "T" in l[:20] and " " in l: l = l.split(" ", 1)[1]     # log z czasem na poczatku
            o.linia(l)
        o.sprzatanie(wszystko=True)
        print("Koniec pliku: ramek dobrych %d, z bledem CRC %d" % (o.n_ok, o.n_crc)); return
    if not a.port: ap.error("podaj port (np. COM5 albo /dev/ttyACM0) albo --plik")
    try: import serial
    except ImportError: sys.exit("Brak pyserial: pip install pyserial")
    print("Ctrl+C konczy. Czekam na ramki...")
    while True:
        try:
            s = serial.Serial(a.port, 115200, timeout=1)
            time.sleep(0.5); s.write(b"p" if a.pryw else b"a"); s.write(b"?")
            ost = time.time()
            while True:
                l = s.readline()
                if l: o.linia(l.decode("latin-1")); ost = time.time()
                o.sprzatanie()
        except KeyboardInterrupt:
            o.sprzatanie(wszystko=True)
            print("\nKoniec: ramek dobrych %d, z bledem CRC %d. Zapis: %s" % (o.n_ok, o.n_crc, a.katalog)); return
        except Exception as e:
            print("%s  port %s: %s - ponawiam za 3 s" % (ts(), a.port, e)); time.sleep(3)

if __name__ == "__main__":
    main()
