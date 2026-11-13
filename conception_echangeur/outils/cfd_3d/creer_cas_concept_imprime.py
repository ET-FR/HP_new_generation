#!/usr/bin/env python3
"""
Cas OpenFOAM 3D du concept d'échangeur imprimé (variante F, tube Ø 150), versions sans et avec stries.

Domaine : tranche périodique de 2 pas de lamelles (5 mm) le long du tube (faces y0 / y1 en cyclicAMI), sur tout le
secteur d'échange (φ de −90 à 140°), entre le filtre (r = 77 mm, entrée) et le noyau (r = 33 mm, sortie).
  entree  cylindre r = 77 : débit imposé (830 m³/h ramené à la tranche), vitesse radiale uniforme, T = 0
  sortie  cylindre r = 33 : pression 0
  cotes   plans des bouts du secteur : glissement
  paroi   solide (lamelles décalées + profils pleins, outils/cad/stl_concept_imprime.py) : non-glissement, T = 1
Air à propriétés constantes, laminaire, stationnaire (simpleFoam), T scalaire passif. Paroi isotherme : lamelles de
1 mm en aluminium imprimé, rendement d'ailette ≈ 0,97 (calcul du 12/11).

Maillage : blockMesh (fond de `base` mm) + snappyHexMesh (paroi au niveau 2, toute la zone d'échange au niveau 2).

    .venv/bin/python conception_echangeur/outils/cfd_3d/creer_cas_concept_imprime.py --version sans --dossier <cas>
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
from creer_cas import AIR, ecrire, systeme  # noqa: E402

GEO = RACINE / "cfd_campagne" / "concept_imprime" / "geometrie"
R_ENTREE, R_SORTIE = 77.0, 33.0      # mm
LONGUEUR_TUBE = 394.0                # mm


def stl_ascii(chemin: Path, regions: dict):
    """regions : {nom: tableau (n, 3, 3) en m}."""
    with open(chemin, "w") as f:
        for nom, tri in regions.items():
            f.write(f"solid {nom}\n")
            for a, b, c in tri:
                n = np.cross(b - a, c - a)
                n = n / (np.linalg.norm(n) or 1)
                f.write(f" facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n  outer loop\n")
                for p in (a, b, c):
                    f.write(f"   vertex {p[0]:.9e} {p[1]:.9e} {p[2]:.9e}\n")
                f.write("  endloop\n endfacet\n")
            f.write(f"endsolid {nom}\n")


def domaine(a0, a1, ymin, ymax, n=230):
    """Secteur d'anneau extrudé en y (m) : régions entree (r = R_ENTREE), sortie (r = R_SORTIE), cotes, bouts."""
    ang = np.radians(np.linspace(a0, a1, n + 1))
    P = lambda r, a, y: np.array([r * 1e-3 * math.cos(a), y, r * 1e-3 * math.sin(a)])
    ent, sor, cot, bou = [], [], [], []
    for i in range(n):
        a, b = ang[i], ang[i + 1]
        for r, L, sens in ((R_ENTREE, ent, 1), (R_SORTIE, sor, -1)):
            p00, p01, p10, p11 = P(r, a, ymin), P(r, a, ymax), P(r, b, ymin), P(r, b, ymax)
            L += [[p00, p10, p11], [p00, p11, p01]] if sens > 0 else [[p00, p11, p10], [p00, p01, p11]]
        for y, sens in ((ymin, -1), (ymax, 1)):
            q = [P(R_SORTIE, a, y), P(R_ENTREE, a, y), P(R_ENTREE, b, y), P(R_SORTIE, b, y)]
            bou += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]] if sens < 0 else [[q[0], q[2], q[1]], [q[0], q[3], q[2]]]
    for a, sens in ((ang[0], -1), (ang[-1], 1)):
        q = [P(R_SORTIE, a, ymin), P(R_ENTREE, a, ymin), P(R_ENTREE, a, ymax), P(R_SORTIE, a, ymax)]
        cot += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]] if sens > 0 else [[q[0], q[2], q[1]], [q[0], q[3], q[2]]]
    return {k: np.array(v) for k, v in (("entree", ent), ("sortie", sor), ("cotes", cot), ("bouts", bou))}


def creer(dossier, version, debit_m3h=830.0, base=1.0, niveau=2, nproc=24, iterations=3000):
    import pyvista as pv
    cas = Path(dossier)
    (cas / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    g = json.loads((GEO / "geometrie.json").read_text())
    P = g["parametres"]
    a0, a1 = P["secteur_deg"]
    per = g["periode_mm"] * 1e-3
    # solide en m
    s = pv.read(GEO / f"solide_{version}.stl").scale(1e-3)
    s.save(cas / "constant" / "triSurface" / "paroi.stl", binary=False)
    stl_ascii(cas / "constant" / "triSurface" / "domaine.stl", domaine(a0, a1, -1e-3, per + 1e-3))
    # fond de maillage
    xs = [R_ENTREE * math.cos(math.radians(a)) for a in np.linspace(a0, a1, 400)] + [0.0]
    zs = [R_ENTREE * math.sin(math.radians(a)) for a in np.linspace(a0, a1, 400)] + [0.0]
    x0, x1 = (min(xs) - 3) * 1e-3, (max(xs) + 3) * 1e-3
    z0, z1 = (min(zs) - 3) * 1e-3, (max(zs) + 3) * 1e-3
    nx, nz = round((x1 - x0) / (base * 1e-3)), round((z1 - z0) / (base * 1e-3))
    ny = max(2, round(per / (base * 1e-3)))
    cyc = lambda nom, voisin, faces, sep: (
        f"    {nom}\n    {{\n        type cyclicAMI;\n        neighbourPatch {voisin};\n        transform translational;\n"
        f"        separationVector (0 {sep:.9g} 0);\n        lowWeightCorrection 0.2;\n        faces ({faces});\n    }}\n")
    ecrire(cas, "system/blockMeshDict", f"""scale 1;
vertices
(
    ({x0:.9g} 0 {z0:.9g}) ({x1:.9g} 0 {z0:.9g}) ({x1:.9g} {per:.9g} {z0:.9g}) ({x0:.9g} {per:.9g} {z0:.9g})
    ({x0:.9g} 0 {z1:.9g}) ({x1:.9g} 0 {z1:.9g}) ({x1:.9g} {per:.9g} {z1:.9g}) ({x0:.9g} {per:.9g} {z1:.9g})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1) );
boundary
(
    fond {{ type patch; faces ((0 4 7 3) (1 2 6 5) (0 3 2 1) (4 5 6 7)); }}
{cyc("y0", "y1", "(0 1 5 4)", per)}{cyc("y1", "y0", "(3 7 6 2)", -per)});
""")
    # point dans l'air : entre le filtre et le bout des lamelles, au milieu du secteur
    am = math.radians((a0 + a1) / 2)
    rl = (P["r_ext"] + R_ENTREE) / 2
    loc = (rl * 1e-3 * math.cos(am), 0.53 * per, rl * 1e-3 * math.sin(am))
    ecrire(cas, "system/snappyHexMeshDict", f"""castellatedMesh true;
snap            true;
addLayers       false;
geometry
{{
    paroi.stl   {{ type triSurfaceMesh; name paroi; }}
    domaine.stl
    {{
        type triSurfaceMesh; name domaine;
        regions {{ entree {{ name entree; }} sortie {{ name sortie; }} cotes {{ name cotes; }} bouts {{ name bouts; }} }}
    }}
    zone
    {{
        type searchableCylinder; point1 (0 -0.001 0); point2 (0 {per + 1e-3:.9g} 0); radius {R_ENTREE * 1e-3:.9g};
    }}
}}
castellatedMeshControls
{{
    maxLocalCells 20000000; maxGlobalCells 80000000; minRefinementCells 0;
    maxLoadUnbalance 0.10; nCellsBetweenLevels 2;
    features ();
    refinementSurfaces
    {{
        paroi   {{ level ({niveau} {niveau}); patchInfo {{ type wall; }} }}
        domaine
        {{
            level ({niveau} {niveau});
            regions
            {{
                entree {{ level ({niveau} {niveau}); patchInfo {{ type patch; }} }}
                sortie {{ level ({niveau} {niveau}); patchInfo {{ type patch; }} }}
                cotes  {{ level ({niveau} {niveau}); patchInfo {{ type patch; }} }}
                bouts  {{ level (0 0); patchInfo {{ type patch; }} }}
            }}
        }}
    }}
    resolveFeatureAngle 30;
    refinementRegions {{ zone {{ mode inside; levels ((1 {niveau})); }} }}
    locationInMesh ({loc[0]:.9g} {loc[1]:.9g} {loc[2]:.9g});
    allowFreeStandingZoneFaces true;
}}
snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; nFeatureSnapIter 10;
    implicitFeatureSnap true; explicitFeatureSnap false; multiRegionFeatureSnap false; }}
addLayersControls {{ relativeSizes true; layers {{}}; expansionRatio 1.2; finalLayerThickness 0.4;
    minThickness 0.1; nGrow 0; featureAngle 60; nRelaxIter 3; nSmoothSurfaceNormals 1; nSmoothNormals 3;
    nSmoothThickness 10; maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3; minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0; nLayerIter 50; }}
meshQualityControls {{ #includeEtc "caseDicts/meshQualityDict"
    nSmoothScale 4; errorReduction 0.75; relaxed {{ maxNonOrtho 75; }} }}
mergeTolerance 1e-6;
""")
    # débit de la tranche
    Q = debit_m3h / 3600 * g["periode_mm"] / LONGUEUR_TUBE
    th = math.radians(a1 - a0)
    U_entree = Q / (th * R_ENTREE * 1e-3 * per)
    cyc_bc = '    "(y0|y1)" { type cyclicAMI; }\n    #includeEtc "caseDicts/setConstraintTypes"\n'
    for nom, classe, dim, interne, cl in (
            ("U", "volVectorField", "[0 1 -1 0 0 0 0]", "(0 0 0)",
             {"entree": f"type flowRateInletVelocity; volumetricFlowRate {Q:.9g}; value uniform (0 0 0);",
              "sortie": "type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0);",
              "cotes": "type slip;", "paroi": "type noSlip;"}),
            ("p", "volScalarField", "[0 2 -2 0 0 0 0]", "0",
             {"entree": "type zeroGradient;", "sortie": "type fixedValue; value uniform 0;",
              "cotes": "type zeroGradient;", "paroi": "type zeroGradient;"}),
            ("T", "volScalarField", "[0 0 0 0 0 0 0]", "0",
             {"entree": "type fixedValue; value uniform 0;",
              "sortie": "type inletOutlet; inletValue uniform 0; value uniform 0;",
              "cotes": "type zeroGradient;", "paroi": "type fixedValue; value uniform 1;"})):
        bf = "".join(f"    {p}\n    {{\n        {cl[p]}\n    }}\n" for p in ("entree", "sortie", "cotes", "paroi"))
        bf += f"    \"(bouts|fond)\"\n    {{\n        {cl['cotes']}\n    }}\n"
        ecrire(cas, f"0/{nom}", f"dimensions      {dim};\ninternalField   uniform {interne};\n\n"
                                f"boundaryField\n{{\n{bf}{cyc_bc}}}\n", classe)
    systeme(cas, False, iterations, 0, nproc, None, iterations=iterations)
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
    # le calcul n'est lancé que par Allrun ; Allmesh ne fait que le maillage (pour le vérifier avant)
    entete = f"""#!/bin/bash
# Cas généré par outils/cfd_3d/creer_cas_concept_imprime.py (OpenFOAM v2606)
cd "$(dirname "$0")" || exit 1
set -e
"""
    (cas / "Allmesh").write_text(entete + f"""[ -d 0.orig ] || mv 0 0.orig
surfaceCheck constant/triSurface/paroi.stl > log.surfaceCheck 2>&1 || true
blockMesh > log.blockMesh 2>&1
decomposePar -force > log.decomposePar 2>&1
mpirun -np {nproc} snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
for d in processor*; do rm -rf $d/0; cp -r 0.orig $d/0; done
mpirun -np {nproc} checkMesh -parallel > log.checkMesh 2>&1 || true
reconstructParMesh -constant > log.reconstructParMesh 2>&1
touch MAILLE
""")
    (cas / "Allrun").write_text(entete + f"""[ -f MAILLE ] || bash Allmesh
mpirun -np {nproc} simpleFoam -parallel > log.simpleFoam 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
""")
    for f in ("Allmesh", "Allrun"):
        (cas / f).chmod(0o755)
    meta = dict(cas="concept_imprime", version=version, debit_m3h=debit_m3h, debit_tranche_m3s=Q, U_entree=U_entree,
                periode_mm=g["periode_mm"], secteur_deg=[a0, a1], r_entree_mm=R_ENTREE, r_sortie_mm=R_SORTIE,
                air=AIR, nproc=nproc, maillage=dict(base_mm=base, niveau=niveau), iterations=iterations,
                mcp_tranche=Q * AIR["rho"] * AIR["cp"], mcp_tube=debit_m3h / 3600 * AIR["rho"] * AIR["cp"],
                geometrie=dict(parametres=P, centres_profils=g["versions"][version]["centres_profils"],
                               aire_paroi_mm2=g["versions"][version]["aire_mm2"]))
    (cas / "cas.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--version", required=True, help="clé de geometrie.json : sans, avec, continu, decale4, ...")
    ap.add_argument("--debit", type=float, default=830.0)
    ap.add_argument("--base", type=float, default=1.0)
    ap.add_argument("--niveau", type=int, default=2)
    ap.add_argument("--nproc", type=int, default=24)
    ap.add_argument("--iterations", type=int, default=3000)
    a = ap.parse_args()
    m = creer(a.dossier, a.version, a.debit, a.base, a.niveau, a.nproc, a.iterations)
    print(json.dumps({k: m[k] for k in ("version", "debit_tranche_m3s", "U_entree")}, ensure_ascii=False))
