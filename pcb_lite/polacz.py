# -*- coding: utf-8 -*-
"""Dotrasowanie wskazanych polaczen pad-pad prostym A* (F/In1/In2/B + przelotki).
uzycie: python3 polacz.py U7.1:U7.3[:0.2] J2.3:TP24.1 ..."""
import math, heapq, sys
import numpy as np
import pcbnew
sys.path.insert(0, "/home/claude/t433lite")
from projekt import TAB, BRIDGE as BR, W, H
P = "/home/claude/t433lite/pcb/t433lite.kicad_pcb"
OX = OY = 100.0
mm = lambda v: int(round(v * 1e6))
V = lambda x, y: pcbnew.VECTOR2I(mm(x + OX), mm(y + OY))
u = lambda v: v / 1e6
b = pcbnew.LoadBoard(P)
NETS = b.GetNetsByName()
def padof(ref, num="1"):
    return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
JOBS = []
USUN = set()
for a in sys.argv[1:]:
    if a.startswith("--usun="):
        USUN = set(a[7:].split(","))
        for t in list(b.GetTracks()):
            if t.GetNetname() in USUN: b.Delete(t)
        continue
    q = a.split(":"); s1, s2 = q[0].split("."), q[1].split(".")
    JOBS.append((padof(*s1), padof(*s2), float(q[2]) if len(q) > 2 else 0.127, float(q[3]) if len(q) > 3 else None))
RNETS = {j[0].GetNetname() for j in JOBS}
# ---------- 4. siatka przeszkod ----------
RES, CLR, HCLR, ECLR = 0.025, 0.15, 0.22, 0.3
LAYS = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LCOST = [1.0, 50.0, 2.0, 1.2]
x0, y0, x1, y1 = TAB["x0"] - 0.1, -0.1, W + 0.1, H + 0.1
nx, ny = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
X, Y = np.meshgrid(x0 + np.arange(nx) * RES, y0 + np.arange(ny) * RES, indexing="ij")
D = np.full((4, nx, ny), 99.0, np.float32)
PADX = {n: np.full((4, nx, ny), 99.0, np.float32) for n in RNETS}
def seg_dist(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    if L2 < 1e-12: return np.hypot(X - ax, Y - ay)
    t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
    return np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
def rect_dist(l, t, r, bt):
    return np.hypot(np.maximum(np.maximum(l - X, 0), X - r), np.maximum(np.maximum(t - Y, 0), Y - bt))
def obst(lay, d, net=None):
    tg = [D] if net not in RNETS else [A for n, A in PADX.items() if n != net]
    for T in tg:
        for li in (range(4) if lay == "all" else [LAYS.index(lay)]): np.minimum(T[li], d, out=T[li])
def obst_track(lay, ax, ay, bx, by, w, net=None):
    if max(ax, bx) < x0 - 1 or min(ax, bx) > x1 + 1 or max(ay, by) < y0 - 1 or min(ay, by) > y1 + 1: return
    obst("all" if lay == "via" else lay, seg_dist(ax, ay, bx, by) - w / 2, net)
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); obst_track("via", u(p.x) - OX, u(p.y) - OY, u(p.x) - OX, u(p.y) - OY, u(t.GetWidth()), t.GetNetname())
    elif t.GetLayer() in LAYS:
        s, e = t.GetStart(), t.GetEnd()
        obst_track(t.GetLayer(), u(s.x) - OX, u(s.y) - OY, u(e.x) - OX, u(e.y) - OY, u(t.GetWidth()), t.GetNetname())
def obst_pad(p):
    bb = p.GetBoundingBox(); l, tp, r, bt = u(bb.GetLeft()) - OX, u(bb.GetTop()) - OY, u(bb.GetRight()) - OX, u(bb.GetBottom()) - OY
    if r < x0 - 1 or l > x1 + 1 or bt < y0 - 1 or tp > y1 + 1: return
    if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
        c = p.GetPosition(); obst("all", np.hypot(X - (u(c.x) - OX), Y - (u(c.y) - OY)) - u(p.GetDrillSize().x) / 2 - HCLR + CLR); return
    if p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
        c = p.GetPosition(); d = np.hypot(X - (u(c.x) - OX), Y - (u(c.y) - OY)) - u(p.GetSize().x) / 2
    else:
        d = rect_dist(l, tp, r, bt)
    th = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
    n = p.GetNetname()
    for li, L in enumerate(LAYS):
        if th or p.IsOnLayer(L):
            for nn_, A in PADX.items():
                if nn_ != n: np.minimum(A[li], d, out=A[li])
            if n not in RNETS: np.minimum(D[li], d, out=D[li])
for f in b.GetFootprints():
    for p in f.Pads(): obst_pad(p)
rects = [(0, 0, W, H), (-3.0, BR["y0"], 2.0, BR["y1"]), (TAB["x0"], TAB["y0"], TAB["x1"], TAB["y1"])]
inside = np.max([np.minimum.reduce([X - a, c - X, Y - bb_, dd - Y]) for a, bb_, c, dd in rects], axis=0)
EDGE = (inside - ECLR + CLR).astype(np.float32)
for li in range(4): np.minimum(D[li], EDGE, out=D[li])
D[1] = -99; D[2] = -99          # plytka 2-warstwowa

# obszary zakazu sciezek (prostokaty z ewentualnymi prostokatnymi otworami)
for z in b.Zones():
    if not (z.GetIsRuleArea() and z.GetDoNotAllowTracks()): continue
    o = z.Outline(); bb = o.Outline(0).BBox()
    m = (X >= u(bb.GetLeft()) - OX) & (X <= u(bb.GetRight()) - OX) & (Y >= u(bb.GetTop()) - OY) & (Y <= u(bb.GetBottom()) - OY)
    for h in range(o.HoleCount(0)):
        hb = o.Hole(0, h).BBox()
        m &= ~((X > u(hb.GetLeft()) - OX) & (X < u(hb.GetRight()) - OX) & (Y > u(hb.GetTop()) - OY) & (Y < u(hb.GetBottom()) - OY))
    for li, L in enumerate(LAYS):
        if z.GetLayerSet().Contains(L): D[li][m] = -1
# odleglosc od dowolnego pola SMD (przelotka nie moze wchodzic w pole, takze tej samej sieci)
SMD = np.full((nx, ny), 99.0, np.float32)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD: continue
        bb = p.GetBoundingBox()
        np.minimum(SMD, rect_dist(u(bb.GetLeft()) - OX, u(bb.GetTop()) - OY, u(bb.GetRight()) - OX, u(bb.GetBottom()) - OY), out=SMD)
def cell(x, y): return int(round((x - x0) / RES)), int(round((y - y0) / RES))
# ---------- 6. trasowanie A* ----------
def route(net, sp, gp, w, clr=None):
    clr = clr or CLR
    Dn = np.minimum(D, PADX[net])
    ok = Dn >= w / 2 + clr - 1e-6
    via_ok = np.all(Dn[[0, 3]] >= 0.3 + CLR - 1e-6, axis=0) & (EDGE >= 0.3 + CLR) & (SMD >= 0.3 + 0.1)
    sc = sp.GetPosition(); gc = gp.GetPosition()
    si, sj = cell(u(sc.x) - OX, u(sc.y) - OY); gi, gj = cell(u(gc.x) - OX, u(gc.y) - OY)
    on = lambda p, li, L: p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH or p.IsOnLayer(L)
    starts = [(li, si, sj) for li, L in enumerate(LAYS) if on(sp, li, L)]
    goals = {(li, gi, gj) for li, L in enumerate(LAYS) if on(gp, li, L)}
    h = lambda i, j: math.hypot(i - gi, j - gj) * RES
    dist = {}; prev = {}; pq = []
    for s in starts: dist[s] = 0.0; heapq.heappush(pq, (h(s[1], s[2]), 0.0, s))
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    while pq:
        f_, g, uu = heapq.heappop(pq)
        if g > dist.get(uu, 1e9): continue
        if uu in goals:
            path = [uu]
            while uu in prev: uu = prev[uu]; path.append(uu)
            return path[::-1]
        l, i, j = uu
        for di, dj in dirs:
            a, c = i + di, j + dj
            if not (0 <= a < nx and 0 <= c < ny) or not ok[l, a, c]: continue
            v = (l, a, c); ng = g + math.hypot(di, dj) * RES * LCOST[l] * (1 + 1.0 * (Dn[l, a, c] < w / 2 + CLR + 0.1))
            if ng < dist.get(v, 1e9): dist[v] = ng; prev[v] = uu; heapq.heappush(pq, (ng + h(a, c), ng, v))
        if via_ok[i, j]:
            for l2 in (0, 3):
                if l2 != l and ok[l2, i, j]:
                    v = (l2, i, j); ng = g + 1.5
                    if ng < dist.get(v, 1e9): dist[v] = ng; prev[v] = uu; heapq.heappush(pq, (ng + h(i, j), ng, v))
    return None

def commit(path, net, w):
    nn = NETS[net]; P_ = [(x0 + i * RES, y0 + j * RES, l) for (l, i, j) in path]
    segs = []; vias = []; st = P_[0]
    for k in range(1, len(P_)):
        a, c = P_[k - 1], P_[k]
        if c[2] != a[2]:
            if (st[0], st[1]) != (a[0], a[1]): segs.append((st, a))
            vias.append(a); st = c; continue
        if k + 1 < len(P_) and P_[k + 1][2] == c[2]:
            d1 = (round((c[0] - a[0]) / RES), round((c[1] - a[1]) / RES)); n_ = P_[k + 1]
            if d1 == (round((n_[0] - c[0]) / RES), round((n_[1] - c[1]) / RES)): continue
        segs.append((st, c)); st = c
    for v in vias:
        o = pcbnew.PCB_VIA(b); o.SetPosition(V(v[0], v[1])); o.SetWidth(mm(0.6)); o.SetDrill(mm(0.3))
        o.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); o.SetNet(nn); b.Add(o)
        obst_track("via", v[0], v[1], v[0], v[1], 0.6, net)
    for s, e in segs:
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(s[0], s[1])); t.SetEnd(V(e[0], e[1])); t.SetWidth(mm(w))
        t.SetLayer(LAYS[s[2]]); t.SetNet(nn); b.Add(t)
        obst_track(LAYS[s[2]], s[0], s[1], e[0], e[1], w, net)
    return len(segs), len(vias)

def padof(ref, num="1"):
    return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
def nearest_pad(net, src, exclude):
    c = src.GetPosition(); best = None
    for f in b.GetFootprints():
        if f.GetReference() in exclude: continue
        for p in f.Pads():
            if p.GetNetname() != net: continue
            q = p.GetPosition(); d = math.hypot(q.x - c.x, q.y - c.y)
            if best is None or d < best[0]: best = (d, p)
    return best[1]

for sp, gp, w, clr in JOBS:
    net = sp.GetNetname()
    path = route(net, sp, gp, w, clr)
    if path is None: print("NIE UDALO SIE", sp.GetNetname()); sys.exit(1)
    print(net, "segm/przel", commit(path, net, w))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
b = pcbnew.LoadBoard(P)
pcbnew.WriteDRCReport(b, "/home/claude/t433lite/pcb/drc.txt", pcbnew.EDA_UNITS_MILLIMETRES, True)
print("zapisano")
