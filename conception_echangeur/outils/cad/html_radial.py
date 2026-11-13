"""Page HTML 3D de l'échangeur cylindrique à flux radial, variante A′ (echangeur_radial.py).

Lit les STL et dimensions.json de docs/formes/cylindre_radial/ et écrit echangeur_radial.html à côté
(Three.js, rotation libre, pièces activables, plan de coupe déplaçable le long de l'axe).

    .venv/bin/python conception_echangeur/outils/cad/html_radial.py
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

RACINE_CE = Path(__file__).resolve().parents[2]
D = RACINE_CE / "docs/formes/cylindre_radial"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "croquis"))
import croquis_radial  # noqa: E402
DE = D / "variante_e"
PIECES_E = [  # nom (fichier STL), titre, couleur, opacité
    ("tubes_web", "Tubes de réfrigérant (tournesol)", "#d9480f", 1.0),
    ("filtre", "Manchon filtrant", "#f08c00", 0.25),
    ("plenum", "Parois du plénum", "#868e96", 0.45),
    ("plaque", "Plaque arrière (contre la vitre)", "#adb5bd", 0.3),
    ("socle", "Socle (châssis)", "#5c7cfa", 0.55),
    ("ventilateur", "Ventilateur axial", "#343a40", 1.0),
    ("volet", "Volet (lames)", "#e03131", 0.8),
]
DF = D / "variante_f"
PIECES_F = [
    ("tubes_web", "Tubes de réfrigérant (tournesol)", "#d9480f", 1.0),
    ("filtre", "Manchon filtrant", "#f08c00", 0.25),
    ("plenum", "Paroi du plénum", "#868e96", 0.45),
    ("flasques", "Flasques de bout", "#adb5bd", 0.3),
    ("plaque", "Plaque arrière (contre la vitre)", "#adb5bd", 0.3),
    ("socle", "Socle (châssis)", "#5c7cfa", 0.55),
    ("ventilateurs", "Ventilateurs axiaux", "#343a40", 1.0),
    ("volet", "Volet (lames)", "#e03131", 0.8),
]
PIECES_FL = [
    ("tranche_lamelles_web", "Lamelles (0,12 mm au pas de 1,2 mm)", "#74c0fc", 1.0),
    ("tranche_tubes", "Tubes de réfrigérant", "#d9480f", 1.0),
    ("tranche_filtre", "Manchon filtrant", "#f08c00", 0.3),
    ("tranche_plenum", "Paroi du plénum", "#868e96", 0.6),
    ("tranche_socle", "Socle", "#5c7cfa", 0.55),
    ("tranche_plaque", "Plaque arrière", "#adb5bd", 0.3),
]
PIECES_FP = [
    ("plis_lamelles_web", "Lamelles en zigzag (galette plissée)", "#74c0fc", 1.0),
    ("plis_tubes", "Tubes de réfrigérant (2 par flanc)", "#d9480f", 1.0),
    ("plis_filtre", "Manchon filtrant", "#f08c00", 0.3),
    ("plis_plenum", "Paroi du plénum", "#868e96", 0.6),
    ("plis_socle", "Socle", "#5c7cfa", 0.55),
    ("plis_plaque", "Plaque arrière", "#adb5bd", 0.3),
]
DI = DF / "imprime"
PIECES_FI = [
    ("imp_sans_lamelles_web", "Sans stries : lamelles décalées", "#74c0fc", 1.0),
    ("imp_sans_profils", "Sans stries : profils porteurs de propane", "#495057", 1.0),
    ("imp_sans_propane", "Sans stries : canaux de propane", "#e8590c", 1.0),
    ("imp_sans_filtre", "Sans stries : filtre", "#f08c00", 0.25),
    ("imp_avec_lamelles_web", "Avec stries : lamelles décalées", "#4dabf7", 1.0),
    ("imp_avec_profils", "Avec stries : profils porteurs de propane", "#343a40", 1.0),
    ("imp_avec_propane", "Avec stries : canaux de propane", "#d9480f", 1.0),
    ("imp_avec_filtre", "Avec stries : filtre", "#f08c00", 0.25),
]
PIECES = [  # nom, titre, couleur, opacité
    ("galette", "Échangeur plissé (galette, sans tubes)", "#40c057", 1.0),
    ("filtre", "Manchon filtrant", "#f08c00", 0.35),
    ("cloisons", "Cloisons de la gorge", "#495057", 1.0),
    ("volute", "Volute", "#868e96", 0.45),
    ("flasques", "Flasques de bout", "#adb5bd", 0.3),
    ("ventilateurs", "Ventilateurs (de principe)", "#343a40", 1.0),
]


def stl_b64(nom, dossier=D):
    m = pv.read(dossier / f"{nom}.stl").triangulate()
    tri = m.points[m.faces.reshape(-1, 4)[:, 1:]].astype(np.float32).reshape(-1)
    return base64.b64encode(tri.tobytes()).decode()


def jpeg_b64(chemin, largeur=1000):
    """Image compressée en JPEG pour l'insérer dans la page."""
    import io
    from PIL import Image
    im = Image.open(chemin).convert("RGB")
    if im.width > largeur:
        im = im.resize((largeur, round(im.height * largeur / im.width)))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82)
    return base64.b64encode(b.getvalue()).decode()


def maillages_json():
    """Coupes du maillage (html_maillage_concept.py) des deux versions, pour la visionneuse du document."""
    dc = DI / "cfd"
    m = {v: json.loads((dc / f"maillage_3d_{v}.json").read_text()) for v in ("sans", "avec") if (dc / f"maillage_3d_{v}.json").exists()}
    return json.dumps(m)


def resultats_3d_json(cles=("continu", "decale4", "sans", "avec"), geo_dossier="concept_imprime", geo_cle=None):
    """Grilles de champs (grille_resultats_concept.py) + solide de la tranche, par cas, pour la vue 3D des résultats."""
    import gzip
    dc = DI / "cfd"
    geo = RACINE_CE / f"cfd_campagne/{geo_dossier}/geometrie"
    out = {}
    for k in cles:
        fg = dc / f"grille_{k}.json"
        if not fg.exists():
            continue
        g = json.loads(fg.read_text())
        s = pv.read(geo / f"solide_{(geo_cle or (lambda x: x))(k)}.stl").triangulate().clip_box([-200, 200, 0, max(5.0, g["origine_mm"][1] + (g["dim"][1] - 1) * g["pas_mm"]), -200, 200],
                                                                                          invert=False).triangulate()
        if s.n_cells > 90000:
            s = s.decimate(1 - 90000 / s.n_cells)
        tri = s.points[s.faces.reshape(-1, 4)[:, 1:]].reshape(-1, 3).astype(np.float64)
        o = tri.min(axis=0)
        sc = float((tri.max(axis=0) - o).max() / 65000)
        q = np.round((tri - o) / sc).astype("<u2")
        g["solide"] = dict(gz=base64.b64encode(gzip.compress(q.tobytes(), 6)).decode(), o=o.tolist(), s=sc)
        out[k] = g
    return json.dumps(out)


def bloc_secteur():
    """Section « Secteur périodique 1/8 » (secteur_periodique.py) : texte + emplacement de la vue 3D."""
    fs = DI / "secteur" / "secteur_e5.json"
    if not fs.exists():
        return "", []
    s = json.loads(fs.read_text())
    dS = DI / "secteur"
    ECARTS = [("_e15", "écart 1,5 mm"), ("_c15", "écart 1,5 mm corrigé"), ("_e4", "écart 4 mm"), ("_e5", "écart 5 mm"),
              ("_f05", "lamelles 0,5 mm, espace radial 1,5 mm"),
              ("_f05i", "lamelles 0,5 mm IMBRIQUÉES à moitié (14/11)"), ("_f05v", "ailettes 0,5 mm EN VAGUE (14/11)"),
              ("_f05s", "lamelles 0,5 mm décalées AVEC DENTS (14/11)")]
    TITRES_LAM = {"_f05i": "Secteur simulé : lamelles imbriquées (chaque couronne recouvre la moitié de ses deux voisines décalées)",
                  "_f05v": "Secteur simulé : ailettes en vague (couronnes décalées reliées par des pentes)",
                  "_f05s": "Secteur simulé : lamelles décalées à bord extérieur en dents triangulaires (une dent par secteur)"}
    MODS = [("dec", "Décalées"), ("cont", "Continues"), ("rad", "Continues + radiales")]
    obj = []

    def ajoute(nom, titre, coul, op, onglets):
        if onglets is not None:
            onglets = [o for o in onglets if o != "__aucun__"]
            if not onglets:
                return
        if (dS / f"{nom}.stl").exists():
            obj.append(dict(nom=nom, titre=titre, couleur=coul, opacite=op, onglet=onglets, **stl_gz(nom, dS)))
    for e, ne in ECARTS:
        og = {m: f"{nm} · {ne}" for m, nm in MODS}
        if e == "_c15":
            og["dec"] = og["cont"] = "__aucun__"
        if e in ("_f05", "_f05i", "_f05v", "_f05s"):
            og["cont"] = og["rad"] = "__aucun__"
        if e in ("_f05i", "_f05v", "_f05s"):
            og["dec"] = {"_f05i": "Imbriquées", "_f05v": "Vague", "_f05s": "Décalées avec dents"}[e] + " · lamelles 0,5 mm, espace radial 1,5 mm"
        ajoute(f"sect_lamelles{e}", TITRES_LAM.get(e, "Secteur simulé : lamelles décalées (couronnes de 5 mm, espace radial 4 mm)"), "#1c7ed6", 1.0, [og["dec"]])
        ajoute(f"tout_lamelles{e}", "Reste de l'échangeur : lamelles décalées", "#a5d8ff", 0.2, [og["dec"]])
        ajoute(f"sect_cont_lamelles{e}", "Secteur simulé : lamelles continues (r 35 → 73 mm)", "#1c7ed6", 1.0, [x for x in (og["cont"], og["rad"]) if x != "__aucun__"])
        ajoute(f"tout_cont_lamelles{e}", "Reste de l'échangeur : lamelles continues", "#a5d8ff", 0.2, [x for x in (og["cont"], og["rad"]) if x != "__aucun__"])
        ajoute(f"sect_profils{e}", "Secteur simulé : 4 profils de propane", "#343a40", 1.0, [og["dec"], og["cont"]])
        ajoute(f"sect_canaux{e}", "Secteur simulé : canaux de propane", "#e8590c", 1.0, [og["dec"], og["cont"]])
        ajoute(f"tout_profils{e}", "Reste de l'échangeur : profils", "#adb5bd", 0.35, [og["dec"], og["cont"]])
        ajoute(f"sect_rad_lamelles{e}", "Secteur simulé : lamelles radiales", "#7048e8", 1.0, [og["rad"]])
        ajoute(f"tout_rad_lamelles{e}", "Reste de l'échangeur : lamelles radiales", "#d0bfff", 0.2, [og["rad"]])
        ajoute(f"sect_rad_profils{e}", "Secteur simulé : 4 profils, centrés sur une lamelle radiale", "#343a40", 1.0, [og["rad"]])
        ajoute(f"sect_rad_canaux{e}", "Secteur simulé : canaux de propane", "#e8590c", 1.0, [og["rad"]])
        ajoute(f"tout_rad_profils{e}", "Reste de l'échangeur : profils", "#adb5bd", 0.35, [og["rad"]])
    for nom, titre, coul, op in (("sect_periodiques_e5", "Faces périodiques en rotation (côtés du secteur)", "#2f9e44", 0.35),
                                 ("sect_entree_e5", "Entrée d'air (r = 77 mm)", "#4dabf7", 0.3),
                                 ("sect_sortie_e5", "Sortie vers le noyau (r = 33 mm)", "#e03131", 0.35)):
        ajoute(nom, titre, coul, op, None)
    s = json.loads((dS / "secteur_e5.json").read_text()) if (dS / "secteur_e5.json").exists() else s
    prof = ", ".join(f"r = {f(r)} mm" for r, a in s["profils"])
    html = f"""<h3 id=secteur-periodique>Secteur périodique de 1/8 pour les études (13/11)</h3>
<p class=aide>Pour aller 8 fois plus vite, l'échangeur (secteur d'échange de 230°) est découpé en <b>{s['n_secteurs']} secteurs identiques de
{f(s['angle_secteur_deg'], 2)}°</b>, chacun avec <b>{s['tubes_par_secteur']} profils de propane</b> (8 × 4 = 32 circuits). La CFD ne calcule qu'un secteur (en
couleur) : ses deux côtés sont des faces périodiques en rotation (vertes), et la tranche reste périodique le long du tube. Environ
250 000 mailles au lieu de 2 millions : quelques minutes par cas, ce qui permet de balayer les paramètres (espace entre couronnes,
longueur des tronçons, jeu, rayon du noyau, position des profils). Le reste de l'échangeur est montré en transparence.</p>
<p class=aide><b>Sélecteur « Modèle »</b> : 3 modèles × 3 écarts entre lamelles (lamelles de 1 mm).
<b>Décalées</b> : couronnes de 5 mm décalées d'un demi-pas, 4 mm libres entre deux couronnes. <b>Continues</b> : lamelles pleines de
r = 35 à 73 mm. <b>Continues + radiales</b> : en plus, des lamelles perpendiculaires qui contiennent l'axe (alignées avec l'air), chaque
profil étant centré sur l'une d'elles.
<b>Écart 1,5 mm</b> (pas 2,5 mm, première version) : une lamelle sur deux supprimée près du noyau ; 7 lamelles radiales par secteur
+ 7 intercalaires (à partir de r = 54 mm) ; défaut de cette version radiale : les profils touchent presque les radiales voisines (fentes).
<b>Lamelles 0,5 mm, espace radial 1,5 mm</b> (lamelles décalées seulement, 13/11) : lamelles de 0,5 mm au pas de 2,5 mm (jeu de 2 mm),
couronnes de 5 mm séparées de 1,5 mm ; les 4 profils sont répartis régulièrement sur la profondeur (r = 40,5 à 67 mm) pour que
chacune des 6 couronnes touche un profil.
<b>Imbriquées</b> (14/11, dessin 2 de l'utilisateur) : mêmes lamelles de 0,5 mm au pas de 2,5 mm, mais chaque rangée porte des
couronnes de 5 mm séparées de 1,5 mm, et la rangée décalée d'un demi-pas est aussi décalée d'une demi-couronne : chaque lamelle recouvre la
moitié des deux lamelles voisines de l'autre rangée (13 couronnes au lieu de 6, deux fois plus de surface). Là où elles se recouvrent, il ne
reste que 0,75 mm entre deux lamelles (pas/2 − épaisseur) : plus d'échange, mais plus de Δp, et un jeu inférieur aux 1,5 mm de dépoudrage.
<b>Vague</b> (14/11, dessin 3) : les couronnes décalées sont reliées en une seule ailette ondulée : paliers de 5 mm alternativement à y et
y + 1,25 mm, raccordés dans les espaces de 1,5 mm par des demi-cosinus (pente maxi ≈ 53°), épaisseur de 0,5 mm mesurée
perpendiculairement à la tôle ; le canal entre deux ailettes garde 2 mm de haut partout, il ondule avec elles.
<b>Décalées avec dents</b> (14/11) : les lamelles décalées de 0,5 mm, avec le bord extérieur en dents triangulaires du concept
« avec stries » (8 dents sur 230°, une par secteur, pointes sur les faces périodiques, rainures en V jusqu'à r = 58 mm) : l'air
entre plus profond par les rainures, le bord d'attaque des lamelles est plus long. Les deux profils extérieurs sont recalés dans
les dents (r = 58,2 mm : φ 8,7 → 7,8° ; r = 67 mm : φ 22,4 → 28,6°, centré sur la dent du bord). Moins de surface de lamelles que les
décalées sans dents (volume du solide 1,65 contre 1,73 cm³).
<b>Écart 1,5 mm corrigé</b> (modèle radial seulement) : même géométrie, mais les lamelles radiales sont coupées à 1,5 mm des profils
(plus de fente). <b>Écart 4 mm</b> (pas 5 mm) : pas d'intercalaires ; 7 radiales par secteur, coupées à 1,5 mm des profils.
<b>Écart 5 mm</b> (pas 6 mm, demande du 13/11) : pas d'intercalaires ; 3 radiales par secteur (5 mm d'écart au bord du noyau,
≈ 11 mm à l'extérieur), coupées à 1,5 mm des profils. Les profils, les frontières du calcul et le secteur sont les mêmes partout.</p>
<p class=aide><b>Position des profils.</b> Avec des lamelles de 1 mm, le rendement d'ailette est d'environ 0,97 quelle que soit la
position des tubes : la répartition « tournesol » (faite pour raccourcir le chemin de la chaleur dans des lamelles minces) n'apporte
plus rien thermiquement. En revanche, avec des couronnes séparées par des espaces, chaque couronne doit toucher un profil, sinon elle
flotte (et ne reçoit pas de chaleur) : le tournesol à aire égale laissait la couronne extérieure sans profil. Les profils sont donc
placés <b>au milieu de chaque espace entre couronnes</b> ({prof}), chacun reliant deux couronnes, et décalés en angle au pas d'or (quinconce)
pour ne pas être dans le sillage les uns des autres. Entraxe mini {f(s['entraxe_mini_mm'], 1)} mm (secteurs voisins compris). Secteur d'une
seule pièce (vérifié). À comparer en CFD : profils en quinconce ou alignés sur un même rayon (moins de sillage, donc moins de Δp ?).</p>
<div class="ligne" id="ongletsSP"></div>
<div class="vue3d" id="vueSP"></div>
<div class="ctrl" id="ctrlSP"></div>
<div class="ctrl"><label><input type="checkbox" id="couperSP"> Couper le long du tube</label>
<input type="range" id="planSP" min="0" max="{s['longueur']}" step="0.1" value="{s['longueur'] / 2}" style="width:260px"> <span id="tplanSP"></span></div>
<div class="ctrl" id="vuesSP">Vue : </div>
{bloc_resultats_secteur()}
"""
    return html, obj


def graphe_dp_hA(v, non_valables, raccord, dc):
    """Graphe Δp = f(hA du tube) des cas du secteur : plein = raccord périodique correct (98–102 %), creux = raccord partiel
    (84–97 %, chiffres à confirmer) ; les cas non valables ne sont pas tracés. Objectif : 600 W/K sous 25 Pa."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FAM = [("_f05s", "Décalées avec dents", "#0b7285"), ("_f05i", "Imbriquées", "#2f9e44"), ("_f05v", "Vague", "#e03131"), ("decale4", "Décalées", "#1c7ed6"),
           ("continu", "Continues", "#f08c00"), ("radiales", "Continues + radiales", "#7048e8")]
    ECART = {"": "écart 1,5", "_c15": "écart 1,5 corrigé", "_p5": "écart 4", "_p6": "écart 5", "_m3": "écart 1,5, maillage fin",
             "_f05b_m3y": "lam. 0,5", "_f05i_m3y": "lam. 0,5", "_f05v_m3y": "lam. 0,5", "_f05s_m3y": "lam. 0,5 + dents"}
    # position des étiquettes (points, alignement) pour éviter les chevauchements
    DECAL = {"decale4": (6, -15, "left"), "decale4_f05b_m3y": (9, 5, "left"), "decale4_f05s_m3y": (8, -13, "left"), "continu": (-8, 6, "right"),
             "decale4_m3": (6, 7, "left"), "continu_p5": (-6, 8, "right"), "continu_p6": (-6, -12, "right"),
             "decale4_p6": (4, -14, "left"), "decale4_p5": (6, 6, "left"), "radiales_p6": (-6, 6, "right"),
             "radiales_p5": (-8, -4, "right")}
    fig, ax = plt.subplots(figsize=(10, 6.2))
    vus = set()
    for k, r in v.items():
        if k in non_valables:
            continue
        ra = raccord(k)
        fam = next(x for x in FAM if x[0] in k)
        suf = k.replace("decale4", "").replace("continu", "").replace("radiales", "")
        bon = ra is not None and 0.98 <= ra <= 1.02
        x, y = r["hA_tube_W_K"], r["dp_Pa"]
        ax.scatter(x, y, s=70, color=fam[2] if bon else "white", edgecolor=fam[2], linewidth=1.8, zorder=3)
        vus.add(fam[1])
        dx, dy, ha = DECAL.get(k, (7, 4, "left"))
        ax.annotate(f"{ECART.get(suf, suf)}" + ("" if bon else f" ({round(100 * ra)} %)"), (x, y), textcoords="offset points",
                    xytext=(dx, dy), fontsize=8, color=fam[2], ha=ha)
    ax.axhline(25, color="#555", ls="--", lw=1)
    ax.axvline(600, color="#555", ls="--", lw=1)
    ax.fill_between([600, 3000], 1, 25, color="#2f9e44", alpha=0.08, zorder=0)
    ax.scatter([600], [25], marker="*", s=260, color="#fab005", edgecolor="#333", zorder=4)
    ax.text(620, 20, "zone visée", fontsize=9, color="#2f9e44")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(35, 1500); ax.set_ylim(15, 600)
    ax.set_xlabel("hA du tube complet (W/K), échelle log"); ax.set_ylabel("Δp de l'échangeur (Pa), échelle log")
    ax.set_title("Secteur 1/8, 830 m³/h : perte de charge en fonction de l'échange")
    ax.grid(alpha=0.3, which="both")
    from matplotlib.lines import Line2D
    from matplotlib.ticker import ScalarFormatter
    for a_ in (ax.xaxis, ax.yaxis):
        a_.set_major_formatter(ScalarFormatter())
        a_.set_minor_formatter(ScalarFormatter())
    ax.tick_params(which="minor", labelsize=7)
    poignees = [Line2D([], [], marker="o", ls="", color=c, markersize=8, label=n) for _, n, c in FAM if n in vus]
    poignees += [Line2D([], [], marker="o", ls="", color="#555", markersize=8, label="plein : raccord périodique correct"),
                 Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor="#555", markersize=8,
                        label="creux : raccord partiel (%), à confirmer"),
                 Line2D([], [], marker="*", ls="", color="#fab005", markeredgecolor="#333", markersize=14, label="Objectif (600 W/K, 25 Pa)")]
    ax.legend(handles=poignees, fontsize=8, loc="upper left")
    fig.tight_layout()
    fi = dc / "graphe_secteur_dp_hA.png"
    fig.savefig(fi, dpi=130)
    plt.close(fig)
    return (f"<figure style='margin:12px 0;max-width:900px'><img src='data:image/jpeg;base64,{jpeg_b64(fi, 1200)}' "
            f"style='width:100%;border:1px solid var(--trait);border-radius:8px'><figcaption class=aide><b>Δp = f(hA du tube)</b> pour "
            "les cas du tableau. Marqueur plein : faces périodiques bien raccordées (98–102 %) ; creux : raccord partiel (84–97 %), "
            "valeur à confirmer. Cas non valables (grisés dans le tableau) non tracés. Lamelles de 1 mm sauf « lam. 0,5 » (0,5 mm, "
            "pas 2,5, espace radial 1,5, maillage fin). Aucune de ces valeurs n'a encore d'étude de maillage valable (voir plus bas). "
            "En bas à droite : plus d'échange pour moins de perte de charge.</figcaption></figure>")


def bloc_resultats_secteur():
    """Résultats CFD du secteur de 1/8 (resultats_concept.py, cas « secteur ») : tableau par écart, vue 3D x/y/z, images."""
    dc = DI / "cfd"
    MOD = [("decale4", "Décalées, espace radial 4 mm"), ("continu", "Lamelles continues"), ("radiales", "Continues + radiales")]
    ECARTS = [("", "écart 1,5 mm (pas 2,5)"), ("_c15", "écart 1,5 mm, corrigé (couloir de 1,5 mm autour des profils)"),
              ("_p5", "écart 4 mm (pas 5)"), ("_p6", "écart 5 mm (pas 6)"),
              ("_f05", "lamelles de 0,5 mm, pas 2,5 (jeu 2 mm), espace radial 1,5 mm"),
              ("_f05b", "lamelles de 0,5 mm, pas 2,5 (jeu 2 mm), espace radial 1,5 mm, écartées des faces périodiques"),
              ("_m3", "écart 1,5 mm (pas 2,5), MAILLAGE FIN 0,156 mm"),
              ("_f05b_m3", "lamelles de 0,5 mm, pas 2,5, espace radial 1,5 mm, MAILLAGE FIN 0,156 mm"),
              ("_f05i_m3", "lamelles 0,5 mm IMBRIQUÉES, maillage fin (1er essai)"), ("_f05v_m3", "ailettes 0,5 mm EN VAGUE, maillage fin (1er essai)"),
              ("_f05b_m3y", "lamelles 0,5 mm décalées, maillage fin, RACCORD CORRIGÉ (14/11)"),
              ("_f05i_m3y", "lamelles 0,5 mm IMBRIQUÉES, maillage fin, raccord corrigé (14/11)"),
              ("_f05v_m3y", "ailettes 0,5 mm EN VAGUE, maillage fin, raccord corrigé (14/11)"),
              ("_f05s_m3y", "lamelles 0,5 mm décalées AVEC DENTS (plis triangulaires), maillage fin, raccord corrigé (14/11)")]
    def raccord(k):
        """Part de la face périodique y0 raccordée à y1 (AMI, sum(weights) moyen, log.simpleFoam)."""
        fl = RACINE_CE / "cfd_campagne/secteur/resultats" / k / "log.simpleFoam"
        if not fl.exists():
            return None
        l = [x for x in fl.read_text(errors="ignore").splitlines()[:400] if "source sum(weights)" in x]
        return float(l[1].split("average:")[1]) if len(l) > 1 else None
    v = {}
    for m, _ in MOD:
        for s_, _ in ECARTS:
            fi = dc / f"resultat_secteur_{m}{s_}.json"
            if fi.exists():
                v[m + s_] = json.loads(fi.read_text())
    if not v:
        return ""
    def stab(r):
        """Stabilité : variation max de Δp et de θ de sortie sur la fenêtre de moyenne."""
        x = max(r["fluctuation_dp"], r["fluctuation_T"]) / 2          # demi-écart (± affiché)
        etat = "stable" if x < 0.01 else ("oscille un peu" if x < 0.05 else "oscille")
        return f"{etat} <span class=aide>(Δp ± {f(50 * r['fluctuation_dp'], 1)} %, θ ± {f(50 * r['fluctuation_T'], 1)} %)</span>"
    NON_VALABLES = {"radiales": "fentes autour des profils", "decale4_f05": "bilan de chaleur faux (lamelles de 0,25 mm sur les faces périodiques)"}
    for k_ in ("decale4_f05b", "decale4_f05b_m3", "decale4_f05i_m3", "decale4_f05v_m3"):
        NON_VALABLES[k_] = "faces périodiques le long du tube raccordées à 18–31 % seulement (défaut du calcul parallèle)"
    tab = ("<tr><th>Modèle</th><th>Écart entre lamelles</th><th class=n>Δp</th><th class=n>hA du tube</th>"
           "<th class=n>hA / Δp<br><span class=aide>(W/K par Pa, plus haut = mieux ; objectif 600 / 25 = 24)</span></th>"
           "<th class=n>Efficacité ε</th><th>Stabilité du calcul</th><th class=n>Bilan de chaleur paroi / air</th><th class=n>Raccord périodique y</th></tr>")
    # dégradé de couleur de hA / Δp (rouge = mauvais, vert = bon), échelle log entre le plus mauvais cas valable et l'objectif (24)
    import math
    rv = [x["hA_tube_W_K"] / x["dp_Pa"] for k_, x in v.items() if k_ not in NON_VALABLES]
    lo, hi = math.log(min(rv)), math.log(24.0)

    def couleur_ratio(val, nv):
        if nv:
            return "transparent"
        s = min(1.0, max(0.0, (math.log(val) - lo) / (hi - lo)))
        return f"hsla({round(120 * s)}, 75%, 45%, 0.35)"
    for m, nom in MOD:
        for s_, ne in ECARTS:
            r = v.get(m + s_)
            if not r:
                continue
            nv = NON_VALABLES.get(m + s_)
            ac = None
            ra = raccord(m + s_)
            bil = r.get("bilan_paroi_sur_air")
            tab += (f"<tr{' style=opacity:.55' if nv else ''}><td>{nom}</td><td>{ne}</td>"
                    f"<td class=n><b>{f(r['dp_Pa'])} Pa</b>{f' (non valable : {nv})' if nv else ''}</td>"
                    f"<td class=n><b>{f(r['hA_tube_W_K'])} W/K</b>{f' <span class=aide>({ac})</span>' if ac else ''}</td><td class=n style='background:{couleur_ratio(r['hA_tube_W_K'] / r['dp_Pa'], nv)}'><b>{f(r['hA_tube_W_K'] / r['dp_Pa'], 2)}</b></td><td class=n>{f(r['efficacite'], 3)}</td><td>{stab(r)}</td>"
                    f"<td class=n>{f(100 * bil) + ' %' if bil else ''}</td><td class=n>{f(100 * ra) + ' %' if ra else ''}</td></tr>")
    graphe = graphe_dp_hA(v, NON_VALABLES, raccord, dc)
    imgs = ""
    for k in [m + "_p6" for m, _ in MOD if m + "_p6" in v]:
        nom = dict(MOD)[k.replace("_p6", "")] + ", écart 5 mm"
        for nm, leg in (("vitesse_y", "vitesse dans une coupe le long du tube"), ("temperature_y", "température θ dans une coupe le long du tube")):
            fi = dc / f"resultat_secteur_{k}_{nm}.png"
            if fi.exists():
                imgs += (f"<figure style='margin:8px 0;max-width:620px;display:inline-block;vertical-align:top;width:49%'>"
                         f"<img src='data:image/jpeg;base64,{jpeg_b64(fi, 800)}' style='width:100%;border:1px solid var(--trait);border-radius:8px'>"
                         f"<figcaption class=aide>{nom}, {leg}.</figcaption></figure> ")
    return f"""<h4 id=resultats-secteur>Résultats CFD du secteur (13/11, 830 m³/h, quelques minutes de calcul par modèle)</h4>
<div class=carte><table>{tab}</table>
{graphe}
<p class=aide>hA du tube complet à 830 m³/h (requis ≈ 600 W/K) ; Δp de l'échangeur seul (budget ≈ 25 Pa). Lamelles de 1 mm.
Efficacité ε : part de l'écart de température air / propane récupérée par l'air (température de mélange en sortie) ; NTU = −ln(1 − ε).
Stabilité : demi-écart max / moyenne de Δp et de θ de sortie sur les 500 dernières itérations (50 si le calcul a convergé tôt) ;
« stable » sous 1 %, « oscille un peu » sous 5 %, « oscille » au-delà (écoulement instationnaire derrière les tronçons : valeurs moyennes).
Bilan de chaleur : chaleur reçue par les parois (gradient de température à la paroi) / chaleur emportée par l'air. Ce bilan devrait
valoir 100 % ; il varie de 47 à 162 % selon les cas, parce que le gradient calculé dans les mailles de paroi est imprécis : ce n'est
pas un indicateur fiable à lui seul (ε, tiré de la température de mélange en sortie, fait foi).<br>
<b>Correction du 14/11 — raccord des faces périodiques.</b> Les faces périodiques le long du tube (y0 ↔ y1) sont reliées par une
interpolation (AMI). En calcul parallèle, OpenFOAM ne la calcule correctement que si aucun processeur ne porte à la fois une partie de
y0 et de y1 : avec le découpage automatique, seuls <b>18 à 31 % de la face étaient raccordés au pas de 2,5 mm</b> (le reste se comportait
en paroi), 84 à 100 % au pas de 5 à 6 mm (colonne « Raccord périodique y »). Les cas au pas de 2,5 mm calculés avant le 14/11 sont donc
faux (grisés). Correctif : découpage en 8 tranches le long du tube (raccord 99,6 à 100,5 %) et arrêt automatique du calcul si le raccord
est hors de 98–102 %. Au pas de 5 à 6 mm, les décalées et les radiales sont à 92–100 %, mais les <b>lamelles continues seulement à 72–84 %</b> : leur comparaison avec les décalées est à refaire avec le raccord corrigé.<br>
<b>Lamelles 0,5 mm au maillage fin, raccord corrigé (14/11)</b> : décalées <b>59 Pa / 299 W/K</b> (ε 0,66) ; <b>imbriquées</b> (chaque
lamelle recouvre la moitié de ses voisines) <b>169 Pa / 731 W/K</b> (ε 0,93) : seule forme qui dépasse les 600 W/K requis, au prix de
jeux de 0,75 mm et d'une perte de charge 7 fois le budget ; <b>vague</b> <b>103 Pa / 330 W/K</b> (ε 0,69) : à peine plus d'échange que les
décalées pour 1,7 fois leur perte de charge (la couche limite n'est plus coupée, et l'air est dévié à chaque pente). Les trois calculs
sont stables, bilans de chaleur 90 à 93 %.<br>
<b>Décalées 0,5 mm avec dents (plis triangulaires, 14/11)</b> : <b>56 Pa / 229 W/K</b> (ε 0,56, hA/Δp 4,1), calcul stable, bilan 91 %,
raccord 100,1 %. Les dents font <b>perdre 23 % d'échange</b> par rapport aux mêmes lamelles sans dents (299 W/K) pour seulement 5 % de
perte de charge en moins. Cause visible dans la coupe y : les creux en V entre deux dents n'ont pas de lamelle, ils forment des canaux
radiaux ouverts où l'air traverse sans toucher de paroi (zone extérieure restée à θ ≈ 0). Le surcroît de surface des flancs ne compense
pas cette fuite. De plus, le recalage des profils dans les dents a déplacé la rangée extérieure de tubes vers les bords du secteur.
Pour que les plis servent, il faudrait qu'ils ne laissent pas de passage direct (dents d'une couronne en face des creux de la suivante,
ou plis dans l'épaisseur plutôt qu'en plan).<br>
<b>Étude de maillage (13/11)</b> : deux cas refaits avec des mailles de 0,156 mm dans toute la zone d'échange (au lieu de 0,25 mm).
Décalées, écart 1,5 mm (lamelles de 1 mm) : 62 → <b>83 Pa</b> (+35 %), 266 → <b>220 W/K</b> (−17 %). Lamelles de 0,5 mm : 30 → 71 Pa,
609 → 291 W/K ; ces deux calculs avaient le défaut de raccord périodique (corrigé le 14/11 : 59 Pa, 299 W/K) : la comparaison n'est
pas valable pour ce cas. Conséquence : <b>tous les
résultats au maillage de 0,25 mm sous-estiment Δp d'environ 30 % et surestiment hA d'environ 15 à 20 %</b> ; les comparaisons entre modèles
restent indicatives, les valeurs absolues doivent être corrigées ou refaites au maillage fin. Les lamelles décalées oscillent (± 9 à
23 % sur Δp) : un calcul instationnaire préciserait leur perte de charge.
<b>Écart 1,5 mm</b> : les lamelles continues donnent 65 Pa et 241 W/K (68 Pa et 218 W/K sur le secteur complet, profils placés
autrement) : le secteur de 1/8 est utilisable pour les études ; le modèle radial n'est pas valable (profils à 0 à 0,4 mm des lamelles
radiales voisines : fentes, jets à 30 m/s). <b>Écarts 4 et 5 mm</b> : moins de lamelles, donc moins de Δp et moins d'échange ; les
lamelles radiales sont coupées à 1,5 mm des profils (plus de fente). <br>
<b>Ce que montrent les trois écarts :</b> élargir l'écart de 1,5 à 4 ou 5 mm ramène la perte de charge au budget (22 à 27 Pa pour les
lamelles décalées et continues), mais l'échange s'effondre (hA ÷ 2,7 à ÷ 5,5) : le h baisse dans des canaux larges et il y a moins de
surface. À écart égal, les <b>lamelles décalées</b> échangent nettement plus que les continues (× 1,8 à 4 et 5 mm) pour à peu près la
même perte de charge : c'est le meilleur des trois modèles partout. Les <b>lamelles radiales</b> ajoutent de la surface mais aussi de la
perte de charge (171 W/K pour 83 Pa à 4 mm). Au budget de 25 Pa, ce tube Ø 150 avec des parois de 1 mm donne environ 80 à 100 W/K,
loin des ≈ 600 requis : comme estimé le 12/11, il faut beaucoup plus de volume ou de surface d'entrée (tube plus long ou plus gros),
ou des parois plus minces.</p></div>
<p><b>Vue 3D des résultats du secteur</b> : champ au choix sur trois coupes x, y, z (curseurs), solide en transparence ; grille de 0,33 mm.</p>
<div class="ligne"><span id="casRS">Modèle : </span></div>
<div class="ligne"><label>Champ <select id="champRS"></select></label>
  <canvas id="barreRS" width="256" height="12" style="width:256px;height:12px;border:1px solid var(--trait)"></canvas>
  <span id="bminRS"></span> → <span id="bmaxRS"></span></div>
<div class="vue3d" id="vueRS" style="position:relative"></div>
<div class="ctrlM">
  <label><input type="checkbox" id="cxRS" checked> <span class="pastille" style="background:#e03131"></span>coupe x</label><input type="range" id="sxRS"><span id="txRS"></span>
  <label><input type="checkbox" id="cyRS" checked> <span class="pastille" style="background:#2f9e44"></span>coupe y (le long du tube)</label><input type="range" id="syRS"><span id="tyRS"></span>
  <label><input type="checkbox" id="czRS" checked> <span class="pastille" style="background:#1c7ed6"></span>coupe z</label><input type="range" id="szRS"><span id="tzRS"></span>
</div>
<div class="ligne"><label><input type="checkbox" id="csRS" checked> solide</label>
  <label>opacité <input type="range" id="osRS" min="0" max="1" step="0.05" value="0.25" style="width:120px"></label>
  <span>Vue :</span><span id="vuesRS"></span></div>
{imgs}
"""


def bloc_resultats():
    """Section « Résultats CFD 3D » du concept imprimé (resultats_concept.py)."""
    dc = DI / "cfd"
    NOMS = {"continu": "Lamelles continues (référence)", "decale4": "Décalées, espace radial 4 mm",
            "sans": "Décalées sans espace (défaut : fentes)", "avec": "Avec stries, sans espace (défaut : fentes)"}
    v = {k: json.loads((dc / f"resultat_{k}.json").read_text()) for k in NOMS if (dc / f"resultat_{k}.json").exists()}
    if not v:
        return ""
    lig = [("Perte de charge Δp (budget ≈ 25 Pa)", lambda r: f"<b>{f(r['dp_Pa'])} Pa</b>"),
           ("Efficacité ε (θ de l'air en sortie)", lambda r: f"{f(r['efficacite'], 3)}"),
           ("NTU", lambda r: f"{f(r['NTU'], 2)}"),
           ("hA du tube complet à 830 m³/h (requis ≈ 600)", lambda r: f"<b>{f(r['hA_tube_W_K'])} W/K</b>"),
           ("Vitesse maximale (entrée : 1,9 m/s)", lambda r: f"{f(r['U_max_m_s'], 1)} m/s"),
           ("Variation sur les 500 dernières itérations (Δp / θ)", lambda r: f"{f(100 * r['fluctuation_dp'], 1)} % / {f(100 * r['fluctuation_T'], 1)} %")]
    tab = "<tr><th></th>" + "".join(f"<th>{NOMS[k]}</th>" for k in v) + "</tr>"
    tab += "".join(f"<tr><td>{a}</td>" + "".join(f"<td class=n>{fn(r)}</td>" for r in v.values()) + "</tr>" for a, fn in lig)
    imgs = ""
    for k in [x for x in ("continu", "decale4", "sans") if x in v]:
        for nom, leg in (("vitesse_radial", "vitesse dans la coupe radiale (φ = 20°)" + (" : les jets (jaune) sortent des fentes de 0,25 mm entre deux couronnes" if k in ("sans", "avec") else ", l'air va de droite à gauche")),
                         ("temperature_y", "température θ dans une coupe y : l'air est presque à la température du propane avant le centre"),
                         ("vitesse_y", "vitesse dans une coupe y")):
            fi = dc / f"resultat_{k}_{nom}.png"
            if fi.exists():
                imgs += (f"<figure style='margin:8px 0'><img src='data:image/jpeg;base64,{jpeg_b64(fi)}' style='width:100%;border:1px solid var(--trait);border-radius:8px'>"
                         f"<figcaption class=aide>{NOMS[k]}, {leg}.</figcaption></figure>")
    return f"""<h3 id=resultats-cfd>Résultats CFD 3D (tranche périodique, 830 m³/h)</h3>
<div class=carte><table>{tab}</table>
<p class=aide><b>Première version (« décalées sans espace », « avec stries ») : défaut de géométrie.</b> Avec des lamelles de 1 mm pour un
jeu de 1,5 mm, la lamelle de la couronne suivante, décalée d'un demi-pas, tombe au milieu du jeu de la précédente ; les couronnes se
touchant, l'air ne passe que par deux fentes de 0,25 mm (33 % de la section) à chaque transition : jets de 21 à 34 m/s, Δp de 560 à
700 Pa. Ces deux cas restent pour mémoire.<br>
<b>Correction (« décalées, espace radial 4 mm »)</b> : un espace libre de 4 mm entre deux couronnes laisse l'air se redistribuer ; la
section de passage ne descend plus sous 59 % (contrôle de la géométrie avant maillage). La perte de charge tombe à environ 74 Pa, mais
reste trois fois au-dessus du budget, et l'espace supprime environ 44 % des lamelles : hA ≈ 240 W/K, moins de la moitié du besoin.<br>
<b>Référence « lamelles continues »</b> (sans décalage ni espace) : Δp ≈ 68 Pa, hA ≈ 218 W/K. Les lamelles décalées avec espace font donc
un peu mieux (+9 % de hA pour +9 % de Δp) avec 44 % de lamelles en moins : par m² de lamelle, elles échangent environ deux fois plus
(relance de la couche limite à chaque couronne). Mais dans les deux cas, le tube Ø 150 avec des parois de 1 mm reste loin du besoin
(≈ 600 W/K sous ≈ 25 Pa) : l'air est déjà réchauffé avant le centre, et la perte de charge vient surtout des jeux de 1,5 mm sur
toute la profondeur. Pistes : moins de profondeur (noyau plus grand), lamelles décalées avec un espace plus court (1 à 2 mm), plus de
surface d'entrée (tube plus long ou Ø 200).<br>
ε est tiré de la température de mélange en sortie (fait foi) ; le flux pariétal mesuré est sous-estimé par le gradient de maille.</p></div>
<p><b>Vue 3D des résultats</b> : champ au choix sur trois coupes x, y, z déplaçables (curseurs) ; solide en transparence. Les champs sont
rééchantillonnés sur une grille de 0,33 mm (environ 4 à 5 points dans un jeu de 1,5 mm).</p>
<div class="ligne"><span id="casR">Cas : </span></div>
<div class="ligne"><label>Champ <select id="champR"></select></label>
  <canvas id="barreR" width="256" height="12" style="width:256px;height:12px;border:1px solid var(--trait)"></canvas>
  <span id="bminR"></span> → <span id="bmaxR"></span></div>
<div class="vue3d" id="vueR" style="position:relative"></div>
<div class="ctrlM">
  <label><input type="checkbox" id="cxR" checked> <span class="pastille" style="background:#e03131"></span>coupe x</label><input type="range" id="sxR"><span id="txR"></span>
  <label><input type="checkbox" id="cyR" checked> <span class="pastille" style="background:#2f9e44"></span>coupe y (le long du tube)</label><input type="range" id="syR"><span id="tyR"></span>
  <label><input type="checkbox" id="czR" checked> <span class="pastille" style="background:#1c7ed6"></span>coupe z</label><input type="range" id="szR"><span id="tzR"></span>
</div>
<div class="ligne"><label><input type="checkbox" id="csR" checked> solide (lamelles, profils)</label>
  <label>opacité <input type="range" id="osR" min="0" max="1" step="0.05" value="0.25" style="width:120px"></label>
  <span>Vue :</span><span id="vuesR"></span></div>
{imgs}
"""


def bloc_maillage():
    """Section « Maillage CFD 3D » du concept imprimé (verifier_maillage_concept.py), vide si pas encore maillé."""
    dc = DI / "cfd"
    if not (dc / "maillage_sans.json").exists():
        return ""
    v = {k: json.loads((dc / f"maillage_{k}.json").read_text()) for k in ("sans", "avec") if (dc / f"maillage_{k}.json").exists()}
    lig = [
        ("Mailles", lambda r: f"{f(r['cellules'] / 1e6, 2)} million (dont {f(100 * r['hexaedres'] / r['cellules'], 1)} % d'hexaèdres)"),
        ("checkMesh", lambda r: "Mesh OK" if r["checkMesh_ok"] else "OK sauf " + "; ".join(
            (e.split(",")[1].split()[0] + " face(s) très biaisée(s)") if "skew" in e else e for e in r["checkMesh_echecs"])),
        ("Non-orthogonalité max / asymétrie max", lambda r: f"{f(r['non_orthogonalite_max'])}° / {f(r['asymetrie_max'], 1)}"),
        ("Fuite : centres de mailles dans le solide", lambda r: f"{r['centres_dans_le_solide']} sur {f(r['echantillon_centres'])} tirés"),
        ("Faces périodiques y0 / y1 (doivent être égales)", lambda r: f"{f(r['aire_y0_mm2'])} / {f(r['aire_y1_mm2'])} mm²"),
        ("Volume d'air maillé / réel (tirage aléatoire dans la tranche)", lambda r: f"{f(r['volume_air_maillage_cm3'], 2)} / {f(r['volume_air_attendu_cm3'], 2)} cm³ ({f(100 * (r['volume_air_maillage_cm3'] / r['volume_air_attendu_cm3'] - 1), 1).replace('-', '−')} %)"),
        ("Entrée (r = 77) / sortie (r = 33)", lambda r: f"{f(r['aire_entree_mm2'])} / {f(r['aire_sortie_mm2'])} mm² (géométrie {f(r['aire_entree_attendue_mm2'])} / {f(r['aire_sortie_attendue_mm2'])})"),
        ("Paroi air / solide", lambda r: f"{f(r['aire_paroi_mm2'])} mm²"),
    ]
    tab = "<tr><th>Contrôle</th>" + "".join(f"<th>{'Sans stries' if k == 'sans' else 'Avec stries'}</th>" for k in v) + "</tr>"
    tab += "".join(f"<tr><td>{a}</td>" + "".join(f"<td class=n>{fn(r)}</td>" for r in v.values()) + "</tr>" for a, fn in lig)
    imgs = ""
    for k in v:
        for nom, leg in (("interstice", "coupe à y = 2,5 mm (plan perpendiculaire au tube) : blanc = solide (lamelles des couronnes coupées, profils)"),
                         ("interstice_zoom", "zoom : environ 6 mailles dans un jeu de 1,5 mm"),
                         ("radial_zoom", "coupe radiale (plan qui contient l'axe, φ = 20°), r = 50 à 66 mm : lamelles décalées en quinconce ; "
                                         "l'air va de droite à gauche, la tranche se répète en haut et en bas")):
            fi = dc / f"maillage_{k}_{nom}.png"
            if fi.exists():
                imgs += (f"<figure style='margin:8px 0'><img src='data:image/jpeg;base64,{jpeg_b64(fi)}' style='width:100%;border:1px solid var(--trait);border-radius:8px'>"
                         f"<figcaption class=aide>{'Sans' if k == 'sans' else 'Avec'} stries, {leg}.</figcaption></figure>")
    return f"""<h3 id=maillage-cfd>Maillage CFD 3D (à valider avant le calcul)</h3>
<p class=aide>Tranche périodique de 5 mm (2 pas de lamelles) sur tout le secteur d'échange, du filtre (r = 77 mm, entrée à débit imposé :
830 m³/h ramenés à la tranche) au noyau (r = 33 mm, sortie). snappyHexMesh : fond de 1 mm, 0,25 mm dans toute la zone d'échange.
Le solide est d'un seul tenant et fermé (contrôle FreeCAD et surfaceCheck) ; dans la version avec stries, une âme radiale de 1 mm dans
chaque dent relie les tronçons décalés (sinon ils flottent), et les deux demi-dents des bouts du secteur, isolées, sont supprimées.
Les lamelles d'une couronne sur deux sont coupées en leur milieu par les faces périodiques ; les autres en sont à 0,75 mm (un premier
maillage avec des lamelles à 0,125 mm des faces bouchait 30 % d'une face périodique : corrigé).</p>
<p><b>Vue 3D interactive du maillage</b> : chaque curseur déplace une coupe (mailles en fil de fer) ; solide en transparence.
Zoomer à la molette pour voir les mailles (0,25 mm). Aussi en pages séparées : <a href="variante_f/imprime/cfd/maillage_3d_sans.html">sans stries</a> ·
<a href="variante_f/imprime/cfd/maillage_3d_avec.html">avec stries</a>.</p>
<p><b>Domaine simulé</b> : exactement ce que voit le calcul (frontières tirées du maillage), les deux versions côte à côte. C'est une
tranche de 5 mm du tube de 394 mm : elle se répète le long du tube par les faces périodiques (vertes). L'air entre par la surface bleue
(le filtre, r = 77 mm), traverse lamelles et profils (gris) et sort par la surface rouge (r = 33 mm) dans le noyau.</p>
<div class="vue3d" id="vueDS"></div>
<div class="ctrl" id="ctrlDS"></div>
<div class="ctrl"><label><input type="checkbox" id="couperDS"> Couper le long du tube</label>
<input type="range" id="planDS" min="0" max="5" step="0.05" value="2.5" style="width:260px"> <span id="tplanDS"></span></div>
<div class="ctrl" id="vuesDS">Vue : </div>
<div class="ligne" id="versionsM">Maillage, version : </div>
<div class="vue3d" id="vueM" style="position:relative"><div id="chargeM" style="position:absolute;margin:12px;color:#495057">Décompression du maillage…</div></div>
<div class="ctrlM">
  <label><input type="checkbox" id="cxM" checked> <span class="pastille" style="background:#e03131"></span>coupe x</label><input type="range" id="sxM"><span id="txM"></span>
  <label><input type="checkbox" id="cyM" checked> <span class="pastille" style="background:#1c7ed6"></span>coupe y (le long du tube)</label><input type="range" id="syM"><span id="tyM"></span>
  <label><input type="checkbox" id="czM" checked> <span class="pastille" style="background:#2f9e44"></span>coupe z</label><input type="range" id="szM"><span id="tzM"></span>
</div>
<div class="ligne"><label><input type="checkbox" id="csM" checked> solide (lamelles, profils)</label>
  <label>opacité <input type="range" id="osM" min="0" max="1" step="0.05" value="0.35" style="width:120px"></label>
  <span>Vue :</span><span id="vuesM"></span></div>
<div class=carte><table>{tab}</table>
<p class=aide>Écarts restants : le volume d'air maillé est 2 à 3 % sous le volume réel (mailles accrochées aux parois courbes) ; la sortie
perd une rangée de mailles le long des faces périodiques (dans le noyau vide, sans effet sur l'échangeur) ; l'aire d'entrée mesurée
varie avec l'angle (faces accrochées au cylindre), mais le débit est imposé.</p></div>
{imgs}
"""


def stl_gz(nom, dossier):
    """Triangles d'un STL en entiers 16 bits relatifs à leur boîte, compressés (gzip) : pour les gros objets."""
    import gzip
    m = pv.read(dossier / f"{nom}.stl").triangulate()
    tri = m.points[m.faces.reshape(-1, 4)[:, 1:]].reshape(-1, 3).astype(np.float64)
    o = tri.min(axis=0)
    s = float((tri.max(axis=0) - o).max() / 65000) or 1.0
    q = np.round((tri - o) / s).astype("<u2")
    return dict(gz=base64.b64encode(gzip.compress(q.tobytes(), 6)).decode(), o=o.tolist(), s=s)


def bloc_domaine():
    """Pièces de la vue « domaine simulé » (domaine_simule_concept.py) : les deux versions côte à côte."""
    dc = DI / "cfd"
    if not (dc / "domaine_simule.json").exists():
        return []
    PIECES_DS = [("paroi", "paroi (lamelles, profils)", "#868e96", 1.0), ("entree", "entrée d'air (r = 77, débit imposé)", "#1c7ed6", 0.35),
                 ("sortie", "sortie (r = 33, vers le noyau)", "#e03131", 0.45), ("cotes", "côtés du secteur (glissement)", "#f59f00", 0.45),
                 ("y0", "face périodique y = 0", "#2f9e44", 0.25), ("y1", "face périodique y = 5 mm", "#2f9e44", 0.25)]
    obj = []
    for v in ("sans", "avec"):
        for nom, titre, coul, op in PIECES_DS:
            if (dc / f"domaine_{v}_{nom}.stl").exists():
                obj.append(dict(nom=f"{v}_{nom}", titre=f"{'Sans' if v == 'sans' else 'Avec'} stries : {titre}", couleur=coul, opacite=op,
                                **stl_gz(f"domaine_{v}_{nom}", dc)))
    return obj


def f(x, n=0):
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",")


def main():
    d = json.loads((D / "dimensions.json").read_text())
    p, g = d["parametres"], d["galette"]
    objets = [dict(nom=n, titre=t, couleur=c, opacite=o, tri=stl_b64(n)) for n, t, c, o in PIECES]
    enc = d["encombrement_mm"]
    lignes = [
        ("Cylindre (enveloppe de la galette)", f"Ø {f(2 * p['r_ext'])} × {f(p['longueur'])} mm"),
        ("Encombrement total (x × y × z)", f"{f(enc['x'])} × {f(enc['y'])} × {f(enc['z'])} mm"),
        ("Plis : nombre, profondeur, épaisseur de galette", f"{g['plis']}, {f(p['r_ext'] - p['r_int'])} mm, {f(p['ep_galette'])} mm"),
        ("Secteur d'aspiration / gorge", f"{f(360 - (p['secteur_gorge_deg'][1] - p['secteur_gorge_deg'][0]))}° / {f(d['gorge_mm'])} mm de corde"),
        ("Surface frontale de la galette dépliée", f"{f(g['surface_frontale_m2'], 3)} m² (enveloppe {f(g['surface_enveloppe_m2'], 3)} m²)"),
        ("Volume de la galette", f"{f(g['volume_dm3'], 2)} dm³"),
        ("Manchon filtrant", f"{f(d['filtre_surface_m2'], 3)} m², r = {f(p['r_filtre'])} mm"),
        ("Bouche de sortie", f"{f(d['bouche_mm'][0])} × {f(d['bouche_mm'][1])} mm"),
        ("Ventilateurs (de principe)", f"{p['n_ventilateurs']} × Ø {f(p['d_ventilateur'])} mm, axiaux"),
    ]
    table = "".join(f"<tr><td>{a}</td><td class=n>{b}</td></tr>" for a, b in lignes)
    css2d, corps2d = croquis_radial.contenu()
    de = json.loads((DE / "dimensions.json").read_text())
    pe, tr, tn = de["parametres"], de["tubes_refrigerant"], de["tubes_nus"]
    objets_e = [dict(nom=n, titre=t_, couleur=c, opacite=o, tri=stl_b64(n, DE)) for n, t_, c, o in PIECES_E]
    enc_e = de["encombrement_mm"]
    lignes_e = [
        ("Encombrement (x pièce × y vitre × z)", f"{f(enc_e['x'])} × {f(enc_e['y'])} × {f(enc_e['z'])} mm"),
        ("Tube", f"Ø {f(2 * pe['r_tube'])}, cintré R {f(pe['r_cintrage'])} sur l'axe, {f(de['ligne_moyenne_mm'])} mm sur l'axe"),
        ("Zone d'échange (sans plis ni ailettes)", f"r {f(pe['r_int_echangeur'])} → {f(pe['r_ext_echangeur'])} mm sur {f(pe['secteur_echangeur_deg'][1] - pe['secteur_echangeur_deg'][0])}°, surface frontale {f(de['zone_echange']['surface_frontale_m2'], 3)} m²"),
        ("Tubes de réfrigérant", f"{tr['nombre']} × Ø {f(pe['d_tube_refrigerant'], 1)} en tournesol (densité uniforme, pas d'or sur le secteur), entraxe mini {f(tr['entraxe_mini_mm'], 1)} mm"),
        ("Longueur et surface des tubes", f"{f(tr['longueur_totale_m'], 1)} m, {f(tr['surface_exterieure_m2'], 2)} m²"),
        ("Volume de propane (Ø int. " + f(pe['d_int_refrigerant'], 1) + ")", f"{f(tr['volume_propane_cm3'])} cm³ (limite 276 cm³ par échangeur)"),
        ("hA des tubes nus (Zukauskas, ordre de grandeur)", f"{f(tn['570']['hA_W_K'])} W/K à 570 m³/h, {f(tn['830']['hA_W_K'])} W/K à 830 m³/h (h ≈ {f(tn['830']['h_moyen_W_m2K'])} W/m²K) ; requis ≈ 600"),
        ("Bouche (= plénum)", f"{f(de['bouche_plenum_mm'][0])} × {f(de['bouche_plenum_mm'][1])} mm, ventilateur axial Ø {f(pe['d_ventilateur'])}"),
    ]
    table_e = "".join(f"<tr><td>{a}</td><td class=n>{b}</td></tr>" for a, b in lignes_e)
    vue_e = f"""<h3>Modèle 3D de la variante E (tubes nus, sans plis ni ailettes)</h3>
<div class="vue3d" id="vueE"></div>
<div class="ctrl" id="ctrlE"></div>
<div class="ctrl"><label><input type="checkbox" id="couperE"> Couper par un plan perpendiculaire à la vitre (y = 0 : coupe A–A)</label>
<input type="range" id="planE" min="-210" max="210" step="1" value="0" style="width:260px"> <span id="tplanE"></span></div>
<div class="ctrl" id="vuesE">Vue : </div>
<p class="aide">Modèle FreeCAD paramétrique (<code>outils/cad/echangeur_fer_a_cheval.py</code>, <code>parametres_fer_a_cheval.json</code>).
Pas de plis ni d'ailettes pour l'instant : l'échangeur est un faisceau de tubes nus, disposés en tournesol dans la coupe ; ils suivent
le fer à cheval et s'arrêtent à la plaque arrière (collecteurs non dessinés). Ici l'affichage est allégé ; les STL complets sont dans <code>variante_e/</code>.</p>
<div class="carte"><b>Dimensions de la variante E</b><table>{table_e}</table></div>"""
    corps2d = corps2d.replace("__VUE3D_E__", vue_e)
    # --- variante F : tube droit, flux vers le haut (3D seulement) ---
    dfj = json.loads((DF / "dimensions.json").read_text())
    pf, trf, tnf, lm = dfj["parametres"], dfj["tubes_refrigerant"], dfj["tubes_nus"], dfj["lamelles"]
    tp_ = dfj["tranche_plissee"]
    objets_fp = [dict(nom=n, titre=t_, couleur=c, opacite=o, tri=stl_b64(n, DF)) for n, t_, c, o in PIECES_FP]
    pi_ = json.loads((DI / "dimensions.json").read_text())
    objets_fi = [dict(nom=n, titre=t_, couleur=c, opacite=o, tri=stl_b64(n, DI)) for n, t_, c, o in PIECES_FI]
    img_q = base64.b64encode((DI / "imp_quinconce.png").read_bytes()).decode()
    objets_fl = [dict(nom=n, titre=t_, couleur=c, opacite=o, tri=stl_b64(n, DF)) for n, t_, c, o in PIECES_FL]
    objets_f = [dict(nom=n, titre=t_, couleur=c, opacite=o, tri=stl_b64(n, DF)) for n, t_, c, o in PIECES_F]
    enc_f = dfj["encombrement_mm"]
    lignes_f = [
        ("Encombrement (x pièce × y vitre × z)", f"{f(enc_f['x'])} × {f(enc_f['y'])} × {f(enc_f['z'])} mm"),
        ("Tube", f"Ø {f(2 * pf['r_tube'])} × {f(dfj['longueur_tube_mm'])} mm, droit, couché le long de la vitre"),
        ("Zone d'échange (sans plis ni ailettes)", f"r {f(pf['r_int_echangeur'])} → {f(pf['r_ext_echangeur'])} mm sur {f(pf['secteur_echangeur_deg'][1] - pf['secteur_echangeur_deg'][0])}° (du point le plus bas du cercle au haut côté vitre), surface frontale {f(dfj['zone_echange']['surface_frontale_m2'], 3)} m²"),
        ("Tubes de réfrigérant", f"{trf['nombre']} × Ø {f(pf['d_tube_refrigerant'], 1)} en tournesol, entraxe mini {f(trf['entraxe_mini_mm'], 1)} mm, {f(trf['longueur_totale_m'], 1)} m, {f(trf['surface_exterieure_m2'], 2)} m²"),
        ("Volume de propane", f"{f(trf['volume_propane_cm3'])} cm³ (limite 276 cm³)"),
        ("Bouche (= dessus du plénum)", f"{f(dfj['bouche_mm'][0])} × {f(dfj['bouche_mm'][1])} mm : {f(tnf['570']['v_bouche_m_s'], 1)} m/s à 570 m³/h, {f(tnf['830']['v_bouche_m_s'], 1)} m/s à 830 m³/h"),
        ("Ventilateurs", f"{pf['n_ventilateurs']} × axial Ø {f(pf['d_ventilateur'])} à axe vertical : {f(tnf['570']['v_ventilateurs_m_s'], 1)} à {f(tnf['830']['v_ventilateurs_m_s'], 1)} m/s dans les roues"),
        ("hA des tubes nus (Zukauskas, ordre de grandeur)", f"{f(tnf['570']['hA_W_K'])} W/K à 570 m³/h, {f(tnf['830']['hA_W_K'])} W/K à 830 m³/h ; requis ≈ 600"),
    ]
    table_f = "".join(f"<tr><td>{a}</td><td class=n>{b}</td></tr>" for a, b in lignes_f)
    secteur_html, objets_sp = bloc_secteur()
    vue_f = f"""<h2 id=variante-f>Variante F : un seul tube droit, flux vers le haut</h2>
<p class=aide>Comme la variante E, mais le fer à cheval est remplacé par <b>un seul tube droit Ø {f(2 * pf['r_tube'])}</b> couché le long de la
vitre (c'est la variante A′ avec un flux vers le haut). L'air de la pièce entre dans le tube par le côté pièce, le dessus et le dessous,
traverse le faisceau de tubes de réfrigérant, ressort par la face tournée vers la vitre dans le plénum (entre le tube et la vitre) et
monte : ventilateurs axiaux à axe vertical, bouche sur tout le dessus du plénum, volet à lames. Le socle s'arrête sous le milieu du tube
et son dessus est au point le plus bas du cercle. Pas de plis ni d'ailettes, pas de collecteurs pour l'instant.</p>
<div class="vue3d" id="vueF"></div>
<div class="ctrl" id="ctrlF"></div>
<div class="ctrl"><label><input type="checkbox" id="couperF"> Couper par un plan perpendiculaire au tube</label>
<input type="range" id="planF" min="-200" max="200" step="1" value="0" style="width:260px"> <span id="tplanF"></span></div>
<div class="ctrl" id="vuesF">Vue : </div>
<p class="aide">Modèle FreeCAD paramétrique (<code>outils/cad/echangeur_tube_droit.py</code>, <code>parametres_tube_droit.json</code>) ;
fichiers dans <code>variante_f/</code>.</p>
<div class="carte"><b>Dimensions de la variante F</b><table>{table_f}</table></div>
<h3>Vue de coupe : tranche de {f(lm['tranche_mm'])} mm avec les lamelles</h3>
<p class=aide>Lamelles d'aluminium de {f(lm['epaisseur_mm'], 2)} mm au pas de {f(lm['pas_mm'], 1)} mm (≈ 21 ailettes par pouce) : plaques en secteur
d'anneau (r {f(pf['r_int_echangeur'])} → {f(pf['r_ext_echangeur'])} mm, {f(pf['secteur_echangeur_deg'][1] - pf['secteur_echangeur_deg'][0])}°) percées pour les 32 tubes,
perpendiculaires à l'axe ; l'air entre entre deux lamelles par l'extérieur et glisse vers le centre. Seule une tranche de
{f(lm['tranche_mm'])} mm ({lm['lamelles_dans_la_tranche']} lamelles) est dessinée ; sur tout le tube il y en aurait {lm['nombre_sur_le_tube']}
({f(lm['surface_m2'], 1)} m²), soit hA ≈ 560 W/K et Δp ≈ 40 Pa à 830 m³/h (ordre de grandeur, écoulement laminaire entre lamelles).
Utilise le mètre pour vérifier le pas.</p>
<div class="vue3d" id="vueFL"></div>
<div class="ctrl" id="ctrlFL"></div>
<div class="ctrl"><label><input type="checkbox" id="couperFL"> Couper dans l'épaisseur de la tranche</label>
<input type="range" id="planFL" min="-12" max="12" step="0.1" value="0" style="width:260px"> <span id="tplanFL"></span></div>
<div class="ctrl" id="vuesFL">Vue : </div>
<h3>Vue de coupe : tranche plissée ({tp_['n_plis']} dents)</h3>
<p class=aide>Même tranche de {f(lm['tranche_mm'])} mm. Chaque lamelle ({f(tp_['lamelle_mm'], 2)} mm au pas de {f(tp_['pas_mm'], 1)} mm,
{tp_['lamelles_dans_la_tranche']} dans la tranche) est une plaque pleine : <b>bord extérieur en zigzag</b> ({tp_['n_plis']} dents de
{f(tp_['largeur_dent_mm'])} mm, rainures jusqu'à r = {f(tp_['r_creux_mm'])} mm, pointes à r = {f(pf['r_ext_echangeur'])} mm) et <b>bord intérieur rond</b>
(r = {f(tp_['r_int_mm'])} mm). L'air entre par les rainures et les flancs des dents ({f(tp_['contour_entree_mm'])} mm de contour, soit
{f(tp_['surface_entree_m2'], 3)} m² sur le tube, ×1,6 l'enveloppe) puis traverse la lamelle vers le centre. Les {tp_['tubes']} tubes sont en
tournesol sur toute la lamelle, dents et anneau (entraxe mini {f(tp_['entraxe_mini_mm'], 1)} mm). {f(tp_['surface_lamelles_tube_complet_m2'], 1)} m²
de lamelles sur tout le tube. Estimation à 830 m³/h : hA ≈ 560 W/K, Δp ≈ 55 Pa (dont ≈ 20 Pa de sortie au rayon
{f(tp_['r_int_mm'])} mm) ; au pas de 1,2 mm : ≈ 430 W/K, ≈ 45 Pa.</p>
<div class="vue3d" id="vueFP"></div>
<div class="ctrl" id="ctrlFP"></div>
<div class="ctrl"><label><input type="checkbox" id="couperFP"> Couper dans l'épaisseur de la tranche</label>
<input type="range" id="planFP" min="-12" max="12" step="0.1" value="0" style="width:260px"> <span id="tplanFP"></span></div>
<div class="ctrl" id="vuesFP">Vue : </div>
<h3>Concept imprimé en 3D (tube Ø {f(2 * pi_['r_ext'] + 4)}) : profils porteurs de propane et lamelles décalées, sans et avec stries</h3>
<p class=aide>Deux tranches de {f(pi_['longueur_tranche'])} mm côte à côte, pour comparer : à gauche <b>sans stries</b> (bord extérieur rond), à droite
<b>avec stries</b> ({pi_['n_dents']} dents triangulaires de {f(pi_['largeur_dent'])} mm à la pointe, rainures jusqu'à r = {f(pi_['r_creux'])} mm).
Parois d'au moins {f(pi_['paroi'])} mm (impression 3D). <b>Noyau vide</b> jusqu'à r = {f(pi_['r_noyau'])} mm.
<b>{pi_['n_tubes']} canaux de propane</b> Ø {f(pi_['d_canal'], 1)}, chacun dans un profil elliptique de {f(pi_['profil_long'])} × {f(2 * (pi_['d_canal'] / 2 + pi_['paroi']), 1)} mm
aligné avec l'air, <b>répartis en tournesol sur tout le disque</b> (dents comprises) pour que la chaleur ait peu de chemin à faire dans les lamelles
(entraxe mini : {f(pi_['versions']['sans']['entraxe_mini_mm'], 1)} mm sans stries, {f(pi_['versions']['avec']['entraxe_mini_mm'], 1)} mm avec).
<b>Lamelles décalées</b> de {f(pi_['ep_lamelle'])} mm, jeu {f(pi_['jeu'], 1)} mm, en couronnes de {f(pi_['l_troncon'])} mm décalées d'un demi-pas ; une sur deux
supprimée sous r = {f(pi_['r_intercalaire'])} mm. Bord d'entrée de l'air : {f(pi_['versions']['sans']['contour_entree_mm'])} mm sans stries,
{f(pi_['versions']['avec']['contour_entree_mm'])} mm avec ; surface d'une lamelle : {f(pi_['versions']['sans']['surface_lamelle_cm2'])} cm² sans,
{f(pi_['versions']['avec']['surface_lamelle_cm2'])} cm² avec. Formes de principe, à comparer en CFD.</p>
<div class="vue3d" id="vueFI"></div>
<div class="ctrl" id="ctrlFI"></div>
<div class="ctrl"><label><input type="checkbox" id="couperFI"> Couper dans l'épaisseur de la tranche</label>
<input type="range" id="planFI" min="-12.5" max="12.5" step="0.1" value="0" style="width:260px"> <span id="tplanFI"></span></div>
<div class="ctrl" id="vuesFI">Vue : </div>
<div class=dessin style="max-width:1000px;margin-top:10px"><img src="data:image/png;base64,{img_q}" style="width:100%" alt="Coupe radiale des lamelles décalées"></div>
{bloc_maillage()}
{bloc_resultats()}
{secteur_html}

"""
    corps2d = corps2d.replace("<h2 id=variante-e>", vue_f + "<h2 id=variante-e>", 1)
    html = MODELE.replace("__CSS2D__", css2d).replace("__CROQUIS__", corps2d).replace("__OBJETS__", json.dumps(objets)).replace("__OBJETS_E__", json.dumps(objets_e)).replace("__OBJETS_F__", json.dumps(objets_f)).replace("__OBJETS_FL__", json.dumps(objets_fl)).replace("__OBJETS_FP__", json.dumps(objets_fp)).replace("__OBJETS_FI__", json.dumps(objets_fi)).replace("__MAILLAGES__", maillages_json()).replace("__OBJETS_DS__", json.dumps(bloc_domaine())).replace("__RES3D__", resultats_3d_json()).replace("__RES3DS__", resultats_3d_json(
        tuple(f"secteur_{m}{s_}" for s_ in ("_p6", "_p5", "") for m in ("decale4", "continu", "radiales")) + ("secteur_radiales_c15", "secteur_decale4_f05b", "secteur_decale4_f05", "secteur_decale4_m3", "secteur_decale4_f05b_m3", "secteur_decale4_f05b_m3y", "secteur_decale4_f05i_m3y", "secteur_decale4_f05v_m3y", "secteur_decale4_f05s_m3y"), "secteur",
        lambda k: k.replace("secteur_", "").replace("_m3y", "").replace("_m3", ""))).replace("__OBJETS_SP__", json.dumps(objets_sp)).replace("__TABLE__", table).replace("__L__", str(p["longueur"])).replace("__L2__", str(p["longueur"] / 2))
    out = D / "echangeur_radial.html"
    out.write_text(html)
    print(out, round(len(html) / 1e6, 2), "Mo")


MODELE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Échangeur radial A′</title>
<style>
:root { --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; } }
:root[data-theme="dark"] { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; }
* { box-sizing:border-box; }
body { margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1200px; margin:0 auto; padding:20px 16px 48px; }
h1 { font-size:22px; margin:0 0 4px; } .sous { color:var(--doux); margin:0 0 12px; font-size:14px; }
#vue, .vue3d { width:100%; height:640px; background:#fff; border:1px solid var(--trait); border-radius:10px; overflow:hidden; }
.ctrl { display:flex; flex-wrap:wrap; gap:6px 16px; margin:10px 0; font-size:14px; align-items:center; }
.ctrl label { display:flex; align-items:center; gap:5px; cursor:pointer; }
.pastille { width:12px; height:12px; border-radius:3px; display:inline-block; }
button { font:inherit; padding:3px 10px; border-radius:6px; border:1px solid var(--trait); background:var(--carte); color:var(--texte); cursor:pointer; }
.carte { background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:12px 14px; margin-top:12px; }
table { border-collapse:collapse; width:100%; font-size:14px; } td { padding:5px 8px; border-bottom:1px solid var(--trait); }
td.n { text-align:right; font-variant-numeric:tabular-nums; } .aide { color:var(--doux); font-size:13px; }
__CSS2D__
.etiq { position:absolute; background:rgba(33,37,41,.88); color:#fff; font:12px/1.3 system-ui,sans-serif; padding:3px 7px;
  border-radius:5px; pointer-events:none; transform:translate(-50%,-130%); white-space:nowrap; }
.ctrlM { display:grid; grid-template-columns:auto 1fr auto; gap:6px 12px; align-items:center; margin:10px 0; font-size:14px; }
.ctrlM input[type=range] { width:100%; } .ligne { display:flex; flex-wrap:wrap; gap:6px 14px; align-items:center; font-size:14px; margin:6px 0; }
button.actif { background:#1c7ed6; color:#fff; border-color:#1c7ed6; }
h2.partie { font-size:20px; margin:34px 0 4px; padding-top:14px; border-top:2px solid var(--trait); }
</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head><body><main>
<h1>Échangeur cylindrique à flux radial, variante A′</h1>
<p class="sous">Sommaire : <a href="#vue">modèle 3D</a> · <a href="#variante-f">variante F (tube droit, flux vers le haut)</a> · <a href="#maillage-cfd">maillage CFD 3D</a> · <a href="#resultats-cfd">résultats CFD</a> · <a href="#secteur-periodique">secteur périodique 1/8</a> · <a href="#variante-e">variante E (fer à cheval)</a> · <a href="#variante-d">variante D (soufflage par le haut)</a> · <a href="#croquis">croquis 2D, variantes A, A′, B, C, filtre et vitesses</a></p>
<p class="sous">Cylindre couché, aspiration à travers le manchon filtrant et l'échangeur plissé sur 280°, chambre centrale vide,
volute au-dessus, ventilateurs juste avant la bouche. Modèle FreeCAD paramétrique
(<code>outils/cad/echangeur_radial.py</code>, <code>parametres_radial.json</code>), sans les tubes de réfrigérant.</p>
<div id="vue"></div>
<div class="ctrl" id="ctrl"></div>
<div class="ctrl"><label><input type="checkbox" id="couper"> Couper le long de l'axe</label>
<input type="range" id="plan" min="0" max="__L__" step="1" value="__L2__" style="width:260px"> <span id="tplan"></span></div>
<div class="ctrl" id="vues">Vue : </div>
<p class="aide">Rotation libre au clic gauche, zoom à la molette, déplacement au clic droit. Bouton « Mètre » : deux clics sur
des pièces visibles donnent la distance en mm et ses composantes (masquer une pièce permet de viser celle de derrière). L'échangeur est représenté par une galette
pleine de 8 mm d'épaisseur pliée en accordéon ; les tubes plats et les ailettes ne sont pas dessinés. Les ventilateurs sont de principe
(2 × Ø 160 axiaux), à dimensionner.</p>
<div class="carte"><b>Dimensions</b><table>__TABLE__</table></div>

<h2 class="partie" id="croquis">Croquis 2D et variantes étudiées</h2>
__CROQUIS__
</main>
<script type="module">
import * as THREE from "three";
import { TrackballControls } from "three/addons/controls/TrackballControls.js";
const dec = s => new Float32Array(Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer);
async function visionneuse(id, OBJETS, VUES, nomPlan) {
  const $ = s => document.getElementById(s + id);
  const boite = $("vue");
  const rendu = new THREE.WebGLRenderer({ antialias: true }); rendu.setPixelRatio(window.devicePixelRatio);
  rendu.setClearColor(0xffffff); rendu.localClippingEnabled = true; boite.appendChild(rendu.domElement);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.3));
  const sol = new THREE.DirectionalLight(0xffffff, 1.0); sol.position.set(1, -2, 2); scene.add(sol);
  const cam = new THREE.PerspectiveCamera(35, 1, 1, 10000);
  const plan = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);   // garde y ≥ position
  const groupe = new THREE.Group(); scene.add(groupe);
  const ctrl = $("ctrl"), mats = [];
  for (const o of OBJETS) {
    let pos;
    if (o.gz) { const u = await degz(o.gz); pos = new Float32Array(u.length);
      for (let i = 0; i < u.length; i += 3) { pos[i] = o.o[0] + u[i] * o.s; pos[i + 1] = o.o[1] + u[i + 1] * o.s; pos[i + 2] = o.o[2] + u[i + 2] * o.s; } }
    else pos = dec(o.tri);
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.computeVertexNormals();
    const m = new THREE.MeshStandardMaterial({ color: o.couleur, side: THREE.DoubleSide, transparent: o.opacite < 1, opacity: o.opacite,
      depthWrite: o.opacite >= 1, metalness: 0.15, roughness: 0.6 });
    mats.push(m);
    const mesh = new THREE.Mesh(g, m); groupe.add(mesh);
    mesh.userData.onglet = o.onglet ? [].concat(o.onglet) : null;
    const l = document.createElement("label"); l.dataset.onglet = o.onglet || ""; mesh.userData.label = l;
    l.innerHTML = `<input type="checkbox" checked><span class="pastille" style="background:${o.couleur}"></span>${o.titre}`;
    l.querySelector("input").onchange = e => { mesh.visible = e.target.checked; };
    ctrl.appendChild(l);
  }
  // onglets (objets portant « onglet ») : un seul jeu visible à la fois, les objets sans onglet restent communs
  const onglets = [...new Set(OBJETS.flatMap(o => o.onglet ? [].concat(o.onglet) : []))], barre = $("onglets");
  if (onglets.length && barre) {
    const montrer = og => { for (const ms of groupe.children) { if (!ms.userData.onglet) continue;
        const on = ms.userData.onglet.includes(og); ms.userData.label.style.display = on ? "" : "none";
        ms.visible = on && ms.userData.label.querySelector("input").checked; }
      for (const b of barre.querySelectorAll("button")) b.classList.toggle("actif", b.textContent === og); };
    barre.append("Modèle : ");
    for (const og of onglets) { const b = document.createElement("button"); b.textContent = og; b.onclick = () => montrer(og); barre.append(b, " "); }
    montrer(onglets[0]);
  }
  const cb = $("couper"), sl = $("plan"), tp = $("tplan");
  function coupe() { plan.constant = -sl.value; tp.textContent = `${nomPlan} = ${sl.value} mm`;
    for (const m of mats) { m.clippingPlanes = cb.checked ? [plan] : []; m.needsUpdate = true; } }
  cb.onchange = coupe; sl.oninput = coupe; coupe();
  const bb = new THREE.Box3().setFromObject(groupe), c = bb.getCenter(new THREE.Vector3()), r = bb.getSize(new THREE.Vector3()).length();
  boite.style.position = "relative";

  // --- échelle : grille au sol (10 mm), lignes et repères chiffrés tous les 50 mm ---
  const echelle = new THREE.Group(); scene.add(echelle);
  {
    const x0 = Math.floor(bb.min.x / 50) * 50 - 50, x1 = Math.ceil(bb.max.x / 50) * 50 + 50;
    const y0 = Math.floor(bb.min.y / 50) * 50 - 50, y1 = Math.ceil(bb.max.y / 50) * 50 + 50, z = bb.min.z - 0.5;
    const fin = [], gros = [];
    for (let x = x0; x <= x1; x += 10) (x % 50 ? fin : gros).push(x, y0, z, x, y1, z);
    for (let y = y0; y <= y1; y += 10) (y % 50 ? fin : gros).push(x0, y, z, x1, y, z);
    for (const [pts, coul] of [[fin, 0xdee2e6], [gros, 0x868e96]]) {
      const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
      echelle.add(new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: coul })));
    }
    const texte = (s, x, y) => {
      const cv = document.createElement("canvas"); cv.width = 128; cv.height = 64; const k = cv.getContext("2d");
      k.font = "bold 40px system-ui,sans-serif"; k.fillStyle = "#495057"; k.textAlign = "center"; k.textBaseline = "middle"; k.fillText(s, 64, 32);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true }));
      sp.scale.set(24, 12, 1); sp.position.set(x, y, z); echelle.add(sp);
    };
    for (let x = x0; x <= x1; x += 50) texte(`${x}`, x, y0 - 12);
    for (let y = y0; y <= y1; y += 50) texte(`${y}`, x0 - 16, y);
    texte("x (mm)", (x0 + x1) / 2, y0 - 30); texte("y (mm)", x0 - 40, (y0 + y1) / 2);
  }
  const lE = document.createElement("label");
  lE.innerHTML = `<input type="checkbox" checked> Échelle (grille 10 mm, repères tous les 50 mm)`;
  lE.querySelector("input").onchange = e => { echelle.visible = e.target.checked; };
  ctrl.appendChild(lE);

  // --- mètre : deux clics sur des pièces visibles → distance et composantes ---
  let modeMetre = false, appui = null;
  const pts = [], metre = new THREE.Group(); scene.add(metre);
  const etiq = document.createElement("div"); etiq.className = "etiq"; etiq.style.display = "none"; boite.appendChild(etiq);
  const aideM = document.createElement("span"); aideM.className = "aide";
  const bM = document.createElement("button"); bM.textContent = "Mètre";
  const bX = document.createElement("button"); bX.textContent = "Effacer la mesure";
  const vider = () => { pts.length = 0; metre.clear(); etiq.style.display = "none"; };
  bM.onclick = () => { modeMetre = !modeMetre; bM.classList.toggle("actif", modeMetre);
    aideM.textContent = modeMetre ? "cliquer deux points sur les pièces (un 3e clic recommence)" : ""; };
  bX.onclick = vider;
  const outilsMetre = [" · ", bM, bX, aideM];
  const ray = new THREE.Raycaster(), rs = r * 0.006;
  const matM = new THREE.MeshBasicMaterial({ color: 0x1c7ed6, depthTest: false });
  rendu.domElement.addEventListener("pointerdown", e => { appui = [e.clientX, e.clientY]; });
  rendu.domElement.addEventListener("pointerup", e => {
    if (!modeMetre || !appui || e.button !== 0 || Math.hypot(e.clientX - appui[0], e.clientY - appui[1]) > 4) return;
    const rc = rendu.domElement.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2((e.clientX - rc.left) / rc.width * 2 - 1, -(e.clientY - rc.top) / rc.height * 2 + 1), cam);
    const vis = groupe.children.filter(m => m.visible);
    const hit = ray.intersectObjects(vis, false).find(h => !cb.checked || plan.distanceToPoint(h.point) >= 0);
    if (!hit) return;
    if (pts.length === 2) vider();
    pts.push(hit.point.clone());
    const b = new THREE.Mesh(new THREE.SphereGeometry(rs, 16, 12), matM); b.position.copy(hit.point); b.renderOrder = 10; metre.add(b);
    if (pts.length === 2) {
      const g = new THREE.BufferGeometry().setFromPoints(pts);
      const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x1c7ed6, depthTest: false })); l.renderOrder = 10; metre.add(l);
      const d = pts[1].clone().sub(pts[0]), f1 = v => v.toFixed(1).replace(".", ",");
      etiq.innerHTML = `<b>${f1(d.length())} mm</b> · Δx ${f1(Math.abs(d.x))} · Δy ${f1(Math.abs(d.y))} · Δz ${f1(Math.abs(d.z))}`;
      etiq.style.display = "block";
    }
  });
  const placeEtiq = () => {
    if (pts.length !== 2) return;
    const m = pts[0].clone().add(pts[1]).multiplyScalar(0.5).project(cam);
    etiq.style.left = `${(m.x + 1) / 2 * boite.clientWidth}px`; etiq.style.top = `${(1 - m.y) / 2 * boite.clientHeight}px`;
  };
  const ctl = new TrackballControls(cam, rendu.domElement); ctl.rotateSpeed = 3; ctl.target.copy(c);
  function vue(d, u) { cam.position.copy(c).add(new THREE.Vector3(...d).normalize().multiplyScalar(r * 1.5)); cam.up.set(...u);
    ctl.target.copy(c); cam.lookAt(c); ctl.update(); }
  for (const [n, d, u] of VUES) { const b = document.createElement("button"); b.textContent = n; b.onclick = () => vue(d, u); $("vues").append(b); }
  $("vues").append(...outilsMetre);
  vue(VUES[0][1], VUES[0][2]);
  scene.add(new THREE.AxesHelper(60));
  function taille() { const w = boite.clientWidth, h = boite.clientHeight; rendu.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); ctl.handleResize(); }
  new ResizeObserver(taille).observe(boite); taille();
  (function boucle() { requestAnimationFrame(boucle); ctl.update(); placeEtiq(); rendu.render(scene, cam); })();
}
visionneuse("", __OBJETS__, [["3D", [1.1, -1, 0.8], [0, 0, 1]], ["Bout", [0, -1, 0], [0, 0, 1]], ["Face (bouche)", [1, 0, 0], [0, 0, 1]],
  ["Dessus", [0, 0, 1], [0, 1, 0]], ["Dessous", [0, 0, -1], [0, 1, 0]]], "y");
visionneuse("F", __OBJETS_F__, [["3D", [1.2, -0.9, 0.8], [0, 0, 1]], ["Bout (coupe)", [0, -1, 0], [0, 0, 1]], ["Face (depuis la pièce)", [1, 0, 0], [0, 0, 1]],
  ["Dessus", [0, 0, 1], [1, 0, 0]], ["Dessous", [0, 0, -1], [1, 0, 0]]], "y");
visionneuse("FL", __OBJETS_FL__, [["3D", [1, -1.2, 0.7], [0, 0, 1]], ["Bout (coupe)", [0, -1, 0], [0, 0, 1]], ["Dessus", [0, 0, 1], [1, 0, 0]],
  ["Face (depuis la pièce)", [1, 0, 0], [0, 0, 1]]], "y");
visionneuse("FP", __OBJETS_FP__, [["3D", [1, -1.2, 0.7], [0, 0, 1]], ["Bout (coupe)", [0, -1, 0], [0, 0, 1]], ["Dessus", [0, 0, 1], [1, 0, 0]],
  ["Face (depuis la pièce)", [1, 0, 0], [0, 0, 1]]], "y");
visionneuse("FI", __OBJETS_FI__, [["3D", [1, -1.2, 0.7], [0, 0, 1]], ["Bout (coupe)", [0, -1, 0], [0, 0, 1]], ["Dessus", [0, 0, 1], [1, 0, 0]],
  ["Face (depuis la pièce)", [1, 0, 0], [0, 0, 1]]], "y");
const MAILLAGES = __MAILLAGES__;
async function degz(b64) {
  if (!b64) return new Uint16Array(0);
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const flux = new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Uint16Array(await new Response(flux).arrayBuffer());
}
async function vueMaillage() {
  const boite = document.getElementById("vueM");
  if (!boite || !Object.keys(MAILLAGES).length) return;
  const rendu = new THREE.WebGLRenderer({ antialias: true }); rendu.setPixelRatio(window.devicePixelRatio); rendu.setClearColor(0xffffff);
  boite.appendChild(rendu.domElement);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.3));
  const dl = new THREE.DirectionalLight(0xffffff, 0.9); dl.position.set(1, -2, 2); scene.add(dl);
  const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 5000);
  const ctl = new TrackballControls(cam, rendu.domElement); ctl.rotateSpeed = 3;
  const mS = new THREE.MeshStandardMaterial({ color: 0x868e96, transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide });
  const solide = new THREE.Mesh(new THREE.BufferGeometry(), mS); scene.add(solide);
  const COUL = { x: 0xe03131, y: 0x1c7ed6, z: 0x2f9e44 }, lignes = {};
  for (const ax of "xyz") { lignes[ax] = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: COUL[ax] })); scene.add(lignes[ax]); }
  let D = null, cache = {};
  const versF = u => { const f = new Float32Array(u.length); for (let i = 0; i < u.length; i += 3) {
    f[i] = D.o[0] + u[i] * D.s; f[i + 1] = D.o[1] + u[i + 1] * D.s; f[i + 2] = D.o[2] + u[i + 2] * D.s; } return f; };
  const maj = async ax => { const sl = document.getElementById("s" + ax + "M"), L = D.coupes[ax], i = +sl.value, k = ax + i;
    if (!cache[k]) cache[k] = versF(await degz(L[i][1]));
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(cache[k], 3));
    lignes[ax].geometry.dispose(); lignes[ax].geometry = g;
    document.getElementById("t" + ax + "M").textContent = `${ax} = ${L[i][0].toFixed(2).replace(".", ",")} mm`; };
  async function charger(v) {
    D = MAILLAGES[v]; cache = {};
    const gS = new THREE.BufferGeometry(); gS.setAttribute("position", new THREE.BufferAttribute(versF(await degz(D.solide)), 3)); gS.computeVertexNormals();
    solide.geometry.dispose(); solide.geometry = gS;
    for (const ax of "xyz") { const sl = document.getElementById("s" + ax + "M"); const L = D.coupes[ax];
      const garde = sl.value !== "" && +sl.max === L.length - 1 ? +sl.value : Math.floor(L.length / 2);
      sl.min = 0; sl.max = L.length - 1; sl.step = 1; sl.value = garde; sl.oninput = () => maj(ax); await maj(ax); }
    for (const b of document.querySelectorAll("#versionsM button")) b.classList.toggle("actif", b.dataset.v === v);
  }
  for (const v of Object.keys(MAILLAGES)) { const b = document.createElement("button"); b.dataset.v = v; b.textContent = v === "sans" ? "Sans stries" : "Avec stries";
    b.onclick = () => charger(v); document.getElementById("versionsM").append(b, " "); }
  for (const ax of "xyz") document.getElementById("c" + ax + "M").onchange = e => { lignes[ax].visible = e.target.checked; };
  document.getElementById("csM").onchange = e => { solide.visible = e.target.checked; };
  document.getElementById("osM").oninput = e => { mS.opacity = +e.target.value; };
  await charger(Object.keys(MAILLAGES)[0]);
  document.getElementById("chargeM").remove();
  const bb = new THREE.Box3().setFromObject(solide), c = bb.getCenter(new THREE.Vector3()), r = bb.getSize(new THREE.Vector3()).length();
  const VUES = [["3D", [1, -1.4, 0.8], [0, 0, 1]], ["Le long du tube (y)", [0, -1, 0], [0, 0, 1]], ["Dessus (z)", [0, 0, 1], [1, 0, 0]], ["Côté (x)", [1, 0, 0], [0, 0, 1]]];
  const vue = (d, u) => { cam.position.copy(c).add(new THREE.Vector3(...d).normalize().multiplyScalar(r * 1.3)); cam.up.set(...u); ctl.target.copy(c); cam.lookAt(c); ctl.update(); };
  for (const [n, d, u] of VUES) { const b = document.createElement("button"); b.textContent = n; b.onclick = () => vue(d, u); document.getElementById("vuesM").append(b, " "); }
  vue(VUES[0][1], VUES[0][2]);
  const taille = () => { const w = boite.clientWidth, h = boite.clientHeight; rendu.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); ctl.handleResize(); };
  new ResizeObserver(taille).observe(boite); taille();
  (function boucle() { requestAnimationFrame(boucle); ctl.update(); rendu.render(scene, cam); })();
}
vueMaillage();
const RES3D = __RES3D__;
const RES3DS = __RES3DS__;
async function vueResultats(sfx, RES3D) {
  const $R = id => document.getElementById(id + sfx);
  const boite = $R("vueR");
  if (!boite || !Object.keys(RES3D).length) return;
  const PAL = { viridis: [[68,1,84],[72,40,120],[62,74,137],[49,104,142],[38,130,142],[31,158,137],[53,183,121],[109,205,89],[180,222,44],[253,231,37]],
    inferno: [[0,0,4],[40,11,84],[101,21,110],[159,42,99],[212,72,66],[245,125,21],[250,193,39],[252,255,164]],
    coolwarm: [[59,76,192],[98,130,234],[141,176,254],[184,208,249],[221,221,221],[245,196,173],[244,154,123],[222,96,77],[180,4,38]] };
  const CHOIX = { U: "viridis", T: "inferno", p: "coolwarm" };
  const palette = nom => { const s = PAL[nom], t = new Uint8Array(256 * 4);
    for (let i = 0; i < 255; i++) { const x = i / 254 * (s.length - 1), a = Math.floor(Math.min(x, s.length - 2)), f = x - a;
      for (let c = 0; c < 3; c++) t[i * 4 + c] = Math.round(s[a][c] * (1 - f) + s[a + 1][c] * f); t[i * 4 + 3] = 255; } return t; };
  const rendu = new THREE.WebGLRenderer({ antialias: true }); rendu.setPixelRatio(window.devicePixelRatio); rendu.setClearColor(0xffffff);
  boite.appendChild(rendu.domElement);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.3));
  const dl = new THREE.DirectionalLight(0xffffff, 0.9); dl.position.set(1, -2, 2); scene.add(dl);
  const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 5000);
  const ctl = new TrackballControls(cam, rendu.domElement); ctl.rotateSpeed = 3;
  const mS = new THREE.MeshStandardMaterial({ color: 0x868e96, transparent: true, opacity: 0.25, depthWrite: false, side: THREE.DoubleSide });
  const solide = new THREE.Mesh(new THREE.BufferGeometry(), mS); scene.add(solide);
  const lutTex = new THREE.DataTexture(new Uint8Array(256 * 4), 256, 1); lutTex.minFilter = lutTex.magFilter = THREE.NearestFilter;
  const uni = { vol: { value: null }, lut: { value: lutTex }, o: { value: new THREE.Vector3() }, dim: { value: new THREE.Vector3() }, pas: { value: 1 } };
  const mat = new THREE.ShaderMaterial({ glslVersion: THREE.GLSL3, uniforms: uni, side: THREE.DoubleSide,
    vertexShader: `out vec3 vp; void main(){ vp = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `precision highp float; precision highp sampler3D;
      uniform sampler3D vol; uniform sampler2D lut; uniform vec3 o, dim; uniform float pas; in vec3 vp; out vec4 fc;
      void main(){ vec3 u = (floor((vp - o) / pas + 0.5) + 0.5) / dim;
        if (any(lessThan(u, vec3(0.0))) || any(greaterThan(u, vec3(1.0)))) discard;
        float k = floor(texture(vol, u).r * 255.0 + 0.5); if (k > 254.5) discard;
        fc = texture(lut, vec2((k + 0.5) / 256.0, 0.5)); }` });
  const COUL = [0xe03131, 0x2f9e44, 0x1c7ed6], plans = [];
  for (let a = 0; a < 3; a++) { const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(12), 3));
    g.setIndex([0, 1, 2, 0, 2, 3]); const m = new THREE.Mesh(g, mat); scene.add(m);
    const gb = new THREE.BufferGeometry(); gb.setAttribute("position", g.attributes.position);     // contour sans la diagonale
    const bord = new THREE.LineLoop(gb, new THREE.LineBasicMaterial({ color: COUL[a] })); scene.add(bord); plans.push([m, bord]); }
  let G = null, cas = null, champ = "T"; const cacheT = {};
  const o = () => G.origine_mm, pas = () => G.pas_mm, N = () => G.dim;
  const placer = a => { const n = N(), c = o()[a] + (+$R("s" + "xyz"[a] + "R").value) * pas();
    const hi = o().map((x, i) => x + (n[i] - 1) * pas()), [u, v] = [[1, 2], [0, 2], [0, 1]][a], p = [];
    for (const [su, sv] of [[0, 0], [1, 0], [1, 1], [0, 1]]) { const q = [0, 0, 0]; q[a] = c; q[u] = su ? hi[u] : o()[u]; q[v] = sv ? hi[v] : o()[v]; p.push(...q); }
    const at = plans[a][0].geometry.attributes.position; at.array.set(p); at.needsUpdate = true;
    plans[a][0].geometry.computeBoundingSphere(); plans[a][1].geometry.computeBoundingSphere(); $R("t" + "xyz"[a] + "R").textContent = `${"xyz"[a]} = ${c.toFixed(2).replace(".", ",")} mm`; };
  async function texture(k, ch) { const cle = k + ch; if (cacheT[cle]) return cacheT[cle];
    const brut = Uint8Array.from(atob(RES3D[k].champs[ch].donnees), c => c.charCodeAt(0));
    const v = new Uint8Array(await new Response(new Blob([brut]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer());
    const n = RES3D[k].dim, tex = new THREE.Data3DTexture(v, n[0], n[1], n[2]);
    tex.format = THREE.RedFormat; tex.type = THREE.UnsignedByteType; tex.minFilter = tex.magFilter = THREE.NearestFilter; tex.unpackAlignment = 1; tex.needsUpdate = true;
    return (cacheT[cle] = tex); }
  const fmt = x => (Math.abs(x) >= 100 ? x.toFixed(0) : Math.abs(x) >= 10 ? x.toFixed(1) : x.toFixed(2)).replace(".", ",");
  async function afficher() {
    uni.vol.value = await texture(cas, champ);
    const t = palette(CHOIX[champ]); lutTex.image.data.set(t); lutTex.needsUpdate = true;
    const b = $R("barreR").getContext("2d"), im = b.createImageData(256, 1);
    for (let i = 0; i < 256; i++) { const q = Math.min(254, Math.round(i / 255 * 254)); im.data.set(t.subarray(q * 4, q * 4 + 4), i * 4); }
    b.putImageData(im, 0, 0);
    const c = G.champs[champ]; $R("bminR").textContent = fmt(c.min);
    $R("bmaxR").textContent = fmt(c.max) + (c.max_reel > c.max * 1.001 ? ` (max ${fmt(c.max_reel)})` : "");
  }
  async function charger(k) {
    cas = k; G = RES3D[k];
    uni.o.value.set(...G.origine_mm); uni.dim.value.set(...G.dim); uni.pas.value = G.pas_mm;
    const u = await degz(G.solide.gz), f = new Float32Array(u.length);
    for (let i = 0; i < u.length; i += 3) { f[i] = G.solide.o[0] + u[i] * G.solide.s; f[i + 1] = G.solide.o[1] + u[i + 1] * G.solide.s; f[i + 2] = G.solide.o[2] + u[i + 2] * G.solide.s; }
    const gS = new THREE.BufferGeometry(); gS.setAttribute("position", new THREE.BufferAttribute(f, 3)); gS.computeVertexNormals();
    solide.geometry.dispose(); solide.geometry = gS;
    for (let a = 0; a < 3; a++) { const s = $R("s" + "xyz"[a] + "R"), n = G.dim[a];
      const garde = s.value !== "" && +s.max === n - 1; s.min = 0; s.max = n - 1; s.step = 1;
      if (!garde) { let v0 = a === 1 ? Math.round(n / 4) : Math.round((0 - G.origine_mm[a]) / G.pas_mm * (a === 0 ? 1.4 : 1));
        if (v0 <= 0 || v0 >= n - 1) v0 = Math.round(n / 2); s.value = v0; }
      s.value = Math.max(0, Math.min(n - 1, +s.value)); s.oninput = () => placer(a); placer(a); }
    for (const b of document.querySelectorAll(`#casR${sfx} button`)) b.classList.toggle("actif", b.dataset.k === k);
    await afficher();
  }
  const NOMS = { continu: "Lamelles continues", decale4: "Décalées, espace 4 mm", sans: "Décalées sans espace (défaut)", avec: "Avec stries (défaut)",
    secteur_decale4: "Décalées, écart 1,5", secteur_continu: "Continues, écart 1,5", secteur_radiales: "Radiales, écart 1,5 (défaut)",
    secteur_decale4_p5: "Décalées, écart 4", secteur_continu_p5: "Continues, écart 4", secteur_radiales_p5: "Radiales, écart 4",
    secteur_decale4_p6: "Décalées, écart 5", secteur_continu_p6: "Continues, écart 5", secteur_radiales_p6: "Radiales, écart 5",
    secteur_radiales_c15: "Radiales, écart 1,5 corrigé", secteur_decale4_f05: "Décalées, lamelles 0,5 mm (non valable)",
    secteur_decale4_f05b: "Décalées, lamelles 0,5 mm (infirmé)",
    secteur_decale4_m3: "Décalées, écart 1,5 — MAILLAGE FIN", secteur_decale4_f05b_m3: "Décalées, lamelles 0,5 mm — maillage fin (raccord faux)",
    secteur_decale4_f05b_m3y: "Décalées 0,5 mm — corrigé (14/11)", secteur_decale4_f05i_m3y: "Imbriquées 0,5 mm (14/11)",
    secteur_decale4_f05v_m3y: "Vague 0,5 mm (14/11)", secteur_decale4_f05s_m3y: "Décalées 0,5 mm avec dents (14/11)" };
  for (const k of Object.keys(RES3D)) { const b = document.createElement("button"); b.dataset.k = k; b.textContent = NOMS[k] || k; b.onclick = () => charger(k);
    $R("casR").append(b, " "); }
  const sel = $R("champR");
  for (const [k, n] of [["T", "Température θ"], ["U", "Vitesse |U| (m/s)"], ["p", "Pression (Pa)"]]) sel.add(new Option(n, k));
  sel.value = champ; sel.onchange = () => { champ = sel.value; afficher(); };
  for (let a = 0; a < 3; a++) $R("c" + "xyz"[a] + "R").onchange = e => { plans[a][0].visible = plans[a][1].visible = e.target.checked; };
  $R("csR").onchange = e => { solide.visible = e.target.checked; };
  $R("osR").oninput = e => { mS.opacity = +e.target.value; };
  await charger(Object.keys(RES3D)[0]);
  const bb = new THREE.Box3().setFromObject(solide), c = bb.getCenter(new THREE.Vector3()), r = bb.getSize(new THREE.Vector3()).length();
  const VUES = [["3D", [1, -1.4, 0.8], [0, 0, 1]], ["Le long du tube (y)", [0, -1, 0], [0, 0, 1]], ["Dessus (z)", [0, 0, 1], [1, 0, 0]], ["Côté (x)", [1, 0, 0], [0, 0, 1]]];
  const vue = (d, u) => { cam.position.copy(c).add(new THREE.Vector3(...d).normalize().multiplyScalar(r * 1.3)); cam.up.set(...u); ctl.target.copy(c); cam.lookAt(c); ctl.update(); };
  for (const [n, d, u] of VUES) { const b = document.createElement("button"); b.textContent = n; b.onclick = () => vue(d, u); $R("vuesR").append(b, " "); }
  vue(VUES[1][1], VUES[1][2]);
  const taille = () => { const w = boite.clientWidth, h = boite.clientHeight; rendu.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); ctl.handleResize(); };
  new ResizeObserver(taille).observe(boite); taille();
  (function boucle() { requestAnimationFrame(boucle); ctl.update(); rendu.render(scene, cam); })();
}
vueResultats("", RES3D);
vueResultats("S", RES3DS);
if (document.getElementById("vueSP")) visionneuse("SP", __OBJETS_SP__, [["3D", [1.2, -1.4, 0.9], [0, 0, 1]], ["Bout (le long du tube)", [0, -1, 0], [0, 0, 1]],
  ["Dessus", [0, 0, 1], [1, 0, 0]], ["Côté", [1, 0, 0], [0, 0, 1]]], "y");
if (document.getElementById("vueDS")) visionneuse("DS", __OBJETS_DS__, [["3D", [0.6, -1.2, 0.9], [0, 0, 1]], ["Le long du tube", [0, -1, 0], [0, 0, 1]],
  ["Dessus", [0, 0, 1], [1, 0, 0]], ["Côté", [1, 0, 0], [0, 0, 1]]], "y");
visionneuse("E", __OBJETS_E__, [["3D", [1.2, -0.9, 0.9], [0, 0, 1]], ["Dessus", [0, 0, 1], [1, 0, 0]], ["Face (depuis la pièce)", [1, 0, 0], [0, 0, 1]],
  ["Côté", [0, -1, 0], [0, 0, 1]], ["Dessous", [0, 0, -1], [1, 0, 0]]], "y");
</script></body></html>"""

if __name__ == "__main__":
    main()
