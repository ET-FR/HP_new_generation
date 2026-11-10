#!/usr/bin/env python3
"""
Estimation côté propane : charge et perte de charge en fonction du diamètre intérieur des tubes.

Question : à diamètre extérieur fixé (6 mm, donc côté air inchangé), réduire le canal intérieur
(paroi plus épaisse) baisse la charge, mais augmente la perte de charge du propane. Jusqu'où
peut-on aller, et avec combien de circuits en parallèle ?

Point de fonctionnement : climatisation nominale (EN 14511, 35 °C dehors, 27 °C dedans),
évaporation 10 °C, condensation 46 °C, froid 2,3 kW (8 000 BTU/h), chaleur rejetée 3,07 kW
(COP 3). Surchauffe et sous-refroidissement inclus dans les zones monophasiques.

Longueur de tube : déduite du calcul CFD de la batterie de référence (tubes ronds nus Ø 6 mm,
4 rangs en quinconce, Pt = 12 mm, air à 1 m/s : efficacité 27,5 %, 333 m de tube par m² de face),
avec l'écart air / paroi à l'entrée (16 K à l'évaporateur, 10 K au condenseur), échange sensible
seul (prudent). C'est une estimation : les ailettes ou une vitesse d'air plus élevée raccourcissent
fortement les tubes, la charge suit la longueur (proportionnelle).

Modèles :
  * charge : masse volumique moyenne par zone ; diphasique avec la fraction de vide de
    Rouhani-Axelsson (forme de Steiner), titre variant linéairement le long du tube ;
  * perte de charge diphasique : Müller-Steinhagen et Heck ; monophasique : laminaire 64/Re
    ou Blasius ; coudes, distributeur et collecteurs non comptés ;
  * pénalité de COP : sensibilité de Carnot, environ 3 % par K de température de saturation
    perdue (évaporateur : -Δp abaisse l'évaporation ; condenseur : relève la condensation).

    python outils/analytique/charge_propane.py      → docs/formes/charge_propane/
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from CoolProp.CoolProp import PropsSI

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "formes" / "charge_propane"
F = "Propane"
G_TERRE = 9.81

TE, TC = 10.0, 46.0                     # °C
Q_EVAP, Q_COND = 2300.0, 3070.0         # W
D_EXT = 6e-3
EPS_REF, M_PAR_M2 = 0.2748, 4 / 0.012   # CFD : efficacité, m de tube par m² de face
RCP_U = 1.204 * 1006 * 1.0              # ρ cp U air (W/m²K par m² de face)
LIMITE_G = 152.0                         # m1 = 4 × LFL, IEC 60335-2-40
# hors batteries, valeurs du simulateur (pac_fenetre/physique.py) : ligne liquide 0,20 L à 30 % de
# liquide, carter 0,80 L de vapeur au refoulement, 0,27 kg d'huile × 15 % de propane dissous
V_LIGNES_L, V_CARTER_L, HUILE_KG, SOLUBILITE = 0.20, 0.80, 0.27, 0.15


def sat(T):
    T = T + 273.15
    return dict(P=PropsSI("P", "T", T, "Q", 0, F), rl=PropsSI("D", "T", T, "Q", 0, F),
                rv=PropsSI("D", "T", T, "Q", 1, F), hl=PropsSI("H", "T", T, "Q", 0, F),
                hv=PropsSI("H", "T", T, "Q", 1, F), ml=PropsSI("V", "T", T, "Q", 0, F),
                mv=PropsSI("V", "T", T, "Q", 1, F), s=PropsSI("I", "T", T, "Q", 0, F),
                dPdT=(PropsSI("P", "T", T + 0.05, "Q", 0, F) - PropsSI("P", "T", T - 0.05, "Q", 0, F)) / 0.1)


def fraction_vide(x, G, p):
    """Rouhani-Axelsson (Steiner 1993)."""
    x = np.clip(x, 1e-6, 1 - 1e-6)
    rl, rv, s = p["rl"], p["rv"], p["s"]
    return x / rv / ((1 + 0.12 * (1 - x)) * (x / rv + (1 - x) / rl)
                     + 1.18 * (1 - x) * (G_TERRE * s * (rl - rv)) ** 0.25 / (G * rl ** 0.5))


def frottement_mono(G, D, mu):
    Re = G * D / mu
    f = 64 / Re if Re < 2300 else 0.3164 * Re ** -0.25
    return f * G ** 2 / (2 * D)            # par masse volumique : dp/dz = f G²/(2 D ρ)


def dpdz_diphasique(x, G, D, p):
    """Müller-Steinhagen et Heck : gradient de pression diphasique (Pa/m)."""
    A = frottement_mono(G, D, p["ml"]) / p["rl"]       # tout liquide
    B = frottement_mono(G, D, p["mv"]) / p["rv"]       # tout vapeur
    Gx = A + 2 * (B - A) * x
    return Gx * (1 - x) ** (1 / 3) + B * x ** 3


def batterie(D_i, n_circ, L_tot, mode):
    """Charge (g) et perte de charge (Pa, K de saturation) d'une batterie."""
    if mode == "evap":
        p, Q = sat(TE), Q_EVAP
        h_in = sat(TC - 4)["hl"]                       # liquide sous-refroidi de 4 K détendu
        x_in = (h_in - p["hl"]) / (p["hv"] - p["hl"])
        zones = [("di", 0.85, x_in, 1.0), ("vap", 0.15, None, None)]
        m = Q / (p["hv"] + 2300 * 5 - h_in)            # surchauffe 5 K, cp vapeur ≈ 2,3 kJ/kgK
    else:
        p, Q = sat(TC), Q_COND
        zones = [("vap", 0.12, None, None), ("di", 0.78, 1.0, 0.0), ("liq", 0.10, None, None)]
        h_e = p["hv"] + 2600 * 25                      # vapeur surchauffée ≈ 25 K au refoulement
        m = Q / (h_e - (p["hl"] - 2600 * 4))
    A_i = math.pi * D_i ** 2 / 4
    G = m / n_circ / A_i
    L_c = L_tot / n_circ
    masse, dp = 0.0, 0.0
    for nom, frac, x0, x1 in zones:
        L = frac * L_c
        if nom == "di":
            xs = np.linspace(x0, x1, 200)
            a = fraction_vide(xs, G, p)
            rho = np.mean(a * p["rv"] + (1 - a) * p["rl"])
            dp += np.mean(dpdz_diphasique(xs, G, D_i, p)) * L
        else:
            rho = p["rv"] if nom == "vap" else p["rl"]
            mu = p["mv"] if nom == "vap" else p["ml"]
            dp += frottement_mono(G, D_i, mu) / rho * L
        masse += rho * A_i * L * n_circ
    dT = dp / p["dPdT"]
    return dict(charge_g=1e3 * masse, dp_kPa=dp / 1e3, dT_sat_K=dT, G=G, debit_g_s=1e3 * m)


def penalite_cop(dT_e, dT_c):
    """Perte relative de COP (Carnot) pour dT_e K d'évaporation et dT_c K de condensation perdus."""
    Te, Tc = TE + 273.15, TC + 273.15
    c0 = Te / (Tc - Te)
    c1 = (Te - dT_e) / (Tc + dT_c - Te + dT_e)
    return 1 - c1 / c0


def hors_tubes_g():
    p = sat(TC)
    return V_LIGNES_L * 0.3 * p["rl"] + V_CARTER_L * p["rv"] + 1e3 * HUILE_KG * SOLUBILITE


def longueurs():
    q_m = lambda dT: EPS_REF * RCP_U * dT / M_PAR_M2        # W par m de tube
    return Q_EVAP / q_m(16.0), Q_COND / q_m(10.0)


SCENARIOS = [("tubes nus, air à 1 m/s (CFD)", 1.0),
             ("tubes 4 fois plus courts (ailettes ou air plus rapide, hypothèse)", 0.25)]
PERTE_COP_MAX = 0.02


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    L_e0, L_c0 = longueurs()
    diam = [1.5e-3, 2.0e-3, 2.5e-3, 3.0e-3, 3.5e-3, 4.0e-3]
    circuits = list(range(1, 129))
    sortie = dict(conditions=dict(Te=TE, Tc=TC, Q_evap_W=Q_EVAP, Q_cond_W=Q_COND,
                                  air="tubes nus Ø 6 mm, 4 rangs en quinconce, 1 m/s"),
                  longueur_evap_m=L_e0, longueur_cond_m=L_c0, limite_charge_g=LIMITE_G,
                  hors_tubes_g=hors_tubes_g(),
                  perte_COP_max=PERTE_COP_MAX, scenarios=[])
    for nom, k in SCENARIOS:
        L_e, L_c = k * L_e0, k * L_c0
        lignes = []
        for D in diam:
            # nombre de circuits minimal (le même pour les deux batteries, au plus simple) pour une
            # perte de COP ≤ 2 % ; plus de circuits = plus de collecteurs, donc le moins possible
            for n in circuits:
                e, c = batterie(D, n, L_e, "evap"), batterie(D, n, L_c, "cond")
                pc = penalite_cop(e["dT_sat_K"], c["dT_sat_K"])
                if pc <= PERTE_COP_MAX:
                    break
            lignes.append(dict(D_i_mm=1e3 * D, paroi_mm=1e3 * (D_EXT - D) / 2, circuits=n,
                               longueur_circuit_evap_m=L_e / n, longueur_circuit_cond_m=L_c / n,
                               evap=e, cond=c, charge_tubes_g=e["charge_g"] + c["charge_g"], perte_COP=pc))
            print(f"[{nom[:12]}] Di {1e3 * D:.1f} mm : {n:3d} circuits, charge tubes {lignes[-1]['charge_tubes_g']:5.0f} g "
                  f"(évap {e['charge_g']:4.0f}, cond {c['charge_g']:4.0f}), ΔT évap {e['dT_sat_K']:.2f} K, "
                  f"cond {c['dT_sat_K']:.2f} K, COP -{100 * pc:.1f} %")
        # sensibilité : perte de COP selon le nombre de circuits, Di = 2, 3, 4 mm
        sens = {f"{1e3 * D:.0f}": [[n, penalite_cop(batterie(D, n, L_e, "evap")["dT_sat_K"],
                                                    batterie(D, n, L_c, "cond")["dT_sat_K"])]
                                   for n in (2, 4, 8, 16, 32, 64)] for D in (2e-3, 3e-3, 4e-3)}
        sortie["scenarios"].append(dict(nom=nom, facteur_longueur=k, longueur_evap_m=L_e, longueur_cond_m=L_c,
                                        resultats=lignes, sensibilite=sens))
    (SORTIE / "resultat.json").write_text(json.dumps(sortie, indent=1, ensure_ascii=False))
    print(f"longueurs (tubes nus) : évaporateur {L_e0:.0f} m, condenseur {L_c0:.0f} m")


if __name__ == "__main__":
    main()
