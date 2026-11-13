"""Rendus de l'échangeur Ø 150 à canal hélicoïdal (outils/cad/echangeur_d150.py), pyvista sans écran.
    .venv/bin/python conception_echangeur/outils/cad/rendu_d150.py   → docs/formes/cylindre_d150_helice/vue_*.png"""
from pathlib import Path

import pyvista as pv

pv.OFF_SCREEN = True
D = Path(__file__).resolve().parents[2] / "docs/formes/cylindre_d150_helice"
STYLE = {"enveloppe": dict(color="#74c0fc", opacity=0.2), "noyau": dict(color="#868e96"),
         "ailette": dict(color="#adb5bd"), "tubes": dict(color="#d6336c"), "domaine_air": dict(color="#15aabf", opacity=0.9)}


def vue(fichier, noms, camera, coupe=None, taille=(1600, 1200), parallele=False):
    pl = pv.Plotter(window_size=taille)
    pl.set_background("white")
    for n in noms:
        m = pv.read(D / f"{n}.stl")
        if coupe is not None and n in coupe:
            m = m.clip(normal=(0, -1, 0), origin=(0, 0, 0))
        pl.add_mesh(m, smooth_shading=True, **STYLE[n])
    pl.camera_position = camera
    if parallele:
        pl.enable_parallel_projection()
    pl.screenshot(D / fichier)
    pl.close()


vue("vue_ensemble.png", ["enveloppe", "noyau", "ailette", "tubes"], [(520, -620, 420), (0, 0, 197), (0, 0, 1)])
vue("vue_coupe.png", ["enveloppe", "noyau", "ailette", "tubes"], [(60, -700, 250), (0, 0, 197), (0, 0, 1)],
    coupe={"enveloppe", "ailette", "noyau"})
vue("vue_air.png", ["domaine_air"], [(480, -560, 420), (0, 0, 197), (0, 0, 1)])
vue("vue_tournesol.png", ["tubes", "noyau", "enveloppe"], [(0, 0, 900), (0, 0, 197), (0, 1, 0)], taille=(1100, 1100),
    parallele=True)
print("rendus dans", D)
