#!/usr/bin/env python3
"""
Cas OpenFOAM 3D de l'échangeur Ø 150 à canal hélicoïdal (outils/cad/echangeur_d150.py), côté air.

Géométrie : surfaces docs/formes/cylindre_d150_helice/cfd/{entree,sortie,tubes,ailette,parois}.stl (mètres),
écrites par outils/cad/export_cfd_d150.py. Maillage : blockMesh + snappyHexMesh (tubes raffinés).
Physique : simpleFoam stationnaire, k-ω SST, air à 20 °C. Deux températures passives sur le même écoulement
(scalarTransport, entrée 0, parois chaudes 1, diffusivité ν/Pr + νt/Prt) :
  Tf  ailette « froide » : tubes ET ailette à 1 (ailette parfaitement conductrice, borne haute)
  Tp  ailette « passive » : tubes à 1, ailette adiabatique (borne basse)
Mesures : débit, pression moyenne (surface et débit) entrée / sortie, T de mélange en sortie → ε, NTU, hA.
Coupes du maillage écrites à t = 0 (postProcess, système « coupes ») pour la page HTML du maillage.

    .venv/bin/python conception_echangeur/outils/cfd_3d/creer_cas_d150.py --dossier cfd_campagne/d150_helice/U5 \
        --vitesse 5 --nproc 64
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
GEO = RACINE / "docs/formes/cylindre_d150_helice"
AIR = dict(nu=1.516e-5, rho=1.204, cp=1006.0, Pr=0.71, Prt=0.85)
PATCHS = ("entree", "sortie", "tubes", "ailette", "parois")
ENTETE = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       {classe};
    object      {objet};
}}
"""


def ecrire(cas: Path, chemin: str, contenu: str, classe="dictionary"):
    f = cas / chemin
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(ENTETE.format(classe=classe, objet=f.name) + contenu)


def bornes_stl(f: Path):
    import pyvista as pv
    b = pv.read(f).bounds
    return np.array(b[0::2]), np.array(b[1::2])


def champ(cas, nom, classe, dim, interne, bc):
    corps = "\n".join(f'    "{k}"\n    {{\n        {v}\n    }}' for k, v in bc.items())   # guillemets : expressions
    ecrire(cas, f"0/{nom}", f"dimensions {dim};\ninternalField uniform {interne};\nboundaryField\n{{\n    #includeEtc \"caseDicts/setConstraintTypes\"\n{corps}\n}}\n",
           classe=classe)


def creer(dossier: str, U=5.0, nproc=64, base=3.0, niv_tubes=3, niv_ailette=2, niv_parois=1, iterations=3000):
    cas = Path(dossier)
    if cas.exists():
        shutil.rmtree(cas)
    (cas / "constant/triSurface").mkdir(parents=True)
    for p in PATCHS:
        shutil.copy(GEO / "cfd" / f"{p}.stl", cas / "constant/triSurface" / f"{p}.stl")
    dim = json.loads((GEO / "dimensions.json").read_text())
    pr = dim["parametres"]
    # boîte de fond : bornes de toutes les surfaces + une maille
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for p in PATCHS:
        a, b = bornes_stl(cas / "constant/triSurface" / f"{p}.stl")
        lo, hi = np.minimum(lo, a), np.maximum(hi, b)
    h = base * 1e-3
    lo, hi = lo - 1.5 * h, hi + 1.5 * h
    n = np.ceil((hi - lo) / h).astype(int)
    hi = lo + n * h
    # point intérieur : dans le canal, loin des tubes
    tubes = np.array(dim["tubes"]["positions_xy_mm"])
    pas, gap = dim["helice"]["pas_mm"], pr["conduit_axial"]
    rm = (dim["rayons_mm"]["noyau"] + dim["rayons_mm"]["interieur"]) / 2
    for deg in range(0, 360, 7):
        t = math.radians(deg)
        q = np.array([rm * math.cos(t), rm * math.sin(t)])
        if np.min(np.linalg.norm(tubes - q, axis=1)) > 6 and 30 < deg < 300:
            break
    loc = (q[0] * 1e-3, q[1] * 1e-3, (pas * deg / 360 + gap / 2) * 1e-3)

    ecrire(cas, "system/blockMeshDict", f"""convertToMeters 1;
vertices
(
    ({lo[0]} {lo[1]} {lo[2]}) ({hi[0]} {lo[1]} {lo[2]}) ({hi[0]} {hi[1]} {lo[2]}) ({lo[0]} {hi[1]} {lo[2]})
    ({lo[0]} {lo[1]} {hi[2]}) ({hi[0]} {lo[1]} {hi[2]}) ({hi[0]} {hi[1]} {hi[2]}) ({lo[0]} {hi[1]} {hi[2]})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({n[0]} {n[1]} {n[2]}) simpleGrading (1 1 1) );
boundary ( fond {{ type wall; faces ( (0 3 2 1) (4 5 6 7) (0 1 5 4) (1 2 6 5) (2 3 7 6) (3 0 4 7) ); }} );
""")
    geom = "\n".join(f'    {p} {{ type triSurfaceMesh; file "{p}.stl"; }}' for p in PATCHS)
    niv = dict(entree=niv_parois, sortie=niv_parois, tubes=niv_tubes, ailette=niv_ailette, parois=niv_parois)
    surf = "\n".join(f"        {p} {{ level ({niv[p]} {niv[p]}); patchInfo {{ type {'patch' if p in ('entree', 'sortie') else 'wall'}; }} }}"
                     for p in PATCHS)
    ecrire(cas, "system/snappyHexMeshDict", f"""castellatedMesh true;
snap            true;
addLayers       false;
geometry
{{
{geom}
}}
castellatedMeshControls
{{
    maxLocalCells       4000000;
    maxGlobalCells      40000000;
    minRefinementCells  10;
    maxLoadUnbalance    0.10;
    nCellsBetweenLevels 3;
    features            ();
    refinementSurfaces
    {{
{surf}
    }}
    resolveFeatureAngle 30;
    refinementRegions
    {{
        tubes {{ mode distance; levels ((0.0008 {niv_tubes}) (0.0025 {max(niv_tubes - 1, 1)})); }}
    }}
    locationInMesh ({loc[0]:.6f} {loc[1]:.6f} {loc[2]:.6f});
    allowFreeStandingZoneFaces false;
}}
snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 50;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap true;
    explicitFeatureSnap false;
    multiRegionFeatureSnap false;
}}
addLayersControls
{{
    relativeSizes true; layers {{}}; expansionRatio 1.2; finalLayerThickness 0.4; minThickness 0.1;
    nGrow 0; featureAngle 60; nRelaxIter 3; nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10;
    maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3; minMedialAxisAngle 90; nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}
meshQualityControls
{{
    maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80; minVol 1e-16;
    minTetQuality 1e-15; minArea -1; minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.05;
    minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4; errorReduction 0.75;
}}
mergeTolerance 1e-6;
""")
    # champs
    Dh = 4 * gap * pr["conduit_radial"] / (2 * (gap + pr["conduit_radial"])) * 1e-3
    k = 1.5 * (0.05 * U) ** 2
    om = math.sqrt(k) / (0.09 ** 0.25 * 0.07 * Dh)
    murs = "(tubes|ailette|parois|fond).*"   # noms de patchs en expressions (snappy peut suffixer le nom)
    champ(cas, "U", "volVectorField", "[0 1 -1 0 0 0 0]", "(0 0 0)", {
        "entree.*": f"type fixedValue; value uniform (0 {U} 0);",
        "sortie.*": "type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0);",
        murs: "type noSlip;"})
    champ(cas, "p", "volScalarField", "[0 2 -2 0 0 0 0]", "0", {
        "entree.*": "type zeroGradient;", "sortie.*": "type fixedValue; value uniform 0;", murs: "type zeroGradient;"})
    champ(cas, "k", "volScalarField", "[0 2 -2 0 0 0 0]", f"{k:.5g}", {
        "entree.*": f"type fixedValue; value uniform {k:.5g};",
        "sortie.*": f"type inletOutlet; inletValue uniform {k:.5g}; value uniform {k:.5g};",
        murs: f"type kqRWallFunction; value uniform {k:.5g};"})
    champ(cas, "omega", "volScalarField", "[0 0 -1 0 0 0 0]", f"{om:.5g}", {
        "entree.*": f"type fixedValue; value uniform {om:.5g};",
        "sortie.*": f"type inletOutlet; inletValue uniform {om:.5g}; value uniform {om:.5g};",
        murs: f"type omegaWallFunction; value uniform {om:.5g};"})
    champ(cas, "nut", "volScalarField", "[0 2 -1 0 0 0 0]", "0", {
        "(entree|sortie).*": "type calculated; value uniform 0;", murs: "type nutUSpaldingWallFunction; value uniform 0;"})
    for T, ail in (("Tf", "type fixedValue; value uniform 1;"), ("Tp", "type zeroGradient;")):
        champ(cas, T, "volScalarField", "[0 0 0 0 0 0 0]", "0", {
            "entree.*": "type fixedValue; value uniform 0;",
            "sortie.*": "type inletOutlet; inletValue uniform 0; value uniform 0;",
            "tubes.*": "type fixedValue; value uniform 1;", "ailette.*": ail, "(parois|fond).*": "type zeroGradient;"})
    ecrire(cas, "constant/transportProperties", f"transportModel Newtonian;\nnu {AIR['nu']};\n")
    ecrire(cas, "constant/turbulenceProperties", "simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }\n")
    alphaD, alphaDt = 1 / AIR["Pr"], 1 / AIR["Prt"]
    surfval = lambda nom, patch, op, champs, extra="": f"""    {nom}
    {{
        type surfaceFieldValue; libs (fieldFunctionObjects); writeControl timeStep; writeInterval 10;
        log false; writeFields false; regionType patch; name {patch}; operation {op}; fields ({champs}); {extra}
    }}"""
    fonctions = "\n".join([
        *(f"""    {T}
    {{
        type scalarTransport; libs (solverFunctionObjects); field {T}; alphaD {alphaD:.6f}; alphaDt {alphaDt:.6f};
        nCorr 1; writeControl writeTime;
    }}""" for T in ("Tf", "Tp")),
        surfval("pEntree", "entree", "areaAverage", "p"),
        surfval("pSortie", "sortie", "areaAverage", "p"),
        surfval("pEntreeDebit", "entree", "weightedAreaAverage", "p", "weightField phi;"),
        surfval("pSortieDebit", "sortie", "weightedAreaAverage", "p", "weightField phi;"),
        surfval("TSortie", "sortie", "weightedAreaAverage", "Tf Tp", "weightField phi;"),
        surfval("debitEntree", "entree", "sum", "phi"),
        surfval("debitSortie", "sortie", "sum", "phi"),
        """    yPlus { type yPlus; libs (fieldFunctionObjects); writeControl writeTime; }""",
    ])
    ecrire(cas, "system/controlDict", f"""application simpleFoam;
startFrom latestTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1;
writeControl timeStep; writeInterval 500; purgeWrite 2; writeFormat binary; writePrecision 8;
writeCompression off; timeFormat general; timePrecision 6; runTimeModifiable true;
functions
{{
{fonctions}
}}
""")
    ecrire(cas, "system/fvSchemes", """ddtSchemes      { default steadyState; }
gradSchemes     { default cellLimited Gauss linear 1; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss limitedLinear 1;
    div(phi,omega)  bounded Gauss limitedLinear 1;
    div(phi,Tf)     bounded Gauss limitedLinear 1;
    div(phi,Tp)     bounded Gauss limitedLinear 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.33; }
interpolationSchemes { default linear; }
snGradSchemes   { default limited corrected 0.33; }
wallDist        { method meshWave; }
""")
    ecrire(cas, "system/fvSolution", """solvers
{
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.05; }
    "(U|k|omega|Tf|Tp)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.1; }
}
SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent no;
    residualControl { p 1e-4; U 1e-5; "(k|omega)" 1e-5; }
}
relaxationFactors { fields { p 0.3; } equations { U 0.7; "(k|omega)" 0.6; "(Tf|Tp)" 0.9; } }
""")
    ecrire(cas, "system/decomposeParDict", f"numberOfSubdomains {nproc};\nmethod scotch;\n")
    # coupes du maillage (cellules coupées, sans interpolation) pour la page HTML, écrites à t = 0
    zc = [0.5 * gap * 1e-3, 0.5 * dim["longueur_interieure_mm"] * 1e-3]
    ecrire(cas, "system/coupes", f"""functions
{{
coupes
{{
    type surfaces; libs (sampling); surfaceFormat vtk; interpolate false; fields (p U Tf Tp);
    surfaces
    {{
        horizontale_bas  {{ type cuttingPlane; point (0 0 {zc[0]:.5f}); normal (0 0 1); interpolate false; }}
        horizontale_mil  {{ type cuttingPlane; point (0 0 {zc[1]:.5f}); normal (0 0 1); interpolate false; }}
        meridienne       {{ type cuttingPlane; point (0 0 0); normal (1 0 0); interpolate false; }}
    }}
}}
}}
""")
    (cas / "Allrun").write_text(f"""#!/bin/bash
# Cas généré par conception_echangeur/outils/cfd_3d/creer_cas_d150.py
cd "$(dirname "$0")" || exit 1
set -e
[ -d 0.orig ] || mv 0 0.orig
blockMesh > log.blockMesh 2>&1
decomposePar -force > log.decomposePar 2>&1
mpirun -np {nproc} snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
mpirun -np {nproc} checkMesh -parallel > log.checkMesh 2>&1 || true
for d in processor*; do rm -rf $d/0; cp -r 0.orig $d/0; done
reconstructParMesh -constant > log.reconstructParMesh 2>&1
rm -rf 0; cp -r 0.orig 0
postProcess -dict system/coupes -time 0 > log.coupes 2>&1 || true
foamToVTK -time 0 -no-internal -exclude-patches '(fond)' -name VTK_maillage > log.vtk_maillage 2>&1 || true
touch MAILLAGE_FINI
mpirun -np {nproc} simpleFoam -parallel > log.simpleFoam 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
postProcess -dict system/coupes -latestTime -fields '(p U Tf Tp)' > log.coupes_fin 2>&1 || true
touch FINI
""")
    (cas / "Allrun").chmod(0o755)
    meta = dict(U_conduit=U, debit_m3h=U * gap * pr["conduit_radial"] * 1e-6 * 3600, Dh_conduit_m=Dh, k=k, omega=om,
                base_mm=base, niveaux=dict(tubes=niv_tubes, ailette=niv_ailette, parois=niv_parois),
                maille_tubes_mm=base / 2 ** niv_tubes, cellules_fond=int(np.prod(n)), locationInMesh=loc,
                nproc=nproc, iterations=iterations, air=AIR)
    (cas / "cas.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--vitesse", type=float, default=5.0, help="vitesse dans le conduit d'entrée (m/s)")
    ap.add_argument("--nproc", type=int, default=64)
    ap.add_argument("--base", type=float, default=3.0, help="maille de fond (mm)")
    ap.add_argument("--niveau-tubes", type=int, default=3, help="3 → 0,375 mm ; 4 → 0,19 mm (base 3 mm)")
    ap.add_argument("--niveau-ailette", type=int, default=2, help="2 → 0,75 mm ; 3 → 0,375 mm")
    ap.add_argument("--niveau-parois", type=int, default=1, help="1 → 1,5 mm ; 2 → 0,75 mm")
    ap.add_argument("--iterations", type=int, default=3000)
    a = ap.parse_args()
    print(json.dumps(creer(a.dossier, a.vitesse, a.nproc, a.base, a.niveau_tubes, a.niveau_ailette, a.niveau_parois,
                           iterations=a.iterations), indent=1))
