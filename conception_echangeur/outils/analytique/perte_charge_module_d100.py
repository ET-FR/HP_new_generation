#!/usr/bin/env python3
"""
Perte de charge du propane à travers un module cylindrique Ø 100 (outils/cad/echangeur_d100.py),
variantes 16 tubes (couronne) et 32 tubes (tournesol).

Chemin d'un circuit : tube 3/8" (40 mm) → arbre de Murray niveau 1 … n → tube d'échange (402 mm)
→ arbre de regroupement n … 1 → tube 3/8" (40 mm). Longueurs des branches recalculées à partir des
mêmes trajets que le modèle FreeCAD (dimensions.json de chaque variante).

Point de fonctionnement et corrélations : ceux de outils/analytique/charge_propane.py
(évaporation 10 °C, condensation 46 °C, sous-refroidissement 4 K, surchauffe 5 K ;
Müller-Steinhagen et Heck en diphasique, 64/Re ou Blasius en monophasique).
Hypothèses propres au module :
  * axe horizontal, pas de terme de gravité ; accélération (changement de phase) négligée ;
  * évaporateur : arbre d'entrée diphasique au titre d'entrée, tubes 85 % diphasiques + 15 %
    surchauffe, arbre de sortie en vapeur ;
  * condenseur (même sens de circulation) : arbre d'entrée en vapeur surchauffée, tubes 12 % vapeur
    + 78 % diphasique + 10 % liquide, arbre de sortie en liquide ;
  * pertes singulières : K = 1 par division ou regroupement, sur la pression dynamique de la branche
    fille (masse volumique homogène). Ordre de grandeur, pas de corrélation diphasique fine.
La puissance d'un module n'est pas connue : résultats donnés pour plusieurs puissances.

    .venv/bin/python conception_echangeur/outils/analytique/perte_charge_module_d100.py   → docs/formes/cylindre_d100*/perte_charge.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "outils/analytique"))
sys.path.insert(0, str(RACINE / "outils/cad"))
import charge_propane as cp  # noqa: E402
import tournesol  # noqa: E402

VARIANTES = {"16 tubes, couronne": RACINE / "docs/formes/cylindre_d100",
             "32 tubes, tournesol": RACINE / "docs/formes/cylindre_d100_t32"}
Q_EVAP_MODULE = [250.0, 500.0, 1000.0, 2300.0]   # W de froid par module (2 300 W = toute la PAC)
K_JONCTION = 1.0


def longueurs_branches(d):
    """Longueur moyenne (m) des branches de chaque niveau 1..n, mêmes trajets que le modèle CAO."""
    p = d["parametres"]
    n = len(p["id_murray"]) - 1
    R = p["r_couronne"]
    tour = p.get("disposition") == "tournesol"
    N = 200

    def lg(pts):
        return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    res = {}
    # niveau 1 : de l'axe vers la couronne
    dz = p["dz_niveau1"]
    res[1] = lg([(R * tournesol.y_doux(i / N), 0.0, dz * i / N) for i in range(N + 1)])
    for k in range(2, n + 1):
        if tour and k == n:
            continue
        dth, dz = math.pi / 2 ** k, p["dz_niveaux"]
        res[k] = lg([(R * math.cos(dth * tournesol.y_doux(i / N)), R * math.sin(dth * tournesol.y_doux(i / N)),
                      dz * i / N) for i in range(N + 1)])
    if tour:
        th = {(0, 0): 0.0}
        for k in range(1, n):
            for j in range(2 ** k):
                th[(k, j)] = j * math.pi if k == 1 else th[(k - 1, j // 2)] + (-1 if j % 2 == 0 else 1) * math.pi / 2 ** k
        nd = [(R * math.cos(th[(n - 1, j)]), R * math.sin(th[(n - 1, j)])) for j in range(2 ** (n - 1))]
        paires, _ = tournesol.feuilles_tournesol(nd, *p["r_tournesol"])
        br = tournesol.branches(paires, nd, 0.0, p["dz_dernier"])
        res[n] = float(np.mean([tournesol.longueur(b["points"]) for b in br]))
    return {k: v * 1e-3 for k, v in res.items()}


def etat(nom, mode):
    """Propriétés d'un tronçon : ('di', x0, x1) diphasique, 'vap' ou 'liq'."""
    return cp.sat(cp.TE if mode == "evap" else cp.TC)


def dp_troncon(m, D, L, phase, p, x0=None, x1=None):
    """Perte par frottement (Pa) d'un tronçon de diamètre D, longueur L, débit m (kg/s)."""
    A = math.pi * D ** 2 / 4
    G = m / A
    if phase == "di":
        xs = np.linspace(x0, x1, 100)
        return float(np.mean(cp.dpdz_diphasique(xs, G, D, p))) * L, G
    rho, mu = (p["rv"], p["mv"]) if phase == "vap" else (p["rl"], p["ml"])
    return cp.frottement_mono(G, D, mu) / rho * L, G


def rho_homogene(phase, p, x=None):
    if phase == "vap":
        return p["rv"]
    if phase == "liq":
        return p["rl"]
    return 1 / (x / p["rv"] + (1 - x) / p["rl"])


def module(d, Q_evap, mode):
    p_geo = d["parametres"]
    ids = [x * 1e-3 for x in p_geo["id_murray"]]
    n = len(ids) - 1
    Lb = longueurs_branches(d)
    L_tube = d["longueur_tubes_mm"] * 1e-3
    L_38 = p_geo["l_tube_entree"] * 1e-3
    s = cp.sat(cp.TE if mode == "evap" else cp.TC)
    if mode == "evap":
        h_in = cp.sat(cp.TC - 4)["hl"]
        x_in = (h_in - s["hl"]) / (s["hv"] - s["hl"])
        m = Q_evap / (s["hv"] + 2300 * 5 - h_in)
        amont, aval = ("di", x_in), ("vap", None)
        tubes = [(0.85, "di", x_in, 1.0), (0.15, "vap", None, None)]
    else:
        Q = Q_evap * cp.Q_COND / cp.Q_EVAP
        m = Q / (s["hv"] + 2600 * 25 - (s["hl"] - 2600 * 4))
        amont, aval = ("vap", None), ("liq", None)
        tubes = [(0.12, "vap", None, None), (0.78, "di", 1.0, 0.0), (0.10, "liq", None, None)]

    postes = {}

    def arbre(cote, phase, x):
        frott, sing = 0.0, 0.0
        # tube 3/8"
        frott += dp_troncon(m, ids[0], L_38, phase, s, x, x)[0]
        for k in range(1, n + 1):
            mk = m / 2 ** k
            dpk, G = dp_troncon(mk, ids[k], Lb[k], phase, s, x, x)
            frott += dpk
            sing += K_JONCTION * G ** 2 / (2 * rho_homogene(phase, s, x))
        postes[f"arbre {cote} (frottement)"] = frott
        postes[f"arbre {cote} (divisions)"] = sing

    arbre("entrée", *amont)
    mt = m / 2 ** n
    dpt = 0.0
    for frac, phase, x0, x1 in tubes:
        dpt += dp_troncon(mt, ids[n], frac * L_tube, phase, s, x0, x1)[0]
    postes["tubes"] = dpt
    arbre("sortie", *aval)
    total = sum(postes.values())
    G_tube = mt / (math.pi * ids[n] ** 2 / 4)
    return dict(Q_evap_W=Q_evap, debit_g_s=1e3 * m, G_tubes_kg_m2s=G_tube,
                postes_Pa={k: round(v, 1) for k, v in postes.items()},
                total_kPa=total / 1e3, dT_sat_K=total / s["dPdT"])


def main():
    tout = {}
    for nom, dossier in VARIANTES.items():
        d = json.loads((dossier / "dimensions.json").read_text())
        res = {mode: [module(d, Q, mode) for Q in Q_EVAP_MODULE] for mode in ("evap", "cond")}
        res["longueurs_branches_mm"] = {k: round(v * 1e3, 1) for k, v in longueurs_branches(d).items()}
        (dossier / "perte_charge.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
        tout[nom] = res
        print(f"\n=== {nom} — branches (mm) : {res['longueurs_branches_mm']}")
        for mode, titre in (("evap", "évaporateur 10 °C"), ("cond", "condenseur 46 °C")):
            print(f"  {titre}")
            for r in res[mode]:
                pt = r["postes_Pa"]
                print(f"    Q froid {r['Q_evap_W']:6.0f} W | {r['debit_g_s']:5.2f} g/s | G tubes {r['G_tubes_kg_m2s']:6.1f} "
                      f"| Δp {r['total_kPa']*1e3:8.0f} Pa = {r['dT_sat_K']:.3f} K | tubes {pt['tubes']:.0f}, "
                      f"arbres {sum(v for k, v in pt.items() if 'arbre' in k):.0f} Pa")


if __name__ == "__main__":
    main()
