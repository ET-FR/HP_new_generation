"""Fiche HTML autonome de l'échangeur Ø 150 à canal hélicoïdal : vue 3D interactive, dimensions, contrôles.
    .venv/bin/python conception_echangeur/outils/cad/html_d150.py   → docs/formes/cylindre_d150_helice/echangeur_d150.html
Lit dimensions.json, les .stl (outils/cad/echangeur_d150.py) et les vues (outils/cad/rendu_d150.py).
Les STL sont allégés puis intégrés en base64 : le fichier s'ouvre seul (three.js vient d'un CDN)."""
import base64
import json
import math
from datetime import date
from pathlib import Path

import pyvista as pv

ICI = Path(__file__).resolve().parent
D = ICI.parents[1] / "docs/formes/cylindre_d150_helice"
SORTIE = D / "echangeur_d150.html"
# nom, titre, couleur, opacité, visible au départ
PIECES = [("enveloppe", "Tube principal, fonds et conduits d'air", "#74c0fc", 0.22, True),
          ("noyau", "Noyau central", "#868e96", 1.0, True),
          ("ailette", "Ailette hélicoïdale et remplissages (aluminium)", "#adb5bd", 1.0, True),
          ("tubes", "32 tubes d'échange (aluminium)", "#d6336c", 1.0, True),
          ("domaine_air", "Domaine d'air (volume à mailler)", "#15aabf", 0.35, False)]


def stl_b64(nom, cible=40000):
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
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",").replace("-", "−")


def table(entetes, lignes):
    o = ["<table><tr>" + "".join(f'<th class="{"n" if i else ""}">{h}</th>' for i, h in enumerate(entetes)) + "</tr>"]
    for l in lignes:
        o.append("<tr>" + "".join(f'<td class="{"n" if i else ""}">{c}</td>' for i, c in enumerate(l)) + "</tr>")
    return "".join(o) + "</table>"


def svg_dessus(d):
    """Vue de dessus cotée : tube, noyau, canal, tubes en tournesol (numérotés), conduits."""
    p, r = d["parametres"], d["rayons_mm"]
    s, cx, cy = 2.6, 260, 250
    o = ['<svg viewBox="0 0 560 500" class="plan" role="img" aria-label="Vue de dessus cotée">']
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r["exterieur"]*s}" class="paroi"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{r["interieur"]*s}" class="air"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{r["noyau"]*s}" class="noyau"/>')
    for rr in (r["tubes_min"], r["tubes_max"]):
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{rr*s:.1f}" class="axe"/>')
    for i, (x, y) in enumerate(d["tubes"]["positions_xy_mm"]):
        X, Y = cx + x * s, cy - y * s
        o.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{p["od_tube"]/2*s:.1f}" class="tube"/>'
                 f'<text x="{X:.1f}" y="{Y-6:.1f}" class="t mini">{i}</text>')
    o.append(f'<line x1="{cx-r["interieur"]*s}" y1="{cy+r["exterieur"]*s+24}" x2="{cx+r["interieur"]*s}" '
             f'y2="{cy+r["exterieur"]*s+24}" class="cote"/>'
             f'<text x="{cx}" y="{cy+r["exterieur"]*s+42}" class="t">Ø int. {f(2*r["interieur"],0)} · Ø ext. {f(2*r["exterieur"],0)}</text>')
    o.append(f'<text x="{cx}" y="{cy+4}" class="t petit">noyau Ø {f(2*r["noyau"],0)}</text>')
    o.append(f'<text x="{cx}" y="22" class="t">Vue de dessus : 32 tubes en tournesol (numéro = ordre du motif)</text></svg>')
    return "".join(o)


def main():
    d = json.loads((D / "dimensions.json").read_text())
    p, r, he, tu = d["parametres"], d["rayons_mm"], d["helice"], d["tubes"]
    stl = {n: stl_b64(n) for n, *_ in PIECES}
    img = {n: png_b64(n) for n in ("vue_ensemble.png", "vue_coupe.png", "vue_air.png", "vue_tournesol.png")}
    geom = dict(Ro=r["exterieur"], Ri=r["interieur"], Rc=r["noyau"], ep=p["ep_principal"], Lint=d["longueur_interieure_mm"],
                gap=p["conduit_axial"], pas=he["pas_mm"], tours=he["tours"], Ld=p["conduit_long"],
                ta=math.tan(math.radians(d.get("conduits", {}).get("inclinaison_deg", 0.0))))
    js = ((ICI / "vue3d_d150.js").read_text()
          .replace("__PIECES__", json.dumps([dict(nom=n, titre=t, couleur=c, opacite=o, visible=v) for n, t, c, o, v in PIECES]))
          .replace("__STL__", json.dumps(stl)).replace("__GEOM__", json.dumps(geom)))
    sec = d["section_canal_meridienne"]
    n_tr = {k: int(v["canal_mm2"] / d["section_conduit_mm2"] + 0.02) for k, v in sec.items()}
    reste = {k: v["canal_mm2"] - n_tr[k] * d["section_conduit_mm2"] for k, v in sec.items()}
    ecarts = tu["ecarts_indice_plus_proches_voisins"]
    vol = d["volumes_cm3"]
    rho_al = 2.70
    lignes_dim = [
        ["Tube principal : Ø ext. × paroi × longueur (fonds compris)", f"{f(2*r['exterieur'],0)} × {f(p['ep_principal'],0)} × {f(p['longueur_principal'],0)} mm"],
        ["Longueur intérieure (entre fonds)", f"{f(d['longueur_interieure_mm'],0)} mm"],
        ["Noyau", f"Ø {f(2*r['noyau'],0)} mm"],
        ["Conduits d'air (axial × radial), longueur dessinée", f"{f(p['conduit_axial'],0)} × {f(p['conduit_radial'],0)} mm, {f(p['conduit_long'],0)} mm"],
        ["Section du conduit", f"{f(d['section_conduit_mm2'],0)} mm²"],
        ["Conduits : inclinaison (pente de l'hélice au rayon moyen), paroi conduit / canal",
         f"{f(d['conduits']['inclinaison_deg'],1)}°, {f(d['conduits']['ep_separation_mm'],0)} mm" if "conduits" in d else "—"],
        ["Ailette hélicoïdale : épaisseur, pas", f"{f(p['ep_ailette'],1)} mm, {f(he['pas_mm'],0)} mm"],
        ["Nombre de tours de l'air", f"{f(he['tours'],2)}"],
        ["Angle de sortie (entrée à 0°)", f"{f(he['angle_sortie_deg'],1)}°"],
        ["Angle de l'hélice (noyau / milieu / paroi)", " / ".join(f(v, 1) + "°" for v in he["angle_helice_deg"].values())],
        ["Longueur du chemin moyen", f"{f(he['longueur_chemin_moyen_mm'],0)} mm"],
        ["Tubes : nombre, Ø ext. × Ø int., matériau", f"{tu['n']}, {f(p['od_tube'],2)} × {f(p['id_tube'],2)} mm, {p['materiau_tubes']}"],
        ["Tubes : rayons des axes, dépassement de chaque fond", f"{f(r['tubes_min'],1)} à {f(r['tubes_max'],1)} mm, {f(p['depassement_tube'],0)} mm"],
        ["Écart minimal entre tubes (axes / parois)", f"{f(tu['ecart_min_axes_mm'],1)} / {f(tu['ecart_min_parois_mm'],1)} mm"],
        ["Surface des tubes dans l'air · surface de l'ailette", f"{f(tu['surface_ext_dans_air_m2'],3)} m² · {f(d['surface_ailette_m2'],3)} m²"],
    ]
    lignes_vol = [[{"enveloppe": "Enveloppe", "noyau": "Noyau", "ailette": "Ailette + remplissages", "tubes": "Tubes",
                    "domaine_air": "Domaine d'air"}[k], f(v, 1),
                   f(v * rho_al, 0) if k in ("ailette", "tubes") else "—"] for k, v in vol.items()]
    lignes_sec = [[f"{k}°", str(n_tr[k]) + (" + conduit" if reste[k] > 50 else ""), f(v["canal_mm2"], 0),
                   f(d["section_conduit_mm2"], 0) if reste[k] > 50 else f(v["canal_mm2"] / max(n_tr[k], 1), 0)]
                  for k, v in sec.items()]
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Échangeur Ø 150 hélice</title>
<style>
:root {{ --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; --accent:#1c7ed6;
  --air-debut:#15aabf; --air-fin:#f59f00; --paroi:#a5d8ff; --air:#e7f5ff; --noyau:#adb5bd; --tube:#d6336c; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --fond:#141517; --carte:#1f2023; --texte:#e9ecef;
  --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; --paroi:#1c4f7a; --air:#17283a; --noyau:#5c636a; }} }}
:root[data-theme="dark"] {{ --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40;
  --accent:#4dabf7; --paroi:#1c4f7a; --air:#17283a; --noyau:#5c636a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; }} h2 {{ font-size:19px; margin:32px 0 10px; }}
.sous {{ color:var(--doux); margin:0 0 18px; }}
.carte {{ background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:14px 16px; overflow-x:auto; }}
#vue3d {{ width:100%; height:620px; border-radius:10px; background:var(--carte); border:1px solid var(--trait); position:relative; overflow:hidden; }}
#vue3d canvas {{ display:block; }}
.etiquettes {{ position:absolute; top:0; left:0; pointer-events:none; }}
.et {{ font-size:11px; color:var(--texte); white-space:nowrap; }}
.et.regle {{ color:var(--doux); }} .et.titre {{ font-size:12px; font-weight:600; }} .et.bout {{ transform:translateX(40%); }}
.et.axe {{ font-weight:700; font-size:13px; }}
.et.marque {{ background:var(--carte); border:1px solid var(--accent); border-radius:5px; padding:1px 6px; transform:translateY(-16px); }}
.ctrl, .outils {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px 16px; margin:10px 0 0; font-size:14px; }}
.ctrl label, .outils label {{ display:flex; align-items:center; gap:6px; cursor:pointer; }}
.pastille {{ width:12px; height:12px; border-radius:3px; display:inline-block; }}
.vues {{ display:flex; gap:6px; align-items:center; }} .outils button {{ font:inherit; padding:4px 12px; border-radius:6px; border:1px solid var(--trait); background:var(--carte); color:var(--texte); cursor:pointer; }}
.outils button.actif {{ border-color:var(--accent); background:var(--accent); color:#fff; }}
#mesure {{ font-variant-numeric:tabular-nums; color:var(--doux); min-height:1.5em; margin-top:6px; font-size:14px; }}
.aide {{ color:var(--doux); font-size:13px; margin-top:6px; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ text-align:left; padding:6px 9px; border-bottom:1px solid var(--trait); }}
th {{ color:var(--doux); font-weight:600; }} td.n, th.n {{ text-align:right; font-variant-numeric:tabular-nums; }}
.grille {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:14px; }}
.plan {{ width:100%; height:auto; }}
.plan .paroi {{ fill:var(--paroi); }} .plan .air {{ fill:var(--air); }} .plan .noyau {{ fill:var(--noyau); }}
.plan .axe {{ fill:none; stroke:var(--doux); stroke-dasharray:4 4; }} .plan .tube {{ fill:var(--tube); }}
.plan .cote {{ stroke:var(--texte); }} .plan .t {{ fill:var(--texte); font-size:13px; text-anchor:middle; }}
.plan .petit {{ font-size:11.5px; }} .plan .mini {{ font-size:8.5px; fill:var(--doux); }}
.rendus img {{ width:100%; border-radius:8px; border:1px solid var(--trait); background:#fff; }}
figure {{ margin:0; }} figcaption {{ color:var(--doux); font-size:13px; }}
code {{ font-size:13px; }} ul {{ padding-left:20px; }} li {{ margin:3px 0; }}
@media (max-width:600px) {{ #vue3d {{ height:420px; }} }}
</style>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}</script>
</head><body><main>
<h1>Échangeur Ø 150 à canal d'air hélicoïdal</h1>
<p class="sous">Version du {date.today().strftime('%d/%m/%Y')} · modèle FreeCAD paramétrique
(<code>outils/cad/echangeur_d150.py</code>, paramètres <code>parametres_d150.json</code>) · modèle pour la simulation, sans arbres de Murray.</p>

<div class="carte">L'air entre par le conduit du bas, tangent à la paroi, et suit un canal en hélice formé par une ailette
d'aluminium : <b>{f(he['tours'],1)} tours</b> sur {f(d['longueur_interieure_mm'],0)} mm, section du canal égale à celle du
conduit ({f(d['section_conduit_mm2'],0)} mm²). Il ressort par le conduit du haut, décalé de {f(he['angle_sortie_deg'],0)}°.
Les deux conduits sont inclinés de la pente de l'hélice ({f(d['conduits']['inclinaison_deg'],0) if 'conduits' in d else '0'}°) : ils la prolongent
en ligne droite et passent sous le fond (entrée) et au-dessus du fond (sortie). Une paroi de 2 mm les sépare du tour qu'ils longent,
ce qui supprime les raccourcis vus dans la CFD du 11/11.
Les <b>{tu['n']} tubes</b> d'aluminium sont parallèles à l'axe, en tournesol, et traversent l'ailette.</div>

<h2>Vue 3D</h2>
<div id="vue3d"></div>
<div class="ctrl" id="ctrl"></div>
<div class="outils" id="outils">
<button data-mode="marqueur">Marqueur</button><button data-mode="regle">Règle (2 points)</button>
<button data-act="effacer">Effacer</button>
<label>Vitesse de l'animation <input type="range" id="vitesse" min="20" max="800" step="10" value="200"></label>
</div>
<div id="mesure"></div>
<p class="aide">Repère : z le long de l'axe (0 = face intérieure du fond bas), x et y dans le plan ; r = distance à
l'axe ; mm. <b>Marqueur</b> : un clic sur une pièce affiche ses coordonnées. <b>Règle</b> : deux clics donnent la distance.
Masquer l'enveloppe ou l'ailette pour atteindre les pièces intérieures. Cocher « Domaine d'air » pour voir le volume
qui sera maillé. Clic gauche : tourner dans tous les sens (boutons « Vue » pour revenir à une vue standard) · molette : zoom · clic droit : déplacer. Maillages allégés pour la vue.</p>

<h2>Dimensions</h2>
<div class="grille">
<div class="carte">{table(["Grandeur", "Valeur"], lignes_dim)}</div>
<div class="carte">{svg_dessus(d)}</div>
</div>

<h2>Contrôles</h2>
<div class="grille">
<div class="carte"><b>Section du canal = section du conduit</b>
{table(["Plan méridien", "Tours coupés", "Section totale mm²", "Par tour mm²"], lignes_sec)}
<p class="aide">Chaque plan contenant l'axe coupe le canal autant de fois qu'il y a de tours à cet angle ; à 315°
il coupe aussi le conduit d'entrée.</p></div>
<div class="carte"><b>Disposition en tournesol</b>
<p>Tube n à r = √(r₁² + (n + ½)(r₂² − r₁²)/{tu['n']}) et à l'angle n × 137,5° (angle d'or), une aire égale par tube.</p>
<p>Écart de numéro entre plus proches voisins : {", ".join(f"<b>{k}</b> ({v} fois)" for k, v in ecarts.items())}.
5, 8 et 13 sont des nombres de Fibonacci : ce sont les familles de spirales (8 et 13) d'un cœur de tournesol.</p></div>
<div class="carte"><b>Volumes et masses</b>
{table(["Pièce", "Volume cm³", "Masse alu g"], lignes_vol)}
<p class="aide">Le domaine d'air est d'un seul tenant (contrôle du script). Masse à 2,70 g/cm³ ; matériau de
l'enveloppe et du noyau non défini.</p></div>
</div>

<h2>Fichiers</h2>
<div class="carte"><ul style="margin:0">
<li><code>echangeur_d150.FCStd</code> : modèle FreeCAD, 5 pièces avec une propriété « Materiau ».</li>
<li><code>echangeur_d150.step</code> : toutes les pièces ; <b><code>domaine_air.step</code> / <code>domaine_air.stl</code></b> : le volume d'air seul, à mailler.</li>
<li><code>enveloppe.stl</code>, <code>noyau.stl</code>, <code>ailette.stl</code>, <code>tubes.stl</code> ; <code>dimensions.json</code>.</li>
<li>Régénérer : modifier <code>outils/cad/parametres_d150.json</code>, relancer <code>echangeur_d150.py</code> (FreeCAD, ≈ 3 min),
<code>rendu_d150.py</code> puis <code>html_d150.py</code>.</li>
</ul></div>

<h2>Hypothèses à valider</h2>
<div class="carte"><ul style="margin:0">
<li>Option retenue : 400 mm et section du canal = section du conduit, d'où {f(he['tours'],1)} tours (10 tours
demanderaient ≈ 1,1 m de long).</li>
<li>Ailette de {f(p['ep_ailette'],1)} mm ; conduits de {f(p['conduit_long'],0)} mm, droits (une inclinaison ferait
traverser un fond) : c'est l'ailette qui fait monter l'air.</li>
<li>Sous le premier tour et au-dessus du dernier, l'espace entre fond et ailette est plein (pas de zone morte).</li>
<li>Pas constant : l'hélice fait {" / ".join(f(v, 0) + "°" for v in he["angle_helice_deg"].values())} au noyau, au milieu et à la paroi.</li>
<li>Tubes de Ø {f(p['od_tube'],2)} × {f(p['id_tube'],2)} mm (niveau 5 de Murray), à {f(p['jeu_tube'],0)} mm au moins du noyau et de la paroi.</li>
</ul></div>

<h2>Rendus</h2>
<div class="grille rendus">
<figure><img alt="Ensemble" src="data:image/png;base64,{img['vue_ensemble.png']}"><figcaption>Ensemble</figcaption></figure>
<figure><img alt="Coupe" src="data:image/png;base64,{img['vue_coupe.png']}"><figcaption>Coupe : ailette et tubes</figcaption></figure>
<figure><img alt="Air" src="data:image/png;base64,{img['vue_air.png']}"><figcaption>Domaine d'air</figcaption></figure>
<figure><img alt="Tournesol" src="data:image/png;base64,{img['vue_tournesol.png']}"><figcaption>Vue de dessus</figcaption></figure>
</div>
</main>
<script type="module">
{js}
</script>
</body></html>"""
    SORTIE.write_text(html)
    print(SORTIE, f"{SORTIE.stat().st_size/1e6:.1f} Mo")


if __name__ == "__main__":
    main()
