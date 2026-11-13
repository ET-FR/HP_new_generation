#!/usr/bin/env python3
"""
Cas OpenFOAM 3D (étape 3) : tubes de la batterie de référence + surface TPMS à la place des ailettes.

Équité avec les ailettes plates : mêmes tubes (même charge de propane), même zone d'échange (toute la
profondeur, rangs × Pl), même quantité de métal (fraction solide = épaisseur / pas des ailettes plates,
0,2 / 1,8 = 11 %). Le métal forme une feuille TPMS d'épaisseur constante (|F| < t), périodique : la
cellule L doit diviser Pt (périodicité en y) ; le domaine fait une cellule en hauteur (périodicité en z).
Avec L = 6 mm, la surface côté air est proche de celle des ailettes plates au pas 1,8 mm.
La feuille TPMS est supposée isotherme (comme les ailettes) et soudée aux tubes.

Maillage : snappyHexMesh (le solide est écrit en STL : tubes -> patch « paroi », TPMS -> « ailette »),
calcul stationnaire simpleFoam laminaire, mêmes mesures que les cas à ailettes.

    python conception_echangeur/outils/cfd_3d/creer_cas_tpms_tubes.py --dossier cfd_campagne/ailettes/lot3/rond_gyroide6 \
        --forme rond --surface gyroide --cellule 6 [--rangs 4] [--nproc 24]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
for d in ("", "outils/cfd_3d", "outils/cfd_2d"):     # cfd_2d en tête (creer_cas 2D)
    sys.path.insert(0, str(RACINE / d))
sys.path.append(str(RACINE.parent))                  # dépôt : pac_fenetre

from creer_cas import AIR, ecrire, systeme  # noqa: E402
from creer_cas_ailettes import etendue_ailettes  # noqa: E402
from geometrie import batterie  # noqa: E402
from pac_fenetre.tpms import SURFACES, champ  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("tpms_cas", RACINE / "outils" / "cfd_tpms" / "creer_cas.py")
_tpms = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tpms)
triangles, ecrire_stl = _tpms.triangles, _tpms.ecrire_stl

FRACTION_SOLIDE = 0.2 / 1.8      # même métal que les ailettes plates (0,2 mm au pas de 1,8 mm)


def alleger(T, cible):
    """Fusionne les sommets de la soupe de triangles et la décime (pyvista) jusqu'à `cible` triangles."""
    import pyvista as pv
    pts, inv = np.unique(np.round(T.reshape(-1, 3), 7), axis=0, return_inverse=True)
    f = inv.reshape(-1, 3)
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    s = pv.PolyData(pts, np.c_[np.full(len(f), 3), f].ravel())
    if s.n_cells > cible:
        s = s.decimate_pro(1 - cible / s.n_cells, preserve_topology=True, feature_angle=60, boundary_vertex_deletion=False)
    f = s.faces.reshape(-1, 4)[:, 1:]
    return s.points[f]


def niveau_feuille(surface, fraction):
    """t tel que la fraction de volume |F| < t vaille `fraction` (feuille d'épaisseur constante)."""
    N = 96
    s = (np.arange(N) + 0.5) * 2 * np.pi / N
    X, Y, Z = np.meshgrid(s, s, s, indexing="ij")
    return float(np.quantile(np.abs(champ(surface, X, Y, Z)), fraction))


def creer(dossier, forme="rond", surface="gyroide", L=6.0, rangs=4, U=1.0, nproc=24, iterations=3000,
          base=0.25, niveau=2, pas_stl=0.06, fraction=FRACTION_SOLIDE):
    cas = Path(dossier)
    (cas / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    b = batterie(forme, rangs=rangs)
    Pt = b.Pt
    if abs(Pt / L - round(Pt / L)) > 1e-6:
        L = Pt / max(1, round(Pt / L))                   # la cellule doit diviser Pt
    x0f, x1f = etendue_ailettes(b)
    a = (b.exterieur.bounds[2] - b.exterieur.bounds[0]) / 2          # demi-axes du tube (mm)
    bb = (b.exterieur.bounds[3] - b.exterieur.bounds[1]) / 2
    centres = [(cx, cy + dy) for cx, cy in b.centres for dy in (-Pt, 0.0, Pt)]
    t = niveau_feuille(surface, fraction)
    k = 2 * math.pi / L

    def phi_tubes(x, y):
        r = np.full(np.shape(x), -1e9)
        for cx, cy in centres:
            r = np.maximum(r, (1 - np.sqrt(((x - cx) / a) ** 2 + ((y - cy) / bb) ** 2)) * min(a, bb))
        return r

    def phi_tpms(x, y, z):                                # > 0 dans la feuille, limitée à la zone d'ailettes
        f = (t - np.abs(champ(surface, k * x, k * y, k * z))) / k
        return np.minimum(f, np.minimum(x - x0f, x1f - x))

    phi = lambda x, y, z: np.maximum(phi_tpms(x, y, z), phi_tubes(x, y))
    m = 0.3
    T = triangles(phi, [(x0f - m, x1f + m), (-m, Pt + m), (-m, L + m)], pas_stl)   # coordonnées en mm
    T = alleger(T, cible=600_000)
    g = T.mean(axis=1)
    sur_tube = np.abs(phi_tubes(g[:, 0], g[:, 1])) < 0.6 * pas_stl
    ecrire_stl(T[sur_tube] * 1e-3, cas / "constant" / "triSurface" / "paroi.stl", "binaire tubes")
    ecrire_stl(T[~sur_tube] * 1e-3, cas / "constant" / "triSurface" / "ailette.stl", "binaire TPMS")
    # surfaces côté air dans le domaine (triangles dont le centre est dans la cellule périodique)
    dedans = (g[:, 1] >= 0) & (g[:, 1] < Pt) & (g[:, 2] >= 0) & (g[:, 2] < L)
    aire = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    A_tubes = float(aire[dedans & sur_tube].sum()) * 1e-6
    A_tpms = float(aire[dedans & ~sur_tube].sum()) * 1e-6

    # fond de maillage et snappyHexMesh (unités : m)
    x0, x1 = (x0f - 8) * 1e-3, (x1f + 15) * 1e-3
    P, Lm = Pt * 1e-3, L * 1e-3
    nx, ny, nz = (max(4, round(v / (base * 1e-3))) for v in (x1 - x0, P, Lm))
    cyc = lambda nom, voisin, faces, sep: (
        f"    {nom}\n    {{\n        type cyclicAMI;\n        neighbourPatch {voisin};\n        transform translational;\n"
        f"        separationVector ({sep[0]:.9g} {sep[1]:.9g} {sep[2]:.9g});\n        lowWeightCorrection 0.2;\n"
        f"        faces ({faces});\n    }}\n")
    ecrire(cas, "system/blockMeshDict", f"""scale 1;
vertices
(
    ({x0:.9g} 0 0) ({x1:.9g} 0 0) ({x1:.9g} {P:.9g} 0) ({x0:.9g} {P:.9g} 0)
    ({x0:.9g} 0 {Lm:.9g}) ({x1:.9g} 0 {Lm:.9g}) ({x1:.9g} {P:.9g} {Lm:.9g}) ({x0:.9g} {P:.9g} {Lm:.9g})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1) );
boundary
(
    entree {{ type patch; faces ((0 4 7 3)); }}
    sortie {{ type patch; faces ((1 2 6 5)); }}
{cyc("bas", "haut", "(0 1 5 4)", (0, P, 0))}{cyc("haut", "bas", "(3 7 6 2)", (0, -P, 0))}{cyc("z0", "z1", "(0 3 2 1)", (0, 0, Lm))}{cyc("z1", "z0", "(4 5 6 7)", (0, 0, -Lm))});
""")
    loc = (x0 + 2e-3, 0.37 * P, 0.41 * Lm)
    ecrire(cas, "system/snappyHexMeshDict", f"""castellatedMesh true;
snap            true;
addLayers       false;
geometry
{{
    paroi.stl   {{ type triSurfaceMesh; name paroi; }}
    ailette.stl {{ type triSurfaceMesh; name ailette; }}
}}
castellatedMeshControls
{{
    maxLocalCells 20000000; maxGlobalCells 60000000; minRefinementCells 0;
    maxLoadUnbalance 0.10; nCellsBetweenLevels 2;
    features ();
    refinementSurfaces
    {{
        paroi   {{ level ({niveau} {niveau}); patchInfo {{ type wall; }} }}
        ailette {{ level ({niveau} {niveau}); patchInfo {{ type wall; }} }}
    }}
    resolveFeatureAngle 30;
    refinementRegions {{}};
    locationInMesh ({loc[0]:.9g} {loc[1]:.9g} {loc[2]:.9g});
    allowFreeStandingZoneFaces true;
}}
snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; nFeatureSnapIter 0;
    implicitFeatureSnap false; explicitFeatureSnap false; multiRegionFeatureSnap false; }}
addLayersControls {{ relativeSizes true; layers {{}}; expansionRatio 1.2; finalLayerThickness 0.4;
    minThickness 0.1; nGrow 0; featureAngle 60; nRelaxIter 3; nSmoothSurfaceNormals 1; nSmoothNormals 3;
    nSmoothThickness 10; maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3; minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0; nLayerIter 50; }}
meshQualityControls {{ #includeEtc "caseDicts/meshQualityDict"
    nSmoothScale 4; errorReduction 0.75; relaxed {{ maxNonOrtho 75; }} }}
mergeTolerance 1e-6;
""")
    # champs
    cyc_bc = '    "(bas|haut|z0|z1)" { type cyclicAMI; }\n    #includeEtc "caseDicts/setConstraintTypes"\n'
    for nom, classe, dim, interne, cl in (
            ("U", "volVectorField", "[0 1 -1 0 0 0 0]", f"({U} 0 0)",
             {"entree": f"type fixedValue; value uniform ({U} 0 0);",
              "sortie": "type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0);",
              "paroi": "type noSlip;"}),
            ("p", "volScalarField", "[0 2 -2 0 0 0 0]", "0",
             {"entree": "type zeroGradient;", "sortie": "type fixedValue; value uniform 0;", "paroi": "type zeroGradient;"}),
            ("T", "volScalarField", "[0 0 0 0 0 0 0]", "0",
             {"entree": "type fixedValue; value uniform 0;",
              "sortie": "type inletOutlet; inletValue uniform 0; value uniform 0;",
              "paroi": "type fixedValue; value uniform 1;"})):
        bf = "".join(f"    {p}\n    {{\n        {cl[r]}\n    }}\n" for p, r in
                     (("entree", "entree"), ("sortie", "sortie"), ("paroi", "paroi"), ("ailette", "paroi")))
        ecrire(cas, f"0/{nom}", f"dimensions      {dim};\ninternalField   uniform {interne};\n\n"
                                f"boundaryField\n{{\n{bf}{cyc_bc}}}\n", classe)
    systeme(cas, False, iterations, 0, nproc, None, iterations=iterations)
    cd = (cas / "system" / "controlDict").read_text()
    i = cd.index("    pEntree")
    cd = cd[:i] + ("    fluxAilette\n    {\n        $fluxParoi;\n        name            ailette;\n    }\n") + cd[i:]
    (cas / "system" / "controlDict").write_text(cd)
    fv = (cas / "system" / "fvSchemes").read_text()
    fv = fv.replace("laplacianSchemes { default Gauss linear corrected; }",
                    "laplacianSchemes { default Gauss linear limited corrected 0.5; }")
    fv = fv.replace("snGradSchemes   { default corrected; }", "snGradSchemes   { default limited corrected 0.5; }")
    fv = fv.replace("gradSchemes     { default Gauss linear; }", "gradSchemes     { default cellLimited Gauss linear 1; }")
    (cas / "system" / "fvSchemes").write_text(fv)
    (cas / "system" / "fvSolution").write_text((cas / "system" / "fvSolution").read_text()
                                                .replace("relaxationFactors { equations { U 0.9; T 0.9; } }",
                                                         "relaxationFactors { equations { U 0.7; T 0.9; } fields { p 0.3; } }")
                                                .replace("consistent          yes;", "consistent          no;"))
    (cas / "Allrun").write_text(f"""#!/bin/bash
# Cas généré par outils/cfd_3d/creer_cas_tpms_tubes.py (OpenFOAM v2606)
cd "$(dirname "$0")" || exit 1
set -e
[ -d 0.orig ] || mv 0 0.orig
blockMesh > log.blockMesh 2>&1
decomposePar -force > log.decomposePar 2>&1
mpirun -np {nproc} snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
# champs initiaux (uniformes, sans valeurs par face) recopiés sur le maillage final de chaque sous-domaine
for d in processor*; do rm -rf $d/0; cp -r 0.orig $d/0; done
mpirun -np {nproc} checkMesh -parallel > log.checkMesh 2>&1 || true
mpirun -np {nproc} simpleFoam -parallel > log.simpleFoam 2>&1
reconstructParMesh -constant > log.reconstructParMesh 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
""")
    (cas / "Allrun").chmod(0o755)
    passage = Pt - 2 * bb
    meta = dict(cas="batterie", ailettes=True, tpms=surface, U=U, U_domaine=U, air=AIR, epaisseur_mm=L, nproc=nproc,
                forme=forme, nom=f"{b.nom} + {SURFACES[surface]['nom']} (cellule {L:.3g} mm)",
                cellule_tpms_mm=L, fraction_solide=fraction, niveau_feuille=t,
                pas_ailettes_mm=None, epaisseur_ailette_mm=None, maillage=dict(cellules=None, base_mm=base, niveau=niveau),
                tranches=dict(n=None),
                Pt=Pt * 1e-3, Pl=b.Pl * 1e-3, rangs=b.rangs, A_int=b.A_int * 1e-6, P_int=b.P_int * 1e-3,
                P_ext=b.P_ext * 1e-3, x_noyau=[x0f * 1e-3, x1f * 1e-3], x_tubes=[x * 1e-3 for x in b.x_noyau],
                x_domaine=[x0, x1], largeur_frontale=2 * bb * 1e-3, Umax=U * Pt / passage,
                Re_Dext=U * 6e-3 / AIR["nu"], A_tubes_domaine=A_tubes, A_ailettes_domaine=A_tpms,
                A_air_domaine=A_tubes + A_tpms, facteur_surface=(A_tubes + A_tpms) / A_tubes,
                instationnaire=False, fin=iterations, debut_moyenne=0.75 * iterations)
    (cas / "cas.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta, len(T)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--forme", default="rond")
    ap.add_argument("--surface", choices=list(SURFACES), default="gyroide")
    ap.add_argument("--cellule", type=float, default=6.0, help="taille de cellule TPMS (mm), diviseur de Pt")
    ap.add_argument("--rangs", type=int, default=4)
    ap.add_argument("--nproc", type=int, default=24)
    ap.add_argument("--iterations", type=int, default=3000)
    ap.add_argument("--base", type=float, default=0.25, help="maille de fond (mm)")
    ap.add_argument("--niveau", type=int, default=2, help="niveau de raffinement aux parois")
    ap.add_argument("--pas-stl", type=float, default=0.06)
    ap.add_argument("--suffixe", default=None)
    a = ap.parse_args()
    m, n = creer(a.dossier, a.forme, a.surface, a.cellule, a.rangs, nproc=a.nproc, iterations=a.iterations,
                 base=a.base, niveau=a.niveau, pas_stl=a.pas_stl)
    if a.suffixe:
        m["suffixe"] = a.suffixe
        (Path(a.dossier) / "cas.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps({k: m[k] for k in ("nom", "niveau_feuille", "facteur_surface", "A_ailettes_domaine",
                                        "A_tubes_domaine")}, indent=1, ensure_ascii=False), n, "triangles")
