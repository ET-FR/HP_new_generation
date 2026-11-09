"""
Écriture d'un maillage OpenFOAM (constant/polyMesh) 2D : le maillage gmsh plan est extrudé
d'une seule maille en z (faces avant / arrière de type « empty »).

Règles OpenFOAM respectées : faces internes d'abord, triées par (propriétaire, voisin) ;
normale orientée du propriétaire vers le voisin ; faces de bord regroupées par patch ;
patchs cycliques : face i de l'un correspond à la face i de l'autre (tri selon x).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

ENTETE = """FoamFile
{{
    version     2.0;
    format      ascii;
    arch        "LSB;label=32;scalar=64";
    class       {classe};
    location    "constant/polyMesh";
    object      {objet};{note}
}}

"""


def _ecrire(dossier, objet, classe, corps, note=""):
    n = f'\n    note        "{note}";' if note else ""
    (dossier / objet).write_text(ENTETE.format(classe=classe, objet=objet, note=n) + corps)


def ecrire_polymesh(cas: str | Path, xy_mm, cellules, bords: dict, types: dict,
                    cycliques: dict | None = None, epaisseur_mm=1.0, echelle=1e-3):
    """xy_mm : noeuds 2D ; cellules : listes de noeuds (triangles / quadrilatères) ;
    bords : {nom: [(n1, n2), ...]} ; types : {nom: "patch" | "wall" | "symmetryPlane" | "cyclic"} ;
    cycliques : {nom: (voisin, (dx, dy))} vecteur de translation du patch vers son voisin (mm)."""
    cycliques = cycliques or {}
    # renumérotation : on ne garde que les noeuds utilisés par les cellules
    utilises = np.unique(np.concatenate([np.asarray(c) for c in cellules]))
    nouveau = -np.ones(len(xy_mm), dtype=int)
    nouveau[utilises] = np.arange(len(utilises))
    xy = np.asarray(xy_mm, float)[utilises]
    cellules = [[int(nouveau[n]) for n in c] for c in cellules]
    bords = {k: [(int(nouveau[a]), int(nouveau[b])) for a, b in v] for k, v in bords.items()}
    N = len(xy)
    cel = []
    for c in cellules:                       # orientation trigonométrique
        p = xy[c]
        aire = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
        cel.append(list(c) if aire > 0 else list(c)[::-1])

    arete_cellules = {}
    for ic, c in enumerate(cel):
        for k in range(len(c)):
            a, b = c[k], c[(k + 1) % len(c)]
            arete_cellules.setdefault(frozenset((a, b)), []).append((ic, a, b))

    internes = []
    for lst in arete_cellules.values():
        if len(lst) == 2:
            (c1, a1, b1), (c2, a2, b2) = lst
            if c1 > c2:
                c1, a1, b1, c2 = c2, a2, b2, c1
            internes.append((c1, c2, [a1, b1, b1 + N, a1 + N]))   # sens trigo du propriétaire
    internes.sort(key=lambda t: (t[0], t[1]))

    faces, owner, neigh = [], [], []
    for c1, c2, f in internes:
        faces.append(f); owner.append(c1); neigh.append(c2)

    patchs = []
    noms = list(bords)
    # un patch cyclique doit suivre l'ordre de son voisin : tri des faces selon la coordonnée
    # le long du bord
    deja = set()
    for nom in noms:
        # second patch d'une paire cyclique : face démarrée sur l'autre sommet, pour que son
        # 1er sommet corresponde à celui de la face couplée (convention OpenFOAM)
        second = nom in cycliques and cycliques[nom][0] in deja
        deja.add(nom)
        lst = []
        for a, b in bords[nom]:
            ic, a0, b0 = arete_cellules[frozenset((a, b))][0]
            f = [b0, b0 + N, a0 + N, a0] if second else [a0, b0, b0 + N, a0 + N]
            lst.append((ic, f, 0.5 * (xy[a0] + xy[b0])))
        if nom in cycliques:
            dx, dy = cycliques[nom][1]
            axe = 0 if abs(dy) > abs(dx) else 1           # translation en y -> tri selon x
            lst.sort(key=lambda t: t[2][axe])
        debut = len(faces)
        for ic, f, _ in lst:
            faces.append(f); owner.append(ic)
        patchs.append((nom, debut, len(lst)))
    # avant / arrière
    debut = len(faces)
    for ic, c in enumerate(cel):
        faces.append([n for n in c[::-1]]); owner.append(ic)          # z = 0, normale -z
        faces.append([n + N for n in c]); owner.append(ic)            # z = e, normale +z
    patchs.append(("avantArriere", debut, 2 * len(cel)))

    d = Path(cas) / "constant" / "polyMesh"
    d.mkdir(parents=True, exist_ok=True)
    pts = np.vstack([np.c_[xy, np.zeros(N)], np.c_[xy, np.full(N, epaisseur_mm)]]) * echelle
    note = f"nPoints:{2 * N}  nCells:{len(cel)}  nFaces:{len(faces)}  nInternalFaces:{len(internes)}"
    _ecrire(d, "points", "vectorField", f"{len(pts)}\n(\n" +
            "\n".join(f"({x:.9g} {y:.9g} {z:.9g})" for x, y, z in pts) + "\n)\n")
    _ecrire(d, "faces", "faceList", f"{len(faces)}\n(\n" +
            "\n".join(f"{len(f)}(" + " ".join(map(str, f)) + ")" for f in faces) + "\n)\n")
    _ecrire(d, "owner", "labelList", f"{len(owner)}\n(\n" + "\n".join(map(str, owner)) + "\n)\n", note)
    _ecrire(d, "neighbour", "labelList", f"{len(neigh)}\n(\n" + "\n".join(map(str, neigh)) + "\n)\n", note)
    corps = f"{len(patchs)}\n(\n"
    for nom, debut, n in patchs:
        t = "empty" if nom == "avantArriere" else types[nom]
        corps += f"    {nom}\n    {{\n        type            {t};\n"
        if t == "wall":
            corps += "        inGroups        1(wall);\n"
        if t == "cyclic":
            voisin, (dx, dy) = cycliques[nom]
            corps += (f"        neighbourPatch  {voisin};\n        transform       translational;\n"
                      f"        separationVector ({dx * echelle:.9g} {dy * echelle:.9g} 0);\n"
                      "        matchTolerance  1e-4;\n")
        corps += f"        nFaces          {n};\n        startFace       {debut};\n    }}\n"
    _ecrire(d, "boundary", "polyBoundaryMesh", corps + ")\n")
    return dict(cellules=len(cel), faces=len(faces), internes=len(internes))
