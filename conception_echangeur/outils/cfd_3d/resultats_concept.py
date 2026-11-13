#!/usr/bin/env python3
"""Dépouillement des cas 3D du concept imprimé (creer_cas_concept_imprime.py).

Grandeurs moyennées sur les `n_moy` dernières itérations (fluctuation = écart max / moyenne) :
  Δp = ρ (p_entrée − p_sortie) ; ε = T de mélange en sortie (T entrée 0, paroi 1) ; NTU = −ln(1 − ε) ;
  hA du tube complet = NTU · ṁcp (débit total du tube) ; bilan : chaleur reçue par la paroi (α ∫ ∇T·n) contre
  chaleur emportée (Q · T_sortie).
Images : vitesse et température dans une coupe y (dans un interstice) et une coupe radiale.
Sorties : docs/formes/cylindre_radial/variante_f/imprime/cfd/resultat_<version>.json et resultat_<version>_*.png

    .venv/bin/python conception_echangeur/outils/cfd_3d/resultats_concept.py <cas_resultats> [...]
(le dossier de résultats doit contenir constant/polyMesh ; sinon il est copié depuis ../../maillage/<version>)
"""
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs/formes/cylindre_radial/variante_f/imprime/cfd"
pv.OFF_SCREEN = True


def serie(cas, nom):
    f = sorted((cas / "postProcessing" / nom).glob("*/surfaceFieldValue.dat"))[-1]
    lignes = [l.split() for l in f.read_text().splitlines() if l and not l.startswith("#")]
    a = np.array([[float(x.strip("()")) for x in l] for l in lignes])
    return a


def moy(a, n, col=1):
    """Moyenne sur les n dernières ITÉRATIONS (les mesures sont écrites toutes les 10 itérations)."""
    pas = max(1, int(round(a[-1, 0] - a[-2, 0]))) if len(a) > 1 else 1
    v = a[-max(1, n // pas):, col]
    m = v.mean()
    return float(m), float((v.max() - v.min()) / abs(m)) if m else 0.0


def main(liste, n_moy=500):
    SORTIE.mkdir(parents=True, exist_ok=True)
    for c in liste:
        cas = Path(c)
        meta = json.loads((cas / "cas.json").read_text())
        v = ("secteur_" if meta.get("cas") == "secteur" else "") + meta["version"]
        rho, cp, nu, Pr = meta["air"]["rho"], meta["air"]["cp"], meta["air"]["nu"], meta["air"]["Pr"]
        n_fin = int(serie(cas, "pEntree")[-1, 0])
        if n_fin < 0.8 * meta.get("iterations", 3000):      # calcul convergé tôt (critère de résidus) : fin seule
            n_moy = 50
        pe, fe = moy(serie(cas, "pEntree"), n_moy)
        ps, _ = moy(serie(cas, "pSortie"), n_moy)
        ts, ft = moy(serie(cas, "TSortie"), n_moy)
        q, _ = moy(serie(cas, "debit"), n_moy)
        flux = serie(cas, "fluxParoi")
        # flux de grad(T) intégré : vecteur (3 comp.) ou scalaire selon la version → somme des composantes normales
        k = max(1, n_moy // 10)
        fl = float(flux[-k:, 1:].sum(axis=1).mean()) if flux.shape[1] > 2 else float(flux[-k:, 1].mean())
        dp = rho * (pe - ps)
        eps = ts
        ntu = -math.log(1 - eps)
        hA = ntu * meta["mcp_tube"]
        q_paroi = abs(fl) * nu / Pr            # m³/s · (unité de T) : chaleur cinématique reçue
        q_air = abs(q) * ts
        n_it = int(serie(cas, "pEntree")[-1, 0])
        res = dict(version=v, iterations=n_it, moyenne_sur=n_moy, dp_Pa=dp, fluctuation_dp=fe, efficacite=eps,
                   fluctuation_T=ft, NTU=ntu, hA_tube_W_K=hA, debit_tranche_m3s=abs(q), debit_impose_m3s=meta["debit_tranche_m3s"],
                   bilan_paroi_sur_air=q_paroi / q_air if q_air else None,
                   Q_tube_W_pour_10K=hA * 10 * (1 - math.exp(-ntu)) / ntu if ntu else None)
        # champs : dernière itération écrite
        if not (cas / "constant/polyMesh").exists():
            shutil.copytree(cas.parents[1] / "maillage" / v / "constant/polyMesh", cas / "constant/polyMesh")
        (cas / "cas.foam").touch()
        r = pv.OpenFOAMReader(str(cas / "cas.foam"))
        r.set_active_time_value(r.time_values[-1])
        r.cell_to_point_creation = True
        vol = r.read()["internalMesh"]
        per = meta["periode_mm"] * 1e-3
        U = vol["U"]
        vol["Umag"] = np.linalg.norm(U, axis=1)
        res["U_max_m_s"] = float(vol["Umag"].max())
        for nom, champ, clim, cmap, titre in (("vitesse", "Umag", [0, float(np.percentile(vol["Umag"], 99.5))], "viridis", "|U| (m/s)"),
                                             ("temperature", "T", [0, 1], "coolwarm", "θ = (T − T_air entrée) / (T_paroi − T_air entrée)")):
            for coupe, y in (("y", 1.25e-3),):
                s = vol.slice(normal=(0, 1, 0), origin=(0, y, 0))
                pl = pv.Plotter(off_screen=True, window_size=(1400, 1200))
                pl.set_background("white")
                pl.add_mesh(s, scalars=champ, clim=clim, cmap=cmap, scalar_bar_args=dict(title=titre, color="black", vertical=False,
                                                                                         position_x=0.2, position_y=0.04, width=0.6))
                pl.camera.position, pl.camera.focal_point, pl.camera.up = (0.005, -0.3, 0.0), (0.005, 0, 0.0), (0, 0, 1)
                if meta.get("cas") == "secteur":
                    pl.view_vector((0, -1, 0), viewup=(0, 0, 1)); pl.reset_camera(); pl.camera.zoom(1.3)
                pl.screenshot(SORTIE / f"resultat_{v}_{nom}_{coupe}.png")
                pl.close()
            # coupe radiale (φ = 20°), r 33 → 77 mm, en projection parallèle
            am = math.radians(sum(meta["secteur_deg"]) / 2 + 3.0 if meta.get("cas") == "secteur" else 20.0)
            n = (-math.sin(am), 0, math.cos(am))
            er = np.array([math.cos(am), 0, math.sin(am)])
            rad = vol.slice(normal=n, origin=(0, 0, 0)).clip(normal=tuple(-er), origin=(0, 0, 0), invert=True)
            pl = pv.Plotter(off_screen=True, window_size=(1600, 420))
            pl.set_background("white")
            pl.add_mesh(rad, scalars=champ, clim=clim, cmap=cmap, show_scalar_bar=False)
            c0 = er * 55e-3 + np.array([0, per / 2, 0])
            pl.camera.focal_point = tuple(c0)
            pl.camera.position = tuple(c0 + np.array(n) * 0.2)
            pl.camera.up = (0, 1, 0)
            pl.enable_parallel_projection()
            pl.camera.parallel_scale = 22e-3 * 420 / 1600 * 1.05
            pl.screenshot(SORTIE / f"resultat_{v}_{nom}_radial.png")
            pl.close()
        (SORTIE / f"resultat_{v}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
