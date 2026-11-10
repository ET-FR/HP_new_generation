"""Cartes CFD du cas « plaques parallèles » : vitesse, température, pression.

    python figure_champs_plaques.py dossier_du_cas sortie.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from matplotlib.collections import PolyCollection


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    d = sorted([p for p in (cas / "VTK").glob("*_[0-9]*") if p.is_dir()], key=lambda p: int(p.name.rsplit("_", 1)[1]))[-1]
    v = pv.read(d / "internal.vtu")
    s = v.slice(normal="z", origin=(0, 0, 0.5 * (v.bounds[4] + v.bounds[5])))
    P, f, i = [], s.faces, 0
    while i < len(f):
        n = f[i]; P.append(s.points[f[i + 1:i + 1 + n]][:, :2] * 1e3); i += n + 1
    U = np.linalg.norm(s.cell_data["U"], axis=1)
    T = s.cell_data["T"]
    p = s.cell_data["p"] * m["air"]["rho"]
    champs = [(U, "turbo", "vitesse |U| (m/s)", (0, 1.55)), (T, "inferno", "température T (0 = entrée, 1 = paroi)", (0, 1)),
              (p - p.min(), "viridis", "pression (Pa)", None)]
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle("CFD : air entre deux plaques parallèles (écartement 2 mm, 1 m/s, Re 264), OpenFOAM v2606\n"
                 "hauteur fortement agrandie sur les vues d'ensemble (canal 100 fois plus long que haut)",
                 fontsize=12, fontweight="bold")
    for k, (val, cmap, nom, lim) in enumerate(champs):
        # vue d'ensemble, y étiré
        ax = fig.add_axes([0.06, 0.80 - k * 0.27, 0.86, 0.09])
        pc = PolyCollection(P, array=val, cmap=cmap, edgecolors="face", linewidths=0.05)
        if lim: pc.set_clim(*lim)
        ax.add_collection(pc); ax.set_xlim(0, 200); ax.set_ylim(0, 2); ax.set_aspect("auto")
        ax.set_title(f"{nom} : canal entier (0 à 200 mm)", fontsize=9.5); ax.tick_params(labelsize=7)
        ax.set_ylabel("y (mm)", fontsize=8)
        cb = fig.colorbar(pc, ax=ax, fraction=0.015, pad=0.01); cb.ax.tick_params(labelsize=7)
        # zoom entrée, échelle réelle
        ax = fig.add_axes([0.06, 0.645 - k * 0.27, 0.86, 0.12])
        pc = PolyCollection(P, array=val, cmap=cmap, edgecolors="face", linewidths=0.05)
        if lim: pc.set_clim(*lim)
        ax.add_collection(pc); ax.set_xlim(0, 30); ax.set_ylim(0, 2); ax.set_aspect("equal")
        ax.set_title("zoom sur l'entrée (0 à 30 mm), échelle réelle", fontsize=9); ax.tick_params(labelsize=7)
        ax.set_ylabel("y (mm)", fontsize=8)
        fig.colorbar(pc, ax=ax, fraction=0.015, pad=0.01).ax.tick_params(labelsize=7)
    fig.text(0.06, 0.04,
             "Lecture : l'air entre à gauche à 1 m/s partout. Les plaques (haut et bas) le freinent : il ralentit contre elles et "
             "accélère au centre jusqu'à 1,5 m/s (profil parabolique).\nIl se réchauffe d'abord contre les plaques, puis dans tout "
             "l'écartement ; vers 100 mm il est presque à la température des plaques. La pression baisse régulièrement : "
             "c'est le frottement sur les plaques.", fontsize=9.5)
    fig.savefig(sortie, dpi=300)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
