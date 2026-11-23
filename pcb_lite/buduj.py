# -*- coding: utf-8 -*-
"""Buduje tracker433.kicad_pcb z projekt.py (KiCad 7, pcbnew)."""
import sys, pcbnew
sys.path.insert(0, "/home/claude/t433lite")
from projekt import *

OX, OY = 100.0, 100.0
mm = pcbnew.FromMM
b = pcbnew.BOARD()

# --- warstwy: 2 Cu ---
b.SetCopperLayerCount(2)
ds = b.GetDesignSettings()
ds.SetBoardThickness(mm(0.8))
ds.m_TrackMinWidth = mm(0.127)
ds.m_MinClearance = mm(0.127)
ds.m_HoleClearance = mm(0.2)
ds.m_HoleToHoleMin = mm(0.25)
ds.m_ViasMinSize = mm(0.6)
ds.m_MinThroughDrill = mm(0.3)
ds.m_CopperEdgeClearance = mm(0.3)

nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetTrackWidth(mm(0.15)); nc.SetClearance(mm(0.127)); nc.SetViaDiameter(mm(0.6)); nc.SetViaDrill(mm(0.3))

nets = {}
ns = ds.m_NetSettings
PWR = pcbnew.NETCLASS("PWR"); PWR.SetTrackWidth(mm(0.4)); PWR.SetClearance(mm(0.127)); PWR.SetViaDiameter(mm(0.7)); PWR.SetViaDrill(mm(0.35))
ns.m_NetClasses["PWR"] = PWR
PWR_NETS = {"VSC", "+3V3", "GND", "GPS_VCC", "LORA_ANT", "GPS_ANT"}
def net(name):
    if name is None: return None
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n
        if name in PWR_NETS: n.SetNetClass(PWR)
    return nets[name]

def place(ref, fpdef, value, x, y, rot):
    fp = pcbnew.FootprintLoad(fpdef[0], fpdef[1])
    if fp is None: raise SystemExit("brak footprintu " + str(fpdef))
    fp.SetReference(ref); fp.SetValue(value)
    b.Add(fp)
    fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x + DX), mm(OY + y)))
    fp.SetOrientationDegrees(rot)
    if ref in BOTTOM: fp.Flip(fp.GetPosition(), False)
    fp.Reference().SetLayer(pcbnew.B_Fab if ref in BOTTOM else pcbnew.F_Fab)
    fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.5), mm(0.5)))
    fp.Reference().SetTextThickness(mm(0.08))
    fp.Value().SetVisible(False)
    return fp

FP = {}
for ref, fpd, val, lcsc, x, y, rot, pads in PARTS:
    fp = place(ref, fpd, val, x, y, rot); FP[ref] = (fp, lcsc)
    for p in fp.Pads():
        try: num = int(p.GetNumber())
        except ValueError: continue
        n = pads.get(num)
        if n: p.SetNet(net(n))
for ref, fpd, val, lcsc, x, y, rot, n1, n2 in PAS:
    fp = place(ref, fpd, val, x, y, rot); FP[ref] = (fp, lcsc)
    for p in fp.Pads():
        p.SetNet(net(n1 if p.GetNumber() == "1" else n2))
for ref, fpd, n, x, y, opis in PADS:
    fp = place(ref, fpd, opis, x, y, 0); FP[ref] = (fp, None)
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    for p in fp.Pads(): p.SetNet(net(n))
    fp.Reference().SetVisible(False)
    fp.Reference().SetVisible(False)
    if ref in ("TP23", "TP24", "TP25"):
        bot = ref in BOTTOM
        t = pcbnew.PCB_TEXT(b); t.SetText(opis); t.SetLayer(pcbnew.B_SilkS if bot else pcbnew.F_SilkS); t.SetMirrored(bot)
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.15))
        t.SetPosition(pcbnew.VECTOR2I(mm(OX + x + DX + (0.6 if ref == "TP23" else 0)), mm(OY + y + (-1.45 if ref == "TP23" else 1.8)))); b.Add(t)

# otwory NPTH
for i, (x, y) in enumerate(HOLES):
    fp = pcbnew.FOOTPRINT(b); fp.SetReference("H%d" % (i + 1)); fp.Reference().SetVisible(False)
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
    pad = pcbnew.PAD(fp); pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0))); pad.SetDrillSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    ls = pcbnew.LSET.AllCuMask(); ls.AddLayer(pcbnew.F_Mask); ls.AddLayer(pcbnew.B_Mask); pad.SetLayerSet(ls)
    fp.Add(pad); b.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))

# metalizowany otwor pod drut (ustawienie paneli)
fp = pcbnew.FOOTPRINT(b); fp.SetReference("H3"); fp.Reference().SetVisible(False)
fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
pad = pcbnew.PAD(fp); pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH); pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE); pad.SetNumber("1")
pad.SetSize(pcbnew.VECTOR2I(mm(WIRE_HOLE[3]), mm(WIRE_HOLE[3]))); pad.SetDrillSize(pcbnew.VECTOR2I(mm(WIRE_HOLE[2]), mm(WIRE_HOLE[2])))
ls = pcbnew.LSET.AllCuMask(); ls.AddLayer(pcbnew.F_Mask); ls.AddLayer(pcbnew.B_Mask); pad.SetLayerSet(ls)
fp.Add(pad); b.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(mm(OX + WIRE_HOLE[0]), mm(OY + WIRE_HOLE[1])))
t = pcbnew.PCB_TEXT(b); t.SetText("DRUT"); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.15))
t.SetPosition(pcbnew.VECTOR2I(mm(OX + WIRE_HOLE[0]), mm(OY + WIRE_HOLE[1] + 1.4))); b.Add(t)

def otwor(ref, x, y, drill, pad, netname=None, npth=False):
    fp = pcbnew.FOOTPRINT(b); fp.SetReference(ref); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | (pcbnew.FP_BOARD_ONLY if npth else 0))
    p = pcbnew.PAD(fp); p.SetNumber("" if npth else "1")
    p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH if npth else pcbnew.PAD_ATTRIB_PTH); p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(pcbnew.VECTOR2I(mm(pad), mm(pad))); p.SetDrillSize(pcbnew.VECTOR2I(mm(drill), mm(drill)))
    ls = pcbnew.LSET.AllCuMask(); ls.AddLayer(pcbnew.F_Mask); ls.AddLayer(pcbnew.B_Mask); p.SetLayerSet(ls)
    fp.Add(p); b.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
    if netname: p.SetNet(net(netname))
    FP[ref] = (fp, None)
    return fp
def napis(txt, x, y, h=0.7, ang=0, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(layer); t.SetMirrored(layer == pcbnew.B_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h))); t.SetTextThickness(mm(max(0.1, 0.15 * h))); t.SetTextAngleDegrees(ang)
    t.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))); b.Add(t)
# pola PV (otwory pod drut 0,4 mm)
for ref, n, x, y, opis in PV_HOLES:
    otwor(ref, x, y, PV_DRILL, PV_PAD, n)
    napis(opis, x + (1.2 if x < W / 2 else -1.2), y, 0.9)
napis("PV", 1.1, 20.5, 0.8); napis("PV", W - 1.1, 20.5, 0.8)
for ref, n, x, y, opis in ANT_HOLES:
    otwor(ref, x, y, PV_DRILL, PV_PAD, n)
    napis(opis, x + (1.9 if x < W / 2 else -1.9), y, 0.8)
# otworki mostka listka
for k, y in enumerate(MOUSE): otwor("MB%d" % (k + 1), 0, y, 0.5, 0.5, npth=True)
# goldpin 2x3 na listku
j2 = pcbnew.FootprintLoad(STD + "Connector_PinHeader_2.54mm.pretty", "PinHeader_2x03_P2.54mm_Vertical")
j2.SetReference("J2"); j2.SetValue("PROG 2x3"); j2.Reference().SetVisible(False); j2.Value().SetVisible(False)
j2.SetAttributes(j2.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
b.Add(j2); j2.SetPosition(pcbnew.VECTOR2I(mm(OX + J2["x"]), mm(OY + J2["y"]))); FP["J2"] = (j2, None)
for p in j2.Pads():
    n_, opis = J2["pins"][int(p.GetNumber())]; p.SetNet(net(n_))
    px, py = p.GetPosition().x / 1e6 - OX, p.GetPosition().y / 1e6 - OY
    napis(opis, px - 1.32 if int(p.GetNumber()) % 2 else px + 1.32, py, 0.8, 90)
napis("PROG", (TAB["x0"] + TAB["x1"]) / 2, TAB["y1"] - 0.9, 0.8)

# --- obrys z zaokraglonymi rogami ---
def seg(x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    s.SetStart(pcbnew.VECTOR2I(mm(OX + x1), mm(OY + y1))); s.SetEnd(pcbnew.VECTOR2I(mm(OX + x2), mm(OY + y2))); b.Add(s)
def arc(cx, cy, sx, sy, ang):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_ARC); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    s.SetCenter(pcbnew.VECTOR2I(mm(OX + cx), mm(OY + cy))); s.SetStart(pcbnew.VECTOR2I(mm(OX + sx), mm(OY + sy)))
    s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T)); b.Add(s)
r = 1.0
seg(r, 0, W - r, 0); seg(W, r, W, H - r); seg(W - r, H, r, H)
_p = [(0, H - r), (0, BRIDGE["y1"]), (TAB["x1"], BRIDGE["y1"]), (TAB["x1"], TAB["y1"]), (TAB["x0"], TAB["y1"]),
      (TAB["x0"], TAB["y0"]), (TAB["x1"], TAB["y0"]), (TAB["x1"], BRIDGE["y0"]), (0, BRIDGE["y0"]), (0, r)]
for _a, _c in zip(_p, _p[1:]): seg(_a[0], _a[1], _c[0], _c[1])
arc(r, r, 0, r, 90); arc(W - r, r, W - r, 0, 90); arc(W - r, H - r, W, H - r, 90); arc(r, H - r, r, H, 90)

# --- strefy: GND na In1 i obu zewnetrznych, +3V3 na In2 ---
def zone(layer, netname, prio=0):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(net(netname)); z.SetAssignedPriority(prio)
    o = z.Outline(); o.NewOutline()
    for x, y in [(0.2, 0.2), (W - 0.2, 0.2), (W - 0.2, H - 0.2), (0.2, H - 0.2)]:
        o.Append(mm(OX + x), mm(OY + y))
    z.SetLocalClearance(mm(0.15)); z.SetMinThickness(mm(0.15))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetThermalReliefGap(mm(0.2)); z.SetThermalReliefSpokeWidth(mm(0.2))
    b.Add(z); return z
zone(pcbnew.B_Cu, "GND")
if "--strefy" in sys.argv:
    zone(pcbnew.F_Cu, "GND")


# --- fanout: przelotka od kazdego pola GND / +3V3 do plaszczyzn In1 (GND) / In2 (+3V3) ---
import math
VIA_D, VIA_H, CLR = 0.6, 0.3, 0.15
vias = []                      # (x, y, net)
allpads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]
def pad_rect(p):
    bb = p.GetBoundingBox(); return (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
PR = [(p, pad_rect(p)) for p in allpads]
def dist_rect(x, y, r):
    dx = max(r[0] - x, 0, x - r[2]); dy = max(r[1] - y, 0, y - r[3]); return math.hypot(dx, dy)
def ok_via(x, y, netn, own):
    if not (OX + 0.6 < x < OX + W - 0.6 and OY + 0.6 < y < OY + H - 0.6): return False
    for p, r in PR:
        d = dist_rect(x, y, r)
        if p.GetNetname() == netn:
            if p is own or (p.GetPosition()==own.GetPosition() and p.GetNumber()==own.GetNumber()): continue
            if d < 0.05: return False           # nie w srodku innego pola (pasta)
            continue
        if d < VIA_D / 2 + CLR: return False
    for vx, vy, vn in vias:
        if math.hypot(vx - x, vy - y) < VIA_D + (0.1 if vn == netn else CLR): return False
    return True
def seg_ok(x1, y1, x2, y2, netn, own):
    lay = pcbnew.F_Cu if own.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    for k in range(1, 9):
        x = x1 + (x2 - x1) * k / 9; y = y1 + (y2 - y1) * k / 9
        for p, r in PR:
            if p is own or p.GetNetname() == netn or not p.IsOnLayer(lay): continue
            if dist_rect(x, y, r) < 0.125 + CLR: return False
    return True
def add_track(x1, y1, x2, y2, n, w=0.25, lay=None):
    t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1))); t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(w)); t.SetLayer(lay if lay is not None else pcbnew.F_Cu); t.SetNet(n); t.SetLocked(True); b.Add(t)
def add_via(x, y, n):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_H))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(n); v.SetLocked(True); b.Add(v); vias.append((x, y, n.GetNetname()))
brak = []
for f in b.GetFootprints():
    fc = f.GetPosition(); fx, fy = pcbnew.ToMM(fc.x), pcbnew.ToMM(fc.y)
    for p in f.Pads():
        n = p.GetNet(); nn = p.GetNetname()
        if nn != "GND": continue
        if f.GetReference() == "U1" and p.GetNumber() != "61": continue   # obrzeze modulu: GND przez wylewke na gorze
        LAY = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        pc = p.GetPosition(); px, py = pcbnew.ToMM(pc.x), pcbnew.ToMM(pc.y)
        r = pad_rect(p); hw, hh = (r[2] - r[0]) / 2, (r[3] - r[1]) / 2
        if hw > 2 and hh > 2:                          # duze pole (EP ESP32): siatka 3x3 przelotek w polu
            for ix in (-1.6, 0, 1.6):
                for iy in (-1.6, 0, 1.6):
                    if ok_via(px + ix, py + iy, nn, p): add_via(px + ix, py + iy, n)
            continue
        if f.GetReference().startswith("TP"): pass
        # kierunek "na zewnatrz" elementu
        dx, dy = px - fx, py - fy
        if abs(dx) < 1e-3 and abs(dy) < 1e-3: dx, dy = 0, -1
        dirs = []
        if abs(dx) >= abs(dy): dirs.append((math.copysign(1, dx), 0))
        else: dirs.append((0, math.copysign(1, dy)))
        dirs += [(0, -1), (0, 1), (-1, 0), (1, 0), (0.707, 0.707), (-0.707, 0.707), (0.707, -0.707), (-0.707, -0.707)]
        done = False
        for vx, vy, vn in vias:                        # istniejaca przelotka tej sieci blisko pola
            if vn == nn and math.hypot(vx - px, vy - py) < max(hw, hh) + 0.75 and seg_ok(px, py, vx, vy, nn, p):
                add_track(px, py, vx, vy, n, lay=LAY); done = True; break
        if done: continue
        for ddx, ddy in dirs:
            base = (hw if abs(ddx) > 0.5 else hh) + VIA_D / 2 + 0.12
            ds = (base + 0.2, base + 0.6, base + 1.0) if f.GetReference() == "U1" else (base, base + 0.3, base + 0.6, base + 1.0, base + 1.5)
            for d in ds:
                for lat in (0, 0.35, -0.35, 0.7, -0.7):
                    x = px + ddx * d + (lat if ddy else 0); y = py + ddy * d + (lat if ddx else 0)
                    if ok_via(x, y, nn, p) and seg_ok(px, py, x, y, nn, p):
                        add_track(px, py, x, y, n, lay=LAY); add_via(x, y, n); done = True; break
                if done: break
            if done: break
        if not done:                                   # ostatecznie: sciezka do najblizszej przelotki tej sieci (do 2 mm)
            best = None
            for vx, vy, vn in vias:
                dd = math.hypot(vx - px, vy - py)
                if vn == nn and dd < 2.0 and seg_ok(px, py, vx, vy, nn, p) and (best is None or dd < best[0]): best = (dd, vx, vy)
            if best: add_track(px, py, best[1], best[2], n, lay=LAY); done = True
        if not done: brak.append(f.GetReference() + "." + p.GetNumber())
print("przelotek fanout:", len(vias), "bez przelotki:", brak)


# --- sciezki w.cz. do otworow antenowych (0,4 mm, na gorze) ---
def rf(net_, pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        add_track(OX + x1, OY + y1, OX + x2, OY + y2, net(net_), w=0.4)
_p6 = [p for p in FP["U2"][0].Pads() if p.GetNumber() == "6"][0].GetPosition()
_x6, _y6 = _p6.x / 1e6 - OX, _p6.y / 1e6 - OY
rf("LORA_ANT", [(_x6, _y6), (1.9, _y6), (1.9, 2.4), (ANT_HOLES[0][2], ANT_HOLES[0][3])])
_p11 = [p for p in FP["U3"][0].Pads() if p.GetNumber() == "11"][0].GetPosition()
rf("GPS_ANT", [(_p11.x / 1e6 - OX, _p11.y / 1e6 - OY), (ANT_HOLES[1][2], ANT_HOLES[1][3])])

# --- pas zakazu sciezek/przelotek 0,35 mm przy krawedzi (dla autoroutera) ---
for (x1, y1, x2, y2) in [(0, 0, W, 0.35), (0, H - 0.35, W, H), (0, 0, 0.35, BRIDGE["y0"]), (0, BRIDGE["y1"], 0.35, H), (W - 0.35, 0, W, H),
                         (TAB["x0"], TAB["y0"], TAB["x1"], TAB["y0"] + 0.35), (TAB["x0"], TAB["y1"] - 0.35, TAB["x1"], TAB["y1"]), (TAB["x0"], TAB["y0"], TAB["x0"] + 0.35, TAB["y1"])]:
    z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowCopperPour(False); z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET(); [ls.AddLayer(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu)]; z.SetLayerSet(ls)
    o = z.Outline(); o.NewOutline()
    for x, y in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]: o.Append(mm(OX + x), mm(OY + y))
    b.Add(z)

# zakaz sciezek na F.Cu pod modulem ESP32 (poza polami)
_u = FP["U1"][0].GetPosition(); _ux, _uy = _u.x / 1e6 - OX, _u.y / 1e6 - OY
z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(False)
z.SetDoNotAllowPads(False); z.SetDoNotAllowCopperPour(False); z.SetDoNotAllowFootprints(False)
ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); z.SetLayerSet(ls)
o = z.Outline(); o.NewOutline()
for x, y in [(-6.4, -6.4), (6.4, -6.4), (6.4, 6.4), (-6.4, 6.4)]: o.Append(mm(OX + _ux + x), mm(OY + _uy + y))
o.NewHole()
for x, y in [(-3.6, -3.6), (3.6, -3.6), (3.6, 3.6), (-3.6, 3.6)]: o.Append(mm(OX + _ux + x), mm(OY + _uy + y), 0, 0)
b.Add(z)

# napis
t = pcbnew.PCB_TEXT(b); t.SetText(NAPIS); t.SetLayer(pcbnew.B_SilkS)
t.SetPosition(pcbnew.VECTOR2I(mm(OX + W / 2), mm(OY + 20.0))); t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
t.SetTextThickness(mm(0.15)); t.SetMirrored(True); b.Add(t)

out = "/home/claude/t433lite/pcb/t433lite.kicad_pcb"
b.Save(out)
print("zapisano", out, "elementow:", len(FP), "sieci:", len(nets))

# --- kontrola nakladania sie (courtyard / bbox) ---
import itertools
def box(fp):
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False, False)
    return bb
items = [(r, f) for r, (f, _) in FP.items()]
for (r1, f1), (r2, f2) in itertools.combinations(items, 2):
    if f1.GetBoundingBox(False, False).Intersects(f2.GetBoundingBox(False, False)):
        # sprawdz pady
        for p1 in f1.Pads():
            for p2 in f2.Pads():
                same = (p1.IsOnLayer(pcbnew.F_Cu) and p2.IsOnLayer(pcbnew.F_Cu)) or (p1.IsOnLayer(pcbnew.B_Cu) and p2.IsOnLayer(pcbnew.B_Cu))
                if same and p1.GetBoundingBox().Intersects(p2.GetBoundingBox()):
                    print("KOLIZJA PADOW", r1, p1.GetNumber(), r2, p2.GetNumber()); break
eb = b.GetBoardEdgesBoundingBox()
for r, f in items:
    for p in f.Pads():
        pb = p.GetBoundingBox()
        if pb.GetLeft() < eb.GetLeft() + mm(0.2) or pb.GetRight() > eb.GetRight() - mm(0.2) or pb.GetTop() < eb.GetTop() + mm(0.2) or pb.GetBottom() > eb.GetBottom() - mm(0.2):
            print("PAD PRZY KRAWEDZI", r, p.GetNumber())

# --- kontrola courtyardow (strona gorna) ---
cy = []
for r, f in items:
    c = f.GetCourtyard(pcbnew.F_CrtYd)
    if c.OutlineCount(): cy.append((r, c.BBox()))
for (r1, b1), (r2, b2) in itertools.combinations(cy, 2):
    if b1.Intersects(b2):
        print("KOLIZJA COURTYARD", r1, r2)
