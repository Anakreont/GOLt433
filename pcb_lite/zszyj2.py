# laczy grupy wysp GND (F/B) przelotkami tam, gdzie wyspa F jednej grupy nachodzi na wyspe B innej
import pcbnew
from collections import defaultdict
P = "/home/claude/t433lite/pcb/t433lite.kicad_pcb"
for runda in range(6):
    b = pcbnew.LoadBoard(P); G = "GND"; g = b.GetNetsByName()[G]
    vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == G]
    pth = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == G and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
    frs = []
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != G: continue
        L = z.GetLayer(); fp = z.GetFilledPolysList(L)
        for k in range(fp.OutlineCount()): frs.append((L, fp, k))
    par = list(range(len(frs)))
    def F(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for it in [v.GetPosition() for v in vias] + [p.GetPosition() for p in pth]:
        ids = [i for i, (L, fp, k) in enumerate(frs) if fp.Contains(it, k)]
        for i in ids[1:]: par[F(i)] = F(ids[0])
    gr = defaultdict(list)
    for i in range(len(frs)): gr[F(i)].append(i)
    if len(gr) == 1: print("jedna grupa GND"); break
    main = max(gr, key=lambda r: sum(frs[i][1].Outline(frs[i][2]).Area() for i in gr[r]))
    dod = 0
    for r, ids in gr.items():
        if r == main: continue
        done = False
        for i in ids:
            L1, fp1, k1 = frs[i]
            for j in gr[main]:
                L2, fp2, k2 = frs[j]
                if L1 == L2: continue
                bb = fp1.Outline(k1).BBox()
                for x in range(bb.GetLeft(), bb.GetRight(), 100000):
                    for y in range(bb.GetTop(), bb.GetBottom(), 100000):
                        ok = all(fp1.Contains(pcbnew.VECTOR2I(x + dx, y + dy), k1) and fp2.Contains(pcbnew.VECTOR2I(x + dx, y + dy), k2)
                                 for dx, dy in ((0, 0), (450000, 0), (-450000, 0), (0, 450000), (0, -450000), (320000, 320000), (-320000, 320000), (320000, -320000), (-320000, -320000)))
                        if ok:
                            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(x, y)); v.SetWidth(600000); v.SetDrill(300000)
                            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(g); b.Add(v); dod += 1; done = True
                            print("przelotka", round(x / 1e6 - 100, 2), round(y / 1e6 - 100, 2)); break
                    if done: break
                if done: break
            if done: break
        if not done: print("nie znaleziono miejsca dla grupy", [(frs[i][0], round(frs[i][1].Outline(frs[i][2]).Area() / 1e12, 2)) for i in ids])
    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(P, b)
    if dod == 0: break
