"""Échangeur cylindrique à ailette hélicoïdale et arbres de Murray (modèle FreeCAD paramétrique).

Concept (discussion du 10 novembre 2026, docs/biomimetisme.md) :
* axe vertical ; N tubes de propane sur une couronne, parallèles à l'axe ;
* propane : entre en haut au centre, arbre de Murray 1 → 2 → … → N, descend dans les tubes,
  arbre de Murray de regroupement en bas (contre-courant avec l'air) ;
* air : entre en bas tangentiellement, monte en tournant entre les nappes d'une ailette en hélice
  à plusieurs filets (le pas fixe le nombre de tours), sort en haut tangentiellement ;
* noyau central plein (peut loger le moteur du ventilateur), l'air ne passe que dans l'anneau.

Lancement (FreeCAD 1.1 en flatpak, sans interface) :
    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('outils/cad/echangeur_helice.py').read())"
Paramètres : outils/cad/parametres_helice.json (créé avec les valeurs par défaut s'il manque).
Sorties dans docs/formes/helice/ : .FCStd, .step, un .stl par famille de pièces, resume.json.
Les tubes et branches sont modélisés pleins (volume du propane + paroi), pour la visualisation ;
les fusions booléennes pour l'impression sont à faire ensuite.
"""
import json
import math
import os

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
RACINE = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur"
F_PARAM = os.path.join(RACINE, "outils/cad/parametres_helice.json")
SORTIE = os.path.join(RACINE, "docs/formes/helice")

DEFAUT = {
    "r_noyau": 150.0,          # mm, rayon du noyau central (bord intérieur de l'anneau d'air)
    "r_ext": 190.0,            # mm, rayon intérieur de l'enveloppe (bord extérieur de l'anneau)
    "r_tubes": 170.0,          # mm, rayon de la couronne de tubes
    "n_niveaux": 5,            # arbre binaire : 2**n tubes (5 → 32)
    "d_tube": 3.0,             # mm, diamètre extérieur d'un tube
    "d_int_tube": 2.0,         # mm, diamètre intérieur (sert à la loi de Murray et à la charge)
    "hauteur": 80.0,           # mm, hauteur de la zone ailetée
    "tours": 1.0,              # nombre de tours de l'air dans la hauteur
    "filets": 16,              # nombre de nappes hélicoïdales entrelacées
    "ep_ailette": 0.4,         # mm, épaisseur d'ailette
    "plenum": 30.0,            # mm, chambre d'air sous et sur la zone ailetée
    "ep_paroi": 2.0,           # mm, épaisseur de l'enveloppe
    "garde_arbre": 25.0,       # mm, distance entre l'enveloppe et le plan de l'arbre
    "conduit_l": 120.0,        # mm, longueur des conduits d'air tangentiels
    "conduit_larg": 35.0,      # mm, largeur (radiale) des conduits
    "conduit_haut": 26.0,      # mm, hauteur des conduits
}


def parametres():
    if not os.path.exists(F_PARAM):
        with open(F_PARAM, "w") as f:
            json.dump(DEFAUT, f, indent=2)
    with open(F_PARAM) as f:
        p = dict(DEFAUT, **json.load(f))
    return p


def cylindre_entre(a, b, d):
    """Cylindre de diamètre d entre les points a et b."""
    axe = b - a
    return Part.makeCylinder(d / 2, axe.Length, a, axe)


def nappe_helice(p, angle0):
    """Une nappe d'ailette : rectangle radial balayé le long d'une hélice (mode de Frenet)."""
    pas = p["hauteur"] / p["tours"]
    ri, re, e = p["r_noyau"], p["r_ext"], p["ep_ailette"]
    spine = Part.makeHelix(pas, p["hauteur"], ri)
    prof = Part.makePolygon([V(ri, 0, -e / 2), V(re, 0, -e / 2), V(re, 0, e / 2), V(ri, 0, e / 2), V(ri, 0, -e / 2)])
    balayage = Part.Wire(spine).makePipeShell([prof], True, True)
    balayage.rotate(V(0, 0, 0), V(0, 0, 1), angle0)
    return balayage


def arbre_murray(p, z, sens):
    """Arbre binaire radial dans le plan z : centre → 2**n extrémités sur la couronne de tubes.
    Diamètres selon Murray (parent = 2^(1/3) × enfant). sens = +1 : l'entrée part vers le haut."""
    n = p["n_niveaux"]
    d_feuille = p["d_tube"]
    rayons = [p["r_tubes"] * k / n for k in range(n + 1)]
    pieces, longueur_vol = [], 0.0
    noeuds = {(0, 0): V(0, 0, z)}
    for k in range(1, n + 1):
        d = d_feuille * 2 ** ((n - k) / 3)
        d_int = p["d_int_tube"] * 2 ** ((n - k) / 3)
        for j in range(2 ** k):
            th = (j + 0.5) * 2 * math.pi / 2 ** k
            q = V(rayons[k] * math.cos(th), rayons[k] * math.sin(th), z)
            noeuds[(k, j)] = q
            parent = noeuds[(k - 1, j // 2)]
            pieces.append(cylindre_entre(parent, q, d))
            pieces.append(Part.makeSphere(d / 2, q))
            longueur_vol += (q - parent).Length * math.pi * d_int ** 2 / 4
    d_racine = d_feuille * 2 ** (n / 3)
    pieces.append(Part.makeSphere(d_racine / 2, V(0, 0, z)))
    pieces.append(cylindre_entre(V(0, 0, z), V(0, 0, z + sens * 40), d_racine))
    feuilles = [noeuds[(n, j)] for j in range(2 ** n)]
    return pieces, feuilles, longueur_vol, d_racine


def surface_nappe(p):
    """Aire d'une face de nappe (hélicoïde) entre r_noyau et r_ext, pour la hauteur entière."""
    pas = p["hauteur"] / p["tours"]
    c = pas / (2 * math.pi)
    n, s = 400, 0.0
    for i in range(n):
        r = p["r_noyau"] + (i + 0.5) * (p["r_ext"] - p["r_noyau"]) / n
        s += 2 * math.pi * math.sqrt(r * r + c * c) * (p["r_ext"] - p["r_noyau"]) / n
    return s * p["tours"]


def main():
    p = parametres()
    os.makedirs(SORTIE, exist_ok=True)
    doc = App.newDocument("echangeur_helice")
    H, pl = p["hauteur"], p["plenum"]
    z_bas, z_haut = -pl - p["ep_paroi"], H + pl + p["ep_paroi"]

    # Ailette hélicoïdale à plusieurs filets
    nappes = [nappe_helice(p, 360.0 * i / p["filets"]) for i in range(p["filets"])]
    ailette = Part.makeCompound(nappes)

    # Arbres de Murray : distribution en haut (entrée du propane), collecte en bas
    z_ah, z_ab = z_haut + p["garde_arbre"], z_bas - p["garde_arbre"]
    haut, feuilles_h, vol_h, d_racine = arbre_murray(p, z_ah, +1)
    bas, feuilles_b, vol_b, _ = arbre_murray(p, z_ab, -1)

    # Tubes : de l'arbre du haut à celui du bas, à travers l'enveloppe
    tubes = [cylindre_entre(fb, fh, p["d_tube"]) for fh, fb in zip(feuilles_h, feuilles_b)]
    l_tube = z_ah - z_ab

    # Enveloppe (anneau fermé) et noyau
    re, ep = p["r_ext"], p["ep_paroi"]
    paroi = Part.makeCylinder(re + ep, z_haut - z_bas, V(0, 0, z_bas)).cut(
        Part.makeCylinder(re, z_haut - z_bas - 2 * ep, V(0, 0, z_bas + ep)))
    noyau = Part.makeCylinder(p["r_noyau"], z_haut - z_bas, V(0, 0, z_bas))
    # Conduits d'air tangentiels : entrée en bas (sens trigonométrique, comme l'hélice), sortie en haut
    L, w, h = p["conduit_l"], p["conduit_larg"], p["conduit_haut"]
    zc_b = -pl / 2 - h / 2
    entree = Part.makeBox(w, L, h, V(re - w, -L, zc_b))
    sortie = Part.makeBox(w, L, h, V(-re, -L, H + pl / 2 - h / 2))
    enveloppe = paroi.fuse([entree, sortie]).cut(
        Part.makeCylinder(re, z_haut - z_bas - 2 * ep, V(0, 0, z_bas + ep))).removeSplitter()
    # vider les conduits (garder une coque de 1,5 mm)
    for b in (entree, sortie):
        o = b.BoundBox
        creux = Part.makeBox(w - 3, L - 1.5, h - 3, V(o.XMin + 1.5, o.YMin - 0.1, o.ZMin + 1.5))
        enveloppe = enveloppe.cut(creux)

    familles = {
        "ailette": ailette,
        "tubes": Part.makeCompound(tubes),
        "arbre_haut": Part.makeCompound(haut),
        "arbre_bas": Part.makeCompound(bas),
        "enveloppe": enveloppe,
        "noyau": noyau,
    }
    for nom, forme in familles.items():
        obj = doc.addObject("Part::Feature", nom)
        obj.Shape = forme
        m = MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.1, AngularDeflection=0.35)
        m.write(os.path.join(SORTIE, f"{nom}.stl"))
    doc.recompute()
    doc.saveAs(os.path.join(SORTIE, "echangeur_helice.FCStd"))
    Part.export([o for o in doc.Objects], os.path.join(SORTIE, "echangeur_helice.step"))

    # Résumé chiffré
    pas = H / p["tours"]
    ecart = pas / p["filets"] - p["ep_ailette"]
    r_moy = (p["r_noyau"] + p["r_ext"]) / 2
    angle = math.degrees(math.atan(pas / (2 * math.pi * r_moy)))
    s_ail = 2 * p["filets"] * surface_nappe(p) * 1e-6
    n_t = 2 ** p["n_niveaux"]
    s_tubes = n_t * math.pi * p["d_tube"] * H * 1e-6
    anneau = math.pi * (p["r_ext"] ** 2 - p["r_noyau"] ** 2) * 1e-6
    sect_air = anneau * math.sin(math.radians(angle)) * (ecart / (ecart + p["ep_ailette"]))
    vol_tubes = n_t * math.pi * p["d_int_tube"] ** 2 / 4 * l_tube
    resume = {
        "parametres": p,
        "tubes": n_t,
        "pas_helice_mm": round(pas, 2),
        "ecart_entre_nappes_mm": round(ecart, 2),
        "angle_helice_deg": round(angle, 1),
        "surface_ailette_m2": round(s_ail, 3),
        "surface_tubes_m2": round(s_tubes, 4),
        "section_passage_air_m2": round(sect_air, 4),
        "vitesse_air_pour_0.21_m3s": round(0.21 / sect_air, 2),
        "longueur_canal_air_mm": round(H / math.sin(math.radians(angle)), 1),
        "distance_max_tube_bout_ailette_mm": round(max(math.pi * p["r_tubes"] / n_t,
                                                     p["r_ext"] - p["r_tubes"], p["r_tubes"] - p["r_noyau"]), 1),
        "diametre_racine_murray_mm": round(d_racine, 2),
        "volume_interne_cm3": {"tubes": round(vol_tubes / 1000, 2), "arbre_haut": round(vol_h / 1000, 2),
                               "arbre_bas": round(vol_b / 1000, 2)},
        "encombrement_mm": {"diametre": round(2 * (re + ep), 1), "hauteur_totale": round(z_ah - z_ab + 80, 1)},
    }
    with open(os.path.join(SORTIE, "resume.json"), "w") as f:
        json.dump(resume, f, indent=2, ensure_ascii=False)
    print(json.dumps(resume, indent=2, ensure_ascii=False))


main()
