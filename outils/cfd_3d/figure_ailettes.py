#!/usr/bin/env python3
"""Figure des résultats d'un cas 3D à ailettes plates (outils/cfd_3d/creer_cas_ailettes.py).

    python outils/cfd_3d/figure_ailettes.py dossier_du_cas sortie.png

Le cas doit contenir resultat.json (outils/cfd_2d/extraire.py) ; VTK_resultats/ est produit au besoin
(foamToVTK, OpenFOAM local).
"""
import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from matplotlib.collections import PolyCollection

RACINE = Path(__file__).resolve().parents[2]
OPENFOAM = "/usr/lib/openfoam/openfoam2412/etc/bashrc"


def polygones(s, axes):
    P, f, i = [], s.faces, 0
    while i < len(f):
        n = f[i]; P.append(s.points[f[i + 1:i + 1 + n]][:, axes] * 1e3); i += n + 1
    return P


def panneau(ax, P, v, cmap, titre, unite, xlim, ylim, vmin=None, vmax=None, aspect="equal"):
    pc = PolyCollection(P, array=v, cmap=cmap, edgecolors="face", linewidths=0.05)
    if vmin is not None:
        pc.set_clim(vmin, vmax)
    ax.add_collection(pc)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect(aspect); ax.set_anchor("W"); ax.tick_params(labelsize=7)
    ax.set_title(titre, fontsize=9.5)
    cb = plt.colorbar(pc, ax=ax, fraction=0.012, pad=0.01); cb.set_label(unite, fontsize=8)
    cb.ax.tick_params(labelsize=7)


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    r = json.loads((cas / "resultat.json").read_text())
    if not (cas / "VTK_resultats").exists():
        subprocess.run(f"source {OPENFOAM} >/dev/null 2>&1; foamToVTK -latestTime -fields '(U T p)' "
                       "-name VTK_resultats > log.vtk 2>&1", shell=True, cwd=cas, check=True, executable="/bin/bash")
    d = sorted([p for p in (cas / "VTK_resultats").glob("*_[0-9]*") if p.is_dir()],
               key=lambda p: int(p.name.rsplit("_", 1)[1]))[-1]
    vol = pv.read(d / "internal.vtu")
    rho = m["air"]["rho"]
    ecart, Pt = m["epaisseur_mm"], m["Pt"] * 1e3
    xa, xb = m["x_noyau"][0] * 1e3 - 6, m["x_noyau"][1] * 1e3 + 15
    x0f, x1f = m["x_noyau"][0] * 1e3, m["x_noyau"][1] * 1e3

    mi = vol.slice(normal="z", origin=(0, 0, 0.5 * ecart * 1e-3))           # milieu entre ailettes
    Pm = polygones(mi, [0, 1])
    pres = vol.slice(normal="z", origin=(0, 0, 0.1 * ecart * 1e-3))         # près de l'ailette
    Pp = polygones(pres, [0, 1])
    cy = vol.slice(normal="y", origin=(0, 0.5 * Pt * 1e-3, 0))              # coupe verticale
    Pc = polygones(cy, [0, 2])
    Um = np.linalg.norm(mi.cell_data["U"], axis=1)
    umax = float(np.percentile(Um, 99.8))

    fig = plt.figure(figsize=(15, 13))
    tpms = m.get("tpms")
    ncel = m["maillage"].get("cellules") or vol.n_cells
    if tpms:
        l1 = f"{m['nom']}, {m['rangs']} rangs, métal = {100 * m['fraction_solide']:.0f} % du volume, air {m['U']:g} m/s en façade"
        l2 = f"OpenFOAM, snappyHexMesh + simpleFoam laminaire, {ncel:,} mailles".replace(",", " ") + ", TPMS isotherme"
    else:
        l1 = (f"{m['nom']} (pas {m['pas_ailettes_mm']:g} mm, épaisseur {m['epaisseur_ailette_mm']:g} mm), "
              f"{m['rangs']} rangs, air {m['U']:g} m/s en façade")
        l2 = (f"OpenFOAM, simpleFoam laminaire, {ncel:,} mailles ".replace(",", " ") +
              f"({m['tranches']['n']} tranches entre deux ailettes), ailettes isothermes")
    fig.suptitle(f"Résultat CFD 3D : {l1}\n{l2}", fontsize=12, fontweight="bold", y=0.995)
    hs, y = 0.155, [0.79, 0.59, 0.39, 0.19]
    lim = ((xa, xb), (0, Pt))
    w = min(0.85, hs * 13 / 15 * (xb - xa) / Pt + 0.04)        # largeur des vues à l'échelle (+ barre de couleur)
    ax = fig.add_axes([0.05, y[0], w, hs])
    panneau(ax, Pm, Um, "turbo", "(a) Vitesse à mi-distance entre deux ailettes (vue de dessus)", "|U| (m/s)",
            *lim, 0, umax)
    ax = fig.add_axes([0.05, y[1], w, hs])
    panneau(ax, Pm, mi.cell_data["T"], "inferno",
            "(b) Température à mi-distance entre deux ailettes (0 = air entrant, 1 = paroi)", "T (-)", *lim, 0, 1)
    ax = fig.add_axes([0.05, y[2], w, hs])
    panneau(ax, Pp, pres.cell_data["T"], "inferno",
            (f"(c) Température au quart de la cellule (z = {0.1 * ecart:.2f} mm)" if tpms else
             f"(c) Température à {0.1 * ecart:.2f} mm de l'ailette : l'air est déjà chaud dès les premiers mm"),
            "T (-)", *lim, 0, 1)
    ax = fig.add_axes([0.05, y[3], w, hs])
    pc = cy.cell_data["T"]
    panneau(ax, Pc, pc, "inferno",
            f"(d) Coupe verticale y = Pt / 2 (à travers les tubes des rangs impairs), hauteur dilatée × {8 if not tpms else 2}", "T (-)",
            (xa, xb), (-0.05, ecart + 0.05), 0, 1, aspect=2 if tpms else 8)
    for zf in (() if tpms else (0, ecart)):
        ax.plot([x0f, x1f], [zf, zf], color="#9aa5b1", lw=3, solid_capstyle="butt")
    ax.set_xlabel("x, sens de l'air (mm)", fontsize=8); ax.set_ylabel("z (mm)", fontsize=8)
    # chiffres clés et comparaison aux tubes nus
    nus = json.loads((RACINE / "docs" / "formes" / m["forme"] / "resultat.json").read_text())["resultats"]
    q = lambda e: 1.2 * 1006 * m["U"] * e * 10 / 1e3
    ax = fig.add_axes([0.05, 0.005, 0.9, 0.14]); ax.axis("off")
    g = (f"Perte de charge          {r['dp_Pa']:6.2f} Pa\n"
         f"Air en sortie            efficacité {100 * r['T_sortie']:.1f} %, NTU = {r['NTU']:.2f}\n"
         f"Chaleur par m² de face   {q(r['T_sortie']):.2f} kW/m² (10 K d'écart air / paroi)\n"
         f"Coefficient d'échange    h = {r['h']:.1f} W/m²K (sur tubes + ailettes)\n"
         f"Part des ailettes        {100 * r['part_ailettes']:.0f} % de la chaleur\n"
         f"Bilan d'énergie          écart air / paroi {100 * r['ecart_bilan']:+.2f} %\n"
         f"Convergence              Δp, T et flux stables à {100 * max(r['stabilite_moyenne'].values()):.2f} % près")
    ch = m["rangs"] / 4
    d2 = (f"Comparaison aux tubes nus, 4 rangs, 1 m/s\n"
          f"  charge R290   × {ch:.2f}   (même tube, {m['rangs']} rangs au lieu de 4)\n"
          f"  Δp            {r['dp_Pa']:6.2f} Pa   contre {nus['dp_Pa']:.2f}  (× {r['dp_Pa'] / nus['dp_Pa']:.1f})\n"
          f"  efficacité    {100 * r['T_sortie']:6.1f} %    contre {100 * nus['T_sortie']:.1f}  "
          f"(× {r['T_sortie'] / nus['T_sortie']:.1f})\n"
          f"  Q face        {q(r['T_sortie']):6.2f}      contre {q(nus['T_sortie']):.2f}\n"
          f"  Q / charge    {q(r['T_sortie']) / ch:6.2f}      contre {q(nus['T_sortie']):.2f}  "
          f"(× {q(r['T_sortie']) / ch / q(nus['T_sortie']):.1f})\n"
          f"  P vent / Q    {r['P_vent_sur_Q'] * 100:6.2f} ‰    contre {nus['P_vent_sur_Q'] * 100:.2f}  "
          f"({100 * (r['P_vent_sur_Q'] / nus['P_vent_sur_Q'] - 1):+.0f} %)")
    ax.text(0, 1, g, va="top", family="monospace", fontsize=9.5)
    ax.text(0.55, 1, d2, va="top", family="monospace", fontsize=9.5)
    fig.savefig(sortie, dpi=200)
    print(sortie)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
