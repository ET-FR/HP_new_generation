"""Échangeur cylindrique à flux radial, variante A′ (choix du 12/11/2026) : modèle 3D sans les tubes de réfrigérant.

Cylindre couché Ø 200 × 400 mm. L'air est aspiré à travers un manchon filtrant puis une galette d'échangeur
plissée en étoile (secteur de 280°), se rassemble dans la chambre centrale vide, passe la gorge (secteur libre de
80° à gauche) et la volute qui remonte au-dessus du cylindre ; les ventilateurs, juste avant la bouche, le rejettent
vers l'avant. Même géométrie que la coupe A′ de docs/formes/cylindre_radial/croquis_2d.html.

Pièces (docs/formes/cylindre_radial/) :
  galette      échangeur plissé (bloc plein de l'épaisseur de la galette ; tubes et ailettes non dessinés)
  filtre       manchon filtrant (coque mince)
  cloisons     deux parois qui ferment les bouts de la galette au bord de la gorge
  volute       parois intérieure et extérieure de la volute
  flasques     plaques de bout (cylindre + volute)
  ventilateurs panneau, moyeux et pales (ventilateurs axiaux de principe)
(le domaine d'air pour la CFD sera construit avec le cas de calcul : il doit inclure les plis et l'extérieur)

Repère : axe du cylindre selon y (0 → longueur), z vertical vers le haut, x vers la bouche (droite de la coupe).

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/echangeur_radial.py').read())"
"""
import json
import math
import os

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
RACINE = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur"
F_PARAM = os.path.join(RACINE, "outils/cad/parametres_radial.json")
SORTIE = os.path.join(RACINE, "docs/formes/cylindre_radial")

DEFAUT = {
    "longueur": 400.0,           # mm, longueur du cylindre (choix utilisateur : Ø 200 × 400)
    "r_ext": 100.0,              # mm, rayon extérieur de la zone plissée
    "r_int": 65.0,               # mm, rayon de la chambre (plis de 35 mm)
    "ep_galette": 8.0,           # mm, épaisseur de la galette d'échangeur (profondeur traversée par l'air)
    "pas_pli_deg": 12.0,         # un pli complet tous les 12°
    "secteur_gorge_deg": [140.0, 220.0],   # secteur sans échangeur, ouvert vers la volute
    "r_filtre": 108.0,           # mm, rayon moyen du manchon filtrant
    "ep_filtre": 3.0,            # mm
    "ep_paroi": 2.0,             # mm, volute et cloisons
    "ep_flasque": 3.0,           # mm
    "volute_y_int": 150.0,       # mm, paroi intérieure de la volute au-dessus de l'axe (partie droite)
    "volute_h_bouche": 170.0,    # mm, hauteur de la bouche
    "x_bouche": 95.0,            # mm, position de la bouche
    "n_ventilateurs": 2,         # ventilateurs axiaux de principe, côte à côte le long de l'axe
    "d_ventilateur": 160.0,      # mm
    "x_ventilateur": 34.0,       # mm, plan du panneau des ventilateurs
}


def parametres():
    if not os.path.exists(F_PARAM):
        with open(F_PARAM, "w") as f:
            json.dump(DEFAUT, f, indent=2, ensure_ascii=False)
    with open(F_PARAM) as f:
        return dict(DEFAUT, **json.load(f))


def pol(r, a):
    a = math.radians(a)
    return V(r * math.cos(a), r * math.sin(a), 0)


def epaissir(fil, ep, L):
    """Ligne ouverte du plan de coupe → bande d'épaisseur ep (bouts arrondis) → prisme de longueur L."""
    face = fil.makeOffset2D(ep / 2, join=0, fill=True, openResult=False)
    return face.extrude(V(0, 0, L))


def bezier(poles):
    b = Part.BezierCurve()
    b.setPoles(poles)
    return b.toShape()


def verifie(nom, s):
    print(f"[{nom}] valide {s.isValid()}, solides {len(s.Solids)}, volume {s.Volume / 1e3:.1f} cm³", flush=True)
    return s


def main():
    p = parametres()
    os.makedirs(SORTIE, exist_ok=True)
    L, Re, Ri, eg = p["longueur"], p["r_ext"], p["r_int"], p["ep_galette"]
    g0, g1 = p["secteur_gorge_deg"]
    ep, ef = p["ep_paroi"], p["ep_flasque"]
    yi, hb, xb = p["volute_y_int"], p["volute_h_bouche"], p["x_bouche"]
    yh = yi + hb

    # --- galette plissée : ligne médiane en zigzag, sommets à Re − eg/2 et Ri + eg/2, de g1 à g0 + 360 ---
    a0, a1 = g1, g0 + 360
    n = int(round((a1 - a0) / (p["pas_pli_deg"] / 2)))
    sommets = [pol(Re - eg / 2 if i % 2 == 0 else Ri + eg / 2, a0 + i * (a1 - a0) / n) for i in range(n + 1)]
    galette = verifie("galette", epaissir(Part.makePolygon(sommets), eg, L))
    long_dev = sum((sommets[i + 1] - sommets[i]).Length for i in range(n))

    # --- cloisons : ferment les bouts de la galette au bord de la gorge (de Ri à Re) ---
    cl = []
    for a in (g0, g1):
        c = Part.makeBox(Re + 1 - Ri, ep, L, V(Ri, -ep / 2, 0))
        c.rotate(V(0, 0, 0), V(0, 0, 1), a)
        cl.append(c)
    cloisons = Part.makeCompound(cl)
    verifie("cloisons", cloisons)

    # --- manchon filtrant : coque r_filtre ± ep/2 sur le secteur d'aspiration (marge de 3° aux bords) ---
    rf, eff = p["r_filtre"], p["ep_filtre"]
    ang = (g0 + 360 - 3) - (g1 + 3)
    fil = Part.makeCylinder(rf + eff / 2, L, V(0, 0, 0), V(0, 0, 1), ang).cut(
        Part.makeCylinder(rf - eff / 2, L, V(0, 0, 0), V(0, 0, 1), ang))
    fil.rotate(V(0, 0, 0), V(0, 0, 1), g1 + 3)
    filtre = verifie("filtre", fil)

    # --- volute : mêmes courbes que le croquis (Bézier), du bord de la gorge à la bouche ---
    o0, i0 = pol(Re, g1), pol(Re, g0)
    ext = Part.Wire([bezier([o0, V(-190, -75, 0), V(-235, 170, 0), V(-130, 275, 0)]),
                     bezier([V(-130, 275, 0), V(-95, yh, 0), V(-20, yh, 0)]),
                     Part.LineSegment(V(-20, yh, 0), V(xb, yh, 0)).toShape()])
    intr = Part.Wire([bezier([i0, V(-100, 110, 0), V(-95, yi, 0), V(-35, yi, 0)]),
                      Part.LineSegment(V(-35, yi, 0), V(xb, yi, 0)).toShape()])
    volute = verifie("volute", Part.makeCompound([epaissir(ext, ep, L), epaissir(intr, ep, L)]))

    # --- flasques : disque (cylindre + filtre) ∪ section intérieure de la volute, aux deux bouts ---
    pts_e = ext.discretize(Distance=3.0)
    pts_i = intr.discretize(Distance=3.0)
    contour = pts_e + [V(xb, yi, 0)] + list(reversed(pts_i)) + [pts_e[0]]
    sec_volute = Part.Face(Part.makePolygon(contour))
    disque = Part.Face(Part.Wire(Part.makeCircle(rf + eff / 2 + 2, V(0, 0, 0))))
    plaque = disque.fuse(sec_volute).removeSplitter()
    fl = []
    for z0 in (-ef, L):
        f = plaque.extrude(V(0, 0, ef))
        if len(f.Solids) > 1:
            f = f.Solids[0].fuse(f.Solids[1:]).removeSplitter()
        f.translate(V(0, 0, z0))
        fl.append(f)
    flasques = verifie("flasques", Part.makeCompound(fl))

    # --- ventilateurs axiaux de principe : panneau percé + moyeu + 5 pales, axe selon x, dans la partie droite ---
    nv, dv, xv = int(p["n_ventilateurs"]), p["d_ventilateur"], p["x_ventilateur"]
    zc = (yi + yh) / 2
    panneau = Part.makeBox(4, hb, L, V(xv - 2, yi, 0))
    rot = []
    for k in range(nv):
        c = (k + 0.5) * L / nv
        panneau = panneau.cut(Part.makeCylinder(dv / 2, 10, V(xv - 5, zc, c), V(1, 0, 0)))
        moyeu = Part.makeCylinder(25, 22, V(xv - 11, zc, c), V(1, 0, 0))
        pales = []
        for j in range(5):
            b = Part.makeBox(2, dv / 2 - 30, 38, V(-1, 27, -19))     # pale à plat, rayon selon y local
            b.rotate(V(0, 0, 0), V(0, 1, 0), 35)                     # calage
            b.rotate(V(0, 0, 0), V(1, 0, 0), j * 72)                 # répartition autour de l'axe
            b.translate(V(xv, zc, c))
            pales.append(b)
        rot.append(moyeu.fuse(pales))
    ventilateurs = verifie("ventilateurs", Part.makeCompound([panneau] + rot))

    pieces = {"galette": galette, "filtre": filtre, "cloisons": cloisons, "volute": volute, "flasques": flasques,
              "ventilateurs": ventilateurs}
    # cylindre couché : axe de la coupe (z) → y, y de la coupe → z (vertical)
    for s in pieces.values():
        s.rotate(V(0, 0, 0), V(1, 0, 0), 90)       # (x, y, z) → (x, −z, y)
        s.translate(V(0, L, 0))                    # axe de 0 à L en y
    doc = App.newDocument("echangeur_radial")
    for nom, forme in pieces.items():
        o = doc.addObject("Part::Feature", nom)
        o.Shape = forme
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.1, AngularDeflection=0.3).write(os.path.join(SORTIE, f"{nom}.stl"))
    doc.recompute()
    doc.saveAs(os.path.join(SORTIE, "echangeur_radial.FCStd"))
    Part.export(doc.Objects, os.path.join(SORTIE, "echangeur_radial.step"))

    sect = a1 - a0
    dim = {
        "parametres": p,
        "galette": {"plis": n // 2, "longueur_developpee_mm": round(long_dev, 1),
                    "surface_frontale_m2": round(long_dev * L * 1e-6, 4),
                    "surface_enveloppe_m2": round(2 * math.pi * Re * sect / 360 * L * 1e-6, 4),
                    "volume_dm3": round(galette.Volume * 1e-6, 2)},
        "filtre_surface_m2": round(2 * math.pi * rf * ang / 360 * L * 1e-6, 4),
        "gorge_mm": round((pol(Re, g0) - pol(Re, g1)).Length, 1),
        "bouche_mm": [L, hb],
        "encombrement_mm": {k: round(v, 0) for k, v in zip(
            ("x", "y", "z"), (doc.getObject("flasques").Shape.BoundBox.XLength,
                              doc.getObject("flasques").Shape.BoundBox.YLength,
                              doc.getObject("flasques").Shape.BoundBox.ZLength))},
        "volumes_cm3": {k: round(v.Volume / 1e3, 1) for k, v in pieces.items()},
    }
    with open(os.path.join(SORTIE, "dimensions.json"), "w") as f:
        json.dump(dim, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in dim.items() if k != "parametres"}, indent=1, ensure_ascii=False))


if not globals().get("SANS_MAIN"):
    main()
