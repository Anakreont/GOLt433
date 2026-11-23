import re,sys
p=sys.argv[1]; s=open(p).read()
PWR=["VSC","BB_L1","BB_L2","GPS_VCC","CAM_3V3"]
a=s.index("(class kicad_default"); b=s.index("(circuit",a)
names=s[a+len('(class kicad_default ""'):b].split()
keep=[n for n in names if n not in PWR]
s=s[:a]+'(class kicad_default "" '+" ".join(keep)+"\n      "+s[b:]
s=s.replace("(class PWR\n","(class PWR "+" ".join(PWR)+"\n")
s=s.replace("(width 400)","(width 300)")
s=s.replace("(clearance 120.1)","(clearance 120.1)")
s=s.replace('(layer In1.Cu\n      (type power)','(layer In1.Cu\n      (type signal)')
# sieci w.cz. prowadzi osobno polacz.py (0,19 mm, odstep 0,25) - wyrzuc je z DSN
for rf in ("LORA_ANT", "GPS_ANT"):
    i = s.find("(net %s\n" % rf)
    if i >= 0:
        j = s.index(")\n", s.index("(pins", i)); j = s.index(")", j + 2) + 1
        s = s[:i] + s[j:]
    s = re.sub(r"(\(class [^\n]*?) %s( |\n)" % rf, r"\1\2", s)
open(p,'w').write(s)
