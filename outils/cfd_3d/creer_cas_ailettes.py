#!/usr/bin/env python3
"""
Cas OpenFOAM 3D (étape 3) : batterie de tubes à ailettes plates, une cellule périodique.

Domaine : le maillage 2D à couches des tubes (outils/cfd_2d/maillage_couches.py, validé en
convergence), resserré aux bords d'attaque et de fuite des ailettes, extrudé en nz tranches dans
l'espace entre deux ailettes voisines (hauteur = pas Fp - épaisseur e), tranches resserrées contre
les ailettes (outils/cfd_3d/ailettes_plates.py).

Patchs :
  entree, sortie        vitesse imposée / pression imposée
  haut, bas             périodicité en y (pas transversal Pt)
  paroi                 tubes, température imposée (T = 1)
  ailette_bas / _haut   faces z = 0 et z = Fp - e dans la zone à ailettes : paroi, T = 1
                        (ailette isotherme : rendement d'ailette 1, hypothèse de ce premier calcul)
  libre_bas / _haut     mêmes faces hors de la zone à ailettes (tampons) : symétrie

Équité : même tube et même charge de propane que la batterie de référence (4 rangs en quinconce,
Pt = 12 mm). Vitesse frontale U_face (1 m/s) : le débit d'une période Fp passe dans l'espace
Fp - e, d'où une vitesse d'entrée U_face × Fp / (Fp - e) dans le domaine. Le rétrécissement
au bord d'attaque de l'ailette (épaisseur e) est ignoré.

    python outils/cfd_3d/creer_cas_ailettes.py --dossier cfd_campagne/ailettes/rond_Fp1.8 \
        [--forme rond] [--pas 1.8] [--epaisseur 0.2] [--tranches-premiere 0.02] [--stationnaire]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "outils" / "cfd_2d"))
sys.path.insert(0, str(RACINE / "outils" / "cfd_3d"))

from creer_cas import AIR, ecrire, systeme  # noqa: E402
from geometrie import FORMES, batterie  # noqa: E402
from maillage_couches import mailler_couches  # noqa: E402
from polymesh import _ecrire  # noqa: E402

TAILLE_BORD = 0.06      # mm, mailles aux bords d'attaque et de fuite des ailettes
DEMI_BANDE = 0.6        # mm, demi-largeur de la bande fine


def tranches(ecart, premiere=0.02, raison=1.15, n_total=None):
    """Cotes z des tranches entre deux ailettes distantes de `ecart` (mm), resserrées
    symétriquement contre les deux ailettes. n_total (pair) : nombre imposé de tranches (convergence),
    la 1re tranche est alors ajustée à raison constante."""
    demi = ecart / 2
    n = n_total // 2 if n_total else max(3, math.ceil(math.log(1 + demi * (raison - 1) / premiere) / math.log(raison)))
    e = premiere * raison ** np.arange(n)
    e *= demi / e.sum()
    z = np.r_[0.0, np.cumsum(e)]
    return np.r_[z, ecart - z[-2::-1]]


def etendue_ailettes(b):
    """Ailettes sur toute la profondeur : rangs × Pl, chaque rang au centre de sa bande."""
    x0, x1 = b.x_noyau
    m = b.Pl / 2 - (b.exterieur.bounds[2] - b.exterieur.bounds[0]) / 2
    return x0 - m, x1 + m


def ecrire_polymesh_3d(cas, xy_mm, cellules, bords, types, cycliques, z_mm, zone_ailette, echelle=1e-3,
                       deplacement=None):
    """Extrusion en len(z_mm) - 1 tranches. zone_ailette(x_mm, y_mm) -> bool pour classer les faces z.
    deplacement(x_mm) -> décalage en z (mm) de toute la colonne (ailettes ondulées) ; None : plates.
    Retourne le nombre de cellules et la surface des ailettes (m², deux faces, vraie aire 3D)."""
    utilises = np.unique(np.concatenate([np.asarray(c) for c in cellules]))
    nouveau = -np.ones(len(xy_mm), dtype=int)
    nouveau[utilises] = np.arange(len(utilises))
    xy = np.asarray(xy_mm, float)[utilises]
    cellules = [[int(nouveau[n]) for n in c] for c in cellules]
    bords = {k: [(int(nouveau[a]), int(nouveau[b])) for a, b in v] for k, v in bords.items()}
    N, nz = len(xy), len(z_mm) - 1
    cel = []
    for c in cellules:
        p = xy[c]
        aire = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
        cel.append(list(c) if aire > 0 else list(c)[::-1])
    nc = len(cel)
    aires = np.array([abs(0.5 * np.sum(xy[c][:, 0] * np.roll(xy[c][:, 1], -1)
                                       - np.roll(xy[c][:, 0], -1) * xy[c][:, 1])) for c in cel])
    centres = np.array([xy[c].mean(axis=0) for c in cel])

    arete = {}
    for ic, c in enumerate(cel):
        for k in range(len(c)):
            a, b = c[k], c[(k + 1) % len(c)]
            arete.setdefault(frozenset((a, b)), []).append((ic, a, b))

    P = lambda n, k: n + k * N                          # noeud n au niveau k
    internes = []
    for lst in arete.values():
        if len(lst) == 2:
            (c1, a1, b1), (c2, _, _) = lst
            if c1 > c2:
                (c2, _, _), (c1, a1, b1) = lst
            for k in range(nz):
                internes.append((c1 + k * nc, c2 + k * nc, [P(a1, k), P(b1, k), P(b1, k + 1), P(a1, k + 1)]))
    for k in range(nz - 1):                              # faces entre tranches, normale +z
        for ic, c in enumerate(cel):
            internes.append((ic + k * nc, ic + (k + 1) * nc, [P(n, k + 1) for n in c]))
    internes.sort(key=lambda t: (t[0], t[1]))
    faces = [f for _, _, f in internes]
    owner = [o for o, _, _ in internes]
    neigh = [v for _, v, _ in internes]

    patchs, deja = [], set()
    for nom in bords:
        second = nom in cycliques and cycliques[nom][0] in deja
        deja.add(nom)
        lst = []
        for a, b in bords[nom]:
            ic, a0, b0 = arete[frozenset((a, b))][0]
            mid = 0.5 * (xy[a0] + xy[b0])
            for k in range(nz):
                f = ([P(b0, k), P(b0, k + 1), P(a0, k + 1), P(a0, k)] if second
                     else [P(a0, k), P(b0, k), P(b0, k + 1), P(a0, k + 1)])
                lst.append((ic + k * nc, f, (round(mid[0], 9), round(mid[1], 9), k)))
        if nom in cycliques:
            dx, dy = cycliques[nom][1]
            axe = 0 if abs(dy) > abs(dx) else 1
            lst.sort(key=lambda t: (t[2][axe], t[2][2]))
        debut = len(faces)
        for ic, f, _ in lst:
            faces.append(f); owner.append(ic)
        patchs.append((nom, types[nom], debut, len(lst)))
    ail = np.array([zone_ailette(x, y) for x, y in centres])
    for nom, k, sens, garder in (("ailette_bas", 0, -1, True), ("ailette_haut", nz, 1, True),
                                 ("libre_bas", 0, -1, False), ("libre_haut", nz, 1, False)):
        debut, n = len(faces), 0
        for ic, c in enumerate(cel):
            if ail[ic] == garder:
                faces.append([P(v, k) for v in (c if sens > 0 else c[::-1])])
                owner.append(ic + (k - 1 if k == nz else 0) * nc)
                n += 1
        patchs.append((nom, "wall" if garder else "symmetry", debut, n))

    d = Path(cas) / "constant" / "polyMesh"
    d.mkdir(parents=True, exist_ok=True)
    dz = deplacement(xy[:, 0]) if deplacement else np.zeros(N)
    pts = np.vstack([np.c_[xy, z + dz] for z in z_mm]) * echelle
    note = f"nPoints:{len(pts)}  nCells:{nc * nz}  nFaces:{len(faces)}  nInternalFaces:{len(internes)}"
    _ecrire(d, "points", "vectorField", f"{len(pts)}\n(\n" +
            "\n".join(f"({x:.9g} {y:.9g} {z:.9g})" for x, y, z in pts) + "\n)\n")
    _ecrire(d, "faces", "faceList", f"{len(faces)}\n(\n" +
            "\n".join(f"{len(f)}(" + " ".join(map(str, f)) + ")" for f in faces) + "\n)\n")
    _ecrire(d, "owner", "labelList", f"{len(owner)}\n(\n" + "\n".join(map(str, owner)) + "\n)\n", note)
    _ecrire(d, "neighbour", "labelList", f"{len(neigh)}\n(\n" + "\n".join(map(str, neigh)) + "\n)\n", note)
    corps = f"{len(patchs)}\n(\n"
    for nom, t, debut, n in patchs:
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
    def aire3d(c):                                        # aire vraie de la face de fond (ondulée)
        q = np.c_[xy[c], dz[c]]
        return 0.5 * np.linalg.norm(sum(np.cross(q[k] - q[0], q[k + 1] - q[0]) for k in range(1, len(c) - 1)))
    A_ail = 2 * sum(aire3d(c) for c, a in zip(cel, ail) if a) * echelle ** 2
    return dict(cellules=nc * nz, cellules_2d=nc, tranches=nz, faces=len(faces), internes=len(internes)), A_ail


def champs_3d(cas, U):
    roles = {"entree": "entree", "sortie": "sortie", "paroi": "paroi", "ailette_bas": "paroi",
             "ailette_haut": "paroi", "haut": "cyclic", "bas": "cyclic", "libre_bas": "symmetry",
             "libre_haut": "symmetry"}
    cl = {"U": {"entree": f"type fixedValue; value uniform ({U} 0 0);",
                "sortie": "type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0);",
                "paroi": "type noSlip;"},
          "p": {"entree": "type zeroGradient;", "sortie": "type fixedValue; value uniform 0;",
                "paroi": "type zeroGradient;"},
          "T": {"entree": "type fixedValue; value uniform 0;",
                "sortie": "type inletOutlet; inletValue uniform 0; value uniform 0;",
                "paroi": "type fixedValue; value uniform 1;"}}
    for nom, (classe, dim, interne) in {"U": ("volVectorField", "[0 1 -1 0 0 0 0]", f"({U} 0 0)"),
                                        "p": ("volScalarField", "[0 2 -2 0 0 0 0]", "0"),
                                        "T": ("volScalarField", "[0 0 0 0 0 0 0]", "0")}.items():
        bf = ""
        for p, role in roles.items():
            txt = f"type {role};" if role in ("cyclic", "symmetry") else cl[nom][role]
            bf += f"    {p}\n    {{\n        {txt}\n    }}\n"
        ecrire(cas, f"0/{nom}", f"dimensions      {dim};\ninternalField   uniform {interne};\n\n"
                                f"boundaryField\n{{\n{bf}}}\n", classe)


def creer(dossier, forme="rond", U_face=1.0, Fp=1.8, e=0.2, premiere=0.02, nproc=48,
          stationnaire=False, fin=None, iterations=4000, finesse=1.0, rangs=4, n_tranches=None,
          ondulation=None, bord=None):
    """ondulation = (amplitude, longueur d'onde) en mm : ailettes ondulées dans le sens de l'air,
    z décalé de A sin(2π (x - x_bord) / λ) dans la zone à ailettes (λ ajustée à un nombre entier de
    demi-ondes sur la profondeur). bord = (amplitude, longueur d'onde) en mm : bord d'attaque ondulé
    (tubercules de baleine), x_bord(y) = x_bord + A sin(2π y / λ), λ ajustée pour diviser Pt."""
    cas = Path(dossier)
    b0 = batterie(forme, rangs=rangs)
    x0f, x1f = etendue_ailettes(b0)
    Ab, lb = bord or (0.0, 1.0)
    if bord:
        lb = b0.Pt / max(1, round(b0.Pt / lb))
    b, xy, cellules, bd = mailler_couches(forme, finesse=finesse, rangs=rangs,
                                          lignes_fines=[(x0f, TAILLE_BORD, DEMI_BANDE + Ab),
                                                        (x1f, TAILLE_BORD, DEMI_BANDE)])
    deplacement, lo = None, None
    if ondulation:
        Ao, lo = ondulation
        n_demi = max(1, round(2 * (x1f - x0f) / lo))
        lo = 2 * (x1f - x0f) / n_demi
        deplacement = lambda x: np.where((x > x0f) & (x < x1f), Ao * np.sin(2 * np.pi * (x - x0f) / lo), 0.0)
    ecart = Fp - e
    z = tranches(ecart, premiere, n_total=n_tranches)
    n, A_ail = ecrire_polymesh_3d(cas, xy, cellules, bd,
                                  {"entree": "patch", "sortie": "patch", "paroi": "wall", "haut": "cyclic",
                                   "bas": "cyclic"},
                                  {"haut": ("bas", (0, -b.Pt)), "bas": ("haut", (0, b.Pt))},
                                  z, lambda x, y: x0f + Ab * math.sin(2 * math.pi * y / lb) <= x <= x1f,
                                  deplacement=deplacement)
    U = U_face * Fp / ecart                                  # vitesse dans le domaine (entre ailettes)
    largeur = (b.exterieur.bounds[3] - b.exterieur.bounds[1]) * 1e-3
    passage = b.Pt - largeur * 1e3
    from shapely import affinity as _aff
    t0 = _aff.translate(b.exterieur, *b.centres[0]); t1 = _aff.translate(b.exterieur, *b.centres[1])
    passage = min(passage, 2 * t0.distance(t1))
    Umax = U * b.Pt / passage
    L_dom = (b.x_domaine[1] - b.x_domaine[0]) * 1e-3
    debut = round(2 * L_dom / U, 3)
    fin = fin or round(debut + 0.25, 3)
    dz = ecart * 1e-3
    A_tubes = b.rangs * b.P_ext * 1e-3 * dz
    meta = dict(cas="batterie", ailettes=True, U=U_face, U_domaine=U, air=AIR, epaisseur_mm=ecart, nproc=nproc,
                finesse=finesse, couches=b.couches, forme=forme, nom=b.nom + (" à ailettes ondulées" if ondulation else " à ailettes plates") + (", bord d'attaque ondulé" if bord else ""),
                pas_ailettes_mm=Fp, epaisseur_ailette_mm=e,
                ondulation_mm=[ondulation[0], lo] if ondulation else None, bord_ondule_mm=[Ab, lb] if bord else None, tranches=dict(n=len(z) - 1, premiere_mm=float(z[1])),
                Pt=b.Pt * 1e-3, Pl=b.Pl * 1e-3, rangs=b.rangs, A_int=b.A_int * 1e-6, P_int=b.P_int * 1e-3,
                P_ext=b.P_ext * 1e-3, x_noyau=[x0f * 1e-3, x1f * 1e-3], x_tubes=[x * 1e-3 for x in b.x_noyau],
                x_domaine=[x * 1e-3 for x in b.x_domaine], largeur_frontale=largeur, Umax=Umax,
                Re_Dext=U_face * 6e-3 / AIR["nu"], A_tubes_domaine=A_tubes, A_ailettes_domaine=A_ail,
                A_air_domaine=A_tubes + A_ail, facteur_surface=(A_tubes + A_ail) / A_tubes,
                instationnaire=not stationnaire, fin=fin if not stationnaire else iterations,
                debut_moyenne=debut if not stationnaire else 0.75 * iterations, maillage=n)
    champs_3d(cas, U)
    systeme(cas, not stationnaire, fin, debut, nproc, None, iterations=iterations)
    # flux de chaleur des ailettes, en plus de celui des tubes (fluxParoi)
    cd = (cas / "system" / "controlDict").read_text()
    ajout = ("    fluxAilette\n    {\n        $fluxParoi;\n        regionType      patch;\n        name            ailette_bas;\n    }\n"
             "    fluxAiletteHaut\n    {\n        $fluxParoi;\n        name            ailette_haut;\n    }\n")
    i = cd.index("    pEntree")
    (cas / "system" / "controlDict").write_text(cd[:i] + ajout + cd[i:])
    solveur = "simpleFoam" if stationnaire else "pimpleFoam"
    (cas / "Allrun").write_text(f"""#!/bin/bash
# Cas généré par outils/cfd_3d/creer_cas_ailettes.py (OpenFOAM v2606)
cd "$(dirname "$0")" || exit 1
set -e
checkMesh > log.checkMesh 2>&1
decomposePar -force > log.decomposePar 2>&1
mpirun -np {nproc} {solveur} -parallel > log.{solveur} 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
""")
    (cas / "Allrun").chmod(0o755)
    (cas / "cas.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--forme", choices=list(FORMES), default="rond")
    ap.add_argument("--vitesse", type=float, default=1.0, help="vitesse frontale (m/s)")
    ap.add_argument("--pas", type=float, default=1.8, help="pas d'ailettes Fp (mm)")
    ap.add_argument("--epaisseur", type=float, default=0.2, help="épaisseur d'ailette (mm)")
    ap.add_argument("--premiere", type=float, default=0.02, help="1re tranche contre l'ailette (mm)")
    ap.add_argument("--nproc", type=int, default=48)
    ap.add_argument("--stationnaire", action="store_true", help="simpleFoam au lieu de pimpleFoam")
    ap.add_argument("--fin", type=float, default=None)
    ap.add_argument("--iterations", type=int, default=4000)
    ap.add_argument("--suffixe", default=None)
    ap.add_argument("--rangs", type=int, default=4)
    ap.add_argument("--tranches", type=int, default=None, help="nombre de tranches imposé (pair)")
    ap.add_argument("--ondulation", type=float, nargs=2, default=None, metavar=("A", "LAMBDA"),
                    help="ailettes ondulées : amplitude et longueur d'onde (mm)")
    ap.add_argument("--bord", type=float, nargs=2, default=None, metavar=("A", "LAMBDA"),
                    help="bord d'attaque ondulé : amplitude et longueur d'onde (mm)")
    a = ap.parse_args()
    m = creer(a.dossier, a.forme, a.vitesse, a.pas, a.epaisseur, a.premiere, a.nproc, a.stationnaire, a.fin,
              a.iterations, rangs=a.rangs, n_tranches=a.tranches, ondulation=a.ondulation, bord=a.bord)
    if a.suffixe:
        m["suffixe"] = a.suffixe
        (Path(a.dossier) / "cas.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps({k: m[k] for k in ("nom", "U_domaine", "maillage", "facteur_surface", "fin", "debut_moyenne",
                                        "tranches")}, indent=1, ensure_ascii=False))
