#!/usr/bin/env python3
"""
Génère un cas OpenFOAM v2606 (ESI) 2D pour l'étude des formes simples (docs/plan_formes_simples.md).

Cas :
  plaques     canal entre deux plaques, stationnaire (simpleFoam)           niveau 0
  tube_isole  tube rond Ø 6 mm seul, instationnaire (pimpleFoam)            niveau 0
  batterie    faisceau d'une forme (rond = validation Zukauskas), instat.   niveaux 0 et 1

Physique commune : air 20 °C à propriétés constantes, laminaire ; vitesse d'entrée uniforme
(1 m/s par défaut) ; paroi à température imposée ; température transportée comme scalaire
passif T (entrée 0, paroi 1) par la fonction scalarTransport.

Mesures écrites dans postProcessing : pressions moyennes entrée / sortie, température de
mélange en sortie, débit, flux de T à la paroi (intégrale de grad(T)·n), efforts (tube isolé),
moyennes temporelles des champs (instationnaire).

    python creer_cas.py --cas batterie --forme rond --dossier cas/rond
    python creer_cas.py --cas plaques --dossier cas/plaques
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cas_validation import D_TUBE, ECART, L_PLAQUE, maillage_plaques, maillage_tube_isole  # noqa: E402
from geometrie import FORMES  # noqa: E402
from maillage import mailler  # noqa: E402
from polymesh import ecrire_polymesh  # noqa: E402

AIR = dict(nu=1.516e-5, rho=1.204, cp=1006.0, Pr=0.71)
EPAISSEUR_MM = 1.0   # épaisseur de l'extrusion (une maille en z)

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


# ------------------------------------------------------------------ conditions aux limites
def champs(cas: Path, U: float, patchs: dict):
    """patchs : {nom: rôle} avec rôle dans entree, sortie, paroi, cyclic, symmetry."""
    cl = {
        "U": {"entree": f"type fixedValue; value uniform ({U} 0 0);",
              "sortie": "type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0);",
              "paroi": "type noSlip;"},
        "p": {"entree": "type zeroGradient;", "sortie": "type fixedValue; value uniform 0;",
              "paroi": "type zeroGradient;"},
        "T": {"entree": "type fixedValue; value uniform 0;",
              "sortie": "type inletOutlet; inletValue uniform 0; value uniform 0;",
              "paroi": "type fixedValue; value uniform 1;"},
    }
    for nom, (classe, dim, interne) in {"U": ("volVectorField", "[0 1 -1 0 0 0 0]", f"({U} 0 0)"),
                                        "p": ("volScalarField", "[0 2 -2 0 0 0 0]", "0"),
                                        "T": ("volScalarField", "[0 0 0 0 0 0 0]", "0")}.items():
        bf = ""
        for p, role in patchs.items():
            if role in ("cyclic", "symmetry"):
                txt = f"type {role};"
            else:
                txt = cl[nom][role]
            bf += f"    {p}\n    {{\n        {txt}\n    }}\n"
        bf += "    avantArriere\n    {\n        type empty;\n    }\n"
        ecrire(cas, f"0/{nom}", f"dimensions      {dim};\ninternalField   uniform {interne};\n\n"
                                f"boundaryField\n{{\n{bf}}}\n", classe)


# ------------------------------------------------------------------ dictionnaires
def systeme(cas: Path, instationnaire: bool, fin: float, debut_moyenne: float, nproc: int,
            efforts: dict | None, iterations=6000):
    alphaD = 1.0 / AIR["Pr"]
    mesures = f"""
    T
    {{
        type            scalarTransport;
        libs            (solverFunctionObjects);
        field           T;
        alphaD          {alphaD:.6f};
        alphaDt         1.17647;
        writeControl    writeTime;
    }}
    gradT
    {{
        type            grad;
        libs            (fieldFunctionObjects);
        field           T;
        result          gradT;
        writeControl    writeTime;
    }}
    fluxParoi
    {{
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        writeControl    timeStep;
        writeInterval   {1 if instationnaire else 10};
        log             false;
        writeFields     false;
        regionType      patch;
        name            paroi;
        operation       areaNormalIntegrate;
        fields          (gradT);
    }}
    pEntree
    {{
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        writeControl    timeStep;
        writeInterval   {1 if instationnaire else 10};
        log             false;
        writeFields     false;
        regionType      patch;
        name            entree;
        operation       areaAverage;
        fields          (p);
    }}
    pSortie
    {{
        $pEntree;
        name            sortie;
    }}
    TSortie
    {{
        $pEntree;
        name            sortie;
        operation       weightedAreaAverage;
        weightField     phi;
        fields          (T);
    }}
    debit
    {{
        $pEntree;
        operation       sum;
        fields          (phi);
    }}
"""
    if efforts:
        mesures += f"""
    efforts
    {{
        type            forceCoeffs;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   1;
        log             false;
        patches         (paroi);
        rho             rhoInf;
        rhoInf          {AIR['rho']};
        liftDir         (0 1 0);
        dragDir         (1 0 0);
        CofR            (0 0 0);
        pitchAxis       (0 0 1);
        magUInf         {efforts['U']};
        lRef            {efforts['lRef']};
        Aref            {efforts['Aref']};
    }}
"""
    if instationnaire:
        mesures += f"""
    moyennes
    {{
        type            fieldAverage;
        libs            (fieldFunctionObjects);
        timeStart       {debut_moyenne};
        writeControl    writeTime;
        fields
        (
            U {{ mean on; prime2Mean off; base time; }}
            p {{ mean on; prime2Mean off; base time; }}
            T {{ mean on; prime2Mean off; base time; }}
        );
    }}
"""
    if instationnaire:
        temps = f"""application     pimpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         {fin};
deltaT          1e-6;
adjustTimeStep  yes;
maxCo           0.8;
writeControl    adjustable;
writeInterval   {fin / 4:g};
purgeWrite      2;
"""
    else:
        temps = f"""application     simpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         {iterations};
deltaT          1;
writeControl    timeStep;
writeInterval   {iterations};
purgeWrite      1;
"""
    ecrire(cas, "system/controlDict", temps + """writeFormat     binary;
writePrecision  10;
timePrecision   8;
runTimeModifiable false;

functions
{""" + mesures + "}\n")

    div_u = "bounded Gauss linearUpwind grad(U)" if not instationnaire else "Gauss linearUpwind grad(U)"
    div_t = "bounded Gauss linearUpwind grad(T)" if not instationnaire else "Gauss linearUpwind grad(T)"
    ecrire(cas, "system/fvSchemes", f"""ddtSchemes      {{ default {'backward' if instationnaire else 'steadyState'}; }}
gradSchemes     {{ default Gauss linear; }}
divSchemes
{{
    default         none;
    div(phi,U)      {div_u};
    div(phi,T)      {div_t};
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}}
laplacianSchemes {{ default Gauss linear corrected; }}
interpolationSchemes {{ default linear; }}
snGradSchemes   {{ default corrected; }}
""")
    algo = ("""PIMPLE
{
    momentumPredictor   yes;
    nOuterCorrectors    1;
    nCorrectors         2;
    nNonOrthogonalCorrectors 1;
}
""" if instationnaire else """SIMPLE
{
    consistent          yes;
    nNonOrthogonalCorrectors 1;
    residualControl { p 1e-7; U 1e-8; }
}
relaxationFactors { equations { U 0.9; T 0.9; } }
""")
    ecrire(cas, "system/fvSolution", f"""solvers
{{
    p
    {{
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          {0.01 if instationnaire else 0.05};
    }}
    pFinal {{ $p; relTol 0; }}
    "(U|T)"
    {{
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-9;
        relTol          {0 if instationnaire else 0.1};
    }}
    "(U|T)Final" {{ $U; relTol 0; }}
}}

{algo}""")
    ecrire(cas, "system/decomposeParDict", f"numberOfSubdomains {nproc};\nmethod scotch;\n")
    ecrire(cas, "constant/transportProperties", f"transportModel  Newtonian;\nnu              {AIR['nu']};\n")
    ecrire(cas, "constant/turbulenceProperties", "simulationType  laminar;\n")


def allrun(cas: Path, nproc: int, solveur: str):
    par = (f"decomposePar -force > log.decomposePar 2>&1\n"
           f"mpirun -np {nproc} {solveur} -parallel > log.{solveur} 2>&1\n"
           f"reconstructPar > log.reconstructPar 2>&1\n") if nproc > 1 else f"{solveur} > log.{solveur} 2>&1\n"
    (cas / "Allrun").write_text(f"""#!/bin/bash
# Cas généré par outils/cfd_2d/creer_cas.py (OpenFOAM v2606)
cd "$(dirname "$0")" || exit 1
set -e
checkMesh > log.checkMesh 2>&1
{par}""")
    (cas / "Allrun").chmod(0o755)


# ------------------------------------------------------------------ cas
def creer(cas_type: str, dossier: str, forme="rond", U=1.0, nproc=4, fin=None, finesse=1.0, couches=False):
    cas = Path(dossier)
    meta = dict(cas=cas_type, U=U, air=AIR, epaisseur_mm=EPAISSEUR_MM, nproc=nproc)
    if cas_type == "plaques":
        xy, el, bd = maillage_plaques(avec_bords=True)
        roles = {"entree": "entree", "sortie": "sortie", "paroi": "paroi"}
        n = ecrire_polymesh(cas, xy, el, bd, {"entree": "patch", "sortie": "patch", "paroi": "wall"},
                            epaisseur_mm=EPAISSEUR_MM)
        Dh = 2 * ECART * 1e-3
        meta.update(ecart_mm=ECART, longueur_mm=L_PLAQUE, Dh=Dh, Re=U * Dh / AIR["nu"], instationnaire=False)
        champs(cas, U, roles)
        systeme(cas, False, 0, 0, nproc, None)
        allrun(cas, nproc, "simpleFoam")
    elif cas_type == "tube_isole":
        xy, el, bd = maillage_tube_isole(avec_bords=True)
        roles = {"entree": "entree", "sortie": "sortie", "paroi": "paroi", "haut_bas": "symmetry"}
        n = ecrire_polymesh(cas, xy, el, bd, {"entree": "patch", "sortie": "patch", "paroi": "wall",
                                              "haut_bas": "symmetry"}, epaisseur_mm=EPAISSEUR_MM)
        D = D_TUBE * 1e-3
        f_tourb = 0.2 * U / D
        fin = fin or round(0.24 / U + 25 / f_tourb, 3)       # traversée du domaine + ~25 périodes
        debut = round(0.24 / U + 5 / f_tourb, 3)
        meta.update(D=D, Re=U * D / AIR["nu"], instationnaire=True, fin=fin, debut_moyenne=debut)
        champs(cas, U, roles)
        systeme(cas, True, fin, debut, nproc, dict(U=U, lRef=D, Aref=D * EPAISSEUR_MM * 1e-3))
        allrun(cas, nproc, "pimpleFoam")
    elif cas_type == "batterie":
        b, xy, tri, bd = mailler(forme, avec_bords=True, finesse=finesse, couches=couches)
        meta.update(finesse=finesse, couches=couches)
        roles = {"entree": "entree", "sortie": "sortie", "paroi": "paroi", "haut": "cyclic", "bas": "cyclic"}
        n = ecrire_polymesh(cas, xy, tri, bd, {"entree": "patch", "sortie": "patch", "paroi": "wall",
                                               "haut": "cyclic", "bas": "cyclic"},
                            cycliques={"haut": ("bas", (0, -b.Pt)), "bas": ("haut", (0, b.Pt))},
                            epaisseur_mm=EPAISSEUR_MM)
        largeur = (b.exterieur.bounds[3] - b.exterieur.bounds[1]) * 1e-3     # face à l'air
        Umax = U * b.Pt / (b.Pt - largeur * 1e3)
        L_dom = (b.x_domaine[1] - b.x_domaine[0]) * 1e-3
        f_tourb = 0.2 * Umax / largeur
        fin = fin or round(2 * L_dom / U + 25 / f_tourb, 3)
        debut = round(2 * L_dom / U, 3)
        meta.update(forme=forme, nom=b.nom, Pt=b.Pt * 1e-3, Pl=b.Pl * 1e-3, rangs=b.rangs,
                    A_int=b.A_int * 1e-6, P_int=b.P_int * 1e-3, P_ext=b.P_ext * 1e-3,
                    x_noyau=[x * 1e-3 for x in b.x_noyau], x_domaine=[x * 1e-3 for x in b.x_domaine],
                    largeur_frontale=largeur, Umax=Umax, Re_Dext=U * 6e-3 / AIR["nu"],
                    instationnaire=True, fin=fin, debut_moyenne=debut)
        champs(cas, U, roles)
        systeme(cas, True, fin, debut, nproc, None)
        allrun(cas, nproc, "pimpleFoam")
    else:
        raise ValueError(cas_type)
    meta["maillage"] = n
    (cas / "cas.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cas", choices=["plaques", "tube_isole", "batterie"], required=True)
    ap.add_argument("--forme", choices=list(FORMES), default="rond")
    ap.add_argument("--vitesse", type=float, default=1.0, help="vitesse frontale (m/s)")
    ap.add_argument("--nproc", type=int, default=4)
    ap.add_argument("--fin", type=float, default=None, help="temps final (s), instationnaire")
    ap.add_argument("--finesse", type=float, default=1.0, help="divise les tailles de maille (batterie)")
    ap.add_argument("--couches", action="store_true", help="couches de quadrilatères contre les parois")
    ap.add_argument("--dossier", required=True)
    a = ap.parse_args()
    m = creer(a.cas, a.dossier, a.forme, a.vitesse, a.nproc, a.fin, a.finesse, a.couches)
    print(json.dumps({k: m[k] for k in m if k not in ("air",)}, indent=1, ensure_ascii=False))
