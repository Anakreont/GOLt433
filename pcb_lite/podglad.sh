#!/bin/bash
# podglad.sh warstwy plik.png
kicad-cli pcb export svg --layers "$1" --page-size-mode 2 --exclude-drawing-sheet -o /tmp/p.svg pcb/t433lite.kicad_pcb >/dev/null 2>&1
python3 -c "import cairosvg; cairosvg.svg2png(url='/tmp/p.svg', write_to='$2', output_width=${3:-900}, background_color='white')"
