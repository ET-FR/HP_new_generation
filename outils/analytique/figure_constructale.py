#!/usr/bin/env python3
"""Figure explicative de la théorie constructale (Bejan).
    python outils/analytique/figure_constructale.py → docs/figures/theorie_constructale.png"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

RACINE = Path(__file__).resolve().parents[2]
BLEU, ORANGE, VERT, GRIS, FONCE, ROUGE = "#2a78d6", "#eb6834", "#1baf7a", "#495057", "#1c3d6e", "#c0392b"
CHAUD = "#fde2d4"

fig = plt.figure(figsize=(15, 10.5))
fig.suptitle("Théorie constructale (Bejan, 1996) : un système qui fait passer un flux prend la forme qui le fait "
             "passer le plus facilement", fontsize=13.5, fontweight="bold", color=FONCE)


def element(ax, x, y, w, h, lame_y=None, vers="droite", lw=1.6):
    """Petit volume chauffé (rose) traversé par une lame conductrice (trait foncé)."""
    ax.add_patch(Rectangle((x, y), w, h, fc=CHAUD, ec="#e8a98a", lw=0.8))
    ly = y + h / 2 if lame_y is None else lame_y
    if vers == "droite":
        ax.plot([x + 0.08 * w, x + w], [ly, ly], color=FONCE, lw=lw, solid_capstyle="butt")
    for k in range(5):                                    # petites flèches de chaleur vers la lame
        xx = x + (k + 0.6) * w / 5.4
        for s in (1, -1):
            ax.annotate("", (xx, ly + s * 0.08 * h), (xx, ly + s * 0.38 * h),
                        arrowprops=dict(arrowstyle="->", color=ORANGE, lw=0.6))


# ---------- (a) construction par échelles ----------
fig.text(0.04, 0.905, "(a) La méthode : optimiser le plus petit élément, puis assembler et optimiser à chaque échelle",
         fontsize=11, fontweight="bold", color=FONCE)
axs = [fig.add_axes([0.03 + k * 0.165, 0.50, 0.15, 0.37]) for k in range(3)]
# 1. élément
ax = axs[0]
element(ax, 0.1, 0.4, 0.8, 0.22)
ax.plot(0.9, 0.51, "o", color=BLEU, ms=9)
ax.text(0.5, 0.75, "1. Élément", ha="center", fontsize=10, fontweight="bold", color=FONCE)
ax.text(0.5, 0.25, "volume chauffé + lame\nconductrice vers la sortie\n→ on optimise sa forme\n(longueur / largeur)",
        ha="center", fontsize=8, color=GRIS, va="top")
# 2. premier construit : 4 éléments sur une tige
ax = axs[1]
for j in range(4):
    element(ax, 0.08, 0.18 + j * 0.15, 0.55, 0.15)
ax.plot([0.63, 0.63], [0.255, 0.705], color=FONCE, lw=3.2)
ax.plot([0.63, 0.85], [0.48, 0.48], color=FONCE, lw=3.2)
ax.plot(0.88, 0.48, "o", color=BLEU, ms=9)
ax.text(0.5, 0.88, "2. Premier assemblage", ha="center", fontsize=10, fontweight="bold", color=FONCE)
ax.text(0.5, 0.12, "les lames se rejoignent sur une\ntige plus épaisse ; on optimise\nle nombre d'éléments", ha="center",
        fontsize=8, color=GRIS, va="top")
# 3. second construit : 4 premiers construits sur un tronc → arbre
ax = axs[2]
for i, (cx, cy) in enumerate([(0.05, 0.53), (0.05, 0.22), (0.50, 0.53), (0.50, 0.22)]):
    for j in range(3):
        ax.add_patch(Rectangle((cx, cy + j * 0.08), 0.26, 0.08, fc=CHAUD, ec="#e8a98a", lw=0.5))
        ax.plot([cx + 0.02, cx + 0.26], [cy + j * 0.08 + 0.04] * 2, color=FONCE, lw=0.9)
    ax.plot([cx + 0.26, cx + 0.26], [cy + 0.04, cy + 0.20], color=FONCE, lw=2.0)
    ax.plot([cx + 0.26, cx + 0.36], [cy + 0.12, cy + 0.12], color=FONCE, lw=2.0)
for cx in (0.41, 0.86):
    ax.plot([cx, cx], [0.34, 0.65], color=FONCE, lw=3.4)
ax.plot([0.41, 0.86], [0.50, 0.50], color=FONCE, lw=4.6)
ax.plot([0.86, 0.97], [0.50, 0.50], color=FONCE, lw=4.6)
ax.plot(0.98, 0.50, "o", color=BLEU, ms=9)
ax.text(0.5, 0.88, "3. Et ainsi de suite", ha="center", fontsize=10, fontweight="bold", color=FONCE)
ax.text(0.5, 0.12, "un arbre apparaît : gros canaux\npour aller loin, petits canaux\npour couvrir la surface",
        ha="center", fontsize=8, color=GRIS, va="top")
for k, ax in enumerate(axs):
    ax.set_xlim(0, 1.03); ax.set_ylim(0, 1); ax.axis("off")
    if k < 2:
        fig.add_artist(FancyArrowPatch((0.03 + k * 0.165 + 0.148, 0.685), (0.03 + (k + 1) * 0.165 + 0.004, 0.685),
                                       transform=fig.transFigure, arrowstyle="-|>", mutation_scale=16, color=GRIS))
fig.text(0.04, 0.475, "Rose : volume qui produit de la chaleur ; trait foncé : chemin facile (métal conducteur, canal) ; "
         "point bleu : sortie du flux.", fontsize=8, color=GRIS)

# ---------- (b) la même forme dans la nature ----------
ax = fig.add_axes([0.53, 0.50, 0.44, 0.37])
fig.text(0.54, 0.905, "(b) Le résultat : des arbres, partout où un flux doit couvrir un volume",
         fontsize=11, fontweight="bold", color=FONCE)


def arbre(ax, x, y, ang, long, larg, niv, couleur):
    if niv == 0:
        return
    x1, y1 = x + long * math.cos(ang), y + long * math.sin(ang)
    ax.plot([x, x1], [y, y1], color=couleur, lw=larg, solid_capstyle="round")
    for s in (1, -1):
        arbre(ax, x1, y1, ang + s * 0.36, long * 0.70, larg / 2 ** (1 / 3), niv - 1, couleur)


for x0, nom, detail, col in [(0.13, "Poumons", "air : ≈ 23 niveaux\nde ramification", BLEU),
                             (0.50, "Rivière", "eau : bassin versant\n(arbre renversé)", VERT),
                             (0.87, "Feuille", "sève : nervures\nramifiées", "#5a8f29")]:
    arbre(ax, x0, 0.12, math.pi / 2, 0.13, 6.5, 7, col)
    ax.text(x0, 0.03, nom, ha="center", fontsize=10, fontweight="bold", color=col)
    ax.text(x0, -0.06, detail, ha="center", fontsize=8, color=GRIS, va="top")
ax.set_xlim(-0.05, 1.05); ax.set_ylim(-0.2, 0.98); ax.set_aspect("equal"); ax.axis("off")
ax.text(0.5, 0.94, "à chaque division, la branche s'affine (ici selon la loi de Murray : × 0,79)", ha="center",
        fontsize=8.5, color=GRIS)

# ---------- (c) un résultat chiffré : l'écart optimal entre ailettes ----------
fig.text(0.04, 0.425, "(c) Un résultat utile : l'écart optimal entre ailettes", fontsize=11, fontweight="bold",
         color=FONCE)
ax = fig.add_axes([0.07, 0.10, 0.36, 0.29])
D = np.linspace(0.3, 6, 2000)
D_opt = 1.6
# croisement des deux asymptotes placé pour que le maximum de la courbe soit à D_opt
Dc = D_opt / 2 ** (1 / 6)
q_s = (D / Dc) ** 2                        # écart petit : l'air passe mal (étouffé)
q_l = Dc / D                               # écart grand : peu de surface, couches limites séparées
q = 1 / (1 / q_s ** 2 + 1 / q_l ** 2) ** 0.5
q_s, q_l = q_s / q.max(), q_l / q.max()
ax.plot(D, q_s, color=ORANGE, lw=1.4, ls="--", label="ailettes trop serrées : l'air passe mal")
ax.plot(D, q_l, color=BLEU, lw=1.4, ls="--", label="ailettes trop écartées : peu de surface")
ax.plot(D, q / q.max(), color="#212529", lw=2.6, label="chaleur échangée (même perte de charge)")
ax.axvline(D_opt, color=VERT, lw=1.2)
ax.text(D_opt + 0.1, 1.1, f"optimum ≈ {D_opt} mm\n(notre maillage)", fontsize=9, color=VERT, fontweight="bold")
ax.set_ylim(0, 1.4); ax.set_xlim(0.3, 6)
ax.set_xlabel("écart entre ailettes (mm)", fontsize=8.5); ax.set_ylabel("chaleur (relative)", fontsize=8.5)
ax.legend(fontsize=7.5, frameon=False, loc="upper right")
ax.tick_params(labelsize=7.5); ax.grid(True, color="#e9ecef", lw=0.6)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fig.text(0.07, 0.012, "Méthode de Bejan : chaque comportement extrême est simple (pointillés) ; l'optimum est "
        "près de leur croisement.\nFormule : D_opt ≈ 2,7 × L × Be^(-1/4) ; L = 41,6 mm, Δp ≈ 5 Pa → 1,6 mm.",
        fontsize=8, color=GRIS, va="bottom")

# ---------- (d) les échelles de notre échangeur ----------
fig.text(0.54, 0.425, "(d) Pour notre PAC : une optimisation par échelle, puis l'ensemble", fontsize=11,
         fontweight="bold", color=FONCE)
ax = fig.add_axes([0.53, 0.05, 0.44, 0.35]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
niveaux = [("Ailette / cellule", "mm", "écart, forme de l'ailette", "chaleur à ventilation donnée", "étape 3"),
           ("Tube et circuit", "cm", "Ø intérieur, longueur", "charge + perte de charge propane", "page 8"),
           ("Collecteur", "dm", "arbre de distribution", "répartition égale + volume", "Murray"),
           ("Batterie", "fenêtre", "face, rangs, vitesse", "encombrement, bruit", "étape 4")]
for k, (nom, ech, quoi, crit, ou) in enumerate(niveaux):
    y = 0.80 - k * 0.22
    w = 0.30 + k * 0.05
    ax.add_patch(FancyBboxPatch((0.02, y - 0.07), w, 0.15, boxstyle="round,pad=0.01", fc="#eef4fb", ec="#9fbbe0"))
    ax.text(0.04, y + 0.03, nom, fontsize=9.5, fontweight="bold", color=FONCE, va="center")
    ax.text(0.04, y - 0.03, f"échelle : {ech}", fontsize=7.5, color=GRIS, va="center")
    ax.text(w + 0.06, y + 0.03, quoi, fontsize=8.5, color="#212529", va="center")
    ax.text(w + 0.06, y - 0.03, f"critère : {crit}  ({ou})", fontsize=8, color=GRIS, va="center")
    if k < 3:
        ax.annotate("", (0.10, y - 0.15), (0.10, y - 0.075), arrowprops=dict(arrowstyle="-|>", color=GRIS))
ax.text(0.02, -0.04, "Puis vérification sur le cycle complet de la PAC : COP (ou SCOP) maximal, charge ≤ 152 g.",
        fontsize=8.5, color=ROUGE, fontweight="bold")

sortie = RACINE / "docs" / "figures" / "theorie_constructale.png"
fig.savefig(sortie, dpi=160)
print(sortie)
