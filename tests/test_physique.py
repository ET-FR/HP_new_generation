"""Vérifications de cohérence physique du modèle (pytest ou python direct)."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pac_fenetre.physique import (TECHNO_REFERENCE, Conception, Conditions,  # noqa: E402
                                  PompeAChaleur, Propane)

FL = Propane()
PAC = PompeAChaleur(Conception(), FL)
CAS = [
    Conditions("chauffage", 7, 20, 0.87, 0.5, 60),
    Conditions("chauffage", -7, 20, 0.87, 0.5, 90),
    Conditions("chauffage", -20, 20, 0.80, 0.5, 110),
    Conditions("clim", 35, 27, 0.40, 0.47, 60),
    Conditions("clim", 46, 27, 0.30, 0.47, 100),
]


def test_bilan_energie():
    for c in CAS:
        e = PAC.resoudre(c)
        assert e.ok, c
        travail_fluide = e.W_arbre * (1 - PAC.c.pertes_carter)
        assert math.isclose(e.Q_cond - e.Q_evap, travail_fluide, rel_tol=1e-6)


def test_second_principe():
    for c in CAS:
        e = PAC.resoudre(c)
        Tc, Te = e.Tc + 273.15, e.Te + 273.15
        carnot_ref = Tc / (Tc - Te) if c.mode == "chauffage" else Te / (Tc - Te)
        assert e.COP_cycle < carnot_ref
        assert e.COP < e.COP_carnot


def test_equilibre_echangeurs():
    for c in CAS:
        e = PAC.resoudre(c)
        air_int, air_ext, _, _ = PAC.cotes_air(c, c.freq)
        air_c, air_e = (air_int, air_ext) if c.mode == "chauffage" else (air_ext, air_int)
        assert math.isclose(e.Q_cond, air_c.Q_condenseur(e.Tc), rel_tol=0.02)
        assert math.isclose(e.Q_evap, air_e.Q_evaporateur(e.Te)[0], rel_tol=0.02)


def test_tendance_temperature_exterieure():
    cops = [PAC.resoudre(Conditions("chauffage", T, 20, 0.6, 0.5, 60)).COP for T in (-15, -5, 5, 15)]
    assert cops == sorted(cops)


def test_technologie_3d_meilleure():
    ref = PompeAChaleur(Conception(technologie=TECHNO_REFERENCE), FL)
    for c in CAS:
        assert PAC.resoudre(c).COP > ref.resoudre(c).COP


def test_regulation_suit_besoin():
    c = Conditions("chauffage", -2, 20, 0.85, 0.5)
    besoin = PAC.besoin(c, 90, 300)
    f, PLR, statut = PAC.regulation(c, besoin)
    assert statut == "modulation"
    assert math.isclose(PAC.resoudre(c, f).Q_sensible, besoin, rel_tol=0.02)


def test_charge_sous_limite_iec():
    m_max, _ = PAC.charge_max_iec()
    for c in CAS:
        assert PAC.resoudre(c).charge_g < m_max


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn()
            print("OK", nom)
