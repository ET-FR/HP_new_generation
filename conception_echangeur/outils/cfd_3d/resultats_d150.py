"""Résultats d'un cas CFD de l'échangeur Ø 150 (creer_cas_d150.py) : ε, NTU, hA, perte de charge, ventilateur.

Moyenne sur les dernières itérations (défaut 500) des mesures de postProcessing/, plus l'écart (max − min)
sur cette fenêtre comme indicateur de convergence. Écrit <cas>/resultat.json et rend les coupes finales
(vitesse, Tf, Tp) en PNG dans <cas>/.

    .venv/bin/python conception_echangeur/outils/cfd_3d/resultats_d150.py conception_echangeur/cfd_campagne/d150_helice/U5
"""
import json
import math
import sys
from pathlib import Path

import numpy as np


def serie(cas, nom):
    f = next((cas / "postProcessing" / nom).glob("*/surfaceFieldValue.dat"))
    a = np.loadtxt(f, comments="#")
    return a


def fenetre(a, n):
    it = a[:, 0]
    sel = it > it.max() - n
    v = a[sel, 1:]
    return v.mean(axis=0), v.max(axis=0) - v.min(axis=0)


def main(cas: Path, n=500):
    meta = json.loads((cas / "cas.json").read_text())
    air = meta["air"]
    rho, cp = air["rho"], air["cp"]
    r = {}
    for nom in ("pEntree", "pSortie", "pEntreeDebit", "pSortieDebit", "TSortie", "debitEntree", "debitSortie"):
        m, e = fenetre(serie(cas, nom), n)
        r[nom] = (m, e)
    Q = -r["debitEntree"][0][0]                       # m³/s (flux entrant négatif)
    mdot = rho * Q
    C = mdot * cp
    dp = rho * (r["pEntree"][0][0] - r["pSortie"][0][0])
    dp_debit = rho * (r["pEntreeDebit"][0][0] - r["pSortieDebit"][0][0])
    res = dict(U_conduit=meta["U_conduit"], debit_m3h=Q * 3600, debit_kg_s=mdot, mCp_W_K=C,
               perte_charge_Pa=dp, perte_charge_ponderee_debit_Pa=dp_debit,
               ecart_perte_charge_Pa=rho * r["pEntree"][1][0],
               puissance_ventilateur_W_eta03=Q * dp / 0.3, desequilibre_debit=abs(r["debitEntree"][0][0] + r["debitSortie"][0][0]) / Q,
               fenetre_iterations=n)
    for i, (cle, titre) in enumerate((("Tf", "ailette froide"), ("Tp", "ailette passive"))):
        eps = r["TSortie"][0][i]
        ntu = -math.log(1 - eps)
        res[cle] = dict(titre=titre, epsilon=eps, ecart_epsilon=r["TSortie"][1][i], NTU=ntu, hA_W_K=ntu * C,
                        W_par_K_d_ecart=eps * C)
    yp = cas / "postProcessing/yPlus"
    fy = next(yp.glob("*/yPlus.dat"), None)
    if fy:
        lignes = [l.split() for l in fy.read_text().splitlines() if l.strip() and not l.startswith("#")]
        der = {}
        for l in lignes:
            der[l[1]] = dict(min=float(l[2]), max=float(l[3]), moyenne=float(l[4]))
        res["yPlus"] = der
    (cas / "resultat.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))
    rendus(cas)


def rendus(cas: Path):
    import pyvista as pv
    pv.OFF_SCREEN = True
    d = cas / "postProcessing/coupes"
    fin = max((x for x in d.iterdir() if x.name != "0"), key=lambda x: float(x.name))
    for coupe, cam in (("meridienne", [(0.6, 0, 0.2), (0, 0, 0.197), (0, 0, 1)]),
                       ("horizontale_mil", [(0, 0, 0.7), (0, 0, 0.197), (0, 1, 0)]),
                       ("horizontale_bas", [(0, -0.02, 0.6), (0, -0.02, 0.05), (0, 1, 0)])):
        f = fin / f"{coupe}.vtp"
        if not f.exists():
            continue
        m = pv.read(f)
        if "U" in m.array_names:
            m["|U| (m/s)"] = np.linalg.norm(m["U"], axis=1)
        if "p" in m.array_names:
            m["p (Pa)"] = m["p"] * 1.204
        for champ, cmap, clim in (("p (Pa)", "coolwarm", None), ("|U| (m/s)", "viridis", None), ("Tf", "inferno", (0, 1)),
                                  ("Tp", "inferno", (0, 1))):
            if champ not in m.array_names:
                continue
            pl = pv.Plotter(window_size=(1300, 1100))
            pl.set_background("white")
            pl.add_mesh(m, scalars=champ, cmap=cmap, clim=clim, scalar_bar_args=dict(title=champ, color="black"))
            pl.camera_position = cam
            pl.enable_parallel_projection()
            pl.add_text(f"{coupe} · {champ}", font_size=12, color="black")
            pl.screenshot(cas / f"coupe_{coupe}_{champ.split()[0].replace('|', '')}.png")
            pl.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), int(sys.argv[2]) if len(sys.argv) > 2 else 500)
