"""Même échangeur et même ventilateur à l'intérieur et à l'extérieur : est-ce que ça tient ?

Idée : un seul « module » (batterie + ventilateur) monté deux fois. Il est dimensionné pour le cas
le plus dur côté extérieur à 2 500 m³/h, tous modes confondus (avec les Te, Tc actuels de la fiche : la clim,
≈ 1 100 W/K ; voir pac_9000btu.html).
Les deux côtés ont alors le même circuit d'air : seul le régime du ventilateur change.

Hypothèses :
* hA du module ∝ débit^0,6 (exposant du simulateur pac_fenetre), à géométrie fixe ;
* besoins de chaque côté recalculés avec les mêmes Te, Tc et puissances que la fiche échangeur
  (conception_echangeur/outils/analytique/fiche_pac_9000.py), en faisant varier le débit d'air ;
* ventilateur : la pale de départ de 500 mm (3 pales larges, anneau, diffuseur, stator), puissance
  calculée par le modèle de conception_ventilateur/animation_ventilateur.html (node).

Lancer : .venv/bin/python conception_ventilateur/outils/module_commun.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(RACINE / "conception_echangeur/outils/analytique"))
import fiche_pac_9000 as fp  # noqa: E402

EXPOSANT = 0.6
Q_REF, DP_REF = 2500.0, 25.0          # point de dimensionnement du module (extérieur, −8,3 °C)
VENT = dict(D=500, nu=0.30, N=3, corde=250, beta=34, faucille=20, jeu=2, anneau="labyrinthe", diffuseur=True,
            stator=True, ba="lisse", bf="dentele", profil="basRe", moteur="foc", givre=1)


def hA_requis(pt, cote, V):
    froid = fp.POINTS[pt["k"]]["mode"] == "froid"
    humide = (cote == "int") == froid
    a = pt["ai"] if cote == "int" else pt["ae"]
    if humide:
        b = fp.batterie_humide(a, V, pt["Qe"], pt["c"]["Te"])
    else:
        b = fp.batterie_seche(a, V, pt["Qc"], pt["c"]["Tc"])
    return b["hA"], b


def calculer():
    R = fp.calculer()
    # module dimensionné sur le besoin extérieur le plus fort à 2 500 m³/h (tous modes confondus)
    hA_ref = max(p["b_ext"]["hA"] for p in R["pts"].values())
    lignes = []
    for k, pt in R["pts"].items():
        pt["k"] = k
        for cote in ("int", "ext"):
            V_fiche = pt["Vi"] if cote == "int" else pt["Ve"]
            V = None
            for v in range(200, 4001, 10):                # plus petit débit où le module suffit
                req, b = hA_requis(pt, cote, v)
                if req and hA_ref * (v / Q_REF) ** EXPOSANT >= req:
                    V = v
                    break
            req_f, _ = hA_requis(pt, cote, V_fiche)
            lignes.append(dict(point=fp.POINTS[k]["nom"], cote=cote, V_fiche=V_fiche, hA_fiche=req_f, V=V,
                               T_out=b["T_out"] if V and "T_out" in b else None,
                               hA_dispo=hA_ref * (V / Q_REF) ** EXPOSANT if V else None))
    return hA_ref, lignes


def puissances(debits):
    html = (RACINE / "conception_ventilateur/animation_ventilateur.html").read_text(encoding="utf-8")
    js = html[html.index("// ===== MODELE (début) ====="):html.index("// ===== MODELE (fin) =====")]
    cas = {str(q): dict(VENT, Qnom=q, dpNom=DP_REF * (q / Q_REF) ** 1.8) for q in debits}  # même circuit d'air
    js += ("\nconst CAS = " + json.dumps(cas) + "; const out = {};\n"
           "for (const [k, p] of Object.entries(CAS)) { p.n = vitessePourDebit(p); const r = pointFonctionnement(p);"
           " out[k] = {n: p.n, Pel: r.Pel, eta: r.eta, ut: r.ut, Re: r.Re, dB: r.dB}; }\nconsole.log(JSON.stringify(out));")
    res = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=120, check=True)
    return json.loads(res.stdout)


if __name__ == "__main__":
    hA_ref, L = calculer()
    P = puissances(sorted({l["V"] for l in L if l["V"]} | {l["V_fiche"] for l in L}))
    print(json.dumps(dict(hA_ref=hA_ref, lignes=L, ventilateur=P), ensure_ascii=False, indent=1, default=float))
