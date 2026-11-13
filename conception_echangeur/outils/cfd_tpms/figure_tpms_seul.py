#!/usr/bin/env python3
"""Figure d'un cas « TPMS seul » terminé (outils/cfd_3d/creer_cas_tpms_seul.py) : vitesse, température,
coupes dans le plan de la face, pression le long du bloc, chiffres clés.

La cellule calculée (L × L en section) est répétée 3 fois en y pour la lecture (périodicité exacte).

    python outils/cfd_tpms/figure_tpms_seul.py dossier_du_cas sortie.png
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

OPENFOAM = "/usr/lib/openfoam/openfoam2412/etc/bashrc"
REPET = 3


def vtk(cas: Path):
    d = cas / "VTK_res"
    if not d.exists():
        subprocess.run(["bash", "-c", f"source {OPENFOAM}; cd '{cas}'; foamToVTK -latestTime -noFunctionObjects "
                        f"-fields '(U p T)' -name VTK_res > log.vtk_res 2>&1"], check=True)
    sous = sorted(p for p in d.iterdir() if p.is_dir())
    return pv.read(sous[-1] / "internal.vtu"), sous[-1]


def polys(s, axes, champ, decal=None):
    s = s.cell_data_to_point_data() if champ not in s.point_data else s
    P, V, f, i = [], [], s.faces, 0
    vals = s.point_data[champ]
    if vals.ndim > 1:
        vals = np.linalg.norm(vals, axis=1)
    while i < len(f):
        n = f[i]; idx = f[i + 1:i + 1 + n]
        P.append(s.points[idx][:, axes] * 1e3); V.append(vals[idx].mean()); i += n + 1
    return P, np.array(V)


def trace(ax, s, axes, champ, cmap, vmin, vmax, repet_axe=None, L=None):
    P, V = polys(s, axes, champ)
    tout_P, tout_V = [], []
    for k in range(REPET if repet_axe is not None else 1):
        for p in P:
            q = p.copy()
            if repet_axe is not None:
                q[:, repet_axe] += k * L
            tout_P.append(q)
        tout_V.append(V)
    pc = PolyCollection(tout_P, array=np.concatenate(tout_V), cmap=cmap, edgecolors="face", linewidths=0.05)
    pc.set_clim(vmin, vmax)
    ax.add_collection(pc)
    ax.set_facecolor("white")
    return pc


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    r = json.loads((cas / "resultat.json").read_text())
    vol, dvtk = vtk(cas)
    L, D = m["cellule_tpms_mm"], m["profondeur_mm"]
    Lm, Dm = L * 1e-3, D * 1e-3
    x0, x1 = m["x_domaine"][0] * 1e3, m["x_domaine"][1] * 1e3
    rho = m["air"]["rho"]

    fig = plt.figure(figsize=(15, 15))
    fig.suptitle(f"Résultat CFD 3D : {m['nom']}, bloc de {D:.1f} mm, air {m['U']:g} m/s en façade\n"
                 f"Même charge de propane que l'ellipse 2:1 à ailettes, 2 rangs ({m['propane_L_par_m2']:.2f} L/m²) ; "
                 "OpenFOAM snappyHexMesh + simpleFoam laminaire, " + f"{vol.n_cells:,}".replace(",", " ") + " mailles",
                 fontsize=12.5, fontweight="bold", y=0.995)
    fig.set_size_inches(15, 13)
    gs = fig.add_gridspec(3, 6, height_ratios=[1.25, 1, 0.8], hspace=0.32, wspace=0.6,
                          left=0.05, right=0.95, top=0.92, bottom=0.05)
    coupe = vol.slice(normal="z", origin=(0, 0, 0.5 * Lm))
    umax = float(np.percentile(np.linalg.norm(vol.cell_data["U"], axis=1), 99.5))
    for k, (champ, cmap, vmin, vmax, titre, lab) in enumerate((
            ("U", "turbo", 0, umax, "(a) Vitesse de l'air, coupe à mi-hauteur\n(3 cellules ; blanc = paroi + propane)", "|U| (m/s)"),
            ("T", "inferno", 0, 1, "(b) Température de l'air, même coupe\n(0 = air entrant, 1 = paroi)", "T (-)"))):
        ax = fig.add_subplot(gs[0, 3 * k:3 * k + 3])
        pc = trace(ax, coupe, [0, 1], champ, cmap, vmin, vmax, repet_axe=1, L=L)
        for xv in (0, D):
            ax.axvline(xv, color="#adb5bd", lw=0.8, ls="--")
        ax.set_xlim(x0, x1); ax.set_ylim(0, REPET * L); ax.set_aspect("equal")
        ax.set_title(titre, fontsize=10); ax.set_ylabel("y (mm)", fontsize=8); ax.tick_params(labelsize=7)
        ax.set_xlabel("x, sens de l'air (mm) ; bloc entre les pointillés", fontsize=8)
        fig.colorbar(pc, ax=ax, fraction=0.04, pad=0.02).set_label(lab, fontsize=8)
    # coupes dans le plan de la face
    for k, fx in enumerate((0.25, 0.5, 0.9)):
        ax = fig.add_subplot(gs[1, 2 * k:2 * k + 2])
        s = vol.slice(normal="x", origin=(fx * Dm, 0, 0))
        pc = trace(ax, s, [1, 2], "T", "inferno", 0, 1)
        ax.set_xlim(0, L); ax.set_ylim(0, L); ax.set_aspect("equal")
        ax.set_title(f"(c{k + 1}) Température, plan de la face à x = {fx * D:.1f} mm", fontsize=9)
        ax.set_xlabel("y (mm)", fontsize=8); ax.set_ylabel("z (mm)", fontsize=8); ax.tick_params(labelsize=7)
    fig.colorbar(pc, ax=fig.axes[-3:], fraction=0.012, pad=0.01).set_label("T (-)", fontsize=8)
    # pression et température moyennes le long de x
    xs = np.linspace(x0 * 1e-3 + 1e-5, x1 * 1e-3 - 1e-5, 90)
    pm, Tm = [], []
    for x in xs:
        s = vol.slice(normal="x", origin=(x, 0, 0)).compute_cell_sizes(length=False, volume=False)
        a = s.cell_data["Area"]
        ux = s.cell_data["U"][:, 0]
        pm.append(rho * float(np.sum(s.cell_data["p"] * a) / np.sum(a)))
        Tm.append(float(np.sum(s.cell_data["T"] * ux * a) / np.sum(ux * a)) if np.sum(ux * a) > 0 else np.nan)
    ax = fig.add_subplot(gs[2, :4])
    ax.axvspan(0, D, color="#e9ecef", zorder=0)
    ax.plot(xs * 1e3, pm, color="#5f3dc4", lw=1.8, label="pression moyenne (Pa)")
    ax.set_xlabel("x (mm)", fontsize=8); ax.set_ylabel("p moyenne (Pa)", fontsize=8, color="#5f3dc4")
    ax.tick_params(labelsize=7); ax.grid(True, color="#e9ecef", lw=0.6)
    ax2 = ax.twinx()
    ax2.plot(xs * 1e3, Tm, color="#d9480f", lw=1.8)
    ax2.set_ylim(0, 1); ax2.set_ylabel("T de mélange (-)", fontsize=8, color="#d9480f"); ax2.tick_params(labelsize=7)
    ax.set_title("(d) Le long du domaine : la pression chute et l'air chauffe dans le bloc (zone grise)", fontsize=9.5)
    # chiffres clés
    ax = fig.add_subplot(gs[2, 4:]); ax.axis("off")
    q = rho * m["air"]["cp"] * m["U"] * r["T_sortie"] * 10 / 1e3
    ax.text(0, 1, "\n".join([
        f"Perte de charge      {r['dp_Pa']:.1f} Pa",
        f"Efficacité           {100 * r['T_sortie']:.1f} %  (NTU {r['NTU']:.2f})",
        f"Chaleur par m² face  {q:.2f} kW/m² (10 K)",
        f"P vent / Q           {r['P_vent_sur_Q'] * 100:.2f} ‰",
        f"h côté air           {r['h']:.0f} W/m²K",
        "",
        f"Cellule {L:g} mm, paroi {m['paroi_mm']:g} mm",
        f"air / paroi / propane  {100 * m['fraction_air']:.0f} / {100 * m['fraction_paroi']:.0f} / "
        f"{100 * m['fraction_propane']:.0f} %",
        f"Dh air {m['Dh_air_mm']:.2f} mm, Re {m['Re_Dh']:.0f}",
        f"Bilan de chaleur {100 * r['ecart_bilan']:+.2f} %",
        f"Stabilité {100 * max(r['stabilite_moyenne'].values()):.2f} %",
        "",
        "Ellipse 2:1 à ailettes, 2 rangs,",
        "même charge : 5,4 Pa, 72,4 %"]),
        family="monospace", fontsize=8.5, va="top")
    fig.savefig(sortie, dpi=150)
    print(sortie)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
