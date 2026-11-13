"""STL du solide de la tranche CFD du secteur périodique de 1/8 (secteur_periodique.py), pour les 3 modèles :
  decale4   lamelles décalées (couronnes de 5 mm, espace radial 4 mm)
  continu   lamelles continues (r 35 → 73 mm à chaque pas)
  radiales  lamelles continues + lamelles radiales (7 + 7 intercalaires par secteur), profils recentrés sur les radiales

Tranche périodique de 2 pas (5 mm) le long du tube : lamelles à y = −0,5 + i·pas (+ demi-pas une couronne sur deux pour
decale4) → les faces y = 0 et y = 5 mm coupent une famille de lamelles en leur milieu et passent à 0,75 mm de l'autre.
En angle, le solide déborde de 4° de chaque côté du secteur (profils et lamelles des secteurs voisins compris) : le
maillage le coupe sur les faces périodiques en rotation. Écrit en mm dans cfd_campagne/secteur/geometrie/.

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/stl_secteur.py').read())"
"""
import json
import math
import os

SANS_MAIN_SECTEUR = True
exec(open("/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/secteur_periodique.py").read())

# configuration : SUFFIXE et S_MODIF peuvent être définis avant l'exec (ex. « _p5 » : une lamelle sur deux)
SUFFIXE = globals().get("SUFFIXE", "_p6")
S.update(globals().get("S_MODIF", {}))
P.update(globals().get("P_MODIF", {}))            # ex. {"ep_lamelle": 0.5}
# période de la tranche le long du tube : un pas, sauf avec les intercalaires (une lamelle sur deux près du noyau) : deux pas
PERIODE = 2 * S["pas_lamelles"] if S["intercalaires"] else S["pas_lamelles"]
DOSSIER_G = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/cfd_campagne/secteur/geometrie"
Y_BANDE = (-1.0, PERIODE + 1.0)
DEBORD = 4.0


def solide_secteur(modele):
    re, rn = P["r_ext"], P["r_noyau"]
    a0, a1 = P["secteur_deg"]
    ns = int(S["n_secteurs"])
    da = (a1 - a0) / ns
    js = ns // 2
    f0, f1 = a0 + js * da, a0 + (js + 1) * da
    rc = P["d_canal"] / 2
    b_prof = rc + P["paroi"]
    pos = tournesol_secteur(0.0, da, rn, re, b_prof)
    if modele == "radiales":
        d_rad = da / S["n_radiales"]
        def angle_rad(r, a):
            cand = [(k + 0.5) * d_rad for k in range(int(S["n_radiales"]))]
            if S["radiales_inter"] and r - P["profil_long"] / 2 >= S["r_radiales_inter"]:
                cand += [k * d_rad for k in range(int(S["n_radiales"]) + 1)]
            return min(cand, key=lambda x: abs(x - a))
        pos = [(r, angle_rad(r, a)) for r, a in pos]
    morceaux = []
    for j in (js - 1, js, js + 1):                     # profils pleins (le canal est dans le solide)
        for r, a in pos:
            aa = a0 + j * da + a
            morceaux.append(dans_plan_y(ellipse(r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa)),
                                                P["profil_long"] / 2, b_prof, aa), Y_BANDE[0], Y_BANDE[1] - Y_BANDE[0]))
    t, jeu, lc = P["ep_lamelle"], P["jeu"], P["l_troncon"]
    pas = S["pas_lamelles"]
    g0, g1 = f0 - DEBORD, f1 + DEBORD

    def plaques(r_in, r_out, dec, inter):
        cs = faces_lamelle(r_in, r_out, g0, g1, 0.5)
        for i in range(-2, 4):
            # par défaut une famille est coupée en son milieu par les faces périodiques ; « phase_y » place au contraire
            # toutes les lamelles à distance des faces (lamelles minces : une demi-lamelle de 0,25 mm sur une face
            # périodique fausse l'interpolation AMI — bilan de chaleur à 33 % le 13/11)
            y = S.get("phase_y", -t / 2) + dec + i * pas
            if y + t < Y_BANDE[0] or y > Y_BANDE[1]:
                continue
            if inter and i % 2 == 1:
                continue
            morceaux.extend(dans_plan_y(c, y, t) for c in cs)
    if modele == "decale4" and S.get("forme_lamelles") == "vague":
        # ailettes en vague (14/11) : ligne moyenne au milieu de la lamelle « phase_y » ; une ailette occupe
        # [y, y + pas/2 + t] : les faces périodiques restent dans la bande libre, comme pour les lamelles décalées
        for i in range(-2, 4):
            yc = S.get("phase_y", -t / 2) + t / 2 + i * pas
            if yc + pas / 2 + t / 2 < Y_BANDE[0] or yc - t / 2 > Y_BANDE[1]:
                continue
            morceaux.append(vague(rn, re, g0, g1, yc))
    elif modele == "decale4":
        for r_in, r_out, fam in troncons(rn, re):
            plaques(r_in, r_out, fam * pas / 2, S["intercalaires"] and r_out <= P["r_intercalaire"])
    else:
        plaques(rn, re, 0.0, False)
    if modele == "radiales":
        rad = lamelles_radiales(f0 - da, f1 + da, rn, re, Y_BANDE[1] - Y_BANDE[0], 3, Y_BANDE[0],
                                exclusions=couloirs(f0 - 2 * da, pos, 5, da))
        morceaux += rad
        # contrôle : distance mini entre le bord d'un profil et une lamelle radiale qui ne le porte pas (doit être ≥ 1,5 mm)
        dmin = 1e9
        for jj in (js - 1, js, js + 1):
            for r, a in pos:
                aa = a0 + jj * da + a
                e = dans_plan_y(ellipse(r * math.cos(math.radians(aa)), r * math.sin(math.radians(aa)), P["profil_long"] / 2, b_prof, aa), 0, 1)
                for q in rad:
                    if e.common(q).Volume > 1e-6:
                        continue
                    dmin = min(dmin, e.distToShape(q)[0])
        print(f"[{modele}] distance mini profil ↔ lamelle radiale voisine : {dmin:.2f} mm", flush=True)
    s = morceaux[0].fuse(morceaux[1:]).removeSplitter()
    if len(s.Solids) > 1:
        # morceaux isolés : doivent tous être hors du secteur calculé (profils des secteurs voisins hors de la bande de débord)
        sol = list(s.Solids)
        ip = max(range(len(sol)), key=lambda i: sol[i].Volume)
        princ = sol[ip]
        gardes = []
        for i, x in enumerate(sol):
            if i == ip:
                continue
            cm = x.CenterOfMass
            phi = math.degrees(math.atan2(cm.z, cm.x))
            dedans = f0 - 1.0 < phi < f1 + 1.0
            if dedans and S.get("garder_morceaux_dans_secteur"):
                # lamelles avec stries (14/11) : la dent du bord du secteur est reliée au reste de la pièce par un profil du
                # secteur voisin, hors de la bande modélisée ; parois à température imposée : on la garde dans le solide CFD
                gardes.append(x)
                print(f"[{modele}] morceau séparé GARDÉ à φ = {phi:.1f}°, r = {math.hypot(cm.x, cm.z):.1f} mm, {x.Volume:.2f} mm³ (relié hors de la bande)", flush=True)
                continue
            print(f"[{modele}] morceau isolé retiré à φ = {phi:.1f}°, r = {math.hypot(cm.x, cm.z):.1f} mm, y = {cm.y:.2f}, {x.Volume:.2f} mm³ ({'DANS LE SECTEUR : ERREUR' if dedans else 'hors du secteur'})", flush=True)
        s = Part.makeCompound([princ] + gardes) if gardes else princ
    return s, dict(secteur_deg=[f0, f1], angle_deg=da, profils=pos)


os.makedirs(DOSSIER_G, exist_ok=True)
F_GEO = os.path.join(DOSSIER_G, "geometrie.json")
anc = json.load(open(F_GEO)) if os.path.exists(F_GEO) else {}
info = anc.get("modeles", {})
for m0 in globals().get("MODELES", ("decale4", "continu", "radiales")):
    m = m0 + SUFFIXE
    s, inf = solide_secteur(m0)
    print(f"[{m}] valide {s.isValid()}, solides {len(s.Solids)}, fermé {all(x.isClosed() for x in s.Shells)}, volume {s.Volume / 1e3:.2f} cm³", flush=True)
    MeshPart.meshFromShape(Shape=s, LinearDeflection=0.02, AngularDeflection=0.2).write(os.path.join(DOSSIER_G, f"solide_{m}.stl"))
    info[m] = dict(inf, solides=len(s.Solids), volume_mm3=s.Volume, secteur_parametres=dict(S), periode_mm=PERIODE)
with open(F_GEO, "w") as f:
    json.dump(dict(parametres=P, secteur=S, periode_mm=PERIODE, modeles=info), f, indent=1, ensure_ascii=False)
