#!/usr/bin/env python3
"""
Rapport général en HTML : docs/rapport_cfd.html (+ dossier docs/rapport_cfd/).

Reprend toutes les pages de docs/resultats_cfd.pdf (images, sommaire cliquable) et y insère les vues 3D
interactives des cas à ailettes (outils/cfd_3d/vue3d_ailettes.py) après la page de l'étape 3.
Appelé à la fin de outils/cfd_2d/rapport_pdf.py ; à lancer seul :

    python outils/cfd_2d/rapport_html.py

La figure 3D est mise en cache (docs/rapport_cfd/vue3d.json) : sur une machine sans les cas 3D
(cfd_campagne/, hors dépôt), le cache est réutilisé.
"""
from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
DOCS = RACINE / "docs"
PDF = DOCS / "resultats_cfd.pdf"
SORTIE = DOCS / "rapport_cfd.html"
DOSSIER = DOCS / "rapport_cfd"
CAS_3D = RACINE / "cfd_campagne" / "ailettes" / "resultats"
ORDRE_3D = ["rond_ail1.8", "ellipse2_ail1.8", "rond_ail1.8_r2", "ellipse2_ail1.8_r2", "rond_ail2.5",
            "rond_ail1.8_ond", "ellipse2_ail1.8_r2_bord", "rond_gyroide6", "ellipse2_r2_gyroide6"]  # convergence (t20, t40) : non affichée


def titres_pages():
    txt = subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True, check=True).stdout
    titres = []
    for page in txt.split("\f"):
        lignes = [l.strip() for l in page.splitlines() if l.strip()]
        if lignes:
            titres.append(lignes[0])
    return titres


def pages_images():
    d = DOSSIER / "pages"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    subprocess.run(["pdftoppm", "-r", "140", "-jpeg", "-jpegopt", "quality=85", str(PDF), str(d / "p")], check=True)
    return sorted(d.glob("p-*.jpg"))


def figure_3d():
    """Figure plotly (dict JSON) ; recalculée si les cas sont présents, sinon cache."""
    cache = DOSSIER / "vue3d.json"
    cas = [CAS_3D / c for c in ORDRE_3D if (CAS_3D / c / "resultat.json").exists()]
    if cas:
        sys.path.insert(0, str(RACINE / "outils" / "cfd_3d"))
        from vue3d_ailettes import figure
        fig = figure([str(c) for c in cas], hauteur=760)
        cache.write_text(fig.to_json())
    return cache.read_text() if cache.exists() else None


def groupe(titre, k):
    """Rubrique du sommaire."""
    if k < 12:
        return None
    if titre.startswith("Géométries"):
        return "Géométries"
    if any(m in titre for m in ("Validation", "Maillages de validation", "convergence", "premier maillage", "Test 3D")):
        return "Validation et tests"
    return "Vues CFD de chaque cas"


CSS = """
:root { --bleu:#1c3d6e; --gris:#495057; --fond:#f4f6f8; --bord:#d0d7de; }
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; background:var(--fond); color:#212529; }
nav { position:fixed; top:0; left:0; bottom:0; width:300px; overflow-y:auto; background:#fff; border-right:1px solid var(--bord);
      padding:18px 14px; font-size:13.5px; }
nav h1 { font-size:16px; color:var(--bleu); margin:0 0 4px; }
nav .date { color:var(--gris); font-size:12px; margin-bottom:14px; }
nav a { display:block; color:#212529; text-decoration:none; padding:4px 8px; border-radius:6px; line-height:1.3; }
nav a:hover { background:#eef4fb; }
nav a.trois-d { color:var(--bleu); font-weight:600; }
nav details { margin-top:8px; } nav summary { cursor:pointer; color:var(--bleu); font-weight:600; padding:4px 0; }
nav details a { font-size:12.5px; padding-left:16px; }
main { margin-left:300px; padding:24px; display:flex; flex-direction:column; align-items:center; gap:24px; }
.page { background:#fff; box-shadow:0 1px 4px rgba(0,0,0,.12); max-width:1000px; width:100%; scroll-margin-top:16px; }
.page img { width:100%; display:block; }
.vue3d { background:#fff; box-shadow:0 1px 4px rgba(0,0,0,.12); max-width:1300px; width:100%; padding:20px 22px;
         scroll-margin-top:16px; }
.vue3d h2 { color:var(--bleu); margin:0 0 6px; font-size:22px; }
.vue3d p { color:var(--gris); margin:0 0 10px; font-size:14px; line-height:1.5; }
@media (max-width:900px) { nav { display:none; } main { margin-left:0; padding:8px; } }
"""


def main():
    DOSSIER.mkdir(parents=True, exist_ok=True)
    titres = titres_pages()
    images = pages_images()
    shutil.copy(RACINE / ".venv/lib/python3.12/site-packages/plotly/package_data/plotly.min.js", DOSSIER / "plotly.min.js") \
        if not (DOSSIER / "plotly.min.js").exists() else None
    fig = figure_3d()
    apres = next((k for k, t in enumerate(titres) if t.startswith("Étape 3 : tubes à ailettes")), None)
    # sommaire
    nav, groupes = [], {}
    for k, t in enumerate(titres):
        lien = f'<a href="#p{k + 1}">{k + 1}. {html.escape(t)}</a>'
        g = groupe(t, k)
        if g:
            groupes.setdefault(g, []).append(lien)
        else:
            nav.append(lien)
            if k == apres and fig:
                nav.append('<a class="trois-d" href="#vue3d">→ Vue 3D interactive des ailettes</a>')
    for g, liens in groupes.items():
        nav.append(f"<details><summary>{g} ({len(liens)})</summary>{''.join(liens)}</details>")
    # pages
    corps = []
    for k, (t, im) in enumerate(zip(titres, images)):
        corps.append(f'<section class="page" id="p{k + 1}"><img src="rapport_cfd/pages/{im.name}" '
                     f'alt="{html.escape(t)}" loading="{"eager" if k < 3 else "lazy"}"></section>')
        if k == apres and fig:
            corps.append('<section class="vue3d" id="vue3d"><h2>Vue 3D interactive : tubes à ailettes (plates, ondulées, TPMS)</h2>'
                         "<p>Glisser pour tourner, molette pour zoomer, clic droit pour déplacer. Le menu en haut à "
                         "gauche choisit le cas ; un clic dans la légende masque ou affiche un objet. Coupe horizontale "
                         "à mi-distance entre les ailettes (température), coupe verticale à travers les tubes 1 et 3 "
                         "(vitesse), lignes de courant colorées par la température. Épaisseur entre ailettes "
                         "dilatée × 4.</p><div id=\"graphe3d\"></div></section>")
    script = ""
    if fig:
        script = ('<script src="rapport_cfd/plotly.min.js"></script><script>'
                  f"const f={fig};Plotly.newPlot('graphe3d',f.data,f.layout,{{displaylogo:false,responsive:true}});"
                  "</script>")
    SORTIE.write_text(f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rapport CFD</title><style>{CSS}</style></head>
<body><nav><h1>Échangeurs de la PAC de fenêtre</h1><div class="date">Rapport CFD, mis à jour le
{date.today():%d/%m/%Y} · <a href="resultats_cfd.pdf" style="display:inline;padding:0">version PDF</a></div>
{''.join(nav)}</nav>
<main>{''.join(corps)}</main>{script}</body></html>
""")
    taille = SORTIE.stat().st_size + sum(f.stat().st_size for f in DOSSIER.rglob("*") if f.is_file())
    print(SORTIE, f"{len(images)} pages, vue 3D : {'oui' if fig else 'non'}, {taille / 1e6:.1f} Mo au total")


if __name__ == "__main__":
    main()
