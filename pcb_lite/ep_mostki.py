# laczy 9 czesci pola centralnego ESP32-S3-MINI-1U (pad 61) sciezkami 0,4 mm na F.Cu
import pcbnew, sys
P = "/home/claude/t433lite/pcb/t433lite.kicad_pcb"
b = pcbnew.LoadBoard(P)
f = b.FindFootprintByReference("U1"); c = f.GetPosition(); g = b.GetNetsByName()["GND"]
d = 1650000
for i in (-1, 0, 1):
    for (x1, y1, x2, y2) in [(-d, i * d, d, i * d), (i * d, -d, i * d, d)]:
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(c.x + x1, c.y + y1)); t.SetEnd(pcbnew.VECTOR2I(c.x + x2, c.y + y2))
        t.SetWidth(400000); t.SetLayer(pcbnew.F_Cu); t.SetNet(g); t.SetLocked(True); b.Add(t)
pcbnew.SaveBoard(P, b)
