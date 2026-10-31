"""
Modèle physique d'une pompe à chaleur réversible de fenêtre au propane (R290).

Modèle "semi-empirique" en régime quasi-statique :
  * Fluide : propane (R290), propriétés réelles via CoolProp (EOS Helmholtz,
    tables bicubiques pour la vitesse).
  * Compresseur rotatif BLDC à vitesse variable (inverter) : rendement
    volumétrique (espace mort + fuites), rendement isentropique fonction du
    taux de compression et de la fréquence, rendement moteur + variateur.
  * Échangeurs : méthode epsilon-NTU côté air (zone diphasique dominante).
    Évaporateur avec batterie humide (modèle enthalpique, Lewis = 1) pour la
    déshumidification en été et le givrage en hiver.
  * Détendeur électronique (EEV) : surchauffe imposée, sous-refroidissement imposé.
  * Vanne 4 voies : inversion du rôle des échangeurs intérieur / extérieur.
  * Dégivrage par inversion de cycle, cyclage marche/arrêt en très faible charge.

Les deux inconnues du cycle (T évaporation, T condensation) sont obtenues en
égalisant, sur chaque échangeur, la puissance côté réfrigérant et la puissance
côté air (résolution par Brent imbriqué, robuste).

Toutes les températures sont en °C dans l'API, les puissances en W.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import CoolProp.CoolProp as CP
from CoolProp import AbstractState
from scipy.optimize import brentq

P_ATM = 101325.0
T0 = 273.15


# --------------------------------------------------------------------------
# Propriétés du propane
# --------------------------------------------------------------------------
class Propane:
    """Accès rapide aux propriétés du R290 (Pa, J/kg, J/kg/K, kg/m3, °C)."""

    def __init__(self):
        # HEOS : équation d'état de référence (Lemmon et al.). Les tables
        # bicubiques sont plus rapides mais imprécises près de la saturation.
        self.AS = AbstractState("HEOS", "Propane")
        self.Tcrit = self.AS.T_critical() - T0
        self.pcrit = self.AS.p_critical()

    def sat(self, T: float, Q: float):
        """État saturé à T (°C) et titre Q : (p, h, s, rho)."""
        a = self.AS
        a.update(CP.QT_INPUTS, Q, T + T0)
        return a.p(), a.hmass(), a.smass(), a.rhomass()

    def psat(self, T: float) -> float:
        self.AS.update(CP.QT_INPUTS, 0.0, T + T0)
        return self.AS.p()

    def tsat(self, p: float) -> float:
        self.AS.update(CP.PQ_INPUTS, p, 1.0)
        return self.AS.T() - T0

    def pT(self, p: float, T: float):
        """(h, s, rho) à p (Pa), T (°C) en phase simple."""
        a = self.AS
        a.update(CP.PT_INPUTS, p, T + T0)
        return a.hmass(), a.smass(), a.rhomass()

    def h_ps(self, p: float, s: float, T_init: float) -> float:
        """h(p, s) en vapeur surchauffée : Newton sur T (ds = cp dT / T)."""
        a = self.AS
        T = T_init + T0
        for _ in range(12):
            a.update(CP.PT_INPUTS, p, T)
            ds = a.smass() - s
            if abs(ds) < 1e-3:
                break
            T -= ds * T / a.cpmass()
        return a.hmass()

    def T_ph(self, p: float, h: float) -> float:
        self.AS.update(CP.HmassP_INPUTS, h, p)
        return self.AS.T() - T0

    def s_ph(self, p: float, h: float) -> float:
        self.AS.update(CP.HmassP_INPUTS, h, p)
        return self.AS.smass()


# --------------------------------------------------------------------------
# Air humide (psychrométrie simplifiée, pression atmosphérique)
# --------------------------------------------------------------------------
def p_vs(T: float) -> float:
    """Pression de vapeur saturante (Pa), formule de Magnus (eau / glace)."""
    if T >= 0.0:
        return 611.2 * math.exp(17.62 * T / (243.12 + T))
    return 611.2 * math.exp(22.46 * T / (272.62 + T))


def w_sat(T: float) -> float:
    pv = p_vs(T)
    return 0.622 * pv / (P_ATM - pv)


def w_from_hr(T: float, hr: float) -> float:
    """Humidité absolue (kg/kg air sec) depuis T (°C) et HR (0..1)."""
    pv = hr * p_vs(T)
    return 0.622 * pv / (P_ATM - pv)


def h_air(T: float, w: float) -> float:
    """Enthalpie de l'air humide (J/kg air sec)."""
    return 1006.0 * T + w * (2501e3 + 1860.0 * T)


def rho_air(T: float, w: float) -> float:
    """Masse volumique de l'air sec dans l'air humide (kg air sec / m3)."""
    pv = w * P_ATM / (0.622 + w)
    return (P_ATM - pv) / (287.05 * (T + T0))


# --------------------------------------------------------------------------
# Paramètres de conception
# --------------------------------------------------------------------------
TECHNOLOGIES = {
    # k_UA  : multiplicateur de conductance UA (même encombrement)
    # k_vent: multiplicateur de puissance ventilateur (pertes de charge air)
    # k_vol : multiplicateur du volume interne côté réfrigérant (charge R290)
    # k_givre: capacité relative d'accumulation de givre avant colmatage
    "Tube-ailettes Cu/Al": dict(k_UA=1.00, k_vent=1.00, k_vol=1.00, k_givre=1.00),
    "Microcanaux Al": dict(k_UA=1.25, k_vent=0.90, k_vol=0.55, k_givre=0.80),
    "Impression 3D métal (TPMS)": dict(k_UA=1.60, k_vent=0.80, k_vol=0.45, k_givre=0.70),
}
TECHNO_REFERENCE = "Tube-ailettes Cu/Al"


@dataclass
class Conception:
    """Paramètres de la machine (valeurs par défaut : unité ~3,5 kW)."""

    # Compresseur rotatif BLDC
    cylindree_cm3: float = 16.0
    f_min: float = 15.0
    f_max: float = 110.0
    f_nom: float = 60.0
    f_opt: float = 55.0          # fréquence de rendement isentropique max
    espace_mort: float = 0.04
    n_poly: float = 1.10
    k_fuite: float = 0.015
    eta_is_max: float = 0.72
    PR_opt: float = 3.0
    pertes_carter: float = 0.07  # fraction du travail perdue vers l'ambiance
    eta_variateur: float = 0.97
    T_refoul_max: float = 110.0

    # Cycle / détendeur électronique
    surchauffe: float = 5.0
    sous_refroid: float = 4.0
    dT_aspiration: float = 1.0   # perte de charge ligne aspiration (K sat.)
    dT_refoulement: float = 0.5  # perte de charge refoulement + V4V (K sat.)

    # Échangeurs et ventilateurs (technologie de référence)
    technologie: str = "Impression 3D métal (TPMS)"
    UA_int_ref: float = 260.0    # W/K, batterie intérieure, débit nominal
    UA_ext_ref: float = 420.0    # W/K, batterie extérieure, débit nominal
    debit_int_nom: float = 520.0   # m3/h
    debit_ext_nom: float = 1300.0  # m3/h
    P_vent_int_nom: float = 28.0   # W (moteur EC)
    P_vent_ext_nom: float = 55.0   # W
    P_veille: float = 4.0          # W électronique de commande
    exposant_UA_debit: float = 0.6

    # Volumes internes (L) pour l'estimation de charge
    V_bat_int: float = 0.55
    V_bat_ext: float = 0.90
    V_lignes: float = 0.20
    V_carter: float = 0.80
    masse_huile: float = 0.27      # kg
    solubilite_huile: float = 0.15  # kg R290 / kg huile

    # Dégivrage
    givre_max_ref: float = 0.60    # kg de givre avant dégivrage (réf.)
    duree_degivrage: float = 180.0  # s
    P_degivrage: float = 900.0      # W électrique pendant le dégivrage
    rendement_degivrage: float = 0.55

    # Cyclage (sous la capacité minimale)
    Cd: float = 0.15

    # Intégration fenêtre
    UA_kit_fenetre: float = 3.0    # W/K pont thermique / fuites du kit

    # Sécurité R290 (IEC 60335-2-40)
    surface_piece: float = 50.0
    h0_installation: float = 1.0   # m (hauteur de rejet, unité de fenêtre)

    @property
    def techno(self):
        return TECHNOLOGIES[self.technologie]


@dataclass
class Conditions:
    mode: str = "chauffage"  # "chauffage" ou "clim"
    T_ext: float = 7.0
    T_int: float = 20.0
    HR_ext: float = 0.80
    HR_int: float = 0.50
    freq: float = 60.0
    ratio_vent: float | None = None  # None : asservi à la fréquence


# --------------------------------------------------------------------------
# Échangeur côté air
# --------------------------------------------------------------------------
@dataclass
class CoteAir:
    T_in: float
    w_in: float
    debit_m3h: float
    UA: float
    frac_res_interne: float = 0.25

    def __post_init__(self):
        self.m_a = self.debit_m3h / 3600.0 * rho_air(self.T_in, self.w_in)
        self.C = self.m_a * (1006.0 + 1860.0 * self.w_in)
        self.eps = 1.0 - math.exp(-self.UA / self.C)
        self.h_in = h_air(self.T_in, self.w_in)

    def Q_condenseur(self, Tc: float) -> float:
        return self.eps * self.C * (Tc - self.T_in)

    def Q_evaporateur(self, Te: float):
        """Retourne (Q_total, Q_latent, débit d'eau condensée/givrée kg/s).

        La surface d'ailette est plus chaude que le réfrigérant (résistance
        interne + efficacité d'ailette) : T_surf = Te + f_int (T_in - Te).
        """
        Q_sec = self.eps * self.C * (self.T_in - Te)
        Ts = Te + self.frac_res_interne * (self.T_in - Te)
        ws = w_sat(Ts)
        if ws < self.w_in:  # surface sous le point de rosée : batterie humide
            Q_hum = self.eps * self.m_a * (self.h_in - h_air(Ts, ws)) / (1.0 - self.frac_res_interne)
            if Q_hum > Q_sec:
                m_eau = self.eps * self.m_a * (self.w_in - ws)
                Q_lat = m_eau * 2501e3
                return Q_hum, min(Q_lat, Q_hum), m_eau
        return Q_sec, 0.0, 0.0


# --------------------------------------------------------------------------
# Résultats
# --------------------------------------------------------------------------
@dataclass
class Etat:
    ok: bool = False
    message: str = ""
    mode: str = "chauffage"
    freq: float = 0.0
    Te: float = float("nan")
    Tc: float = float("nan")
    p_bp: float = float("nan")
    p_hp: float = float("nan")
    PR: float = float("nan")
    T_refoul: float = float("nan")
    m_dot: float = 0.0
    eta_v: float = float("nan")
    eta_is: float = float("nan")
    eta_mot: float = float("nan")
    Q_cond: float = 0.0
    Q_evap: float = 0.0
    Q_lat: float = 0.0
    Q_utile: float = 0.0        # chauffage : Q_cond ; clim : Q_evap total
    Q_sensible: float = 0.0     # partie sensible de Q_utile
    W_arbre: float = 0.0
    P_comp: float = 0.0
    P_vent: float = 0.0
    P_tot: float = 0.0
    COP_cycle: float = float("nan")
    COP: float = float("nan")
    COP_integre: float = float("nan")
    Q_integre: float = float("nan")
    COP_carnot: float = float("nan")
    eta_exergie: float = float("nan")
    eau_kg_h: float = 0.0
    givre: bool = False
    frac_degivrage: float = 0.0
    T_air_int_out: float = float("nan")
    T_air_ext_out: float = float("nan")
    debit_int: float = 0.0
    debit_ext: float = 0.0
    charge_g: float = float("nan")
    points_ph: list = field(default_factory=list)  # [(h kJ/kg, p bar), ...]
    alarmes: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Modèle de la machine
# --------------------------------------------------------------------------
class PompeAChaleur:
    def __init__(self, conception: Conception | None = None, fluide: Propane | None = None):
        self.c = conception or Conception()
        self.fl = fluide or Propane()

    # ---- ventilation asservie ------------------------------------------------
    def ratio_ventilation(self, f: float) -> float:
        c = self.c
        r = 0.55 + 0.45 * (f - c.f_min) / (c.f_nom - c.f_min)
        return min(max(r, 0.5), 1.2)

    # ---- compresseur ---------------------------------------------------------
    def compresseur(self, Te: float, Tc: float, f: float):
        c, fl = self.c, self.fl
        T_bp_asp = Te - c.dT_aspiration
        p_asp = fl.psat(T_bp_asp)
        p_ref = fl.psat(Tc + c.dT_refoulement)
        T1 = T_bp_asp + c.surchauffe
        h1, s1, rho1 = fl.pT(p_asp, T1)
        PR = p_ref / p_asp

        eta_v = 1.0 + c.espace_mort - c.espace_mort * PR ** (1.0 / c.n_poly)
        eta_v *= 1.0 - c.k_fuite * (PR - 1.0) * math.sqrt(c.f_nom / max(f, 1.0))
        eta_v = min(max(eta_v, 0.05), 1.0)

        eta_is = c.eta_is_max * (1.0 - 0.012 * (PR - c.PR_opt) ** 2)
        eta_is *= 1.0 - 0.08 * ((f - c.f_opt) / c.f_opt) ** 2
        eta_is = min(max(eta_is, 0.25), 0.80)

        eta_mot = 0.935 - 0.06 * ((f - 70.0) / 70.0) ** 2

        m = rho1 * c.cylindree_cm3 * 1e-6 * f * eta_v
        T2s_init = (T1 + T0) * PR ** (0.12 / 1.12) - T0
        h2s = fl.h_ps(p_ref, s1, max(T2s_init, Tc + 1.0))
        w = (h2s - h1) / eta_is
        h2 = h1 + (1.0 - c.pertes_carter) * w
        return dict(p_asp=p_asp, p_ref=p_ref, h1=h1, s1=s1, h2=h2, PR=PR,
                    eta_v=eta_v, eta_is=eta_is, eta_mot=eta_mot, m=m, w=w)

    def h_sortie_condenseur(self, Tc: float) -> float:
        fl, sc = self.fl, self.c.sous_refroid
        if sc < 0.1:
            return fl.sat(Tc, 0.0)[1]
        h, _, _ = fl.pT(fl.psat(Tc), Tc - sc)
        return h

    # ---- côtés air -----------------------------------------------------------
    def cotes_air(self, cond: Conditions, f: float):
        c, t = self.c, self.c.techno
        r = cond.ratio_vent if cond.ratio_vent is not None else self.ratio_ventilation(f)
        w_int = w_from_hr(cond.T_int, cond.HR_int)
        w_ext = w_from_hr(cond.T_ext, cond.HR_ext)
        UA_int = c.UA_int_ref * t["k_UA"] * r ** c.exposant_UA_debit
        UA_ext = c.UA_ext_ref * t["k_UA"] * r ** c.exposant_UA_debit
        air_int = CoteAir(cond.T_int, w_int, c.debit_int_nom * r, UA_int)
        air_ext = CoteAir(cond.T_ext, w_ext, c.debit_ext_nom * r, UA_ext)
        P_vent = (c.P_vent_int_nom + c.P_vent_ext_nom) * t["k_vent"] * r ** 3
        return air_int, air_ext, P_vent, r

    # ---- résolution du cycle -------------------------------------------------
    def resoudre(self, cond: Conditions, f: float | None = None) -> Etat:
        c, fl = self.c, self.fl
        f = cond.freq if f is None else f
        e = Etat(mode=cond.mode, freq=f)
        air_int, air_ext, P_vent, _ = self.cotes_air(cond, f)
        if cond.mode == "chauffage":
            air_c, air_e = air_int, air_ext
        else:
            air_c, air_e = air_ext, air_int
        e.debit_int, e.debit_ext = air_int.debit_m3h, air_ext.debit_m3h

        Tc_max = min(fl.Tcrit - 8.0, 88.0)
        alarmes = []

        def Tc_pour_Te(Te):
            def r(Tc):
                k = self.compresseur(Te, Tc, f)
                h3 = self.h_sortie_condenseur(Tc)
                return k["m"] * (k["h2"] - h3) - air_c.Q_condenseur(Tc)

            lo = max(air_c.T_in + 0.05, Te + 2.0)
            r_lo, r_hi = r(lo), r(Tc_max)
            if r_hi > 0:
                return Tc_max, True
            if r_lo < 0:
                return lo, False
            return brentq(r, lo, Tc_max, xtol=0.01), False

        def g(Te):
            Tc, _ = Tc_pour_Te(Te)
            k = self.compresseur(Te, Tc, f)
            h4 = self.h_sortie_condenseur(Tc)
            Q_ref = k["m"] * (k["h1"] - h4)
            Q_air, _, _ = air_e.Q_evaporateur(Te)
            return Q_ref - Q_air

        Te_hi = air_e.T_in - 0.05
        Te_lo = max(-42.0, air_e.T_in - 50.0)
        try:
            if g(Te_lo) > 0:
                Te = Te_lo
                alarmes.append("Évaporation hors plage basse")
            else:
                Te = brentq(g, Te_lo, Te_hi, xtol=0.01)
            Tc, hp_sature = Tc_pour_Te(Te)
        except Exception as exc:  # pragma: no cover
            e.message = f"Échec de résolution : {exc}"
            return e
        if hp_sature:
            alarmes.append("Pression HP maximale (hors enveloppe)")

        k = self.compresseur(Te, Tc, f)
        h3 = self.h_sortie_condenseur(Tc)
        m = k["m"]
        e.Te, e.Tc, e.m_dot = Te, Tc, m
        e.p_bp, e.p_hp, e.PR = k["p_asp"], k["p_ref"], k["PR"]
        e.eta_v, e.eta_is, e.eta_mot = k["eta_v"], k["eta_is"], k["eta_mot"]
        e.T_refoul = fl.T_ph(k["p_ref"], k["h2"])
        e.W_arbre = m * k["w"]
        e.P_comp = e.W_arbre / (k["eta_mot"] * c.eta_variateur)
        e.P_vent = P_vent
        e.P_tot = e.P_comp + P_vent + c.P_veille
        e.Q_cond = m * (k["h2"] - h3)
        e.Q_evap = m * (k["h1"] - h3)
        Q_e_air, Q_lat, m_eau = air_e.Q_evaporateur(Te)
        e.Q_lat = Q_lat * (e.Q_evap / Q_e_air) if Q_e_air > 0 else 0.0
        e.eau_kg_h = m_eau * 3600.0

        if cond.mode == "chauffage":
            e.Q_utile = e.Q_sensible = e.Q_cond
            e.T_air_int_out = air_int.T_in + e.Q_cond / air_int.C
            e.T_air_ext_out = air_ext.T_in - (e.Q_evap - e.Q_lat) / air_ext.C
            T_ch, T_fr = cond.T_int, cond.T_ext
            e.givre = (Te + 0.25 * (cond.T_ext - Te)) < 0.0 and m_eau > 0
        else:
            e.Q_utile = e.Q_evap
            e.Q_sensible = e.Q_evap - e.Q_lat
            e.T_air_int_out = air_int.T_in - e.Q_sensible / air_int.C
            e.T_air_ext_out = air_ext.T_in + e.Q_cond / air_ext.C
            T_ch, T_fr = cond.T_ext, cond.T_int

        e.COP_cycle = e.Q_utile / e.W_arbre
        e.COP = e.Q_utile / e.P_tot
        dT = T_ch - T_fr
        if cond.mode == "chauffage":
            e.COP_carnot = (T_ch + T0) / dT if dT > 0.5 else float("inf")
        else:
            e.COP_carnot = (T_fr + T0) / dT if dT > 0.5 else float("inf")
        e.eta_exergie = e.COP / e.COP_carnot if math.isfinite(e.COP_carnot) else float("nan")

        # Dégivrage (chauffage) : bilan sur un cycle givrage + dégivrage
        e.Q_integre, e.COP_integre = e.Q_utile, e.COP
        if e.givre:
            M = c.givre_max_ref * c.techno["k_givre"]
            t_givr = M / m_eau
            t_d = c.duree_degivrage
            E_fonte = M * (334e3 + 2100.0 * max(0.0, -Te)) / c.rendement_degivrage
            E_piece = max(0.0, E_fonte - c.P_degivrage * t_d)  # prélevé dans la pièce
            Q_moy = (0.95 * e.Q_utile * t_givr - E_piece) / (t_givr + t_d)
            P_moy = (e.P_tot * t_givr + c.P_degivrage * t_d) / (t_givr + t_d)
            e.frac_degivrage = t_d / (t_givr + t_d)
            e.Q_integre, e.COP_integre = Q_moy, Q_moy / P_moy

        # Charge de propane estimée
        t = c.techno
        V_c = (c.V_bat_int if cond.mode == "chauffage" else c.V_bat_ext) * t["k_vol"]
        V_e = (c.V_bat_ext if cond.mode == "chauffage" else c.V_bat_int) * t["k_vol"]
        _, _, _, rl_c = fl.sat(Tc, 0.0)
        _, _, _, rv_c = fl.sat(Tc, 1.0)
        _, _, _, rl_e = fl.sat(Te, 0.0)
        _, _, _, rv_e = fl.sat(Te, 1.0)
        charge = (V_c * (0.25 * rl_c + 0.75 * rv_c) + V_e * (0.10 * rl_e + 0.90 * rv_e)
                  + c.V_lignes * 0.3 * rl_c + c.V_carter * rv_c) * 1e-3
        charge += c.masse_huile * c.solubilite_huile
        e.charge_g = charge * 1000.0

        if e.T_refoul > c.T_refoul_max:
            alarmes.append(f"T refoulement > {c.T_refoul_max:.0f} °C")
        if e.Te < -35:
            alarmes.append("BP très basse")

        e.points_ph = self._points_ph(k, Te, Tc, h3)
        e.alarmes = alarmes
        e.ok = True
        return e

    def _points_ph(self, k, Te, Tc, h3):
        fl = self.fl
        p_e = fl.psat(Te)
        p_c = fl.psat(Tc)
        hv_c = fl.sat(Tc, 1.0)[1]
        hl_c = fl.sat(Tc, 0.0)[1]
        hv_e = fl.sat(Te, 1.0)[1]
        # compression représentée par quelques points intermédiaires
        pts = []
        for i in range(6):
            x = i / 5
            pts.append((k["h1"] + x * (k["h2"] - k["h1"]),
                        k["p_asp"] * (k["p_ref"] / k["p_asp"]) ** x))
        pts += [(k["h2"], p_c), (hv_c, p_c), (hl_c, p_c), (h3, p_c),
                (h3, p_e), (hv_e, p_e), (k["h1"], p_e), (k["h1"], k["p_asp"])]
        return [(h / 1e3, p / 1e5) for h, p in pts]

    # ---- charge du bâtiment et régulation inverter ----------------------------
    def besoin(self, cond: Conditions, H: float, apports: float) -> float:
        """Besoin thermique (W, sensible) de la pièce aux conditions données."""
        H_tot = H + self.c.UA_kit_fenetre
        if cond.mode == "chauffage":
            return H_tot * (cond.T_int - cond.T_ext) - apports
        return H_tot * (cond.T_ext - cond.T_int) + apports

    def regulation(self, cond: Conditions, besoin: float):
        """Fréquence qui égalise la capacité sensible au besoin.

        Retourne (f, PLR, statut). PLR < 1 : cyclage à f_min.
        """
        c = self.c
        if besoin <= 0:
            return 0.0, 0.0, "arrêt"

        def Q(f):
            e = self.resoudre(cond, f)
            return e.Q_sensible if e.ok else 0.0

        q_min = Q(c.f_min)
        if q_min >= besoin:
            return c.f_min, besoin / q_min, "cyclage"
        q_max = Q(c.f_max)
        if q_max <= besoin:
            return c.f_max, 1.0, "capacité insuffisante"
        f = brentq(lambda f: Q(f) - besoin, c.f_min, c.f_max, xtol=0.2)
        return f, 1.0, "modulation"

    def facteur_cyclage(self, PLR: float) -> float:
        return 1.0 - self.c.Cd * (1.0 - PLR)

    # ---- charge maximale admissible ------------------------------------------
    def charge_max_iec(self):
        """Charge max R290 selon IEC 60335-2-40 (formule pièce), en g.

        m_max = 2.5 * LFL^(5/4) * h0 * A^(1/2), LFL = 0.038 kg/m3.
        m1 = 4 * LFL (en kg, soit 152 g) : pas de contrainte de surface en dessous.
        (Valeurs à vérifier selon l'édition applicable de la norme.)
        """
        LFL = 0.038
        m_max = 2.5 * LFL ** 1.25 * self.c.h0_installation * math.sqrt(self.c.surface_piece)
        return m_max * 1000.0, 4 * LFL * 1000.0

    def avec_techno(self, techno: str) -> "PompeAChaleur":
        return PompeAChaleur(replace(self.c, technologie=techno), self.fl)
