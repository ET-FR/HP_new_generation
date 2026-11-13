"""Variante E (12/11/2026) : tube Ø 150 cintré en fer à cheval autour du plénum, modèle 3D sans les plis.

L'échangeur est pour l'instant un faisceau de tubes nus, sans ailettes : les tubes de réfrigérant, disposés en tournesol
(angle d'or) dans la zone d'échange de la coupe (secteur d'anneau), suivent le fer à cheval. Pas de collecteurs
(raccordement de type Murray à faire plus tard) : les tubes s'arrêtent à la plaque arrière, contre la vitre.

Repère : x perpendiculaire à la vitre (0 = vitre, vers la pièce), y le long de la vitre, z vertical (axe du tube à z = 0).
Coupe du tube : u vers l'extérieur du fer à cheval, z vers le haut, angle φ depuis u (0 = extérieur, 90 = haut).

Pièces (docs/formes/cylindre_radial/variante_e/) :
  tubes         tubes de réfrigérant en tournesol
  filtre        manchon filtrant (coque mince)
  plenum        parois latérales du plénum (du haut du tube à la bouche)
  plaque        plaque arrière contre la vitre
  socle         châssis sous tout l'appareil, dessus au point le plus bas du cercle du tube
  ventilateur   axial à axe vertical sous la bouche
  volet         lames du volet dans la bouche

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/echangeur_fer_a_cheval.py').read())"
"""
import json
import math
import os

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
RACINE = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur"
F_PARAM = os.path.join(RACINE, "outils/cad/parametres_fer_a_cheval.json")
SORTIE = os.path.join(RACINE, "docs/formes/cylindre_radial/variante_e")

DEFAUT = {
    "largeur": 400.0,            # mm, hors tout le long de la vitre (choix utilisateur)
    "profondeur": 250.0,         # mm, hors tout dans la pièce (choix utilisateur)
    "hauteur": 200.0,            # mm, hors tout (choix utilisateur)
    "r_tube": 75.0,              # mm, tube Ø 150 (choix utilisateur ; Ø 100 avant)
    "r_cintrage": 100.0,         # mm, rayon de la ligne moyenne dans les cintres
    "r_int_echangeur": 20.0,     # mm, rayon intérieur de la zone d'échange (faisceau de tubes)
    "r_ext_echangeur": 73.0,     # mm, rayon extérieur de la zone d'échange
    "secteur_echangeur_deg": [-90.0, 140.0],   # φ, secteur ouvert à l'air (commence au point le plus bas du cercle)
    "secteur_ouverture_deg": [140.0, 220.0],   # φ, sortie vers le plénum
    "d_tube_refrigerant": 3.0,   # mm, diamètre extérieur des tubes
    "d_int_refrigerant": 2.2,    # mm, diamètre intérieur (volume de propane)
    "n_tubes": 32,               # nombre de tubes de réfrigérant (choix utilisateur)
    "marge_tubes": 3.0,          # mm, distance mini entre un tube et le bord de la zone d'échange
    "r_filtre": 79.0,
    "ep_filtre": 2.0,
    "ep_paroi": 2.0,
    "ep_socle": 15.0,            # mm, socle (châssis) sous le tube : son dessus est au point le plus bas du cercle
    "d_ventilateur": 90.0,
    "z_ventilateur": 75.0,
    "pas_lames": 15.0,
}


def parametres():
    if not os.path.exists(F_PARAM):
        with open(F_PARAM, "w") as f:
            json.dump(DEFAUT, f, indent=2, ensure_ascii=False)
    with open(F_PARAM) as f:
        return dict(DEFAUT, **json.load(f))


def verifie(nom, s):
    print(f"[{nom}] valide {s.isValid()}, solides {len(s.Solids)}, volume {s.Volume / 1e3:.1f} cm³", flush=True)
    return s


def secteur(r0, r1, a0, a1, pas=2.0):
    """Face plane (u, z) d'un secteur d'anneau, dans le plan local XY."""
    n = max(2, int(abs(a1 - a0) / pas))
    ext = [V(r1 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), r1 * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 0) for i in range(n + 1)]
    if r0 <= 0:
        pts = ext + [V(0, 0, 0)]
    else:
        pts = ext + [V(r0 * math.cos(math.radians(a1 - (a1 - a0) * i / n)), r0 * math.sin(math.radians(a1 - (a1 - a0) * i / n)), 0) for i in range(n + 1)]
    return Part.Face(Part.makePolygon(pts + [pts[0]]))


def tubes_nus(centres, p, Xr, Lm, Rk, e0, e1):
    """hA d'un faisceau de tubes nus en écoulement radial vers l'intérieur (ordre de grandeur).
    Vitesse d'approche locale u(r) = Q / (θ r L(r)), vitesse maxi entre tubes u·s/(s − d) avec s l'entraxe local,
    Nu de Zukauskas pour un cylindre en écoulement transverse (40 < Re < 1000 : 0,51 Re^0,5 Pr^0,37 ;
    au-delà : 0,26 Re^0,6 Pr^0,37). Air à 25 °C."""
    d = p["d_tube_refrigerant"] * 1e-3
    nu_air, k_air, pr = 1.56e-5, 0.026, 0.71
    th = math.radians(e1 - e0)
    aire = math.radians(e1 - e0) / 2 * ((p["r_ext_echangeur"] - p["marge_tubes"]) ** 2 - (p["r_int_echangeur"] + p["marge_tubes"]) ** 2)
    s = math.sqrt(aire / len(centres) * 2 / math.sqrt(3)) * 1e-3   # entraxe d'un réseau triangulaire de même densité
    out = {}
    for q in (570, 830):
        Q, hA, hs = q / 3600, 0.0, []
        for u_, z_ in centres:
            r = math.hypot(u_, z_) * 1e-3
            lt = (2 * Xr + Lm + math.pi * (Rk + u_)) * 1e-3
            u = Q / (th * r * (2 * Xr + Lm + math.pi * Rk) * 1e-3)
            um = u * s / (s - d)
            re_ = um * d / nu_air
            nu = (0.51 * re_ ** 0.5 if re_ < 1000 else 0.26 * re_ ** 0.6) * pr ** 0.37
            h = nu * k_air / d
            hs.append(h)
            hA += h * math.pi * d * lt
        out[str(q)] = {"hA_W_K": round(hA), "h_moyen_W_m2K": round(sum(hs) / len(hs))}
    return out


def main():
    p = parametres()
    os.makedirs(SORTIE, exist_ok=True)
    R, Rk = p["r_tube"], p["r_cintrage"]
    Yc = p["largeur"] / 2 - R                 # ligne moyenne des branches
    Xr = p["profondeur"] - R - Rk             # partie droite des branches
    Lm = 2 * (Yc - Rk)                        # fond droit
    ri, re = p["r_int_echangeur"], p["r_ext_echangeur"]
    e0, e1 = p["secteur_echangeur_deg"]
    o0, o1 = p["secteur_ouverture_deg"]
    ep = p["ep_paroi"]
    z_bas = -R - p["ep_socle"]
    z_haut = z_bas + p["hauteur"]
    assert Xr >= 0 and Lm >= 0, "cotes incompatibles"

    # coupe (u, z) au départ de la branche du haut (plan x = 0) : local X → global y, local Y → global z, local Z → global x
    mat = App.Matrix(0, 0, 1, 0,      # x = w
                     1, 0, 0, 0,      # y = u
                     0, 1, 0, 0)      # z = z
    pla = App.Placement(mat)
    pla.Base = V(0, Yc, 0)

    def place(face):
        f = face.copy()
        f.Placement = pla.multiply(f.Placement)
        return f

    def balaye(face_locale):
        """Balaye une coupe le long du fer à cheval : branche, cintre, fond, cintre, branche."""
        s = place(face_locale)
        morceaux = []
        if Xr > 0:
            morceaux.append(s.extrude(V(Xr, 0, 0)))
            s = s.copy(); s.translate(V(Xr, 0, 0))
        c1 = V(Xr, Yc - Rk, 0)
        morceaux.append(s.revolve(c1, V(0, 0, -1), 90))
        s = s.copy(); s.rotate(c1, V(0, 0, -1), 90)
        if Lm > 0:
            morceaux.append(s.extrude(V(0, -Lm, 0)))
            s = s.copy(); s.translate(V(0, -Lm, 0))
        c2 = V(Xr, -(Yc - Rk), 0)
        morceaux.append(s.revolve(c2, V(0, 0, -1), 90))
        s = s.copy(); s.rotate(c2, V(0, 0, -1), 90)
        if Xr > 0:
            morceaux.append(s.extrude(V(-Xr, 0, 0)))
        return Part.makeCompound(morceaux)

    # --- tubes en tournesol dans le secteur d'échangeur ---
    dt = p["d_tube_refrigerant"]
    m = p["marge_tubes"] + dt / 2
    # n tubes exactement : tournesol de Vogel ramené à la zone d'échange (secteur d'anneau, marges comprises).
    # rayon : densité uniforme (r² linéaire entre les bords) ; angle : pas d'or (fraction 0,618…) sur le secteur.
    nt = int(p["n_tubes"])
    r0, r1 = ri + m, re - m
    g = (math.sqrt(5) - 1) / 2
    centres = []
    for k in range(nt):
        r = math.sqrt(r0 ** 2 + (r1 ** 2 - r0 ** 2) * (k + 0.5) / nt)
        ma = math.degrees(m / r)                        # marge angulaire aux bords radiaux du secteur
        aa = e0 + ma + ((k * g) % 1.0) * (e1 - e0 - 2 * ma)
        centres.append((r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa))))
    d_min = min(math.dist(a, b) for i, a in enumerate(centres) for b in centres[i + 1:])
    print(f"tubes : {len(centres)}, entraxe mini {d_min:.2f} mm", flush=True)
    cercles = [Part.Face(Part.Wire(Part.makeCircle(dt / 2, V(u, z, 0)))) for u, z in centres]
    tubes = verifie("tubes", balaye(Part.makeCompound(cercles)))

    # --- filtre, gouttière, parois du plénum ---
    rf, eff = p["r_filtre"], p["ep_filtre"]
    filtre = verifie("filtre", balaye(secteur(rf - eff / 2, rf + eff / 2, e0 + 2, e1 - 2)))
    gout = secteur(R - ep, R, o1, 360 + e0).fuse(secteur(ri, R, o1 - 1.5, o1 + 0.5)).removeSplitter()
    gouttiere = verifie("gouttiere", balaye(gout))
    # paroi du plénum : du bord haut de l'ouverture du tube (φ = o0, r = R) jusqu'à la bouche, à u = −R
    ub, zb = R * math.cos(math.radians(o0)), R * math.sin(math.radians(o0))
    paroi = Part.Face(Part.makePolygon([V(ub, zb, 0), V(-R, zb + 10, 0), V(-R, z_haut, 0), V(-R - ep, z_haut, 0),
                                        V(-R - ep, zb + 10, 0), V(ub - 0.5, zb - 1.5, 0), V(ub, zb, 0)]))
    plenum = verifie("plenum", balaye(paroi))

    # --- plaque arrière, socle (châssis) ---
    plaque = verifie("plaque", Part.makeBox(3, p["largeur"] + 10, z_haut - z_bas, V(-3, -p["largeur"] / 2 - 5, z_bas)))

    def contour(d, pas=3.0):
        """Points (x, y) de la ligne décalée de d, de la vitre en haut à la vitre en bas."""
        r = Rk + d
        pts = [(0, Yc + d), (Xr, Yc + d)]
        na = max(4, int(r * math.pi / 2 / pas))
        pts += [(Xr + r * math.cos(math.radians(90 - 90 * i / na)), Yc - Rk + r * math.sin(math.radians(90 - 90 * i / na))) for i in range(1, na + 1)]
        pts += [(Xr + r, -(Yc - Rk))]
        pts += [(Xr + r * math.cos(math.radians(-90 * i / na)), -(Yc - Rk) + r * math.sin(math.radians(-90 * i / na))) for i in range(1, na + 1)]
        pts += [(0, -Yc - d)]
        return pts
    # socle : s'arrête sous le milieu du tube (ligne moyenne, là où le tube touche le socle), fermé contre la vitre ;
    # dessus à z = −R (point le plus bas du cercle)
    pts = contour(0.0)
    socle = verifie("socle", Part.Face(Part.makePolygon([V(x, y, z_bas) for x, y in pts] + [V(*pts[0], z_bas)])).extrude(V(0, 0, p["ep_socle"])))

    # --- ventilateur axial (axe z) au centre du plénum, sous la bouche ---
    xpl = Xr + Rk - R                         # profondeur du plénum (sur l'axe y = 0)
    xc, dv, zv = xpl / 2, p["d_ventilateur"], p["z_ventilateur"]
    anneau = Part.makeCylinder(dv / 2 + 3, 20, V(xc, 0, zv - 10)).cut(Part.makeCylinder(dv / 2 + 1, 20, V(xc, 0, zv - 10)))
    moyeu = Part.makeCylinder(18, 20, V(xc, 0, zv - 10))
    pales = []
    for j in range(5):
        b = Part.makeBox(dv / 2 - 20, 26, 2, V(17, -13, -1))
        b.rotate(V(0, 0, 0), V(1, 0, 0), 30)
        b.rotate(V(0, 0, 0), V(0, 0, 1), j * 72)
        b.translate(V(xc, 0, zv))
        pales.append(b)
    ventilateur = verifie("ventilateur", Part.makeCompound([anneau, moyeu.fuse(pales)]))

    # --- volet : lames parallèles à la vitre, sur toute la bouche ---
    rcoin = Rk - R
    lames = []
    x = p["pas_lames"] / 2
    while x < xpl - 2:
        ymax = (Yc - R) if x <= Xr else (Yc - Rk) + math.sqrt(max(rcoin ** 2 - (x - Xr) ** 2, 0))
        if ymax > 5:
            lames.append(Part.makeBox(1.5, 2 * ymax - 2, 14, V(x - 0.75, -ymax + 1, z_haut - 16)))
        x += p["pas_lames"]
    volet = verifie("volet", Part.makeCompound(lames))

    # gouttière et bac à condensats retirés pour l'instant (demande du 12/11) ; la gouttière reste construite ci-dessus
    pieces = {"tubes": tubes, "filtre": filtre, "plenum": plenum, "plaque": plaque, "socle": socle, "ventilateur": ventilateur,
              "volet": volet}
    doc = App.newDocument("variante_e")
    for nom, forme in pieces.items():
        o = doc.addObject("Part::Feature", nom)
        o.Shape = forme
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.15, AngularDeflection=0.35).write(os.path.join(SORTIE, f"{nom}.stl"))
    # maillages allégés pour la page web : bloc sans les trous, tubes en facettes grossières
    MeshPart.meshFromShape(Shape=tubes, LinearDeflection=1.0, AngularDeflection=1.0).write(os.path.join(SORTIE, "tubes_web.stl"))
    doc.recompute()
    if os.path.exists(os.path.join(SORTIE, "variante_e.FCStd")):
        os.remove(os.path.join(SORTIE, "variante_e.FCStd"))
    doc.saveAs(os.path.join(SORTIE, "variante_e.FCStd"))
    Part.export(doc.Objects, os.path.join(SORTIE, "variante_e.step"))

    # --- grandeurs ---
    lg = 2 * Xr + math.pi * Rk + Lm           # longueur de la ligne moyenne
    l_tubes = tubes.Volume / (math.pi * dt ** 2 / 4)  # longueur totale de tube
    bb = Part.makeCompound(list(pieces.values())).BoundBox
    # surface frontale (r = re sur le secteur) par Pappus, cintres compris
    da = math.radians(e1 - e0)
    u_moy = re * (math.sin(math.radians(e1)) - math.sin(math.radians(e0))) / da    # u moyen de l'arc extérieur
    s_front = re * da * (2 * Xr + Lm + math.pi * (Rk + u_moy))
    dim = {
        "parametres": p,
        "ligne_moyenne_mm": round(lg, 1),
        "tubes_refrigerant": {"nombre": len(centres), "entraxe_mini_mm": round(d_min, 2),
                              "longueur_totale_m": round(l_tubes * 1e-3, 1),
                              "volume_propane_cm3": round(l_tubes * math.pi * p["d_int_refrigerant"] ** 2 / 4 * 1e-3, 1),
                              "surface_exterieure_m2": round(l_tubes * math.pi * dt * 1e-6, 3)},
        "zone_echange": {"surface_frontale_m2": round(s_front * 1e-6, 4)},
        "tubes_nus": tubes_nus(centres, p, Xr, Lm, Rk, e0, e1),
        "bouche_plenum_mm": [round(xpl, 1), round(2 * (Yc - R), 1)],
        "encombrement_mm": {"x": round(bb.XLength), "y": round(bb.YLength), "z": round(bb.ZLength)},
        "volumes_cm3": {k: round(v.Volume / 1e3, 1) for k, v in pieces.items()},
    }
    with open(os.path.join(SORTIE, "dimensions.json"), "w") as f:
        json.dump(dim, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in dim.items() if k != "parametres"}, indent=1, ensure_ascii=False))


if not globals().get("SANS_MAIN"):
    main()
