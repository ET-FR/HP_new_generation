"""Tests de la géométrie gyroïde et des corrélations de Leeds (pytest ou python direct).

Références : Qureshi (Leeds, 2026), tableaux 3.1, 5.9, 5.11 et 5.13.
"""

import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import pac_fenetre.aeraulique as A  # noqa: E402
from pac_fenetre.gyroide import GeometrieGyroide, proprietes_reduites  # noqa: E402
from pac_fenetre.physique import Conception, Conditions, PompeAChaleur  # noqa: E402

EXEMPLE = os.path.join(RACINE, "config_air", "EXEMPLE_gyroide.json")


def test_geometrie_tableau_5_13():
    """Canal F > R, 4 cellules de L = 10 mm : V et Ah à 0,5 % près."""
    for R, V, Ah in ((0.0, 2000.2, 1237.3), (0.3, 1612.5, 1216.7), (0.6, 1219.3, 1150.5)):
        frac, aire, _ = proprietes_reduites(R)
        assert math.isclose(frac * 4000.0, V, rel_tol=0.005), R
        assert math.isclose(aire * 400.0, Ah, rel_tol=0.005), R


def test_geometrie_tableau_3_1():
    """Cellule de côté 2π mm, R = 0 et 0,5."""
    c = (2 * math.pi) ** 3
    f0, a0, _ = proprietes_reduites(0.0)
    f5, a5, _ = proprietes_reduites(0.5)
    assert math.isclose(a0 * (2 * math.pi) ** 2, 122.2, rel_tol=0.005)
    assert math.isclose(a5 * (2 * math.pi) ** 2, 116.6, rel_tol=0.01)
    assert math.isclose((1 - f5) * c, 162.5, rel_tol=0.01)


def test_dh_et_conservation_volume():
    g = GeometrieGyroide(0.010, 0.0, 0.0)
    assert math.isclose(g.Dh_air * 1e3, 6.47, rel_tol=0.01)
    assert math.isclose(g.phi_air + g.phi_propane + g.phi_paroi, 1.0)
    assert g.epaisseur_paroi < 1e-5


def test_epaisseur_paroi_proportionnelle_a_L():
    e10 = GeometrieGyroide(0.010, 0.3, -0.3).epaisseur_paroi
    e5 = GeometrieGyroide(0.005, 0.3, -0.3).epaisseur_paroi
    assert math.isclose(e10 / e5, 2.0, rel_tol=1e-6)


def test_correlations_tableau_5_11():
    """Re = 100 (L10, R0) : f = 0,98 et j = 0,063 dans la thèse."""
    assert abs(A._leeds_gyroide(100.0, None) - 0.98) < 0.01
    assert abs(A.j_leeds_gyroide(100.0) - 0.063) < 0.002


def test_transition_continue_et_alertee():
    f1, f2, f3 = (A._leeds_gyroide(Re, None) for Re in (129.999, 165.0, 200.0))
    assert min(f1, f3) <= f2 <= max(f1, f3)
    assert A.alertes_domaine_leeds(165.0)
    assert not A.alertes_domaine_leeds(1000.0)
    assert A.alertes_domaine_leeds(9000.0)


def test_couplage_UA_et_charge():
    pac = PompeAChaleur(Conception().avec_aeraulique(EXEMPLE))
    c = Conditions("chauffage", 7, 20, 0.8, 0.5, 60)
    air_int, air_ext, _, (r_int, _) = pac.cotes_air(c, 60)
    UA_int, _, _ = pac.c.aeraulique["int"].UA(pac.c.debit_int_nom * r_int, c.T_int)
    assert math.isclose(air_int.UA, UA_int)
    e = pac.resoudre(c)
    assert e.ok and math.isfinite(e.COP)
    assert "h_air" in e.aero["int"] and "part_R_air" in e.aero["int"]
    # la charge dépend du volume propane de la géométrie
    ref = PompeAChaleur().resoudre(c)
    assert abs(e.charge_g - ref.charge_g) > 1.0


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn()
            print("OK", nom)
