"""Schéma de principe d'un compresseur rotatif (deux coupes) et d'un scroll.

    python outils/figure_compresseurs.py docs/schema_compresseurs.png

Dessin pédagogique, proportions indicatives (pas un plan constructeur).
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle

ACIER, FONTE, CUIVRE, AIMANT = "#8d99a6", "#5c6773", "#d9822b", "#4263eb"
ASP, REF, HUILE = "#4dabf7", "#f03e3e", "#ffe8a3"
TXT = dict(fontsize=8.5, color="#212529")


def u(a):
    return np.array([np.cos(a), np.sin(a)])


def legende(ax, xy, xytext, texte, ha="left"):
    ax.annotate(texte, xy=xy, xytext=xytext, ha=ha, va="center", **TXT,
                arrowprops=dict(arrowstyle="-", color="#495057", lw=0.7))


def fleche(ax, p0, p1, couleur, lw=2.0, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=12, color=couleur,
                                 lw=lw, connectionstyle=f"arc3,rad={rad}", zorder=20))


# ---------------------------------------------------------------------------
def rotatif_vertical(ax):
    ax.set_title("Rotatif : coupe verticale", fontsize=11, fontweight="bold")
    # enveloppe hermétique
    ax.add_patch(Rectangle((-58, 0), 116, 262, fc="#f1f3f5", ec="#343a40", lw=2.2, zorder=1))
    ax.add_patch(Rectangle((-56, 2), 112, 22, fc=HUILE, ec="none", zorder=2))
    # palier inférieur, cylindre, palier principal, silencieux
    ax.add_patch(Rectangle((-30, 22), 60, 10, fc=FONTE, ec="k", lw=0.6, zorder=3))
    ax.add_patch(Rectangle((-56, 32), 112, 30, fc=FONTE, ec="k", lw=0.8, zorder=3))
    ax.add_patch(Rectangle((-14, 34), 34, 26, fc=ACIER, ec="k", lw=0.6, zorder=4))   # rouleau (coupe)
    ax.add_patch(Rectangle((-8, 36), 24, 22, fc="#adb5bd", ec="k", lw=0.5, zorder=5))  # excentrique
    ax.add_patch(Rectangle((-30, 62), 60, 18, fc=FONTE, ec="k", lw=0.6, zorder=3))
    ax.add_patch(Polygon([(-40, 80), (40, 80), (34, 94), (-34, 94)], fc="#ced4da", ec="k", lw=0.6, zorder=3))
    # arbre
    ax.add_patch(Rectangle((-6, 20), 12, 190, fc="#adb5bd", ec="k", lw=0.6, zorder=6))
    # moteur : stator, têtes de bobines, rotor à aimants
    for x0 in (-56, 32):
        ax.add_patch(Rectangle((x0, 112), 24, 76, fc=ACIER, ec="k", lw=0.6, zorder=3))
        ax.add_patch(Rectangle((x0 + 2, 102), 20, 10, fc=CUIVRE, ec="k", lw=0.4, zorder=3))
        ax.add_patch(Rectangle((x0 + 2, 188), 20, 10, fc=CUIVRE, ec="k", lw=0.4, zorder=3))
    ax.add_patch(Rectangle((-29, 116), 58, 68, fc="#c5cbd3", ec="k", lw=0.6, zorder=4))
    for x0 in (-26, 18):
        ax.add_patch(Rectangle((x0, 122), 8, 56, fc=AIMANT, ec="none", zorder=5))
    # tube de refoulement
    ax.add_patch(Rectangle((18, 262), 8, 28, fc="#adb5bd", ec="k", lw=0.6, zorder=2))
    # bouteille séparatrice (accumulateur) et tube d'aspiration
    ax.add_patch(Rectangle((-100, 80), 28, 120, fc="#e9ecef", ec="#343a40", lw=1.6, zorder=2))
    ax.add_patch(Rectangle((-90, 200), 8, 26, fc="#adb5bd", ec="k", lw=0.6, zorder=2))
    ax.add_patch(Polygon([(-89, 80), (-83, 80), (-83, 50), (-56, 50), (-56, 44), (-89, 44)],
                         fc="#adb5bd", ec="k", lw=0.6, zorder=2))
    # écoulements
    fleche(ax, (-86, 240), (-86, 205), ASP)
    fleche(ax, (-86, 70), (-62, 47), ASP, rad=0.3)
    fleche(ax, (0, 96), (-44, 205), REF, rad=-0.15)
    fleche(ax, (-44, 205), (20, 250), REF, rad=-0.3)
    fleche(ax, (22, 262), (22, 296), REF)
    # légendes
    legende(ax, (22, 280), (60, 290), "Refoulement (haute pression)")
    legende(ax, (-86, 225), (-235, 250), "Aspiration", ha="left")
    legende(ax, (-86, 140), (-235, 165), "Bouteille séparatrice\n(protège du liquide)")
    legende(ax, (44, 150), (72, 175), "Stator bobiné")
    legende(ax, (22, 150), (72, 145), "Rotor à aimants (moteur BLDC)")
    legende(ax, (0, 205), (72, 215), "Arbre")
    legende(ax, (30, 87), (72, 100), "Silencieux de refoulement")
    legende(ax, (40, 47), (72, 60), "Cylindre (bloc de compression)")
    legende(ax, (16, 40), (72, 35), "Rouleau sur excentrique")
    legende(ax, (40, 12), (72, 10), "Bain d'huile (propane dissous)")
    legende(ax, (58, 235), (72, 245), "Enveloppe hermétique (haute pression)")
    ax.set_xlim(-240, 180); ax.set_ylim(-5, 305)


# ---------------------------------------------------------------------------
def rotatif_horizontal(ax):
    ax.set_title("Rotatif : coupe horizontale du cylindre", fontsize=11, fontweight="bold")
    R, r, ri, e = 50.0, 40.0, 33.0, 10.0
    th = np.radians(210.0)                       # direction du point de contact
    c = e * u(th)
    ax.add_patch(Circle((0, 0), R + 26, fc=FONTE, ec="k", lw=1.0, zorder=1))

    def frontiere_rouleau(a):
        d = u(a)
        b = d @ c
        return (b + np.sqrt(b * b - c @ c + r * r)) * d

    def chambre(a0, a1, couleur):
        a = np.linspace(a0, a1, 120)
        ext = [R * u(x) for x in a]
        inn = [frontiere_rouleau(x) for x in a[::-1]]
        ax.add_patch(Polygon(ext + inn, fc=couleur, ec="none", alpha=0.85, zorder=2))

    chambre(np.radians(91), th, "#a5d8ff")                       # aspiration (croît)
    chambre(th, np.radians(449), "#ffc9c9")                      # compression (diminue)
    ax.add_patch(Circle(c, r, fc=ACIER, ec="k", lw=0.8, zorder=3))      # rouleau
    ax.add_patch(Circle(c, ri, fc="#adb5bd", ec="k", lw=0.6, zorder=4))  # excentrique
    ax.add_patch(Circle((0, 0), 11, fc="#868e96", ec="k", lw=0.6, zorder=5))  # arbre
    ax.plot(0, 0, "k+", ms=6, zorder=6)
    # palette dans sa fente + ressort
    y_tip = frontiere_rouleau(np.pi / 2)[1]
    ax.add_patch(Rectangle((-3.4, R - 2), 6.8, 40, fc="white", ec="none", zorder=2))
    ax.add_patch(Rectangle((-2.6, y_tip), 5.2, R + 12 - y_tip, fc="#495057", ec="k", lw=0.5, zorder=6))
    zz = np.linspace(R + 12, R + 36, 9)
    ax.plot([0 if i in (0, 8) else (2.5 if i % 2 else -2.5) for i in range(9)], zz, color="k", lw=0.9, zorder=6)
    # orifice d'aspiration (à gauche de la palette) et de refoulement (à droite)
    a_s, a_d = np.radians(112), np.radians(68)
    p_s = [(R - 1) * u(a_s) + 4 * u(a_s + np.pi / 2), (R + 27) * u(a_s) + 4 * u(a_s + np.pi / 2),
           (R + 27) * u(a_s) - 4 * u(a_s + np.pi / 2), (R - 1) * u(a_s) - 4 * u(a_s + np.pi / 2)]
    ax.add_patch(Polygon(p_s, fc="#a5d8ff", ec="k", lw=0.5, zorder=2))
    p_d = [(R - 1) * u(a_d) + 2 * u(a_d + np.pi / 2), (R + 14) * u(a_d) + 2 * u(a_d + np.pi / 2),
           (R + 14) * u(a_d) - 2 * u(a_d + np.pi / 2), (R - 1) * u(a_d) - 2 * u(a_d + np.pi / 2)]
    ax.add_patch(Polygon(p_d, fc="#ffc9c9", ec="k", lw=0.5, zorder=2))
    v0 = (R + 14) * u(a_d)
    ax.plot([v0[0] - 4, v0[0] + 9], [v0[1] + 3, v0[1] - 3], color="k", lw=2.2, zorder=7)  # clapet
    fleche(ax, tuple((R + 45) * u(a_s)), tuple((R + 4) * u(a_s)), ASP)
    fleche(ax, tuple((R + 12) * u(a_d)), tuple((R + 42) * u(a_d)), REF)
    # sens de rotation
    fleche(ax, tuple(18 * u(np.radians(-40))), tuple(18 * u(np.radians(50))), "#212529", lw=1.3, rad=0.45)
    # légendes
    legende(ax, (0, R + 30), (30, 112), "Palette poussée par un ressort\n(sépare aspiration et refoulement)")
    legende(ax, tuple((R + 36) * u(a_s)), (-205, 100), "Aspiration")
    legende(ax, tuple((R + 16) * u(a_d)), (60, 82), "Clapet de refoulement")
    legende(ax, tuple(-30 * u(np.radians(150)) + np.array([-10, 10])), (-205, 45), "Chambre d'aspiration\n(volume qui augmente)")
    legende(ax, (35, 0), (90, 10), "Chambre de compression\n(volume qui diminue)")
    legende(ax, tuple(c + np.array([-25, -24])), (-205, -60), "Rouleau (roule contre\nle cylindre)")
    legende(ax, tuple(R * u(th)), (-205, -20), "Point de contact\n(tourne avec l'arbre)")
    legende(ax, (0, -8), (25, -95), "Arbre et excentrique (sens de rotation)")
    ax.set_xlim(-210, 165); ax.set_ylim(-110, 125)


# ---------------------------------------------------------------------------
def scroll(ax):
    ax.set_title("Scroll : coupe horizontale des spirales", fontsize=11, fontweight="bold")
    a, t = 3.0, 2.6
    phi = np.linspace(0.5 * np.pi, 5.6 * np.pi, 900)

    def paroi(rot, dx, dy):
        x = a * (np.cos(phi) + phi * np.sin(phi))
        y = a * (np.sin(phi) - phi * np.cos(phi))
        n = np.stack([-np.sin(phi), np.cos(phi)], 1)
        cen = np.stack([x, y], 1)
        pts = np.vstack([cen + t / 2 * n, (cen - t / 2 * n)[::-1]])
        cr, sr = np.cos(rot), np.sin(rot)
        pts = pts @ np.array([[cr, sr], [-sr, cr]])
        return pts + [dx, dy]

    ro = np.pi * a - t
    psi = np.radians(35)
    ax.add_patch(Circle((0, 0), 68, fc="#e9ecef", ec="#343a40", lw=2.0, zorder=0))
    ax.add_patch(Polygon(paroi(0, 0, 0), fc="#5c7cfa", ec="k", lw=0.5, zorder=2))
    ax.add_patch(Polygon(paroi(np.pi, *(ro * u(psi))), fc=CUIVRE, ec="k", lw=0.5, zorder=3))
    ax.add_patch(Circle((0, 0), 3.2, fc=REF, ec="k", lw=0.6, zorder=5))
    # trajectoire orbitale du centre de la spirale mobile
    ax.add_patch(Circle((0, 0), ro, fc="none", ec="#212529", lw=0.8, ls="--", zorder=4))
    fleche(ax, tuple(ro * u(psi)), tuple(ro * u(psi + 1.3)), "#212529", lw=1.2, rad=0.35)
    fleche(ax, (88, -50), (62, -32), ASP)
    fleche(ax, (-78, -45), (-55, -30), ASP)
    legende(ax, (0, 0), (30, -88), "Refoulement au centre")
    legende(ax, (-36, 30), (-130, 85), "Spirale fixe")
    legende(ax, tuple(ro * u(psi) + np.array([22, 18])), (62, 82), "Spirale mobile (orbite\nsans tourner sur elle-même)")
    legende(ax, (-18, -36), (-130, -88), "Poches de gaz : elles se forment à\nl'extérieur et rétrécissent vers le centre")
    ax.text(90, -52, "Aspiration\n(périphérie)", va="top", **TXT)
    legende(ax, tuple(ro * u(psi + 1.6)), (-130, 20), "Orbite (quelques mm)")
    ax.set_xlim(-135, 135); ax.set_ylim(-105, 105)


def main(sortie):
    fig, axs = plt.subplots(1, 3, figsize=(18, 6.0), gridspec_kw=dict(width_ratios=[1.05, 1.0, 0.95]))
    rotatif_vertical(axs[0]); rotatif_horizontal(axs[1]); scroll(axs[2])
    for ax in axs:
        ax.set_aspect("equal"); ax.axis("off")
    fig.text(0.5, 0.025,
             "Bleu : gaz aspiré (basse pression)   |   Rouge : gaz refoulé (haute pression)   |   "
             "Schéma de principe, proportions indicatives",
             ha="center", fontsize=9, color="#495057")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(sortie, dpi=140, facecolor="white")
    print("écrit :", sortie)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/schema_compresseurs.png")
