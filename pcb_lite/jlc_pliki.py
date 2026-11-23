# -*- coding: utf-8 -*-
"""Pliki dla JLCPCB: Gerbery + wiercenia (zip), BOM.csv, CPL.csv (z t433lite.kicad_pcb)."""
import csv, os, subprocess, sys, zipfile, collections
sys.path.insert(0, "/home/claude/t433lite")
import pcbnew
from projekt import PARTS, PAS

PCB = "/home/claude/t433lite/pcb/t433lite.kicad_pcb"
OUT = "/home/claude/t433lite/jlcpcb"
os.makedirs(OUT + "/gerber", exist_ok=True)

layers = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "-o", OUT + "/gerber/", "-l", layers,
                "--subtract-soldermask", "--no-x2", PCB], check=True, capture_output=True)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "-o", OUT + "/gerber/", "--format", "excellon",
                "--drill-origin", "absolute", "--excellon-units", "mm", "--excellon-separate-th",
                "--generate-map", "--map-format", "gerberx2", PCB], check=True, capture_output=True)
zp = OUT + "/t433lite_gerber.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(OUT + "/gerber")):
        z.write(OUT + "/gerber/" + f, f)

lcsc = {r[0]: r[3] for r in PARTS}
lcsc.update({r[0]: r[3] for r in PAS})
val = {r[0]: r[2] for r in PARTS}
val.update({r[0]: r[2] for r in PAS})

b = pcbnew.LoadBoard(PCB)
rows, bom = [], collections.OrderedDict()
for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    ref = fp.GetReference()
    if ref not in lcsc: continue
    pos = fp.GetPosition()
    x = pcbnew.ToMM(pos.x); y = -pcbnew.ToMM(pos.y)
    rot = fp.GetOrientationDegrees() % 360
    lay = "Bottom" if fp.IsFlipped() else "Top"
    rows.append([ref, "%.3f" % x, "%.3f" % y, lay, "%.1f" % rot])
    key = lcsc[ref]   # 8.11: grupowanie po numerze LCSC (JLC nie przyjmuje tej samej czesci w dwoch wierszach)
    bom.setdefault(key, {"v": val[ref].split(" (")[0], "fp": fp.GetFPID().GetLibItemName().wx_str(), "refs": []})["refs"].append(ref)

with open(OUT + "/CPL_t433lite.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]); w.writerows(rows)
with open(OUT + "/BOM_t433lite.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for l, e in bom.items():
        w.writerow([e["v"], ",".join(e["refs"]), e["fp"], l])
print("spod:", [r[0] for r in rows if r[3] == "Bottom"])
print("gerber zip:", zp, os.path.getsize(zp), "B; elementow w CPL:", len(rows), "; pozycji BOM:", len(bom))
