#!/usr/bin/env python3
"""
PDF de synthèse des résultats CFD 2D : docs/resultats_cfd.pdf.

Relit docs/formes/<forme>/ (resultat.json, images) : à relancer quand de nouveaux résultats
sont rangés.

    python outils/cfd_2d/rapport_pdf.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

RACINE = Path(__file__).resolve().parents[2]
DOCS = RACINE / "docs"
FORMES = DOCS / "formes"
SORTIE = DOCS / "resultats_cfd.pdf"

NIVEAU1 = [("rond", "Rond"), ("carre", "Carré"), ("losange", "Losange"),
           ("triangle_pointe", "Triangle, pointe amont"), ("triangle_base", "Triangle, base amont"),
           ("ellipse2", "Ellipse 2:1"), ("ellipse3", "Ellipse 3:1"), ("plat4", "Tube plat 4:1"),
           ("goutte", "Goutte"), ("lentille", "Lentille")]
A4 = (8.27, 11.69)
BLEU = "#1c3d6e"


def lire(chemin):
    p = FORMES / chemin
    return json.loads(p.read_text()) if p.exists() else None


def tableau(fig, y, entetes, lignes, largeurs, titre, taille=8.5, h_ligne=0.026):
    """Tableau placé sous l'ordonnée y (fraction de page) ; renvoie l'ordonnée sous le tableau."""
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
    return y - 0.025 - h - 0.035


def pct(a, b):
    return f"{100 * (a / b - 1):+.1f} %"


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

    lignes, n_ok = [], 0
    for cle, nom in NIVEAU1:
        d = lire(f"{cle}/resultat.json")
        if d and d.get("parametres", {}).get("couches"):
            r = d["resultats"]; n_ok += 1
            lignes.append([nom, f"{r['dp_Pa']:.2f}", f"{r['h']:.1f}", f"{100 * r['T_sortie']:.1f}",
                           f"{r['P_vent_sur_Q'] * 1e3:.1f}", f"{r['profondeur_mm']:.0f}"])
        else:
            lignes.append([nom, "en cours", "", "", "", ""])
    tableau(fig, y,
            ["Forme (même charge R290)", "Δp (Pa)", "h (W/m²K)", "Efficacité (%)", "P vent / Q (‰/K)", "Profondeur (mm)"],
            lignes, [0.30, 0.12, 0.13, 0.15, 0.16, 0.14],
            f"3. Comparaison des formes (niveau 1) : {n_ok} / {len(NIVEAU1)} calculées", taille=8)
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
        page_synthese(pdf)
        for cle, nom in NIVEAU1:
            page_image(pdf, f"Niveau 1 : {nom}", [f"{cle}/resultat.png"])
        page_image(pdf, "Validation : plaques parallèles", ["plaques/profils_validation.png", "plaques/champs.png"])
        page_image(pdf, "Validation : tube isolé", ["tube_isole/resultat.png"])
        page_image(pdf, "Faisceau de tubes ronds : convergence en maillage",
                   ["rond/convergence.png", "rond/maillage_couches.png"])
        page_image(pdf, "Test 3D : cellule gyroïde (TPMS)", ["tpms_gyroide/resultat.png"],
                   "Chronométrage et frottement seulement (Leeds +5 %) ; échange non mesuré.")
    print(SORTIE)


if __name__ == "__main__":
    main()
