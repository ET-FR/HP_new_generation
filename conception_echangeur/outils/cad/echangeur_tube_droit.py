"""Variante F (12/11/2026) : comme la variante E, mais un seul tube droit couché le long de la vitre (au lieu du fer à
cheval) ; l'air sort vers le haut. C'est un peu la variante A′ avec un flux vertical.

Le tube Ø 150 est parallèle à la vitre. L'air de la pièce entre radialement (côté pièce, dessus, dessous), traverse le
faisceau de tubes de réfrigérant (tubes nus en tournesol, ni plis ni ailettes pour l'instant), ressort par la face du tube
tournée vers la vitre dans un plénum, entre le tube et la vitre, et monte : ventilateurs axiaux à axe vertical, bouche sur
tout le dessus du plénum, volet à lames.

Repère : x perpendiculaire à la vitre (0 = vitre, vers la pièce), y le long de la vitre (axe du tube), z vertical (axe du
tube à z = 0). Coupe du tube : angle φ depuis +x (0 = côté pièce, 90 = haut, 180 = côté vitre).

Pièces (docs/formes/cylindre_radial/variante_f/) :
  tubes         tubes de réfrigérant en tournesol (droits, le long du tube)
  filtre        manchon filtrant (coque mince) sur le secteur d'échange
  plenum        paroi du plénum, du haut de l'ouverture du tube jusqu'à la bouche
  flasques      plaques de bout (tube + plénum)
  plaque        plaque arrière contre la vitre
  socle         châssis : dessus au point le plus bas du cercle, s'arrête sous le milieu du tube
  ventilateurs  axiaux à axe vertical dans le plénum
  volet         lames du volet dans la bouche

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/echangeur_tube_droit.py').read())"
"""
import json
import math
import os

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
RACINE = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur"
F_PARAM = os.path.join(RACINE, "outils/cad/parametres_tube_droit.json")
SORTIE = os.path.join(RACINE, "docs/formes/cylindre_radial/variante_f")

DEFAUT = {
    "largeur": 400.0,            # mm, hors tout le long de la vitre (flasques comprises)
    "profondeur": 250.0,         # mm, hors tout dans la pièce
    "hauteur": 200.0,            # mm, hors tout
    "r_tube": 75.0,              # mm, tube Ø 150
    "r_int_echangeur": 20.0,     # mm, rayon intérieur de la zone d'échange (faisceau de tubes)
    "r_ext_echangeur": 73.0,     # mm, rayon extérieur de la zone d'échange
    "secteur_echangeur_deg": [-90.0, 140.0],   # φ : du point le plus bas du cercle jusqu'au haut côté vitre
    "secteur_ouverture_deg": [140.0, 220.0],   # φ : sortie vers le plénum (côté vitre)
    "n_tubes": 32,
    "d_tube_refrigerant": 3.0,
    "d_int_refrigerant": 2.2,
    "marge_tubes": 3.0,
    "r_filtre": 79.0,
    "ep_filtre": 2.0,
    "ep_paroi": 2.0,
    "ep_flasque": 3.0,
    "ep_socle": 15.0,            # mm, dessus du socle au point le plus bas du cercle
    "n_ventilateurs": 3,
    "d_ventilateur": 90.0,
    "z_ventilateur": 75.0,
    "pas_lames": 15.0,
    "ep_lamelle": 0.12,          # mm, lamelles d'aluminium (dimensionnement du 12/11 : ≈ 560 W/K, ≈ 40 Pa à 830 m³/h)
    "pas_lamelles": 1.2,         # mm (≈ 21 ailettes par pouce)
    "longueur_tranche": 24.0,    # mm, tranche dessinée avec ses lamelles (vue de coupe)
    # tranche plissée (12/11, corrigée) : lamelle pleine, bord extérieur en zigzag, bord intérieur rond, tubes en tournesol
    "n_plis": 8,                 # dents du zigzag extérieur
    "ep_galette_plis": 6.0,      # mm, largeur d'une dent
    "r_creux_plis": 45.0,        # mm, fond des rainures entre dents
    "r_int_plis": 25.0,          # mm, bord intérieur rond de la lamelle
    "ep_lamelle_plis": 0.10,
    "pas_lamelles_plis": 1.0,
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


def tournesol(n, r0, r1, a0, a1, m):
    """n points en tournesol (Vogel) dans un secteur d'anneau : densité uniforme, pas d'or sur le secteur."""
    g = (math.sqrt(5) - 1) / 2
    pts = []
    for k in range(n):
        r = math.sqrt(r0 ** 2 + (r1 ** 2 - r0 ** 2) * (k + 0.5) / n)
        ma = math.degrees(m / r)
        a = a0 + ma + ((k * g) % 1.0) * (a1 - a0 - 2 * ma)
        pts.append((r * math.cos(math.radians(a)), r * math.sin(math.radians(a))))
    return pts


def main():
    p = parametres()
    os.makedirs(SORTIE, exist_ok=True)
    R, ef, ep = p["r_tube"], p["ep_flasque"], p["ep_paroi"]
    W = p["largeur"]
    L = W - 2 * ef                           # longueur du tube entre flasques
    y0 = -L / 2
    xt = p["profondeur"] - R                 # axe du tube
    ri, re = p["r_int_echangeur"], p["r_ext_echangeur"]
    e0, e1 = p["secteur_echangeur_deg"]
    o0, o1 = p["secteur_ouverture_deg"]
    z_bas = -R - p["ep_socle"]
    z_haut = z_bas + p["hauteur"]
    xo = xt + R * math.cos(math.radians(o0))  # bord haut de l'ouverture vers le plénum
    zo = R * math.sin(math.radians(o0))
    xpl = xt - R                              # paroi du plénum (verticale) côté tube
    assert xpl > 20, "plénum trop étroit"

    def coupe_xz(face2d):
        """Face dans le plan local (x, z) → plan y = y0, prête à extruder selon +y."""
        f = face2d.copy()
        f.rotate(V(0, 0, 0), V(1, 0, 0), 90)     # (x, y, 0) → (x, 0, y)
        f.translate(V(0, y0, 0))
        return f

    def secteur(r0, r1, a0, a1, pas=2.0):
        n = max(2, int(abs(a1 - a0) / pas))
        pe = [V(xt + r1 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), r1 * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 0) for i in range(n + 1)]
        pi = [V(xt + r0 * math.cos(math.radians(a1 - (a1 - a0) * i / n)), r0 * math.sin(math.radians(a1 - (a1 - a0) * i / n)), 0) for i in range(n + 1)]
        pts = pe + pi
        return Part.Face(Part.makePolygon(pts + [pts[0]]))

    # --- tubes de réfrigérant (droits) ---
    dt = p["d_tube_refrigerant"]
    m = p["marge_tubes"] + dt / 2
    centres = tournesol(int(p["n_tubes"]), ri + m, re - m, e0, e1, m)
    d_min = min(math.dist(a, b) for i, a in enumerate(centres) for b in centres[i + 1:])
    print(f"tubes : {len(centres)}, entraxe mini {d_min:.2f} mm", flush=True)
    cercles = Part.makeCompound([Part.Face(Part.Wire(Part.makeCircle(dt / 2, V(xt + u, z, 0)))) for u, z in centres])
    tubes = verifie("tubes", coupe_xz(cercles).extrude(V(0, L, 0)))

    # --- filtre ---
    rf, eff = p["r_filtre"], p["ep_filtre"]
    filtre = verifie("filtre", coupe_xz(secteur(rf - eff / 2, rf + eff / 2, e0 + 2, e1 - 2)).extrude(V(0, L, 0)))

    # --- paroi du plénum : du bord haut de l'ouverture du tube jusqu'à la bouche, verticale à x = xpl ---
    paroi = Part.Face(Part.makePolygon([V(xo, zo, 0), V(xpl, zo + 10, 0), V(xpl, z_haut, 0), V(xpl - ep, z_haut, 0),
                                        V(xpl - ep, zo + 10, 0), V(xo - 0.5, zo - 1.5, 0), V(xo, zo, 0)]))
    plenum = verifie("plenum", coupe_xz(paroi).extrude(V(0, L, 0)))

    # --- flasques : disque du tube (filtre compris) ∪ section du plénum, aux deux bouts ---
    disque = Part.Face(Part.Wire(Part.makeCircle(rf + eff / 2 + 1, V(xt, 0, 0))))
    rect = Part.Face(Part.makePolygon([V(0, z_bas + p["ep_socle"], 0), V(xt, z_bas + p["ep_socle"], 0), V(xt, zo + 10, 0),
                                       V(xpl, zo + 10, 0), V(xpl, z_haut, 0), V(0, z_haut, 0), V(0, z_bas + p["ep_socle"], 0)]))
    plaque_bout = disque.fuse(rect).removeSplitter()
    fl = []
    for yb in (y0 - ef, y0 + L):
        f = plaque_bout.copy()
        f.rotate(V(0, 0, 0), V(1, 0, 0), 90)
        f = f.extrude(V(0, ef, 0))
        f.translate(V(0, yb, 0))
        fl.append(f)
    flasques = verifie("flasques", Part.makeCompound(fl))

    # --- plaque arrière, socle (jusqu'au milieu du tube, dessus à z = −R) ---
    plaque = verifie("plaque", Part.makeBox(3, W, z_haut - z_bas, V(-3, -W / 2, z_bas)))
    socle = verifie("socle", Part.makeBox(xt, W, p["ep_socle"], V(0, -W / 2, z_bas)))

    # --- ventilateurs axiaux (axe z) dans le plénum, côte à côte le long de y ---
    nv, dv, zv = int(p["n_ventilateurs"]), p["d_ventilateur"], p["z_ventilateur"]
    xc = xpl / 2
    rot = []
    for k in range(nv):
        yc = y0 + (k + 0.5) * L / nv
        anneau = Part.makeCylinder(dv / 2 + 3, 15, V(xc, yc, zv - 7.5)).cut(Part.makeCylinder(dv / 2 + 1, 15, V(xc, yc, zv - 7.5)))
        moyeu = Part.makeCylinder(14, 15, V(xc, yc, zv - 7.5))
        pales = []
        for j in range(5):
            b = Part.makeBox(dv / 2 - 15, 20, 2, V(13, -10, -1))
            b.rotate(V(0, 0, 0), V(1, 0, 0), 30)
            b.rotate(V(0, 0, 0), V(0, 0, 1), j * 72)
            b.translate(V(xc, yc, zv))
            pales.append(b)
        rot += [anneau, moyeu.fuse(pales)]
    ventilateurs = verifie("ventilateurs", Part.makeCompound(rot))

    # --- volet : lames parallèles à la vitre sur toute la bouche ---
    lames = []
    x = p["pas_lames"] / 2
    while x < xpl - ep - 2:
        lames.append(Part.makeBox(1.5, L - 2, 12, V(x - 0.75, y0 + 1, z_haut - 14)))
        x += p["pas_lames"]
    volet = verifie("volet", Part.makeCompound(lames))

    # --- tranche de démonstration avec les lamelles (vue de coupe) ---
    lt, el, pl_ = p["longueur_tranche"], p["ep_lamelle"], p["pas_lamelles"]
    yt0 = -lt / 2

    def tranche(face2d, ya, h):
        f = face2d.copy()
        f.rotate(V(0, 0, 0), V(1, 0, 0), 90)
        f.translate(V(0, ya, 0))
        return f.extrude(V(0, h, 0))
    lam = secteur(ri, re, e0, e1, pas=1.0)
    for c in cercles.Faces:
        lam = lam.cut(c)
    n_lam = int(lt / pl_)
    t_pieces = {
        "tranche_lamelles": Part.makeCompound([tranche(lam, yt0 + (i + 0.5) * pl_ - el / 2, el) for i in range(n_lam)]),
        "tranche_tubes": tranche(cercles, yt0, lt),
        "tranche_filtre": tranche(secteur(rf - eff / 2, rf + eff / 2, e0 + 2, e1 - 2), yt0, lt),
        "tranche_plenum": tranche(paroi, yt0, lt),
        "tranche_socle": Part.makeBox(xt, lt, p["ep_socle"], V(0, yt0, z_bas)),
        "tranche_plaque": Part.makeBox(3, lt, z_haut - z_bas, V(-3, yt0, z_bas)),
    }
    for nom, forme in t_pieces.items():
        verifie(nom, forme)
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.3, AngularDeflection=0.6).write(os.path.join(SORTIE, f"{nom}.stl"))
    Part.makeCompound(list(t_pieces.values())).exportStep(os.path.join(SORTIE, "tranche_lamelles.step"))
    # lamelles allégées pour la page web : contour à 5°, trous en dodécagones
    lam_w = secteur(ri, re, e0, e1, pas=5.0)
    for u, z in centres:
        lam_w = lam_w.cut(Part.Face(Part.makePolygon([V(xt + u + dt / 2 * math.cos(math.radians(30 * j)), z + dt / 2 * math.sin(math.radians(30 * j)), 0)
                                                      for j in range(13)])))
    MeshPart.meshFromShape(Shape=Part.makeCompound([tranche(lam_w, yt0 + (i + 0.5) * pl_ - el / 2, el) for i in range(n_lam)]),
                           LinearDeflection=1.0, AngularDeflection=1.0).write(os.path.join(SORTIE, "tranche_lamelles_web.stl"))

    # --- tranche plissée : lamelle pleine, bord extérieur en zigzag (dents et rainures où l'air entre), bord intérieur rond ;
    #     tubes en tournesol sur toute la lamelle (dents et anneau) ---
    npl, eg, rip, rcr = int(p["n_plis"]), p["ep_galette_plis"], p["r_int_plis"], p["r_creux_plis"]
    elp, plp = p["ep_lamelle_plis"], p["pas_lamelles_plis"]
    sommets = []
    for i in range(2 * npl + 1):
        a = math.radians(e0 + i * (e1 - e0) / (2 * npl))
        r = (re - eg / 2) if i % 2 == 0 else rcr
        sommets.append(V(xt + r * math.cos(a), r * math.sin(a), 0))
    bande = Part.makePolygon(sommets).makeOffset2D(eg / 2, join=0, fill=True, openResult=False)
    anneau = secteur(rip, rcr, e0, e1, pas=1.0)
    union = bande.fuse(anneau).removeSplitter()
    f0 = union.Faces[0] if len(union.Faces) == 1 else max(union.Faces, key=lambda f: f.Area)
    lam_p = Part.Face(f0.OuterWire)                     # bouche les poches fermées entre dents
    # tubes : tournesol de Vogel sur le secteur d'anneau rip → re, gardés s'ils sont dans la lamelle avec une marge
    marge_p = dt / 2 + 1.5

    def candidats(n):
        g = (math.sqrt(5) - 1) / 2
        out = []
        for k in range(n):
            r = math.sqrt(rip ** 2 + (re ** 2 - rip ** 2) * (k + 0.5) / n)
            a = e0 + ((k * g) % 1.0) * (e1 - e0)
            q = V(xt + r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), 0)
            if lam_p.isInside(q, 0.01, True) and Part.Vertex(q).distToShape(lam_p.OuterWire)[0] >= marge_p:
                out.append(q)
        return out
    nt_p = int(p["n_tubes"])
    nvog = nt_p
    centres_p = candidats(nvog)
    while len(centres_p) < nt_p:
        nvog += 1
        centres_p = candidats(nvog)
    centres_p = centres_p[:nt_p]
    d_min_p = min((a - b).Length for k, a in enumerate(centres_p) for b in centres_p[k + 1:])
    trous = [Part.Face(Part.Wire(Part.makeCircle(dt / 2, q))) for q in centres_p]
    lam_w = lam_p.copy()
    for c in trous:
        lam_p = lam_p.cut(c)
    for q in centres_p:
        lam_w = lam_w.cut(Part.Face(Part.makePolygon([q + V(dt / 2 * math.cos(math.radians(30 * j)), dt / 2 * math.sin(math.radians(30 * j)), 0)
                                                      for j in range(13)])))
    n_lp = int(lt / plp)
    # contour d'entrée de l'air : bord extérieur en zigzag (contour total moins l'arc intérieur et les deux bords de bout)
    th_ = math.radians(e1 - e0)
    contour_ext = f0.OuterWire.Length - rip * th_ - 2 * (re - rip)
    p_pieces = {
        "plis_lamelles": Part.makeCompound([tranche(lam_p, yt0 + (i + 0.5) * plp - elp / 2, elp) for i in range(n_lp)]),
        "plis_tubes": tranche(Part.makeCompound(trous), yt0, lt),
        "plis_filtre": t_pieces["tranche_filtre"], "plis_plenum": t_pieces["tranche_plenum"],
        "plis_socle": t_pieces["tranche_socle"], "plis_plaque": t_pieces["tranche_plaque"],
    }
    for nom, forme in p_pieces.items():
        verifie(nom, forme)
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.3, AngularDeflection=0.6).write(os.path.join(SORTIE, f"{nom}.stl"))
    Part.makeCompound(list(p_pieces.values())).exportStep(os.path.join(SORTIE, "tranche_plissee.step"))
    MeshPart.meshFromShape(Shape=Part.makeCompound([tranche(lam_w, yt0 + (i + 0.5) * plp - elp / 2, elp) for i in range(n_lp)]),
                           LinearDeflection=1.0, AngularDeflection=1.0).write(os.path.join(SORTIE, "plis_lamelles_web.stl"))
    plis_info = {"n_plis": npl, "tubes": len(centres_p), "entraxe_mini_mm": round(d_min_p, 1), "largeur_dent_mm": eg,
                 "r_int_mm": rip, "r_creux_mm": rcr, "profondeur_dents_mm": round(re - rcr, 1),
                 "contour_entree_mm": round(contour_ext, 1), "surface_entree_m2": round(contour_ext * L * 1e-6, 3),
                 "lamelle_mm": elp, "pas_mm": plp, "lamelles_dans_la_tranche": n_lp,
                 "surface_une_lamelle_cm2": round(lam_p.Area / 100, 1),
                 "surface_lamelles_tube_complet_m2": round(2 * lam_p.Area * int(L / plp) * 1e-6, 2),
                 "centres_tubes": [[round(q.x - xt, 2), round(q.y, 2)] for q in centres_p]}
    print("plis :", plis_info, flush=True)

    pieces = {"tubes": tubes, "filtre": filtre, "plenum": plenum, "flasques": flasques, "plaque": plaque, "socle": socle,
              "ventilateurs": ventilateurs, "volet": volet}
    doc = App.newDocument("variante_f")
    for nom, forme in pieces.items():
        o = doc.addObject("Part::Feature", nom)
        o.Shape = forme
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.15, AngularDeflection=0.35).write(os.path.join(SORTIE, f"{nom}.stl"))
    MeshPart.meshFromShape(Shape=tubes, LinearDeflection=1.0, AngularDeflection=1.0).write(os.path.join(SORTIE, "tubes_web.stl"))
    doc.recompute()
    if os.path.exists(os.path.join(SORTIE, "variante_f.FCStd")):
        os.remove(os.path.join(SORTIE, "variante_f.FCStd"))
    doc.saveAs(os.path.join(SORTIE, "variante_f.FCStd"))
    Part.export(doc.Objects, os.path.join(SORTIE, "variante_f.step"))

    # --- grandeurs ---
    th = math.radians(e1 - e0)
    s_front = re * th * L
    a_bouche = (xpl - ep) * L
    d, nu_air, k_air, pr = dt * 1e-3, 1.56e-5, 0.026, 0.71
    aire = th / 2 * ((re - p["marge_tubes"]) ** 2 - (ri + p["marge_tubes"]) ** 2)
    s = math.sqrt(aire / len(centres) * 2 / math.sqrt(3)) * 1e-3
    tn = {}
    for q in (570, 830):
        Q, hA, hs = q / 3600, 0.0, []
        for u_, z_ in centres:
            r = math.hypot(u_, z_) * 1e-3
            um = Q / (th * r * L * 1e-3) * s / (s - d)
            re_ = um * d / nu_air
            h = (0.51 * re_ ** 0.5 if re_ < 1000 else 0.26 * re_ ** 0.6) * pr ** 0.37 * k_air / d
            hs.append(h)
            hA += h * math.pi * d * L * 1e-3
        tn[str(q)] = {"hA_W_K": round(hA), "h_moyen_W_m2K": round(sum(hs) / len(hs)),
                      "v_bouche_m_s": round(Q / (a_bouche * 1e-6), 1),
                      "v_ventilateurs_m_s": round(Q / (nv * math.pi * (dv / 2000) ** 2), 1)}
    bb = Part.makeCompound(list(pieces.values())).BoundBox
    l_tubes = len(centres) * L
    dim = {
        "parametres": p,
        "longueur_tube_mm": L,
        "tubes_refrigerant": {"nombre": len(centres), "entraxe_mini_mm": round(d_min, 2),
                              "longueur_totale_m": round(l_tubes * 1e-3, 1),
                              "volume_propane_cm3": round(l_tubes * math.pi * p["d_int_refrigerant"] ** 2 / 4 * 1e-3, 1),
                              "surface_exterieure_m2": round(l_tubes * math.pi * dt * 1e-6, 3)},
        "zone_echange": {"surface_frontale_m2": round(s_front * 1e-6, 4)},
        "tubes_nus": tn,
        "tranche_plissee": plis_info,
        "lamelles": {"epaisseur_mm": el, "pas_mm": pl_, "nombre_sur_le_tube": int(L / pl_),
                     "surface_m2": round(2 * lam.Area * int(L / pl_) * 1e-6, 2), "tranche_mm": lt, "lamelles_dans_la_tranche": n_lam},
        "bouche_mm": [round(xpl - ep, 1), round(L, 1)],
        "encombrement_mm": {"x": round(bb.XLength), "y": round(bb.YLength), "z": round(bb.ZLength)},
        "volumes_cm3": {k: round(v.Volume / 1e3, 1) for k, v in pieces.items()},
    }
    with open(os.path.join(SORTIE, "dimensions.json"), "w") as f:
        json.dump(dim, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in dim.items() if k != "parametres"}, indent=1, ensure_ascii=False))


if not globals().get("SANS_MAIN"):
    main()
