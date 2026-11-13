"""Figure d'un maillage à anneaux de couches (cas OpenFOAM, VTK_maillage/ via foamToVTK -constant).

    python figure_maillage_couches.py dossier_du_cas sortie.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_polymesh as fp  # noqa: E402


def main(cas, sortie):
    fp.VTK_DIR = "VTK_maillage"
    cas = Path(cas)
    P, K, B, st = fp.charger(cas)
    m = json.loads((cas / "cas.json").read_text())
    c, Pt = m["couches"], m["Pt"] * 1e3
    x1 = m["x_noyau"][1] * 1e3
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle(f"{m['nom']} : maillage à anneaux de couches structurées\n"
                 f"{len(P)} mailles dont {int((K == 4).sum())} quadrilatères ; {c['n']} couches, 1re de "
                 f"{c['premiere']:.3f} mm, raison {c['raison']}, épaisseur {c['epaisseur']:.2f} mm ; "
                 f"non-orthogonalité max {st['nonortho']:.0f}°", fontsize=11.5, fontweight="bold")
    ax = fig.add_axes([0.05, 0.55, 0.9, 0.33]); fp.dessiner(ax, P, K, B, (-2, x1 + 1), (-0.3, Pt + 0.3), lw=0.12)
    ax.set_title("Noyau de la batterie : anneaux de quadrilatères autour de chaque tube", fontsize=9.5)
    cx = m["x_noyau"][0] * 1e3 + (m["Pl"] * 1e3)       # tube coupé par le bord bas (2e rang)
    ax = fig.add_axes([0.05, 0.06, 0.42, 0.42]); fp.dessiner(ax, P, K, B, (cx - 4, cx + 6), (-0.3, 5), lw=0.2)
    ax.set_title("Zoom : tube coupé par le bord bas", fontsize=9.5)
    ax = fig.add_axes([0.53, 0.06, 0.42, 0.42]); fp.dessiner(ax, P, K, B, (5.5, 6.6), (Pt / 2 - 0.6, Pt / 2 + 0.6), lw=0.3)
    ax.set_title("Zoom paroi : couches fines contre le tube", fontsize=9.5)
    fig.savefig(sortie, dpi=300)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
