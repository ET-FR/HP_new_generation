"""Figure des maillages des cas de validation du niveau 0.

    python figure_validation.py docs/maillages/validation_niveau0.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.patches import Circle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cas_validation import D_TUBE, ECART, L_PLAQUE, maillage_plaques, maillage_tube_isole  # noqa: E402
from geometrie import batterie  # noqa: E402


def maille(ax, xy, el, lw):
    ax.add_collection(PolyCollection([xy[e] for e in el], facecolors="none", edgecolors="#1c3d6e", linewidths=lw))
    ax.set_aspect("equal"); ax.tick_params(labelsize=7)


def main(sortie):
    xyp, elp = maillage_plaques()
    xyt, elt = maillage_tube_isole()
    nq = sum(len(e) == 4 for e in elt)
    b = batterie("rond")
    fig = plt.figure(figsize=(15, 15))
    fig.suptitle("Niveau 0 : maillages des cas de validation (résultats connus d'avance)",
                 fontsize=13, fontweight="bold", y=0.985)

    ax = fig.add_axes([0.05, 0.86, 0.9, 0.06])
    maille(ax, xyp, elp, 0.05); ax.set_xlim(0, L_PLAQUE); ax.set_ylim(0, ECART)
    ax.axhspan(-0.6, 0, color="#adb5bd", clip_on=False); ax.axhspan(ECART, ECART + 0.6, color="#adb5bd", clip_on=False)
    ax.set_title(f"1. Canal entre deux plaques parallèles (ailette plate idéale) : écartement {ECART:g} mm "
                 f"(Dh = 4 mm), longueur {L_PLAQUE:g} mm, {len(elp)} quadrilatères. Cible : f·Re = 24, Nu = 7,54",
                 fontsize=9.5, pad=12)
    ax.set_xlabel("x (mm), l'air entre à gauche à 1 m/s", fontsize=8)
    ax = fig.add_axes([0.05, 0.64, 0.42, 0.17])
    maille(ax, xyp, elp, 0.3); ax.set_xlim(0, 4); ax.set_ylim(0, ECART)
    ax.set_title("Zoom sur l'entrée du canal : 40 mailles dans l'écartement,\nresserrées contre les plaques",
                 fontsize=9.5)

    ax = fig.add_axes([0.53, 0.64, 0.42, 0.17]); ax.axis("off")
    ax.text(0, 1, "Ce que vérifie chaque cas\n\n"
            "1. Plaques : solution exacte en écoulement établi.\n"
            "   Valide le frottement et l'échange près d'une paroi,\n"
            "   et la longueur d'établissement (environ 50 mm).\n\n"
            "2. Faisceau de tubes ronds (cas « rond » du niveau 1) :\n"
            "   corrélation de Zukauskas, Re ≈ 800 entre les tubes.\n"
            "   Valide le cas réel de la batterie.\n\n"
            "3. Tube isolé : corrélation de Hilpert, Strouhal ≈ 0,2.\n"
            "   Valide le sillage instationnaire (lâcher de\n"
            "   tourbillons), à Re ≈ 400.", va="top", fontsize=10, family="monospace")

    ax = fig.add_axes([0.05, 0.38, 0.9, 0.20])
    maille(ax, xyt, elt, 0.08); ax.set_xlim(-60, 180); ax.set_ylim(-60, 60)
    ax.add_patch(Circle((0, 0), D_TUBE / 2, color="#adb5bd", zorder=3))
    ax.set_title(f"3. Tube rond isolé, Ø {D_TUBE:g} mm : domaine 40 Ø × 20 Ø (blocage 5 %), sillage raffiné "
                 f"sur 12 Ø, {len(elt)} mailles", fontsize=9.5)
    ax.set_xlabel("x (mm)", fontsize=8)
    ax = fig.add_axes([0.05, 0.05, 0.42, 0.28])
    maille(ax, xyt, elt, 0.15); ax.set_xlim(-6, 24); ax.set_ylim(-9, 9)
    ax.add_patch(Circle((0, 0), D_TUBE / 2, color="#adb5bd", zorder=3))
    ax.set_title("Zoom : tube et début du sillage", fontsize=9.5)
    ax = fig.add_axes([0.53, 0.05, 0.42, 0.28])
    maille(ax, xyt, elt, 0.3); ax.set_xlim(2.4, 3.6); ax.set_ylim(-0.6, 0.6)
    ax.add_patch(Circle((0, 0), D_TUBE / 2, color="#adb5bd", zorder=3))
    ax.set_title(f"Zoom sur la paroi : {nq} quadrilatères en 20 couches\n"
                 "(1re couche 0,01 mm, raison 1,15), puis triangles", fontsize=9.5)
    Path(sortie).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(sortie, dpi=110)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/maillages/validation_niveau0.png")
