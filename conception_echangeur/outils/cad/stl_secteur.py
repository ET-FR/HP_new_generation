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
PERIODE = S["pas_lamelles"] if S["pas_lamelles"] >= 5.0 else 2 * S["pas_lamelles"]   # période de la tranche le long du tube
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
        c = secteur(r_in, r_out, g0, g1, pas=0.5)
        for i in range(-2, 4):
            y = -0.5 + dec + i * pas
            if y + t < Y_BANDE[0] or y > Y_BANDE[1]:
                continue
            if inter and i % 2 == 1:
                continue
            morceaux.append(dans_plan_y(c, y, t))
    if modele == "decale4":
        k, r_in = 0, rn
        while r_in < re - 0.5:
            r_out = min(r_in + lc, re)
            plaques(r_in, r_out, (k % 2) * pas / 2, S["intercalaires"] and r_out <= P["r_intercalaire"])
            r_in = r_out + S["espace_radial"]
            k += 1
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
        for i, x in enumerate(sol):
            if i == ip:
                continue
            cm = x.CenterOfMass
            phi = math.degrees(math.atan2(cm.z, cm.x))
            dedans = f0 - 1.0 < phi < f1 + 1.0
            print(f"[{modele}] morceau isolé retiré à φ = {phi:.1f}° ({'DANS LE SECTEUR : ERREUR' if dedans else 'hors du secteur'})", flush=True)
        s = princ
    return s, dict(secteur_deg=[f0, f1], angle_deg=da, profils=pos)


os.makedirs(DOSSIER_G, exist_ok=True)
F_GEO = os.path.join(DOSSIER_G, "geometrie.json")
anc = json.load(open(F_GEO)) if os.path.exists(F_GEO) else {}
info = anc.get("modeles", {})
for m0 in ("decale4", "continu", "radiales"):
    m = m0 + SUFFIXE
    s, inf = solide_secteur(m0)
    print(f"[{m}] valide {s.isValid()}, solides {len(s.Solids)}, fermé {all(x.isClosed() for x in s.Shells)}, volume {s.Volume / 1e3:.2f} cm³", flush=True)
    MeshPart.meshFromShape(Shape=s, LinearDeflection=0.02, AngularDeflection=0.2).write(os.path.join(DOSSIER_G, f"solide_{m}.stl"))
    info[m] = dict(inf, solides=len(s.Solids), volume_mm3=s.Volume, secteur_parametres=dict(S), periode_mm=PERIODE)
with open(F_GEO, "w") as f:
    json.dump(dict(parametres=P, secteur=S, periode_mm=PERIODE, modeles=info), f, indent=1, ensure_ascii=False)
