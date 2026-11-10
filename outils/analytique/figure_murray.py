#!/usr/bin/env python3
"""Figure explicative de la loi de Murray : arbre de collecteur à 32 circuits de 2 mm, et compromis
pompage / volume.   python outils/analytique/figure_murray.py → docs/figures/loi_murray.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

RACINE = Path(__file__).resolve().parents[2]
BLEU, ORANGE, VERT, GRIS = "#2a78d6", "#eb6834", "#1baf7a", "#495057"
NIV = 5                       # 2^5 = 32 circuits
D_FEUILLE = 2.0               # mm

fig = plt.figure(figsize=(14, 7.2))
fig.suptitle("Loi de Murray : à chaque division, r₀³ = r₁³ + r₂³  (deux branches égales : parent = 1,26 × enfant)",
             fontsize=13, fontweight="bold", color="#1c3d6e")

# ---------- arbre ----------
ax = fig.add_axes([0.03, 0.06, 0.58, 0.82])
ys = {NIV: np.linspace(0, 31, 32)}
for k in range(NIV - 1, -1, -1):
    ys[k] = ys[k + 1].reshape(-1, 2).mean(axis=1)
diam = {k: D_FEUILLE * 2 ** ((NIV - k) / 3) for k in range(NIV + 1)}
couleurs = plt.cm.viridis(np.linspace(0.15, 0.85, NIV + 1))
for k in range(NIV):
    for i, y0 in enumerate(ys[k]):
        for y1 in ys[k + 1][2 * i:2 * i + 2]:
            x0, x1 = k, k + 1
            chemin = MPath([(x0, y0), (x0 + 0.5, y0), (x1 - 0.5, y1), (x1, y1)],
                           [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4])
            ax.add_patch(PathPatch(chemin, fc="none", ec=couleurs[k], lw=diam[k] * 1.9, capstyle="round"))
ax.plot([-0.6, 0], [ys[0][0]] * 2, color=couleurs[0], lw=diam[0] * 1.9, solid_capstyle="round")
for y in ys[NIV]:
    ax.plot([NIV, NIV + 0.5], [y, y], color=couleurs[NIV], lw=diam[NIV] * 1.9, solid_capstyle="butt")
for k in range(NIV + 1):
    n = 2 ** k
    ax.text(k if k < NIV else NIV + 0.25, 33.3, f"{n} canal" if n == 1 else f"{n} canaux", ha="center",
            fontsize=8.5, color=GRIS)
    ax.text(k if k < NIV else NIV + 0.25, 32.2, f"Ø {diam[k]:.2f} mm", ha="center", fontsize=9.5,
            fontweight="bold", color=couleurs[k] * 0.8)
ax.annotate("propane\n(entrée)", (-0.6, ys[0][0]), xytext=(-0.62, ys[0][0] - 4.5), fontsize=9, color=GRIS,
            ha="center", arrowprops=dict(arrowstyle="-", color=GRIS, lw=0.6))
ax.text(NIV + 0.6, 15.5, "32 circuits\nde la batterie", fontsize=9, color=GRIS, va="center")
ax.set_xlim(-1.0, NIV + 1.4); ax.set_ylim(-1.5, 34.5); ax.axis("off")
ax.set_title("Collecteur imprimé en arbre : épaisseur des traits proportionnelle au diamètre", fontsize=10.5)
ax.text(-0.9, -1.4, "Bifurcations douces (courbes) : moins de pertes qu'à angle droit. "
        "Le frottement à la paroi est le même dans tous les canaux.", fontsize=8.5, color=GRIS)

# ---------- compromis ----------
ax2 = fig.add_axes([0.68, 0.47, 0.29, 0.39])
r = np.linspace(0.55, 1.8, 300)
P, C = 1 / r ** 4, 2 * r ** 2
ax2.plot(r, P, color=ORANGE, lw=2, label="pompage  ∝ 1 / r⁴  (perte de charge)")
ax2.plot(r, C, color=BLEU, lw=2, label="volume  ∝ r²  (charge de propane)")
ax2.plot(r, P + C, color="#212529", lw=2.4, label="total")
ax2.plot([1], [3], "o", color=VERT, ms=8, zorder=5)
ax2.annotate("optimum :\ndébit ∝ r³", (1, 3), xytext=(1.12, 5.6), fontsize=9, color=VERT, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=VERT))
ax2.set_ylim(0, 10); ax2.set_xlim(0.55, 1.8)
ax2.set_xlabel("rayon du canal (relatif à l'optimum)", fontsize=8.5); ax2.set_ylabel("coût (unités relatives)", fontsize=8.5)
ax2.set_title("Pour un débit donné : un rayon optimal", fontsize=10.5)
ax2.legend(fontsize=7.8, frameon=False, loc="upper center")
ax2.tick_params(labelsize=7.5); ax2.grid(True, color="#e9ecef", lw=0.6)
for sp in ("top", "right"):
    ax2.spines[sp].set_visible(False)

fig.text(0.68, 0.36, "Comment on obtient la loi", va="top", fontsize=10.5, fontweight="bold", color="#1c3d6e")
fig.text(0.68, 0.315,
         "1. Pompage (Poiseuille) : P = 8 μ L Q² / (π r⁴)\n"
         "2. Volume : C = b · π r² L\n"
         "3. Minimum de P + C  →  Q ∝ r³\n"
         "4. Débit conservé à la division : Q₀ = Q₁ + Q₂\n"
         "     →  r₀³ = r₁³ + r₂³\n\n"
         "Pour nous : « volume » = charge de propane,\n"
         "« pompage » = perte de COP. En diphasique\n"
         "l'exposant change : à recalculer (étape 4).",
         fontsize=9, color="#212529", linespacing=1.4, va="top")
sortie = RACINE / "docs" / "figures" / "loi_murray.png"
fig.savefig(sortie, dpi=170)
print(sortie)
