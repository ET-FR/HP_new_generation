"""Rendu des STL de l'échangeur à hélice (outils/cad/echangeur_helice.py) avec pyvista, sans écran.
    .venv/bin/python conception_echangeur/outils/cad/rendu_echangeur.py [dossier]   (défaut : docs/formes/helice)
Produit vue_ensemble.png (enveloppe transparente, coupe) et vue_details.png."""
import sys
from pathlib import Path

import pyvista as pv

pv.OFF_SCREEN = True
DOSSIER = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "docs/formes/helice"
STYLE = {
    "ailette": dict(color="#adb5bd", opacity=1.0),
    "tubes": dict(color="#d6336c"),
    "arbre_haut": dict(color="#e8590c"),
    "arbre_bas": dict(color="#1c7ed6"),
    "noyau": dict(color="#495057", opacity=0.35),
    "enveloppe": dict(color="#74c0fc", opacity=0.18),
}


def charger():
    return {n: pv.read(DOSSIER / f"{n}.stl") for n in STYLE if (DOSSIER / f"{n}.stl").exists()}


def vue(maillages, fichier, coupe=False, camera=None, titre=""):
    pl = pv.Plotter(window_size=(1600, 1200))
    pl.set_background("white")
    for n, m in maillages.items():
        if coupe and n in ("ailette", "enveloppe", "noyau"):
            m = m.clip(normal=(0, -1, 0), origin=(0, 0, 0), invert=False)
        pl.add_mesh(m, smooth_shading=True, **STYLE[n])
    if camera:
        pl.camera_position = camera
    else:
        pl.view_isometric()
        pl.camera.elevation = 18
    if titre:
        pl.add_text(titre, font_size=12, color="black")
    pl.screenshot(DOSSIER / fichier)
    pl.close()


def main():
    m = charger()
    vue(m, "vue_ensemble.png", titre="Échangeur à ailette hélicoïdale : enveloppe transparente")
    vue(m, "vue_coupe.png", coupe=True, titre="Coupe : ailette en hélice, tubes, arbres de Murray")
    z = m["ailette"].bounds[5]
    vue({"arbre_haut": m["arbre_haut"], "tubes": m["tubes"], "noyau": m["noyau"]}, "vue_arbre.png",
        camera=[(0, -150, 650), (0, 0, z), (0, 1, 0)], titre="Arbre de Murray du haut (1 → 32)")
    vue({"ailette": m["ailette"], "tubes": m["tubes"]}, "vue_ailette.png",
        camera=[(260, -260, 120), (170, 0, 40), (0, 0, 1)], titre="Détail : nappes en hélice traversées par les tubes")
    print("rendus dans", DOSSIER)


if __name__ == "__main__":
    main()
