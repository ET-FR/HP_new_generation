#!/usr/bin/env python3
"""
Cas OpenFOAM 3D du secteur périodique de 1/8 (outils/cad/secteur_periodique.py, géométrie : outils/cad/stl_secteur.py).

Fond de maillage = le secteur lui-même (blockMesh, arcs) : r de 33 mm (sortie) à 77 mm (entrée, filtre), φ sur un secteur
de 28,75°, y sur la période de 5 mm. Faces exactes :
  entree  r = 77 mm : débit imposé (830 m³/h × 5/394 × 1/8), vitesse radiale uniforme, T = 0
  sortie  r = 33 mm : p = 0
  per0 / per1  côtés du secteur : cyclicAMI en rotation autour de l'axe du tube (y)
  y0 / y1      faces de la tranche : cyclicAMI en translation
  paroi   solide (snappyHexMesh) : non-glissement, T = 1
snappyHexMesh en SÉRIE (le maillage parallèle avec des cyclicAMI plantait le 13/11), puis découpe pour simpleFoam.

    .venv/bin/python conception_echangeur/outils/cfd_3d/creer_cas_secteur.py --modele continu --dossier <cas>
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "outils" / "cfd_2d"))
from creer_cas import AIR, ecrire, systeme  # noqa: E402

GEO = RACINE / "cfd_campagne" / "secteur" / "geometrie"
R_ENTREE, R_SORTIE = 77.0, 33.0
LONGUEUR_TUBE = 394.0


def creer(dossier, modele, debit_m3h=830.0, base=1.0, niveau=2, nproc=16, iterations=3000):
    import pyvista as pv
    cas = Path(dossier)
    (cas / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    g = json.loads((GEO / "geometrie.json").read_text())
    inf = g["modeles"][modele]
    f0, f1 = inf["secteur_deg"]
    da = f1 - f0
    per_mm = inf.get("periode_mm", g["periode_mm"])
    per = per_mm * 1e-3
    n_sect = int(g["secteur"]["n_secteurs"])
    pv.read(GEO / f"solide_{modele}.stl").scale(1e-3).save(cas / "constant" / "triSurface" / "paroi.stl", binary=False)
    ri, ro = R_SORTIE * 1e-3, R_ENTREE * 1e-3
    pt = lambda r, a, y: f"({r * math.cos(math.radians(a)):.9g} {y:.9g} {r * math.sin(math.radians(a)):.9g})"
    am = (f0 + f1) / 2
    nr = round((ro - ri) / (base * 1e-3))
    nt = round(ro * math.radians(da) / (base * 1e-3))
    ny = max(2, round(per / (base * 1e-3)))
    cyc = lambda nom, voisin, faces, transf: (
        f"    {nom}\n    {{\n        type cyclicAMI;\n        neighbourPatch {voisin};\n{transf}        lowWeightCorrection 0.2;\n"
        f"        faces ({faces});\n    }}\n")
    rot = "        transform rotational;\n        rotationAxis (0 1 0);\n        rotationCentre (0 0 0);\n"
    tr = lambda s: f"        transform translational;\n        separationVector (0 {s:.9g} 0);\n"
    ecrire(cas, "system/blockMeshDict", f"""scale 1;
vertices
(
    {pt(ri, f0, 0)} {pt(ro, f0, 0)} {pt(ro, f1, 0)} {pt(ri, f1, 0)}
    {pt(ri, f0, per)} {pt(ro, f0, per)} {pt(ro, f1, per)} {pt(ri, f1, per)}
);
blocks ( hex (0 3 2 1 4 7 6 5) ({nt} {nr} {ny}) simpleGrading (1 1 1) );
edges
(
    arc 1 2 {pt(ro, am, 0)}
    arc 0 3 {pt(ri, am, 0)}
    arc 5 6 {pt(ro, am, per)}
    arc 4 7 {pt(ri, am, per)}
);
boundary
(
    entree {{ type patch; faces ((1 2 6 5)); }}
    sortie {{ type patch; faces ((0 4 7 3)); }}
{cyc("per0", "per1", "(0 1 5 4)", rot)}{cyc("per1", "per0", "(3 7 6 2)", rot)}{cyc("y0", "y1", "(0 3 2 1)", tr(per))}{cyc("y1", "y0", "(4 5 6 7)", tr(-per))});
""")
    rl = (g["parametres"]["r_ext"] + R_ENTREE) / 2
    loc = (rl * 1e-3 * math.cos(math.radians(am + 0.37)), 0.53 * per, rl * 1e-3 * math.sin(math.radians(am + 0.37)))
    ecrire(cas, "system/snappyHexMeshDict", f"""castellatedMesh true;
snap            true;
addLayers       false;
geometry
{{
    paroi.stl   {{ type triSurfaceMesh; name paroi; }}
    tout {{ type searchableBox; min (-1 -1 -1); max (1 1 1); }}
}}
castellatedMeshControls
{{
    maxLocalCells 20000000; maxGlobalCells 80000000; minRefinementCells 0;
    maxLoadUnbalance 0.10; nCellsBetweenLevels 2;
    features ();
    refinementSurfaces {{ paroi {{ level ({niveau} {niveau}); patchInfo {{ type wall; }} }} }}
    resolveFeatureAngle 30;
    refinementRegions {{ tout {{ mode inside; levels ((1 {niveau})); }} }}
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
    Q = debit_m3h / 3600 * per_mm / LONGUEUR_TUBE / n_sect
    cyc_bc = '    "(y0|y1|per0|per1)" { type cyclicAMI; }\n    #includeEtc "caseDicts/setConstraintTypes"\n'
    for nom, classe, dim, interne, cl in (
            ("U", "volVectorField", "[0 1 -1 0 0 0 0]", "(0 0 0)",
             {"entree": f"type flowRateInletVelocity; volumetricFlowRate {Q:.9g}; value uniform (0 0 0);",
              "sortie": "type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0);", "paroi": "type noSlip;"}),
            ("p", "volScalarField", "[0 2 -2 0 0 0 0]", "0",
             {"entree": "type zeroGradient;", "sortie": "type fixedValue; value uniform 0;", "paroi": "type zeroGradient;"}),
            ("T", "volScalarField", "[0 0 0 0 0 0 0]", "0",
             {"entree": "type fixedValue; value uniform 0;", "sortie": "type inletOutlet; inletValue uniform 0; value uniform 0;",
              "paroi": "type fixedValue; value uniform 1;"})):
        bf = "".join(f"    {p}\n    {{\n        {cl[p]}\n    }}\n" for p in ("entree", "sortie", "paroi"))
        ecrire(cas, f"0/{nom}", f"dimensions      {dim};\ninternalField   uniform {interne};\n\n"
                                f"boundaryField\n{{\n{bf}{cyc_bc}}}\n", classe)
    systeme(cas, False, iterations, 0, nproc, None, iterations=iterations)
    fv = (cas / "system" / "fvSchemes").read_text()
    fv = fv.replace("laplacianSchemes { default Gauss linear corrected; }", "laplacianSchemes { default Gauss linear limited corrected 0.5; }")
    fv = fv.replace("snGradSchemes   { default corrected; }", "snGradSchemes   { default limited corrected 0.5; }")
    fv = fv.replace("gradSchemes     { default Gauss linear; }", "gradSchemes     { default cellLimited Gauss linear 1; }")
    (cas / "system" / "fvSchemes").write_text(fv)
    (cas / "system" / "fvSolution").write_text((cas / "system" / "fvSolution").read_text()
                                                .replace("relaxationFactors { equations { U 0.9; T 0.9; } }",
                                                         "relaxationFactors { equations { U 0.7; T 0.9; } fields { p 0.3; } }")
                                                .replace("consistent          yes;", "consistent          no;"))
    entete = '#!/bin/bash\n# Cas généré par outils/cfd_3d/creer_cas_secteur.py (OpenFOAM v2606)\ncd "$(dirname "$0")" || exit 1\nset -e\n'
    (cas / "Allmesh").write_text(entete + """[ -d 0.orig ] || mv 0 0.orig
rm -rf 0 && cp -r 0.orig 0
blockMesh > log.blockMesh 2>&1
snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
checkMesh > log.checkMesh 2>&1 || true
decomposePar -force > log.decomposePar 2>&1
touch MAILLE
""")
    (cas / "Allrun").write_text(entete + f"""[ -f MAILLE ] || bash Allmesh
mpirun -np {nproc} simpleFoam -parallel > log.simpleFoam 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
""")
    for f in ("Allmesh", "Allrun"):
        (cas / f).chmod(0o755)
    meta = dict(cas="secteur", version=modele, debit_m3h=debit_m3h, debit_tranche_m3s=Q, periode_mm=per_mm,
                secteur_deg=[f0, f1], n_secteurs=n_sect, r_entree_mm=R_ENTREE, r_sortie_mm=R_SORTIE, air=AIR, nproc=nproc,
                maillage=dict(base_mm=base, niveau=niveau), iterations=iterations,
                mcp_tranche=Q * AIR["rho"] * AIR["cp"], mcp_tube=debit_m3h / 3600 * AIR["rho"] * AIR["cp"],
                U_entree=Q / (math.radians(da) * R_ENTREE * 1e-3 * per), profils=inf["profils"])
    (cas / "cas.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--modele", required=True, help="decale4, continu, radiales")
    ap.add_argument("--nproc", type=int, default=16)
    ap.add_argument("--iterations", type=int, default=3000)
    a = ap.parse_args()
    m = creer(a.dossier, a.modele, nproc=a.nproc, iterations=a.iterations)
    print(json.dumps({k: m[k] for k in ("version", "debit_tranche_m3s", "U_entree")}, ensure_ascii=False))
