"""
Ajuste les 10 coefficients EN 12900 / AHRI 540 à partir d'un tableau de points.

Utile quand le constructeur fournit un tableau de performances (Te, Tc, vitesse,
débit, puissance) plutôt que les coefficients. Avec --synthetique, génère une
carte de test à partir du modèle générique (ce n'est PAS un vrai compresseur).

    python outils/ajuster_carte.py points.csv --nom "XYZ" --surchauffe 10 -o cartes/xyz.json
    python outils/ajuster_carte.py --synthetique -o cartes/SYNTHETIQUE_generique.json

CSV attendu (en-tête obligatoire, unités SI, températures de rosée) :
    Te_C,Tc_C,vitesse_tr_s,debit_kg_h,puissance_W
Au moins 10 points par vitesse, idéalement 20 ou plus répartis sur l'enveloppe.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def termes(S, D):
    return [1, S, D, S * S, S * D, D * D, S ** 3, S * S * D, S * D * D, D ** 3]


def ajuster(points):
    """points : [(S, D, X)] -> (coefficients, erreur relative max)."""
    A = np.array([termes(S, D) for S, D, _ in points], dtype=float)
    y = np.array([x for _, _, x in points], dtype=float)
    if len(y) < 10:
        raise ValueError("au moins 10 points par vitesse")
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    err = np.max(np.abs(A @ c - y) / np.maximum(np.abs(y), 1e-12))
    return c.tolist(), float(err)


def points_synthetiques():
    """Points du modèle générique, surchauffe 5 K, pour les tests."""
    from pac_fenetre.physique import Conception, PompeAChaleur
    pac = PompeAChaleur(Conception())
    c = pac.c
    lignes = []
    for f in (15.0, 30.0, 60.0, 90.0, 110.0):
        for S in np.arange(-20.0, 15.1, 2.5):
            for D in np.arange(25.0, 62.6, 2.5):
                if not 20.0 <= D - S <= 70.0:   # zone de fonctionnement réaliste
                    continue
                Te, Tc = S + c.dT_aspiration, D - c.dT_refoulement
                k = pac.compresseur(Te, Tc, f)
                P = k["m"] * k["w"] / k["eta_mot"]   # bornes compresseur
                lignes.append((S, D, f, k["m"] * 3600.0, P))
    return lignes, c


def enveloppe(lignes, synthetique):
    Ss, Ds = [l[0] for l in lignes], [l[1] for l in lignes]
    if synthetique:  # domaine ajusté : rectangle limité à 20 <= D - S <= 70 K
        s0, s1, d0, d1 = min(Ss), max(Ss), min(Ds), max(Ds)
        return [[s0, d0], [d0 - 20.0, d0], [s1, s1 + 20.0], [s1, d1], [d1 - 70.0, d1], [s0, s0 + 70.0]]
    return [[min(Ss), min(Ds)], [max(Ss), min(Ds)], [max(Ss), max(Ds)], [min(Ss), max(Ds)]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--synthetique", action="store_true")
    ap.add_argument("--nom", default="")
    ap.add_argument("--surchauffe", type=float, help="K, conditions de référence")
    ap.add_argument("--T-aspiration", type=float, help="°C, alternative à --surchauffe")
    ap.add_argument("--sous-refroid", type=float, default=0.0)
    ap.add_argument("--cylindree", type=float)
    ap.add_argument("--inclut-variateur", action="store_true")
    ap.add_argument("--source", default="")
    ap.add_argument("-o", "--sortie", required=True)
    a = ap.parse_args()

    if a.synthetique:
        lignes, c = points_synthetiques()
        nom = "SYNTHÉTIQUE : modèle générique du simulateur (pas un vrai compresseur)"
        ref = {"surchauffe_K": c.surchauffe, "T_aspiration_C": None,
               "sous_refroidissement_K": c.sous_refroid}
        cyl, source, inclut = c.cylindree_cm3, "outils/ajuster_carte.py --synthetique", False
    else:
        if not a.csv or (a.surchauffe is None and a.T_aspiration is None):
            ap.error("donner un CSV et --surchauffe ou --T-aspiration")
        with open(a.csv, encoding="utf-8") as f:
            lignes = [(float(r["Te_C"]), float(r["Tc_C"]), float(r["vitesse_tr_s"]),
                       float(r["debit_kg_h"]), float(r["puissance_W"])) for r in csv.DictReader(f)]
        nom = a.nom or os.path.basename(a.csv)
        ref = {"surchauffe_K": a.surchauffe, "T_aspiration_C": a.T_aspiration,
               "sous_refroidissement_K": a.sous_refroid}
        cyl, source, inclut = a.cylindree, a.source, a.inclut_variateur

    vitesses = sorted({l[2] for l in lignes})
    cm, cp = {}, {}
    for v in vitesses:
        pts = [l for l in lignes if l[2] == v]
        cm[str(v)], em = ajuster([(S, D, m) for S, D, _, m, _ in pts])
        cp[str(v)], ep = ajuster([(S, D, P) for S, D, _, _, P in pts])
        print(f"{v:6.1f} tr/s : {len(pts)} points, erreur max débit {em*100:.2f} %, puissance {ep*100:.2f} %")

    Ss, Ds = [l[0] for l in lignes], [l[1] for l in lignes]
    carte = {
        "nom": nom,
        "fluide": "R290",
        "source": source,
        "synthetique": bool(a.synthetique),
        "cylindree_cm3": cyl,
        "unites": {"temperature": "C", "debit_massique": "kg/h", "puissance": "W"},
        "reference": ref,
        "puissance_inclut_variateur": inclut,
        "enveloppe_Te_Tc_C": enveloppe(lignes, a.synthetique),
        "coefficients": {"debit_massique": cm, "puissance_electrique": cp},
    }
    with open(a.sortie, "w", encoding="utf-8") as f:
        json.dump(carte, f, indent=2, ensure_ascii=False)
    print("écrit :", a.sortie)
    if not a.synthetique:
        print("Remplacer l'enveloppe rectangulaire par celle de la fiche constructeur.")


if __name__ == "__main__":
    main()
