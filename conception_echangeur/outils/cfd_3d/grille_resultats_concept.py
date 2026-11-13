#!/usr/bin/env python3
"""Rééchantillonne les champs finaux d'un cas 3D du concept imprimé sur une grille régulière (vue 3D à coupes x, y, z
du rapport, html_radial.py). Chaque point prend la valeur de la maille qui le contient ; hors du fluide : 255.
Champs : |U| (m/s), θ = T (0 = air entrant, 1 = paroi), p (Pa, relative à la sortie).
Sortie : docs/formes/cylindre_radial/variante_f/imprime/cfd/grille_<version>.json (méta + champs uint8 gzip base64).

    .venv/bin/python conception_echangeur/outils/cfd_3d/grille_resultats_concept.py <cas> [pas_mm]
"""
import base64
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs/formes/cylindre_radial/variante_f/imprime/cfd"


def main(cas, pas_mm=0.33):
    cas = Path(cas)
    meta = json.loads((cas / "cas.json").read_text())
    v = ("secteur_" if meta.get("cas") == "secteur" else "") + meta["version"]
    rho = meta["air"]["rho"]
    (cas / "cas.foam").touch()
    r = pv.OpenFOAMReader(str(cas / "cas.foam"))
    r.set_active_time_value(max(r.time_values))
    r.disable_all_patch_arrays()
    r.enable_patch_array("internalMesh")
    r.cell_to_point_creation = False
    m = r.read()["internalMesh"]
    m.cell_data["Umag"] = np.linalg.norm(m.cell_data["U"], axis=1)
    m.cell_data["pPa"] = m.cell_data["p"] * rho
    pas = pas_mm * 1e-3
    b = np.array(m.bounds)
    o = b[0::2]
    n = (np.ceil((b[1::2] - o) / pas)).astype(int) + 1
    g = pv.ImageData(dimensions=n, spacing=(pas, pas, pas), origin=o)
    s = g.sample(m, pass_cell_data=True, mark_blank=False)
    ok = s.point_data["vtkValidPointMask"].astype(bool)
    print(v, "grille", n.tolist(), int(np.prod(n)), "points,", int(ok.sum()), "dans le fluide", flush=True)
    champs = {"U": ("Umag", "|U| (m/s)"), "T": ("T", "θ (0 = air entrant, 1 = paroi)"), "p": ("pPa", "p (Pa, par rapport à la sortie)")}
    out = dict(version=v, origine_mm=(o * 1e3).tolist(), pas_mm=pas_mm, dim=n.tolist(), champs={})
    for cle, (nom, titre) in champs.items():
        val = np.asarray(s.point_data[nom], dtype=float)
        lo, hi = (0.0, 1.0) if cle == "T" else tuple(np.percentile(val[ok], [0.1, 99.9]))
        if cle == "p":
            lo = 0.0
        q = np.clip(np.round((val - lo) / (hi - lo) * 254), 0, 254).astype(np.uint8)
        q[~ok] = 255
        out["champs"][cle] = dict(titre=titre, min=float(lo), max=float(hi), max_reel=float(val[ok].max()),
                                  donnees=base64.b64encode(gzip.compress(q.tobytes(), 9)).decode())
        print(v, cle, round(len(out["champs"][cle]["donnees"]) / 1e6, 2), "Mo", flush=True)
    (SORTIE / f"grille_{v}.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main(sys.argv[1], *(float(x) for x in sys.argv[2:3]))
