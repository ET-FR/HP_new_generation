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
        ["2", "Agencement", "aligné / quinconce, pas, nombre de rangs (1, 2, 4, 8)", "à faire"],
        ["3", "Ailettes et TPMS", "ailettes (plates, persiennées…), surfaces TPMS en 3D", "à faire"],
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
                    f"{titre} : {n_ok} / {len(liste)} calculées", taille=7.8, h_ligne=0.022)
    fig.text(0.06, y + 0.02, LEGENDE, fontsize=7.3, va="top", color="#343a40", linespacing=1.45)
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
        axes[2].plot([r["P_vent_sur_Q"] / DT_REF * 1e3 for _, r in pts], [100 * r["T_sortie"] for _, r in pts], **st)
    for ax, xl, yl, t in ((axes[0], "vitesse (m/s)", "h (W/m²K)", "Coefficient d'échange"),
                          (axes[1], "vitesse (m/s)", "Δp (Pa)", "Perte de charge"),
                          (axes[2], "P vent / Q (‰, 10 K)", "efficacité (%)", "Compromis")):
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
                lignes.append([nom, f"{U:g}", "en cours", "", "", "", "", ""]); continue
            z = r.get("zukauskas", {})
            lignes.append([nom, f"{U:g}", f"{r['Re_max_D6']:.0f}", f"{r['dp_Pa']:.2f}", f"{r['h']:.1f}",
                           f"{100 * r['T_sortie']:.1f} %", f"{r['P_vent_sur_Q'] / DT_REF * 1e3:.2f}",
                           f"± {100 * max(r['stabilite_moyenne'].values()):.1f} %"
                           + (f"  (Δp Zuk. {100 * z['ecart_dp']:+.0f} %)" if "ecart_dp" in z else "")])
    y = tableau(fig, 0.63, ["Forme", "U (m/s)", "Re max", "Δp (Pa)", "h (W/m²K)", "Efficacité", "P vent / Q (‰)",
                            "Stabilité"], lignes, [0.15, 0.08, 0.09, 0.10, 0.11, 0.11, 0.13, 0.23],
                "Résultats", taille=7.2, h_ligne=0.021)
    fig.text(0.06, y + 0.02, "Re max : nombre de Reynolds sur la vitesse maximale entre tubes et le Ø 6 mm du rond. "
             "Au-delà de Re ≈ 1 000, l'écoulement réel devient\n3D et turbulent dans les sillages : le calcul 2D "
             "laminaire est alors moins fiable (tendance correcte, valeurs à confirmer en 3D).\n"
             "Δp Zuk. : écart aux abaques de Zukauskas (tubes ronds seulement).",
             fontsize=7.3, va="top", color="#343a40", linespacing=1.45)
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
        page_image(pdf, "Géométries : série 1", ["../maillages/formes_niveau1.png"],
                   "Tracées sur le premier maillage (triangles) ; calculs faits sur le maillage à couches (page convergence).")
        page_image(pdf, "Géométries : série 2", ["../maillages/formes_serie2.png"])
        for cle, nom in NIVEAU1 + SERIE2:
            page_image(pdf, nom, [f"{cle}/resultat.png"])
        for cle, nom in BALAYAGE:
            for U in VITESSES:
                if U != 1.0:
                    page_image(pdf, f"{nom}, {U:g} m/s", [f"{cle}/resultat_U{U:g}.png"])
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
