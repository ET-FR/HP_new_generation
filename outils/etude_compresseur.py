"""
Étude du compresseur : quelle part du COP il coûte, quels rendements il faut
pour viser un COP de 5 à 6, quelle cylindrée choisir.

    python outils/etude_compresseur.py            # tableaux Markdown sur la sortie
    python outils/etude_compresseur.py -o docs/resultats_compresseur.md

Toutes les comparaisons sont faites à PUISSANCE FIXÉE (la fréquence est
cherchée par la régulation du simulateur), sinon un compresseur plus gros
paraîtrait meilleur ou moins bon simplement parce qu'il fournit plus.

Le compresseur est le modèle GÉNÉRIQUE du simulateur (rotatif BLDC). Les
valeurs absolues dépendent de ses hypothèses (forme de η_is(PR, f), η_mot(f),
fuites) ; ce sont les tendances et les ordres de grandeur qui comptent tant
qu'aucune carte constructeur n'est chargée.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pac_fenetre.physique import Conception, Conditions, PompeAChaleur, Propane  # noqa: E402

FL = Propane()

# (libellé, conditions, puissance sensible demandée en W)
POINTS = [
    ("Chauffage 7/20, 1,6 kW", Conditions("chauffage", 7, 20, 0.87, 0.5), 1600.0),
    ("Chauffage 7/20, 3,2 kW", Conditions("chauffage", 7, 20, 0.87, 0.5), 3200.0),
    ("Chauffage 2/20, 2,5 kW", Conditions("chauffage", 2, 20, 0.84, 0.5), 2500.0),
    ("Clim 35/27, 1,5 kW sens.", Conditions("clim", 35, 27, 0.40, 0.47), 1500.0),
    ("Clim 35/27, 2,6 kW sens.", Conditions("clim", 35, 27, 0.40, 0.47), 2600.0),
]

# Variante « échangeurs et ventilation améliorés » (voir README, objectif)
AMELIOREE = dict(UA_int_ref=520 * 1.5 ** 0.6, UA_ext_ref=840 * 1.5 ** 0.6,
                 debit_int_nom=780, debit_ext_nom=1950, P_vent_int_nom=42, P_vent_ext_nom=82)


def point(conc: Conception, cond: Conditions, Q: float):
    """État à puissance fixée (None si hors plage de modulation)."""
    pac = PompeAChaleur(conc, FL)
    f, _, statut = pac.regulation(cond, Q)
    if statut != "modulation":
        return None, statut
    e = pac.resoudre(cond, f)
    return (pac, e) if e.ok else (None, "non convergé")


def eta_global(e) -> float:
    """Puissance isentropique / puissance électrique compresseur (η_is·η_mot·η_var)."""
    return e.W_arbre * e.eta_is / e.P_comp


def eta_requis(e, cop_cible: float) -> float:
    """η global du compresseur qui donnerait cop_cible, cycle (Te, Tc, débit) figé.

    P_tot = P_comp + (ventilateurs + veille). On garde le reste identique et on
    cherche P_comp, d'où η = P_isentropique / P_comp. Approximation : en
    chauffage, un compresseur meilleur cède un peu moins de chaleur au
    condenseur, l'effet est de second ordre.
    """
    P_annexe = e.P_tot - e.P_comp
    P_comp = e.Q_utile / cop_cible - P_annexe
    return float("inf") if P_comp <= 0 else e.W_arbre * e.eta_is / P_comp


def fmt(x, n=2):
    return "n.d." if x is None or x != x else (f"{x:.{n}f}" if x != float("inf") else "impossible")


def tableau(entetes, lignes):
    out = ["| " + " | ".join(entetes) + " |", "|" + "---|" * len(entetes)]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in lignes]
    return "\n".join(out)


def section_etat(base: Conception) -> str:
    lignes = []
    for lab, cond, Q in POINTS:
        pac, e = point(base, cond, Q)
        if pac is None:
            lignes.append([lab] + ["hors plage (" + e + ")"] + [""] * 8)
            continue
        cas = dict(pac.cascade_pertes(cond, e))
        perte = 1 - cas["moteur"] / cas["cycle"]
        lignes.append([lab, f"{e.freq:.0f}", f"{e.Te:.1f} / {e.Tc:.1f}", fmt(e.PR), fmt(e.eta_v),
                       fmt(e.eta_is), fmt(e.eta_mot), fmt(eta_global(e)),
                       f"{100 * perte:.0f} %", fmt(e.COP)])
    return tableau(["Point", "f (tr/s)", "Te / Tc (°C)", "PR", "η_v", "η_is", "η_mot",
                    "η global", "COP perdu par le compresseur", "COP unité"], lignes)


def section_balayage(base: Conception, champ: str, valeurs, fmt_val=str, debits_fixes=False) -> str:
    """debits_fixes : ventilateurs à leur débit nominal quelle que soit la
    fréquence (sinon ils suivent la fréquence du compresseur, ce qui mélange
    l'effet du compresseur et celui de la ventilation)."""
    entetes = [champ] + [lab for lab, _, _ in POINTS]
    lignes = []
    for v in valeurs:
        conc = replace(base, **{champ: v})
        l = [fmt_val(v)]
        for _, cond, Q in POINTS:
            if debits_fixes:
                cond = replace(cond, debit_int=conc.debit_int_nom, debit_ext=conc.debit_ext_nom)
            pac, e = point(conc, cond, Q)
            l.append("hors plage" if pac is None else f"{e.COP:.2f} ({e.freq:.0f})")
        lignes.append(l)
    return tableau(entetes, lignes)


def section_cylindree(base: Conception, valeurs) -> str:
    """Puissance mini (f_min) et maxi (f_max) en chauffage 7/20 et -7/20."""
    lignes = []
    for v in valeurs:
        pac = PompeAChaleur(replace(base, cylindree_cm3=v), FL)
        c7 = Conditions("chauffage", 7, 20, 0.87, 0.5)
        cm7 = Conditions("chauffage", -7, 20, 0.87, 0.5)
        qmin = pac.resoudre(c7, pac.c.f_min).Q_sensible
        qmax7 = pac.resoudre(cm7, pac.c.f_max).Q_sensible
        lignes.append([f"{v:g}", f"{qmin / 1e3:.2f}", f"{qmax7 / 1e3:.2f}"])
    return tableau(["Cylindrée (cm³)", "P mini à 7 °C, f_min (kW)", "P maxi à -7 °C, f_max (kW)"], lignes)


def section_requis(base: Conception, cibles=(5.0, 5.5, 6.0)) -> str:
    lignes = []
    for nom, conc in (("actuels", base), ("améliorés", replace(base, **AMELIOREE))):
        for lab, cond, Q in POINTS:
            pac, e = point(conc, cond, Q)
            if pac is None:
                continue
            lignes.append([lab, nom, fmt(eta_global(e)), fmt(e.COP)]
                          + [fmt(eta_requis(e, c)) for c in cibles])
    return tableau(["Point", "Échangeurs", "η global actuel", "COP actuel"]
                   + [f"η requis COP {c:g}" for c in cibles], lignes)


def rapport() -> str:
    base = Conception()
    parties = [
        "# Étude du compresseur (résultats générés)\n",
        "Généré par `python outils/etude_compresseur.py`. Compresseur générique du "
        "simulateur, puissance fixée par la régulation.\n",
        "## 1. État actuel aux points de référence\n",
        "« COP perdu par le compresseur » : écart entre le cycle réel avec "
        "compression isentropique et le COP après compression et moteur "
        "(cascade de pertes du simulateur).\n",
        section_etat(base),
        "\n## 2. η global requis pour un COP cible\n",
        "η global = η_is · η_mot · η_var. Cycle figé (approximation). "
        "« améliorés » : UA x2, débits d'air x1,5 (voir README).\n",
        section_requis(base),
        "\n## 3. Sensibilité au rendement isentropique maximal\n",
        "COP unité (fréquence en tr/s entre parenthèses).\n",
        section_balayage(base, "eta_is_max", [0.65, 0.70, 0.72, 0.75, 0.78, 0.82], lambda v: f"{v:.2f}"),
        "\n## 4. Sensibilité au rendement moteur maximal\n",
        section_balayage(base, "eta_mot_max", [0.90, 0.935, 0.95, 0.965], lambda v: f"{v:.3f}"),
        "\n## 5. Cylindrée\n",
        "Le modèle générique garde le meilleur rendement à 55 tr/s (η_is) et "
        "70 tr/s (moteur) quelle que soit la cylindrée : la tendance dépend de "
        "cette hypothèse, à confirmer sur des cartes réelles.\n",
        "Ventilateurs asservis à la fréquence (régulation actuelle du simulateur) :\n",
        section_balayage(base, "cylindree_cm3", [10, 12, 14, 16, 20, 24], lambda v: f"{v:g}"),
        "\nVentilateurs à débit nominal fixe (effet du compresseur seul) :\n",
        section_balayage(base, "cylindree_cm3", [10, 12, 14, 16, 20, 24], lambda v: f"{v:g}",
                         debits_fixes=True),
        "\nPlage de modulation (f_min = 15 tr/s, f_max = 110 tr/s) :\n",
        section_cylindree(base, [10, 12, 14, 16, 20, 24]),
        "",
    ]
    return "\n".join(parties)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--sortie", help="fichier Markdown de sortie")
    a = ap.parse_args()
    texte = rapport()
    if a.sortie:
        with open(a.sortie, "w", encoding="utf-8") as f:
            f.write(texte)
        print("écrit :", a.sortie)
    else:
        print(texte)
