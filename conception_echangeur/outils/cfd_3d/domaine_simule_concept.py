#!/usr/bin/env python3
"""Domaine réellement simulé (concept imprimé) : frontières du maillage (paroi, entrée, sortie, côtés, faces périodiques)
écrites en STL allégés (mm), pour la vue 3D du document (html_radial.py). La version « avec » est décalée en x.

    .venv/bin/python conception_echangeur/outils/cfd_3d/domaine_simule_concept.py <cas_sans> <cas_avec>
"""
import json
import sys
from pathlib import Path

import pyvista as pv

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs/formes/cylindre_radial/variante_f/imprime/cfd"
DECALAGE_X = {"sans": 0.0, "avec": 180.0}
CIBLE = {"paroi": 160000, "entree": 6000, "sortie": 4000, "cotes": 2000, "y0": 20000, "y1": 20000}


def main(cas_liste):
    SORTIE.mkdir(parents=True, exist_ok=True)
    info = {}
    for c in cas_liste:
        cas = Path(c)
        v = json.loads((cas / "cas.json").read_text())["version"]
        (cas / "cas.foam").touch()
        r = pv.OpenFOAMReader(str(cas / "cas.foam"))
        r.enable_all_patch_arrays()
        r.cell_to_point_creation = False
        bord = r.read()["boundary"]
        info[v] = {}
        for nom, cible in CIBLE.items():
            if nom not in bord.keys():
                continue
            s = bord[nom].extract_surface().triangulate().clean()
            aire = s.area * 1e6
            if s.n_cells > cible:
                s = s.decimate(1 - cible / s.n_cells)
            s = s.scale(1e3).translate((DECALAGE_X[v], 0, 0))
            s.save(SORTIE / f"domaine_{v}_{nom}.stl")
            info[v][nom] = {"faces_maillage": int(bord[nom].n_cells), "aire_mm2": round(aire, 1)}
            print(v, nom, bord[nom].n_cells, "→", s.n_cells, flush=True)
    (SORTIE / "domaine_simule.json").write_text(json.dumps(dict(decalage_x=DECALAGE_X, versions=info), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
