#!/usr/bin/env python3
"""
Premier maillage 3D : batterie de tubes ronds à ailettes plates (étape 3).

Les ailettes plates sont perpendiculaires aux tubes : entre deux ailettes, l'air occupe une
extrusion exacte de la coupe 2D. On réutilise donc le maillage 2D à couches validé en
convergence (outils/cfd_2d/maillage_couches.py, 4 rangs en quinconce, Pt = 12 mm) et on
l'empile en tranches dans l'épaisseur entre ailettes, resserrées contre les ailettes.

Domaine : une cellule périodique en y (pas transversal Pt) et, en z, l'espace entre deux
ailettes voisines (pas d'ailettes Fp, épaisseur e). Faces z = 0 et z = Fp - e : ailettes
(paroi) dans le noyau, symétrie dans les tampons amont et aval. Même charge de propane que la
batterie de référence : les ailettes sont en métal plein, elles ajoutent de la surface côté
air sans ajouter de propane.

Hypothèses du premier maillage (à discuter) : ailettes isothermes (rendement d'ailette 1, la
conduction dans l'ailette viendra ensuite), ailettes du bord d'attaque du 1er rang au bord de
fuite du 4e, épaisseur d'ailette retirée du domaine mais bord d'attaque de l'ailette ignoré.

    python outils/cfd_3d/ailettes_plates.py [--pas 1.8] [--epaisseur 0.2]
        → docs/maillages/ailettes_plates.png et .json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "outils" / "cfd_2d"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402

from maillage_couches import mailler_couches  # noqa: E402

BLEU = "#1c3d6e"


def tranches(ecart, premiere=0.02, raison=1.15):
    """Abscisses z des tranches entre deux parois distantes de `ecart` (mm), resserrées
    symétriquement contre les deux parois (progression géométrique jusqu'au milieu)."""
    demi = ecart / 2
    n = max(3, math.ceil(math.log(1 + demi * (raison - 1) / premiere) / math.log(raison)))
    e = premiere * raison ** np.arange(n)
    e *= demi / e.sum()                       # ajusté pour tomber juste au milieu
    z = np.r_[0.0, np.cumsum(e)]
    return np.r_[z, ecart - z[-2::-1]], n


def coupe(xy, cellules, p0, p1):
    """Intervalles (abscisse curviligne) des cellules 2D coupées par le segment p0 → p1."""
    seg = LineString([p0, p1])
    out = []
    for c in cellules:
        poly = Polygon(xy[c])
        if not poly.intersects(seg):
            continue
        inter = poly.intersection(seg)
        for g in getattr(inter, "geoms", [inter]):
            if g.length > 0:
                s = [seg.project(Point(pt)) for pt in g.coords]
                out.append((min(s), max(s)))
    return sorted(out)


def dessiner_coupe(ax, intervalles, z, s0, decal=0.0, lw=0.15, couleur="#2a78d6"):
    """Grille d'une coupe verticale : chaque intervalle × chaque tranche."""
    rects = [[(a + decal, z[k]), (b + decal, z[k]), (b + decal, z[k + 1]), (a + decal, z[k + 1])]
             for a, b in intervalles for k in range(len(z) - 1)]
    h = np.diff(z)
    couleurs = plt.cm.viridis(np.clip(np.tile(h, len(intervalles)) / h.max(), 0, 1))
    ax.add_collection(PolyCollection(rects, facecolors=couleurs, edgecolors="k", linewidths=lw))


def vue_3d(ax, b, Fp, e, n_ail=4):
    """Tubes (cylindres) et ailettes (plaques translucides) sur quelques pas d'ailettes."""
    H = n_ail * Fp
    r = b.exterieur.bounds[2]                 # rayon extérieur (rond centré)
    zz = np.linspace(0, H, 2)
    # tubes pleins (y = Pt/2) et demi-tubes coupés par les bords périodiques (y = 0 et y = Pt)
    tubes = [(cx, cy, 0.0, 2 * math.pi) for cx, cy in b.centres if cy > 0]
    tubes += [(cx, 0.0, 0.0, math.pi) for cx, cy in b.centres if cy == 0]
    tubes += [(cx, b.Pt, math.pi, 2 * math.pi) for cx, cy in b.centres if cy == 0]
    for cx, cy, t0, t1 in tubes:
        T, Z = np.meshgrid(np.linspace(t0, t1, 40), zz)
        ax.plot_surface(cx + r * np.cos(T), cy + r * np.sin(T), Z, color="#c0392b",
                        alpha=0.9, linewidth=0, shade=True)
    x0, x1 = b.x_noyau
    for k in range(n_ail + 1):
        zf = k * Fp
        X, Y = np.meshgrid([x0, x1], [0, b.Pt])
        ax.plot_surface(X, Y, np.full_like(X, zf), color="#9aa5b1", alpha=0.35, linewidth=0)
    ax.quiver(x0 - 12, b.Pt / 2, H / 2, 8, 0, 0, color="#2a78d6", arrow_length_ratio=0.3, lw=2)
    ax.text(x0 - 14, b.Pt / 2, H / 2 + 1.2, "air", color="#2a78d6", fontsize=9)
    ax.set_box_aspect((x1 - x0 + 14, b.Pt, H))
    ax.set_xlim(x0 - 14, x1); ax.set_ylim(0, b.Pt); ax.set_zlim(0, H)
    ax.set_xlabel("x, sens de l'air (mm)", fontsize=7); ax.set_ylabel("y (mm)", fontsize=7)
    ax.set_zlabel("z, axe des tubes (mm)", fontsize=7)
    ax.tick_params(labelsize=6); ax.view_init(elev=22, azim=-62)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forme", default="rond")
    ap.add_argument("--pas", type=float, default=1.8, help="pas d'ailettes Fp (mm)")
    ap.add_argument("--epaisseur", type=float, default=0.2, help="épaisseur d'ailette (mm)")
    a = ap.parse_args()
    Fp, e = a.pas, a.epaisseur
    b, xy, cellules, bords = mailler_couches(a.forme)
    z, n_demi = tranches(Fp - e)
    n2d, nz = len(cellules), len(z) - 1
    x0, x1 = b.x_noyau
    aire_ext = Polygon(b.exterieur.exterior.coords).area
    A_ail = 2 * (b.Pt * (x1 - x0) - b.rangs * aire_ext) / Fp
    A_tub = b.rangs * b.P_ext * (Fp - e) / Fp
    info = dict(forme=a.forme, pas_ailettes_mm=Fp, epaisseur_mm=e, ecart_mm=Fp - e, Pt_mm=b.Pt, Pl_mm=b.Pl,
                rangs=b.rangs, cellules_2d=n2d, tranches=nz, cellules_3d=n2d * nz,
                premiere_tranche_mm=float(z[1]), tranche_milieu_mm=float(np.diff(z).max()),
                surface_air_sans_ailettes_mm2_par_mm=b.rangs * b.P_ext,
                surface_air_avec_ailettes_mm2_par_mm=A_ail + A_tub,
                facteur_surface=(A_ail + A_tub) / (b.rangs * b.P_ext))
    sortie = RACINE / "docs" / "maillages"
    (sortie / "ailettes_plates.json").write_text(json.dumps(info, indent=1, ensure_ascii=False))
    print(json.dumps(info, indent=1, ensure_ascii=False))

    # ---------- figure ----------
    fig = plt.figure(figsize=(15, 11.5))
    mil = lambda n: f"{n:,}".replace(",", " ")
    fig.suptitle(f"Premier maillage 3D : tubes ronds à ailettes plates (pas {Fp:g} mm, épaisseur {e:g} mm), "
                 f"4 rangs en quinconce, Pt = {b.Pt:.0f} mm\n"
                 f"{mil(n2d)} mailles par tranche × {nz} tranches = {mil(n2d * nz)} mailles ; surface côté air × "
                 f"{info['facteur_surface']:.1f} par rapport aux tubes nus, même charge de propane",
                 fontsize=11.5, fontweight="bold")
    ax = fig.add_axes([-0.03, 0.40, 0.46, 0.52], projection="3d")
    vue_3d(ax, b, Fp, e)
    ax.set_title("(a) Géométrie : tubes (rouge) traversant les ailettes (gris), 4 pas d'ailettes ;\n"
                 "le calcul porte sur l'espace entre deux ailettes, périodique en y", fontsize=8.5)

    # (b) coupe xy au milieu de l'espace entre ailettes : le maillage 2D
    ax = fig.add_axes([0.47, 0.60, 0.50, 0.30])
    polys = [xy[c] for c in cellules]
    ax.add_collection(PolyCollection(polys, facecolors="none", edgecolors="#343a40", linewidths=0.08))
    ax.axvspan(x0, x1, color="#9aa5b1", alpha=0.18, lw=0)
    ax.text((x0 + x1) / 2, b.Pt + 0.4, "zone à ailettes (paroi en z = 0 et z = écart)", ha="center",
            fontsize=7.5, color="#495057")
    ax.text(x0 - 7, b.Pt + 0.4, "tampon amont : symétrie", ha="center", fontsize=7, color="#495057")
    ax.set_xlim(x0 - 12, x1 + 10); ax.set_ylim(-0.2, b.Pt + 1.2); ax.set_aspect("equal")
    ax.set_xlabel("x (mm)", fontsize=8); ax.set_ylabel("y (mm)", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title("(b) Vue de dessus (plan entre deux ailettes) : maillage 2D à couches, validé en convergence",
                 fontsize=8.5)

    # (c) coupe xz à y = Pt/2 (à travers les tubes pleins des rangs 1 et 3)
    yc = b.Pt / 2
    iv = coupe(xy, cellules, (b.x_domaine[0], yc), (b.x_domaine[1], yc))
    s0 = b.x_domaine[0]
    ax = fig.add_axes([0.47, 0.37, 0.50, 0.17])
    dessiner_coupe(ax, iv, z, s0, decal=s0, lw=0.05)
    for zf in (0, Fp - e):
        ax.plot([x0, x1], [zf, zf], color="#495057", lw=2.2, solid_capstyle="butt")
    ax.set_xlim(x0 - 12, x1 + 10); ax.set_ylim(-0.15, Fp - e + 0.15)
    ax.set_xlabel("x (mm)", fontsize=8); ax.set_ylabel("z (mm)", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title(f"(c) Coupe verticale y = Pt / 2 : {nz} tranches entre les deux ailettes (traits épais), "
                 f"1re de {z[1]:.3f} mm ; trous blancs = tubes (échelle verticale dilatée)", fontsize=8.5)

    # (d) zoom xz autour du premier tube (jonction tube / ailette)
    cx = [c for c in b.centres if c[1] > 0][0][0]
    r = b.exterieur.bounds[2]
    ax = fig.add_axes([0.05, 0.06, 0.38, 0.25])
    dessiner_coupe(ax, iv, z, s0, decal=s0, lw=0.12)
    for zf in (0, Fp - e):
        ax.plot([x0, x1], [zf, zf], color="#495057", lw=3, solid_capstyle="butt")
    ax.set_xlim(cx - r - 1.2, cx - r + 1.0); ax.set_ylim(-0.08, Fp - e + 0.08); ax.set_aspect("equal")
    ax.set_xlabel("x (mm)", fontsize=8); ax.set_ylabel("z (mm)", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title("(d) Zoom, coupe y = Pt / 2 : coin ailette / tube en amont du 1er tube\n"
                 "(mailles fines contre l'ailette et contre le tube)", fontsize=8.5)

    # (e) coupe yz à travers le centre du 1er tube : ce que voit l'air de face
    ivy = coupe(xy, cellules, (cx, 0.0), (cx, b.Pt))
    ax = fig.add_axes([0.50, 0.06, 0.40, 0.25])
    dessiner_coupe(ax, ivy, z, 0.0, lw=0.1)
    for zf in (0, Fp - e):
        ax.plot([0, b.Pt], [zf, zf], color="#495057", lw=3, solid_capstyle="butt")
    ax.set_xlim(0, b.Pt); ax.set_ylim(-0.08, Fp - e + 0.08); ax.set_aspect("equal")
    ax.set_xlabel("y (mm)", fontsize=8); ax.set_ylabel("z (mm)", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title("(e) Coupe x = centre du 1er tube : section de passage de l'air entre deux ailettes\n"
                 "(blanc au centre = tube ; haut et bas de la cellule : conditions périodiques en y)", fontsize=8.5)
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0, np.diff(z).max()))
    cb = fig.colorbar(sm, cax=fig.add_axes([0.925, 0.09, 0.008, 0.19]))
    cb.set_label("épaisseur de tranche (mm)", fontsize=7); cb.ax.tick_params(labelsize=6)
    fig.savefig(sortie / "ailettes_plates.png", dpi=200)
    print(sortie / "ailettes_plates.png")


if __name__ == "__main__":
    main()
