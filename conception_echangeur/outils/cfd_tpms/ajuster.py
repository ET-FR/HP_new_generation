#!/usr/bin/env python3
"""
Ajuste des corrélations côté air j = a·Re^-b et f = c·Re^-d par surface TPMS (et porosité)
à partir des resultats.csv de la campagne CFD, et les écrit pour le simulateur :

    python conception_echangeur/outils/cfd_tpms/ajuster.py cfd_campagne/resultats.csv
        -> pac_fenetre/donnees/correlations_air_tpms.json

f est le frottement APPARENT sur la profondeur simulée (entrée, sortie et zone
d'établissement comprises) : à utiliser avec Kc = Ke = 0 et pour des profondeurs
proches de celle de la campagne (profondeur_mm dans le JSON).
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE.parent / "pac_fenetre" / "donnees" / "correlations_air_tpms.json"


def loi_puissance(Re, y):
    """Moindres carrés en log : y = a Re^-b. Retourne (a, b, R², écart relatif max)."""
    X, Y = [math.log(r) for r in Re], [math.log(v) for v in y]
    n = len(X)
    mx, my = sum(X) / n, sum(Y) / n
    sxx = sum((x - mx) ** 2 for x in X)
    pente = sum((x - mx) * (yy - my) for x, yy in zip(X, Y)) / sxx if sxx else 0.0
    a, b = math.exp(my - pente * mx), -pente
    pred = [a * r ** -b for r in Re]
    ss_res = sum((math.log(v) - math.log(p)) ** 2 for v, p in zip(y, pred))
    ss_tot = sum((yy - my) ** 2 for yy in Y)
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return a, b, r2, max(abs(p / v - 1) for v, p in zip(y, pred))


def main(fichiers):
    lignes = []
    for f in fichiers:
        with open(f) as fh:
            lignes += list(csv.DictReader(fh))
    groupes = defaultdict(list)
    for l in lignes:
        if l["termine"] != "True":
            continue
        groupes[(l["surface"], round(float(l["phi_air"]), 2))].append(l)

    existant = json.loads(SORTIE.read_text()) if SORTIE.exists() else {}
    corr = existant.get("correlations", {})
    for (surface, phi), ls in sorted(groupes.items()):
        ls.sort(key=lambda l: float(l["Re"]))
        Re = [float(l["Re"]) for l in ls]
        j = [float(l["j"]) for l in ls]
        f = [float(l["f"]) for l in ls]
        if len(Re) < 2:
            print(f"{surface} φ={phi}: un seul point, pas d'ajustement")
            continue
        aj, bj, r2j, ej = loi_puissance(Re, j)
        af, bf, r2f, ef = loi_puissance(Re, f)
        cle = f"{surface}_phi{phi:.2f}"
        corr[cle] = dict(
            surface=surface, phi_air=phi, profondeur_mm=float(ls[0]["profondeur_mm"]),
            Dh_mm=float(ls[0]["Dh_mm"]), Re_min=min(Re), Re_max=max(Re),
            j=dict(a=aj, b=bj, R2=r2j, ecart_max=ej), f=dict(a=af, b=bf, R2=r2f, ecart_max=ef),
            maillage=dict(finesse=int(ls[0]["finesse"]), raffinement=int(ls[0]["raffinement"])),
            points=[dict(Re=r, j=jj, f=ff) for r, jj, ff in zip(Re, j, f)])
        print(f"{cle:22s} j = {aj:.4f}·Re^-{bj:.3f} (R² {r2j:.3f}, écart max {ej:.1%})   "
              f"f = {af:.4f}·Re^-{bf:.3f} (R² {r2f:.3f}, écart max {ef:.1%})   Re {min(Re):.0f}–{max(Re):.0f}")

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(dict(
        source="CFD OpenFOAM v2412, outils/cfd_tpms (cellule périodique en section, profondeur réelle, "
               "air Pr 0,71, paroi isotherme ; laminaire Re ≤ 300, k-ω SST au-delà)",
        date=date.today().isoformat(), correlations=corr), indent=1, ensure_ascii=False))
    print(f"-> {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["resultats.csv"])
