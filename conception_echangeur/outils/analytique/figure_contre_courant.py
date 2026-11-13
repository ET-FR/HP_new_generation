"""Schéma : courant parallèle / croisé (poumon d'oiseau) / contre-courant (branchies),
rete mirabile (pattes d'oiseau, thon) et leçons pour la PAC (circuitage, échangeur interne).

Profils calculés avec le même NTU = 2 et des débits de capacité égaux (Cr = 1) :
le fluide « air » entre à 1, le fluide « sang / propane » à 0 (température ou concentration réduite).
Sortie : docs/figures/contre_courant.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

NTU = 2.0
CHAUD, FROID, GRIS = "#d6336c", "#1c7ed6", "#495057"
SORTIE = Path(__file__).resolve().parents[2] / "docs/figures/contre_courant.png"


def fleche(ax, x0, y0, x1, y1, c, lw=2.0, ms=14):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=ms, color=c, lw=lw))


def profils():
    x = np.linspace(0, 1, 200)
    # parallèle : les deux tendent vers 0,5
    d = np.exp(-2 * NTU * x)
    par = (0.5 + 0.5 * d, 0.5 - 0.5 * d)
    # contre-courant, Cr = 1 : profils linéaires, efficacité NTU / (1 + NTU)
    e = NTU / (1 + NTU)
    air_c = 1 - e * x
    sang_c = (1 - e) - e * x + e  # sang entre à 0 en x = 1, sort à e en x = 0
    sang_c = e * (1 - x)
    # courant croisé (oiseau) : N capillaires en parallèle, chacun de NTU = NTU, mélangés à la sortie
    n = 12
    xs = (np.arange(n) + 0.5) / n
    eps = 1 - np.exp(-NTU)
    air_x = np.exp(-eps * x)
    capi = eps * np.exp(-eps * xs)  # sortie de chaque capillaire
    return x, par, (air_c, sang_c), (air_x, xs, capi)


def panneau_profil(ax, titre, sous_titre, x, air, sang, sens_sang, sortie_sang, sortie_air, capi=None):
    ax.plot(x, air, color=CHAUD, lw=2.5, label="air / eau (porte O₂ ou chaleur)")
    if sang is not None:
        ax.plot(x, sang, color=FROID, lw=2.5, label="sang / propane")
    if capi is not None:
        xs, v = capi
        for xi, vi in zip(xs, v):
            ax.plot([xi, xi], [0, vi], color=FROID, lw=1.2, alpha=0.6)
            ax.plot(xi, vi, "o", color=FROID, ms=4)
        ax.axhline(v.mean(), color=FROID, ls="--", lw=1.8, label="sang mélangé en sortie")
    # flèches de sens
    fleche(ax, 0.05, 1.12, 0.35, 1.12, CHAUD)
    if sens_sang == "droite":
        fleche(ax, 0.05, -0.12, 0.35, -0.12, FROID)
    elif sens_sang == "gauche":
        fleche(ax, 0.35, -0.12, 0.05, -0.12, FROID)
    else:
        for xi in (0.15, 0.3, 0.45):
            fleche(ax, xi, 0.02 - 0.1, xi, -0.2, FROID, lw=1.2, ms=9)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.25, 1.25)
    ax.set_title(titre, fontsize=12, fontweight="bold", loc="left", pad=22)
    ax.text(0, 1.03, sous_titre, transform=ax.transAxes, fontsize=9, color=GRIS)
    ax.set_xlabel("position le long de l'échangeur")
    ax.set_yticks([0, 0.5, 1])
    ax.text(0.98, 0.97, f"sang sortant : {sortie_sang:.2f}\nair sortant : {sortie_air:.2f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#ced4da"))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def panneau_rete(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Pattes d'oiseau, thon : rete mirabile", fontsize=12, fontweight="bold", loc="left")
    # artère (descend) et veine (remonte)
    ax.add_patch(FancyBboxPatch((3.0, 1.2), 0.8, 7.2, boxstyle="round,pad=0.05", fc="#ffe3e3", ec=CHAUD, lw=2))
    ax.add_patch(FancyBboxPatch((4.4, 1.2), 0.8, 7.2, boxstyle="round,pad=0.05", fc="#d0ebff", ec=FROID, lw=2))
    fleche(ax, 3.4, 7.6, 3.4, 2.0, CHAUD, lw=2.5)
    fleche(ax, 4.8, 2.0, 4.8, 7.6, FROID, lw=2.5)
    for y in np.linspace(2.5, 7.0, 5):
        fleche(ax, 3.85, y, 4.35, y - 0.25, "#f08c00", lw=1.5, ms=10)
    ax.text(3.4, 9.0, "artère\n40 °C", ha="center", fontsize=10, color=CHAUD)
    ax.text(4.8, 9.0, "veine\n≈ 37 °C", ha="center", fontsize=10, color=FROID)
    ax.text(3.4, 0.3, "≈ 8 °C", ha="center", fontsize=10, color=CHAUD)
    ax.text(4.8, 0.3, "≈ 5 °C", ha="center", fontsize=10, color=FROID)
    ax.text(1.4, 4.8, "corps\n(chaud)\n↑\n\n\n↓\npied\n(froid)", ha="center", va="center", fontsize=9, color=GRIS)
    ax.text(5.8, 7.6, "La chaleur passe de l'aller\nau retour sans quitter le corps :\nle pied reste froid,\npeu de chaleur perdue.",
            fontsize=9, va="top")
    ax.text(5.8, 4.2, "Thon : même faisceau,\nmais il garde la chaleur\ndu muscle rouge\n(> 10 °C au-dessus de l'eau).",
            fontsize=9, va="top")
    ax.text(5.8, 1.6, "PAC : échangeur interne\nliquide / aspiration.", fontsize=9, va="top", fontweight="bold")


def panneau_circuits(ax):
    ax.set_xlim(0, 12)
    ax.set_ylim(-1.8, 6.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Batterie : circuitage (leçon de l'oiseau et du poisson)", fontsize=12, fontweight="bold", loc="left")
    couleurs = ["#2f9e44", "#f08c00", "#7048e8", "#e8590c"]
    for k, x0 in enumerate((0.6, 6.6)):
        fleche(ax, x0 - 0.4, 5.6, x0 + 1.4, 5.6, CHAUD, lw=2.5)
        ax.text(x0 + 1.6, 5.6, "air", va="center", color=CHAUD, fontsize=10)
        cols = [x0 + 0.6 + 1.3 * i for i in range(3)]
        lignes = [1.0, 2.2, 3.4, 4.6]
        if k == 0:
            for i, xc in enumerate(cols):
                ax.plot([xc] * 4, lignes, color=couleurs[i], lw=3, zorder=1)
                ax.text(xc, 0.3, f"rang {i + 1}", ha="center", fontsize=8, color=couleurs[i])
            ax.text(x0 + 1.9, -0.5, "À éviter : un circuit par rang.\nLe rang 1 voit l'air le plus chaud :\n"
                    "surchauffes inégales.", ha="center", va="top", fontsize=9, color="#c92a2a")
        else:
            for j, y in enumerate(lignes):
                ax.plot([cols[-1], cols[0]], [y, y], color=couleurs[j], lw=3, zorder=1)
                fleche(ax, cols[-1] + 0.6, y, cols[-1] + 0.05, y, couleurs[j], lw=1.5, ms=9)
            ax.text(cols[-1] + 0.75, 0.3, "propane\nentre ici", ha="center", fontsize=8)
            ax.text(x0 + 1.9, -0.5, "Mieux : chaque circuit traverse tous\nles rangs, entrée côté sortie d'air\n"
                    "(contre-courant global, tous égaux).", ha="center", va="top", fontsize=9, color="#2b8a3e")
        for xc in cols:
            for y in lignes:
                ax.add_patch(plt.Circle((xc, y), 0.28, fc="white", ec=GRIS, lw=1.5, zorder=2))


def panneau_ihx(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("PAC : échangeur interne (le « rete » du cycle)", fontsize=12, fontweight="bold", loc="left")

    def boite(x, y, w, h, t, c):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", fc="white", ec=c, lw=2))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=9)

    boite(3.0, 8.0, 4.0, 1.0, "condenseur (intérieur)", CHAUD)
    boite(3.0, 1.0, 4.0, 1.0, "évaporateur (extérieur)", FROID)
    boite(8.2, 4.4, 1.5, 1.2, "compres-\nseur", GRIS)
    boite(0.3, 4.4, 1.5, 1.2, "détendeur", GRIS)
    boite(3.8, 4.2, 2.4, 1.6, "échangeur\ninterne", "#f08c00")
    # ligne liquide : condenseur -> échangeur -> détendeur
    ax.plot([3.0, 2.6, 2.6, 3.8], [8.5, 8.5, 5.4, 5.4], color=CHAUD, lw=2.5)
    fleche(ax, 2.6, 6.8, 2.6, 6.0, CHAUD)
    ax.plot([3.8, 3.4, 3.4, 1.8], [4.6, 4.6, 5.0, 5.0], color=CHAUD, lw=2.5, ls="--")
    # ligne d'aspiration : évaporateur -> échangeur -> compresseur
    ax.plot([7.0, 7.4, 7.4, 6.2], [1.5, 1.5, 4.6, 4.6], color=FROID, lw=2.5)
    fleche(ax, 7.4, 2.6, 7.4, 3.4, FROID)
    ax.plot([6.2, 7.8, 7.8, 8.2], [5.4, 5.4, 5.0, 5.0], color=FROID, lw=2.5, ls="--")
    # retour compresseur -> condenseur et détendeur -> évaporateur
    ax.plot([8.95, 8.95, 7.0], [5.6, 8.5, 8.5], color=GRIS, lw=1.5)
    ax.plot([1.05, 1.05, 3.0], [4.4, 1.5, 1.5], color=GRIS, lw=1.5)
    ax.text(0.2, 7.2, "liquide chaud\n→ sous-refroidi", fontsize=8.5, color=CHAUD)
    ax.text(7.7, 2.2, "vapeur froide\n→ surchauffée", fontsize=8.5, color=FROID)
    ax.text(5.0, 3.2, "+ : un peu de COP, compresseur protégé\n− : volume de liquide = charge",
            ha="center", fontsize=8.5, color=GRIS)


def main():
    x, par, cc, cr = profils()
    fig = plt.figure(figsize=(17, 11))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.15], hspace=0.45, wspace=0.25,
                          left=0.04, right=0.98, top=0.88, bottom=0.04)
    fig.suptitle("Contre-courant dans la nature : poumon d'oiseau, branchies, pattes d'oiseau, thon",
                 fontsize=16, fontweight="bold", x=0.04, ha="left")
    fig.text(0.04, 0.925, f"Profils calculés avec les mêmes débits et la même surface (NTU = {NTU:g}) : "
             "l'air entre à 1, le sang (ou le propane) à 0.", fontsize=10, color=GRIS)

    a = fig.add_subplot(gs[0, 0])
    panneau_profil(a, "1. Même sens (parallèle)", "ingénierie : le moins bon", x, par[0], par[1],
                   "droite", par[1][-1], par[0][-1])
    a = fig.add_subplot(gs[0, 1])
    air_x, xs, capi = cr
    panneau_profil(a, "2. Courant croisé : poumon d'oiseau", "capillaires en travers, sang mélangé à la sortie",
                   x, air_x, None, "bas", capi.mean(), air_x[-1], capi=(xs, capi))
    poignees = a.get_legend_handles_labels()
    a.text(0.97, 0.80, "sang sortant > air sortant :\nimpossible chez un mammifère", transform=a.transAxes,
           ha="right", va="top", fontsize=9, color=FROID)
    a = fig.add_subplot(gs[0, 2])
    panneau_profil(a, "3. Contre-courant : branchies de poisson", "sang à l'opposé de l'eau", x, cc[0], cc[1],
                   "gauche", cc[1][0], cc[0][-1])
    h, l = a.get_legend_handles_labels()
    a.legend(h + poignees[0][1:], l + poignees[1][1:], loc="lower left", bbox_to_anchor=(0.0, 0.12),
             fontsize=8.5, frameon=False)

    panneau_rete(fig.add_subplot(gs[1, 0]))
    panneau_circuits(fig.add_subplot(gs[1, 1]))
    panneau_ihx(fig.add_subplot(gs[1, 2]))

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SORTIE, dpi=130)
    print(SORTIE)


if __name__ == "__main__":
    main()
