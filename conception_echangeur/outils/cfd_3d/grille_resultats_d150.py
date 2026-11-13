"""Rééchantillonne les champs finaux d'un cas CFD Ø 150 sur une grille régulière (pour la vue 3D à coupes).

Tourne sur la machine de calcul, dans le dossier du cas reconstruit (reconstructPar -latestTime fait).
Chaque point de la grille prend la valeur de la maille OpenFOAM qui le contient (valeurs par maille, pas
d'interpolation) ; les points hors du fluide (tubes, ailette, parois, extérieur) sont marqués 255.
Champs : p (Pa), |U| (m/s), Uz (m/s), Tf, Tp, taille de maille (mm, racine cubique du volume).
Sortie : grille.json (origine, pas, dimensions, bornes) + grille_<champ>.u8.gz (uint8, ordre x le plus rapide).

    python3 grille_resultats_d150.py <cas> [pas_mm]
"""
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyvista as pv

cas = Path(sys.argv[1]).resolve()
pas = float(sys.argv[2]) * 1e-3 if len(sys.argv) > 2 else 1.5e-3
(cas / "cas.foam").touch()
t0 = time.time()
r = pv.OpenFOAMReader(str(cas / "cas.foam"))
r.set_active_time_value(max(r.time_values))
r.disable_all_patch_arrays()
r.enable_patch_array("internalMesh")
r.cell_to_point_creation = False
m = r.read()["internalMesh"]
m = m.compute_cell_sizes(length=False, area=False, volume=True)
m.cell_data["taille"] = np.cbrt(np.abs(m.cell_data["Volume"])) * 1e3
U = m.cell_data["U"]
m.cell_data["Umag"] = np.linalg.norm(U, axis=1)
m.cell_data["Uz"] = U[:, 2]
m.cell_data["pPa"] = m.cell_data["p"] * 1.204
print("maillage lu", m.n_cells, "mailles", round(time.time() - t0), "s", flush=True)

b = np.array(m.bounds)
o = b[0::2]
n = (np.ceil((b[1::2] - o) / pas)).astype(int) + 1
print("grille", n, int(np.prod(n)), "points", flush=True)
g = pv.ImageData(dimensions=n, spacing=(pas, pas, pas), origin=o)
champs = {"p": ("pPa", "p (Pa)"), "U": ("Umag", "|U| (m/s)"), "Uz": ("Uz", "U vertical (m/s)"),
          "Tf": ("Tf", "Tf (ailette froide)"), "Tp": ("Tp", "Tp (ailette passive)"), "taille": ("taille", "taille de maille (mm)")}
s = g.sample(m, pass_cell_data=True, mark_blank=False)
valide = s.point_data["vtkValidPointMask"].astype(bool)
print("échantillonné", valide.sum(), "points dans le fluide", round(time.time() - t0), "s", flush=True)

meta = dict(origine_mm=(o * 1e3).tolist(), pas_mm=pas * 1e3, dim=n.tolist(), mailles=int(m.n_cells), champs={})
for cle, (nom, titre) in champs.items():
    v = np.asarray(s.point_data[nom], dtype=float)
    lo, hi = np.percentile(v[valide], [0.1, 99.9]) if cle in ("p", "U", "Uz") else (v[valide].min(), v[valide].max())
    if cle in ("Tf", "Tp"):
        lo, hi = 0.0, 1.0
    q = np.clip(np.round((v - lo) / (hi - lo) * 254), 0, 254).astype(np.uint8)
    q[~valide] = 255
    (cas / f"grille_{cle}.u8.gz").write_bytes(gzip.compress(q.tobytes(), 9))
    meta["champs"][cle] = dict(titre=titre, min=float(lo), max=float(hi),
                               min_reel=float(v[valide].min()), max_reel=float(v[valide].max()))
(cas / "grille.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
print(json.dumps(meta, indent=1, ensure_ascii=False))
print("fini", round(time.time() - t0), "s")
