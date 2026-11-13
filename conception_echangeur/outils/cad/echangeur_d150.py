"""Échangeur cylindrique Ø 150 à canal d'air hélicoïdal et 32 tubes en tournesol, pour la simulation.

Demande du 2026-11-11 (option B : 400 mm, section du canal = section du conduit) :
* tube principal Ø ext. 150 mm, paroi 3 mm, longueur 400 mm fonds compris ;
* 32 tubes d'échange en aluminium (Ø 3,49 × 2,49), disposés en tournesol (modèle de Vogel, angle d'or),
  parallèles à l'axe, traversant les fonds ; pas d'arbres de Murray ;
* conduits d'air tangents 100 mm (selon l'axe) × 50 mm (selon le rayon), entrée en bas, sortie en haut ;
* canal d'air en hélice formé par une ailette : section méridienne = 50 × 100 mm = section du conduit ;
  noyau Ø 44 (= 144 − 2 × 50) ; pas = 100 mm + épaisseur d'ailette ; ≈ 2,9 tours dans 394 mm ;
* sous le premier tour et au-dessus du dernier, l'espace entre fond et ailette est plein (pas de zone
  morte), sauf le passage du conduit.

Révision du 2026-11-11 (CFD à 2,5 m/s : un tiers de l'air passait directement du conduit d'entrée à la fin du
premier tour, un cinquième sortait dès le début du dernier tour) :
* conduits inclinés de l'angle de l'hélice au rayon moyen (≈ 19°) : ils prolongent l'hélice en ligne droite,
  passent sous le fond (entrée) et au-dessus du fond (sortie) sur le quart de tour qu'ils traversent ;
* paroi de 2 mm (`ep_separation`) entre chaque conduit et le canal voisin, à l'intérieur du cylindre ;
* tubes situés sous un conduit : ils traversent le conduit et sortent par sa paroi (collecteur à contourner).

Pièces exportées (docs/formes/cylindre_d150_helice/) : enveloppe (tube + fonds + conduits), noyau,
ailette (hélice + remplissages), tubes, domaine_air (volume d'air seul, prêt à mailler), .FCStd, .step,
.stl, dimensions.json.

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/echangeur_d150.py').read())"
"""
import json
import math
import os
import sys

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
RACINE = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur"
sys.path.insert(0, os.path.join(RACINE, "outils/cad"))
import tournesol  # noqa: E402

F_PARAM = os.path.join(RACINE, "outils/cad/parametres_d150.json")
SORTIE = os.path.join(RACINE, "docs/formes/cylindre_d150_helice")

DEFAUT = {
    "d_ext_principal": 150.0,   # mm (donné)
    "ep_principal": 3.0,        # mm, paroi et fonds (donné)
    "longueur_principal": 400.0,  # mm, fonds compris (donné)
    "conduit_axial": 100.0,     # mm, largeur du conduit d'air, selon l'axe (donné)
    "conduit_radial": 50.0,     # mm, hauteur du conduit d'air, selon le rayon (donné)
    "conduit_long": 120.0,      # mm, longueur dessinée du conduit, depuis le point de tangence
    "ep_ailette": 1.0,          # mm, épaisseur de l'ailette hélicoïdale (hypothèse)
    "ep_separation": 2.0,       # mm, paroi entre un conduit et le tour de canal qu'il longe (≥ 2 mailles)
    "inclinaison_conduits": "helice",  # "helice" : pente de l'hélice au rayon moyen ; ou un angle en degrés
    "n_tubes": 32,
    "od_tube": 3.49,            # mm (niveau 5 de Murray, Ø int. 2,49 + 2 × 0,5)
    "id_tube": 2.49,
    "jeu_tube": 3.0,            # mm, jeu minimal tube / noyau et tube / paroi (axe à r_min, r_max)
    "depassement_tube": 10.0,   # mm, tube qui dépasse de chaque fond (raccordement)
    "materiau_tubes": "aluminium",
    "materiau_ailette": "aluminium",
}


def parametres():
    if not os.path.exists(F_PARAM):
        with open(F_PARAM, "w") as f:
            json.dump(DEFAUT, f, indent=2, ensure_ascii=False)
    with open(F_PARAM) as f:
        return dict(DEFAUT, **json.load(f))


def anneau(r1, r2, z0, h):
    return Part.makeCylinder(r2, h, V(0, 0, z0)).cut(Part.makeCylinder(r1, h, V(0, 0, z0)))


def balayage(rc, ri, pas, z0, theta0, tours, z_bas, z_haut):
    """Volume balayé par le rectangle méridien r ∈ [rc, ri], z ∈ [z0 + z_bas, z0 + z_haut] le long d'une
    hélice droite (sens trigonométrique en montant) de pas `pas`, sur `tours` tours, partant de l'angle θ0."""
    helice = Part.makeHelix(pas, pas * tours, rc)
    helice.translate(V(0, 0, z0))
    prof = Part.makePolygon([V(rc, 0, z0 + z_bas), V(ri, 0, z0 + z_bas), V(ri, 0, z0 + z_haut),
                             V(rc, 0, z0 + z_haut), V(rc, 0, z0 + z_bas)])
    s = Part.Wire(helice).makePipeShell([prof], True, True)
    s.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(theta0))
    return s


def verifie(nom, s):
    n = len(s.Solids)
    print(f"[{nom}] valide {s.isValid()}, solides {n}, volume {s.Volume/1e3:.1f} cm³", flush=True)
    return s


def main():
    p = parametres()
    os.makedirs(SORTIE, exist_ok=True)
    ep = p["ep_principal"]
    Ro = p["d_ext_principal"] / 2
    Ri = Ro - ep
    Lint = p["longueur_principal"] - 2 * ep          # z ∈ [0, Lint] : intérieur, fonds de z = −ep et Lint + ep
    gap, h = p["conduit_axial"], p["conduit_radial"]
    Rc = Ri - h                                      # rayon du noyau
    t = p["ep_ailette"]
    pas = gap + t
    tours = (Lint - gap) / pas
    th_fin = 2 * math.pi * tours
    Ld = p["conduit_long"]
    e_sep = p["ep_separation"]
    r_m = (Rc + Ri) / 2
    incl = p["inclinaison_conduits"]
    alpha = math.atan(pas / (2 * math.pi * r_m)) if incl == "helice" else math.radians(float(incl))
    ta = math.tan(alpha)

    A = anneau(Rc, Ri, 0, Lint)
    # canal d'air : fenêtre d'entrée z ∈ [0, gap] à θ = 0, fenêtre de sortie z ∈ [Lint − gap, Lint] à θ_fin
    C = verifie("canal", balayage(Rc, Ri, pas, 0, 0, tours, 0, gap))
    # remplissages : sous le premier tour et au-dessus du dernier
    # (profil de hauteur = pas : au-delà, le balayage se recouvre d'un tour à l'autre et le booléen échoue)
    # W1 = {θ ∈ [0, 2π[, 0 ≤ z < z_h(θ)} avec z_h(θ) = pas·θ/2π (face inférieure du canal du 1er tour)
    W1 = anneau(Rc, Ri, 0, pas).cut(balayage(Rc, Ri, pas, 0, 0, 1.0, 0, pas))
    # W2 = {dernier tour, z_h(θ) + pas < z ≤ Lint} (au-dessus de l'ailette du dernier tour)
    th_s = th_fin - 2 * math.pi
    z_s = pas * (tours - 1)
    W2 = anneau(Rc, Ri, Lint - gap, gap).cut(balayage(Rc, Ri, pas, z_s, th_s, 1.0, 0, pas))
    verifie("remplissage bas", W1)
    verifie("remplissage haut", W2)
    # parties des remplissages où le conduit peut passer : sous le canal moins e_sep (entrée), au-dessus de
    # l'ailette plus e_sep − t (sortie) → paroi de e_sep entre conduit et canal
    # (remplissage décalé puis recoupé à l'anneau : soustraire deux hélicoïdes presque parallèles fait échouer OCC)
    W1s = W1.copy()
    W1s.translate(V(0, 0, -e_sep))
    W1s = W1s.common(anneau(Rc, Ri, 0, pas))
    W2s = W2.copy()
    W2s.translate(V(0, 0, e_sep - t))
    W2s = W2s.cut(Part.makeBox(4 * Ro, 4 * Ro, pas, V(-2 * Ro, -2 * Ro, Lint)))   # (common avec l'anneau : vide, bogue OCC)
    verifie("passage possible bas", W1s)
    verifie("passage possible haut", W2s)

    def conduit(x0, x1, z0, z1, sens, longueur):
        """Prisme oblique : section verticale x ∈ [x0, x1], z ∈ [z0, z1] dans le plan y = 0, poussée selon
        (0, sens, sens·tan α) sur `longueur` en y : le conduit suit la pente de l'hélice."""
        f = Part.Face(Part.makePolygon([V(x0, 0, z0), V(x1, 0, z0), V(x1, 0, z1), V(x0, 0, z1), V(x0, 0, z0)]))
        return f.extrude(V(0, sens * longueur, sens * longueur * ta))

    # conduits : entrée à θ = 0 (l'air arrive en +y et monte), sortie à θ_fin (l'air part en avant et monte)
    D_in = conduit(Rc, Ri, 0, gap, -1, Ld)
    D_out = conduit(Rc, Ri, Lint - gap, Lint, 1, Ld)
    D_out.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(th_fin))
    cyl_i = Part.makeCylinder(Ri, Lint, V(0, 0, 0))
    # recouvrement de 10 mm avec le début et la fin du canal : des volumes qui se touchent seulement par une
    # face laissent cette face DANS le domaine fusionné (paroi parasite qui bouchait la sortie, CFD du 11/11)
    rec = 10.0
    D_in_rec = Part.makeBox(h, rec, gap, V(Rc, 0, 0))
    D_out_rec = Part.makeBox(h, rec, gap, V(Rc, -rec, Lint - gap))
    D_out_rec.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(th_fin))
    # pont de ±2 mm à travers le plan de sortie : le canal (balayage parti de θ = 0) et le remplissage haut
    # (balayage parti de θ_fin − 2π) ne coïncident pas exactement sur ce plan ; sans pont, un film solide
    # d'épaisseur infime y reste et bouche la sortie. Bas du pont à + 1 mm pour ne pas percer l'ailette.
    pont = Part.makeBox(h, 4.0, gap - 1.0, V(Rc, -2.0, Lint - gap + 1.0))
    pont.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(th_fin))
    morceaux = [D_in.common(W1s), D_out.common(W2s), D_in.cut(cyl_i), D_out.cut(cyl_i),
                D_in_rec.common(C), D_out_rec.common(C), pont.common(cyl_i)]
    for nom, m in zip(("entrée dans le remplissage", "sortie dans le remplissage", "conduit d'entrée", "conduit de sortie"), morceaux):
        verifie(nom, m)
    F = C.fuse(morceaux).removeSplitter()
    verifie("air (sans tubes)", F)
    if len(F.Solids) != 1:
        raise RuntimeError("le domaine d'air n'est pas d'un seul tenant")
    # aucune face du domaine ne doit rester sur les plans des fenêtres d'entrée (θ = 0) et de sortie (θ_fin)
    for nom, ang, z0 in (("entrée", 0.0, 0.0), ("sortie", th_fin, Lint - gap)):
        tng = V(-math.sin(ang), math.cos(ang), 0)
        rad = V(math.cos(ang), math.sin(ang), 0)
        parasite = sum(fa.Area for fa in F.Faces if isinstance(fa.Surface, Part.Plane)
                       and abs(abs(fa.Surface.Axis.dot(tng)) - 1) < 1e-4 and abs(fa.CenterOfMass.dot(tng)) < 0.5
                       and fa.CenterOfMass.dot(rad) > Rc and z0 - 1 < fa.CenterOfMass.z < z0 + gap + 1)
        print(f"[fenêtre {nom}] paroi parasite {parasite:.1f} mm²", flush=True)
        if parasite > 300.0:          # reste toléré : bande de 1 mm sous le pont (≈ 2 × 50 mm²)
            raise RuntimeError(f"paroi interne sur la fenêtre de {nom} : {parasite:.0f} mm²")

    # tubes en tournesol : axe entre r_min et r_max, aire égale par tube
    od, idt = p["od_tube"], p["id_tube"]
    r_min, r_max = Rc + p["jeu_tube"] + od / 2, Ri - p["jeu_tube"] - od / 2
    pts = [(r * math.cos(a), r * math.sin(a)) for r, a in tournesol.vogel(p["n_tubes"], r_min, r_max)]
    dep = p["depassement_tube"]
    c_f, s_f = math.cos(th_fin), math.sin(th_fin)

    def bornes_tube(x, y):
        """z bas et haut du tube : au-delà du fond, ou au-delà de la paroi du conduit s'il passe dessous / dessus."""
        zb, zh = -ep - dep, Lint + ep + dep
        if Rc - ep <= x <= Ri + ep and y < 0:                       # sous le conduit d'entrée
            zb = min(zb, y * ta - ep - dep)
        xp, yp = x * c_f + y * s_f, -x * s_f + y * c_f              # repère du conduit de sortie
        if Rc - ep <= xp <= Ri + ep and yp > 0:
            zh = max(zh, Lint + yp * ta + ep + dep)
        return zb, zh
    bt = [bornes_tube(x, y) for x, y in pts]
    t_ext = [Part.makeCylinder(od / 2, zh - zb, V(x, y, zb)) for (x, y), (zb, zh) in zip(pts, bt)]
    t_int = [Part.makeCylinder(idt / 2, zh - zb + 2, V(x, y, zb - 1)) for (x, y), (zb, zh) in zip(pts, bt)]
    print("[tubes] traversant un conduit :", sum(1 for zb, zh in bt if zb < -ep - dep or zh > Lint + ep + dep), flush=True)
    tubes_ext = Part.makeCompound(t_ext)
    tubes = Part.makeCompound([e.cut(i) for e, i in zip(t_ext, t_int)])

    # ailette = anneau − volume d'air − tubes : construite d'un bloc à partir du domaine d'air (valide, d'un seul
    # tenant). La construction par morceaux (remplissages − conduits) laissait des feuilles d'épaisseur nulle dans
    # les plans z = pas, z = Lint − gap et dans la fenêtre de sortie : invisibles pour la CFD, mais elles semblaient
    # boucher le passage dans la vue 3D.
    # Anneau resserré de 0,01 mm : les parois du canal issues du balayage sont des BSplines qui ne coïncident pas
    # exactement avec les cylindres r = Ri et r = Rc ; sans ce retrait, la soustraction laisse une peau d'épaisseur
    # quasi nulle sur toute la paroi (solide non valide, triangulation qui recouvre tout le cylindre).
    d_ = 0.01
    A_ail = Part.makeCylinder(Ri - d_, Lint - 2 * d_, V(0, 0, d_)).cut(Part.makeCylinder(Rc + d_, Lint - 2 * d_, V(0, 0, d_)))
    brut = A_ail.cut(F).cut(tubes_ext)
    sol = [x for x in brut.Solids if x.Volume > 1000.0]            # sans copeaux ni volumes nuls (mm³)
    ailette = Part.makeCompound(sol)
    verifie("ailette", ailette)
    if not ailette.isValid():
        raise RuntimeError("ailette non valide")
    # contrôle : aucune grande face plane dans les fenêtres d'entrée / sortie, aucune face horizontale traversante
    for nom, ang in (("entrée", 0.0), ("sortie", th_fin)):
        tng = V(-math.sin(ang), math.cos(ang), 0)
        fen = sum(abs(fa.Area) for fa in ailette.Faces if isinstance(fa.Surface, Part.Plane)
                  and abs(abs(fa.Surface.Axis.dot(tng)) - 1) < 1e-4 and abs(fa.CenterOfMass.dot(tng)) < 1.0)
        print(f"[ailette, fenêtre {nom}] faces dans le plan : {fen:.0f} mm²", flush=True)
        if fen > 300.0:
            raise RuntimeError(f"l'ailette ferme la fenêtre de {nom} ({fen:.0f} mm²)")
    trav = [fa for fa in ailette.Faces if isinstance(fa.Surface, Part.Plane) and abs(abs(fa.Surface.Axis.z) - 1) < 1e-6
            and fa.Area < 0]
    if trav:
        raise RuntimeError(f"faces dégénérées dans l'ailette : {len(trav)}")
    air = verifie("domaine d'air", F.cut(tubes_ext))
    noyau = Part.makeCylinder(Rc, Lint, V(0, 0, 0))
    # enveloppe : tube + fonds, trous des tubes, ouvertures et coques des conduits
    env = Part.makeCylinder(Ro, Lint + 2 * ep, V(0, 0, -ep)).cut(cyl_i)
    coques = []
    for sens, rot, z in ((-1, 0.0, 0.0), (1, th_fin, Lint - gap)):
        ext = conduit(Rc - ep, Ri + ep, z - ep, z + gap + ep, sens, Ld)
        intr = conduit(Rc, Ri, z, z + gap, sens, Ld + 2)
        intr.translate(V(0, -sens * 1.0, -sens * ta))               # dépasse de 1 mm de chaque côté
        c = ext.cut(intr)
        c.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(rot))
        coques.append(c.cut(Part.makeCylinder(Ri, Lint + 2 * ep, V(0, 0, -ep))))
    env = env.fuse(coques).cut(D_in).cut(D_out).cut(tubes_ext).removeSplitter()
    verifie("enveloppe", env)

    pieces = {"enveloppe": env, "noyau": noyau, "ailette": ailette, "tubes": tubes, "domaine_air": air}
    doc = App.newDocument("echangeur_d150")
    for nom, forme in pieces.items():
        o = doc.addObject("Part::Feature", nom)
        o.Shape = forme
        o.addProperty("App::PropertyString", "Materiau", "Simulation")
        o.Materiau = {"tubes": p["materiau_tubes"], "ailette": p["materiau_ailette"], "domaine_air": "air"}.get(nom, "à définir")
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.08, AngularDeflection=0.3).write(
            os.path.join(SORTIE, f"{nom}.stl"))
    doc.recompute()
    doc.saveAs(os.path.join(SORTIE, "echangeur_d150.FCStd"))
    Part.export(doc.Objects, os.path.join(SORTIE, "echangeur_d150.step"))
    Part.export([doc.getObject("domaine_air")], os.path.join(SORTIE, "domaine_air.step"))

    # contrôles : section méridienne du canal (plan contenant l'axe) à plusieurs angles
    sections = {}
    for deg in (45, 90, 135, 180, 225, 270, 315):
        a = math.radians(deg)
        lame = Part.makeBox(0.2, Ri + 1, Lint, V(-0.1, 0, 0))   # lame mince dans le plan méridien θ = 90°
        lame.rotate(V(0, 0, 0), V(0, 0, 1), deg - 90)
        aire = F.common(lame).Volume / 0.2
        aire_tubes = F.common(tubes_ext).common(lame).Volume / 0.2
        sections[deg] = dict(canal_mm2=round(aire, 0), canal_moins_tubes_mm2=round(aire - aire_tubes, 0))
    # contrôle tournesol : écarts d'indice entre plus proches voisins (doivent être des nombres de Fibonacci)
    ecarts = {}
    for i, a in enumerate(pts):
        d = sorted((math.dist(a, b), abs(i - j)) for j, b in enumerate(pts) if j != i)
        for _, k in d[:2]:
            ecarts[k] = ecarts.get(k, 0) + 1
    dmin = min(math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1:])
    dim = {
        "parametres": p,
        "rayons_mm": {"exterieur": Ro, "interieur": Ri, "noyau": Rc, "tubes_min": round(r_min, 2), "tubes_max": round(r_max, 2)},
        "longueur_interieure_mm": Lint,
        "helice": {"pas_mm": pas, "tours": round(tours, 3), "angle_sortie_deg": round(math.degrees(th_fin) % 360, 1),
                   "angle_helice_deg": {f"r{r:.0f}": round(math.degrees(math.atan(pas / (2 * math.pi * r))), 1)
                                        for r in (Rc, r_m, Ri)},
                   "longueur_chemin_moyen_mm": round(tours * math.hypot(2 * math.pi * r_m, pas), 0)},
        "conduits": {"inclinaison_deg": round(math.degrees(alpha), 2), "ep_separation_mm": e_sep,
                     "descente_sous_fond_mm": round(Ld * ta, 1)},
        "section_conduit_mm2": gap * h,
        "section_canal_meridienne": sections,
        "tubes": {"n": p["n_tubes"], "positions_xy_mm": [[round(x, 2), round(y, 2)] for x, y in pts],
                  "ecart_min_axes_mm": round(dmin, 2), "ecart_min_parois_mm": round(dmin - od, 2),
                  "surface_ext_dans_air_m2": round(p["n_tubes"] * math.pi * od * Lint * 1e-6, 4),
                  "ecarts_indice_plus_proches_voisins": dict(sorted(ecarts.items()))},
        "volumes_cm3": {k: round(v.Volume / 1e3, 1) for k, v in pieces.items()},
        "surface_ailette_m2": round(ailette.Area * 1e-6, 4),
    }
    with open(os.path.join(SORTIE, "dimensions.json"), "w") as f:
        json.dump(dim, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in dim.items() if k != "parametres"}, indent=1, ensure_ascii=False))


if not globals().get("SANS_MAIN"):
    main()
