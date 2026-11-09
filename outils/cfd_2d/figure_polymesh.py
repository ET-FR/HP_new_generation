"""Figure des maillages OpenFOAM (après conversion foamToVTK) : cellules et patchs de bord.

    python figure_polymesh.py dossier_des_cas sortie.png [nom_dossier_vtk]
(les cas plaques, tube_isole et rond doivent contenir le dossier produit par
 foamToVTK -constant, « VTK » par défaut)
"""
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D

COUL = {"entree": "#1c7ed6", "sortie": "#7048e8", "paroi": "#e03131", "haut": "#2f9e44",
        "bas": "#2f9e44", "haut_bas": "#f08c00"}
LEG = {"entree": "entrée : vitesse imposée 1 m/s, T = 0", "sortie": "sortie : pression imposée",
       "paroi": "paroi : non-glissement, T = 1", "haut": "haut / bas : raccordement cyclique",
       "haut_bas": "haut / bas : symétrie (glissement)"}


VTK_DIR = "VTK"


def charger(cas: Path):
    d = next((cas / VTK_DIR).glob("*_0"))
    m = pv.read(d / "internal.vtu")
    z0 = m.points[:, 2].min()
    polys, kinds = [], []
    for i in range(m.n_cells):
        c = m.get_cell(i)
        pts = c.points[np.isclose(c.points[:, 2], z0)][:, :2] * 1e3
        if len(pts) >= 3:
            ctr = pts.mean(0)
            pts = pts[np.argsort(np.arctan2(pts[:, 1] - ctr[1], pts[:, 0] - ctr[0]))]
            polys.append(pts); kinds.append(len(pts))
    bords = {}
    for f in (d / "boundary").glob("*.vtp"):
        if f.stem == "avantArriere":
            continue
        b = pv.read(f)
        segs = []
        fa = b.faces; i = 0
        while i < len(fa):
            n = fa[i]; ids = fa[i + 1:i + 1 + n]; i += n + 1
            p = b.points[ids]; p = p[np.isclose(p[:, 2], z0)][:, :2] * 1e3
            if len(p) == 2:
                segs.append(p)
        bords[f.stem] = segs
    log = (cas / "log.checkMesh").read_text()
    st = dict(nonortho=float(re.search(r"non-orthogonality Max: ([\d.]+)", log).group(1)),
              skew=float(re.search(r"Max skewness = ([\d.e+-]+)", log).group(1)),
              ok="Mesh OK" in log)
    return polys, np.array(kinds), bords, st


def dessiner(ax, polys, kinds, bords, xlim, ylim, lw=0.15, lwb=2.2):
    fc = np.where(kinds == 4, "#d0ebff", "#f1f3f5")
    ax.add_collection(PolyCollection(polys, facecolors=fc, edgecolors="#1c3d6e", linewidths=lw))
    for nom, segs in bords.items():
        ax.add_collection(LineCollection(segs, colors=COUL.get(nom, "k"), linewidths=lwb, zorder=5))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.tick_params(labelsize=7)


def main(base, sortie):
    base = Path(base)
    fig = plt.figure(figsize=(15, 17))
    fig.suptitle("Maillages OpenFOAM du niveau 0, tels que lus par OpenFOAM v2606 pour les calculs\n"
                 "bleu clair = quadrilatères (hexaèdres une fois extrudés), gris = triangles (prismes) ; "
                 "traits de couleur = patchs de bord", fontsize=12, fontweight="bold", y=0.995)
    poignees = [Line2D([], [], color=COUL[k], lw=3, label=LEG[k]) for k in ("entree", "sortie", "paroi", "haut", "haut_bas")]
    poignees += [plt.Rectangle((0, 0), 1, 1, fc="#d0ebff", ec="#1c3d6e", label="quadrilatère"),
                 plt.Rectangle((0, 0), 1, 1, fc="#f1f3f5", ec="#1c3d6e", label="triangle")]
    fig.legend(handles=poignees, loc="upper center", ncol=4, fontsize=9, bbox_to_anchor=(0.5, 0.955))

    P, K, B, st = charger(base / "plaques")
    ax = fig.add_axes([0.05, 0.84, 0.9, 0.05]); dessiner(ax, P, K, B, (-2, 202), (-0.3, 2.3), lw=0.03, lwb=1.5)
    ax.set_title(f"1. Plaques parallèles : {len(P)} cellules, non-orthogonalité max {st['nonortho']:.0f}°, "
                 f"{'Mesh OK' if st['ok'] else 'ÉCHEC'}", fontsize=9.5)
    ax = fig.add_axes([0.05, 0.66, 0.28, 0.15]); dessiner(ax, P, K, B, (-0.3, 2.5), (-0.1, 2.1), lw=0.3)
    ax.set_title("Zoom entrée : resserrement vers les plaques", fontsize=9)

    P, K, B, st = charger(base / "rond")
    ax = fig.add_axes([0.38, 0.66, 0.58, 0.15])
    dessiner(ax, P, K, B, (-31, 97), (-0.5, 12.5), lw=0.05, lwb=1.6)
    ax.set_title(f"2. Faisceau de tubes ronds : {len(P)} cellules, non-orthogonalité max {st['nonortho']:.0f}°, "
                 f"{'Mesh OK' if st['ok'] else 'ÉCHEC'} (haut et bas raccordés)", fontsize=9.5)

    ax = fig.add_axes([0.05, 0.39, 0.42, 0.23]); dessiner(ax, P, K, B, (-2, 38), (-0.5, 12.5), lw=0.15)
    ax.set_title("Zoom sur le noyau : tubes coupés par les bords haut / bas\n(même tube de part et d'autre)", fontsize=9)

    P2, K2, B2, st2 = charger(base / "tube_isole")
    ax = fig.add_axes([0.53, 0.39, 0.43, 0.23]); dessiner(ax, P2, K2, B2, (-62, 182), (-62, 62), lw=0.04, lwb=1.6)
    ax.set_title(f"3. Tube isolé : {len(P2)} cellules dont {int((K2 == 4).sum())} quadrilatères, "
                 f"non-orthogonalité max {st2['nonortho']:.0f}°, {'Mesh OK' if st2['ok'] else 'ÉCHEC'}", fontsize=9.5)
    ax = fig.add_axes([0.05, 0.04, 0.42, 0.31]); dessiner(ax, P2, K2, B2, (-5, 15), (-7, 7), lw=0.15)
    ax.set_title("Zoom : couches de quadrilatères autour du tube, puis triangles", fontsize=9)
    ax = fig.add_axes([0.53, 0.04, 0.43, 0.31]); dessiner(ax, P2, K2, B2, (2.2, 3.8), (-0.8, 0.8), lw=0.3)
    ax.set_title("Zoom paroi : 20 couches, première de 0,01 mm", fontsize=9)
    fig.savefig(sortie, dpi=110)


if __name__ == "__main__":
    if len(sys.argv) > 3:
        VTK_DIR = sys.argv[3]
    main(sys.argv[1], sys.argv[2])
