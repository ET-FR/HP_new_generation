"""Extraction du maillage gmsh courant (avant gmsh.finalize) : noeuds, cellules 2D et arêtes
de bord par groupe physique. Unités du modèle gmsh (mm)."""
import gmsh
import numpy as np


def extraire():
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    idx = {int(t): i for i, t in enumerate(tags)}
    xy = xyz.reshape(-1, 3)[:, :2]
    cellules = []
    types, _, conn = gmsh.model.mesh.getElements(2)
    for t, c in zip(types, conn):
        n = {2: 3, 3: 4}[int(t)]
        cellules += [[idx[int(k)] for k in c[i:i + n]] for i in range(0, len(c), n)]
    bords = {}
    for dim, pg in gmsh.model.getPhysicalGroups(1):
        nom = gmsh.model.getPhysicalName(dim, pg)
        aretes = []
        for ent in gmsh.model.getEntitiesForPhysicalGroup(dim, pg):
            _, _, c = gmsh.model.mesh.getElements(1, int(ent))
            for cc in c:
                aretes += [(idx[int(cc[i])], idx[int(cc[i + 1])]) for i in range(0, len(cc), 2)]
        bords[nom] = aretes
    return xy, cellules, bords
