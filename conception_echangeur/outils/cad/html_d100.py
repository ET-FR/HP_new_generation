"""Fiche HTML autonome de l'échangeur Ø 100 : dimensions, cotes, vue 3D interactive, rendus.
    .venv/bin/python conception_echangeur/outils/cad/html_d100.py [dossier]   → <dossier>/echangeur_d100.html
    (défaut docs/formes/cylindre_d100 ; variante 32 tubes en tournesol : docs/formes/cylindre_d100_t32)
Lit dimensions.json et les .stl produits par outils/cad/echangeur_d100.py (FreeCAD) et les vues de
outils/cad/rendu_d100.py. Les STL sont allégés puis intégrés en base64 : le fichier s'ouvre seul,
sans serveur (seul three.js vient d'un CDN)."""
import base64
import json
import math
import sys
from datetime import date
from pathlib import Path

import pyvista as pv

RACINE = Path(__file__).resolve().parents[2]
D = (RACINE / sys.argv[1]) if len(sys.argv) > 1 else RACINE / "docs/formes/cylindre_d100"
SORTIE = D / "echangeur_d100.html"
PIECES = [("enveloppe", "Tube principal et conduits d'air", "#74c0fc", 0.25),
          ("noyau", "Noyau central", "#868e96", 0.6),
          ("tubes", "Tubes d'échange", "#d6336c", 1.0),
          ("arbre_entree", "Arbre de Murray, entrée", "#e8590c", 1.0),
          ("arbre_sortie", "Arbre de Murray, sortie", "#1c7ed6", 1.0)]
RHO_LIQ = 0.47  # g/cm³, propane liquide vers 45 °C (ordre de grandeur)


def stl_b64(nom, cible=30000):
    m = pv.read(D / f"{nom}.stl").triangulate()
    if m.n_cells > cible:
        m = m.decimate_pro(1 - cible / m.n_cells, preserve_topology=True)
    tmp = D / f"_{nom}_leger.stl"
    m.save(tmp, binary=True)
    b = base64.b64encode(tmp.read_bytes()).decode()
    tmp.unlink()
    return b


def png_b64(nom):
    return base64.b64encode((D / nom).read_bytes()).decode()


def f(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


def svg_bout(d):
    """Vue de bout cotée : tube principal, noyau, tubes (couronne ou tournesol)."""
    p = d["parametres"]
    s = 3.2  # px/mm
    cx, cy = 250, 215
    ri, re = p["d_int_principal"] / 2, p["d_int_principal"] / 2 + p["ep_principal"]
    rn, rc, rt = p["d_noyau"] / 2, p["r_couronne"], d["od_tubes_echange_mm"] / 2
    o = [f'<svg viewBox="0 0 500 440" class="plan" role="img" aria-label="Vue de bout cotée">']
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{re*s}" class="paroi"/><circle cx="{cx}" cy="{cy}" r="{ri*s}" class="air"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{rn*s}" class="noyau"/>')
    tour = p.get("disposition") == "tournesol"
    rayons = p["r_tournesol"] if tour else [rc]
    for r in rayons:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r*s}" class="axe"/>')
    # vue depuis +x (côté entrée du propane), z vers le haut : à droite = +y, en bas = +x du repère FreeCAD
    for x, y in d["feuilles_xy_mm"]:
        o.append(f'<circle cx="{cx+y*s:.1f}" cy="{cy+x*s:.1f}" r="{rt*s:.1f}" class="tube"/>')
    # cotes
    y = cy + re * s + 28
    o.append(f'<line x1="{cx-ri*s}" y1="{y}" x2="{cx+ri*s}" y2="{y}" class="cote"/>')
    o.append(f'<text x="{cx}" y="{y+16}" class="t">Ø int. {f(2*ri,0)} (paroi {f(p["ep_principal"],0)}, Ø ext. {f(2*re,0)})</text>')
    rr = max(rayons)
    o.append(f'<line x1="{cx}" y1="{cy}" x2="{cx+rr*s*0.7071:.1f}" y2="{cy-rr*s*0.7071:.1f}" class="cote"/>')
    txt = f"tubes de R {f(rayons[0],0)} à R {f(rayons[1],0)}" if tour else f"R {f(rc)} (couronne)"
    o.append(f'<text x="{cx+rr*s*0.7071+40}" y="{cy-rr*s*0.7071-14}" class="t petit">{txt}</text>')
    o.append(f'<text x="{cx}" y="{cy+5}" class="t petit">noyau Ø {f(2*rn,0)}</text>')
    o.append(f'<text x="{cx}" y="{cy+rr*s+30}" class="t petit">{d["n_tubes"]} tubes Ø {f(2*rt,2)} × {f(p["id_murray"][-1],2)}'
             f'{" en tournesol (angle d’or 137,5°)" if tour else ""}</text>')
    o.append(f'<text x="{cx}" y="22" class="t">Vue de bout côté entrée du propane (sans les arbres)</text></svg>')
    return "".join(o)


def svg_cote(d):
    """Vue de côté cotée selon l'axe : arbres, fonds, chambres d'air, zone d'échange."""
    p = d["parametres"]
    L, P, ef = p["l_active"], p["plenum"], p["ep_fond"]
    la, lt, gf = d["longueur_arbre_mm"], p["l_tube_entree"], p["garde_fond"]
    tot = d["encombrement_mm"]["longueur_hors_tout"]
    s = 920 / tot
    x0 = 20
    X = lambda mm: x0 + (mm + lt + la + gf + ef + P) * s  # mm depuis le début de la zone active
    ri = p["d_int_principal"] / 2 + p["ep_principal"]
    cy, h = 175, ri * s * 1.25
    o = [f'<svg viewBox="0 0 960 400" class="plan" role="img" aria-label="Vue de côté cotée">']
    o.append(f'<rect x="{X(-P-ef):.1f}" y="{cy-h:.1f}" width="{(L+2*P+2*ef)*s:.1f}" height="{2*h:.1f}" class="paroi"/>')
    o.append(f'<rect x="{X(0):.1f}" y="{cy-h:.1f}" width="{L*s:.1f}" height="{2*h:.1f}" class="zone"/>')
    for z in (-P - ef, L + P):
        o.append(f'<rect x="{X(z):.1f}" y="{cy-h:.1f}" width="{ef*s:.1f}" height="{2*h:.1f}" class="fond"/>')
    for sg in (-1, 1):
        o.append(f'<line x1="{X(-P-ef-gf):.1f}" y1="{cy+sg*h*0.62:.1f}" x2="{X(L+P+ef+gf):.1f}" y2="{cy+sg*h*0.62:.1f}" class="tubeL"/>')
    # arbres (schématiques) et tubes 3/8
    for a, b, c in ((X(-P-ef-gf-la), X(-P-ef-gf), "sortie"), (X(L+P+ef+gf), X(L+P+ef+gf+la), "entree")):
        g, dd = (b, a) if c == "sortie" else (a, b)
        o.append(f'<path d="M{dd:.1f},{cy} C{(a+b)/2:.1f},{cy} {(a+b)/2:.1f},{cy-h*0.62:.1f} {g:.1f},{cy-h*0.62:.1f} '
                 f'M{dd:.1f},{cy} C{(a+b)/2:.1f},{cy} {(a+b)/2:.1f},{cy+h*0.62:.1f} {g:.1f},{cy+h*0.62:.1f}" class="arbre {c}"/>')
    o.append(f'<line x1="{x0}" y1="{cy}" x2="{X(-P-ef-gf-la):.1f}" y2="{cy}" class="entree3 sortie"/>')
    o.append(f'<line x1="{X(L+P+ef+gf+la):.1f}" y1="{cy}" x2="{x0+tot*s:.1f}" y2="{cy}" class="entree3 entree"/>')
    # flèches de sens
    o.append(f'<text x="{x0+tot*s-4:.1f}" y="{cy+h*0.62+26:.1f}" class="t droite fl-p">← propane entre (3/8")</text>')
    o.append(f'<text x="{x0+4}" y="{cy+h*0.62+26:.1f}" class="t gauche fl-p">← sort (3/8")</text>')
    o.append(f'<text x="{X(-P/2):.1f}" y="{cy+h+18:.1f}" class="t petit fl-a">air entre ↑</text>')
    o.append(f'<text x="{X(L+P/2):.1f}" y="{cy-h-8:.1f}" class="t petit fl-a">air sort ↑</text>')
    o.append(f'<text x="{X(L/2):.1f}" y="{cy+4}" class="t petit">air en rotation, de gauche à droite →</text>')

    def cote(a, b, y, txt):
        o.append(f'<line x1="{X(a):.1f}" y1="{y}" x2="{X(b):.1f}" y2="{y}" class="cote"/>'
                 f'<line x1="{X(a):.1f}" y1="{y-5}" x2="{X(a):.1f}" y2="{y+5}" class="cote"/>'
                 f'<line x1="{X(b):.1f}" y1="{y-5}" x2="{X(b):.1f}" y2="{y+5}" class="cote"/>'
                 f'<text x="{(X(a)+X(b))/2:.1f}" y="{y-6}" class="t petit">{txt}</text>')
    yb = cy + h + 46
    cote(0, L, yb, f"zone d'échange {f(L,0)}")
    cote(-P - ef, -ef, yb, f"{f(P,0)}")
    cote(L + ef, L + P + ef, yb, f"{f(P,0)}")
    cote(-P - ef, L + P + ef, yb + 34, f"tube principal {f(d['encombrement_mm']['longueur_tube_principal'],0)}")
    cote(L + P + ef + gf, L + P + ef + gf + la, cy - h - 34, f"arbre {f(la,0)}")
    cote(-P - ef - gf - la - lt, L + P + ef + gf + la + lt, yb + 68, f"hors tout {f(tot,0)}")
    o.append("</svg>")
    return "".join(o)


def main():
    d = json.loads((D / "dimensions.json").read_text())
    p = d["parametres"]
    v = d["volume_interne_cm3"]
    nt = d["n_tubes"]
    nmax = len(p["id_murray"]) - 1
    tour = p.get("disposition") == "tournesol"
    stl = {n: stl_b64(n) for n, *_ in PIECES}
    img = {n: png_b64(n) for n in ("vue_ensemble.png", "vue_arbre.png", "vue_bout.png")}

    lignes_murray = "".join(
        f"<tr><td>{x['niveau']}</td><td>{x['branches']}</td><td class='n'>{f(x['id_mm'],2)}</td><td class='n'>{f(x['od_mm'],2)}</td>"
        f"<td class='n'>{'—' if x['rapport_parent_enfant'] is None else f(x['rapport_parent_enfant'],3)}</td>"
        f"<td>{'tube 3/8&quot; (donné)' if x['niveau']==0 else (f'{nt} tubes d’échange' if x['niveau']==nmax else 'branche imprimée')}</td></tr>"
        for x in d["niveaux_murray"])
    enc = d["encombrement_mm"]
    pieces_js = json.dumps([{"nom": n, "titre": t, "couleur": c, "opacite": o} for n, t, c, o in PIECES])
    stl_js = json.dumps(stl)
    ri, P, L = p["d_int_principal"] / 2, p["plenum"], p["l_active"]
    a = p["angle_conduit_deg"]
    r_m = (p["d_noyau"] / 2 + ri) / 2
    tours_ideal = (L + P) / (2 * math.pi * r_m * math.tan(math.radians(a)))
    bornes = [pv.read(D / f"{n}.stl").bounds for n, *_ in PIECES]
    geom = {"ri": ri, "ep": p["ep_principal"], "w": p["conduit_larg"], "lc": p["conduit_long"], "P": P, "L": L,
            "angle": a, "r_noyau": p["d_noyau"] / 2, "tours_ideal": round(tours_ideal, 2),
            "x_min": min(b[0] for b in bornes), "x_max": max(b[1] for b in bornes)}
    script_js = ((Path(__file__).with_name("vue3d_d100.js")).read_text()
                 .replace("__PIECES__", pieces_js).replace("__STL__", stl_js).replace("__GEOM__", json.dumps(geom)))

    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Échangeur cylindrique Ø 100</title>
<style>
:root {{ --fond:#f8f9fa; --carte:#ffffff; --texte:#212529; --doux:#495057; --trait:#dee2e6; --accent:#1c7ed6; --air-debut:#15aabf; --air-fin:#f59f00;
  --paroi:#a5d8ff; --air:#e7f5ff; --noyau:#adb5bd; --tube:#d6336c; --entree:#e8590c; --sortie:#1c7ed6; --zone:#d0ebff; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --fond:#141517; --carte:#1f2023; --texte:#e9ecef;
  --doux:#adb5bd; --trait:#373a40; --paroi:#1c4f7a; --air:#17283a; --noyau:#5c636a; --zone:#1b3550; }} }}
:root[data-theme="dark"] {{ --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40;
  --paroi:#1c4f7a; --air:#17283a; --noyau:#5c636a; --zone:#1b3550; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; }} h2 {{ font-size:19px; margin:36px 0 10px; }}
.sous {{ color:var(--doux); margin:0 0 20px; }}
.carte {{ background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:16px; }}
#vue3d {{ width:100%; height:520px; border-radius:10px; background:var(--carte); border:1px solid var(--trait); position:relative; overflow:hidden; }}
#vue3d canvas {{ display:block; }}
.etiquettes {{ position:absolute; top:0; left:0; pointer-events:none; }}
.et {{ font-size:11px; color:var(--texte); white-space:nowrap; }}
.et.regle {{ color:var(--doux); }} .et.titre {{ font-size:12px; font-weight:600; }}
.et.bout {{ transform:translateX(50%); }} .et.axe {{ font-weight:700; font-size:13px; }}
.et.marque {{ background:var(--carte); border:1px solid var(--accent); border-radius:5px; padding:1px 6px;
  transform:translateY(-16px); font-variant-numeric:tabular-nums; }}
.outils {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px 14px; margin:10px 0 0; font-size:14px; }}
.vues {{ display:flex; gap:6px; align-items:center; }} .outils button {{ font:inherit; padding:4px 12px; border-radius:6px; border:1px solid var(--trait);
  background:var(--carte); color:var(--texte); cursor:pointer; }}
.outils button.actif {{ border-color:var(--accent); background:var(--accent); color:#fff; }}
.outils input[type=range] {{ width:140px; }}
#mesure {{ font-variant-numeric:tabular-nums; color:var(--doux); min-height:1.5em; margin-top:6px; font-size:14px; }}
.ctrl {{ display:flex; flex-wrap:wrap; gap:8px 16px; margin:10px 0 0; font-size:14px; }}
.ctrl label {{ display:flex; align-items:center; gap:6px; cursor:pointer; }}
.pastille {{ width:12px; height:12px; border-radius:3px; display:inline-block; }}
.aide {{ color:var(--doux); font-size:13px; margin-top:6px; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--trait); }}
th {{ color:var(--doux); font-weight:600; }}
td.n, th.n {{ text-align:right; font-variant-numeric:tabular-nums; }}
.grille {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }}
.plan {{ width:100%; height:auto; }}
.plan .paroi {{ fill:var(--paroi); stroke:var(--doux); stroke-width:1; }}
.plan .air {{ fill:var(--air); }} .plan .zone {{ fill:var(--zone); }}
.plan .noyau {{ fill:var(--noyau); }} .plan .fond {{ fill:var(--doux); }}
.plan .axe {{ fill:none; stroke:var(--doux); stroke-dasharray:4 4; stroke-width:1; }}
.plan .tube {{ fill:var(--tube); }} .plan .tubeL {{ stroke:var(--tube); stroke-width:3; }}
.plan .arbre {{ fill:none; stroke-width:3; }} .plan .entree {{ stroke:var(--entree); }} .plan .sortie {{ stroke:var(--sortie); }}
.plan .entree3 {{ stroke-width:5; }}
.plan .cote {{ stroke:var(--texte); stroke-width:1; }}
.plan .t {{ fill:var(--texte); font-size:13px; text-anchor:middle; }} .plan .petit {{ font-size:11.5px; }}
.plan .droite {{ text-anchor:end; }} .plan .gauche {{ text-anchor:start; }}
.plan .fl-p {{ fill:var(--entree); font-weight:600; }} .plan .fl-a {{ fill:var(--accent); font-weight:600; }}
.rendus img {{ width:100%; border-radius:8px; border:1px solid var(--trait); background:#fff; }}
.rendus figure {{ margin:0; }} figcaption {{ color:var(--doux); font-size:13px; margin-top:4px; }}
ul {{ padding-left:20px; }} li {{ margin:4px 0; }}
.hyp {{ color:var(--doux); }}
@media (max-width:600px) {{ #vue3d {{ height:360px; }} h1 {{ font-size:22px; }} }}
</style>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}</script>
</head><body><main>
<h1>Échangeur cylindrique Ø 100 mm</h1>
<p class="sous">Version du {date.today().strftime('%d/%m/%Y')} · modèle FreeCAD paramétrique
(<code>outils/cad/echangeur_d100.py</code>) · enveloppe et circuit du propane, sans ailettes.</p>

<div class="carte">
<p style="margin-top:0">Un tube principal de <b>Ø {f(p['d_int_principal'],0)} mm</b> contient <b>{nt} tubes</b> de propane parallèles à
son axe. Le propane entre par un tube 3/8" côté droit. Un <b>arbre de Murray 1 → {nt}</b> le répartit, et un arbre identique
le regroupe à gauche. L'air entre tangentiellement à gauche, avance en tournant dans l'anneau entre le noyau et la
paroi, puis sort à droite : il circule <b>à contre-courant</b> du propane.</p>
</div>

<h2>Vue 3D</h2>
<div id="vue3d"></div>
<div class="ctrl" id="ctrl"></div>
<div class="outils" id="outils">
<button data-mode="marqueur">Marqueur</button><button data-mode="regle">Règle (2 points)</button>
<button data-act="effacer">Effacer</button>
<label>Tours de l'air <input type="range" id="tours" min="0" step="1"> <span id="tours_val"></span></label>
<label>Vitesse <input type="range" id="vitesse" min="20" max="600" step="10" value="150"></label>
</div>
<div id="mesure"></div>
<p class="aide">Repère : x le long de l'axe (0 = début de la zone d'échange, l'air avance vers +x), z vertical,
r = distance à l'axe ; cotes en mm. <b>Marqueur</b> : un clic sur une pièce affiche ses coordonnées.
<b>Règle</b> : deux clics donnent la distance et ses composantes. Masquer l'enveloppe pour atteindre les tubes.<br>
<b>Animation</b> : trajectoire idéale de l'air (couleur = avancement, de l'entrée à la sortie). Sans ailettes ni aubes, la
rotation s'amortit le long du tube : le nombre réel de tours est plus faible que l'idéal
(≈ {f(tours_ideal,1)} tours, si l'hélice gardait l'angle d'entrée de {f(a,1)}°). Le curseur montre l'effet.<br>
Clic gauche : tourner dans tous les sens (boutons « Vue » pour revenir à une vue standard) · molette : zoom · clic droit : déplacer. Les maillages sont allégés pour la vue ;
le modèle exact est dans <code>echangeur_d100.FCStd</code> et <code>echangeur_d100.step</code>.</p>

<h2>Plans cotés (mm)</h2>
<div class="carte">{svg_cote(d)}</div>
<div class="grille" style="margin-top:16px">
<div class="carte">{svg_bout(d)}</div>
<div class="carte">
<table>
<tr><th>Encombrement</th><th class="n">mm</th></tr>
<tr><td>Longueur hors tout (tubes 3/8" compris)</td><td class="n">{f(enc['longueur_hors_tout'],0)}</td></tr>
<tr><td>Longueur du tube principal (fonds compris)</td><td class="n">{f(enc['longueur_tube_principal'],0)}</td></tr>
<tr><td>Zone d'échange</td><td class="n">{f(p['l_active'],0)}</td></tr>
<tr><td>Chambre d'air à chaque bout</td><td class="n">{f(p['plenum'],0)}</td></tr>
<tr><td>Diamètre extérieur</td><td class="n">{f(enc['diametre_exterieur'],0)}</td></tr>
<tr><td>Largeur avec les conduits d'air</td><td class="n">{f(enc['largeur_avec_conduits'],0)}</td></tr>
<tr><td>Longueur d'un arbre (axe → tubes)</td><td class="n">{f(d['longueur_arbre_mm'],0)}</td></tr>
</table>
</div>
</div>

<h2>Arbre de Murray (1 → {nt})</h2>
<div class="carte">
<table>
<tr><th>Niveau</th><th>Branches</th><th class="n">Ø int. (mm)</th><th class="n">Ø ext. (mm)</th><th class="n">Ø parent / Ø enfant</th><th>Nature</th></tr>
{lignes_murray}
</table>
<p class="aide">Loi de Murray : Ø parent = 2^(1/3) × Ø enfant ≈ 1,26. Divisions en Y doux : chaque branche part en
s'écartant d'environ 30 à 45°, glisse le long de la couronne et arrive dans l'axe du tube. Tous les circuits ont le même
chemin. Niveau 1 : de l'axe vers la couronne sur {f(p['dz_niveau1'],0)} mm ; niveaux 2 à 4 : {f(p['dz_niveaux'],0)} mm chacun.</p>
</div>

<h2>Tubes, anneau d'air et volumes</h2>
<div class="grille">
<div class="carte"><table>
<tr><th>Tubes et anneau</th><th class="n">Valeur</th></tr>
<tr><td>Tubes d'échange (Ø ext. × Ø int.)</td><td class="n">{f(d['od_tubes_echange_mm'],2)} × {f(p['id_murray'][-1],2)} mm</td></tr>
<tr><td>Longueur d'un tube (fond à fond + gardes)</td><td class="n">{f(d['longueur_tubes_mm'],0)} mm</td></tr>
{f"<tr><td>Rayons des tubes (tournesol, un rayon par tube)</td><td class='n'>{f(p['r_tournesol'][0],0)} à {f(p['r_tournesol'][1],0)} mm</td></tr>" if tour else f"<tr><td>Rayon de la couronne</td><td class='n'>{f(p['r_couronne'])} mm</td></tr>"}
<tr><td>Écart minimal entre deux tubes</td><td class="n">{f(d['ecart_entre_tubes_mm'],2)} mm</td></tr>
<tr><td>Jeu tube / paroi · tube / noyau (minimum)</td><td class="n">{f(d['jeu_tube_paroi_mm'],2)} · {f(d['jeu_tube_noyau_mm'],2)} mm</td></tr>
<tr><td>Section de passage de l'air (anneau − tubes)</td><td class="n">{f(d['section_air_anneau_cm2'])} cm²</td></tr>
<tr><td>Surface extérieure des tubes dans la zone d'échange</td><td class="n">{f(d['surface_ext_tubes_zone_active_m2'],4)} m²</td></tr>
<tr><td>Conduits d'air tangentiels (radial × axial)</td><td class="n">{f(p['conduit_larg'],0)} × {f(p['conduit_haut'],0)} mm</td></tr>
<tr><td>Inclinaison des conduits vers l'aval (axe)</td><td class="n">{f(p['angle_conduit_deg'],1)}°</td></tr>
</table></div>
<div class="carte"><table>
<tr><th>Volume intérieur côté propane</th><th class="n">cm³</th><th class="n">g si plein de liquide</th></tr>
<tr><td>Arbre d'entrée (avec 40 mm de 3/8")</td><td class="n">{f(v['arbre_entree'],2)}</td><td class="n">{f(v['arbre_entree']*RHO_LIQ)}</td></tr>
<tr><td>{nt} tubes</td><td class="n">{f(v['tubes'],2)}</td><td class="n">{f(v['tubes']*RHO_LIQ)}</td></tr>
<tr><td>Arbre de sortie (avec 40 mm de 3/8")</td><td class="n">{f(v['arbre_sortie'],2)}</td><td class="n">{f(v['arbre_sortie']*RHO_LIQ)}</td></tr>
<tr><td><b>Total</b></td><td class="n"><b>{f(v['total'],2)}</b></td><td class="n"><b>{f(v['total']*RHO_LIQ)}</b></td></tr>
</table>
<p class="aide">Masse : borne haute avec ≈ {f(RHO_LIQ,2)} g/cm³ (propane liquide vers 45 °C, ordre de grandeur). En
fonctionnement, une grande partie du volume contient de la vapeur : la charge réelle est plus faible.</p></div>
</div>

<h2>Données et hypothèses</h2>
<div class="carte">
<p style="margin-top:0"><b>Données :</b> tube principal Ø {f(p['d_int_principal'],0)} mm ; entrée et sortie du propane en
tube 3/8" (Ø {f(p['od_entree'],2)} × {f(p['id_entree'],2)} mm) ; arbre de Murray 1 → {nt} avec les Ø intérieurs
{", ".join(f(x,2) for x in p['id_murray'])} mm.</p>
<p class="hyp"><b>Hypothèses que j'ai prises par défaut</b> (toutes réglables dans
<code>outils/cad/parametres_d100.json</code>) :</p>
<ul class="hyp">
<li>100 mm = diamètre <b>intérieur</b> ; paroi de {f(p['ep_principal'],0)} mm, fonds de {f(p['ep_fond'],0)} mm.</li>
<li>Zone d'échange de {f(p['l_active'],0)} mm ; chambre d'air de {f(p['plenum'],0)} mm à chaque bout pour les conduits.</li>
<li>Noyau central plein de Ø {f(p['d_noyau'],0)} mm ; {"niveaux 1 à " + str(nmax-1) + f" sur une couronne de R {f(p['r_couronne'])} mm, puis dernier niveau en tournesol : tube i au rayon √(r₁² + (i + ½)(r₂² − r₁²)/{nt}) et à l’angle i × 137,5°, motif tourné de {f(p.get('rotation_tournesol_deg',0),0)}° et tubes attribués deux à deux aux nœuds de la couronne pour raccourcir les branches (affectation optimale). Branches du dernier niveau de {f(p['dz_dernier'],0)} mm selon l’axe ; leurs longueurs diffèrent de quelques mm, ≈ 1 % d’un circuit." if tour else f"couronne des tubes au milieu de l'anneau (R {f(p['r_couronne'])} mm)."}</li>
<li>Paroi des branches imprimées et des {nt} tubes : {f(p['ep_branche'],1)} mm.</li>
<li>Axe horizontal ; les arbres sont à l'extérieur des fonds, que les tubes traversent.</li>
<li>Conduits d'air rectangulaires {f(p['conduit_larg'],0)} × {f(p['conduit_haut'],0)} mm, tangents à la paroi et inclinés de {f(p['angle_conduit_deg'],1)}° vers l'aval :
l'air entre déjà en hélice. Angle par défaut tel que tan α = section du conduit / section de l'anneau
(rapport des vitesses axiale et tangentielle à débit égal) ; réglable par <code>angle_conduit_deg</code>.</li>
</ul>
</div>

<h2>Points ouverts</h2>
<div class="carte"><ul style="margin:0">
<li><b>Surface d'échange :</b> les tubes nus offrent {f(d['surface_ext_tubes_zone_active_m2'],3)} m². Les ailettes restent à dessiner
(longitudinales ou en hélice).</li>
<li><b>Débit d'air :</b> la section de {f(d['section_air_anneau_cm2'],0)} cm² laisse passer ≈
{f(d['section_air_anneau_cm2']*1e-4*2*3600,0)} m³/h à 2 m/s. Un module transporte donc quelques centaines de watts :
il en faudrait plusieurs pour une PAC de fenêtre.</li>
<li><b>Orientation :</b> avec l'axe horizontal, l'eau de condensation stagne en bas du tube principal. À trancher : axe
vertical ou point de purge.</li>
<li><b>Fabrication :</b> passage étanche des tubes à travers les fonds, ou impression en une seule pièce.</li>
</ul></div>

<h2>Rendus</h2>
<div class="grille rendus">
<figure><img alt="Ensemble" src="data:image/png;base64,{img['vue_ensemble.png']}"><figcaption>Ensemble, enveloppe transparente</figcaption></figure>
<figure><img alt="Arbre d'entrée" src="data:image/png;base64,{img['vue_arbre.png']}"><figcaption>Arbre de Murray d'entrée (1 → {nt})</figcaption></figure>
<figure><img alt="Vue de bout" src="data:image/png;base64,{img['vue_bout.png']}"><figcaption>Vue de bout côté entrée</figcaption></figure>
</div>
</main>
<script type="module">
{script_js}
</script>
</body></html>"""
    SORTIE.write_text(html)
    print(SORTIE, f"{SORTIE.stat().st_size/1e6:.1f} Mo")


if __name__ == "__main__":
    main()
