"""
Boucle de simulation temps réel, indépendante de l'affichage.

Gère la régulation inverter (rampe de fréquence), la temporisation d'inversion
de la vanne 4 voies, le temps simulé et le calcul progressif de la courbe
COP = f(T extérieure). Utilisé par l'interface web (`serveur.py`).
"""

from __future__ import annotations

import math
from dataclasses import asdict

import numpy as np

from .physique import (TECHNO_REFERENCE, TECHNOLOGIES, Conception, Conditions,
                       PompeAChaleur, Propane)

CONDITIONS_TYPES = {  # conditions de référence proposées au changement de mode
    "chauffage": dict(T_ext=7.0, T_int=20.0, HR_ext=87.0, HR_int=50.0),
    "clim": dict(T_ext=35.0, T_int=27.0, HR_ext=40.0, HR_int=47.0),
}

# (clé, libellé, min, max, valeur initiale, pas)
REGLAGES = [
    ("T_ext", "T extérieure (°C)", -20, 46, 7.0, 0.5),
    ("T_int", "T intérieure (°C)", 10, 32, 20.0, 0.5),
    ("HR_ext", "HR extérieure (%)", 20, 100, 87.0, 1),
    ("HR_int", "HR intérieure (%)", 20, 90, 50.0, 1),
    ("H", "Déperditions pièce H (W/K)", 20, 200, 90.0, 1),
    ("apports", "Apports internes/solaires (W)", 0, 1500, 300.0, 10),
    ("freq", "Fréquence manuelle (Hz)", 15, 110, 60.0, 0.5),
    ("debit_int", "Débit air intérieur (m³/h)", 150, 800, 520.0, 10),
    ("debit_ext", "Débit air extérieur (m³/h)", 400, 1800, 1300.0, 10),
    ("vitesse", "Accélération du temps (x)", 1, 120, 20.0, 1),
]

# Paramètres de conception réglables par composant (onglet « Simulateur temps réel 2 »).
# (composant, clé de Conception, libellé, unité, min, max, pas). Valeur initiale : défaut de Conception.
CONCEPTION_REGLABLE = [
    ("compresseur", "cylindree_cm3", "Cylindrée", "cm³", 4, 40, 0.5),
    ("compresseur", "f_min", "Fréquence min", "Hz", 10, 40, 1),
    ("compresseur", "f_max", "Fréquence max", "Hz", 70, 140, 1),
    ("compresseur", "eta_is_max", "η isentropique max", "", 0.40, 0.85, 0.01),
    ("bat_int", "UA_int_ref", "UA nominal", "W/K", 60, 1000, 10),
    ("bat_int", "debit_int_nom", "Débit d'air nominal", "m³/h", 150, 1200, 10),
    ("bat_int", "P_vent_int_nom", "Ventilateur nominal", "W", 5, 150, 1),
    ("bat_int", "V_bat_int", "Volume interne", "L", 0.10, 3.0, 0.05),
    ("bat_ext", "UA_ext_ref", "UA nominal", "W/K", 60, 1500, 10),
    ("bat_ext", "debit_ext_nom", "Débit d'air nominal", "m³/h", 300, 2500, 10),
    ("bat_ext", "P_vent_ext_nom", "Ventilateur nominal", "W", 5, 250, 1),
    ("bat_ext", "V_bat_ext", "Volume interne", "L", 0.10, 4.0, 0.05),
    ("detendeur", "surchauffe", "Surchauffe", "K", 1, 15, 0.5),
    ("detendeur", "sous_refroid", "Sous-refroidissement", "K", 0, 15, 0.5),
]


def _json(v):
    """Remplace NaN / inf par None pour une sérialisation JSON stricte."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {k: _json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json(x) for x in v]
    if isinstance(v, np.floating):
        return _json(float(v))
    return v


class Moteur:
    RAMPE_HZ_S = 1.5        # vitesse de variation de l'inverter
    DELAI_INVERSION = 120.0  # s, égalisation des pressions avant redémarrage
    K_UA_MIN, K_UA_MAX = 0.2, 5.0  # bornes du multiplicateur d'UA réglable
    T_EXT_COURBE = {"chauffage": np.linspace(-20, 18, 14), "clim": np.linspace(18, 46, 13)}

    def __init__(self):
        self.fluide = Propane()
        # copie des multiplicateurs par machine : modifiables sans toucher aux valeurs par défaut
        self.pac = {t: PompeAChaleur(Conception(technologie=t, multiplicateurs=dict(v)), self.fluide)
                    for t, v in TECHNOLOGIES.items()}
        self.params = {k: v for k, _, _, _, v, _ in REGLAGES}
        self.params.update(mode="chauffage", techno="Impression 3D métal (TPMS)", auto=True, ventil_auto=True,
                           k_UA={t: v["k_UA"] for t, v in TECHNOLOGIES.items()},
                           conception={k: float(getattr(Conception, k)) for _, k, *_ in CONCEPTION_REGLABLE})
        self.t_sim = 0.0
        self.f_reel = 0.0
        self.f_cible = 0.0
        self.PLR, self.statut, self.besoin = 1.0, "", 0.0
        self.delai = 10.0
        self.dirty = True
        self._cache_cle, self._cache_etat = None, None
        self.courbe = {}
        self._courbe_iter = None

    # --------------------------------------------------------------- réglages
    def regler(self, modifs: dict):
        p = self.params
        for k, v in modifs.items():
            if k not in p:
                continue
            if k == "mode":
                if v not in CONDITIONS_TYPES or v == p["mode"]:
                    continue
                p["mode"] = v
                p.update(CONDITIONS_TYPES[v])
                self.f_reel = 0.0
                self.delai = self.DELAI_INVERSION
            elif k == "techno":
                if v in TECHNOLOGIES:
                    p[k] = v
            elif k == "k_UA":
                for t, val in v.items():
                    if t in TECHNOLOGIES:
                        val = min(max(float(val), self.K_UA_MIN), self.K_UA_MAX)
                        p[k][t] = self.pac[t].c.multiplicateurs["k_UA"] = val
                self._cache_cle = None
            elif k == "conception":
                self._regler_conception(v)
            elif k in ("auto", "ventil_auto"):
                p[k] = bool(v)
            else:
                lo, hi = next((a, b) for c, _, a, b, _, _ in REGLAGES if c == k)
                p[k] = min(max(float(v), lo), hi)
        self.dirty = True

    def _regler_conception(self, modifs: dict):
        """Applique des paramètres de conception à toutes les machines (une par technologie)."""
        bornes = {k: (lo, hi) for _, k, _, _, lo, hi, _ in CONCEPTION_REGLABLE}
        c = self.params["conception"]
        for k, val in modifs.items():
            if k not in bornes:
                continue
            lo, hi = bornes[k]
            c[k] = float(min(max(float(val), lo), hi))
        c["f_min"] = min(c["f_min"], Conception.f_nom - 5)  # ratio_ventilation divise par f_nom - f_min
        c["f_max"] = max(c["f_max"], Conception.f_nom + 5)
        for pac in self.pac.values():
            for k, val in c.items():
                setattr(pac.c, k, val)
        self._cache_cle = None

    # --------------------------------------------------------------- calculs
    def conditions(self, f=None) -> Conditions:
        p = self.params
        manuel = not p["ventil_auto"]
        return Conditions(mode=p["mode"], T_ext=p["T_ext"], T_int=p["T_int"],
                          HR_ext=p["HR_ext"] / 100, HR_int=p["HR_int"] / 100,
                          freq=self.f_reel if f is None else f,
                          debit_int=p["debit_int"] if manuel else None,
                          debit_ext=p["debit_ext"] if manuel else None)

    def _consigne(self, pac, cond):
        """(f, PLR, statut, besoin) pour une PAC et des conditions données."""
        besoin = pac.besoin(cond, self.params["H"], self.params["apports"])
        if self.params["auto"]:
            f, PLR, statut = pac.regulation(cond, besoin)
        else:
            f, PLR, statut = self.params["freq"], 1.0, "manuel"
        return f, PLR, statut, besoin

    def _maj_cible(self):
        pac = self.pac[self.params["techno"]]
        self.f_cible, self.PLR, self.statut, self.besoin = self._consigne(pac, self.conditions())
        self.courbe = {}
        self._courbe_iter = self._generer_courbe()
        self.dirty = False

    def _generer_courbe(self):
        cond0 = self.conditions()
        techno = self.params["techno"]
        refs = [techno] + ([TECHNO_REFERENCE] if techno != TECHNO_REFERENCE else [])
        for T in self.T_EXT_COURBE[self.params["mode"]]:
            for t in refs:
                pac = self.pac[t]
                cond = Conditions(**{**cond0.__dict__, "T_ext": float(T)})
                f, PLR, statut, _ = self._consigne(pac, cond)
                if f <= 0:
                    val = (np.nan, np.nan)
                else:
                    e = pac.resoudre(cond, f)
                    k = pac.facteur_cyclage(PLR)
                    val = (e.COP_integre * k, e.COP * k) if e.ok else (np.nan, np.nan)
                self.courbe.setdefault(t, []).append((float(T), *val))
            yield

    def _etat(self, f):
        pac = self.pac[self.params["techno"]]
        cond = self.conditions(f)
        cle = (self.params["techno"], self.params["mode"],
               tuple(round(v, 3) for v in cond.__dict__.values() if isinstance(v, float)))
        if cle != self._cache_cle:
            self._cache_cle, self._cache_etat = cle, pac.resoudre(cond, f)
        return self._cache_etat

    # --------------------------------------------------------------- boucle
    def pas(self, dt_reel=0.1):
        if self.dirty:
            self._maj_cible()
        if self._courbe_iter is not None:
            try:
                next(self._courbe_iter)
            except StopIteration:
                self._courbe_iter = None

        dt = dt_reel * self.params["vitesse"]
        self.t_sim += dt
        c = self.pac[self.params["techno"]].c
        if self.delai > 0:
            self.delai -= dt
            self.f_reel = 0.0
        elif self.f_cible <= 0:
            self.f_reel = 0.0
        else:
            if self.f_reel < c.f_min:
                self.f_reel = c.f_min  # démarrage
            df = self.f_cible - self.f_reel
            pas_max = self.RAMPE_HZ_S * dt
            self.f_reel += max(-pas_max, min(pas_max, df))
        return self.instantane()

    def instantane(self) -> dict:
        """État courant complet, sérialisable en JSON."""
        pac = self.pac[self.params["techno"]]
        e = self._etat(self.f_reel) if self.f_reel > 0 else None
        marche = e is not None and e.ok
        k_cyc = pac.facteur_cyclage(self.PLR) if marche else 1.0
        cop_eff = e.COP_integre * k_cyc if marche else None
        q_eff = e.Q_integre * self.PLR if marche else 0.0
        p_eff = q_eff / cop_eff if marche and cop_eff > 0 else 0.0
        m_max, m1 = pac.charge_max_iec()
        cascade = None
        if marche:
            cascade = pac.cascade_pertes(self.conditions(), e) + [("cyclage", cop_eff)]
        detail_cop = self._detail_cop(pac, e, k_cyc, cop_eff) if marche else None
        cycles_ref = pac.cycles_reference(self.conditions(), e) if marche else None
        return _json(dict(
            cascade=cascade, detail_cop=detail_cop, cycles_ref=cycles_ref,
            params=self.params, t_sim=self.t_sim, f_reel=self.f_reel, f_cible=self.f_cible,
            PLR=self.PLR, statut=self.statut, besoin=self.besoin, delai=self.delai,
            marche=marche, k_cyc=k_cyc, cop_eff=cop_eff, q_eff=q_eff, p_eff=p_eff,
            etat=asdict(e) if e is not None else None,
            courbe=self.courbe, courbe_complete=self._courbe_iter is None,
            iec=dict(m_max=m_max, m1=m1, h0=pac.c.h0_installation, surface=pac.c.surface_piece),
        ))

    def _detail_cop(self, pac, e, k_cyc, cop_eff) -> dict:
        """Grandeurs intermédiaires du calcul du COP effectif, pour l'affichage pas à pas."""
        c, fl = pac.c, pac.fl
        k = pac.compresseur(e.Te, e.Tc, e.freq)
        p1 = e.points["1"]
        rho1 = fl.pT(k["p_asp"], p1["T"])[2]
        h2s = k["h1"] + k["w"] * k["eta_is"]
        P_integre = e.Q_integre / e.COP_integre if e.COP_integre else float("nan")
        return dict(
            carte=c.carte is not None, mode=e.mode,
            rho1=rho1, V_cyl=c.cylindree_cm3, f=e.freq, eta_v=e.eta_v, m=e.m_dot,
            h1=k["h1"] / 1e3, h2s=h2s / 1e3, h2=k["h2"] / 1e3, h3=e.points["3"]["h"],
            eta_is=e.eta_is, w=k["w"] / 1e3, pertes_carter=c.pertes_carter, W_arbre=e.W_arbre,
            eta_mot=e.eta_mot, eta_var=k["eta_var"], P_comp=e.P_comp,
            P_vent=e.P_vent, P_veille=c.P_veille, P_tot=e.P_tot,
            Q_utile=e.Q_utile, COP=e.COP,
            givre=e.givre, frac_degivrage=e.frac_degivrage, Q_integre=e.Q_integre,
            P_integre=P_integre, COP_integre=e.COP_integre, duree_degivrage=c.duree_degivrage,
            P_degivrage=c.P_degivrage,
            Cd=c.Cd, PLR=self.PLR, k_cyc=k_cyc, cop_eff=cop_eff, besoin=self.besoin, statut=self.statut,
            surchauffe=c.surchauffe, sous_refroid=c.sous_refroid, Te=e.Te, Tc=e.Tc,
            p_asp=k["p_asp"] / 1e5, p_ref=k["p_ref"] / 1e5,
            dT_asp=c.dT_aspiration, dT_ref=c.dT_refoulement, PR=e.PR,
            eta_is_max=c.eta_is_max, PR_opt=c.PR_opt, f_opt=c.f_opt, f_nom=c.f_nom,
            espace_mort=c.espace_mort, n_poly=c.n_poly, k_fuite=c.k_fuite,
        )

    def statique(self) -> dict:
        """Données fixes : cloche de saturation, réglages, technologies."""
        fl = self.fluide
        dome = []
        for t in np.linspace(-42, fl.Tcrit - 0.3, 160):
            pl, h_l, _, _ = fl.sat(float(t), 0.0)
            _, h_v, _, _ = fl.sat(float(t), 1.0)
            dome.append((h_l / 1e3, h_v / 1e3, pl / 1e5))
        isothermes = [(t, fl.psat(t) / 1e5) for t in (-20, 0, 20, 40, 60)]
        return _json(dict(
            dome=dome, isothermes=isothermes, technologies=TECHNOLOGIES,
            reference=TECHNO_REFERENCE, reglages=REGLAGES, conception=CONCEPTION_REGLABLE,
            conception_defaut={k: float(getattr(Conception, k)) for _, k, *_ in CONCEPTION_REGLABLE},
            UA_ref=dict(int=Conception.UA_int_ref, ext=Conception.UA_ext_ref),
            k_UA_bornes=(self.K_UA_MIN, self.K_UA_MAX),
            T_ext_courbe={m: list(map(float, v)) for m, v in self.T_EXT_COURBE.items()},
        ))
