#!/usr/bin/env python3
"""Vérifie et illustre le maillage 3D du concept imprimé (creer_cas_concept_imprime.py) avant le calcul.

Contrôles : pas de maille dans le solide (fuite), surfaces des patchs (entrée, sortie, paroi) contre la géométrie,
volume d'air contre le volume attendu, résumé de checkMesh. Images : coupe dans un interstice (plan y = cste),
coupe radiale (plan qui contient l'axe, entre deux profils) qui montre les lamelles décalées, zoom.
Sorties : docs/formes/cylindre_radial/variante_f/imprime/cfd/maillage_<version>_*.png et maillage_<version>.json

    .venv/bin/python conception_echangeur/outils/cfd_3d/verifier_maillage_concept.py <cas> [<cas> ...]
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs/formes/cylindre_radial/variante_f/imprime/cfd"
pv.OFF_SCREEN = True


def lire(cas):
    (cas / "cas.foam").touch()
    r = pv.OpenFOAMReader(str(cas / "cas.foam"))
    r.enable_all_patch_arrays()
    r.cell_to_point_creation = False
    m = r.read()
    return m["internalMesh"], m["boundary"]


def check_mesh(cas):
    t = (cas / "log.checkMesh").read_text(errors="ignore") if (cas / "log.checkMesh").exists() else ""
    res = {}
    for cle, motif in (("cellules", r"cells:\s+(\d+)"), ("hexaedres", r"hexahedra:\s+(\d+)"),
                       ("polyedres", r"polyhedra:\s+(\d+)"), ("non_orthogonalite_max", r"Mesh non-orthogonality Max: ([\d.]+)"),
                       ("asymetrie_max", r"Max skewness = ([\d.]+)"), ("rapport_aspect_max", r"Max aspect ratio = ([\d.]+)")):
        mm = re.search(motif, t)
        if mm:
            res[cle] = float(mm.group(1))
    res["checkMesh_ok"] = "Mesh OK" in t
    res["checkMesh_echecs"] = re.findall(r"\*\*\*(.+)", t)[:6]
    return res


def main(cas_liste):
    SORTIE.mkdir(parents=True, exist_ok=True)
    for c in cas_liste:
        cas = Path(c)
        meta = json.loads((cas / "cas.json").read_text())
        v = meta["version"]
        per = meta["periode_mm"] * 1e-3
        a0, a1 = meta["secteur_deg"]
        th = math.radians(a1 - a0)
        vol, bord = lire(cas)
        res = dict(version=v, **check_mesh(cas))
        res["cellules_lues"] = int(vol.n_cells)
        # surfaces des patchs
        for nom in ("entree", "sortie", "cotes", "paroi", "y0", "y1"):
            if nom in bord.keys():
                res[f"aire_{nom}_mm2"] = round(float(bord[nom].compute_cell_sizes(length=False, volume=False)["Area"].sum()) * 1e6, 1)
        res["aire_entree_attendue_mm2"] = round(th * meta["r_entree_mm"] * per * 1e3, 1)
        res["aire_sortie_attendue_mm2"] = round(th * meta["r_sortie_mm"] * per * 1e3, 1)
        # volume d'air : secteur moins le solide (coupé à la tranche)
        sol = pv.read(cas / "constant/triSurface/paroi.stl")
        # volume du solide dans la tranche : tirage de points uniformes dans le secteur (indépendant du maillage)
        rng0 = np.random.default_rng(1)
        n_mc = 600000
        r_mc = np.sqrt(rng0.uniform((meta["r_sortie_mm"] * 1e-3) ** 2, (meta["r_entree_mm"] * 1e-3) ** 2, n_mc))
        a_mc = np.radians(rng0.uniform(a0, a1, n_mc))
        pts_mc = np.c_[r_mc * np.cos(a_mc), rng0.uniform(0, per, n_mc), r_mc * np.sin(a_mc)]
        dans = pv.PolyData(pts_mc).select_enclosed_points(sol.clean(), tolerance=1e-9, check_surface=False)["SelectedPoints"]
        v_solide = th / 2 * ((meta["r_entree_mm"] * 1e-3) ** 2 - (meta["r_sortie_mm"] * 1e-3) ** 2) * per * dans.mean()
        v_secteur = th / 2 * ((meta["r_entree_mm"] * 1e-3) ** 2 - (meta["r_sortie_mm"] * 1e-3) ** 2) * per
        v_air = float(vol.compute_cell_sizes(length=False, area=False)["Volume"].sum())
        res["volume_air_maillage_cm3"] = round(v_air * 1e6, 3)
        res["volume_air_attendu_cm3"] = round((v_secteur - v_solide) * 1e6, 3)
        # fuite : centres de mailles à l'intérieur du solide (échantillon)
        cc = vol.cell_centers()
        rng = np.random.default_rng(0)
        idx = rng.choice(cc.n_points, size=min(400000, cc.n_points), replace=False)
        ech = pv.PolyData(cc.points[idx])
        sel = ech.select_enclosed_points(sol.clean(), tolerance=1e-9, check_surface=False)
        dedans = int(sel["SelectedPoints"].sum())
        res["echantillon_centres"] = int(len(idx))
        res["centres_dans_le_solide"] = dedans
        # images
        am = math.radians(20.0)        # plan radial entre deux profils
        coupes = {
            "interstice": (vol.slice(normal=(0, 1, 0), origin=(0, 2.5e-3, 0)), None),
        }
        sl = coupes["interstice"][0]
        for nom, (cam_pos, cam_fp, cam_up, zoom) in {
                "interstice": ((0.005, -0.25, 0.0), (0.005, 0, 0.0), (0, 0, 1), 1.0),
                "interstice_zoom": ((0.055, -0.06, 0.02), (0.055, 0, 0.02), (0, 0, 1), 1.0)}.items():
            pl = pv.Plotter(off_screen=True, window_size=(1400, 1100))
            pl.set_background("white")
            pl.add_mesh(sl, color="#e7f5ff", show_edges=True, edge_color="#1c7ed6", line_width=0.4)
            pl.camera.position, pl.camera.focal_point, pl.camera.up = cam_pos, cam_fp, cam_up
            pl.screenshot(SORTIE / f"maillage_{v}_{nom}.png")
            pl.close()
        n = (-math.sin(am), 0, math.cos(am))
        rad = vol.slice(normal=n, origin=(0, 0, 0))
        er = np.array([math.cos(am), 0, math.sin(am)])
        rad = rad.clip(normal=tuple(-er), origin=tuple(er * 0.0), invert=True)      # seulement le côté φ = 20°
        for nom, (rmin, rmax) in {"radial": (33e-3, 77e-3), "radial_zoom": (50e-3, 66e-3)}.items():
            morceau = rad.clip(normal=tuple(er), origin=tuple(er * rmin), invert=False).clip(
                normal=tuple(-er), origin=tuple(er * rmax), invert=False)
            pl = pv.Plotter(off_screen=True, window_size=(1600, 520 if nom == "radial" else 800))
            pl.set_background("white")
            pl.add_mesh(morceau, color="#e7f5ff", show_edges=True, edge_color="#1c7ed6", line_width=0.5)
            c0 = er * (rmin + rmax) / 2 + np.array([0, per / 2, 0])
            pl.camera.focal_point = tuple(c0)
            pl.camera.position = tuple(c0 + np.array(n) * 0.2)
            pl.camera.up = (0, 1, 0)
            pl.enable_parallel_projection()
            pl.camera.parallel_scale = (per / 2) * (1.6 if nom == "radial" else 1.25) if nom != "radial" else (rmax - rmin) / 2 * 520 / 1600 * 1.05
            pl.screenshot(SORTIE / f"maillage_{v}_{nom}.png")
            pl.close()
        (SORTIE / f"maillage_{v}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
