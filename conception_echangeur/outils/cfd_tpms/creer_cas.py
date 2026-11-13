#!/usr/bin/env python3
"""
Génère un cas OpenFOAM (v2412, ESI) pour mesurer j et f côté AIR d'un noyau TPMS.

Domaine : une cellule TPMS en section (périodique en y et z, patchs cyclicAMI),
profondeur réelle du noyau D dans le sens de l'air (x), tampons libres en amont
et en aval. Le solide (paroi + propane, ou paroi d'un hybride : l'air voit la même
chose) est la région F < niveau, limitée à 0 ≤ x ≤ D ; sa surface est écrite en
STL et maillée par snappyHexMesh. Paroi à température imposée (propane diphasique,
paroi mince), air entrant à T = 0, paroi à T = 1 (scalaire passif, propriétés constantes).

Mesures (fonctions OpenFOAM) : débit, pression moyenne et température de mélange
à l'entrée et à la sortie -> NTU, h, j de Colburn, f apparent (entrée + sortie compris).

    python creer_cas.py --surface gyroide --phi 0.6 --Re 400 --Dh 4 --profondeur 24 \
                        --dossier cas/gyroide_Re400

Re est construit sur Dh air et la vitesse dans les pores u_c = U_front / φ.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE.parent))  # dépôt : pac_fenetre
from pac_fenetre.tpms import SURFACES, champ, geometrie  # noqa: E402

AIR = dict(nu=1.516e-5, rho=1.204, cp=1006.0, Pr=0.71, Prt=0.85)  # air sec à 20 °C
RE_LAMINAIRE_MAX = 300.0   # au-delà : k-ω SST (comme Qureshi, Leeds, au-dessus de Re ≈ 200)


# ---------------------------------------------------------------- surface STL
_COINS = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
_TETRAS = [(0, 5, 1, 6), (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6)]


def fonction_solide(surface: str, niveau: float, L: float, D: float):
    """phi > 0 dans le solide : F < niveau et 0 < x < D (coordonnées en m)."""
    k = 2.0 * math.pi / L

    def phi(x, y, z):
        F = champ(surface, k * x, k * y, k * z)
        return np.minimum(np.minimum(niveau - F, k * x), k * (D - x))
    return phi


def triangles(phi, bornes, pas):
    """Marching tetrahedra vectorisé. Renvoie (n, 3, 3) triangles, normales vers phi < 0 (air)."""
    (x0, x1), (y0, y1), (z0, z1) = bornes
    nx, ny, nz = (max(2, int(math.ceil((b - a) / pas))) for a, b in bornes)
    xs, ys, zs = np.linspace(x0, x1, nx + 1), np.linspace(y0, y1, ny + 1), np.linspace(z0, z1, nz + 1)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    V = phi(X, Y, Z)
    P = np.stack([X, Y, Z], axis=-1)
    tris = []
    for tet in _TETRAS:
        v = [V[c[0]:c[0] + nx, c[1]:c[1] + ny, c[2]:c[2] + nz].ravel() for c in _COINS[list(tet)]]
        p = [P[c[0]:c[0] + nx, c[1]:c[1] + ny, c[2]:c[2] + nz].reshape(-1, 3) for c in _COINS[list(tet)]]
        dedans = [vi > 0 for vi in v]
        code = sum(d.astype(np.int8) << q for q, d in enumerate(dedans))
        for c in range(1, 15):
            m = code == c
            if not m.any():
                continue
            I = [q for q in range(4) if c >> q & 1]
            O = [q for q in range(4) if not c >> q & 1]

            def pt(a, b):
                va, vb = v[a][m], v[b][m]
                t = (va / (va - vb))[:, None]
                return p[a][m] + t * (p[b][m] - p[a][m])
            if len(I) == 1:
                tris.append(np.stack([pt(I[0], O[0]), pt(I[0], O[1]), pt(I[0], O[2])], axis=1))
            elif len(I) == 3:
                tris.append(np.stack([pt(O[0], I[0]), pt(O[0], I[1]), pt(O[0], I[2])], axis=1))
            else:
                a, b, cc, d = pt(I[0], O[0]), pt(I[0], O[1]), pt(I[1], O[1]), pt(I[1], O[0])
                tris.append(np.stack([a, b, cc], axis=1))
                tris.append(np.stack([a, cc, d], axis=1))
    T = np.concatenate(tris)
    # orientation : normale vers l'air (phi décroissant)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    T, n, ln = T[ln > 1e-18], n[ln > 1e-18], ln[ln > 1e-18]
    n /= ln[:, None]
    g = T.mean(axis=1)
    eps = 0.2 * pas
    vers_solide = phi(*(g + eps * n).T) > phi(*(g - eps * n).T)
    T[vers_solide] = T[vers_solide][:, [0, 2, 1]]
    return T


def ecrire_stl(T, chemin: Path, nom="binaire TPMS"):  # ne pas commencer par "solid" (= ASCII)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1)[:, None]
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data = np.zeros(len(T), dtype=dt)
    data["n"], data["v"] = n, T
    with open(chemin, "wb") as f:
        f.write(nom.encode().ljust(80, b" "))
        f.write(np.uint32(len(T)).tobytes())
        f.write(data.tobytes())


# ---------------------------------------------------------------- fichiers OpenFOAM
def entete(classe, objet, loc=None):
    l = f'    location    "{loc}";\n' if loc else ""
    return ("FoamFile\n{\n    version     2.0;\n    format      ascii;\n"
            f"    class       {classe};\n{l}    object      {objet};\n}}\n\n")


def ecrire(dossier: Path, rel: str, classe: str, contenu: str):
    f = dossier / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    obj = Path(rel).name
    f.write_text(entete(classe, obj, str(Path(rel).parent)) + contenu)


def creer_cas(surface, phi_air, Re, Dh_mm, profondeur_mm, dossier, finesse=8, niveau_raff=1,
              nproc=4, iterations=3000, res_stl=40):
    g = geometrie(surface, phi_air, Dh=Dh_mm * 1e-3)
    L, Dh, D, n = g["L"], g["Dh_air"], profondeur_mm * 1e-3, g["niveau"]
    turbulent = Re > RE_LAMINAIRE_MAX
    u_c = Re * AIR["nu"] / Dh                 # vitesse dans les pores
    U = u_c * g["phi_air"]                    # vitesse frontale
    L_amont, L_aval = max(L, 1.5 * Dh), max(2 * L, 3 * Dh)
    dx = Dh / finesse                         # maille de base
    dossier = Path(dossier)
    (dossier / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)

    # surface du solide (débord latéral pour couper proprement les patchs périodiques)
    m = 0.08 * L
    T = triangles(fonction_solide(surface, n, L, D), [(-m, D + m), (-m, L + m), (-m, L + m)], L / res_stl)
    ecrire_stl(T, dossier / "constant" / "triSurface" / "solide.stl")

    x0, x1 = -L_amont, D + L_aval
    nx, nyz = int(math.ceil((x1 - x0) / dx)), max(4, int(math.ceil(L / dx)))
    cyc = lambda nom, voisin, faces, sep: f"""    {nom}
    {{
        type            cyclicAMI;
        neighbourPatch  {voisin};
        transform       translational;
        separationVector ({sep[0]:.9g} {sep[1]:.9g} {sep[2]:.9g});
        lowWeightCorrection 0.2;
        faces           ({faces});
    }}
"""
    ecrire(dossier, "system/blockMeshDict", "dictionary", f"""scale 1;
vertices
(
    ({x0:.9g} 0 0) ({x1:.9g} 0 0) ({x1:.9g} {L:.9g} 0) ({x0:.9g} {L:.9g} 0)
    ({x0:.9g} 0 {L:.9g}) ({x1:.9g} 0 {L:.9g}) ({x1:.9g} {L:.9g} {L:.9g}) ({x0:.9g} {L:.9g} {L:.9g})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {nyz} {nyz}) simpleGrading (1 1 1) );
boundary
(
    entree {{ type patch; faces ((0 4 7 3)); }}
    sortie {{ type patch; faces ((1 2 6 5)); }}
{cyc("y0", "y1", "(0 1 5 4)", (0, L, 0))}{cyc("y1", "y0", "(3 7 6 2)", (0, -L, 0))}{cyc("z0", "z1", "(0 3 2 1)", (0, 0, L))}{cyc("z1", "z0", "(4 5 6 7)", (0, 0, -L))});
""")
    # point dans l'air : tampon amont
    loc = (x0 * 0.5, 0.37 * L, 0.41 * L)
    ecrire(dossier, "system/snappyHexMeshDict", "dictionary", f"""castellatedMesh true;
snap            true;
addLayers       false;
geometry {{ solide.stl {{ type triSurfaceMesh; name solide; }} }}
castellatedMeshControls
{{
    maxLocalCells 4000000; maxGlobalCells 40000000; minRefinementCells 0;
    maxLoadUnbalance 0.10; nCellsBetweenLevels 3;
    features ();
    refinementSurfaces {{ solide {{ level ({niveau_raff} {niveau_raff}); patchInfo {{ type wall; }} }} }}
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
    ecrire(dossier, "system/decomposeParDict", "dictionary", f"numberOfSubdomains {nproc};\nmethod scotch;\n")

    # champs
    paroi = "solide"
    cyc_bc = "    \"(y0|y1|z0|z1)\" { type cyclicAMI; }\n"
    ecrire(dossier, "0/U", "volVectorField", f"""dimensions [0 1 -1 0 0 0 0];
internalField uniform ({U:.6g} 0 0);
boundaryField
{{
    entree {{ type fixedValue; value uniform ({U:.6g} 0 0); }}
    sortie {{ type inletOutlet; inletValue uniform (0 0 0); value uniform ({U:.6g} 0 0); }}
    {paroi} {{ type noSlip; }}
{cyc_bc}}}
""")
    ecrire(dossier, "0/p", "volScalarField", f"""dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{{
    entree {{ type zeroGradient; }}
    sortie {{ type fixedValue; value uniform 0; }}
    {paroi} {{ type zeroGradient; }}
{cyc_bc}}}
""")
    ecrire(dossier, "0/T", "volScalarField", f"""dimensions [0 0 0 0 0 0 0];
internalField uniform 0;
boundaryField
{{
    entree {{ type fixedValue; value uniform 0; }}
    sortie {{ type inletOutlet; inletValue uniform 0; value uniform 0; }}
    {paroi} {{ type fixedValue; value uniform 1; }}
{cyc_bc}}}
""")
    if turbulent:
        I = 0.02
        k = 1.5 * (I * u_c) ** 2
        om = math.sqrt(k) / (0.09 ** 0.25 * 0.07 * Dh)
        for nom, dim, val, mur in (("k", "[0 2 -2 0 0 0 0]", k, "kqRWallFunction"),
                                   ("omega", "[0 0 -1 0 0 0 0]", om, "omegaWallFunction"),
                                   ("nut", "[0 2 -1 0 0 0 0]", 0, "nutLowReWallFunction")):
            ent = (f"type fixedValue; value uniform {val:.6g};" if nom != "nut" else "type calculated; value uniform 0;")
            ecrire(dossier, f"0/{nom}", "volScalarField", f"""dimensions {dim};
internalField uniform {val:.6g};
boundaryField
{{
    entree {{ {ent} }}
    sortie {{ {"type inletOutlet; inletValue uniform %.6g; value uniform %.6g;" % (val, val) if nom != "nut" else "type calculated; value uniform 0;"} }}
    {paroi} {{ type {mur}; value uniform {val:.6g}; }}
{cyc_bc}}}
""")
    ecrire(dossier, "constant/transportProperties", "dictionary", f"transportModel Newtonian;\nnu {AIR['nu']};\n")
    ecrire(dossier, "constant/turbulenceProperties", "dictionary",
           "simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs off; }\n"
           if turbulent else "simulationType laminar;\n")

    plans = "\n".join(f"""    {nom}
    {{
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        writeControl    timeStep;
        writeInterval   10;
        writeFields     false;
        log             false;
        regionType      patch;
        name            {patch};
        operation       {op};
        {"weightField     phi;" if op == "weightedAreaAverage" else ""}
        fields          ({champs});
    }}""" for nom, patch, op, champs in (
        ("pEntree", "entree", "areaAverage", "p"), ("pSortie", "sortie", "areaAverage", "p"),
        ("TSortie", "sortie", "weightedAreaAverage", "T"), ("debit", "entree", "sum", "phi")))
    ecrire(dossier, "system/controlDict", "dictionary", f"""application     simpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         {iterations};
deltaT          1;
writeControl    timeStep;
writeInterval   {iterations};
purgeWrite      1;
writeFormat     binary;
writePrecision  8;
runTimeModifiable true;
functions
{{
    T
    {{
        type            scalarTransport;
        libs            (solverFunctionObjects);
        field           T;
        alphaD          {1 / AIR['Pr']:.6g};
        alphaDt         {1 / AIR['Prt']:.6g};
        {"nut nut;" if turbulent else ""}
        bounded01       false;
    }}
{plans}
}}
""")
    ecrire(dossier, "system/fvSchemes", "dictionary", """ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,T) bounded Gauss linearUpwind grad(T);
    div(phi,k) bounded Gauss upwind;
    div(phi,omega) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited corrected 0.5; }
wallDist { method meshWave; }
""")
    ecrire(dossier, "system/fvSolution", "dictionary", """solvers
{
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-8; relTol 0.05; }
    "(U|k|omega|T)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0.1; }
}
SIMPLE
{
    consistent no;
    nNonOrthogonalCorrectors 1;
    residualControl { p 1e-5; U 1e-6; }
}
relaxationFactors { equations { U 0.7; "(k|omega)" 0.6; T 0.9; } fields { p 0.3; } }
""")
    meta = dict(surface=surface, nom=SURFACES[surface]["nom"], phi_air=g["phi_air"], niveau=n, L=L, Dh=Dh,
                beta_air=g["beta_air"], profondeur=D, Re=Re, u_c=u_c, U_front=U, turbulent=turbulent,
                finesse=finesse, niveau_raff=niveau_raff, nproc=nproc, air=AIR,
                A_front=L * L, A_air=g["beta_air"] * L * L * D + 2 * (1 - g["phi_air"]) * L * L)
    (dossier / "cas.json").write_text(json.dumps(meta, indent=2))
    allrun = f"""#!/bin/bash
# Cas TPMS {surface}, Re = {Re:g}, généré par creer_cas.py
cd "$(dirname "$0")" || exit 1
set -e
blockMesh > log.blockMesh 2>&1
snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
checkMesh > log.checkMesh 2>&1 || true
{"decomposePar -force > log.decomposePar 2>&1" if nproc > 1 else ""}
{"mpirun -np %d simpleFoam -parallel > log.simpleFoam 2>&1" % nproc if nproc > 1 else "simpleFoam > log.simpleFoam 2>&1"}
"""
    (dossier / "Allrun").write_text(allrun)
    os.chmod(dossier / "Allrun", 0o755)
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--surface", choices=list(SURFACES), required=True)
    ap.add_argument("--phi", type=float, default=0.6, help="porosité côté air")
    ap.add_argument("--Re", type=float, required=True, help="Re sur Dh air et vitesse dans les pores")
    ap.add_argument("--Dh", type=float, default=4.0, help="diamètre hydraulique air (mm)")
    ap.add_argument("--profondeur", type=float, default=24.0, help="profondeur du noyau (mm)")
    ap.add_argument("--finesse", type=int, default=8, help="mailles de base par Dh")
    ap.add_argument("--raffinement", type=int, default=1, help="niveau de raffinement à la paroi")
    ap.add_argument("--nproc", type=int, default=4)
    ap.add_argument("--iterations", type=int, default=3000)
    ap.add_argument("--dossier", required=True)
    a = ap.parse_args()
    meta = creer_cas(a.surface, a.phi, a.Re, a.Dh, a.profondeur, a.dossier, a.finesse, a.raffinement,
                     a.nproc, a.iterations)
    print(json.dumps({k: meta[k] for k in ("surface", "L", "Dh", "Re", "u_c", "turbulent")}, indent=1))


if __name__ == "__main__":
    main()
