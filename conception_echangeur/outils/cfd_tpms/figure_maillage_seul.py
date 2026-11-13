#!/usr/bin/env python3
"""Figure du maillage d'un cas TPMS seul (outils/cfd_tpms/creer_cas.py, maillé par snappyHexMesh).

    python conception_echangeur/outils/cfd_tpms/figure_maillage_seul.py dossier_du_cas sortie.png
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

pv.OFF_SCREEN = True


def polys(s, axes):
    P, f, i = [], s.faces, 0
    while i < len(f):
        n = f[i]; P.append(s.points[f[i + 1:i + 1 + n]][:, axes] * 1e3); i += n + 1
    return P


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    d = sorted(p for p in (cas / "VTK_m").glob("*_0") if p.is_dir())[0]
    vol = pv.read(d / "internal.vtu")
    paroi = pv.read(d / "boundary" / "solide.vtp")
    L, D = m["L"] * 1e3, m["profondeur"] * 1e3
    # vue 3D de la paroi (côté air), rendue hors écran
    pl = pv.Plotter(off_screen=True, window_size=(1400, 900))
    pl.add_mesh(paroi.scale(1e3), color="#c9a227", smooth_shading=True, show_edges=False)
    pl.add_mesh(paroi.scale(1e3).extract_feature_edges(), color="k", line_width=0.5) if False else None
    pl.camera_position = [(-9, -10, 9), (D / 2, L / 2, L / 2), (0, 0, 1)]
    pl.add_axes(xlabel="x (air)", ylabel="y", zlabel="z")
    img3d = pl.screenshot(return_img=True); pl.close()

    fig = plt.figure(figsize=(15, 11))
    fig.suptitle(f"Maillage : {m['nom']} seul, cellule {L:.1f} mm, porosité air {m['phi_air']:.2f}, "
                 f"Dh air {m['Dh'] * 1e3:.2f} mm, noyau {D:g} mm\n"
                 f"snappyHexMesh, {vol.n_cells:,} mailles".replace(",", " ") +
                 f" (base {m['Dh'] / m['finesse'] * 1e3:.3f} mm, {m['Dh'] / m['finesse'] / 2 ** m['niveau_raff'] * 1e3:.3f} mm à la paroi)",
                 fontsize=12, fontweight="bold", y=0.99)
    ax = fig.add_axes([0.02, 0.50, 0.46, 0.44]); ax.imshow(img3d); ax.axis("off")
    ax.set_title("(a) Paroi côté air d'une cellule (1 période en y et z) : l'air la traverse selon x", fontsize=9.5)
    # coupes avec arêtes
    for k, (normal, orig, axes, xl, yl, pos, titre) in enumerate((
            ("z", (0, 0, 0.5 * m["L"]), [0, 1], "x, sens de l'air (mm)", "y (mm)", [0.53, 0.55, 0.45, 0.36],
             "(b) Coupe z = L/2 : mailles (air), blanc = paroi + propane"),
            ("x", (0.5 * m["profondeur"], 0, 0), [1, 2], "y (mm)", "z (mm)", [0.06, 0.06, 0.38, 0.38],
             "(c) Coupe x = mi-noyau, dans le plan de la face"),
            ("z", (0, 0, 0.5 * m["L"]), [0, 1], "x (mm)", "y (mm)", [0.53, 0.06, 0.42, 0.38],
             "(d) Zoom sur la paroi : raffinement et accrochage (snap)"))):
        s = vol.slice(normal=normal, origin=orig)
        ax = fig.add_axes(pos)
        ax.add_collection(PolyCollection(polys(s, axes), facecolors="#dbe9f6", edgecolors="#1c3d6e", linewidths=0.25))
        if k == 0:
            ax.set_xlim(-2, D + 3); ax.set_ylim(0, L)
            for xv in (0, D):
                ax.axvline(xv, color="#eb6834", lw=1, ls="--")
        elif k == 1:
            ax.set_xlim(0, L); ax.set_ylim(0, L)
        else:
            ax.set_xlim(D / 2 - 0.8, D / 2 + 0.8); ax.set_ylim(L / 2 - 0.6, L / 2 + 0.6)
        ax.set_aspect("equal"); ax.set_title(titre, fontsize=9.5); ax.tick_params(labelsize=7)
        ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(yl, fontsize=8)
    fig.savefig(sortie, dpi=170)
    print(sortie)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
