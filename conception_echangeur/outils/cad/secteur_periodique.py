"""Secteur périodique de 1/8 du concept imprimé (variante F, tube Ø 150), pour les études CFD rapides (13/11/2026).

L'échangeur (secteur d'échange de 230°) est découpé en 8 secteurs identiques de 28,75° ; chacun porte 4 profils de propane
placés en tournesol À L'INTÉRIEUR du secteur (8 × 4 = 32 circuits). La CFD ne calcule qu'un secteur, avec des faces
périodiques en rotation sur ses deux côtés (et en translation le long du tube, comme avant).

Lamelles : version « décalées, espace radial 4 mm » (meilleur cas du 13/11) : couronnes de 5 mm, décalées d'un demi-pas
d'une couronne à l'autre, 4 mm libres entre deux couronnes ; une lamelle sur deux sous r_intercalaire.

Sorties (docs/formes/cylindre_radial/variante_f/imprime/secteur/) : un secteur détaillé sur `longueur` mm (lamelles,
profils, canaux, frontières du calcul) et l'échangeur complet en transparence (8 secteurs), pour la vue 3D du rapport.

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/secteur_periodique.py').read())"
"""
import json
import math
import os

SANS_MAIN = True
exec(open("/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/concept_imprime.py").read())

SORTIE_S = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/docs/formes/cylindre_radial/variante_f/imprime/secteur"
S = {
    "n_secteurs": 8,
    "tubes_par_secteur": 4,
    "espace_radial": 4.0,       # mm, entre deux couronnes de lamelles
    "longueur": 25.0,           # mm de tube dessinés (10 pas de lamelles)
    "r_entree": 77.0,           # frontières du calcul
    "r_sortie": 33.0,
    # lamelles perpendiculaires (radiales, elles contiennent l'axe) : n par secteur sur toute la profondeur, plus autant
    # d'intercalaires à partir de r_radiales_inter (sinon les canaux s'élargissent trop vers l'extérieur)
    "n_radiales": 3,            # 3 par secteur : 5 mm d'écart au bord du noyau (r = 35 mm), ≈ 11 mm à l'extérieur (7 avant)
    "r_radiales_inter": 54.0,
    # campagne du 13/11 (3e) : 5 mm d'écart entre deux lamelles (demande de l'utilisateur)
    "pas_lamelles": 6.0,        # mm (1 mm de lamelle, 5 mm d'écart) ; 2,5 mm avant
    "intercalaires": False,     # plus de « une lamelle sur deux » près du noyau (le pas est déjà large)
    "radiales_inter": False,    # plus de lamelles radiales intercalaires (une radiale sur deux)
    "couloir_profil": 1.5,      # mm : les lamelles radiales sont coupées à moins de 1,5 mm du bord d'un profil (pas de fente)
}


# version : SUFFIXE_S et S_MODIF_S peuvent être définis avant l'exec (fichiers <pièce><SUFFIXE_S>.stl)
SUFFIXE_S = globals().get("SUFFIXE_S", "")
S.update(globals().get("S_MODIF_S", {}))
P.update(globals().get("P_MODIF_S", {}))       # ex. {"ep_lamelle": 0.5}


def tournesol_secteur(f0, f1, rn, re, b_prof):
    """4 profils dans le secteur [f0, f1] : un au milieu de chaque espace entre couronnes, angles au pas d'or (quinconce)."""
    n = int(S["tubes_par_secteur"])
    g = (math.sqrt(5) - 1) / 2
    # rayons : au milieu de chaque espace entre deux couronnes (« à cheval ») : chaque profil relie deux couronnes, aucune
    # couronne ne flotte (le tournesol à aire égale laissait la couronne extérieure sans profil)
    if S.get("profils_reguliers"):
        # profils répartis régulièrement sur la profondeur (couronnes rapprochées : un profil par espace ne suffit plus)
        a_ = P["profil_long"] / 2
        r0_, r1_ = rn + a_, re - a_ - 0.5
        rayons = [r0_ + (r1_ - r0_) * k / (n - 1) for k in range(n)]
        out = []
        for k in range(n):
            r = rayons[k]
            ma = math.degrees((b_prof + P["jeu_profils"]) / r)
            out.append((r, f0 + ma + ((k * g) % 1.0) * (f1 - f0 - 2 * ma)))
        if S.get("stries"):
            out = recaler_dans_dents(out, f0, f1, b_prof)
        return out
    rayons, r_in = [], rn
    while True:
        r_out = min(r_in + P["l_troncon"], re)
        if r_out >= re - 0.5:
            break
        rayons.append(min(r_out + S["espace_radial"] / 2, re - P["profil_long"] / 2 + 0.5))
        r_in = r_out + S["espace_radial"]
    out = []
    for k in range(n):
        r = rayons[k % len(rayons)]
        ma = math.degrees((b_prof + P["jeu_profils"]) / r)
        a = f0 + ma + ((k * g) % 1.0) * (f1 - f0 - 2 * ma)
        out.append((r, a))
    return out


def plan_dents(a0, a1):
    """Contour (vue de dessus) des lamelles « avec stries » (contour_lamelle du concept) : bord extérieur en dents
    triangulaires, une dent par secteur, pointes sur les faces périodiques, rainure en V au milieu de chaque secteur jusqu'à
    r_creux ; aligné sur la grille des secteurs et débordant d'un secteur de chaque côté de [a0, a1]."""
    A0, A1 = P["secteur_deg"]
    da = (A1 - A0) / S["n_secteurs"]
    k0 = math.floor((a0 - A0) / da + 1e-9) - 1
    k1 = math.ceil((a1 - A0) / da - 1e-9) + 1
    nd0 = P["n_dents"]
    P["n_dents"] = k1 - k0
    try:
        return contour_lamelle(True, P["r_noyau"] - 1.0, P["r_ext"], A0 + k0 * da, A0 + k1 * da)
    finally:
        P["n_dents"] = nd0


def recaler_dans_dents(pos, f0, f1, b_prof):
    """Profils (r, φ relatif au début du secteur) déplacés en angle pour tenir dans les dents (lamelles avec stries) :
    l'angle le plus proche de l'angle d'origine où l'ellipse agrandie de 0,5 mm est entièrement sur la lamelle (les bords
    du secteur sont permis : la dent y est centrée, le profil est alors partagé avec le secteur voisin)."""
    A0, A1 = P["secteur_deg"]
    da = (A1 - A0) / S["n_secteurs"]
    plan = plan_dents(A0, A0 + da)          # secteur de référence (relatif : angles + A0)
    out = []
    for r, a in pos:
        def dehors(x):
            aa = A0 + x
            e = ellipse(r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa)), P["profil_long"] / 2 + 0.5, b_prof + 0.5, aa)
            return e.cut(plan).Area
        if dehors(a) < 1e-3:
            out.append((r, a))
            continue
        cand = sorted((x * da / 200 for x in range(201)), key=lambda x: abs(x - a))
        best = next((x for x in cand if dehors(x) < 1e-3), None)
        if best is None:
            best = min(cand, key=dehors)
        print(f"profil r = {r:.1f} : φ {a:.2f} → {best:.2f}° (dans la dent)", flush=True)
        out.append((r, best))
    return out


def faces_lamelle(r_in, r_out, a0, a1, pas_ang):
    """Faces (vue de dessus) d'une couronne de lamelles, découpée par le contour en dents si S["stries"]."""
    c = secteur(r_in, r_out, a0, a1, pas=pas_ang)
    if not S.get("stries"):
        return [c]
    return [f for f in c.common(plan_dents(a0, a1)).Faces if f.Area > 0.5]


def lamelles(a0, a1, rn, re, y0, longueur, pas_ang=1.0, continues=False):
    """continues : lamelles pleines de r_noyau à r_ext à chaque pas (sans coupure, sans espace, sans intercalaires),
    comme le cas CFD « lamelles continues » du 13/11."""
    t, jeu, lc = P["ep_lamelle"], P["jeu"], P["l_troncon"]
    pas = S["pas_lamelles"]
    if continues:
        c = secteur(rn, re, a0, a1, pas=pas_ang)
        return [dans_plan_y(c, y0 + i * pas, t) for i in range(int(longueur / pas))]
    forme = S.get("forme_lamelles", "decale")
    if forme == "vague":
        res, i = [], 0
        while y0 + i * pas + pas / 2 + t <= y0 + longueur:
            res.append(vague(rn, re, a0, a1, y0 + t / 2 + i * pas))
            i += 1
        return res
    res = []
    for r_in, r_out, fam in troncons(rn, re):
        cs = faces_lamelle(r_in, r_out, a0, a1, pas_ang)
        i = 0
        while True:
            y = y0 + fam * pas / 2 + i * pas
            if y + t > y0 + longueur:
                break
            if not (S["intercalaires"] and r_out <= P["r_intercalaire"] and i % 2 == 1):
                res += [dans_plan_y(c, y, t) for c in cs]
            i += 1
    return res


def troncons(rn, re, forme=None):
    """Couronnes de lamelles (r_in, r_out, famille) ; famille 0 au pas, famille 1 décalée d'un demi-pas le long du tube.
    forme (S["forme_lamelles"]) :
      decale   couronnes de l_troncon séparées de espace_radial, familles alternées (une couronne sur deux décalée) ;
      imbrique chaque famille a ses couronnes séparées de espace_radial, la famille 1 décalée d'une demi-période
               radiale : chaque lamelle recouvre la moitié des deux lamelles voisines de l'autre famille (14/11) ;
      vague    mêmes couronnes que decale, reliées entre elles (voir vague())."""
    lc, g = P["l_troncon"], S["espace_radial"]
    forme = forme or S.get("forme_lamelles", "decale")
    out = []
    if forme == "imbrique":
        per = lc + g
        for fam, r0 in ((0, rn), (1, rn - per / 2)):
            r = r0
            while r < re:
                a, b = max(r, rn), min(r + lc, re)
                if b - a >= 1.0:                      # pas de morceau de moins de 1 mm
                    out.append((a, b, fam))
                r += per
        return out
    k, r_in = 0, rn
    while r_in < re - 0.5:
        r_out = min(r_in + lc, re)
        out.append((r_in, r_out, k % 2))
        r_in = r_out + g
        k += 1
    return out


def ligne_vague(rn, re):
    """Ligne moyenne (r, y) de l'ailette en vague : paliers aux couronnes « decale » (y = 0 ou pas/2), raccordés dans les
    espaces radiaux par des demi-cosinus (pente nulle aux deux bouts, pas d'angle vif)."""
    pas = S["pas_lamelles"]
    tr = troncons(rn, re, "decale")
    pts = []
    for i, (a, b, fam) in enumerate(tr):
        y = fam * pas / 2
        if i > 0:
            b0, y0_ = tr[i - 1][1], tr[i - 1][2] * pas / 2
            n = 16
            for j in range(1, n):
                s = j / n
                pts.append((b0 + (a - b0) * s, y0_ + (y - y0_) * (1 - math.cos(math.pi * s)) / 2))
        pts += [(a, y), (b, y)]
    return pts


def vague(rn, re, a0, a1, yc):
    """Ailette en vague d'épaisseur ep_lamelle (mesurée perpendiculairement à la tôle), ligne moyenne à yc + ligne_vague,
    tournée de a0 à a1 autour de l'axe du tube."""
    t = P["ep_lamelle"]
    pts = ligne_vague(rn, re)
    haut, bas = [], []
    for i, (r, y) in enumerate(pts):
        p0, p1 = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        dr, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dr, dy)
        nr, ny = -dy / L, dr / L
        haut.append((r + nr * t / 2, yc + y + ny * t / 2))
        bas.append((r - nr * t / 2, yc + y - ny * t / 2))
    c, s = math.cos(math.radians(a1)), math.sin(math.radians(a1))
    poly = [V(r * c, y, r * s) for r, y in haut + bas[::-1]]
    f = Part.Face(Part.makePolygon(poly + [poly[0]]))
    return f.revolve(V(0, 0, 0), V(0, 1, 0), a1 - a0)      # rotation autour de +y : l'angle φ décroît, de a1 à a0


def couloirs(fa, pos, n_secteurs=1, da=None):
    """Zones interdites aux lamelles radiales : ellipses des profils agrandies de couloir_profil (faces 2D)."""
    b = P["d_canal"] / 2 + P["paroi"] + S["couloir_profil"]
    a_ = P["profil_long"] / 2 + S["couloir_profil"]
    out = []
    for j in range(n_secteurs):
        for r, a in pos:
            aa = fa + j * (da or 0.0) + a
            out.append(ellipse(r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa)), a_, b, aa))
    return out


def lamelles_radiales(fa, fb, rn, re, longueur, n_secteurs=1, y0=0.0, exclusions=None, pos_profils=None):
    """exclusions : faces 2D retirées des lamelles radiales (couloirs autour des profils) ; pos_profils : profils
    (r, φ absolu) posés sur une radiale : la partie de cette radiale sous le profil est gardée (le profil l'épaissit)."""
    """Parois radiales de 1 mm (plans φ = cste, contenant l'axe), du secteur [fa, fb] découpé en n_secteurs de même angle :
    n_radiales complètes par secteur, décalées d'un demi-pas (les faces périodiques ne les touchent pas), et autant
    d'intercalaires (de r_radiales_inter à r_ext) entre elles, dont celles des bords coupées en leur milieu par la face
    périodique."""
    t = P["ep_lamelle"]
    da = (fb - fa) / n_secteurs
    d = da / S["n_radiales"]
    res = []

    def paroi(a, r0):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        e = t / 2
        f = Part.Face(Part.makePolygon([V(r0 * c + e * s, r0 * s - e * c, 0), V(re * c + e * s, re * s - e * c, 0),
                                        V(re * c - e * s, re * s + e * c, 0), V(r0 * c - e * s, r0 * s + e * c, 0),
                                        V(r0 * c + e * s, r0 * s - e * c, 0)]))
        for z in exclusions or []:
            f = f.cut(z)
        if f.Area < 1e-3:
            return None
        return dans_plan_y(f, y0, longueur)
    for j in range(n_secteurs):
        f0 = fa + j * da
        for k in range(int(S["n_radiales"])):
            res.append(paroi(f0 + (k + 0.5) * d, rn))
            if S["radiales_inter"]:
                res.append(paroi(f0 + k * d, S["r_radiales_inter"]))
        if S["radiales_inter"] and j == n_secteurs - 1:
            res.append(paroi(fb, S["r_radiales_inter"]))
    return [x for x in res if x is not None]


def main_secteur():
    os.makedirs(SORTIE_S, exist_ok=True)
    re, rn = P["r_ext"], P["r_noyau"]
    a0, a1 = P["secteur_deg"]
    ns = int(S["n_secteurs"])
    da = (a1 - a0) / ns
    L = S["longueur"]
    rc = P["d_canal"] / 2
    b_prof = rc + P["paroi"]
    # secteur simulé : le 4e (au milieu, côté pièce)
    js = ns // 2
    f0, f1 = a0 + js * da, a0 + (js + 1) * da
    pos = tournesol_secteur(0.0, da, rn, re, b_prof)          # positions relatives au début du secteur

    def profils(fa, dy=0.0, long=L):
        pr, ca = [], []
        for r, a in pos:
            aa = fa + a
            cx, cz = r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa))
            e = ellipse(cx, cz, P["profil_long"] / 2, b_prof, aa)
            trou = Part.Face(Part.Wire(Part.makeCircle(rc, V(cx, cz, 0))))
            pr.append(dans_plan_y(e.cut(trou), dy, long))
            ca.append(dans_plan_y(trou, dy, long))
        return pr, ca

    pr, ca = profils(f0)
    # modèle avec lamelles radiales : chaque profil recentré sur la lamelle radiale la plus proche (sinon une lamelle passe
    # à quelques dixièmes de mm de son axe et laisse des poches d'air minces) ; intercalaires seulement au-delà de r_radiales_inter
    d_rad = da / S["n_radiales"]
    def angle_rad(r, a):
        cand = [(k + 0.5) * d_rad for k in range(int(S["n_radiales"]))]
        if S["radiales_inter"] and r - P["profil_long"] / 2 >= S["r_radiales_inter"]:
            cand += [k * d_rad for k in range(int(S["n_radiales"]) + 1)]
        return min(cand, key=lambda x: abs(x - a))
    pos_rad = [(r, angle_rad(r, a)) for r, a in pos]
    pos_ini = pos
    pos = pos_rad
    pr_r, ca_r = profils(f0)
    pr_tout_r = []
    for j in range(ns):
        if j != js:
            pr_tout_r += profils(a0 + j * da)[0]
    pos = pos_ini
    lam = lamelles(f0, f1, rn, re, 0.0, L, pas_ang=0.25)
    # frontières du calcul (secteur) : faces périodiques en rotation, entrée, sortie
    def plan_radial(a):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        f = Part.Face(Part.makePolygon([V(S["r_sortie"] * c, S["r_sortie"] * s, 0), V(S["r_entree"] * c, S["r_entree"] * s, 0),
                                        V(S["r_entree"] * c + 0, S["r_entree"] * s, 0), V(S["r_sortie"] * c, S["r_sortie"] * s, 0)]))
        return f
    def bande_radiale(a):
        """Face radiale (r_sortie → r_entree) dans le plan φ = a, sur toute la longueur."""
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        return Part.Face(Part.makePolygon([V(S["r_sortie"] * c, 0, S["r_sortie"] * s), V(S["r_entree"] * c, 0, S["r_entree"] * s),
                                           V(S["r_entree"] * c, L, S["r_entree"] * s), V(S["r_sortie"] * c, L, S["r_sortie"] * s),
                                           V(S["r_sortie"] * c, 0, S["r_sortie"] * s)]))
    def arc(r, fa, fb):
        n = 30
        pts = [V(r * math.cos(math.radians(fa + (fb - fa) * i / n)), 0, r * math.sin(math.radians(fa + (fb - fa) * i / n))) for i in range(n + 1)]
        w = Part.makePolygon(pts)
        return w.extrude(V(0, L, 0))
    pieces = {
        "sect_lamelles": Part.makeCompound(lam),
        "sect_profils": Part.makeCompound(pr),
        "sect_canaux": Part.makeCompound(ca),
        "sect_periodiques": Part.makeCompound([bande_radiale(f0), bande_radiale(f1)]),
        "sect_entree": arc(S["r_entree"], f0, f1),
        "sect_sortie": arc(S["r_sortie"], f0, f1),
    }
    # échangeur complet, en transparence : couronnes sur 230° (sans le secteur simulé) et 32 profils
    lam_tout = lamelles(a0, f0, rn, re, 0.0, L, pas_ang=4.0) + lamelles(f1, a1, rn, re, 0.0, L, pas_ang=4.0)
    pr_tout = []
    for j in range(ns):
        if j != js:
            pr_tout += profils(a0 + j * da)[0]
    pieces["tout_lamelles"] = Part.makeCompound(lam_tout)
    pieces["sect_cont_lamelles"] = Part.makeCompound(lamelles(f0, f1, rn, re, 0.0, L, pas_ang=0.25, continues=True))
    pieces["sect_rad_lamelles"] = Part.makeCompound(lamelles_radiales(f0, f1, rn, re, L,
                                                                      exclusions=couloirs(f0 - da, pos_rad, 3, da)))
    pieces["sect_rad_profils"] = Part.makeCompound(pr_r)
    pieces["sect_rad_canaux"] = Part.makeCompound(ca_r)
    pieces["tout_rad_profils"] = Part.makeCompound(pr_tout_r)
    excl_tout = couloirs(a0, pos_rad, ns, da)
    pieces["tout_rad_lamelles"] = Part.makeCompound(lamelles_radiales(a0, f0, rn, re, L, js, exclusions=excl_tout)
                                                    + lamelles_radiales(f1, a1, rn, re, L, ns - js - 1, exclusions=excl_tout))
    pieces["tout_cont_lamelles"] = Part.makeCompound(lamelles(a0, f0, rn, re, 0.0, L, pas_ang=4.0, continues=True)
                                                     + lamelles(f1, a1, rn, re, 0.0, L, pas_ang=4.0, continues=True))
    pieces["tout_profils"] = Part.makeCompound(pr_tout)
    for nom, forme in pieces.items():
        fin = nom.startswith("tout")
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.8 if fin else 0.15, AngularDeflection=0.8 if fin else 0.4).write(
            os.path.join(SORTIE_S, f"{nom}{SUFFIXE_S}.stl"))
        print(nom, len(forme.Solids), "solides", flush=True)
    # distance mini entre profils (dans le secteur et avec les secteurs voisins)
    pts = []
    for j in (js - 1, js, js + 1):
        for r, a in pos:
            aa = a0 + j * da + a
            pts.append((r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa))))
    dmin = min(math.dist(p, q) for i, p in enumerate(pts) for q in pts[i + 1:])
    info = dict(S, profils_radiales=[[round(r, 2), round(a, 2)] for r, a in pos_rad], angle_secteur_deg=da, secteur_simule_deg=[f0, f1], profils=[[round(r, 2), round(a, 2)] for r, a in pos],
                entraxe_mini_mm=round(dmin, 1), parametres=P)
    with open(os.path.join(SORTIE_S, f"secteur{SUFFIXE_S}.json"), "w") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in info.items() if k != "parametres"}, ensure_ascii=False))


if not globals().get("SANS_MAIN_SECTEUR"):
    main_secteur()
