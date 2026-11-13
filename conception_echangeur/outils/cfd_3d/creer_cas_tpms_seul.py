#!/usr/bin/env python3
"""
Cas OpenFOAM 3D : échangeur TPMS seul (feuille TPMS séparant air et propane), côté air.

La feuille (paroi d'épaisseur e) sépare deux labyrinthes qui ne communiquent pas : air et propane.
Seul l'air est calculé : la paroi est supposée à la température du propane (diphasique, h de
quelques milliers de W/m²K contre ~100 côté air), comme pour les tubes et les ailettes.

Équité avec la batterie à tubes (étape 3) : même vitesse en façade (1 m/s), même charge de propane
par m² de face. Le volume du labyrinthe propane par m² de face (L/m²) fixe l'épaisseur du bloc :
    profondeur = V_propane / fraction_propane.
Par défaut, la charge de l'ellipse 2:1 à 2 rangs (2,09 L/m²). Air et propane ont le même volume
(feuille centrée), la paroi de e = 0,3 mm prend le reste.

Domaine : une cellule L × L en section (périodique en y et z, cyclicAMI), le bloc sur toute sa
profondeur, tampons libres en amont (3 mm) et en aval (6 mm). Faces avant et arrière du bloc :
paroi (propane fermé). snappyHexMesh, simpleFoam laminaire, mêmes mesures que l'étape 3.

    python conception_echangeur/outils/cfd_3d/creer_cas_tpms_seul.py --dossier cfd_campagne/tpms_seul/gyroide_L3 \
        --surface gyroide --cellule 3 [--charge 2.094] [--paroi 0.3] [--base 0.15] [--niveau 2]
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
from creer_cas_tpms_tubes import alleger  # noqa: E402
from geometrie import batterie  # noqa: E402
from pac_fenetre.tpms import SURFACES, champ  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("tpms_cas", RACINE / "outils" / "cfd_tpms" / "creer_cas.py")
_tpms = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tpms)
triangles, ecrire_stl = _tpms.triangles, _tpms.ecrire_stl


def charge_reference(forme="ellipse2", rangs=2):
    """Volume de propane par m² de face de la batterie à tubes (mm³/mm² = L/m²)."""
    b = batterie(forme, rangs=rangs)
    return rangs * b.A_int / b.Pt


def partage(surface, L, e, N=96):
    """Niveau n tel que air (F > n) et propane (à plus de e de la surface côté air) aient le même
    volume. Retourne n, fraction air, fraction propane, fraction paroi, surface côté air / volume (1/mm)."""
    s = (np.arange(N) + 0.5) * L / N
    X, Y, Z = np.meshgrid(s, s, s, indexing="ij")
    k = 2 * np.pi / L
    F = champ(surface, k * X, k * Y, k * Z)
    g = np.gradient(np.pad(F, 1, mode="wrap"), L / N)
    G = np.sqrt(sum(a[1:-1, 1:-1, 1:-1] ** 2 for a in g))
    lo, hi = float(F.min()), float(F.max())
    for _ in range(50):
        n = 0.5 * (lo + hi)
        d = (F - n) / np.maximum(G, 1e-9)            # distance signée approchée (mm), > 0 dans l'air
        fa, fp = float((d > 0).mean()), float((d < -e).mean())
        lo, hi = (lo, n) if fp > fa else (n, hi)      # trop de propane : baisser n (air F > n grandit)
    # surface côté air par volume : |∇H| intégré ≈ aire de l'isosurface (méthode de la bande)
    bande = 0.02 * L
    beta = float((np.abs((F - n) / np.maximum(G, 1e-9)) < bande / 2).mean() / bande)
    return n, fa, fp, 1 - fa - fp, beta


def creer(dossier, surface="gyroide", L=3.0, charge=None, e=0.3, U=1.0, nproc=8, iterations=2000,
          base=0.15, niveau=2, pas_stl=None, amont=3.0, aval=6.0):
    cas = Path(dossier)
    (cas / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    charge = charge or charge_reference()
    n, fa, fp, fw, beta = partage(surface, L, e)
    D = charge / fp                                     # profondeur du bloc (mm)
    k = 2 * math.pi / L
    pas_stl = pas_stl or L / 60

    def phi(x, y, z):                                   # > 0 dans le solide (paroi + propane), 0 < x < D
        return np.minimum((n - champ(surface, k * x, k * y, k * z)) / k, np.minimum(x, D - x))

    mg = 0.08 * L
    T = triangles(phi, [(-mg, D + mg), (-mg, L + mg), (-mg, L + mg)], pas_stl)
    T = alleger(T, cible=400_000)
    ecrire_stl(T * 1e-3, cas / "constant" / "triSurface" / "paroi.stl", "binaire TPMS seul")
    g = T.mean(axis=1)
    dedans = (g[:, 1] >= 0) & (g[:, 1] < L) & (g[:, 2] >= 0) & (g[:, 2] < L)
    aire = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    A_air = float(aire[dedans].sum()) * 1e-6

    x0, x1 = -amont * 1e-3, (D + aval) * 1e-3
    Lm = L * 1e-3
    nx, ny = max(4, round((x1 - x0) / (base * 1e-3))), max(4, round(Lm / (base * 1e-3)))
    cyc = lambda nom, voisin, faces, sep: (
        f"    {nom}\n    {{\n        type cyclicAMI;\n        neighbourPatch {voisin};\n        transform translational;\n"
        f"        separationVector ({sep[0]:.9g} {sep[1]:.9g} {sep[2]:.9g});\n        lowWeightCorrection 0.2;\n"
        f"        faces ({faces});\n    }}\n")
    ecrire(cas, "system/blockMeshDict", f"""scale 1;
vertices
(
    ({x0:.9g} 0 0) ({x1:.9g} 0 0) ({x1:.9g} {Lm:.9g} 0) ({x0:.9g} {Lm:.9g} 0)
    ({x0:.9g} 0 {Lm:.9g}) ({x1:.9g} 0 {Lm:.9g}) ({x1:.9g} {Lm:.9g} {Lm:.9g}) ({x0:.9g} {Lm:.9g} {Lm:.9g})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {ny}) simpleGrading (1 1 1) );
boundary
(
    entree {{ type patch; faces ((0 4 7 3)); }}
    sortie {{ type patch; faces ((1 2 6 5)); }}
{cyc("bas", "haut", "(0 1 5 4)", (0, Lm, 0))}{cyc("haut", "bas", "(3 7 6 2)", (0, -Lm, 0))}{cyc("z0", "z1", "(0 3 2 1)", (0, 0, Lm))}{cyc("z1", "z0", "(4 5 6 7)", (0, 0, -Lm))});
""")
    loc = (x0 / 2, 0.37 * Lm, 0.41 * Lm)
    ecrire(cas, "system/snappyHexMeshDict", f"""castellatedMesh true;
snap            true;
addLayers       false;
geometry {{ paroi.stl {{ type triSurfaceMesh; name paroi; }} }}
castellatedMeshControls
{{
    maxLocalCells 20000000; maxGlobalCells 60000000; minRefinementCells 0;
    maxLoadUnbalance 0.10; nCellsBetweenLevels 2;
    features ();
    refinementSurfaces {{ paroi {{ level ({niveau} {niveau}); patchInfo {{ type wall; }} }} }}
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
        bf = "".join(f"    {p}\n    {{\n        {cl[p]}\n    }}\n" for p in ("entree", "sortie", "paroi"))
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
    (cas / "Allrun").write_text(f"""#!/bin/bash
# Cas généré par outils/cfd_3d/creer_cas_tpms_seul.py
cd "$(dirname "$0")" || exit 1
set -e
[ -d 0.orig ] || mv 0 0.orig
blockMesh > log.blockMesh 2>&1
decomposePar -force > log.decomposePar 2>&1
mpirun -np {nproc} snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
for d in processor*; do rm -rf $d/0; cp -r 0.orig $d/0; done
mpirun -np {nproc} checkMesh -parallel > log.checkMesh 2>&1 || true
mpirun -np {nproc} simpleFoam -parallel > log.simpleFoam 2>&1
reconstructParMesh -constant > log.reconstructParMesh 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
""")
    (cas / "Allrun").chmod(0o755)
    Dh = 4 * fa / beta                                   # mm
    meta = dict(cas="batterie", ailettes=True, tpms_seul=True, tpms=surface, U=U, U_domaine=U, air=AIR,
                epaisseur_mm=L, nproc=nproc, forme="tpms_seul",
                nom=f"{SURFACES[surface]['nom']} seul (cellule {L:.3g} mm, paroi {e:g} mm)",
                cellule_tpms_mm=L, paroi_mm=e, niveau_feuille=n, fraction_air=fa, fraction_propane=fp,
                fraction_paroi=fw, beta_air_par_mm=beta, Dh_air_mm=Dh, profondeur_mm=D,
                propane_L_par_m2=charge, charge_relative=charge / charge_reference("rond", 4),
                pas_ailettes_mm=None, epaisseur_ailette_mm=None,
                maillage=dict(cellules=None, base_mm=base, niveau=niveau, paroi_mm=base / 2 ** niveau),
                tranches=dict(n=None), Pt=Lm, Pl=None, rangs=None,
                x_noyau=[0.0, D * 1e-3], x_domaine=[x0, x1], Umax=U / fa,
                Re_Dh=U / fa * Dh * 1e-3 / AIR["nu"], A_air_domaine=A_air, A_tubes_domaine=0.0,
                A_ailettes_domaine=A_air, instationnaire=False, fin=iterations, debut_moyenne=0.75 * iterations)
    (cas / "cas.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--surface", choices=list(SURFACES), default="gyroide")
    ap.add_argument("--cellule", type=float, default=3.0, help="taille de cellule TPMS (mm)")
    ap.add_argument("--charge", type=float, default=None, help="propane par m² de face (L/m²) ; défaut : ellipse 2 rangs")
    ap.add_argument("--paroi", type=float, default=0.3, help="épaisseur de paroi (mm)")
    ap.add_argument("--nproc", type=int, default=8)
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--base", type=float, default=0.15, help="maille de fond (mm)")
    ap.add_argument("--niveau", type=int, default=2, help="niveau de raffinement à la paroi")
    ap.add_argument("--suffixe", default=None)
    a = ap.parse_args()
    m = creer(a.dossier, a.surface, a.cellule, a.charge, a.paroi, nproc=a.nproc, iterations=a.iterations,
              base=a.base, niveau=a.niveau)
    if a.suffixe:
        m["suffixe"] = a.suffixe
        (Path(a.dossier) / "cas.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps({k: m[k] for k in ("nom", "fraction_air", "fraction_propane", "fraction_paroi", "profondeur_mm",
                                        "Dh_air_mm", "Re_Dh", "A_air_domaine")}, indent=1, ensure_ascii=False))
