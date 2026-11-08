"""
Modèles d'échangeurs air / propane pour le comparateur de surfaces.

Chaque échangeur expose l'interface utilisée par `aeraulique.CircuitAir` :
    UA(debit_m3h, T_in) -> (UA W/K, détail, alertes)
    dp(Q m³/s, T_in, T_out) -> (Δp Pa, Re, f)
    A_frontale, volume_propane_L, masse_kg

Familles :
  * EchangeurTPMS (feuillet) : réseau air F > n_air, paroi, réseau propane F < n_propane.
  * EchangeurTPMS (hybride)  : réseau air TPMS, tout le reste solide, propane dans des
    tubes ronds noyés ; la structure TPMS travaille en ailette (rendement d'ailette).
  * EchangeurTubesNus        : faisceau de tubes nus ronds en quinconce (VDI Heat Atlas :
    Gnielinski pour l'échange, Gaddis–Gnielinski pour la perte de charge).

Côté air TPMS, j et f viennent de la campagne CFD (donnees/correlations_air_tpms.json,
outils/cfd_tpms) ; à défaut, pour le gyroïde seulement, de la corrélation de Leeds (eau).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .aeraulique import CP_AIR, _leeds_gyroide, j_leeds_gyroide, k_air, mu_air, rho_air_sec
from .tpms import geometrie, niveau_pour_porosite, proprietes_reduites

FICHIER_CFD = Path(__file__).with_name("donnees") / "correlations_air_tpms.json"
PR_AIR = 0.71


def correlations_cfd() -> dict:
    if not FICHIER_CFD.exists():
        return {}
    return json.loads(FICHIER_CFD.read_text()).get("correlations", {})


def correlation_air(surface: str, phi_air: float):
    """(j(Re), f(Re), source, f_apparent, (Re_min, Re_max)) ou None si aucune donnée."""
    cfd = correlations_cfd()
    proches = [c for c in cfd.values() if c["surface"] == surface]
    if proches:
        c = min(proches, key=lambda c: abs(c["phi_air"] - phi_air))
        J, F = c["j"], c["f"]
        src = f"CFD air (φ {c['phi_air']:.2f}, Re {c['Re_min']:.0f}–{c['Re_max']:.0f})"
        if abs(c["phi_air"] - phi_air) > 0.05:
            src += f" ; porosité demandée {phi_air:.2f} : extrapolation"
        return (lambda Re: J["a"] * Re ** -J["b"], lambda Re: F["a"] * Re ** -F["b"], src, True,
                (c["Re_min"], c["Re_max"]))
    if surface == "gyroide":
        return (j_leeds_gyroide, lambda Re: _leeds_gyroide(Re, None),
                "Leeds (eau, Pr 7) : estimation", False, (20.0, 8000.0))
    return None


def _G_Re(debit_m3h, T_in, sigma, A_f, Dh):
    G = debit_m3h / 3600.0 * rho_air_sec(T_in) / (sigma * A_f)
    return G, G * Dh / mu_air(T_in)


# ------------------------------------------------------------------- TPMS
@dataclass
class EchangeurTPMS:
    surface: str
    largeur: float              # m
    hauteur: float              # m
    profondeur: float           # m (sens de l'air)
    phi_air: float              # porosité côté air
    Dh: float                   # m, diamètre hydraulique côté air
    k_metal: float              # W/m/K
    rho_metal: float            # kg/m³
    h_propane: float            # W/m²/K
    mode: str = "feuillet"      # "feuillet" ou "hybride"
    phi_propane: float = 0.10   # feuillet : fraction de volume du réseau propane
    d_tube: float = 3.0e-3      # hybride : diamètre extérieur des tubes (m)
    e_tube: float = 0.4e-3      # hybride : épaisseur de tube (m)
    pas_tube: float = 12e-3     # hybride : pas des tubes (m), en hauteur et en profondeur

    def __post_init__(self):
        self.geo = geometrie(self.surface, self.phi_air, Dh=self.Dh)
        self.L, self.beta_air = self.geo["L"], self.geo["beta_air"]
        self.corr = correlation_air(self.surface, self.phi_air)
        V = self.V_coeur
        if self.mode == "feuillet":
            n_p = niveau_pour_porosite(self.surface, 1.0 - self.phi_propane)
            _, s_red = proprietes_reduites(self.surface, round(n_p, 6))
            self.beta_propane = s_red / self.L
            self.phi_paroi = 1.0 - self.phi_air - self.phi_propane
            self.e_paroi = self.phi_paroi / (0.5 * (self.beta_air + self.beta_propane))
            self.A_propane = self.beta_propane * V
            self._V_prop = self.phi_propane * V
            self._masse = self.phi_paroi * V * self.rho_metal
        else:
            n_haut = max(1, int(self.hauteur / self.pas_tube))
            n_prof = max(1, round(self.profondeur / self.pas_tube))
            self.n_tubes = n_haut * n_prof
            d_i = self.d_tube - 2 * self.e_tube
            self.A_propane = self.n_tubes * math.pi * d_i * self.largeur
            self._V_prop = self.n_tubes * math.pi * d_i ** 2 / 4 * self.largeur
            self._masse = ((1 - self.phi_air) * V * self.rho_metal)
            self.e_paroi = self.e_tube

    @property
    def A_frontale(self):
        return self.largeur * self.hauteur

    @property
    def V_coeur(self):
        return self.A_frontale * self.profondeur

    @property
    def volume_propane_L(self):
        return self._V_prop * 1e3

    @property
    def masse_kg(self):
        return self._masse

    def _alertes(self, Re):
        a = []
        if self.corr is None:
            a.append(f"{self.surface} : aucune corrélation côté air (lancer la campagne CFD)")
            return a
        lo, hi = self.corr[4]
        if not lo <= Re <= hi:
            a.append(f"Re air = {Re:.0f} hors plage de la corrélation ({lo:.0f}–{hi:.0f}) : extrapolation")
        return a

    def UA(self, debit_m3h: float, T_in: float):
        if self.corr is None:
            return float("nan"), {}, self._alertes(0)
        G, Re = _G_Re(debit_m3h, T_in, self.phi_air, self.A_frontale, self.Dh)
        Pr = CP_AIR * mu_air(T_in) / k_air(T_in)
        j = self.corr[0](Re)
        h = j * G * CP_AIR * Pr ** (-2 / 3)
        A_air = self.beta_air * self.V_coeur
        if self.mode == "feuillet":
            eta = 1.0
            R_paroi = self.e_paroi / (self.k_metal * 0.5 * (A_air + self.A_propane))
        else:
            # structure TPMS pleine = ailette volumique autour des tubes :
            # k_eff θ'' = h β θ, k_eff ≈ k (1−φ)^1.5 (réseau ouvert), ℓ = demi-distance entre tubes
            k_eff = self.k_metal * (1 - self.phi_air) ** 1.5
            m = math.sqrt(h * self.beta_air / k_eff)
            ell = max(self.pas_tube - self.d_tube, 1e-4) / 2
            eta = math.tanh(m * ell) / (m * ell)
            R_paroi = self.e_tube / (self.k_metal * self.A_propane)
        R_air = 1 / (eta * h * A_air)
        R_ref = 1 / (self.h_propane * self.A_propane)
        UA = 1 / (R_air + R_paroi + R_ref)
        return UA, dict(Re=Re, j=j, h_air=h, A_air=A_air, A_propane=self.A_propane, eta_ailette=eta,
                        part_R_air=R_air * UA, part_R_paroi=R_paroi * UA, part_R_propane=R_ref * UA), \
            self._alertes(Re)

    def dp(self, Q: float, T_in: float, T_out: float):
        if self.corr is None:
            return float("nan"), float("nan"), float("nan")
        r_in, r_out = rho_air_sec(T_in), rho_air_sec(T_out)
        r_m = 2.0 / (1.0 / r_in + 1.0 / r_out)
        T_m = 0.5 * (T_in + T_out)
        G = Q * r_in / (self.phi_air * self.A_frontale)
        Re = G * self.Dh / mu_air(T_m)
        f = self.corr[1](Re)
        s2 = self.phi_air ** 2
        frot = f * 4 * self.profondeur / self.Dh * r_in / r_m
        if self.corr[3]:   # f apparent CFD : entrée et sortie déjà comprises
            dp = G * G / (2 * r_in) * (frot + 2 * (r_in / r_out - 1))
        else:              # Kays & London, Kc / Ke usuels
            Kc, Ke = 0.5, 0.15
            dp = G * G / (2 * r_in) * ((Kc + 1 - s2) + 2 * (r_in / r_out - 1) + frot - (1 - s2 - Ke) * r_in / r_out)
        return dp, Re, f


# ------------------------------------------------------------------- tubes nus
@dataclass
class EchangeurTubesNus:
    """Faisceau de tubes nus ronds en quinconce, tubes horizontaux sur toute la largeur."""
    largeur: float
    hauteur: float
    profondeur: float
    d: float                    # m, diamètre extérieur
    e: float                    # m, épaisseur de paroi
    a: float                    # pas transversal / d
    b: float                    # pas longitudinal / d
    k_metal: float
    rho_metal: float
    h_propane: float

    def __post_init__(self):
        self.n_haut = max(1, int(self.hauteur / (self.a * self.d)))
        self.n_rangs = max(1, int(self.profondeur / (self.b * self.d)))
        self.n_tubes = self.n_haut * self.n_rangs
        d_i = self.d - 2 * self.e
        self.A_air = self.n_tubes * math.pi * self.d * self.largeur
        self.A_propane = self.n_tubes * math.pi * d_i * self.largeur
        self._V_prop = self.n_tubes * math.pi * d_i ** 2 / 4 * self.largeur
        self._masse = self.n_tubes * math.pi * (self.d ** 2 - d_i ** 2) / 4 * self.largeur * self.rho_metal
        self.psi = 1 - math.pi / (4 * self.a) if self.b >= 1 else 1 - math.pi / (4 * self.a * self.b)

    A_frontale = EchangeurTPMS.A_frontale
    V_coeur = EchangeurTPMS.V_coeur
    volume_propane_L = EchangeurTPMS.volume_propane_L
    masse_kg = EchangeurTPMS.masse_kg

    def _w_e(self, u):
        """Vitesse dans la section la plus étroite (transversale ou diagonale)."""
        c = math.sqrt((self.a / 2) ** 2 + self.b ** 2)
        gap = min(self.a - 1, 2 * (c - 1))
        return u * self.a / gap

    def UA(self, debit_m3h: float, T_in: float):
        u = debit_m3h / 3600 / self.A_frontale
        nu = mu_air(T_in) / rho_air_sec(T_in)
        Pr = CP_AIR * mu_air(T_in) / k_air(T_in)
        l = math.pi * self.d / 2
        Re = u * l / (self.psi * nu)
        Nu_lam = 0.664 * math.sqrt(Re) * Pr ** (1 / 3)
        Nu_tur = 0.037 * Re ** 0.8 * Pr / (1 + 2.443 * Re ** -0.1 * (Pr ** (2 / 3) - 1))
        Nu0 = 0.3 + math.sqrt(Nu_lam ** 2 + Nu_tur ** 2)
        fA = 1 + 2 / (3 * self.b)
        N = self.n_rangs
        Nu = Nu0 * (fA if N >= 10 else (1 + (N - 1) * fA) / N)
        h = Nu * k_air(T_in) / l
        R_air = 1 / (h * self.A_air)
        R_paroi = self.e / (self.k_metal * 0.5 * (self.A_air + self.A_propane))
        R_ref = 1 / (self.h_propane * self.A_propane)
        UA = 1 / (R_air + R_paroi + R_ref)
        al = [] if 10 <= Re <= 1e6 else [f"Re_ψ = {Re:.0f} hors domaine Gnielinski (10–10⁶)"]
        return UA, dict(Re=Re, j=Nu / (Re * Pr ** (1 / 3)), h_air=h, A_air=self.A_air, A_propane=self.A_propane,
                        eta_ailette=1.0, part_R_air=R_air * UA, part_R_paroi=R_paroi * UA,
                        part_R_propane=R_ref * UA), al

    def dp(self, Q: float, T_in: float, T_out: float):
        T_m = 0.5 * (T_in + T_out)
        rho = rho_air_sec(T_m)
        u = Q * rho_air_sec(T_in) / rho / self.A_frontale
        w = self._w_e(u)
        Re = w * self.d * rho / mu_air(T_m)
        a, b = self.a, self.b
        c = a if b >= 0.5 * math.sqrt(2 * a + 1) else math.sqrt((a / 2) ** 2 + b ** 2)
        xi_l = 280 * math.pi * ((b ** 0.5 - 0.6) ** 2 + 0.75) / ((4 * a * b - math.pi) * c ** 1.6) / Re
        xi_t = (2.5 + 1.2 / (a - 0.85) ** 1.08 + 0.4 * (b / a - 1) ** 3 - 0.01 * (a / b - 1) ** 3) * Re ** -0.25
        xi = xi_l + xi_t * (1 - math.exp(-(Re + 1000) / 2000))
        return xi * self.n_rangs * rho * w * w / 2, Re, xi
