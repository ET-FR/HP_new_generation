#!/usr/bin/env python3
"""
PDF de synthèse des résultats CFD 2D : docs/resultats_cfd.pdf.

Relit docs/formes/<forme>/ (resultat.json, images) : à relancer quand de nouveaux résultats
sont rangés.

    python outils/cfd_2d/rapport_pdf.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
RACINE = Path(__file__).resolve().parents[2]
DOCS = RACINE / "docs"
FORMES = DOCS / "formes"
SORTIE = DOCS / "resultats_cfd.pdf"

NIVEAU1 = [("rond", "Rond"), ("carre", "Carré"), ("losange", "Losange"),
           ("triangle_pointe", "Triangle, pointe amont"), ("triangle_base", "Triangle, base amont"),
           ("ellipse2", "Ellipse 2:1"), ("ellipse3", "Ellipse 3:1"), ("plat4", "Tube plat 4:1"),
           ("goutte", "Goutte"), ("lentille", "Lentille")]
SERIE2 = [("naca0030", "Profil d'aile NACA 0030"), ("goutte_inversee", "Goutte inversée"),
          ("ellipse4", "Ellipse 4:1"), ("ellipse5", "Ellipse 5:1"), ("stade8", "Tube plat 8:1 arrondi"),
          ("hexagone_pointe", "Hexagone, pointe amont"), ("hexagone_plat", "Hexagone, plat amont"),
          ("demi_cercle_plat", "Demi-cercle, plat amont"), ("demi_cercle_rond", "Demi-cercle, arrondi amont"),
          ("etoile6", "Rond à 6 ailettes longit."), ("cannele12", "Rond cannelé (12 ondes)"),
          ("trois_canaux", "Multicanaux (3 canaux)")]
# Étape 1 : balayage en vitesse (10 novembre 2026)
BALAYAGE = [("rond", "Rond"), ("ellipse2", "Ellipse 2:1"), ("lentille", "Lentille 3:1"), ("ellipse4", "Ellipse 4:1")]
VITESSES = [0.5, 1.0, 2.0, 3.0]
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # ordre fixe, palette validée (CVD)
MARQUEURS = ["o", "s", "^", "D"]
A4 = (8.27, 11.69)
DT_REF = 10.0     # K, écart de température air / paroi de référence pour P vent / Q
LEGENDE = (
    "Conditions : batterie de 4 rangs en quinconce, air à 1 m/s en face, même charge de propane et même périmètre "
    "côté propane pour toutes les formes.\n"
    "Δp : perte de charge de l'air à travers la batterie ; fixe la puissance et le bruit du ventilateur.\n"
    "h : coefficient d'échange moyen côté air, par m² de surface extérieure des tubes.\n"
    "Efficacité : part de l'écart de température entre l'air entrant et la paroi récupérée par l'air en sortie ; "
    "à vitesse égale,\n    elle est proportionnelle à la chaleur échangée par m² de face.\n"
    f"P vent / Q : puissance de ventilation (Δp × débit) divisée par la chaleur échangée, pour un écart air / paroi de "
    f"{DT_REF:.0f} K ; plus c'est bas, mieux c'est.\n"
    "Prof. : profondeur de la batterie dans le sens de l'air (encombrement à charge égale).\n"
    "Stabilité : écart entre les moyennes de la 1re et de la 2e moitié du calcul (écoulement instationnaire) ; "
    "au-delà de ±2 %, le calcul est à prolonger.")
BLEU = "#1c3d6e"


def lire(chemin):
    p = FORMES / chemin
    return json.loads(p.read_text()) if p.exists() else None


def valeur(texte):
    """Nombre lu dans une cellule (« 27.5 % », « ± 0.1 % », « 3.32 ») ; None si ce n'en est pas un."""
    try:
        return float(str(texte).replace("±", "").replace("%", "").replace(",", ".").split()[0])
    except (ValueError, IndexError):
        return None


ROUGE, JAUNE, VERT = (0.973, 0.412, 0.420), (1.0, 0.922, 0.518), (0.388, 0.745, 0.482)


def couleur_degrade(x):
    """0 → rouge, 0,5 → jaune, 1 → vert, éclairci pour garder le texte lisible."""
    a, b, t = (ROUGE, JAUNE, 2 * x) if x < 0.5 else (JAUNE, VERT, 2 * x - 1)
    c = [a[k] + (b[k] - a[k]) * t for k in range(3)]
    return tuple(0.45 + 0.55 * v for v in c)


def bornes(lignes, col):
    """5e et 95e centiles de la colonne : une valeur extrême ne doit pas écraser l'échelle."""
    import numpy as np
    v = [valeur(l[col]) for l in lignes]
    v = [x for x in v if x is not None]
    return tuple(np.percentile(v, [5, 95])) if v else (0.0, 1.0)


def tableau(fig, y, entetes, lignes, largeurs, titre, taille=8.5, h_ligne=0.026, degrades=None):
    """Tableau placé sous l'ordonnée y (fraction de page) ; renvoie l'ordonnée sous le tableau.
    degrades : {colonne: sens} ; fond du rouge (mauvais) au vert (bon), échelle propre à ce tableau.
    sens = +1 : plus c'est grand, mieux c'est (chaleur) ; -1 : plus c'est petit, mieux c'est (Δp)."""
    sens = degrades or {}
    degrades = {c: bornes(lignes, c) for c in sens}
    fig.text(0.06, y, titre, fontsize=11, fontweight="bold", color=BLEU, va="top")
    h = h_ligne * (len(lignes) + 1)
    ax = fig.add_axes([0.06, y - 0.025 - h, 0.88, h]); ax.axis("off")
    t = ax.table(cellText=lignes, colLabels=entetes, colWidths=largeurs, cellLoc="center", bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False)
    t.set_fontsize(taille)
    for (r, c), cel in t.get_celld().items():
        cel.set_edgecolor("#ced4da")
        if r == 0:
            cel.set_facecolor(BLEU); cel.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cel.set_facecolor("#f1f3f5")
        if c == 0 and r > 0:
            cel.set_text_props(ha="left"); cel._loc = "left"
        if r > 0 and c in degrades:
            x = valeur(lignes[r - 1][c])
            lo, hi = degrades[c]
            if x is not None and hi > lo:
                t = min(1.0, max(0.0, (x - lo) / (hi - lo)))
                cel.set_facecolor(couleur_degrade(t if sens[c] > 0 else 1 - t))
    return y - 0.025 - h - 0.035


def conclusion(fig, y, lignes, titre="Conclusion"):
    """Encadré de conclusion placé sous l'ordonnée y ; renvoie l'ordonnée sous l'encadré."""
    h = 0.036 + 0.0150 * len(lignes)
    ax = fig.add_axes([0.05, y - h, 0.90, h]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#eef4fb", edgecolor="#9fbbe0", lw=0.8))
    fig.text(0.065, y - 0.008, titre, fontsize=10, fontweight="bold", color=BLEU, va="top")
    fig.text(0.065, y - 0.028, "\n".join(l if l.startswith(" ") else "• " + l for l in lignes), fontsize=7.8, va="top", color="#212529",
             linespacing=1.5)
    return y - h - 0.015


def pct(a, b):
    return f"{100 * (a / b - 1):+.1f} %"


def etat_vitesse():
    n = sum((FORMES / c / f"resultat_U{U:g}.json").exists() for c, _ in BALAYAGE for U in VITESSES if U != 1.0)
    total = len(BALAYAGE) * (len(VITESSES) - 1)
    return "fait" if n == total else f"en cours ({n} / {total})"


def page_introduction(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.955, "Échangeurs d'une PAC de fenêtre au propane", fontsize=17, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.933, f"Étude CFD côté air. Mis à jour le {date.today():%d/%m/%Y}.", fontsize=8.5, color="#495057")
    y = 0.90
    blocs = [
        ("But", [
            "Concevoir les deux échangeurs air / propane d'une pompe à chaleur de fenêtre réversible (chauffage et clim),",
            "au propane R290, imprimés en 3D, pour une pièce de 50 m² au plus. Cible : 8 000 BTU/h (≈ 2,3 kW).",
            "Contrainte forte : charge de propane ≤ 152 g (norme IEC 60335-2-40), dominée par le volume des échangeurs.",
            "Côté air se trouvent la plus grosse résistance thermique, le ventilateur et le bruit : c'est là qu'il faut",
            "trouver la meilleure forme de tube, celle qui échange le plus pour le moins de puissance de ventilation."]),
        ("Méthode", [
            "1. Comparer des formes simples en CFD 2D avec des règles d'équité strictes, pour comprendre ce qui compte.",
            "2. Construire une base de simulations, puis optimiser par optimisation bayésienne multi-objectif et",
            "    multi-fidélité (Ax / BoTorch) : simulateur de la PAC (rapide) → CFD 2D → CFD 3D (coûteuse).",
            "3. Objectifs finaux : COP (ou SCOP) maximal, charge minimale ; contraintes : encombrement de la fenêtre,",
            "    tenue à la pression, bruit, givre et condensats."]),
        ("Règles communes à tous les calculs", [
            "Même charge de propane et même périmètre de contact côté propane : canal intérieur de Dh = 4 mm, paroi 1 mm.",
            "Batterie de référence : 4 rangs en quinconce, pas transversal = 2 Ø extérieur du rond (ajusté à charge égale).",
            "Air à 20 °C, paroi à température imposée (propane en changement de phase), écoulement laminaire",
            "instationnaire, OpenFOAM v2606, maillage à couches validé en convergence."]),
    ]
    for titre, lignes in blocs:
        fig.text(0.06, y, titre, fontsize=11, fontweight="bold", color=BLEU, va="top")
        fig.text(0.06, y - 0.024, "\n".join(lignes), fontsize=8.3, va="top", color="#212529", linespacing=1.5)
        y -= 0.024 + 0.0168 * len(lignes) + 0.025
    etapes = [
        ["0", "Validation de la chaîne", "plaques, tube isolé, faisceau de ronds ; convergence en maillage", "fait"],
        ["1", "Forme du tube", "22 formes à 1 m/s, même charge", "fait"],
        ["1b", "Vitesse de l'air", "4 formes du meilleur compromis, 0,5 / 1 / 2 / 3 m/s", etat_vitesse()],
        ["2", "Agencement", "aligné / quinconce, pas, nombre de rangs (1, 2, 4, 8)", "fait"],
        ["3", "Ailettes et TPMS", "ailettes (plates, persiennées…), surfaces TPMS en 3D", "en cours"],
        ["4", "Base + optimisation", "plan d'expériences, puis optimisation bayésienne sur le cycle complet", "à faire"],
        ["5", "Validation physique", "prototype imprimé, essais d'échange, de givrage et de fuite", "à faire"],
    ]
    y = tableau(fig, y + 0.01, ["Étape", "Sujet", "Contenu", "État"], etapes, [0.08, 0.21, 0.53, 0.18],
                "Étapes", taille=7.8, h_ligne=0.026)
    fig.text(0.06, y + 0.015, "Dans ce document : validation et convergence (p. 2), comparaison des formes (p. 3), "
             "compromis (p. 4), influence de la vitesse,\npuis géométries et une page de champs (vitesse, température, "
             "pression) par cas.", fontsize=7.8, va="top", color="#495057", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)


def page_synthese(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Résultats CFD 2D côté air", fontsize=17, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.945, f"PAC de fenêtre R290, batterie air / propane. Mis à jour le {date.today():%d/%m/%Y}. "
             "OpenFOAM v2606, air 20 °C, laminaire, 1 m/s.", fontsize=8.5, color="#495057")

    pl, ti, rt = lire("plaques/resultat.json"), lire("tube_isole/resultat.json"), lire("rond/resultat_maillage_triangles.json")
    lignes = []
    if pl:
        r = pl["resultats"]
        lignes += [["Plaques parallèles", "f·Re", f"{r['fRe']:.2f}", "24 (exact)", pct(r["fRe"], 24)],
                   ["Plaques parallèles", "Nu", f"{r['Nu']:.3f}", "7,541 (exact)", pct(r["Nu"], 7.541)]]
    if rt:
        r = rt["resultats"]; z = r["zukauskas"]
        lignes += [["Faisceau tubes ronds", "Nu (Ø 6 mm)", f"{r['Nu_D6']:.2f}", "Zukauskas 11,3 à 15,5", "dans la fourchette"],
                   ["Faisceau tubes ronds", "Δp (Pa)", f"{r['dp_Pa']:.2f}", f"Zukauskas {z['dp_Pa']:.2f}", pct(r["dp_Pa"], z["dp_Pa"])]]
    if ti:
        r = ti["resultats"]
        lignes += [["Tube isolé", "Nu", f"{r['Nu']:.2f}", f"Hilpert {r['Nu_Hilpert']:.2f}", pct(r["Nu"], r["Nu_Hilpert"])],
                   ["Tube isolé", "Strouhal", f"{r['St']:.3f}", f"Roshko {r['St_Roshko']:.3f}", pct(r["St"], r["St_Roshko"])],
                   ["Tube isolé", "Cd", f"{r['Cd']:.2f}", "essais 1,1 à 1,2", "surestimé (2D)"]]
    y = tableau(fig, 0.925, ["Cas", "Grandeur", "CFD", "Référence", "Écart"], lignes,
            [0.27, 0.15, 0.13, 0.27, 0.18], "1. Validation (niveau 0) : la chaîne est validée")

    cv = lire("rond/convergence_couches.json")
    if cv:
        g = cv["grandeurs"]
        lignes = [["Δp (Pa)", f"{g['dp_Pa']['grossier']:.2f}", f"{g['dp_Pa']['moyen']:.2f}", f"{g['dp_Pa']['fin']:.2f}", "4,4 ± 2,5 %"],
                  ["Nu (Ø 6 mm)", f"{g['Nu_D6']['grossier']:.2f}", f"{g['Nu_D6']['moyen']:.2f}", f"{g['Nu_D6']['fin']:.2f}", "14,2 ± 1,5 %"]]
        n = cv["cellules"]
        y = tableau(fig, y,
                ["Grandeur", f"Grossier ({n['grossier']})", f"Moyen ({n['moyen']})", f"Fin ({n['fin']})", "Valeur retenue"],
                lignes, [0.22, 0.19, 0.19, 0.19, 0.21],
                "2. Convergence en maillage (tubes ronds, couches) : maillage moyen retenu")

    y = conclusion(fig, y + 0.01, [
        "Cas exacts (plaques) retrouvés à 0,3 % près : le solveur, les conditions aux limites et l'extraction sont justes.",
        "Faisceau de ronds : Nu dans la fourchette de Zukauskas, Δp 12 % sous l'abaque (écart habituel en 2D laminaire).",
        "Tube isolé : Nu et Strouhal 7 à 8 % au-dessus des références, Cd surestimé : effet connu du calcul 2D,",
        "    sans conséquence pour comparer des formes entre elles.",
        "Maillage moyen retenu : incertitude ± 2,5 % sur Δp, ± 1,5 % sur Nu. Un écart de moins de 5 % entre deux",
        "    formes n'est donc pas significatif."], "Conclusion de l'étape 0")
    fig.text(0.06, y, "La comparaison des formes est en page 3.", fontsize=9, color="#495057", va="top")
    pdf.savefig(fig); plt.close(fig)


def ligne_forme(cle, nom):
    d = lire(f"{cle}/resultat.json")
    if d and d.get("parametres", {}).get("couches"):
        r = d["resultats"]
        return [nom, f"{r['dp_Pa']:.2f}", f"{r['h']:.1f}", f"{100 * r['T_sortie']:.1f} %",
                f"{r['P_vent_sur_Q'] / DT_REF * 1e3:.2f}", f"{r['profondeur_mm']:.0f}",
                f"± {100 * max(r['stabilite_moyenne'].values()):.1f} %"], True
    return [nom, "en cours", "", "", "", "", ""], False


def page_comparaison(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Comparaison des formes de tubes", fontsize=15, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.945, "Même charge de propane et même périmètre côté propane pour toutes les formes.",
             fontsize=8.5, color="#495057")
    entetes = ["Forme (même charge R290)", "Δp (Pa)", "h (W/m²K)", "Efficacité", "P vent / Q (‰)",
               "Prof. (mm)", "Stabilité"]
    largeurs = [0.27, 0.10, 0.11, 0.12, 0.14, 0.13, 0.13]
    y = 0.925
    for titre, liste in (("Série 1", NIVEAU1), ("Série 2", SERIE2)):
        res = [ligne_forme(c, n) for c, n in liste]
        n_ok = sum(ok for _, ok in res)
        y = tableau(fig, y, entetes, [l for l, _ in res], largeurs,
                    f"{titre} : {n_ok} / {len(liste)} calculées", taille=7.8, h_ligne=0.022,
                    degrades={1: -1, 3: +1})
    fig.text(0.06, y + 0.02, LEGENDE + "\nCouleurs : du rouge (moins bien) au vert (mieux), chaque tableau sur sa propre échelle ; "
             "Efficacité : vert = plus de chaleur ; Δp : vert = moins de perte de charge.",
             fontsize=7.3, va="top", color="#343a40", linespacing=1.45)
    pdf.savefig(fig); plt.close(fig)


def page_compromis(pdf):
    """Efficacité contre P vent / Q pour toutes les formes à 1 m/s ; front de Pareto en évidence."""
    pts = []
    for cle, nom in NIVEAU1 + SERIE2:
        d = lire(f"{cle}/resultat.json")
        if d and d.get("parametres", {}).get("couches"):
            r = d["resultats"]
            pts.append((r["P_vent_sur_Q"] / DT_REF * 1e3, 100 * r["T_sortie"], nom))
    if len(pts) < 3:
        return
    pareto = [p for p in pts if not any(q[0] <= p[0] and q[1] >= p[1] and q != p for q in pts)]
    pareto.sort()
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Compromis échange / ventilation des 22 formes", fontsize=15, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.95, "Air à 1 m/s, même charge de propane. En haut à gauche : meilleur.\n"
             "En bleu, le front de Pareto : aucune autre forme ne fait mieux sur les deux critères à la fois.",
             fontsize=8, color="#495057", va="top", linespacing=1.4)
    ax = fig.add_axes([0.11, 0.40, 0.83, 0.50])
    autres = [p for p in pts if p not in pareto]
    ax.scatter([p[0] for p in autres], [p[1] for p in autres], s=30, color="#adb5bd", edgecolor="white", lw=0.6,
               zorder=2, label="autres formes")
    ax.plot([p[0] for p in pareto], [p[1] for p in pareto], color="#2a78d6", lw=1.6, marker="o", ms=6,
            mec="white", mew=0.8, zorder=3, label="front de Pareto")
    decalage = {"Hexagone, plat amont": (-4, 6, "right"), "Hexagone, pointe amont": (0, -11, "center"),
                "Losange": (4, 5, "left"), "Profil d'aile NACA 0030": (-5, -3, "right"),
                "Tube plat 4:1": (-4, -10, "right"), "Goutte inversée": (5, 3, "left"),
                "Ellipse 3:1": (5, 3, "left"), "Goutte": (5, -4, "left"), "Lentille": (-5, 4, "right"),
                "Ellipse 4:1": (-5, 4, "right"), "Ellipse 5:1": (-5, 4, "right"),
                "Tube plat 8:1 arrondi": (5, -9, "left"), "Rond à 6 ailettes longit.": (-6, 4, "right")}
    for x, yv, nom in pts:
        dx, dy, ha = decalage.get(nom, (5, 3, "left"))
        ax.annotate(nom, (x, yv), xytext=(dx, dy), textcoords="offset points", fontsize=6.3, ha=ha,
                    color="#212529" if (x, yv, nom) in pareto else "#6c757d")
    from matplotlib.ticker import FuncFormatter, NullFormatter
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}")); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([0.2, 0.5, 1, 2, 5, 10])
    ax.set_xlabel("P vent / Q (‰, pour 10 K d'écart air / paroi) : plus bas = moins de ventilateur", fontsize=8)
    ax.set_ylabel("Efficacité (%) : plus haut = plus de chaleur par m² de face", fontsize=8)
    ax.tick_params(labelsize=7.5); ax.grid(True, color="#e9ecef", lw=0.6)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    fig.text(0.06, 0.34, "Lecture : les formes rondes échangent le plus sur peu de profondeur mais coûtent en ventilation ;\n"
             "les formes allongées divisent la puissance de ventilation par 4 à 6 mais échangent 2 à 2,5 fois moins par m² de face.\n"
             "Le rond à ailettes a beaucoup plus de surface côté air : c'est déjà un tube à ailettes (à comparer plus tard aux ailettes).",
             fontsize=7.8, va="top", color="#343a40", linespacing=1.5)
    conclusion(fig, 0.27, [
        "Deux familles : formes compactes (rond, hexagones, losange) à 25 à 27 % d'efficacité mais P vent / Q de 1,3 à 2 ‰ ;",
        "    formes allongées (ellipses 3:1 à 5:1, lentille, tubes plats) à 11 à 17 % mais 0,2 à 0,4 ‰.",
        "Le rond est la meilleure forme compacte : il échange le plus pour la plus faible ventilation de sa famille, sur 37 mm.",
        "L'ellipse 2:1 est le meilleur intermédiaire : 25 % de chaleur en moins que le rond, 54 % de ventilation en moins.",
        "Faces plates ou arêtes face à l'air (triangle base amont, demi-cercle plat amont, carré) : nettement moins bonnes.",
        "Les formes allongées demandent une batterie 1,6 à 3 fois plus profonde à charge égale (60 à 113 mm).",
        "Retenues pour la suite (front de Pareto) : rond, ellipse 2:1, lentille 3:1, ellipse 4:1."], "Conclusion de l'étape 1")
    pdf.savefig(fig); plt.close(fig)


def resultat_vitesse(cle, U):
    d = lire(f"{cle}/resultat.json" if U == 1.0 else f"{cle}/resultat_U{U:g}.json")
    return d["resultats"] if d and abs(d["parametres"]["U"] - U) < 1e-9 else None


def page_vitesse(pdf):
    res = {c: {U: resultat_vitesse(c, U) for U in VITESSES} for c, _ in BALAYAGE}
    if not any(r for c in res for U, r in res[c].items() if U != 1.0 and r):
        return
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Étape 1 : influence de la vitesse de l'air", fontsize=15, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.945, "4 formes du meilleur compromis, 0,5 à 3 m/s en face, même batterie (4 rangs, même charge).",
             fontsize=8.5, color="#495057")
    axes = [fig.add_axes([0.08 + k * 0.31, 0.70, 0.25, 0.20]) for k in range(3)]
    for (cle, nom), col, mk in zip(BALAYAGE, COULEURS, MARQUEURS):
        pts = [(U, r) for U, r in res[cle].items() if r]
        if not pts:
            continue
        Us = [U for U, _ in pts]
        st = dict(color=col, marker=mk, ms=4.5, lw=1.6, label=nom, mec="white", mew=0.6)
        axes[0].plot(Us, [r["h"] for _, r in pts], **st)
        axes[1].plot(Us, [r["dp_Pa"] for _, r in pts], **st)
        # chaleur par m² de face pour 10 K d'écart air / paroi : ρ cp U ε ΔT (kW/m²), comparable entre vitesses
        q_face = [1.2 * 1006 * U * r["T_sortie"] * DT_REF / 1e3 for U, r in pts]
        axes[2].plot([r["P_vent_sur_Q"] / DT_REF * 1e3 for _, r in pts], q_face, **st)
    for ax, xl, yl, t in ((axes[0], "vitesse (m/s)", "h (W/m²K)", "Coefficient d'échange"),
                          (axes[1], "vitesse (m/s)", "Δp (Pa)", "Perte de charge"),
                          (axes[2], "P vent / Q (‰, 10 K)", "Q par m² de face (kW/m², 10 K)", "Compromis (vitesse libre)")):
        ax.set_xlabel(xl, fontsize=7.5); ax.set_ylabel(yl, fontsize=7.5); ax.set_title(t, fontsize=9)
        ax.tick_params(labelsize=7); ax.grid(True, color="#e9ecef", lw=0.6)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    from matplotlib.ticker import FuncFormatter, NullFormatter
    axes[1].set_yscale("log"); axes[2].set_xscale("log")
    for ax, axe in ((axes[1], "yaxis"), (axes[2], "xaxis")):
        getattr(ax, axe).set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        getattr(ax, axe).set_minor_formatter(NullFormatter())
    axes[2].set_xticks([0.1, 0.2, 0.5, 1, 2, 5, 10])
    axes[0].legend(fontsize=7, frameon=False, loc="upper left")
    lignes = []
    for cle, nom in BALAYAGE:
        for U in VITESSES:
            r = res[cle][U]
            if r is None:
                lignes.append([nom, f"{U:g}", "en cours", "", "", "", "", "", ""]); continue
            z = r.get("zukauskas", {})
            lignes.append([nom, f"{U:g}", f"{r['Re_max_D6']:.0f}", f"{r['dp_Pa']:.2f}", f"{r['h']:.1f}",
                           f"{100 * r['T_sortie']:.1f} %", f"{1.2 * 1006 * U * r['T_sortie'] * DT_REF / 1e3:.2f}",
                           f"{r['P_vent_sur_Q'] / DT_REF * 1e3:.2f}",
                           f"± {100 * max(r['stabilite_moyenne'].values()):.1f} %"
                           + (f"  (Δp Zuk. {100 * z['ecart_dp']:+.0f} %)" if "ecart_dp" in z else "")])
    y = tableau(fig, 0.63, ["Forme", "U (m/s)", "Re max", "Δp (Pa)", "h (W/m²K)", "Efficacité", "Q face (kW/m²)",
                            "P vent / Q (‰)", "Stabilité"], lignes,
                [0.12, 0.07, 0.08, 0.09, 0.10, 0.10, 0.12, 0.12, 0.20],
                "Résultats", taille=6.9, h_ligne=0.021, degrades={3: -1, 6: +1})
    fig.text(0.06, y + 0.02, "Re max : nombre de Reynolds sur la vitesse maximale entre tubes et le Ø 6 mm du rond. "
             "Au-delà de Re ≈ 1 000, l'écoulement réel devient\n3D et turbulent dans les sillages : le calcul 2D "
             "laminaire est alors moins fiable (tendance correcte, valeurs à confirmer en 3D).\n"
             "Δp Zuk. : écart aux abaques de Zukauskas (tubes ronds seulement). Q face : chaleur par m² de face "
             "(10 K d'écart air / paroi) ; Q face et Δp colorés du rouge au vert ;\nl'efficacité baisse avec la vitesse alors que la "
             "chaleur augmente, c'est donc Q face qui compare les vitesses entre elles.",
             fontsize=7.3, va="top", color="#343a40", linespacing=1.45)
    conclusion(fig, y - 0.065, [
        "Quand la vitesse est libre, le rond donne le plus de chaleur par m² de face pour un même coût de ventilation",
        "    (graphique de droite) ; l'ellipse 2:1 le suit de près (5 % en dessous), la lentille et l'ellipse 4:1 sont derrière.",
        "Exemple : le rond à 0,5 m/s échange 2,3 kW/m² pour 0,26 ‰, mieux que l'ellipse 4:1 à 1 m/s (1,8 kW/m² pour 0,30 ‰).",
        "Ralentir l'air est donc plus efficace qu'allonger le tube ; l'avantage des formes allongées à 1 m/s venait surtout",
        "    de la vitesse plus faible entre les tubes. Elles ne gardent l'avantage que pour des P vent / Q très bas (< 0,2 ‰).",
        "Le prix d'une vitesse faible est une grande surface de face, fixée par la fenêtre. Au-delà de 2 m/s : à confirmer en 3D."],
        "Conclusion de l'étape 1b")
    pdf.savefig(fig); plt.close(fig)


# Niveau 2 : agencement (10 novembre 2026), rond et ellipse 2:1 à 1 m/s
NIVEAU2_FORMES = [("rond", "Rond"), ("ellipse2", "Ellipse 2:1")]
NIVEAU2 = [("rangs1", "1 rang"), ("rangs2", "2 rangs"), ("rangs8", "8 rangs"), ("pt0.75", "Pt × 0,75"),
           ("pt1.25", "Pt × 1,25"), ("pt1.5", "Pt × 1,5"), ("pl0.6", "Pl × 0,6"), ("pl1.5", "Pl × 1,5"),
           ("aligne", "Aligné"), ("aligne_pt0.75", "Aligné, Pt × 0,75")]


def q_face(r, U):
    """Chaleur par m² de face pour 10 K d'écart air / paroi (kW/m²)."""
    return 1.2 * 1006 * U * r["T_sortie"] * DT_REF / 1e3


def page_niveau2(pdf):
    res = {}
    for cle, _ in NIVEAU2_FORMES:
        for tag, _ in [("ref", "")] + NIVEAU2:
            d = lire(f"{cle}/resultat.json" if tag == "ref" else f"{cle}/resultat_N2_{tag}.json")
            if d:
                res[cle, tag] = d
    if not any(t != "ref" for _, t in res):
        return
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Niveau 2 : agencement de la batterie", fontsize=15, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.95, "Rond et ellipse 2:1, air à 1 m/s. Référence : 4 rangs en quinconce, Pt = 2 Ø (rond), "
             "Pl = Pt √3 / 2.\nLa charge de propane par m² de face varie ici comme rangs / Pt : colonne « Charge ».",
             fontsize=8, color="#495057", va="top", linespacing=1.4)
    axes = [fig.add_axes([0.08 + k * 0.31, 0.765, 0.25, 0.115]) for k in range(3)]
    series = [("rangs", [("rangs1", 1), ("rangs2", 2), ("ref", 4), ("rangs8", 8)], "nombre de rangs"),
              ("pt", [("pt0.75", 0.75), ("ref", 1.0), ("pt1.25", 1.25), ("pt1.5", 1.5)], "Pt / Pt référence"),
              ("pl", [("pl0.6", 0.6), ("ref", 1.0), ("pl1.5", 1.5)], "Pl / Pl référence")]
    for ax, (_, pts, xl) in zip(axes, series):
        for (cle, nom), col, mk in zip(NIVEAU2_FORMES, COULEURS, MARQUEURS):
            xy = [(x, q_face(res[cle, t]["resultats"], 1.0)) for t, x in pts if (cle, t) in res]
            if xy:
                ax.plot(*zip(*xy), color=col, marker=mk, ms=4.5, lw=1.6, mec="white", mew=0.6, label=nom)
        ax.set_xlabel(xl, fontsize=7.5); ax.set_title("Q par m² de face", fontsize=9)
        ax.tick_params(labelsize=7); ax.grid(True, color="#e9ecef", lw=0.6)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_ylabel("kW/m² (10 K)", fontsize=7.5); axes[0].set_xticks([1, 2, 4, 8])
    axes[0].legend(fontsize=7, frameon=False, loc="upper left")
    lignes = []
    for cle, nom in NIVEAU2_FORMES:
        for tag, titre in [("ref", "Référence (4 rangs)")] + NIVEAU2:
            d = res.get((cle, tag))
            if not d:
                lignes.append([nom, titre, "en cours", "", "", "", "", "", "", "", ""]); continue
            r, m = d["resultats"], d["parametres"]
            charge = m["rangs"] / 4 / m.get("pt_facteur", 1.0)
            lignes.append([nom, titre, f"{r['Re_max_D6']:.0f}", f"{r['dp_Pa']:.2f}", f"{r['h']:.1f}",
                           f"{100 * r['T_sortie']:.1f} %", f"{r['P_vent_sur_Q'] / DT_REF * 1e3:.2f}",
                           f"{r['profondeur_mm']:.0f}", f"{charge:.2f}", f"{q_face(r, m['U']) / charge:.2f}",
                           f"± {100 * max(r['stabilite_moyenne'].values()):.1f} %"])
    y = tableau(fig, 0.715, ["Forme", "Agencement", "Re max", "Δp (Pa)", "h (W/m²K)", "Efficacité",
                            "P vent / Q (‰)", "Prof. (mm)", "Charge", "Q / charge", "Stabilité"], lignes,
                [0.09, 0.15, 0.07, 0.07, 0.09, 0.09, 0.10, 0.08, 0.07, 0.09, 0.10], "Résultats",
                taille=6.5, h_ligne=0.0178, degrades={3: -1, 5: +1, 9: +1})
    fig.text(0.06, y + 0.02, "Mêmes grandeurs que les autres tableaux (Δp, h, efficacité, P vent / Q, profondeur, "
             "stabilité : voir la légende de la page de comparaison des formes).\n"
             "Re max : Reynolds sur la vitesse maximale entre tubes et le Ø 6 mm du rond.\n"
             "Charge : charge de propane par m² de face, relative à la référence (1 = 4 rangs, Pt de référence).\n"
             "Q / charge : chaleur par m² de face (kW/m², 10 K d'écart air / paroi) divisée par la charge relative "
             "\n(Δp, efficacité et Q / charge colorés du rouge au vert) ; Q / charge est le critère qui compte si la charge de 152 g "
             "est la contrainte limitante.",
             fontsize=7, va="top", color="#343a40", linespacing=1.45)
    conclusion(fig, y - 0.058, [
        "La quinconce s'impose : en aligné, la chaleur chute de 43 % (rond) et de 27 % (ellipse 2:1) à charge égale.",
        "Resserrer les tubes en largeur (Pt × 0,75) donne le plus de chaleur par gramme de propane (+ 20 % pour le rond),",
        "    mais la ventilation par kW monte de 46 % : intéressant si la charge limite, pas si le bruit limite.",
        "Moins de rangs utilise mieux le propane (2 rangs : + 13 %) mais demande 2 fois plus de surface de face.",
        "Le pas en profondeur (Pl) change peu la chaleur ; Pl × 0,6 amincit la batterie (37 → 25 mm), + 37 % de ventilation.",
        "L'ellipse 2:1 ventile partout 2 fois moins par kW que le rond, pour 20 à 25 % de chaleur par gramme en moins.",
        "Cas instables corrigés (11/11) : ellipse Pl × 1,5 moyennée après son régime transitoire (dès 0,85 s), rond",
        "    Pl × 1,5 dès 0,5 s, 3 cas prolongés. Ellipse Pt × 1,5 reste à ± 2,4 % : bouffées irrégulières, valeurs inchangées."],
        "Conclusion de l'étape 2")
    pdf.savefig(fig); plt.close(fig)


# Étape 3 : ailettes plates (outils/cfd_3d/creer_cas_ailettes.py), CFD 3D stationnaire
AILETTES = [("rond", "Rond", "", "nus"), ("rond", "Rond", "_ail1.8", "1,8 mm"),
            ("rond", "Rond", "_ail1.8_t20", "1,8 mm, 20 tranches"), ("rond", "Rond", "_ail1.8_t40", "1,8 mm, 40 tranches"),
            ("rond", "Rond", "_ail2.5", "2,5 mm"), ("rond", "Rond", "_ail1.8_r2", "1,8 mm, 2 rangs"),
            ("ellipse2", "Ellipse 2:1", "", "nus"), ("ellipse2", "Ellipse 2:1", "_ail1.8", "1,8 mm"),
            ("ellipse2", "Ellipse 2:1", "_ail1.8_r2", "1,8 mm, 2 rangs")]


def page_ailettes(pdf):
    if not lire("rond/resultat_ail1.8.json"):
        return
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Étape 3 : tubes à ailettes plates (CFD 3D)", fontsize=15, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.95, "Mêmes tubes et même charge de propane que les tubes nus (4 rangs en quinconce, Pt = 12 mm), "
             "air à 1 m/s en façade.\nAilettes de 0,2 mm sur toute la profondeur (4 Pl), supposées isothermes ; "
             "domaine : l'espace entre deux ailettes, en 28 tranches.", fontsize=8, color="#495057", va="top",
             linespacing=1.4)
    lignes = []
    for cle, nom, suf, ail in AILETTES:
        d = lire(f"{cle}/resultat{suf}.json")
        if not d:
            lignes.append([nom, ail, "en cours", "", "", "", "", "", "", ""]); continue
        r, m = d["resultats"], d["parametres"]
        q = 1.2 * 1006 * m["U"] * r["T_sortie"] * DT_REF / 1e3
        charge = m.get("rangs", 4) / 4
        lignes.append([nom, ail, f"{r['dp_Pa']:.2f}", f"{r['h']:.1f}", f"{100 * r['T_sortie']:.1f} %", f"{q:.2f}",
                       f"{r['P_vent_sur_Q'] / DT_REF * 1e3:.2f}", f"{charge:.2f}", f"{q / charge:.2f}",
                       f"{100 * r['part_ailettes']:.0f} %" if "part_ailettes" in r else "-"])
    y = tableau(fig, 0.905, ["Tube", "Ailettes", "Δp (Pa)", "h (W/m²K)", "Efficacité", "Q face",
                             "P vent / Q", "Charge", "Q / charge", "Ailettes"], lignes,
                [0.11, 0.18, 0.08, 0.10, 0.10, 0.08, 0.10, 0.08, 0.10, 0.07], "Résultats", taille=7, h_ligne=0.021,
                degrades={2: -1, 5: +1, 8: +1})
    fig.text(0.06, y + 0.02, "h : moyen sur toute la surface côté air (tubes + ailettes). Q face : chaleur par m² de "
             "face (kW/m², 10 K d'écart air / paroi).\nP vent / Q en ‰. Charge : propane relatif à la référence "
             "(4 rangs). Ailettes : part de la chaleur échangée par les ailettes.\n"
             "Calcul stationnaire : résidus plafonnant vers 7·10⁻³, mais Δp, température de sortie et flux constants\n"
             "à moins de 0,1 % depuis l'itération 2 000 ; bilan de chaleur fermé à 0,2 %.",
             fontsize=7, va="top", color="#343a40", linespacing=1.45)
    conclusion(fig, y - 0.04, [
        "À charge de propane égale, les ailettes multiplient la chaleur par m² de face par 3,1 (rond) et 4,3 (ellipse 2:1),",
        "    pour une ventilation par kW à peine plus élevée avec le rond (+ 11 %), + 57 % avec l'ellipse.",
        "Pour la même puissance il faut donc 3 à 4 fois moins de tube, donc de propane : c'est le levier qui manquait.",
        "Les ailettes portent 85 à 91 % de la chaleur ; avec elles le rond redevient compétitif face à l'ellipse.",
        "L'air sort à 86-90 % de l'écart de température : 4 rangs sont trop profonds avec ailettes, 2 rangs à l'essai.",
        "À vérifier : convergence (20 / 40 tranches), rendement d'ailette réel (≈ 98 % estimé), stabilité instationnaire."],
        "Premières conclusions")
    pdf.savefig(fig); plt.close(fig)


def page_longitudinal(pdf):
    """Piste : tubes parallèles à l'air, estimation analytique (outils/analytique/tubes_longitudinaux.py)."""
    d = lire("longitudinal/resultat.json")
    if not d:
        return
    pts = []
    for cle, nom in NIVEAU1 + SERIE2:
        r = lire(f"{cle}/resultat.json")
        if r and r.get("parametres", {}).get("couches"):
            r = r["resultats"]
            pts.append((r["P_vent_sur_Q"] / DT_REF * 1e3, 100 * r["T_sortie"], nom))
    pareto = sorted(p for p in pts if not any(q[0] <= p[0] and q[1] >= p[1] and q != p for q in pts))
    lon = d["charge_egale"]
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Piste : tubes parallèles à l'air (estimation, à valider en CFD 3D)", fontsize=15, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.95, "Tubes ronds Ø 6 mm couchés dans le sens de l'air, en réseau triangulaire de pas P dans le plan "
             "de la face ; air à 1 m/s.\nMême tube et même charge de propane que la batterie de référence : la "
             "profondeur découle du pas (même longueur de tube par m² de face).\nCalcul analytique, pas CFD : "
             "couche limite laminaire en développement dans l'anneau équivalent à la cellule, pertes aux bouts.",
             fontsize=8, color="#495057", va="top", linespacing=1.4)
    ax = fig.add_axes([0.11, 0.53, 0.83, 0.34])
    ax.scatter([p[0] for p in pts if p not in pareto], [p[1] for p in pts if p not in pareto], s=22,
               color="#adb5bd", edgecolor="white", lw=0.5, zorder=2, label="formes en travers (CFD 2D)")
    ax.plot([p[0] for p in pareto], [p[1] for p in pareto], color="#2a78d6", lw=1.4, marker="o", ms=5,
            mec="white", mew=0.7, zorder=3, label="front de Pareto, en travers")
    for x, yv, nom in pareto:
        ax.annotate(nom, (x, yv), xytext=(-5, 4), textcoords="offset points", fontsize=6, ha="right", color="#2a78d6")
    xs = [1e3 * r["P_vent_sur_Q"] for r in lon]; ys = [100 * r["T_sortie"] for r in lon]
    ax.plot(xs, ys, color="#eb6834", lw=1.8, marker="s", ms=5, mec="white", mew=0.7, zorder=4,
            label="tubes parallèles à l'air (estimation)")
    for r, x, yv in zip(lon, xs, ys):
        ax.annotate(f"P = {r['P_mm']:g} mm", (x, yv), xytext=(5, -9), textcoords="offset points", fontsize=6,
                    color="#b8461b")
    from matplotlib.ticker import FuncFormatter, NullFormatter
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}")); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([0.2, 0.5, 1, 2, 5, 10])
    ax.set_xlabel("P vent / Q (‰, 10 K d'écart air / paroi) : plus bas = moins de ventilateur", fontsize=8)
    ax.set_ylabel("Efficacité (%) : plus haut = plus de chaleur", fontsize=8)
    ax.tick_params(labelsize=7.5); ax.grid(True, color="#e9ecef", lw=0.6)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    lignes = [[f"{r['P_mm']:g}", f"{r['P_sur_D']:.2f}", f"{r['profondeur_mm']:.0f}", f"{r['Re_Dh']:.0f}",
               f"{r['dp_Pa']:.2f}", f"{r['h']:.1f}", f"{100 * r['T_sortie']:.1f} %", f"{1e3 * r['P_vent_sur_Q']:.2f}",
               "faible (P/D < 1,5)" if r["P_sur_D"] < 1.49 else ("transition ?" if r["Re_Dh"] > 2300 else "bonne")]
              for r in lon]
    ref = lire("rond/resultat.json")["resultats"]
    lignes.append(["Rond en travers", "2.00", f"{ref['profondeur_mm']:.0f}", "", f"{ref['dp_Pa']:.2f}", f"{ref['h']:.1f}",
                   f"{100 * ref['T_sortie']:.1f} %", f"{ref['P_vent_sur_Q'] / DT_REF * 1e3:.2f}", "CFD 2D"])
    v = d["verification"]
    y = tableau(fig, 0.47, ["Pas P (mm)", "P / D", "Prof. (mm)", "Re (Dh)", "Δp (Pa)", "h (W/m²K)", "Efficacité",
                            "P vent / Q (‰)", "Fiabilité"], lignes,
                [0.13, 0.08, 0.10, 0.09, 0.09, 0.10, 0.11, 0.13, 0.17], "Résultats à charge égale (1 m/s)",
                taille=7, h_ligne=0.019, degrades={4: -1, 6: +1})
    fig.text(0.06, y + 0.02, f"Vérification du calcul sur le canal plan : f·Re = {v['fRe']:.2f} (exact 24), "
             f"Nu = {v['Nu']:.2f} (exact 7,54) ; zone d'entrée à moins de 2,5 % de la corrélation de Shah.\n"
             "Fiabilité : l'anneau équivalent n'est plus fidèle sous P/D ≈ 1,5 (passage très inégal autour du tube) ; "
             "au-delà de Re ≈ 2 300 l'écoulement peut devenir turbulent.\nCollecteurs non comptés : ni leur volume de "
             "propane, ni leur obstacle à l'air. Δp et efficacité colorés du rouge au vert.",
             fontsize=7, va="top", color="#343a40", linespacing=1.45)
    conclusion(fig, y - 0.04, [
        "Sur le papier, les tubes parallèles à l'air valent les meilleures formes en travers : la courbe suit le front de",
        "    Pareto, un peu en dessous à pas large (P ≥ 10 mm), un peu au-dessus à pas serré (P ≤ 9 mm).",
        "Raison : à charge égale les tubes sont courts (16 à 42 mm), l'air reste en régime d'entrée où l'échange est fort.",
        "Les points au-dessus du front (P = 7,5 et 8 mm) sont ceux où le modèle est le moins fiable (passage inégal).",
        "    Exemple P = 8 mm : autant de chaleur que le rond en travers, 12 % de Δp en moins, 19 mm de profondeur au lieu de 37.",
        "Bilan : concurrent sérieux, pas une rupture ; l'écart au front reste dans l'incertitude (± 15 %).",
        "Le juge sera le collecteur (milliers de tubes de 2 cm à raccorder), non compté ici ; avantage non compté :",
        "    contre-courant air / propane. Suite si on garde la piste : CFD 3D d'une cellule et dessin du collecteur."],
        "Conclusion")
    pdf.savefig(fig); plt.close(fig)


def page_charge_propane(pdf):
    """Côté propane : charge et perte de charge selon le diamètre intérieur (outils/analytique/charge_propane.py)."""
    d = lire("charge_propane/resultat.json")
    if not d:
        return
    lim, hors = d["limite_charge_g"], d["hors_tubes_g"]
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, "Côté propane : diamètre intérieur des tubes (estimation)", fontsize=15,
             fontweight="bold", color=BLEU)
    fig.text(0.06, 0.95, "Tube de Ø extérieur 6 mm (côté air inchangé) ; le canal intérieur rétrécit quand la paroi "
             "s'épaissit. Climatisation nominale : évaporation 10 °C,\ncondensation 46 °C, 2,3 kW de froid. "
             f"Longueur de tube tirée de la CFD (tubes nus, 4 rangs, 1 m/s) : {d['longueur_evap_m']:.0f} m à "
             f"l'évaporateur, {d['longueur_cond_m']:.0f} m au condenseur.\nPour chaque diamètre : le nombre minimal "
             f"de circuits en parallèle pour perdre au plus {100 * d['perte_COP_max']:.0f} % de COP par la perte de "
             "charge du propane.", fontsize=8, color="#495057", va="top", linespacing=1.4)
    ax = fig.add_axes([0.10, 0.60, 0.38, 0.25])
    for sc, col, mk in zip(d["scenarios"], COULEURS, MARQUEURS):
        D = [r["D_i_mm"] for r in sc["resultats"]]
        m = [r["charge_tubes_g"] for r in sc["resultats"]]
        ax.plot(D, m, color=col, marker=mk, ms=4.5, lw=1.6, mec="white", mew=0.6,
                label="tubes nus, 1 m/s" if sc["facteur_longueur"] == 1 else "tubes 4 fois plus courts")
        for r, x, y in zip(sc["resultats"], D, m):
            ax.annotate(f"{r['circuits']}", (x, y), xytext=(-3, 5), textcoords="offset points", fontsize=6,
                        color=col, ha="right")
    ax.axhline(lim, color="#c0392b", lw=1, ls="--"); ax.text(3.0, lim * 0.84, f"limite totale {lim:.0f} g",
                                                             fontsize=6.5, color="#c0392b")
    ax.axhline(lim - hors, color="#c0392b", lw=1, ls=":")
    ax.text(2.6, (lim - hors) * 0.84, f"reste pour les tubes ≈ {lim - hors:.0f} g", fontsize=6.5, color="#c0392b")
    ax.set_yscale("log"); ax.set_xlabel("Ø intérieur (mm)", fontsize=7.5); ax.set_ylabel("charge dans les tubes (g)",
                                                                                          fontsize=7.5)
    ax.set_title("Charge des deux batteries (chiffres : circuits)", fontsize=9)
    from matplotlib.ticker import FuncFormatter, NullFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}")); ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_yticks([20, 50, 100, 200, 500, 1000])
    ax.legend(fontsize=6.5, frameon=False, loc="lower right")
    ax2 = fig.add_axes([0.58, 0.60, 0.36, 0.25])
    sc = d["scenarios"][0]
    for (Dm, pts), col, mk in zip(sorted(sc["sensibilite"].items()), COULEURS, MARQUEURS):
        ax2.plot([p[0] for p in pts], [max(100 * p[1], 0.01) for p in pts], color=col, marker=mk, ms=4.5, lw=1.6,
                 mec="white", mew=0.6, label=f"Ø int. {Dm} mm")
    ax2.axhline(100 * d["perte_COP_max"], color="#495057", lw=0.8, ls="--")
    ax2.set_xscale("log", base=2); ax2.set_yscale("log"); ax2.set_ylim(0.05, 120)
    ax2.set_xlabel("circuits en parallèle", fontsize=7.5); ax2.set_ylabel("perte de COP (%)", fontsize=7.5)
    ax2.set_title("Perte de COP par la perte de charge (tubes nus)", fontsize=9)
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}")); ax2.yaxis.set_minor_formatter(NullFormatter())
    ax2.legend(fontsize=6.5, frameon=False)
    for a_ in (ax, ax2):
        a_.tick_params(labelsize=7); a_.grid(True, color="#e9ecef", lw=0.6)
        for sp in ("top", "right"):
            a_.spines[sp].set_visible(False)
    lignes = []
    for sc in d["scenarios"]:
        nom = "Tubes nus, 1 m/s" if sc["facteur_longueur"] == 1 else "4 fois plus courts"
        for r in sc["resultats"]:
            lignes.append([nom, f"{r['D_i_mm']:.1f}", f"{r['paroi_mm']:.2f}", f"{r['circuits']}",
                           f"{r['longueur_circuit_cond_m']:.1f}", f"{r['evap']['charge_g']:.0f}",
                           f"{r['cond']['charge_g']:.0f}", f"{r['charge_tubes_g']:.0f}",
                           f"{r['charge_tubes_g'] + hors:.0f}"])
    y = tableau(fig, 0.53, ["Longueur", "Ø int. (mm)", "Paroi (mm)", "Circuits", "Circuit cond. (m)",
                            "Évap. (g)", "Cond. (g)", "Tubes (g)", "Total (g)"], lignes,
                [0.17, 0.09, 0.09, 0.09, 0.13, 0.10, 0.10, 0.11, 0.12], "Résultats (perte de COP ≤ 2 %)",
                taille=7, h_ligne=0.0185, degrades={7: -1, 8: -1})
    fig.text(0.06, y + 0.02, f"Total : tubes + reste du circuit ({hors:.0f} g selon les volumes du simulateur : "
             "huile du compresseur, carter, ligne liquide). Collecteurs et distributeurs non comptés.\n"
             "Charge : fraction de vide de Rouhani-Axelsson ; perte de charge : Müller-Steinhagen et Heck ; "
             "COP : sensibilité de Carnot (≈ 3 % par K perdu) ;\nau-delà d'environ 20 % de perte de COP, la valeur "
             "n'est plus qu'indicative (perte de charge comparable à la pression). Charges colorées du rouge au vert.",
             fontsize=7, va="top", color="#343a40", linespacing=1.45)
    conclusion(fig, y - 0.035, [
        "Le diamètre intérieur est un levier fort : la charge varie comme son carré. Passer de 4 à 2 mm la divise par 4.",
        "Mais il faut alors 3 fois plus de circuits en parallèle pour garder la perte de charge du propane (39 au lieu de 12).",
        "Le vrai problème est la longueur : en tubes nus à 1 m/s il faut ≈ 450 m de tube, et le total dépasse la limite",
        "    à tous les diamètres, même 1,5 mm (193 g avec 64 circuits). Le reste du circuit prend déjà ≈ 95 g sur 152.",
        "Le condenseur porte 87 % de la charge des tubes (liquide et diphasique dense) : c'est lui qu'il faut réduire.",
        "Avec des tubes 4 fois plus courts (ailettes, air plus rapide) : Ø ≤ 2 mm tient dans la limite (138 g, 24 circuits).",
        "Conclusion : canal fin ET tubes courts ; l'étape 3 (ailettes) devient prioritaire, et les collecteurs sont à",
        "    concevoir avec soin, car leur volume s'ajoute (non compté ici)."], "Conclusion")
    pdf.savefig(fig); plt.close(fig)


def page_image(pdf, titre, images, notes=""):
    images = [FORMES / i for i in images if (FORMES / i).exists()]
    if not images:
        return
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, titre, fontsize=14, fontweight="bold", color=BLEU)
    if notes:
        fig.text(0.06, 0.945, notes, fontsize=8.5, color="#495057")
    h = 0.90 / len(images)
    for k, im in enumerate(images):
        ax = fig.add_axes([0.03, 0.92 - (k + 1) * h, 0.94, h - 0.01])
        ax.imshow(mpimg.imread(im), interpolation="none"); ax.axis("off")
    pdf.savefig(fig); plt.close(fig)


def main():
    with PdfPages(SORTIE) as pdf:
        page_introduction(pdf)
        page_synthese(pdf)
        page_comparaison(pdf)
        page_compromis(pdf)
        page_vitesse(pdf)
        page_niveau2(pdf)
        page_ailettes(pdf)
        page_image(pdf, "Étape 3 : maillage 3D des ailettes plates", ["../maillages/ailettes_plates.png"])
        for cle, nom in (("rond", "Rond"), ("ellipse2", "Ellipse 2:1")):
            page_image(pdf, f"{nom} à ailettes plates (pas 1,8 mm), CFD 3D", [f"{cle}/resultat_ail1.8.png"])
        page_longitudinal(pdf)
        page_charge_propane(pdf)
        page_image(pdf, "Géométries : série 1", ["../maillages/formes_niveau1.png"],
                   "Tracées sur le premier maillage (triangles) ; calculs faits sur le maillage à couches (page convergence).")
        page_image(pdf, "Géométries : série 2", ["../maillages/formes_serie2.png"])
        # vues CFD rangées par forme : toutes les vitesses d'une forme à la suite (0,5 → 3 m/s)
        for cle, nom in NIVEAU1 + SERIE2:
            for U in VITESSES:
                page_image(pdf, f"{nom}, {U:g} m/s".replace(".", ","),
                           [f"{cle}/resultat.png" if U == 1.0 else f"{cle}/resultat_U{U:g}.png"])
            for tag, titre in NIVEAU2:
                page_image(pdf, f"{nom}, niveau 2 : {titre}", [f"{cle}/resultat_N2_{tag}.png"])
        page_image(pdf, "Maillages de validation (niveau 0)",
                   ["../maillages/validation_niveau0.png", "../maillages/openfoam_niveau0.png"])
        page_image(pdf, "Validation : plaques parallèles", ["plaques/profils_validation.png", "plaques/champs.png"])
        page_image(pdf, "Validation : tube isolé", ["tube_isole/resultat.png"])
        page_image(pdf, "Faisceau de tubes ronds : convergence en maillage",
                   ["rond/convergence.png", "rond/maillage_couches.png"])
        page_image(pdf, "Faisceau de tubes ronds : premier maillage (triangles), non retenu",
                   ["rond/resultat_maillage_triangles.png"])
        page_image(pdf, "Test 3D : cellule gyroïde (TPMS)", ["tpms_gyroide/resultat.png"],
                   "Chronométrage et frottement seulement (Leeds +5 %) ; échange non mesuré.")
        page_image(pdf, "Test 3D : surfaces TPMS et maillage", ["tpms_gyroide/coupes_tpms.png", "tpms_gyroide/maillage.png"])
    compresser(SORTIE)
    print(SORTIE)
    try:                                       # rapport HTML : mêmes pages + vues 3D interactives
        import rapport_html
        rapport_html.main()
    except Exception as e:                     # noqa: BLE001  (pdftoppm absent, etc.)
        print("rapport HTML non régénéré :", e)


def compresser(chemin):
    """Images recompressées en JPEG (qualité 90, 250 dpi) : PDF ≈ 5 Mo au lieu de 140 Mo
    (limite GitHub 100 Mo), netteté conservée au zoom."""
    if not shutil.which("gs"):
        return
    tmp = chemin.with_suffix(".tmp.pdf")
    subprocess.run(["gs", "-q", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-dAutoFilterColorImages=false",
                    "-dColorImageFilter=/DCTEncode", "-dJPEGQ=90", "-dDownsampleColorImages=true",
                    "-dColorImageResolution=250", "-dColorImageDownsampleThreshold=1.2",
                    f"-sOutputFile={tmp}", str(chemin)], check=True)
    tmp.replace(chemin)


if __name__ == "__main__":
    main()
