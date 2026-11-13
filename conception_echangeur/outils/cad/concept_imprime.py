"""Concept d'échangeur imprimé en 3D pour la variante F (12/11/2026), tube Ø 150 : tranche de démonstration (vue de coupe).

Idées réunies (discussion du 12/11) :
  - parois d'au moins 1 mm (impression 3D) ;
  - noyau vide jusqu'à r = r_noyau : la zone proche de l'axe coûte beaucoup de perte de charge pour peu d'échange ;
  - nervures radiales porteuses de propane (piste 2) : parois radiales de 1,2 mm qui s'épaississent en profil
    elliptique autour de chaque canal (Ø 2,2 mm, paroi 1 mm), alignées avec l'air ; 8 nervures × 4 canaux = 32 circuits ;
  - lamelles décalées (piste 1) : les lamelles (perpendiculaires à l'axe) sont coupées en couronnes de l_tronçon dans le
    sens de l'air ; d'une couronne à la suivante, elles sont décalées d'un demi-pas le long de l'axe (relance de la
    couche limite) ;
  - plaques intercalaires (piste 3) : près du noyau, une lamelle sur deux est supprimée (le passage double là où l'air
    accélère).

Repère : axe du tube selon y, coupe (x, z) ; φ depuis +x (0 = côté pièce, 90 = haut), secteur d'échange de φ0 à φ1.

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/concept_imprime.py').read())"
"""
import json
import math
import os

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
SORTIE = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/docs/formes/cylindre_radial/variante_f/imprime"

P = {
    "r_ext": 73.0,            # mm, tube Ø 150 (choix utilisateur du 12/11 ; filtre à 77)
    "r_noyau": 35.0,          # mm, noyau vide
    "secteur_deg": [-90.0, 140.0],
    "n_tubes": 32,            # canaux de propane, chacun dans son profil, répartis en tournesol sur le disque
    "d_canal": 2.2,           # mm, diamètre intérieur du canal de propane
    "paroi": 1.0,             # mm, paroi minimale imprimée
    "jeu_profils": 1.5,       # mm, distance mini entre deux profils et entre un profil et le bord de la lamelle
    # stries : bord extérieur des lamelles en dents triangulaires (version « avec stries »)
    "n_dents": 8,
    "largeur_dent": 6.0,      # mm, à la pointe
    "r_creux": 55.0,          # mm, fond des rainures entre dents
    "decalage_x_avec": 180.0, # mm, la version « avec stries » est dessinée à côté
    "profil_long": 11.0,      # mm, longueur (radiale) du profil elliptique autour d'un canal
    "ep_lamelle": 1.0,        # mm
    "jeu": 1.5,               # mm, jeu entre lamelles (dépoudrage)
    "l_troncon": 5.0,         # mm, longueur d'un tronçon de lamelle dans le sens de l'air
    "r_intercalaire": 45.0,   # mm, en dessous : une lamelle sur deux
    "longueur_tranche": 25.0, # mm
    "r_filtre": 77.0,
}


def secteur(r0, r1, a0, a1, pas=2.0):
    n = max(2, int(abs(a1 - a0) / pas))
    pe = [V(r1 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), r1 * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 0) for i in range(n + 1)]
    pi = [V(r0 * math.cos(math.radians(a1 - (a1 - a0) * i / n)), r0 * math.sin(math.radians(a1 - (a1 - a0) * i / n)), 0) for i in range(n + 1)]
    pts = pe + pi
    return Part.Face(Part.makePolygon(pts + [pts[0]]))


def dans_plan_y(face, y0, h):
    """Face du plan (x, z) dessinée dans le plan XY local → extrudée selon +y à partir de y0."""
    f = face.copy()
    f.rotate(V(0, 0, 0), V(1, 0, 0), 90)       # (x, y, 0) → (x, 0, y)
    f.translate(V(0, y0, 0))
    return f.extrude(V(0, h, 0))


def ellipse(cx, cz, a, b, ang, n=36):
    """Ellipse (demi-axes a radial, b tangentiel) tournée de ang degrés, en polygone."""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        u, v = a * math.cos(t), b * math.sin(t)
        pts.append(V(cx + u * c - v * s, cz + u * s + v * c, 0))
    return Part.Face(Part.makePolygon(pts))


def contour_lamelle(stries, rn, re, a0, a1):
    """Face de la lamelle : secteur d'anneau, ou (stries) bord extérieur en dents triangulaires et bord intérieur rond."""
    if not stries:
        return secteur(rn, re, a0, a1, pas=1.0)
    nd, w, rcr = int(P["n_dents"]), P["largeur_dent"], P["r_creux"]
    sommets = []
    for i in range(2 * nd + 1):
        a = math.radians(a0 + i * (a1 - a0) / (2 * nd))
        r = (re - w / 2) if i % 2 == 0 else rcr
        sommets.append(V(r * math.cos(a), r * math.sin(a), 0))
    bande = Part.makePolygon(sommets).makeOffset2D(w / 2, join=0, fill=True, openResult=False)
    u = bande.fuse(secteur(rn, rcr, a0, a1, pas=1.0)).removeSplitter()
    f0 = max(u.Faces, key=lambda f: f.Area)
    return Part.Face(f0.OuterWire)


def placer_profils(lam_face, rn, re, a0, a1, b_prof):
    """32 profils en tournesol dans la lamelle (marge jeu_profils au bord et entre profils)."""
    # profils porteurs de propane : 32, en tournesol sur le disque, orientés dans le sens de l'air (radial) ---
    g = (math.sqrt(5) - 1) / 2
    jp = P["jeu_profils"]
    acceptes = []
    n_vog = int(P["n_tubes"])
    while len(acceptes) < P["n_tubes"] and n_vog < 400:
        acceptes = []
        for k in range(n_vog):
            r = math.sqrt(rn ** 2 + (re ** 2 - rn ** 2) * (k + 0.5) / n_vog)
            a = a0 + ((k * g) % 1.0) * (a1 - a0)
            e = ellipse(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), P["profil_long"] / 2, b_prof, a)
            grand = ellipse(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), P["profil_long"] / 2 + jp, b_prof + jp, a)
            if grand.cut(lam_face).Area > 1e-3:                       # doit tenir dans la lamelle, avec la marge
                continue
            if any(grand.common(o).Area > 1e-6 for _, o, _ in acceptes):
                continue
            acceptes.append((e, e, (r, a)))
            if len(acceptes) == P["n_tubes"]:
                break
        n_vog += 1
    return acceptes


def construire(stries, dx):
    re, rn = P["r_ext"], P["r_noyau"]
    a0, a1 = P["secteur_deg"]
    lt = P["longueur_tranche"]
    y0 = -lt / 2
    rc = P["d_canal"] / 2
    b_prof = rc + P["paroi"]
    lam_face = contour_lamelle(stries, rn, re, a0, a1)

    acceptes = placer_profils(lam_face, rn, re, a0, a1, b_prof)
    profils, canaux = [], []
    for e, _, (r, a) in acceptes:
        trou = Part.Face(Part.Wire(Part.makeCircle(rc, V(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), 0))))
        profils.append(dans_plan_y(e.cut(trou), y0, lt))
        canaux.append(dans_plan_y(trou, y0, lt))
    d_min = min(math.dist((r1 * math.cos(math.radians(b1)), r1 * math.sin(math.radians(b1))),
                          (r2 * math.cos(math.radians(b2)), r2 * math.sin(math.radians(b2))))
                for i_, (_, _, (r1, b1)) in enumerate(acceptes) for (_, _, (r2, b2)) in acceptes[i_ + 1:])

    # --- lamelles décalées : couronnes de l_tronçon (∩ contour), demi-pas de décalage d'une couronne à l'autre ---
    t, jeu, lc = P["ep_lamelle"], P["jeu"], P["l_troncon"]
    pas = t + jeu
    lam, lam_w = [], []
    k = 0
    r_in = rn
    lam_face_w = contour_lamelle(stries, rn, re, a0, a1) if stries else secteur(rn, re, a0, a1, pas=7.0)
    while r_in < re - 0.5:
        r_out = min(r_in + lc, re)
        couronne = secteur(r_in, r_out, a0, a1, pas=1.0).common(lam_face) if stries else secteur(r_in, r_out, a0, a1, pas=2.0)
        couronne_w = couronne if stries else secteur(r_in, r_out, a0, a1, pas=7.0)
        dec = (k % 2) * pas / 2
        i = 0
        while couronne.Area > 1e-3:
            y = y0 + dec + i * pas
            if y + t > y0 + lt:
                break
            if not (r_out <= P["r_intercalaire"] and i % 2 == 1):
                lam.append(dans_plan_y(couronne, y, t))
                lam_w.append(dans_plan_y(couronne_w, y, t))
            i += 1
        r_in = r_out
        k += 1
    rf = P["r_filtre"]
    filtre = dans_plan_y(secteur(rf - 1, rf + 1, a0 + 2, a1 - 2), y0, lt)
    pieces = {"lamelles": Part.makeCompound(lam), "lamelles_web": Part.makeCompound(lam_w), "profils": Part.makeCompound(profils),
              "propane": Part.makeCompound(canaux), "filtre": filtre}
    for s in pieces.values():
        s.translate(V(dx, 0, 0))
    th = math.radians(a1 - a0)
    contour = lam_face.OuterWire.Length - rn * th - 2 * (re - rn)     # bord extérieur (entrée de l'air)
    info = {"stries": stries, "tubes": len(acceptes), "entraxe_mini_mm": round(d_min, 1),
            "surface_lamelle_cm2": round(lam_face.Area / 100, 1), "contour_entree_mm": round(contour, 1),
            "lamelles_dans_la_tranche": len(lam), "pas_lamelles": pas}
    return pieces, info


def main():
    os.makedirs(SORTIE, exist_ok=True)
    infos = {}
    tout = []
    for cle, stries, dx in (("sans", False, 0.0), ("avec", True, P["decalage_x_avec"])):
        pieces, info = construire(stries, dx)
        infos[cle] = info
        for nom, forme in pieces.items():
            print(f"[{cle} {nom}] valide {forme.isValid()}, solides {len(forme.Solids)}", flush=True)
            fin = nom == "lamelles_web"
            MeshPart.meshFromShape(Shape=forme, LinearDeflection=1.0 if fin else 0.3, AngularDeflection=1.0 if fin else 0.6).write(
                os.path.join(SORTIE, f"imp_{cle}_{nom}.stl"))
            if not fin:
                tout.append(forme)
        print(cle, info, flush=True)
    Part.makeCompound(tout).exportStep(os.path.join(SORTIE, "concept_imprime.step"))
    with open(os.path.join(SORTIE, "dimensions.json"), "w") as f:
        json.dump(dict(P, versions=infos), f, indent=2, ensure_ascii=False)


if not globals().get("SANS_MAIN"):
    main()
