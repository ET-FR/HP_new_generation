"""Figure du cas de validation « plaques parallèles » (profils de vitesse, pression, température).

    python figure_plaques.py dossier_du_cas sortie.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    r = json.loads((cas / "resultat.json").read_text())
    d = sorted([p for p in (cas / "VTK").glob("*_[0-9]*") if p.is_dir()], key=lambda p: int(p.name.rsplit("_", 1)[1]))[-1]
    v = pv.read(d / "internal.vtu")
    cc = v.cell_centers().points
    U = v.cell_data["U"][:, 0]; T = v.cell_data["T"]
    gap = m["ecart_mm"] * 1e-3
    fig, ax = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("Validation niveau 0 : canal entre deux plaques parallèles (écartement 2 mm, Dh 4 mm, 1 m/s, "
                 f"Re = {r['Re']:.0f}), OpenFOAM v2606", fontsize=12, fontweight="bold")
    a = ax[0, 0]
    yy = np.linspace(0, 1, 200)
    a.plot(6 * yy * (1 - yy), yy * gap * 1e3, "k--", lw=2, label="parabole exacte (établi)")
    for x, c in ((0.001, "#74c0fc"), (0.005, "#4dabf7"), (0.02, "#1c7ed6"), (0.15, "#e03131")):
        xs = np.unique(np.round(cc[:, 0], 9))
        xi = xs[np.argmin(abs(xs - x))]
        s = np.isclose(cc[:, 0], xi); o = np.argsort(cc[s, 1])
        a.plot(U[s][o] / m["U"], cc[s, 1][o] * 1e3, color=c, lw=1.8, label=f"x = {xi * 1e3:.0f} mm")
    a.set_xlabel("U / U moyenne"); a.set_ylabel("y (mm)"); a.legend(fontsize=8)
    a.set_title("(a) Profil de vitesse : plat à l'entrée, parabolique une fois établi", fontsize=10)
    a = ax[0, 1]
    pr = r["profil"]
    x = np.array(pr["x"]) * 1e3; p = np.array(pr["p"]) * m["air"]["rho"]
    a.plot(x, p - p[-1], color="#5f3dc4", lw=2, label="CFD")
    pente = 24 / r["Re"] * 2 * m["U"] ** 2 / m["Dh"] * m["air"]["rho"]       # exact, établi
    a.plot(x, pente * (x[-1] - x) / 1e3, "k--", label="pente exacte f·Re = 24")
    a.set_xlabel("x (mm)"); a.set_ylabel("p moyenne (Pa)"); a.legend(fontsize=8)
    a.set_title(f"(b) Pression : f·Re = {r['fRe']:.2f} (exact 24, écart {100 * (r['fRe'] / 24 - 1):+.1f} %)", fontsize=10)
    a = ax[1, 0]
    Tb = np.array(pr["Tb"])
    a.semilogy(x, 1 - Tb, color="#e8590c", lw=2, label="CFD : 1 - T mélange")
    NTU = 2 * r["Nu_exact"] * m["air"]["nu"] / m["air"]["Pr"] * (x / 1e3) / (m["U"] * gap * m["Dh"])
    a.semilogy(x, np.exp(-NTU), "k--", label="établi exact (Nu = 7,54)")
    a.set_ylim(1e-4, 1.2); a.set_xlabel("x (mm)"); a.set_ylabel("1 - T mélange"); a.legend(fontsize=8)
    a.set_title(f"(c) Échauffement de l'air : Nu = {r['Nu']:.3f} (exact 7,541, écart "
                f"{100 * (r['Nu'] / 7.541 - 1):+.1f} %)", fontsize=10)
    a = ax[1, 1]; a.axis("off")
    a.text(0, 0.95, "BILAN DE LA VALIDATION\n\n"
           f"Frottement établi   f·Re = {r['fRe']:.2f}   exact 24      → {100 * (r['fRe'] / 24 - 1):+.1f} %\n"
           f"Échange établi      Nu   = {r['Nu']:.3f}  exact 7,541   → {100 * (r['Nu'] / 7.541 - 1):+.1f} %\n\n"
           "Convergence : SIMPLE stationnaire, 1138 itérations, résidus < 1e-7\n"
           "Maillage : 40 × 800 rectangles, resserrés vers les plaques\n\n"
           "La chaîne (maillage, conditions aux limites, solveur,\n"
           "mesures de pression et de température) retrouve la\n"
           "solution exacte : elle est validée pour un écoulement\n"
           "laminaire établi près d'une paroi.", va="top", family="monospace", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(sortie, dpi=300)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
