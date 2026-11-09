"""
Maillage 2D d'une batterie avec couches de quadrilatères contre les tubes (gmsh, noyau « geo »).

Autour de chaque tube, un anneau structuré (quadrilatères, première maille très fine, croissance
géométrique) ; au-delà, des triangles. Toutes les formes de geometrie.py sont convexes et
symétriques par rapport à l'axe de l'écoulement : chaque contour est coupé en deux chemins
(haut / bas) à ses deux points sur cet axe, et chaque demi-anneau est un quadrangle maillé en
« transfinite ». Les tubes coupés par les bords périodiques (y = 0 et y = Pt) n'ont qu'un
demi-anneau, coupé net sur le bord : le raccordement cyclique reste conforme.

    python maillage_couches.py --forme rond [--finesse 1]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import gmsh
import numpy as np
from shapely.geometry import LineString
from shapely.geometry.polygon import orient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_gmsh import extraire  # noqa: E402
from geometrie import FORMES, batterie  # noqa: E402

# réglages de référence (finesse = 1), en mm
PREMIERE_COUCHE = 0.01
RAISON = 1.15
EPAISSEUR_COUCHES = 0.48
TAILLE_PAROI = 0.08     # taille tangentielle le long des tubes
TAILLE_LOIN = 0.6
TAILLE_TAMPON = 1.0
DIST_TRANSITION = 2.0


def chemins(poly, eps=1e-9):
    """Coupe un contour convexe symétrique (centré sur y = 0) en chemin haut (de droite à gauche)
    et chemin bas (de gauche à droite), avec les deux points exacts sur l'axe."""
    poly = orient(poly, 1)
    axe = poly.exterior.intersection(LineString([(-1e3, 0), (1e3, 0)]))
    xs = sorted(p.x for p in getattr(axe, "geoms", [axe]))
    L, R = (xs[0], 0.0), (xs[-1], 0.0)
    pts = np.asarray(poly.exterior.coords)[:-1]
    ang = np.mod(np.arctan2(pts[:, 1], pts[:, 0]), 2 * math.pi)
    haut = pts[(pts[:, 1] > eps)]
    haut = haut[np.argsort(np.mod(np.arctan2(haut[:, 1], haut[:, 0]), 2 * math.pi))]
    bas = pts[(pts[:, 1] < -eps)]
    bas = bas[np.argsort(np.mod(np.arctan2(bas[:, 1], bas[:, 0]), 2 * math.pi))]
    del ang
    return [R, *map(tuple, haut), L], [L, *map(tuple, bas), R]


def _longueur(p):
    p = np.asarray(p)
    return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))


def mailler_couches(forme: str, finesse=1.0, sortie=None, avec_bords=True, **kw):
    b = batterie(forme, **kw)
    k = 1.0 / finesse
    e1, h_t = PREMIERE_COUCHE * k, TAILLE_PAROI * k
    n_couches = max(3, round(math.log(1 + EPAISSEUR_COUCHES * (RAISON - 1) / e1) / math.log(RAISON)))
    delta = e1 * (RAISON ** n_couches - 1) / (RAISON - 1)
    interieur = b.exterieur                                   # paroi du tube côté air
    exterieur = b.exterieur.buffer(delta, quad_segs=48)       # limite de l'anneau
    ih, ib = chemins(interieur)
    eh, eb = chemins(exterieur)

    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add(f"{forme}_couches")
    g = gmsh.model.geo
    x0, x1, Pt = b.x_domaine[0], b.x_domaine[1], b.Pt
    paroi, haut, bas, anneaux_ext, surfaces_q = [], [], [], [], []

    def spline(pts, cx, cy, sens=1):
        p = pts if sens > 0 else pts[::-1]
        tags = [g.addPoint(cx + x, cy + y, 0) for x, y in p]
        return g.addSpline(tags), tags

    def demi_anneau(cx, cy, chemin_i, chemin_e):
        """chemin_i et chemin_e dans le même sens (droite -> gauche pour le haut, gauche -> droite
        pour le bas). Retourne (courbe intérieure, courbe extérieure, radiale début, radiale fin)."""
        ci, pi = spline(chemin_i, cx, cy)
        ce, pe = spline(chemin_e, cx, cy)
        r0 = g.addLine(pi[0], pe[0])
        r1 = g.addLine(pi[-1], pe[-1])
        n_t = max(8, round(_longueur(chemin_i) / h_t)) + 1
        g.mesh.setTransfiniteCurve(ci, n_t)
        g.mesh.setTransfiniteCurve(ce, n_t)
        for r in (r0, r1):
            g.mesh.setTransfiniteCurve(r, n_couches + 1, "Progression", RAISON)
        boucle = g.addCurveLoop([ci, r1, -ce, -r0])
        s = g.addPlaneSurface([boucle])
        g.mesh.setTransfiniteSurface(s, "Left", [pi[0], pi[-1], pe[-1], pe[0]])
        g.mesh.setRecombine(2, s)
        surfaces_q.append(s)
        paroi.append(ci)
        return ci, ce, r0, r1, pe

    # tubes : rangées pleines (cy = Pt/2) et rangées coupées (cy = 0, répétées en y = Pt)
    trous = []                 # boucles fermées des anneaux pleins
    coupes_bas, coupes_haut = [], []   # (x_gauche_ext, x_droite_ext, courbe ext, radiales, points)
    for cx, cy in b.centres:
        if cy > 0:
            _, ceh, r0h, r1h, peh = demi_anneau(cx, cy, ih, eh)
            _, ceb, r0b, r1b, peb = demi_anneau(cx, cy, ib, eb)
            # les deux demi-anneaux partagent les points sur l'axe : radiales à fusionner
            trous.append((ceh, ceb))
        else:
            # tube coupé en y = 0 : moitié haute ; copie en y = Pt : moitié basse
            _, ce, r0, r1, pe = demi_anneau(cx, 0.0, ih, eh)
            coupes_bas.append((cx + eh[-1][0], cx + eh[0][0], ce, r0, r1, pe))
            _, ce2, r02, r12, pe2 = demi_anneau(cx, Pt, ib, eb)
            coupes_haut.append((cx + eb[0][0], cx + eb[-1][0], ce2, r02, r12, pe2))
    g.synchronize()
    g.removeAllDuplicates()       # fusionne les points / radiales communs aux demi-anneaux
    g.synchronize()

    # contour du domaine d'air triangulé
    def bord_horizontal(y, coupes, montant):
        """Construit le bord y = cte de gauche à droite, en contournant les demi-anneaux coupés.
        Retourne la liste orientée des courbes et les courbes situées sur le bord (pour la
        périodicité), dans l'ordre des x croissants."""
        coupes = sorted(coupes, key=lambda c: c[0])
        courbes, sur_bord = [], []
        x_prec = g.addPoint(x0, y, 0)
        coin_debut = x_prec
        for xg, xd, ce, r0, r1, pe in coupes:
            # points extérieurs de l'anneau sur le bord
            pg, pd = (pe[-1], pe[0]) if not montant else (pe[0], pe[-1])
            l = g.addLine(x_prec, pg); courbes.append(l); sur_bord.append(l)
            courbes.append(ce if montant else -ce)
            x_prec = pd
        p_fin = g.addPoint(x1, y, 0)
        l = g.addLine(x_prec, p_fin); courbes.append(l); sur_bord.append(l)
        return courbes, sur_bord, coin_debut, p_fin

    # bas : y = 0, demi-anneaux hauts ; chemin extérieur eh va de droite à gauche
    cb, sb, pb0, pb1 = bord_horizontal(0.0, coupes_bas, montant=False)
    # haut : y = Pt, demi-anneaux bas ; chemin extérieur eb va de gauche à droite
    ch, sh, ph0, ph1 = bord_horizontal(Pt, coupes_haut, montant=True)
    sortie_c = g.addLine(pb1, ph1)
    entree_c = g.addLine(ph0, pb0)
    boucle = g.addCurveLoop(cb + [sortie_c] + [-c for c in reversed(ch)] + [entree_c])
    boucles_trous = [g.addCurveLoop([ceh, ceb]) for ceh, ceb in trous]
    air_tri = g.addPlaneSurface([boucle] + boucles_trous)
    g.synchronize()
    # radiales sur les bords (font partie de haut / bas)
    for xg, xd, ce, r0, r1, pe in coupes_bas:
        bas += [r0, r1]
    for xg, xd, ce, r0, r1, pe in coupes_haut:
        haut += [r0, r1]
    bas += sb; haut += sh

    cle = lambda c: gmsh.model.getBoundingBox(1, abs(c))[0]
    haut.sort(key=cle); bas.sort(key=cle)
    gmsh.model.mesh.setPeriodic(1, [abs(c) for c in haut], [abs(c) for c in bas],
                                [1, 0, 0, 0, 0, 1, 0, Pt, 0, 0, 1, 0, 0, 0, 0, 1])
    for nom, cs in (("entree", [entree_c]), ("sortie", [sortie_c]), ("haut", haut), ("bas", bas),
                    ("paroi", paroi)):
        gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, [abs(c) for c in cs]), nom)
    gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, surfaces_q + [air_tri]), "air")

    f = gmsh.model.mesh.field
    ext_courbes = [abs(c) for ceh, ceb in trous for c in (ceh, ceb)] + \
                  [abs(c[2]) for c in coupes_bas + coupes_haut]
    d = f.add("Distance"); f.setNumbers(d, "CurvesList", ext_courbes); f.setNumber(d, "Sampling", 400)
    t = f.add("Threshold"); f.setNumber(t, "InField", d)
    f.setNumber(t, "SizeMin", h_t); f.setNumber(t, "SizeMax", TAILLE_LOIN * k)
    f.setNumber(t, "DistMin", 0.0); f.setNumber(t, "DistMax", DIST_TRANSITION)
    bx = f.add("Box"); f.setNumber(bx, "VIn", TAILLE_LOIN * k); f.setNumber(bx, "VOut", TAILLE_TAMPON * k)
    f.setNumber(bx, "XMin", b.x_noyau[0] - 3); f.setNumber(bx, "XMax", b.x_noyau[1] + 6)
    f.setNumber(bx, "YMin", -1); f.setNumber(bx, "YMax", Pt + 1); f.setNumber(bx, "Thickness", 4)
    m = f.add("Min"); f.setNumbers(m, "FieldsList", [t, bx]); f.setAsBackgroundMesh(m)
    for o in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints", "MeshSizeFromCurvature"):
        gmsh.option.setNumber(f"Mesh.{o}", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.model.mesh.generate(2)
    xy, cellules, bords = extraire()
    if sortie:
        gmsh.write(sortie)
    gmsh.finalize()
    b.couches = dict(premiere=e1, raison=RAISON, n=n_couches, epaisseur=delta, tangentielle=h_t)
    return (b, xy, cellules, bords) if avec_bords else (b, xy, cellules)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forme", choices=list(FORMES), default="rond")
    ap.add_argument("--finesse", type=float, default=1.0)
    a = ap.parse_args()
    b, xy, cel, bd = mailler_couches(a.forme, a.finesse)
    nq = sum(len(c) == 4 for c in cel)
    print(f"{a.forme}: {len(cel)} cellules dont {nq} quadrilatères ; couches {b.couches} ;",
          {k: len(v) for k, v in bd.items()})
