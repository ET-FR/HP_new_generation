"""
Maillages des cas de validation du niveau 0 (docs/plan_formes_simples.md).

1. Canal entre deux plaques parallèles (ailette plate idéale) : écartement 2 mm, donc
   Dh = 2 × écartement = 4 mm comme les tubes ; longueur 200 mm, bien au-delà des longueurs
   d'établissement dynamique (~0,05 Re Dh ≈ 53 mm) et thermique (~0,05 Re Pr Dh ≈ 38 mm)
   à 1 m/s. Référence : f·Re = 24 (Fanning) et Nu = 7,54 (paroi isotherme), écoulement établi.
2. Tube rond isolé : Ø extérieur 6 mm (le tube de référence), domaine 40 Ø × 20 Ø
   (blocage 5 %), bords haut / bas en glissement. Re ≈ 400 à 1 m/s : sillage instationnaire.
   Références : Hilpert (Nu = 0,683 Re^0,466 Pr^1/3), Strouhal ≈ 0,2, Cd ≈ 1 à 1,2.

(Le faisceau de tubes ronds est le cas « rond » de geometrie.py : Zukauskas.)
Unités : mm.

    python cas_validation.py --cas plaques --sortie cas/plaques.msh
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import gmsh
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_gmsh import extraire  # noqa: E402

ECART = 2.0          # mm, écartement des plaques
L_PLAQUE = 200.0     # mm
D_TUBE = 6.0         # mm


def _resultat(sortie, avec_bords=False):
    xy, elems, bords = extraire()
    if sortie:
        Path(sortie).parent.mkdir(parents=True, exist_ok=True)
        gmsh.write(sortie)
    gmsh.finalize()
    return (xy, elems, bords) if avec_bords else (xy, elems)


def maillage_plaques(sortie=None, n_travers=40, n_long=800, resserrement=0.08, avec_bords=False):
    """Maillage structuré en quadrilatères, resserré vers les deux parois."""
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("plaques")
    g = gmsh.model.geo
    p = [g.addPoint(0, 0, 0), g.addPoint(L_PLAQUE, 0, 0), g.addPoint(L_PLAQUE, ECART, 0), g.addPoint(0, ECART, 0)]
    bas, sortie_, haut, entree = (g.addLine(p[0], p[1]), g.addLine(p[1], p[2]),
                                  g.addLine(p[2], p[3]), g.addLine(p[3], p[0]))
    s = g.addPlaneSurface([g.addCurveLoop([bas, sortie_, haut, entree])])
    g.mesh.setTransfiniteCurve(bas, n_long + 1); g.mesh.setTransfiniteCurve(haut, n_long + 1)
    for c in (sortie_, entree):
        g.mesh.setTransfiniteCurve(c, n_travers + 1, "Bump", resserrement)
    g.mesh.setTransfiniteSurface(s); g.mesh.setRecombine(2, s)
    g.synchronize()
    for nom, cs in (("entree", [entree]), ("sortie", [sortie_]), ("paroi", [bas, haut])):
        gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, cs), nom)
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [s]), "air")
    gmsh.model.mesh.generate(2)
    return _resultat(sortie, avec_bords)


def maillage_tube_isole(sortie=None, premiere_couche=0.01, n_couches=20, raison=1.15,
                        taille_paroi=0.06, taille_sillage=0.25, taille_loin=2.0, avec_bords=False):
    """Couches de quadrilatères contre la paroi, sillage raffiné, triangles ailleurs."""
    D = D_TUBE
    x0, x1, h = -10 * D, 30 * D, 20 * D
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("tube_isole")
    occ = gmsh.model.occ
    dom = occ.addRectangle(x0, -h / 2, 0, x1 - x0, h)
    occ.cut([(2, dom)], [(2, occ.addDisk(0, 0, 0, D / 2, D / 2))])
    occ.synchronize()
    eps = 1e-6
    grp = {"entree": [], "sortie": [], "haut_bas": [], "paroi": []}
    for _, c in gmsh.model.getEntities(1):
        xa, ya, _, xb, yb, _ = gmsh.model.getBoundingBox(1, c)
        if abs(xa - x0) < eps and abs(xb - x0) < eps:
            grp["entree"].append(c)
        elif abs(xa - x1) < eps and abs(xb - x1) < eps:
            grp["sortie"].append(c)
        elif abs(abs(ya) - h / 2) < eps and abs(abs(yb) - h / 2) < eps:
            grp["haut_bas"].append(c)
        else:
            grp["paroi"].append(c)
    for nom, cs in grp.items():
        gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, cs), nom)
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [s for _, s in gmsh.model.getEntities(2)]), "air")

    f = gmsh.model.mesh.field
    cl = f.add("BoundaryLayer")
    f.setNumbers(cl, "CurvesList", grp["paroi"])
    f.setNumber(cl, "Size", premiere_couche); f.setNumber(cl, "Ratio", raison)
    f.setNumber(cl, "Thickness", premiere_couche * (raison ** n_couches - 1) / (raison - 1))
    f.setNumber(cl, "Quads", 1)
    f.setAsBoundaryLayer(cl)
    d = f.add("Distance"); f.setNumbers(d, "CurvesList", grp["paroi"]); f.setNumber(d, "Sampling", 300)
    t = f.add("Threshold"); f.setNumber(t, "InField", d)
    f.setNumber(t, "SizeMin", taille_paroi); f.setNumber(t, "SizeMax", taille_loin)
    f.setNumber(t, "DistMin", 0.3); f.setNumber(t, "DistMax", 4 * D)
    bx = f.add("Box"); f.setNumber(bx, "VIn", taille_sillage); f.setNumber(bx, "VOut", taille_loin)
    f.setNumber(bx, "XMin", -1.0 * D); f.setNumber(bx, "XMax", 12 * D)
    f.setNumber(bx, "YMin", -1.5 * D); f.setNumber(bx, "YMax", 1.5 * D); f.setNumber(bx, "Thickness", 2 * D)
    m = f.add("Min"); f.setNumbers(m, "FieldsList", [t, bx]); f.setAsBackgroundMesh(m)
    for o in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints", "MeshSizeFromCurvature"):
        gmsh.option.setNumber(f"Mesh.{o}", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.model.mesh.generate(2)
    return _resultat(sortie, avec_bords)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cas", choices=["plaques", "tube_isole"], required=True)
    ap.add_argument("--sortie", default=None)
    a = ap.parse_args()
    xy, el = (maillage_plaques if a.cas == "plaques" else maillage_tube_isole)(a.sortie)
    print(f"{a.cas}: {len(el)} mailles, {len(xy)} noeuds")
