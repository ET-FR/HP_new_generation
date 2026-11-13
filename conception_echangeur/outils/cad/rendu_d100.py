"""Rendus de l'échangeur Ø 100 (outils/cad/echangeur_d100.py) avec pyvista, sans écran.
    .venv/bin/python conception_echangeur/outils/cad/rendu_d100.py [dossier]   → <dossier>/vue_*.png (défaut docs/formes/cylindre_d100)"""
import sys
from pathlib import Path

import pyvista as pv

pv.OFF_SCREEN = True
RACINE = Path(__file__).resolve().parents[2]
D = (RACINE / sys.argv[1]) if len(sys.argv) > 1 else RACINE / "docs/formes/cylindre_d100"
STYLE = {"enveloppe": dict(color="#74c0fc", opacity=0.22), "noyau": dict(color="#868e96", opacity=0.5),
         "tubes": dict(color="#d6336c"), "arbre_entree": dict(color="#e8590c"), "arbre_sortie": dict(color="#1c7ed6")}


def vue(fichier, noms, camera, coupe=False, taille=(1800, 1000)):
    pl = pv.Plotter(window_size=taille)
    pl.set_background("white")
    for n in noms:
        m = pv.read(D / f"{n}.stl")
        if coupe and n in ("enveloppe", "noyau"):
            m = m.clip(normal=(0, 0, 1), origin=(0, 0, 0))
        pl.add_mesh(m, smooth_shading=True, **STYLE[n])
    pl.camera_position = camera
    pl.screenshot(D / fichier)
    pl.close()


tout = list(STYLE)
vue("vue_ensemble.png", tout, [(420, -560, 300), (150, 0, 0), (0, 0, 1)])
vue("vue_coupe.png", tout, [(330, -420, 380), (150, 0, 0), (0, 0, 1)], coupe=True)
vue("vue_arbre.png", ["arbre_entree", "tubes"], [(560, -170, 110), (380, 0, 0), (0, 0, 1)], taille=(1400, 1000))
vue("vue_bout.png", ["arbre_entree", "tubes", "enveloppe"], [(800, 0, 0), (150, 0, 0), (0, 0, 1)], taille=(1000, 1000))
print("ok")
