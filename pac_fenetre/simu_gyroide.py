"""
Simulation d'une PAC dont les deux batteries sont des échangeurs gyroïdes
paramétrés depuis l'interface web (onglet « Dimensionnement des échangeurs »).

Chaque batterie : géométrie gyroïde (période L, niveaux air / propane),
dimensions, matériau (conductivité de paroi), h côté propane, débit d'air et
rendement ventilateur. UA et perte de charge viennent de la même géométrie
(corrélations f et j de Leeds, `aeraulique.EchangeurGyroide`), la charge de
propane du volume du réseau propane. Le cycle complet (`PompeAChaleur`) est
résolu à la fréquence qui fournit la puissance demandée.
"""

from __future__ import annotations

import math
from dataclasses import replace

from scipy.optimize import brentq

from .aeraulique import (CircuitAir, EchangeurGyroide, VentilateurRendementConstant,
                         RE_MIN_LEEDS, RE_MAX_LEEDS)
from .dimensionnement import MATERIAUX
from .gyroide import GeometrieGyroide
from .physique import Conception, Conditions, PompeAChaleur

MATERIAUX_IMPRESSION = {k: v for k, v in MATERIAUX.items() if v["impression"]}

# (clé, libellé, unité, min, max, pas, défaut intérieur, défaut extérieur)
PARAMETRES = [
    ("L_mm", "Période de cellule L", "mm", 3.0, 30.0, 0.5, 8.0, 8.0),
    ("niveau_air", "Niveau côté air", "", -0.6, 0.9, 0.05, 0.0, 0.0),
    ("niveau_propane", "Niveau côté propane", "", -1.3, 0.6, 0.05, -0.9, -0.9),
    ("largeur_mm", "Largeur (face)", "mm", 100, 900, 10, 600, 700),
    ("hauteur_mm", "Hauteur (face)", "mm", 100, 700, 10, 350, 450),
    ("profondeur_mm", "Profondeur (sens de l'air)", "mm", 10, 200, 5, 25, 30),
    ("debit_m3h", "Débit d'air", "m³/h", 100, 2500, 10, 450, 1000),
    ("h_propane", "h côté propane", "W/m²K", 500, 8000, 100, 2500, 2500),
    ("eta_vent", "Rendement ventilateur", "", 0.10, 0.60, 0.01, 0.25, 0.25),
]
DEFAUT = {
    "mode": "chauffage", "T_ext": 7.0, "T_int": 20.0, "HR_ext": 0.87, "HR_int": 0.50,
    "puissance_kW": 2.0, "materiau": "AlSi10Mg (LPBF)",
    "int": {k: d_int for k, *_, d_int, _ in PARAMETRES},
    "ext": {k: d_ext for k, *_, d_ext in PARAMETRES},
}


def _borne(v, lo, hi):
    return min(max(float(v), lo), hi)


def _lire(req: dict) -> dict:
    p = {k: req.get(k, v) for k, v in DEFAUT.items() if not isinstance(v, dict)}
    p["mode"] = "clim" if p["mode"] == "clim" else "chauffage"
    p["T_ext"] = _borne(p["T_ext"], -25, 46)
    p["T_int"] = _borne(p["T_int"], 10, 32)
    p["HR_ext"], p["HR_int"] = _borne(p["HR_ext"], 0.1, 1.0), _borne(p["HR_int"], 0.1, 1.0)
    p["puissance_kW"] = _borne(p["puissance_kW"], 0.3, 6.0)
    if p["materiau"] not in MATERIAUX_IMPRESSION:
        p["materiau"] = DEFAUT["materiau"]
    for cote in ("int", "ext"):
        src = req.get(cote) or {}
        p[cote] = {k: _borne(src.get(k, DEFAUT[cote][k]), lo, hi)
                   for k, _, _, lo, hi, *_ in PARAMETRES}
        g = p[cote]
        g["niveau_propane"] = min(g["niveau_propane"], g["niveau_air"] - 0.1)  # paroi d'épaisseur > 0
    return p


def _echangeur(g: dict, materiau: str) -> EchangeurGyroide:
    return EchangeurGyroide(
        largeur=g["largeur_mm"] / 1e3, hauteur=g["hauteur_mm"] / 1e3, profondeur=g["profondeur_mm"] / 1e3,
        geo=GeometrieGyroide(g["L_mm"] / 1e3, g["niveau_air"], g["niveau_propane"]),
        Kc=0.5, Ke=0.15, h_propane=g["h_propane"], k_paroi=MATERIAUX[materiau]["k"])


def _circuit(g: dict, ech: EchangeurGyroide) -> CircuitAir:
    A = ech.A_frontale
    return CircuitAir(ech, VentilateurRendementConstant(f"η = {g['eta_vent']:.2f}", g["eta_vent"]), 1,
                      [{"nom": "grille", "K": 1.0, "A": A}])


def _resoudre_puissance(pac: PompeAChaleur, cond: Conditions, Q_cible: float):
    """État à la fréquence qui fournit Q_cible (W) ; f_max si inatteignable."""
    c = pac.c
    def ecart(f):
        e = pac.resoudre(cond, f)
        return (e.Q_utile if e.ok else 0.0) - Q_cible
    e_min, e_max = ecart(c.f_min), ecart(c.f_max)
    if e_max < 0:
        return pac.resoudre(cond, c.f_max), "puissance demandée inatteignable : compresseur à f max"
    if e_min > 0:
        return pac.resoudre(cond, c.f_min), "puissance minimale supérieure à la demande : f min (cyclage)"
    f = brentq(ecart, c.f_min, c.f_max, xtol=0.05)
    return pac.resoudre(cond, f), None


def simuler(req: dict) -> dict:
    p = _lire(req)
    mat = MATERIAUX[p["materiau"]]
    echs = {cote: _echangeur(p[cote], p["materiau"]) for cote in ("int", "ext")}
    aero = {cote: _circuit(p[cote], echs[cote]) for cote in ("int", "ext")}
    aero.update(nom="gyroïde (interface)", exemple=False)

    base = Conception()
    c = replace(base, aeraulique=aero,
                technologie="Impression 3D métal (TPMS)",
                multiplicateurs=dict(k_UA=1.0, k_vent=1.0, k_vol=1.0, k_givre=0.7),
                debit_int_nom=p["int"]["debit_m3h"], debit_ext_nom=p["ext"]["debit_m3h"],
                V_bat_int=echs["int"].volume_propane_L, V_bat_ext=echs["ext"].volume_propane_L)
    cond = Conditions(mode=p["mode"], T_ext=p["T_ext"], T_int=p["T_int"], HR_ext=p["HR_ext"],
                      HR_int=p["HR_int"], debit_int=p["int"]["debit_m3h"], debit_ext=p["ext"]["debit_m3h"])
    pac = PompeAChaleur(c)
    e, alerte_f = _resoudre_puissance(pac, cond, p["puissance_kW"] * 1e3)

    # Référence : machine du simulateur temps réel (tube-ailettes), même conditions, même puissance
    ref = PompeAChaleur(Conception(technologie="Tube-ailettes Cu/Al"))
    cond_ref = replace(cond, debit_int=None, debit_ext=None)
    e_ref, _ = _resoudre_puissance(ref, cond_ref, p["puissance_kW"] * 1e3)

    batteries = {}
    for cote in ("int", "ext"):
        ech, g = echs[cote], p[cote]
        T_in = p["T_int"] if cote == "int" else p["T_ext"]
        UA, det, alertes = ech.UA(g["debit_m3h"], T_in)
        a = e.aero.get(cote, {})
        geo = ech.geo.resume()
        u_face = g["debit_m3h"] / 3600.0 / ech.A_frontale
        batteries[cote] = dict(
            geo, UA=UA, Re=det["Re"], j=det["j"], h_air=det["h_air"], A_air=det["A_air"],
            A_propane=det["A_propane"], part_R_air=det["part_R_air"], part_R_paroi=det["part_R_paroi"],
            part_R_propane=det["part_R_propane"], dp=a.get("dp_total", float("nan")),
            dp_echangeur=a.get("dp_echangeur", float("nan")), P_vent=a.get("P", float("nan")),
            u_face=u_face, volume_propane_L=ech.volume_propane_L,
            masse_kg=geo["phi_paroi"] * ech.V_coeur * mat["rho"],
            cellules_profondeur=g["profondeur_mm"] / g["L_mm"],
            debit=g["debit_m3h"], alertes=alertes,
            paroi_trop_fine=geo["paroi_mm"] < mat["e_min"])

    resultat = dict(
        ok=bool(e.ok), message=e.message if not e.ok else "", alerte_f=alerte_f, params=p,
        batteries=batteries,
        etat=dict(mode=e.mode, freq=e.freq, Te=e.Te, Tc=e.Tc, T_refoul=e.T_refoul, m_dot=e.m_dot,
                  Q_utile=e.Q_utile, P_comp=e.P_comp, P_vent=e.P_vent, P_tot=e.P_tot,
                  COP=e.COP, COP_cycle=e.COP_cycle, COP_carnot=e.COP_carnot, eta_exergie=e.eta_exergie,
                  T_air_int_out=e.T_air_int_out, T_air_ext_out=e.T_air_ext_out,
                  debit_int=e.debit_int, debit_ext=e.debit_ext, charge_g=e.charge_g,
                  points=e.points, alarmes=e.alarmes, givre=e.givre),
        reference=dict(COP=e_ref.COP, Te=e_ref.Te, Tc=e_ref.Tc, freq=e_ref.freq, P_vent=e_ref.P_vent,
                       charge_g=e_ref.charge_g, ok=bool(e_ref.ok)),
        domaine_leeds=[RE_MIN_LEEDS, RE_MAX_LEEDS],
    )
    return resultat


def hypotheses_ui() -> dict:
    return dict(parametres=PARAMETRES, defaut=DEFAUT, materiaux=list(MATERIAUX_IMPRESSION),
                e_min={k: v["e_min"] for k, v in MATERIAUX_IMPRESSION.items()},
                k={k: v["k"] for k, v in MATERIAUX_IMPRESSION.items()})
