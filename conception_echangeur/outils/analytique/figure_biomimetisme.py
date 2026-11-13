#!/usr/bin/env python3
"""Planche des formes bio-inspirées retenues (docs/biomimetisme.md).
    python conception_echangeur/outils/analytique/figure_biomimetisme.py → docs/figures/formes_biomimetisme.png"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle

RACINE = Path(__file__).resolve().parents[2]
BLEU, ORANGE, VERT, GRIS, FONCE, ROUGE = "#2a78d6", "#eb6834", "#1baf7a", "#495057", "#1c3d6e", "#c0392b"
METAL = "#9aa5b1"

fig = plt.figure(figsize=(16, 9.6))
fig.suptitle("Formes bio-inspirées retenues pour la PAC de fenêtre (détail et sources : docs/biomimetisme.md)",
             fontsize=13.5, fontweight="bold", color=FONCE)
L, H = 0.235, 0.30
pos = [(0.02 + i * 0.245, 0.555) for i in range(4)] + [(0.02 + i * 0.245, 0.085) for i in range(4)]


def cadre(k, titre, nature, pour_nous, etape, d3=False):
    x, y = pos[k]
    fig.text(x + 0.005, y + H + 0.035, titre, fontsize=10.5, fontweight="bold", color=FONCE)
    fig.text(x + 0.005, y + H + 0.012, f"nature : {nature}", fontsize=8, color=GRIS)
    fig.text(x + 0.005, y - 0.012, pour_nous, fontsize=8, color="#212529", va="top")
    fig.text(x + L - 0.005, y + H + 0.035, etape, fontsize=8, color=VERT, fontweight="bold", ha="right")
    ax = fig.add_axes([x, y, L, H], projection="3d" if d3 else None)
    if not d3:
        ax.set_aspect("equal"); ax.axis("off")
    return ax


def fleche(ax, x0, y0, x1, y1, c=BLEU, lw=1.5, ms=12):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=ms, color=c, lw=lw))


# 1. moustache de phoque ------------------------------------------------------------------
ax = cadre(0, "1. Tube « moustache de phoque »", "moustache du phoque veau-marin",
           "l'ellipse ondule le long du tube : les tourbillons\ndu sillage sont cassés (- 13 % de Δp publiés)",
           "étape 3", d3=True)
t = np.linspace(0, 2 * math.pi, 60)
z = np.linspace(0, 3.0, 120)
T, Z = np.meshgrid(t, z)
lam = 1.0
A = 1.0 + 0.18 * np.cos(2 * math.pi * Z / lam)                 # demi-grand axe (sens de l'air)
B = 0.5 + 0.09 * np.cos(2 * math.pi * Z / lam + math.pi)       # demi-petit axe, en opposition
ax.plot_surface(A * np.cos(T), B * np.sin(T), Z, color="#c0392b", alpha=0.95, linewidth=0, shade=True)
ax.plot_surface(1.0 * np.cos(T) + 0, 0.5 * np.sin(T) + 2.6, Z, color=METAL, alpha=0.55, linewidth=0, shade=True)
ax.text(0, 2.6, 3.35, "ellipse 2:1 lisse\n(référence)", fontsize=7, color=GRIS, ha="center")
ax.text(0, 0, 3.35, "ondulée", fontsize=7.5, color=ROUGE, ha="center", fontweight="bold")
ax.quiver(-2.6, 1.3, 1.5, 1.3, 0, 0, color=BLEU, arrow_length_ratio=0.35, lw=2)
ax.text(-2.6, 1.3, 1.75, "air", color=BLEU, fontsize=8)
ax.set_box_aspect((5, 4.5, 3.2)); ax.set_xlim(-2.6, 2.4); ax.set_ylim(-1.2, 3.3); ax.set_zlim(0, 3.2)
ax.view_init(elev=24, azim=-58); ax.set_axis_off()

# 2. tubercules de baleine ----------------------------------------------------------------
ax = cadre(1, "2. Ailette à bord d'attaque ondulé", "nageoire de la baleine à bosse",
           "les bosses du bord d'attaque créent des tourbillons\nqui renforcent l'échange (idée nouvelle)",
           "étape 3")
yy = np.linspace(0, 6, 400)
xb = 0.35 * np.sin(2 * math.pi * yy / 1.5)
ax.add_patch(Polygon(np.c_[np.r_[xb, 6, 6], np.r_[yy, 6, 0]], fc=METAL, ec="#5b6570", lw=1))
ax.add_patch(Polygon([[-0.4, 6.6], [6, 6.6], [6, 7.6], [-0.4, 7.6]], fc="none", ec="none"))
ax.add_patch(Rectangle((0, 7.0), 6, 1.0, fc="#d3d8de", ec="#5b6570", lw=1))
ax.text(3, 8.25, "ailette plate classique", ha="center", fontsize=7.5, color=GRIS)
ax.text(3, -0.55, "ailette « baleine »", ha="center", fontsize=7.5, color=ROUGE, fontweight="bold")
for yv in (0.37, 1.87, 3.37, 4.87):
    for s in (1, -1):
        cx, cy = 1.3, yv + s * 0.2
        th = np.linspace(0, 1.6 * math.pi, 40)
        ax.plot(cx + 0.18 * np.cos(th) * (1 + th / 6), cy + s * 0.18 * np.sin(th) * (1 + th / 6), color=ORANGE, lw=0.9)
for yv in (1, 3, 5):
    fleche(ax, -2.2, yv, -0.6, yv)
ax.text(-2.2, 5.6, "air", color=BLEU, fontsize=8)
ax.text(1.9, 5.7, "tourbillons", color=ORANGE, fontsize=7)
for (cx, cy) in [(3.6, 1.5), (3.6, 4.5), (5.1, 3.0)]:
    ax.add_patch(Circle((cx, cy), 0.45, fc="#c0392b", ec="none"))
ax.text(4.5, 5.6, "tubes", fontsize=7, color=ROUGE)
ax.set_xlim(-2.5, 6.3); ax.set_ylim(-0.9, 8.6)

# 3. arbre de Murray ---------------------------------------------------------------------
ax = cadre(2, "3. Collecteur en arbre de Murray", "vaisseaux sanguins, bronches",
           "chaque circuit a exactement le même chemin :\nrépartition égale du propane, volume réduit",
           "collecteurs")


def arbre(ax, x, y, dy, niv, lw):
    if niv == 0:
        ax.plot([x, x + 0.6], [y, y], color=couleur(niv), lw=lw, solid_capstyle="butt")
        return
    for s in (1, -1):
        xs = np.linspace(0, 1, 30)
        yc = y + s * dy * (3 * xs ** 2 - 2 * xs ** 3)
        ax.plot(x + xs, yc, color=couleur(niv), lw=lw / 2 ** (1 / 3), solid_capstyle="round")
        arbre(ax, x + 1, y + s * dy, dy / 2, niv - 1, lw / 2 ** (1 / 3))


couleur = lambda n: plt.cm.viridis(0.2 + 0.13 * (4 - n))
ax.plot([-0.8, 0], [0, 0], color=couleur(4), lw=9, solid_capstyle="round")
arbre(ax, 0, 0, 2.0, 4, 9)
ax.text(-1.0, 0.6, "propane", fontsize=7.5, color=GRIS, ha="left")
ax.text(4.7, 4.3, "16 circuits", fontsize=7.5, color=GRIS)
ax.text(1.8, -4.6, "Ø × 0,79 à chaque division", fontsize=7.5, color=GRIS, ha="center")
ax.set_xlim(-2.2, 5.8); ax.set_ylim(-4.9, 4.8)

# 4. contre-courant ---------------------------------------------------------------------
ax = cadre(3, "4. Circuits à contre-courant global", "poumon d'oiseau, pattes des oiseaux, thon",
           "le propane remonte rang par rang contre l'air :\nproche du contre-courant pur",
           "étape 4")
for i in range(4):
    for j in range(5):
        ax.add_patch(Circle((1.2 + i * 1.3, 0.6 + j * 1.1 + (0.55 if i % 2 else 0)), 0.32, fc="#c0392b", ec="none"))
ys = [0.6 + j * 1.1 for j in range(5)]
chemin_x = [5.1, 5.1, 3.8, 3.8, 2.5, 2.5, 1.2, 1.2]
chemin_y = [ys[0] + 0.55, ys[4] + 0.55, ys[4], ys[0], ys[0] + 0.55, ys[4] + 0.55, ys[4], ys[0]]
ax.plot(chemin_x, chemin_y, color=ORANGE, lw=2, zorder=3)
for k in range(len(chemin_x) - 1):
    xm, ym = (chemin_x[k] + chemin_x[k + 1]) / 2, (chemin_y[k] + chemin_y[k + 1]) / 2
    fleche(ax, xm - 0.01 * (chemin_x[k + 1] - chemin_x[k]), ym - 0.01 * (chemin_y[k + 1] - chemin_y[k]),
           xm + 0.01 * (chemin_x[k + 1] - chemin_x[k]) + 0.001, ym + 0.01 * (chemin_y[k + 1] - chemin_y[k]),
           c=ORANGE, ms=10)
for yv in (1.2, 3.0, 4.8):
    fleche(ax, -0.9, yv, 0.5, yv)
ax.text(-0.9, 5.7, "air →", color=BLEU, fontsize=8)
ax.text(5.6, ys[0] + 0.3, "entrée\npropane", fontsize=7, color=ORANGE)
ax.text(0.2, ys[0] - 0.75, "sortie propane", fontsize=7, color=ORANGE)
ax.text(2.9, 6.6, "rang 1 … rang 4", fontsize=7, color=GRIS, ha="center")
ax.set_xlim(-1.2, 6.8); ax.set_ylim(-0.6, 7.0)

# 5. ailette vascularisée ----------------------------------------------------------------
ax = cadre(4, "5. Ailette « vascularisée »", "oreille d'éléphant, de fennec",
           "de petits canaux de propane passent dans l'ailette :\nmoins de conduction, ailette plus fine",
           "étape 4")
ax.add_patch(Rectangle((0, 0), 6, 6, fc="#d3d8de", ec="#5b6570", lw=1))
for cy in (1.5, 4.5):
    ax.add_patch(Circle((1.0, cy), 0.55, fc="#c0392b", ec="none"))
    for dy, c in [(1.2, 1), (-1.2, 1)]:
        xs = np.linspace(1.5, 5.6, 50)
        ax.plot(xs, cy + dy * np.tanh((xs - 1.5) / 1.3) * 0.9, color="#c0392b", lw=2.2)
        xs2 = np.linspace(3.2, 5.6, 30)
        y0 = cy + dy * np.tanh((3.2 - 1.5) / 1.3) * 0.9
        ax.plot(xs2, y0 + (dy * 0.35) * np.tanh((xs2 - 3.2) / 0.8), color="#c0392b", lw=1.3)
        ax.plot(xs2, y0 - (dy * 0.35) * np.tanh((xs2 - 3.2) / 0.8), color="#c0392b", lw=1.3)
    ax.plot([1.5, 5.6], [cy, cy], color="#c0392b", lw=2.2)
ax.text(3, -0.6, "ailette vue de face : tubes (disques) et canaux internes (traits)", ha="center", fontsize=7,
        color=GRIS)
ax.set_xlim(-0.3, 6.3); ax.set_ylim(-1.0, 6.4)

# 6. disque radial : toile et tournesol ----------------------------------------------------
ax = cadre(5, "6. Échangeur en disque à flux radial", "toile d'araignée, tournesol (phyllotaxie)",
           "propane distribué en rayons et en cercles ; tubes\nplacés en spirale (angle d'or) devant un ventilateur rond",
           "si ventilateur axial")
R = 3.0
for k in range(12):
    a = 2 * math.pi * k / 12
    ax.plot([0, R * math.cos(a)], [0, R * math.sin(a)], color="#c0392b", lw=1.6)
for r in (0.9, 1.6, 2.3, 3.0):
    th = np.linspace(0, 2 * math.pi, 200)
    ax.plot(r * np.cos(th), r * np.sin(th), color="#c0392b", lw=0.9, alpha=0.8)
ax.add_patch(Circle((0, 0), 0.25, fc=FONCE))
ax.text(0, -3.6, "toile : réseau de canaux", ha="center", fontsize=7, color=GRIS)
or_ = math.pi * (3 - math.sqrt(5))
for n in range(1, 260):
    r = 0.19 * math.sqrt(n)
    ax.add_patch(Circle((7.5 + r * math.cos(n * or_), r * math.sin(n * or_)), 0.09, fc=ORANGE, ec="none"))
ax.text(7.5, -3.6, "tournesol : tubes en spirale", ha="center", fontsize=7, color=GRIS)
ax.set_xlim(-3.4, 10.9); ax.set_ylim(-4.0, 3.6)

# 7. pale de chouette ---------------------------------------------------------------------
ax = cadre(6, "7. Pale de ventilateur « chouette »", "aile de chouette (vol silencieux)",
           "bord de fuite en dents de scie : moins de bruit\n(- 2 dB et + 4,7 % de débit publiés)",
           "ventilateur")
xs = np.linspace(0, 6, 300)
haut = 1.6 + 0.9 * np.sin(math.pi * xs / 6) ** 0.8
bas_l = 0.0 + 0.3 * np.sin(math.pi * xs / 6)
dents = bas_l - 0.35 * (np.abs(((xs * 2.2) % 1.0) - 0.5) * 2)
ax.add_patch(Polygon(np.c_[np.r_[xs, xs[::-1]], np.r_[haut, dents[::-1]]], fc=METAL, ec="#5b6570", lw=1))
ax.add_patch(Polygon(np.c_[np.r_[xs, xs[::-1]], np.r_[haut + 3.2, bas_l[::-1] + 3.2]], fc="#d3d8de",
                     ec="#5b6570", lw=1))
ax.text(3, 6.25, "pale classique", ha="center", fontsize=7.5, color=GRIS)
ax.text(3, -0.85, "pale « chouette » : bord de fuite dentelé", ha="center", fontsize=7.5, color=ROUGE,
        fontweight="bold")
ax.text(6.35, 2.55, "bord d'attaque\n(air entrant)", fontsize=6.5, color=GRIS, va="center")
ax.text(6.35, 0.0, "bord de fuite", fontsize=6.5, color=GRIS, va="center")
ax.set_xlim(-0.6, 8.4); ax.set_ylim(-1.2, 6.6)

# 8. mouillabilité alternée ---------------------------------------------------------------
ax = cadre(7, "8. Surface à mouillabilité alternée", "scarabée du Namib, cactus, Nepenthes",
           "bandes qui attirent l'eau entre zones qui la repoussent :\nles condensats s'évacuent, le givre est retardé",
           "étape 5")
ax.add_patch(Rectangle((0, 0), 6, 6, fc="#eef2f5", ec="#5b6570", lw=1))
for k in range(4):
    ax.add_patch(Rectangle((0.55 + k * 1.45, 0), 0.4, 6, fc="#9fc5e8", ec="none"))
rng = np.random.default_rng(3)
for _ in range(45):
    x0 = rng.uniform(0.1, 5.9); y0 = rng.uniform(0.3, 5.9)
    near = any(abs(x0 - (0.75 + k * 1.45)) < 0.35 for k in range(4))
    if not near:
        ax.add_patch(Circle((x0, y0), rng.uniform(0.07, 0.17), fc="#2a78d6", ec="white", lw=0.5, alpha=0.9))
for k in range(4):
    fleche(ax, 0.75 + k * 1.45, 4.5, 0.75 + k * 1.45, 1.0, c=FONCE, lw=1.2, ms=9)
ax.text(3, -0.6, "gouttes (zones qui repoussent l'eau) → bandes de drainage (bleu clair)", ha="center",
        fontsize=7, color=GRIS)
ax.set_xlim(-0.3, 6.3); ax.set_ylim(-1.0, 6.4)

sortie = RACINE / "docs" / "figures" / "formes_biomimetisme.png"
fig.savefig(sortie, dpi=160)
print(sortie)
