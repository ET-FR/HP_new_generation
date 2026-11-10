"""Figure des résultats d'un cas « batterie » : champ instantané, champs moyens, chiffres clés.

    python figure_resultat.py dossier_du_cas sortie.png
(le cas doit contenir VTK_resultats/ : foamToVTK -latestTime -fields '(U T p UMean TMean pMean)'
 -name VTK_resultats, et resultat.json produit par extraire.py)
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


def coupe(m):
    zc = 0.5 * (m.bounds[4] + m.bounds[5])
    s = m.slice(normal="z", origin=(0, 0, zc))
    P, f, i = [], s.faces, 0
    while i < len(f):
        n = f[i]; P.append(s.points[f[i + 1:i + 1 + n]][:, :2] * 1e3); i += n + 1
    return s, P


def panneau(ax, P, v, cmap, titre, unite, x0, x1, H, vmin=None, vmax=None):
    pc = PolyCollection(P, array=v, cmap=cmap, edgecolors="face", linewidths=0.1)
    if vmin is not None:
        pc.set_clim(vmin, vmax)
    ax.add_collection(pc)
    ax.set_xlim(x0, x1); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.tick_params(labelsize=7)
    ax.set_title(titre, fontsize=9.5)
    cb = plt.colorbar(pc, ax=ax, fraction=0.012, pad=0.01); cb.set_label(unite, fontsize=8)


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    r = json.loads((cas / "resultat.json").read_text())
    d = sorted([p for p in (cas / "VTK_resultats").glob("*_[0-9]*") if p.is_dir()], key=lambda p: int(p.name.rsplit("_", 1)[1]))[-1]
    vol = pv.read(d / "internal.vtu")
    s, P = coupe(vol)
    rho = m["air"]["rho"]
    x0, x1 = m["x_domaine"][0] * 1e3, m["x_domaine"][1] * 1e3
    H = m["Pt"] * 1e3
    xa, xb = m["x_noyau"][0] * 1e3 - 6, m["x_noyau"][1] * 1e3 + 25
    Ui = np.linalg.norm(s.cell_data["U"], axis=1)
    Um = np.linalg.norm(s.cell_data["UMean"], axis=1)
    umax = float(np.percentile(Ui, 99.8))
    fig = plt.figure(figsize=(15, 13.5))
    fig.suptitle(f"Résultat CFD 2D : {m['nom']} (niveau 0, comparaison Zukauskas), air 1 m/s, "
                 f"OpenFOAM v2606, pimpleFoam laminaire instationnaire", fontsize=12, fontweight="bold", y=0.99)
    hs = 0.155
    y = [0.80, 0.61, 0.42, 0.23]
    panneau(fig.add_axes([0.05, y[0], 0.88, hs]), P, Ui, "turbo",
            "(a) Vitesse instantanée (fin du calcul) : on voit les tourbillons qui se détachent derrière chaque tube",
            "|U| (m/s)", xa, xb, H, 0, umax)
    panneau(fig.add_axes([0.05, y[1], 0.88, hs]), P, Um, "turbo",
            "(b) Vitesse moyennée dans le temps : jets entre les tubes, sillages lents derrière",
            "|U| moyenne (m/s)", xa, xb, H, 0, umax)
    panneau(fig.add_axes([0.05, y[2], 0.88, hs]), P, s.cell_data["TMean"], "inferno",
            "(c) Température moyenne (0 = air entrant, 1 = paroi) : l'air se réchauffe au contact des tubes",
            "T (-)", xa, xb, H, 0, 1)
    pm = s.cell_data["pMean"] * rho
    panneau(fig.add_axes([0.05, y[3], 0.88, hs]), P, pm - np.percentile(pm, 1), "viridis",
            "(d) Pression moyenne : forte au nez des tubes (arrêt de l'air), chute à travers la batterie",
            "p (Pa)", xa, xb, H)
    z = r.get("zukauskas", {})
    ax = fig.add_axes([0.05, 0.015, 0.9, 0.17]); ax.axis("off")
    g = (f"Perte de charge          {r['dp_Pa']:6.2f} Pa   (4 rangs, f par rang = {r['f_par_rang']:.3f})\n"
         f"Air en sortie            T = {r['T_sortie']:.3f}   →  efficacité {100 * r['T_sortie']:.1f} %, NTU = {r['NTU']:.3f}\n"
         f"Coefficient d'échange    h = {r['h']:.1f} W/m²K   Nu (Ø 6 mm) = {r['Nu_D6']:.2f}   j = {r['j']:.4f}\n"
         f"Bilan d'énergie          air / paroi : écart {100 * r['ecart_bilan']:+.2f} %\n"
         f"Stabilité de la moyenne  écart 1re / 2e moitié : Δp {100 * r['stabilite_moyenne']['dp']:.2f} %, "
         f"T {100 * r['stabilite_moyenne']['T_sortie']:.2f} %  →  durée suffisante")
    d2 = (f"Zukauskas (Re_max = {r['Re_max_D6']:.0f}, 4 rangs, C2 = {z.get('C2', 0):.2f})\n"
          f"  loi « cylindre isolé » (100 < Re < 1000) : Nu = {z.get('Nu_cylindre_isole', 0):.2f}  "
          f"({100 * (r['Nu_D6'] / z.get('Nu_cylindre_isole', 1) - 1):+.0f} %)\n"
          f"  loi faisceau 1000 < Re < 2e5 prolongée  : Nu = {z.get('Nu_loi_1e3', 0):.2f}  "
          f"({100 * (r['Nu_D6'] / z.get('Nu_loi_1e3', 1) - 1):+.0f} %)\n"
          f"  → CFD dans la fourchette des deux lois")
    ax.text(0, 1, g, va="top", family="monospace", fontsize=9.5)
    ax.text(0.58, 1, d2, va="top", family="monospace", fontsize=9.5)
    fig.savefig(sortie, dpi=300)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
