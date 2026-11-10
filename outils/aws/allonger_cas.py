#!/usr/bin/env python3
"""Allonge la durée simulée de cas pas encore lancés : la fenêtre de moyenne est multipliée par
(1 + FACTEUR). Idempotent : se base sur fin_initiale si elle existe.
    python3 allonger_cas.py FACTEUR cas1 cas2 ...
"""
import json
import re
import sys

facteur = float(sys.argv[1])
for c in sys.argv[2:]:
    m = json.load(open(f"{c}/cas.json"))
    f0 = m.get("fin_initiale", m["fin"])
    m["fin_initiale"] = f0
    m["fin"] = round(f0 + facteur * (f0 - m["debut_moyenne"]), 4)
    json.dump(m, open(f"{c}/cas.json", "w"), indent=1, ensure_ascii=False)
    cd = open(f"{c}/system/controlDict").read()
    cd = re.sub(r"^endTime\s+[^;]+;", "endTime         %g;" % m["fin"], cd, flags=re.M)
    cd = re.sub(r"^writeInterval\s+[^;]+;", "writeInterval   %g;" % (m["fin"] / 4), cd, flags=re.M)
    open(f"{c}/system/controlDict", "w").write(cd)
    print(f"{c:17s} fin {f0} -> {m['fin']} s (moyenne à partir de {m['debut_moyenne']} s)")
