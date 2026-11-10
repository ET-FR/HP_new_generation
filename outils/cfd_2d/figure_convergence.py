"""Figure de convergence en maillage du faisceau de tubes ronds (deux familles de maillages).

    python figure_convergence.py   ->  docs/formes/rond/convergence.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = Path(__file__).resolve().parents[2] / "docs" / "formes" / "rond"


def main():
    t = json.loads((D / "convergence_triangles.json").read_text())
    c = json.loads((D / "convergence_couches.json").read_text())

    def ser(e, k):
        noms = ("grossier", "moyen", "fin")
        return [e["cellules"][n] for n in noms], [e["grandeurs"][k][n] for n in noms]

    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Convergence en maillage, faisceau de tubes ronds (1 m/s) : triangles seuls et anneaux de couches",
                 fontweight="bold")
    for a, k, lab, yl in ((ax[0], "dp_Pa", "Δp (Pa)", (3.9, 5.2)), (ax[1], "Nu_D6", "Nu (Ø 6 mm)", (13.0, 15.5))):
        for e, coul, nom in ((t, "#adb5bd", "triangles seuls"), (c, "#1c7ed6", "anneaux de couches")):
            N, v = ser(e, k)
            a.plot(N, v, "o-", color=coul, lw=2, label=nom)
            for n, x in zip(N, v):
                a.annotate(f"{x:.2f}", (n, x), textcoords="offset points", xytext=(0, 8), ha="center",
                           fontsize=8, color=coul)
        a.set_xscale("log"); a.set_xlabel("nombre de mailles"); a.set_ylabel(lab); a.set_ylim(*yl); a.grid(alpha=.3)
    ax[0].axhline(5.016, color="k", ls="--", lw=1, label="Zukauskas (abaques) 5,02 Pa")
    ax[0].axhspan(4.28, 4.48, color="#d0ebff", alpha=.5, label="plage 4,28 à 4,48 Pa")
    ax[0].set_title("Perte de charge : toutes les valeurs entre 4,28 et 4,48 Pa (±2,5 %)", fontsize=9.5)
    ax[1].axhspan(14.0, 14.4, color="#d0ebff", alpha=.5, label="plage 14,0 à 14,4")
    ax[1].set_title("Échange : les deux familles convergent vers Nu ≈ 14,2", fontsize=9.5)
    ax[0].legend(fontsize=8); ax[1].legend(fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(D / "convergence.png", dpi=300)


if __name__ == "__main__":
    main()
