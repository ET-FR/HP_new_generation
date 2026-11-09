"""Figure du cas de validation « tube isolé » : sillage, température, efforts, spectre.

    python figure_tube_isole.py dossier_du_cas sortie.png
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
from matplotlib.patches import Circle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extraire import serie  # noqa: E402


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    r = json.loads((cas / "resultat.json").read_text())
    d = sorted([p for p in (cas / "VTK_resultats").glob("*_[0-9]*") if p.is_dir()], key=lambda p: int(p.name.rsplit("_", 1)[1]))[-1]
    v = pv.read(d / "internal.vtu")
    s = v.slice(normal="z", origin=(0, 0, 0.5 * (v.bounds[4] + v.bounds[5])))
    P, f, i = [], s.faces, 0
    while i < len(f):
        n = f[i]; P.append(s.points[f[i + 1:i + 1 + n]][:, :2] * 1e3); i += n + 1
    D = m["D"] * 1e3
    fig = plt.figure(figsize=(15, 14))
    fig.suptitle(f"Validation niveau 0 : tube rond isolé Ø {D:g} mm, air 1 m/s, Re = {r['Re']:.0f}, "
                 "OpenFOAM v2606 (pimpleFoam laminaire instationnaire)", fontsize=12, fontweight="bold", y=0.99)
    champs = [(np.linalg.norm(s.cell_data["U"], axis=1), "turbo", (0, 1.6),
               "(a) Vitesse instantanée : allée de tourbillons de Bénard-von Kármán derrière le tube", "|U| (m/s)"),
              (np.linalg.norm(s.cell_data["UMean"], axis=1), "turbo", (0, 1.6),
               "(b) Vitesse moyennée : zone de recirculation derrière le tube, air accéléré sur les côtés", "|U| moy. (m/s)"),
              (s.cell_data["T"], "inferno", (0, 1),
               "(c) Température instantanée : la chaleur du tube est emportée par les tourbillons", "T (-)")]
    for k, (val, cmap, lim, titre, unite) in enumerate(champs):
        ax = fig.add_axes([0.04, 0.745 - k * 0.222, 0.90, 0.20])
        pc = PolyCollection(P, array=val, cmap=cmap, edgecolors="face", linewidths=0.3)
        pc.set_clim(*lim); ax.add_collection(pc)
        ax.add_patch(Circle((0, 0), D / 2, color="#adb5bd", zorder=3))
        ax.set_xlim(-12, 110); ax.set_ylim(-16, 16); ax.set_aspect("equal"); ax.tick_params(labelsize=7)
        ax.set_title(titre, fontsize=9.5, pad=3)
        cb = fig.colorbar(pc, ax=ax, fraction=0.012, pad=0.01); cb.set_label(unite, fontsize=8)
    c = serie(cas, "efforts", "coefficient.dat")
    ent = None
    for fch in (cas / "postProcessing" / "efforts").glob("*/coefficient.dat"):
        for l in fch.read_text().splitlines():
            if l.startswith("#") and "Cd" in l:
                ent = l.lstrip("#").split()
        break
    t, Cd, Cl = c[:, 0], c[:, ent.index("Cd")], c[:, ent.index("Cl")]
    ax = fig.add_axes([0.05, 0.05, 0.40, 0.21])
    ax.plot(t, Cl, color="#1c7ed6", lw=0.8, label="Cl (portance)")
    ax.plot(t, Cd, color="#e03131", lw=1.2, label="Cd (traînée)")
    ax.axvline(m["debut_moyenne"], color="k", ls="--", lw=1); ax.text(m["debut_moyenne"], 2.6, " début de la moyenne", fontsize=8)
    ax.set_ylim(-2.5, 3); ax.set_xlabel("temps simulé (s)"); ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)
    ax.set_title("(d) Efforts sur le tube : démarrage, puis oscillation régulière", fontsize=9.5)
    ax = fig.add_axes([0.52, 0.05, 0.20, 0.21])
    msk = t >= m["debut_moyenne"]
    tu = np.linspace(t[msk][0], t[msk][-1], 2 ** 14)
    sgl = np.interp(tu, t[msk], Cl[msk]); sgl -= sgl.mean()
    sp = np.abs(np.fft.rfft(sgl * np.hanning(len(sgl)))); fr = np.fft.rfftfreq(len(sgl), tu[1] - tu[0])
    ax.plot(fr, sp / sp.max(), color="#1c7ed6"); ax.set_xlim(0, 150)
    ax.axvline(r["f_Hz"], color="k", ls=":", lw=1)
    ax.set_xlabel("fréquence (Hz)"); ax.set_title(f"(e) Spectre de Cl : pic à {r['f_Hz']:.1f} Hz", fontsize=9.5)
    ax.grid(alpha=0.3)
    ax = fig.add_axes([0.75, 0.05, 0.24, 0.21]); ax.axis("off")
    ax.text(0, 1, "COMPARAISON AUX RÉFÉRENCES\n\n"
            f"Nu   CFD {r['Nu']:6.2f}\n"
            f"     Hilpert          {r['Nu_Hilpert']:5.2f}  ({100 * (r['Nu'] / r['Nu_Hilpert'] - 1):+.0f} %)\n"
            f"     Churchill-Bern.  {r['Nu_Churchill_Bernstein']:5.2f}  ({100 * (r['Nu'] / r['Nu_Churchill_Bernstein'] - 1):+.0f} %)\n\n"
            f"St   CFD {r['St']:6.3f}\n"
            f"     Roshko           {r['St_Roshko']:5.3f}  ({100 * (r['St'] / r['St_Roshko'] - 1):+.0f} %)\n\n"
            f"Cd   CFD {r['Cd']:6.2f}\n"
            "     essais ≈ 1,1 à 1,2 ; le 2D\n"
            "     surestime (sillage réel 3D)\n\n"
            f"{r['periodes_moyennees']:.0f} périodes moyennées\n"
            f"stabilité : Cd {100 * r['stabilite_moyenne']['Cd']:.2f} %, Nu {100 * r['stabilite_moyenne']['Nu']:.2f} %",
            va="top", family="monospace", fontsize=9)
    fig.savefig(sortie, dpi=110)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
