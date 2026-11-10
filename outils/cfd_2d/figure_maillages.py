"""Figure des maillages 2D de toutes les formes (noyau de la batterie + vue d'ensemble).

    python figure_maillages.py docs/maillages/formes_niveau1.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometrie import FORMES  # noqa: E402
from maillage import mailler  # noqa: E402


def dessiner(ax, b, xy, tri, xlim, lw=0.12):
    ax.triplot(mtri.Triangulation(xy[:, 0], xy[:, 1], tri), color="#1c3d6e", lw=lw)
    ext = np.asarray(b.exterieur.exterior.coords); intr = np.asarray(b.interieur.exterior.coords)
    for cx, cy in b.centres:
        for dy in ((0.0,) if cy > 0 else (0.0, b.Pt)):
            ax.fill(ext[:, 0] + cx, ext[:, 1] + cy + dy, color="#adb5bd", zorder=3)
            ax.fill(intr[:, 0] + cx, intr[:, 1] + cy + dy, color="#ffd8a8", zorder=4)
    ax.set_xlim(*xlim); ax.set_ylim(0, b.Pt); ax.set_aspect("equal")
    ax.tick_params(labelsize=7)


def main(sortie):
    formes = list(FORMES)
    res = {f: mailler(f) for f in formes}
    fig = plt.figure(figsize=(16, 21))
    fig.suptitle("Maillages 2D des formes simples : même charge de propane et même périmètre côté propane "
                 "(Dh intérieur 4 mm, paroi 1 mm, quinconce 4 rangs)\n"
                 "gris = paroi métallique, orange = canal de propane, bleu = maillage de l'air ; "
                 "l'air s'écoule de gauche à droite, haut et bas périodiques",
                 fontsize=11.5, fontweight="bold", y=0.995)
    # vue d'ensemble du domaine complet (rond)
    b, xy, tri = res["rond"]
    ax = fig.add_axes([0.05, 0.905, 0.9, 0.055])
    dessiner(ax, b, xy, tri, b.x_domaine, lw=0.06)
    ax.axvline(b.x_noyau[0], color="#e03131", ls="--", lw=1); ax.axvline(b.x_noyau[1], color="#e03131", ls="--", lw=1)
    ax.set_title(f"Domaine complet, tube rond : tampon amont 30 mm, noyau {b.x_noyau[1]:.0f} mm, "
                 f"tampon aval 60 mm ({len(tri)} mailles)", fontsize=9)
    # noyaux
    n = len(formes)
    for k, f in enumerate(formes):
        b, xy, tri = res[f]
        col, lig = k % 2, k // 2
        ax = fig.add_axes([0.05 + col * 0.48, 0.71 - lig * 0.175, 0.44, 0.15])
        dessiner(ax, b, xy, tri, (b.x_noyau[0] - 4, b.x_noyau[1] + 4))
        ax.set_title(f"{b.nom} : pas {b.Pt:.1f} × {b.Pl:.1f} mm, noyau {b.x_noyau[1]:.0f} mm, "
                     f"périmètre air {b.P_ext:.1f} mm/tube, {len(tri)} mailles", fontsize=8.5)
    Path(sortie).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(sortie, dpi=110)
    # zoom paroi
    b, xy, tri = res["rond"]
    fig2, ax = plt.subplots(figsize=(7, 6))
    cx, cy = b.centres[0]
    dessiner(ax, b, xy, tri, (cx - 4.5, cx + 4.5), lw=0.3)
    ax.set_ylim(cy - 4.5, cy + 4.5)
    ax.set_title("Zoom sur un tube rond : mailles de 0,08 mm contre la paroi,\n"
                 "grossissant jusqu'à 0,6 mm à 2 mm de la paroi", fontsize=10)
    fig2.savefig(str(sortie).replace(".png", "_zoom.png"), dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/maillages/formes_niveau1.png")
