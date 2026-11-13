"""Tests des surfaces TPMS, des modèles d'échangeurs du comparateur et du générateur CFD."""

import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "conception_echangeur", "outils", "cfd_tpms"))

import numpy as np  # noqa: E402

from pac_fenetre.comparateur import DEFAUT, evaluer  # noqa: E402
from pac_fenetre.echangeurs_air import EchangeurTPMS, EchangeurTubesNus  # noqa: E402
from pac_fenetre.gyroide import GeometrieGyroide  # noqa: E402
from pac_fenetre.tpms import SURFACES, geometrie, proprietes_reduites  # noqa: E402


def test_tpms_coherent_avec_gyroide():
    """Le module générique retrouve la géométrie du module gyroïde historique."""
    g = GeometrieGyroide(0.006, 0.3, -0.6)
    phi, s = proprietes_reduites("gyroide", 0.3)
    assert math.isclose(phi, g.phi_air, rel_tol=1e-3)
    assert math.isclose(s / 0.006, g.beta_air, rel_tol=2e-3)


def test_dh_egal_meme_surface_volumique():
    """À porosité et Dh égaux, toutes les surfaces ont β = 4 φ / Dh."""
    for s in SURFACES:
        g = geometrie(s, 0.6, Dh=4e-3)
        assert math.isclose(g["Dh_air"], 4e-3, rel_tol=1e-9)
        assert math.isclose(g["beta_air"], 4 * g["phi_air"] / 4e-3, rel_tol=1e-9)
        assert abs(g["phi_air"] - 0.6) < 0.01


def test_tubes_nus_ordres_de_grandeur():
    """Tubes Ø1 mm en quinconce : Δp de quelques dizaines de Pa, h côté air 100-300 W/m²K."""
    e = EchangeurTubesNus(0.6, 0.35, 0.025, 1e-3, 0.15e-3, 2.0, 1.75, 190, 2730, 3000)
    UA, det, al = e.UA(450, 20)
    dp, Re, xi = e.dp(450 / 3600, 20, 30)
    assert 100 < det["h_air"] < 300
    assert 3 < dp < 60
    assert not al
    assert e.n_tubes == int(0.35 / 2e-3) * int(0.025 / 1.75e-3)


def test_hybride_moins_de_propane_que_feuillet():
    k = dict(largeur=0.6, hauteur=0.35, profondeur=0.025, phi_air=0.6, Dh=4e-3, k_metal=130,
             rho_metal=2670, h_propane=2500)
    f = EchangeurTPMS("gyroide", mode="feuillet", phi_propane=0.1, **k)
    h = EchangeurTPMS("gyroide", mode="hybride", **k)
    assert h.volume_propane_L < f.volume_propane_L
    UA, det, _ = h.UA(450, 20)
    assert 0 < det["eta_ailette"] <= 1


def test_comparateur_reference_et_tubes():
    ref = evaluer("reference", DEFAUT)
    tub = evaluer("tubes_nus", DEFAUT)
    assert ref["ok"] and tub["ok"]
    for r in (ref, tub):
        assert 2.0 < r["COP"] < 8.0
    assert tub["batteries"]["int"]["UA"] > 0


def test_stl_ferme_et_oriente():
    """La surface du solide est fermée dans le domaine et orientée vers l'air."""
    from creer_cas import fonction_solide, triangles
    L, D = 5e-3, 10e-3
    phi = fonction_solide("gyroide", -0.3, L, D)
    T = triangles(phi, [(-0.5e-3, D + 0.5e-3), (0, L), (0, L)], L / 16)
    assert len(T) > 1000
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1)[:, None]
    g = T.mean(axis=1)
    assert np.mean(phi(*(g + 1e-5 * n).T) < phi(*(g - 1e-5 * n).T)) > 0.99


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
            print("ok", nom)
