"""Tests de l'aéraulique physique (pytest ou python direct)."""

import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from pac_fenetre.aeraulique import (CircuitAir, CourbeVitesse, GeometrieEchangeur,  # noqa: E402
                                    Ventilateur, charger_aeraulique, mu_air, rho_air_sec)
from pac_fenetre.physique import Conception, Conditions, PompeAChaleur  # noqa: E402

VENT_REEL = os.path.join(RACINE, "ventilateurs", "W1G200-EC87-20.json")
EXEMPLE = os.path.join(RACINE, "config_air", "EXEMPLE_aeraulique.json")


def geo(**kw):
    d = dict(A_frontale=0.04, profondeur=0.1, sigma=1.0, D_h=0.004, Kc=0.0, Ke=0.0,
             correlation_f="canal_droit_PROVISOIRE")
    d.update(kw)
    return GeometrieEchangeur(**d)


def test_kays_london_frottement_pur():
    """σ = 1, Kc = Ke = 0, isotherme : Δp = f · 4L/Dh · ρu²/2."""
    g, Q, T = geo(), 0.01, 20.0
    dp, Re, f = g.dp(Q, T, T)
    u, r = Q / g.A_frontale, rho_air_sec(T)
    assert math.isclose(Re, r * u * g.D_h / mu_air(T), rel_tol=1e-9)
    assert math.isclose(dp, f * 4 * g.profondeur / g.D_h * r * u * u / 2, rel_tol=1e-9)


def test_laminaire_dp_proportionnel_au_debit():
    g = geo()
    d1, Re1, _ = g.dp(0.005, 20, 20)
    d2, Re2, _ = g.dp(0.010, 20, 20)
    assert Re2 < 2300
    assert math.isclose(d2 / d1, 2.0, rel_tol=1e-9)


def test_acceleration_air_chauffe():
    g = geo(sigma=0.6, Kc=0.4, Ke=0.1)
    assert g.dp(0.1, 20, 38)[0] > g.dp(0.1, 20, 20)[0]


def test_ventilateur_point_mesure():
    """Point d'une courbe mesurée : vitesse et puissance de la fiche."""
    v = charger_aeraulique(EXEMPLE)["int"].ventilateur
    n, P, al = v.point(370.0, 18.0)
    assert abs(n - 1300) < 15 and abs(P - 8.0) < 0.3, (n, P)


def test_ventilateur_baisse_rendement_basse_vitesse():
    """À 900 tr/min, la puissance mesurée dépasse la loi en n³ (moteur EC)."""
    v = charger_aeraulique(EXEMPLE)["int"].ventilateur
    n, P, _ = v.point(250.0, 8.0)
    assert abs(n - 900) < 30
    assert P > 8.0 * (900 / 1300) ** 3 * 1.3


def test_ventilateur_inadapte_signale():
    v = charger_aeraulique(EXEMPLE)["int"].ventilateur
    n, P, al = v.point(260.0, 200.0)
    assert math.isnan(P) and al


def _pac_ventilateur_fort():
    """Ventilateur FICTIF à forte pression, uniquement pour tester l'intégration."""
    fort = Ventilateur("fictif", [CourbeVitesse(3000, [400, 800, 1200, 1600],
                                                [400, 300, 180, 0], [40, 55, 65, 70])],
                       n_max=4000, n_min=500)
    aero = charger_aeraulique(EXEMPLE)
    aero["int"] = CircuitAir(aero["int"].echangeur, fort, 1, aero["int"].accessoires)
    aero["ext"] = CircuitAir(aero["ext"].echangeur, fort, 1, aero["ext"].accessoires)
    from dataclasses import replace
    return PompeAChaleur(replace(Conception(), aeraulique=aero))


def test_integration_cycle():
    pac = _pac_ventilateur_fort()
    e = pac.resoudre(Conditions("chauffage", 7, 20, 0.8, 0.5, 60))
    assert e.ok and math.isfinite(e.COP)
    assert math.isclose(e.P_vent, e.aero["int"]["P"] + e.aero["ext"]["P"])
    assert math.isclose(e.P_tot, e.P_comp + e.P_vent + pac.c.P_veille)


def test_loi_historique_inchangee_sans_aeraulique():
    e = PompeAChaleur().resoudre(Conditions("chauffage", 7, 20, 0.8, 0.5, 60))
    assert abs(e.P_vent - (28 + 55) * 0.8) < 1e-9


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn()
            print("OK", nom)
