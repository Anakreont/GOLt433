# -*- coding: utf-8 -*-
"""Dodaje przelotki GND do wysp masy na F/B, ktore nie maja polaczenia z In1 (po wypelnieniu stref)."""
import pcbnew
P = "/home/claude/t433lite/pcb/t433lite.kicad_pcb"
b = pcbnew.LoadBoard(P)
gnd = b.GetNetsByName()["GND"]
vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND"]
pth = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == "GND" and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
dod = 0
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname() != "GND" or z.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu): continue
    fp = z.GetFilledPolysList(z.GetLayer())
    for k in range(fp.OutlineCount()):
        out = fp.Outline(k)
        has = any(fp.Contains(v.GetPosition(), k) for v in vias) or any(fp.Contains(p.GetPosition(), k) for p in pth)
        if has: continue
        bb = out.BBox(); ok = None
        step = 100000
        for x in range(bb.GetLeft(), bb.GetRight(), step):
            for y in range(bb.GetTop(), bb.GetBottom(), step):
                c = pcbnew.VECTOR2I(x, y)
                if not fp.Contains(c, k): continue
                # odleglosc od krawedzi wyspy >= 0.25 mm (promien przelotki 0.2 + zapas)
                tmp = pcbnew.SHAPE_POLY_SET(); tmp.AddOutline(out)
                if tmp.SquaredDistance(c, False) if False else False: pass
                ok_ = True
                for dx, dy in ((450000, 0), (-450000, 0), (0, 450000), (0, -450000), (320000, 320000), (-320000, 320000), (320000, -320000), (-320000, -320000)):
                    if not fp.Contains(pcbnew.VECTOR2I(x + dx, y + dy), k): ok_ = False; break
                if ok_: ok = c; break
            if ok: break
        if ok:
            v = pcbnew.PCB_VIA(b); v.SetPosition(ok); v.SetWidth(600000); v.SetDrill(300000)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v); vias.append(v); dod += 1
            print("przelotka GND", z.GetLayerName(), round(ok.x / 1e6 - 100, 2), round(ok.y / 1e6 - 100, 2), "pole wyspy mm2", round(out.Area() / 1e12, 2))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
b = pcbnew.LoadBoard(P)
pcbnew.WriteDRCReport(b, "/home/claude/t433lite/pcb/drc.txt", pcbnew.EDA_UNITS_MILLIMETRES, True)
print("dodano", dod)
