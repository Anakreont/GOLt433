#!/bin/bash
cd /home/claude/t433lite
python3 -c "
import pcbnew
b=pcbnew.LoadBoard('pcb/t433lite.kicad_pcb'); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard('pcb/t433lite.kicad_pcb',b)
b=pcbnew.LoadBoard('pcb/t433lite.kicad_pcb')
pcbnew.WriteDRCReport(b,'pcb/drc.txt',pcbnew.EDA_UNITS_MILLIMETRES,True)" 2>&1 | grep -v leak
grep -E "^\*\* Found" pcb/drc.txt
grep -E "^\[" pcb/drc.txt | sed 's/\]:.*/]/' | sort | uniq -c | grep -v "lib_footprint\|silk_overlap\|silk_edge\|silk_over"
grep -A4 "^\[unconnected\|^\[clearance\|^\[hole\|^\[copper_edge\|^\[solder_mask\|^\[shorting\|^\[items_not\|^\[tracks_cross\|^\[starved" pcb/drc.txt | grep "@\|^\[" | cut -c1-120 | head -${1:-40}
