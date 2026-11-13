"""
Dessin de principe de la « branchie imprimée » : plaques minces droites dans le sens de l'air,
micro-canaux de propane dans l'épaisseur de chaque plaque, contre-courant croisé.

Sortie : conception_echangeur/docs/figures/branchie_imprimee.png
Dimensions indicatives (à optimiser) : plaque 1,0 mm, canal 0,5 mm, pas 2,5 mm (jeu d'air 1,5 mm),
profondeur 24 mm dans le sens de l'air.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

SORTIE = Path(__file__).resolve().parents[2] / "docs" / "figures" / "branchie_imprimee.png"

METAL = "#b8c4cf"
METAL_BORD = "#5b6b7a"
PROPANE = "#d9480f"
AIR = "#1c7ed6"

# Dimensions (mm)
EP = 1.0        # épaisseur de plaque
PAS = 2.5       # pas des plaques
PROF = 24.0     # profondeur (sens de l'air)
HAUT = 40.0     # hauteur dessinée (tronçon)
N_CANAUX = 6    # canaux verticaux dans la profondeur
D_CANAL = 0.5


def boite(ax, x0, y0, z0, dx, dy, dz, couleur, alpha=1.0):
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    faces = [
        [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
        [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
    ]
    ax.add_collection3d(Poly3DCollection(faces, facecolor=couleur, edgecolor=METAL_BORD,
                                         linewidths=0.4, alpha=alpha))


def vue_3d(ax):
    n = 6
    for i in range(n):
        y = i * PAS * 2.2  # écartement exagéré pour la lisibilité
        boite(ax, 0, y, 0, PROF, EP * 1.6, HAUT, METAL, alpha=0.92)
        # canaux visibles en pointillés sur la face avant
        for k in range(N_CANAUX):
            x = PROF * (k + 0.5) / N_CANAUX
            ax.plot([x, x], [y - 0.01, y - 0.01], [1.5, HAUT - 1.5], color=PROPANE, lw=1.1,
                    ls=(0, (2, 1.5)), alpha=0.9)
    ymax = (n - 1) * PAS * 2.2 + EP * 1.6
    # collecteurs propane (haut, arrière = entrée ; haut, avant = sortie), simplifiés
    for x, lab in [(PROF - 1.5, "entrée\npropane"), (1.5, "sortie\npropane")]:
        ax.plot([x, x], [-3, ymax + 3], [HAUT + 2, HAUT + 2], color=PROPANE, lw=4,
                solid_capstyle="round")
        ax.text(x, ymax + 5, HAUT + 4, lab, color=PROPANE, fontsize=8, ha="center")
    # flèches d'air
    for z in (10, 22, 34):
        ax.quiver(-14, ymax / 2, z, 10, 0, 0, color=AIR, arrow_length_ratio=0.35, lw=1.6)
        ax.quiver(PROF + 3, ymax / 2, z, 10, 0, 0, color=AIR, arrow_length_ratio=0.35, lw=1.6)
    ax.text(-16, ymax / 2, HAUT + 6, "air", color=AIR, fontsize=10, weight="bold")
    ax.set_xlim(-15, PROF + 14)
    ax.set_ylim(-4, ymax + 6)
    ax.set_zlim(0, HAUT + 8)
    ax.set_box_aspect((PROF + 29, ymax + 10, HAUT + 8))
    ax.view_init(elev=22, azim=-58)
    ax.set_axis_off()
    ax.set_title("a) Vue d'ensemble : lamelles verticales parallèles\n(écartement exagéré)",
                 fontsize=10)


def vue_plaque(ax):
    """Une plaque vue de face : serpentin vertical de l'arrière vers l'avant (contre-courant)."""
    ax.add_patch(Rectangle((0, 0), PROF, HAUT, facecolor=METAL, edgecolor=METAL_BORD, lw=1))
    xs = [PROF * (k + 0.5) / N_CANAUX for k in range(N_CANAUX)][::-1]  # de l'arrière vers l'avant
    pts = []
    for k, x in enumerate(xs):
        haut_bas = (HAUT - 3, 3) if k % 2 == 0 else (3, HAUT - 3)
        pts += [(x, haut_bas[0]), (x, haut_bas[1])]
    pts = [(xs[0], HAUT + 4)] + pts + [(xs[-1], HAUT + 4 if N_CANAUX % 2 == 0 else -4)]
    px, py = zip(*pts)
    ax.plot(px, py, color=PROPANE, lw=2.2)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        if abs(y1 - y0) > 10:
            ym = (y0 + y1) / 2
            ax.add_patch(FancyArrowPatch((x0, ym - np.sign(y1 - y0) * 2), (x1, ym + np.sign(y1 - y0) * 2),
                                         arrowstyle="-|>", mutation_scale=12, color=PROPANE))
    ax.text(xs[0], HAUT + 6, "entrée propane", color=PROPANE, ha="center", fontsize=8)
    ax.text(xs[-1], HAUT + 6 if N_CANAUX % 2 == 0 else -9, "sortie", color=PROPANE, ha="center",
            fontsize=8)
    for y in (8, 20, 32):
        ax.add_patch(FancyArrowPatch((-10, y), (-1, y), arrowstyle="-|>", mutation_scale=14, color=AIR))
        ax.add_patch(FancyArrowPatch((PROF + 1, y), (PROF + 10, y), arrowstyle="-|>",
                                     mutation_scale=14, color=AIR))
    ax.text(-10, 42, "air entrant", color=AIR, fontsize=8)
    ax.text(PROF + 1, 42, "air sortant", color=AIR, fontsize=8)
    ax.annotate("", xy=(PROF, -6), xytext=(0, -6), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(PROF / 2, -9.5, f"profondeur ≈ {PROF:.0f} mm", ha="center", fontsize=8)
    ax.text(PROF / 2, -14, "le propane remonte l'air de l'arrière vers l'avant\n"
            "= contre-courant croisé (comme le poumon d'oiseau)", ha="center", fontsize=8,
            style="italic")
    ax.set_xlim(-13, PROF + 13)
    ax.set_ylim(-18, HAUT + 10)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("b) Une lamelle vue de face : micro-canal en serpentin", fontsize=10)


def vue_coupe(ax, decale=False):
    """Coupe horizontale : plaques (sens de l'air = x) avec canaux dans l'épaisseur."""
    n = 5
    for i in range(n):
        y0 = i * PAS
        if not decale:
            troncons = [(0, PROF)]
        else:
            L = PROF / 4
            dec = (L / 2) * (i % 2)
            troncons = []
            for k in range(-1, 5):
                a, b = k * L + dec + 0.4, (k + 1) * L + dec - 0.4
                a, b = max(a, 0), min(b, PROF)
                if b - a > 1:
                    troncons.append((a, b))
        for a, b in troncons:
            ax.add_patch(Rectangle((a, y0), b - a, EP, facecolor=METAL, edgecolor=METAL_BORD, lw=0.8))
        for k in range(N_CANAUX):
            x = PROF * (k + 0.5) / N_CANAUX
            if any(a + 0.4 < x < b - 0.4 for a, b in troncons):
                ax.add_patch(Circle((x, y0 + EP / 2), D_CANAL / 2, facecolor=PROPANE, edgecolor="none"))
    for i in range(n - 1):
        y = i * PAS + EP + (PAS - EP) / 2
        ax.add_patch(FancyArrowPatch((-4, y), (-0.3, y), arrowstyle="-|>", mutation_scale=8, color=AIR))
        ax.plot([0, PROF], [y, y], color=AIR, lw=0.6, ls=":")
    if not decale:
        # cotes
        ax.annotate("", xy=(PROF + 1.5, PAS), xytext=(PROF + 1.5, 0),
                    arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.text(PROF + 2.2, PAS / 2, f"pas {PAS} mm", va="center", fontsize=7.5)
        ax.annotate("", xy=(PROF + 1.5, PAS + EP), xytext=(PROF + 1.5, PAS),
                    arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.text(PROF + 2.2, PAS + EP / 2, f"plaque {EP} mm", va="center", fontsize=7.5)
        ax.annotate("", xy=(PROF + 1.5, 2 * PAS), xytext=(PROF + 1.5, PAS + EP),
                    arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.text(PROF + 2.2, PAS + EP + (PAS - EP) / 2, f"jeu d'air {PAS - EP} mm", va="center",
                fontsize=7.5)
        ax.text(PROF * 0.5 / N_CANAUX, 4 * PAS + EP + 0.8, f"canal Ø{D_CANAL} mm", color=PROPANE,
                fontsize=7.5)
        ax.set_title("c) Coupe horizontale : plaques lisses continues (f/j ≈ 2–3)", fontsize=10)
    else:
        ax.set_title("d) Variante « plaques décalées » : la couche limite repart\n"
                     "à chaque tronçon (h ↑, f/j ≈ 3–4)", fontsize=10)
    ax.text(-4, (n - 1) * PAS + 2.2, "air", color=AIR, fontsize=9, weight="bold")
    ax.set_xlim(-5, PROF + 11)
    ax.set_ylim(-1, (n - 1) * PAS + 3)
    ax.set_aspect("equal")
    ax.set_axis_off()


def main():
    fig = plt.figure(figsize=(13, 10.5))
    ax1 = fig.add_subplot(2, 2, 1, projection="3d")
    vue_3d(ax1)
    vue_plaque(fig.add_subplot(2, 2, 2))
    vue_coupe(fig.add_subplot(2, 2, 3))
    vue_coupe(fig.add_subplot(2, 2, 4), decale=True)
    fig.suptitle("« Branchie imprimée » : lamelles droites irriguées de l'intérieur par le propane",
                 fontsize=13, weight="bold")
    fig.text(0.5, 0.015,
             "Lamelles verticales : le condensat s'écoule le long des plaques. Dimensions indicatives, à optimiser "
             "(pas, profondeur, nombre de passes) ;\nalimentation des lamelles par un arbre de distribution "
             "(loi de Murray) non dessiné.", ha="center", fontsize=8.5, color="#444")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SORTIE, dpi=150)
    print(SORTIE)


if __name__ == "__main__":
    main()
