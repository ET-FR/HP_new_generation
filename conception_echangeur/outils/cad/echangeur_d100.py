"""Échangeur cylindrique Ø 100 mm : tube principal, 16 tubes de propane, arbres de Murray 1 → 16.

Modèle FreeCAD paramétrique (version du 10 novembre 2026, remplace outils/cad/echangeur_helice.py).
* Tube principal : Ø intérieur 100 mm, axe horizontal (axe X dans le fichier final).
* Propane : entrée 3/8" (Ø 9,53 × 7,90) côté +X, arbre de Murray en 4 niveaux (7,90 → 6,27 → 4,98
  → 3,95 → 3,14 mm), 16 tubes droits sur une couronne, arbre de regroupement et sortie 3/8" côté −X.
  Les divisions sont des Y doux : chaque branche part dans l'axe puis s'écarte le long de la couronne.
* Air : entre tangentiellement côté −X (sortie du propane), tourne dans l'anneau entre le noyau et la
  paroi, sort tangentiellement côté +X : contre-courant.
* Pas encore d'ailettes.

Lancement (FreeCAD 1.1 en flatpak, sans interface ; /tmp n'est pas visible du flatpak) :
    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/echangeur_d100.py').read())"
Paramètres : outils/cad/parametres_d100.json (créé avec les valeurs par défaut s'il manque).
Sorties : docs/formes/cylindre_d100/ (.FCStd, .step, .stl par pièce, dimensions.json).

Variante 32 tubes en tournesol (niveau 5 de Murray, Ø int. 2,49 ; tubes placés selon l'angle d'or,
chacun à un rayon différent, voir outils/cad/tournesol.py) : définir VARIANTE avant l'exec,
    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "VARIANTE='t32'; exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/echangeur_d100.py').read())"
→ outils/cad/parametres_d100_t32.json, sorties dans docs/formes/cylindre_d100_t32/.
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

VARIANTE = globals().get("VARIANTE", "")
SUFFIXE = f"_{VARIANTE}" if VARIANTE else ""
F_PARAM = os.path.join(RACINE, f"outils/cad/parametres_d100{SUFFIXE}.json")
SORTIE = os.path.join(RACINE, f"docs/formes/cylindre_d100{SUFFIXE}")

DEFAUT = {
    "d_int_principal": 100.0,   # mm, Ø intérieur du tube principal (donné)
    "ep_principal": 2.0,        # mm, paroi du tube principal (hypothèse)
    "l_active": 300.0,          # mm, longueur de la zone d'échange (hypothèse)
    "plenum": 40.0,             # mm, chambre d'air à chaque bout, où arrivent les conduits (hypothèse)
    "ep_fond": 3.0,             # mm, épaisseur des fonds (hypothèse)
    "d_noyau": 30.0,            # mm, noyau central plein (hypothèse)
    "r_couronne": 32.5,         # mm, rayon de la couronne des 16 tubes (milieu de l'anneau d'air)
    "od_entree": 9.53,          # mm, tube d'entrée / sortie 3/8" (donné)
    "id_entree": 7.90,          # mm (donné)
    "id_murray": [7.90, 6.27, 4.98, 3.95, 3.14],  # mm, niveaux 0 à 4 (donné)
    "ep_branche": 0.5,          # mm, paroi des branches et des 16 tubes (hypothèse)
    "dz_niveau1": 25.0,         # mm, longueur axiale de la division axe → couronne
    "dz_niveaux": 12.0,         # mm, longueur axiale des divisions suivantes
    "garde_fond": 8.0,          # mm, tube droit entre le fond et la dernière division
    "l_tube_entree": 40.0,      # mm, longueur de tube 3/8" dessinée
    "conduit_larg": 20.0,       # mm, conduit d'air tangentiel, largeur radiale (hypothèse)
    "conduit_haut": 30.0,       # mm, hauteur (selon l'axe) (hypothèse)
    "conduit_long": 70.0,       # mm, longueur dessinée
    "disposition": "couronne",  # "couronne" (tous les tubes sur r_couronne) ou "tournesol" (dernier niveau)
    "r_tournesol": [19.0, 46.0],  # mm, rayons extrêmes des tubes en tournesol
    "dz_dernier": 20.0,         # mm, longueur axiale du dernier niveau en tournesol (décalage latéral ≤ 14 mm)
}
VARIANTES = {"t32": {"id_murray": [7.90, 6.27, 4.98, 3.95, 3.14, 2.49], "disposition": "tournesol"}}
DEFAUT.update(VARIANTES.get(VARIANTE, {}))


def parametres():
    if not os.path.exists(F_PARAM):
        with open(F_PARAM, "w") as f:
            json.dump(DEFAUT, f, indent=2)
    with open(F_PARAM) as f:
        return dict(DEFAUT, **json.load(f))


def lisse(t):
    return t * t * (3 - 2 * t)


def y_doux(t):
    """Progression avec une pente non nulle au départ (les deux filles s'écartent tout de suite,
    division en Y d'environ 30 à 45°) et nulle à l'arrivée (fin dans l'axe)."""
    return 0.5 * (1 - (1 - t) ** 2) + 0.5 * lisse(t)


def balayage(points, d):
    """Tube plein de diamètre d le long d'une courbe lisse passant par les points."""
    courbe = Part.BSplineCurve()
    courbe.interpolate(points)
    arete = courbe.toShape()
    t0 = arete.tangentAt(arete.FirstParameter)
    cercle = Part.Wire(Part.makeCircle(d / 2, points[0], t0))
    return Part.Wire(arete).makePipeShell([cercle], True, False)


def chemin(p, k, th_p, th_c, z_p, z_c, n=24):
    """Points d'une branche du niveau k : niveau 1 de l'axe vers la couronne (θ fixe),
    niveaux suivants le long de la couronne (θ glisse de θ_p à θ_c), départ et arrivée dans l'axe."""
    R = p["r_couronne"]
    pts = []
    for i in range(n + 1):
        t = i / n
        z = z_p + (z_c - z_p) * t
        if k == 1:
            r, th = R * y_doux(t), th_c
        else:
            r, th = R, th_p + (th_c - th_p) * y_doux(t)
        pts.append(V(r * math.cos(th), r * math.sin(th), z))
    return pts


def arbre(p, sens, z_feuilles):
    """Arbre 1 → 16. sens = +1 : l'arbre s'étend vers +z au-delà de z_feuilles (côté entrée).
    Renvoie (pièces extérieures, pièces intérieures, positions des 16 feuilles, z du tronc)."""
    ids = p["id_murray"]
    n = len(ids) - 1
    e = p["ep_branche"]
    od = lambda k: p["od_entree"] if k == 0 else ids[k] + 2 * e
    # z de chaque niveau : niveau n aux feuilles, puis on remonte vers le tronc
    tour = p["disposition"] == "tournesol"
    z = {n: z_feuilles}
    for k in range(n - 1, 0, -1):
        z[k] = z[k + 1] + sens * (p["dz_dernier"] if tour and k == n - 1 else p["dz_niveaux"])
    z[0] = z[1] + sens * p["dz_niveau1"]
    ext, intr = [], []
    noeuds = {(0, 0): 0.0}
    R = p["r_couronne"]
    paires = None
    for k in range(1, n + 1):
        if tour and k == n:
            # dernier niveau : deux tubes en tournesol par nœud du niveau précédent (sur la couronne)
            nd = [(R * math.cos(noeuds[(n - 1, j)]), R * math.sin(noeuds[(n - 1, j)])) for j in range(2 ** (n - 1))]
            paires, rot = tournesol.feuilles_tournesol(nd, *p["r_tournesol"])
            p["rotation_tournesol_deg"] = rot
            for b_i, b in enumerate(tournesol.branches(paires, nd, z[n - 1], z[n])):
                pts = [V(*q) for q in b["points"]]
                depart = 0.3 * od(k - 1)
                i0 = next(i for i, q in enumerate(pts) if (q - pts[0]).Length >= depart)
                ext.append(balayage(pts[i0:], od(k)))
                intr.append(balayage(pts[i0:], ids[k]))
        for j in range(2 ** k if not (tour and k == n) else 0):
            if k == 1:
                th_c = j * math.pi  # 0° et 180°
            else:
                th_p = noeuds[(k - 1, j // 2)]
                th_c = th_p + (-1 if j % 2 == 0 else 1) * math.pi / 2 ** k
            th_p = noeuds[(k - 1, j // 2)]
            noeuds[(k, j)] = th_c
            pts = chemin(p, k, th_p, th_c, z[k - 1], z[k])
            # départ décalé dans la sphère de jonction : évite des faces confondues entre sœurs
            # et avec l'arrivée du parent (cas dégénéré qui fait perdre des pièces aux booléens)
            depart = 0.3 * od(k - 1)
            i0 = next(i for i, q in enumerate(pts) if (q - pts[0]).Length >= depart)
            pts = pts[i0:]
            ext.append(balayage(pts, od(k)))
            intr.append(balayage(pts, ids[k]))
        # sphères aux divisions (diamètre du parent)
        for j in range(2 ** (k - 1)):
            th = noeuds[(k - 1, j)]
            r = 0.0 if k == 1 else p["r_couronne"]
            c = V(r * math.cos(th), r * math.sin(th), z[k - 1])
            # 4 % plus grosse que la branche qui arrive : à diamètre égal, le bout de la branche est un
            # grand cercle de la sphère (surfaces tangentes) et la fusion d'OpenCascade échoue sans erreur
            ext.append(Part.makeSphere(1.04 * od(k - 1) / 2, c))
            intr.append(Part.makeSphere(1.04 * ids[k - 1] / 2, c))
    # tube d'entrée / sortie 3/8" dans l'axe
    l = p["l_tube_entree"]
    ext.append(Part.makeCylinder(p["od_entree"] / 2, l, V(0, 0, z[0]), V(0, 0, sens)))
    intr.append(Part.makeCylinder(p["id_entree"] / 2, l + 1, V(0, 0, z[0]), V(0, 0, sens)))
    if paires:
        feuilles = [V(x, y, z_feuilles) for pr in paires for x, y in pr]
    else:
        feuilles = [V(R * math.cos(noeuds[(n, j)]), R * math.sin(noeuds[(n, j)]), z_feuilles) for j in range(2 ** n)]
    return ext, intr, feuilles, z[0]


def main():
    p = parametres()
    os.makedirs(SORTIE, exist_ok=True)
    L, P, ef = p["l_active"], p["plenum"], p["ep_fond"]
    ri = p["d_int_principal"] / 2
    z_fond_h, z_fond_b = L + P + ef, -P - ef          # faces extérieures des fonds
    z_f_h, z_f_b = z_fond_h + p["garde_fond"], z_fond_b - p["garde_fond"]

    ext_h, int_h, feuilles_h, z_tronc_h = arbre(p, +1, z_f_h)
    ext_b, int_b, feuilles_b, z_tronc_b = arbre(p, -1, z_f_b)
    od_t = p["id_murray"][-1] + 2 * p["ep_branche"]
    tubes_e = [Part.makeCylinder(od_t / 2, z_f_h - z_f_b, fb, V(0, 0, 1)) for fb in feuilles_b]
    tubes_i = [Part.makeCylinder(p["id_murray"][-1] / 2, z_f_h - z_f_b, fb, V(0, 0, 1)) for fb in feuilles_b]

    def fusion_sure(pieces, nom):
        """Fusion pièce par pièce (la fusion groupée échoue sur ces balayages), puis contrôle :
        chaque pièce doit être entièrement contenue dans le résultat ; sinon on la refusionne."""
        def ajout(acc, x):
            """Fusion contrôlée : OpenCascade renvoie parfois une forme vide ou amputée sans erreur.
            Essai normal, puis avec tolérance ; None si les deux échouent."""
            for tol in (None, 1e-4, 1e-3):
                try:
                    r = acc.fuse(x) if tol is None else acc.fuse([x], tol)
                except Exception:
                    continue
                if r.isNull() or not r.isValid():
                    continue
                # volume attendu de l'union : détecte une fusion qui ampute une partie sans erreur
                attendu = acc.Volume + x.Volume - x.common(acc).Volume
                if abs(r.Volume - attendu) <= 2e-3 * attendu:
                    return r
            return None

        def fusionner(ordre):
            acc, reste = ordre[0], list(ordre[1:])
            for passe in range(3):
                differees = []
                for x in reste:
                    r = ajout(acc, x)
                    if r is None:
                        differees.append(x)
                    else:
                        acc = r
                if differees:
                    print(f"[{nom}] passe {passe} : {len(differees)} fusion(s) différée(s)", flush=True)
                reste = differees
                if not reste:
                    break
            return acc, reste

        acc, reste = fusionner(list(pieces))
        if reste:
            # le résultat dépend de l'ordre : on recommence en partant des pièces récalcitrantes
            ids_reste = {id(x) for x in reste}
            print(f"[{nom}] nouvel ordre : {len(reste)} pièce(s) en tête", flush=True)
            acc, reste = fusionner(reste + [x for x in pieces if id(x) not in ids_reste])
        for essai in range(3):
            # perdue si la soustraction ET l'intersection le disent (une soustraction qui échoue
            # renvoie parfois la pièce entière alors qu'elle est bien dans le résultat)
            perdues = [k for k, x in enumerate(pieces)
                       if x.cut(acc).Volume > 0.01 * x.Volume and x.common(acc).Volume < 0.99 * x.Volume]
            if not perdues:
                break
            print(f"[{nom}] essai {essai} : pièces perdues {perdues}, refusion")
            for k in perdues:
                acc = ajout(acc, pieces[k]) or acc
        if perdues:
            raise RuntimeError(f"[{nom}] pièces toujours perdues après refusion : {perdues}")
        return acc

    def creux(ext, intr, nom):
        e = fusion_sure(ext, nom + " ext")
        try:
            i = fusion_sure(intr, nom + " int")
            c = e.cut(i)
        except RuntimeError as err:
            # repli : on creuse l'enveloppe canal par canal (pas de fusion des volumes intérieurs),
            # chaque soustraction contrôlée par son volume attendu ; le fluide = enveloppe − paroi
            print(f"[{nom}] {err} → creusement canal par canal", flush=True)
            c = e
            for k, x in enumerate(intr):
                attendu = c.Volume - x.common(c).Volume
                r = c.cut(x)
                if r.isNull() or not r.isValid() or abs(r.Volume - attendu) > 2e-3 * attendu:
                    raise RuntimeError(f"[{nom}] creusement du canal {k} incorrect")
                c = r
            i = e.cut(c)
        print(f"[{nom}] solides : ext {len(e.Solids)}, int {len(i.Solids)}, paroi {len(c.Solids)} ; "
              f"valides : {e.isValid()} {i.isValid()} {c.isValid()}")
        return c, i

    arbre_h, fluide_h = creux(ext_h, int_h, 'arbre entrée')
    arbre_b, fluide_b = creux(ext_b, int_b, 'arbre sortie')
    tubes, fluide_t = creux(tubes_e, tubes_i, 'tubes')

    # Tube principal avec fonds, noyau, conduits d'air tangentiels
    ep = p["ep_principal"]
    h_tot = z_fond_h - z_fond_b
    coque = Part.makeCylinder(ri + ep, h_tot, V(0, 0, z_fond_b))
    vide = Part.makeCylinder(ri, h_tot - 2 * ef, V(0, 0, z_fond_b + ef))
    w, hc, lc = p["conduit_larg"], p["conduit_haut"], p["conduit_long"]
    # Inclinaison des conduits vers l'avant (sens de l'air, +z) : l'air entre en hélice au lieu d'un
    # plan perpendiculaire à l'axe. Par défaut, angle de l'hélice que donne la conservation du débit :
    # tan α = section du conduit / section de l'anneau.
    a_conduit = p.get("angle_conduit_deg")
    if a_conduit is None:
        s_ann = math.pi * (ri ** 2 - (p["d_noyau"] / 2) ** 2) - len(feuilles_b) * math.pi * (od_t / 2) ** 2
        a_conduit = math.degrees(math.atan(w * hc / s_ann))
    p["angle_conduit_deg"] = round(a_conduit, 2)
    conduits = []
    for x0, xv, zc, signe in ((ri - w, ri - w, -P / 2, +1),        # entrée côté −z, vers +y
                              (-ri - ep, -ri, L + P / 2, -1)):     # sortie côté +z, vers −y
        ext = Part.makeBox(w + ep, lc, hc + 2 * ep, V(x0, -lc, zc - hc / 2 - ep))
        vid = Part.makeBox(w, lc + 1, hc, V(xv, -lc - 0.5, zc - hc / 2))
        for s in (ext, vid):  # pivot sur la génératrice de tangence (y = 0)
            s.rotate(V(0, 0, zc), V(1, 0, 0), signe * a_conduit)
        conduits.append((ext, vid))
    env = coque.fuse([c[0] for c in conduits]).cut(vide)
    for _, vid in conduits:
        env = env.cut(vid)
    env = env.cut(Part.makeCompound(tubes_e))  # passages des tubes dans les fonds
    noyau = Part.makeCylinder(p["d_noyau"] / 2, h_tot - 2 * ef, V(0, 0, z_fond_b + ef))

    pieces = {"enveloppe": env, "noyau": noyau, "tubes": tubes, "arbre_entree": arbre_h, "arbre_sortie": arbre_b}
    # Axe horizontal : z → x (entrée du propane côté +X)
    for s in list(pieces.values()) + [fluide_h, fluide_b, fluide_t]:
        s.rotate(V(0, 0, 0), V(0, 1, 0), 90)

    doc = App.newDocument("echangeur_d100")
    for nom, forme in pieces.items():
        doc.addObject("Part::Feature", nom).Shape = forme
        MeshPart.meshFromShape(Shape=forme, LinearDeflection=0.08, AngularDeflection=0.3).write(
            os.path.join(SORTIE, f"{nom}.stl"))
    doc.recompute()
    doc.saveAs(os.path.join(SORTIE, "echangeur_d100.FCStd"))
    Part.export(doc.Objects, os.path.join(SORTIE, "echangeur_d100.step"))

    # Dimensions et chiffres dérivés
    ids = p["id_murray"]
    e = p["ep_branche"]
    vol = lambda s: s.Volume / 1000.0  # cm³
    nt = len(feuilles_b)
    xy = [(q.x, q.y) for q in feuilles_b]
    rs = [math.hypot(*q) for q in xy]
    anneau = math.pi * (ri ** 2 - (p["d_noyau"] / 2) ** 2) - nt * math.pi * (od_t / 2) ** 2
    dim = {
        "parametres": p,
        "niveaux_murray": [{"niveau": k, "branches": 2 ** k, "id_mm": ids[k],
                            "od_mm": round(p["od_entree"] if k == 0 else ids[k] + 2 * e, 2),
                            "rapport_parent_enfant": round(ids[k - 1] / ids[k], 3) if k else None}
                           for k in range(len(ids))],
        "od_tubes_echange_mm": round(od_t, 2),
        "longueur_tubes_mm": round(z_f_h - z_f_b, 1),
        "n_tubes": nt,
        "feuilles_xy_mm": [[round(a, 2), round(b, 2)] for a, b in xy],
        "ecart_entre_tubes_mm": round(min(math.dist(a, b) for i, a in enumerate(xy) for b in xy[i + 1:]) - od_t, 2),
        "jeu_tube_paroi_mm": round(ri - max(rs) - od_t / 2, 2),
        "jeu_tube_noyau_mm": round(min(rs) - od_t / 2 - p["d_noyau"] / 2, 2),
        "longueur_arbre_mm": round(abs(z_tronc_h - z_f_h), 1),
        "encombrement_mm": {
            "longueur_hors_tout": round(z_tronc_h - z_tronc_b + 2 * p["l_tube_entree"], 1),
            "longueur_tube_principal": round(h_tot, 1),
            "diametre_exterieur": round(2 * (ri + ep), 1),
            "largeur_avec_conduits": round(ri + ep + lc, 1)},
        "section_air_anneau_cm2": round(anneau / 100, 1),
        "surface_ext_tubes_zone_active_m2": round(nt * math.pi * od_t * L * 1e-6, 4),
        "volume_interne_cm3": {"arbre_entree": round(vol(fluide_h), 2), "arbre_sortie": round(vol(fluide_b), 2),
                               "tubes": round(vol(fluide_t), 2)},
    }
    dim["volume_interne_cm3"]["total"] = round(sum(dim["volume_interne_cm3"].values()), 2)
    with open(os.path.join(SORTIE, "dimensions.json"), "w") as f:
        json.dump(dim, f, indent=2, ensure_ascii=False)
    print(json.dumps(dim, indent=2, ensure_ascii=False))


if not globals().get("SANS_MAIN"):
    main()
