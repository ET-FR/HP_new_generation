#!/usr/bin/env python3
"""
Étude de convergence en maillage par l'indice de convergence de maillage (GCI), procédure de
Celik et al. (ASME J. Fluids Eng. 130, 2008), sur trois maillages (grossier, moyen, fin).

Pour chaque grandeur φ : rapports de raffinement r = (N_fin / N_moyen)^(1/2) en 2D, ordre
apparent p (résolution itérative), valeur extrapolée φ_ext (Richardson), erreurs relatives et
GCI_fin = 1,25 |(φ_fin - φ_moyen) / φ_fin| / (r_21^p - 1).
Le GCI n'a de sens qu'en convergence monotone (0 < R < 1, R = e21 / e32) ; sinon le régime
est signalé et l'ordre p, la valeur extrapolée et le GCI ne doivent pas être utilisés.

    python convergence.py cas_grossier cas_moyen cas_fin [--json sortie.json]
(chaque dossier doit contenir cas.json et resultat.json produits par creer_cas.py / extraire.py)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

GRANDEURS = {"dp_Pa": "perte de charge Δp (Pa)", "Nu_D6": "Nu sur Ø 6 mm",
             "T_sortie": "température de sortie (efficacité)", "h": "h (W/m²·K)"}


def gci(phi3, phi2, phi1, N3, N2, N1, dim=2):
    """phi1 = fin, phi2 = moyen, phi3 = grossier. Retourne un dictionnaire de résultats."""
    r21 = (N1 / N2) ** (1 / dim)
    r32 = (N2 / N3) ** (1 / dim)
    e21, e32 = phi2 - phi1, phi3 - phi2
    if e21 == 0 or e32 == 0:
        return dict(p=float("nan"), monotone=False, R=float("nan"), regime="identique")
    R = e21 / e32                        # Celik : 0 < R < 1 convergence monotone (asymptotique)
    regime = ("monotone" if 0 < R < 1 else "oscillante" if R < 0 else
              "non asymptotique (l'écart grandit avec le raffinement)")
    s = math.copysign(1, e32 / e21)
    p = 2.0
    for _ in range(100):
        q = math.log((r21 ** p - s) / (r32 ** p - s))
        p_nouv = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(p_nouv - p) < 1e-8:
            break
        p = p_nouv
    ext = (r21 ** p * phi1 - phi2) / (r21 ** p - 1)
    ea21 = abs((phi1 - phi2) / phi1)
    return dict(r21=r21, r32=r32, R=R, regime=regime, p=p, monotone=0 < R < 1, phi_ext=ext,
                ecart_fin_moyen=ea21, ecart_fin_extrapole=abs((ext - phi1) / ext),
                GCI_fin=1.25 * ea21 / (r21 ** p - 1),
                GCI_moyen=1.25 * abs((phi2 - phi3) / phi2) / (r32 ** p - 1))


def etude(grossier, moyen, fin):
    cas = [Path(c) for c in (grossier, moyen, fin)]
    meta = [json.loads((c / "cas.json").read_text()) for c in cas]
    res = [json.loads((c / "resultat.json").read_text()) for c in cas]
    N = [m["maillage"]["cellules"] for m in meta]
    sortie = dict(cellules=dict(grossier=N[0], moyen=N[1], fin=N[2]), grandeurs={})
    for k, nom in GRANDEURS.items():
        v = [r[k] for r in res]
        g = gci(v[0], v[1], v[2], N[0], N[1], N[2])
        g.update(nom=nom, grossier=v[0], moyen=v[1], fin=v[2])
        sortie["grandeurs"][k] = g
    return sortie


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("grossier"); ap.add_argument("moyen"); ap.add_argument("fin")
    ap.add_argument("--json")
    a = ap.parse_args()
    e = etude(a.grossier, a.moyen, a.fin)
    print(f"cellules : {e['cellules']}")
    for k, g in e["grandeurs"].items():
        print(f"{g['nom']:40s} {g['grossier']:9.4f} {g['moyen']:9.4f} {g['fin']:9.4f}  "
              f"p={g['p']:.2f}  extrapolé={g.get('phi_ext', float('nan')):9.4f}  "
              f"GCI fin={100 * g.get('GCI_fin', float('nan')):.2f} %  GCI moyen={100 * g.get('GCI_moyen', float('nan')):.2f} %"
              f"  R={g.get('R', float('nan')):.2f} : {g.get('regime')}")
    if a.json:
        Path(a.json).write_text(json.dumps(e, indent=1, ensure_ascii=False))
