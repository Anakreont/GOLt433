import sys, re, pcbnew
P = "/home/claude/t433lite/pcb/t433lite.kicad_pcb"
b = pcbnew.LoadBoard(P)
s = open(sys.argv[1]).read()
res = int(re.search(r"\(resolution um (\d+)\)", s).group(1))
k = 1000 // res                                      # jednostka SES -> nm
L = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu}
nets = b.GetNetsByName()
# usun stare sciezki
have = set()
if '--zastap' in sys.argv:
    for t in list(b.GetTracks()): b.Delete(t)
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T: have.add(('v', t.GetPosition().x//1000, t.GetPosition().y//1000))
    else: have.add(('t', t.GetStart().x//1000, t.GetStart().y//1000, t.GetEnd().x//1000, t.GetEnd().y//1000)); have.add(('t', t.GetEnd().x//1000, t.GetEnd().y//1000, t.GetStart().x//1000, t.GetStart().y//1000))
tok = re.findall(r"\(|\)|\"[^\"]*\"|[^\s()]+", s[s.index("(network_out"):])
i = 0; cur = None; ntr = nvia = 0
def P2(x, y): return pcbnew.VECTOR2I(int(float(x) * k), int(-float(y) * k))
while i < len(tok):
    t = tok[i]
    if t == "(" and tok[i + 1] == "net":
        cur = nets[tok[i + 2].strip('"')]; i += 3; continue
    if t == "(" and tok[i + 1] == "path":
        lay = L[tok[i + 2]]; w = int(float(tok[i + 3]) * k); j = i + 4; pts = []
        while tok[j] != ")": pts.append(tok[j]); j += 1
        xy = [P2(pts[n], pts[n + 1]) for n in range(0, len(pts), 2)]
        for a, c in zip(xy, xy[1:]):
            if ('t', a.x//1000, a.y//1000, c.x//1000, c.y//1000) in have: continue
            tr = pcbnew.PCB_TRACK(b); tr.SetStart(a); tr.SetEnd(c); tr.SetWidth(w); tr.SetLayer(lay); tr.SetNet(cur); b.Add(tr); ntr += 1
        i = j; continue
    if t == "(" and tok[i + 1] == "via":
        name = tok[i + 2].strip('"'); x, y = tok[i + 3], tok[i + 4]
        m = re.search(r"_(\d+):(\d+)_um", name)
        if ('v', P2(x, y).x//1000, P2(x, y).y//1000) in have: i += 5; continue
        v = pcbnew.PCB_VIA(b); v.SetPosition(P2(x, y)); v.SetWidth(int(m.group(1)) * 1000); v.SetDrill(int(m.group(2)) * 1000)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(cur); b.Add(v); nvia += 1
        i += 5; continue
    i += 1
print("sciezki", ntr, "przelotki", nvia)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(P, b)
b = pcbnew.LoadBoard(P)
pcbnew.WriteDRCReport(b, "/home/claude/t433lite/pcb/drc.txt", pcbnew.EDA_UNITS_MILLIMETRES, True)
