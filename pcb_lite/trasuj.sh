#!/bin/bash
# buduje plytke bez stref zewnetrznych, trasuje Freeroutingiem, importuje, wylewa strefy, DRC
cd /home/claude/t433lite
python3 buduj.py > /tmp/b.log 2>&1 || { cat /tmp/b.log; exit 1; }
python3 -c "
import pcbnew
b=pcbnew.LoadBoard('pcb/t433lite.kicad_pcb'); pcbnew.ExportSpecctraDSN(b,'pcb/t433lite.dsn')"
python3 dsn_fix.py pcb/t433lite.dsn
cd pcb && rm -f t433lite.ses && timeout 590 xvfb-run -a java -jar /tmp/freerouting.jar -de t433lite.dsn -do t433lite.ses -mp ${1:-50} > /tmp/fr19.out 2>&1; cd ..
cp pcb/t433lite.ses /tmp/last.ses
python3 buduj.py --strefy > /dev/null 2>&1
python3 import_drc.py /tmp/last.ses 2>&1 | grep -v "memory leak"
grep -E "^\*\* Found" pcb/drc.txt
grep -E "^\[" pcb/drc.txt | sed 's/\]:.*/]/' | sort | uniq -c | sort -rn | grep -v "lib_footprint\|silk\|courtyard\|text_height"
grep -A4 "^\[unconnected\|^\[clearance\|^\[hole\|^\[copper_edge\|^\[solder_mask\|^\[shorting" pcb/drc.txt | grep "@" | cut -c1-110
