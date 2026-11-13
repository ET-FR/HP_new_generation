"""STL du solide de la tranche périodique de CFD 3D du concept imprimé (concept_imprime.py), versions sans et avec stries.

Tranche de 2 pas de lamelles (5 mm) le long du tube, périodique. Lamelles à y = Y0 + i·pas (+ demi-pas une couronne
sur deux) ; Y0 = −0,5 mm : les faces périodiques (y = 0 et y = 5 mm) coupent les lamelles des couronnes paires en plein
milieu de leur épaisseur, et les lamelles des couronnes impaires en sont à 0,75 mm (aucun passage plus mince qu'une maille
entre une lamelle et une face périodique : sinon le maillage le bouche d'un côté seulement). Sous r_intercalaire, une
lamelle sur deux (i pair seulement). Les profils (pleins : le canal de
propane est dans le solide) traversent toute la tranche et dépassent de 1 mm de chaque côté (coupés par le maillage).
Le solide est fusionné en une seule pièce et écrit en mm dans cfd_campagne/concept_imprime/geometrie/.

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/stl_concept_imprime.py').read())"
"""
import json
import math
import os

SANS_MAIN = True
exec(open("/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/concept_imprime.py").read())

DOSSIER = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/cfd_campagne/concept_imprime/geometrie"
PERIODE = 2                      # pas de lamelles dans la tranche
Y0 = -0.5                        # les faces périodiques coupent les lamelles paires en leur milieu


def solide(stries, decale=True, espace=0.0):
    """decale : couronnes décalées d'un demi-pas (sinon lamelles continues, sans coupure) ;
    espace : espace radial libre entre deux couronnes (mm), pour que l'air se redistribue."""
    re, rn = P["r_ext"], P["r_noyau"]
    a0, a1 = P["secteur_deg"]
    rc = P["d_canal"] / 2
    b_prof = rc + P["paroi"]
    lam_face = contour_lamelle(stries, rn, re, a0, a1)
    acceptes = placer_profils(lam_face, rn, re, a0, a1, b_prof)
    t, jeu, lc = P["ep_lamelle"], P["jeu"], P["l_troncon"]
    pas = t + jeu
    morceaux = [dans_plan_y(e, -1.0, PERIODE * pas + 2.0) for e, _, _ in acceptes]
    if not decale:
        lc, espace = re - rn, 0.0               # une seule « couronne » : lamelle continue de r_noyau à r_ext
    k, r_in = 0, rn
    while r_in < re - 0.5:
        r_out = min(r_in + lc, re)
        couronne = secteur(r_in, r_out, a0, a1, pas=1.0)
        if stries:
            couronne = couronne.common(lam_face)
        if couronne.Area > 1e-3:
            for i in range(-1, PERIODE + 2):
                y = Y0 + (k % 2) * pas / 2 * decale + i * pas
                if y + t < -1.0 or y > PERIODE * pas + 1.0:          # hors de la bande −1 … période + 1 mm
                    continue
                if r_out <= P["r_intercalaire"] and i % 2 == 1:
                    continue
                morceaux.append(dans_plan_y(couronne, y, t))
        r_in = r_out + espace
        k += 1
    if not decale and P["r_intercalaire"] > rn:
        # lamelles continues : la lamelle sur deux supprimée près du noyau est coupée à r_intercalaire
        pass
    if stries:
        # âme radiale de 1 mm dans chaque dent (alignée avec l'air) : relie les tronçons décalés de la dent à l'anneau
        nd, rcr = int(P["n_dents"]), P["r_creux"]
        for i in range(nd + 1):
            ang = a0 + 2 * i * (a1 - a0) / (2 * nd)
            c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            r0_, r1_, e = rcr - 6.0, re - 1.0, t / 2
            # aux deux bouts du secteur, l'âme est décalée vers l'intérieur de la demi-dent
            d = 0.0 if 0 < i < nd else (e if i == 0 else -e)
            n_ = (-s_, c)
            q = lambda r, sg: V(r * c + (d + sg * e) * n_[0], r * s_ + (d + sg * e) * n_[1], 0)
            ame = Part.Face(Part.makePolygon([q(r0_, -1), q(r1_, -1), q(r1_, 1), q(r0_, 1), q(r0_, -1)])).common(lam_face)
            morceaux.append(dans_plan_y(ame, -1.0, PERIODE * pas + 2.0))
    s = morceaux[0].fuse(morceaux[1:]).removeSplitter()
    if len(s.Solids) > 1 and not stries:
        print(f"ATTENTION : {len(s.Solids)} morceaux séparés (couronnes non reliées à un profil) : "
              f"{[round(x.Volume, 1) for x in sorted(s.Solids, key=lambda x: x.Volume)[:-1]]} mm³", flush=True)
    if len(s.Solids) > 1 and stries:  # demi-dents isolées aux bouts du secteur : supprimées, rien ne les relie au propane
        print(f"[{'avec' if stries else 'sans'}] morceaux isolés supprimés : "
              f"{[round(x.Volume, 1) for x in sorted(s.Solids, key=lambda x: x.Volume)[:-1]]} mm³", flush=True)
        s = max(s.Solids, key=lambda x: x.Volume)
    return s, [(r, a) for _, _, (r, a) in acceptes], pas


VERSIONS = {          # clé : (stries, décalées, espace radial entre couronnes en mm)
    "continu": (False, False, 0.0),
    "decale4": (False, True, 4.0),
}
os.makedirs(DOSSIER, exist_ok=True)
F_GEO = os.path.join(DOSSIER, "geometrie.json")
anc = json.load(open(F_GEO)) if os.path.exists(F_GEO) else {}
info = anc.get("versions", {})
for cle, (stries, decale, espace) in VERSIONS.items():
    s, centres, pas = solide(stries, decale, espace)
    print(f"[{cle}] valide {s.isValid()}, solides {len(s.Solids)}, fermé {all(x.isClosed() for x in s.Shells)}, "
          f"volume {s.Volume / 1e3:.2f} cm³", flush=True)
    MeshPart.meshFromShape(Shape=s, LinearDeflection=0.02, AngularDeflection=0.2).write(os.path.join(DOSSIER, f"solide_{cle}.stl"))
    info[cle] = {"solides": len(s.Solids), "volume_mm3": s.Volume, "aire_mm2": s.Area, "centres_profils": centres,
                 "stries": stries, "decale": decale, "espace_radial_mm": espace}
with open(F_GEO, "w") as f:
    json.dump(dict(parametres=P, periode_mm=PERIODE * pas, y0=Y0, versions=info), f, indent=1, ensure_ascii=False)
