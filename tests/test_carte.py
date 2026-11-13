"""Tests de la carte compresseur (pytest ou python direct).

La carte utilisée est SYNTHÉTIQUE : ajustée sur le modèle générique du
simulateur (compresseurs/ajuster_carte.py --synthetique). Elle sert à vérifier la
mécanique (polynômes, interpolation, corrections, enveloppe), pas à
représenter un compresseur réel.
"""

import json
import math
import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from pac_fenetre.physique import Conception, Conditions, PompeAChaleur, Propane  # noqa: E402

CARTE = os.path.join(RACINE, "compresseurs", "SYNTHETIQUE_generique.json")
FL = Propane()
GEN = PompeAChaleur(Conception(), FL)
CAR = PompeAChaleur(Conception().avec_carte(CARTE), FL)


def test_carte_reproduit_compresseur_generique():
    """Mêmes (Te, Tc, f) : débit et puissance électrique à ~1,5 % près."""
    for Te, Tc, f in [(1.0, 40.0, 60.0), (-12.0, 37.0, 90.0), (9.0, 46.0, 60.0), (5.0, 35.0, 30.0)]:
        g, k = GEN.compresseur(Te, Tc, f), CAR.compresseur(Te, Tc, f)
        P_g = g["m"] * g["w"] / g["eta_mot"]
        P_k = k["m"] * k["w"] / k["eta_mot"]
        assert math.isclose(g["m"], k["m"], rel_tol=0.005), (Te, Tc, f)
        assert math.isclose(P_g, P_k, rel_tol=0.015), (Te, Tc, f)
        assert not k["alertes"], k["alertes"]


def test_cycle_complet_avec_carte():
    for c in [Conditions("chauffage", 7, 20, 0.8, 0.5, 60), Conditions("clim", 35, 27, 0.4, 0.47, 60)]:
        g, k = GEN.resoudre(c), CAR.resoudre(c)
        assert k.ok, k.message
        assert math.isclose(g.P_comp, k.P_comp, rel_tol=0.03)
        assert math.isclose(g.Q_utile, k.Q_utile, rel_tol=0.03)


def test_correction_surchauffe():
    """Une carte déclarée à 10 K de surchauffe, utilisée à 5 K, doit donner
    un débit plus élevé (gaz aspiré plus dense)."""
    with open(CARTE, encoding="utf-8") as f:
        d = json.load(f)
    d["reference"]["surchauffe_K"] = 10.0
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(d, f)
    pac = PompeAChaleur(Conception().avec_carte(f.name), FL)
    os.unlink(f.name)
    k5, k10 = CAR.compresseur(1.0, 40.0, 60.0), pac.compresseur(1.0, 40.0, 60.0)
    p = FL.psat(0.0)
    rho5, rho10 = FL.pT(p, 5.0)[2], FL.pT(p, 10.0)[2]
    assert math.isclose(k10["m"] / k5["m"], rho5 / rho10, rel_tol=1e-6)


def test_alarme_hors_enveloppe():
    e = CAR.resoudre(Conditions("clim", 46, 27, 0.3, 0.47, 110))
    assert any("enveloppe" in a for a in e.alarmes), e.alarmes


def test_alarme_vitesse_hors_carte():
    k = CAR.compresseur(1.0, 40.0, 130.0)
    assert any("hors carte" in a for a in k["alertes"])


def test_plage_vitesse_reprise_de_la_carte():
    c = CAR.c
    assert (c.f_min, c.f_max) == (15.0, 110.0)
    assert math.isclose(c.f_nom / c.f_max, 60.0 / 110.0)


if __name__ == "__main__":
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            fn()
            print("OK", nom)
