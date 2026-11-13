"""
Maillage 2D d'une batterie (gmsh) : domaine périodique en y, tubes retranchés, mailles fines
près des parois. Le maillage 2D sera extrudé d'une maille en z pour OpenFOAM (gmshToFoam).

    python maillage.py --forme rond --sortie cas/rond.msh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import gmsh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometrie import FORMES, batterie  # noqa: E402
from export_gmsh import extraire  # noqa: E402

TAILLE_PAROI = 0.08   # mm, taille des mailles contre la paroi
TAILLE_LOIN = 0.6     # mm, dans le noyau loin des parois
TAILLE_TAMPON = 1.0   # mm, dans les tampons amont / aval
DIST_TRANSITION = 2.0  # mm, distance sur laquelle la maille grossit


def mailler(forme: str, sortie: str | None = None, voir=False, avec_bords=False, finesse=1.0,
            couches=False, **kw):
    """finesse : divise toutes les tailles de maille (1 = maillage de référence, 1,5 = plus fin).
    couches : ajoute des couches de quadrilatères contre les parois (1re couche 0,02 mm / finesse,
    raison 1,2, 10 couches), comme pour le tube isolé."""
    b = batterie(forme, **kw)
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add(forme)
    occ = gmsh.model.occ
    x0, x1 = b.x_domaine
    dom = occ.addRectangle(x0, 0, 0, x1 - x0, b.Pt)
    ext = np.asarray(b.exterieur.exterior.coords)[:-1]
    tubes = []
    for (cx, cy) in b.centres:
        for dy in ((0.0,) if cy > 0 else (0.0, b.Pt)):
            pts = [occ.addPoint(cx + x, cy + dy + y, 0) for x, y in ext]
            c = occ.addSpline(pts + [pts[0]])
            tubes.append(occ.addPlaneSurface([occ.addCurveLoop([c])]))
    occ.cut([(2, dom)], [(2, t) for t in tubes])
    occ.synchronize()

    eps = 1e-6
    entree, sortie_, haut, bas, parois = [], [], [], [], []
    for _, c in gmsh.model.getEntities(1):
        xa, ya, _, xb, yb, _ = gmsh.model.getBoundingBox(1, c)
        if abs(xa - x0) < eps and abs(xb - x0) < eps:
            entree.append(c)
        elif abs(xa - x1) < eps and abs(xb - x1) < eps:
            sortie_.append(c)
        elif abs(ya - b.Pt) < eps and abs(yb - b.Pt) < eps:
            haut.append(c)
        elif abs(ya) < eps and abs(yb) < eps:
            bas.append(c)
        else:
            parois.append(c)
    cle = lambda c: gmsh.model.getBoundingBox(1, c)[0]
    haut.sort(key=cle); bas.sort(key=cle)
    gmsh.model.mesh.setPeriodic(1, haut, bas, [1, 0, 0, 0, 0, 1, 0, b.Pt, 0, 0, 1, 0, 0, 0, 0, 1])
    for nom, cs in (("entree", entree), ("sortie", sortie_), ("haut", haut), ("bas", bas), ("paroi", parois)):
        gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, cs), nom)
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [s for _, s in gmsh.model.getEntities(2)]), "air")

    f = gmsh.model.mesh.field
    k = 1.0 / finesse
    if couches:
        e1, raison, n = 0.02 * k, 1.2, 10
        cl = f.add("BoundaryLayer")
        f.setNumbers(cl, "CurvesList", parois)
        f.setNumber(cl, "Size", e1); f.setNumber(cl, "Ratio", raison)
        f.setNumber(cl, "Thickness", e1 * (raison ** n - 1) / (raison - 1)); f.setNumber(cl, "Quads", 1)
        f.setAsBoundaryLayer(cl)
    d = f.add("Distance"); f.setNumbers(d, "CurvesList", parois); f.setNumber(d, "Sampling", 400)
    t = f.add("Threshold"); f.setNumber(t, "InField", d)
    f.setNumber(t, "SizeMin", TAILLE_PAROI * k); f.setNumber(t, "SizeMax", TAILLE_LOIN * k)
    f.setNumber(t, "DistMin", 0.0); f.setNumber(t, "DistMax", DIST_TRANSITION)
    bx = f.add("Box"); f.setNumber(bx, "VIn", TAILLE_LOIN * k); f.setNumber(bx, "VOut", TAILLE_TAMPON * k)
    f.setNumber(bx, "XMin", b.x_noyau[0] - 3); f.setNumber(bx, "XMax", b.x_noyau[1] + 6)
    f.setNumber(bx, "YMin", -1); f.setNumber(bx, "YMax", b.Pt + 1); f.setNumber(bx, "Thickness", 4)
    m = f.add("Min"); f.setNumbers(m, "FieldsList", [t, bx]); f.setAsBackgroundMesh(m)
    for o in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints", "MeshSizeFromCurvature"):
        gmsh.option.setNumber(f"Mesh.{o}", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.model.mesh.generate(2)

    xy, cellules, bords = extraire()
    tri = np.array(cellules) if len({len(c) for c in cellules}) == 1 else cellules
    if sortie:
        Path(sortie).parent.mkdir(parents=True, exist_ok=True)
        gmsh.write(sortie)
    gmsh.finalize()
    return (b, xy, tri, bords) if avec_bords else (b, xy, tri)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forme", choices=list(FORMES), required=True)
    ap.add_argument("--sortie", default=None)
    a = ap.parse_args()
    b, xy, tri = mailler(a.forme, a.sortie)
    print(f"{a.forme}: {len(tri)} triangles, {len(xy)} noeuds")
