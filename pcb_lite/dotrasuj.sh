#!/bin/bash
# kolejny przebieg Freeroutingu na juz poprowadzonej plytce (tylko brakujace polaczenia)
cd /home/claude/t433lite
python3 -c "
import pcbnew
b=pcbnew.LoadBoard('pcb/t433lite.kicad_pcb')
import sys
usun=set('$2'.split(',')) if '$2' else set()
for t in list(b.GetTracks()):
    if t.GetNetname() in usun: b.Delete(t)
    else: t.SetLocked(True)
for z in list(b.Zones()):
    if z.GetIsRuleArea(): continue
    b.Remove(z)
pcbnew.ExportSpecctraDSN(b,'pcb/pass2.dsn')" 2>&1 | grep -v leak
python3 dsn_fix.py pcb/pass2.dsn
cd pcb && rm -f pass2.ses && timeout 590 xvfb-run -a java -jar /tmp/freerouting.jar -de pass2.dsn -do pass2.ses -mp ${1:-30} > /tmp/fr2.out 2>&1; cd ..
python3 import_drc.py pcb/pass2.ses 2>&1 | grep -v "memory leak"
grep -E "^\*\* Found" pcb/drc.txt
grep -E "^\[" pcb/drc.txt | sed 's/\]:.*/]/' | sort | uniq -c | sort -rn | grep -v "lib_footprint\|silk\|courtyard\|text_height"
grep -A4 "^\[unconnected\|^\[clearance\|^\[hole\|^\[copper_edge\|^\[solder_mask\|^\[shorting\|^\[tracks_crossing" pcb/drc.txt | grep "@" | cut -c1-110
