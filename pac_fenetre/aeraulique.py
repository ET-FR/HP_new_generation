"""
Aéraulique : puissance ventilateur calculée physiquement.

Remplace la loi P = P_nom × k_vent × r³ par :

    1. Courbe du circuit d'air : Δp(Q) = Δp échangeur + Σ pertes singulières
       * échangeur : formulation de Kays & London (contraction d'entrée,
         accélération, frottement du cœur, expansion de sortie) avec un facteur
         de frottement de Fanning f(Re) fourni par une corrélation choisie ;
       * accessoires (grilles, filtre, coudes) : K × ρ u² / 2 sur leur section.
    2. Point de fonctionnement du ventilateur réel : vitesse n telle que la
       courbe constructeur, transposée par les lois de similitude
       (Q ∝ n, Δp ∝ n², P ∝ n³), passe par (Q, Δp du circuit).
    3. Puissance électrique : interpolée entre les courbes mesurées à
       plusieurs vitesses, ce qui capte la baisse de rendement du moteur EC
       à basse vitesse (les lois de similitude seules l'ignorent).

Toutes les données (géométrie, coefficients Kc / Ke, ventilateur) viennent
d'un fichier JSON : aucune valeur n'est supposée ici. Voir
`config_air/EXEMPLE_aeraulique.json`.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field

from scipy.optimize import brentq

from .gyroide import GeometrieGyroide

R_AIR = 287.05


def rho_air_sec(T: float) -> float:
    return 101325.0 / (R_AIR * (T + 273.15))


def k_air(T: float) -> float:
    """Conductivité de l'air sec (W/m/K), linéaire 0 à 50 °C."""
    return 0.02414 + 7.5e-5 * T


CP_AIR = 1006.0


def mu_air(T: float) -> float:
    """Viscosité dynamique de l'air (Sutherland), Pa.s."""
    Tk = T + 273.15
    return 1.716e-5 * (Tk / 273.15) ** 1.5 * (273.15 + 110.4) / (Tk + 110.4)


# --------------------------------------------------------------------------
# Corrélations de frottement (Fanning)
# --------------------------------------------------------------------------
def _canal_droit(Re: float, geo) -> float:
    """PROVISOIRE, PAS UN GYROÏDE : canal droit circulaire établi.
    Laminaire f = 16/Re, turbulent Blasius f = 0,079 Re^-0,25."""
    if Re < 2300.0:
        return 16.0 / max(Re, 1e-9)
    return 0.079 * Re ** -0.25


# Qureshi (Leeds, 2026), tableau 5.9 : gyroïde L = 10 mm, niveau 0, eau (Pr ≈ 7),
# CFD périodique, parois lisses. fA / jA : 20 ≤ Re < 130 (stationnaire) ;
# fB / jB : 200 ≤ Re ≤ 8000 (instationnaire, k-ω SST). Entre 130 et 200 : zone
# exclue des ajustements, interpolation linéaire en Re (alerte).
# f ne dépend pas de L par similitude dynamique : l'écart de ~9 % rapporté par
# la thèse entre L = 5 et 40 mm est traité comme une incertitude, pas un effet.
RE_MIN_LEEDS, RE_A_MAX, RE_B_MIN, RE_MAX_LEEDS = 20.0, 130.0, 200.0, 8000.0


def _fA(Re):
    return 25.21 * Re ** -0.743 + 0.1533


def _fB(Re):
    return 2.209 * Re ** -0.3243 + 0.3538


def _jA(Re):
    return 2.324 * Re ** -0.9467 + 0.03393


def _jB(Re):
    return 0.9448 * Re ** -0.4908 + 0.006636


def _deux_regimes(Re, fa, fb):
    Re_c = min(max(Re, RE_MIN_LEEDS), RE_MAX_LEEDS)   # pas d'extrapolation
    if Re_c < RE_A_MAX:
        return fa(Re_c)
    if Re_c < RE_B_MIN:
        x = (Re_c - RE_A_MAX) / (RE_B_MIN - RE_A_MAX)
        return fa(RE_A_MAX) + x * (fb(RE_B_MIN) - fa(RE_A_MAX))
    return fb(Re_c)


def _leeds_gyroide(Re: float, geo) -> float:
    """Fanning f, corrélation Qureshi (Leeds, 2026), tableau 5.9."""
    return _deux_regimes(Re, _fA, _fB)


def j_leeds_gyroide(Re: float) -> float:
    """Colburn j, corrélation Qureshi (Leeds, 2026), tableau 5.9.
    ATTENTION : établie pour de l'eau (Pr ≈ 7). Pour l'air (Pr ≈ 0,7), le
    passage par Pr^(1/3) est une approximation correcte en turbulent mais qui
    sous-estime h en laminaire (jusqu'à ~2x) : estimation basse."""
    return _deux_regimes(Re, _jA, _jB)


def alertes_domaine_leeds(Re: float) -> list:
    a = []
    if Re < RE_MIN_LEEDS or Re > RE_MAX_LEEDS:
        a.append(f"Re air = {Re:.0f} hors domaine Leeds (20-8000), valeur bornée")
    elif RE_A_MAX <= Re < RE_B_MIN:
        a.append(f"Re air = {Re:.0f} en zone de transition 130-200 (non ajustée, interpolée)")
    return a


CORRELATIONS_F = {
    "canal_droit_PROVISOIRE": _canal_droit,
    "leeds_gyroide": _leeds_gyroide,
}


# --------------------------------------------------------------------------
# Échangeur côté air
# --------------------------------------------------------------------------
@dataclass
class GeometrieEchangeur:
    A_frontale: float        # m², section frontale
    profondeur: float        # m, dans le sens de l'air
    sigma: float             # section libre / section frontale
    D_h: float               # m, diamètre hydraulique côté air
    Kc: float                # coefficient de contraction d'entrée
    Ke: float                # coefficient d'expansion de sortie
    correlation_f: str
    L_cellule: float | None = None   # m (corrélation gyroïde)
    R_offset: float | None = None    # m (corrélation gyroïde)

    def dp(self, Q: float, T_in: float, T_out: float):
        """Δp (Pa) et Re pour un débit volumique Q (m³/s) à l'entrée."""
        r_in, r_out = rho_air_sec(T_in), rho_air_sec(T_out)
        r_m = 2.0 / (1.0 / r_in + 1.0 / r_out)
        m = Q * r_in
        G = m / (self.sigma * self.A_frontale)        # kg/m²/s dans les pores
        T_m = 0.5 * (T_in + T_out)
        Re = G * self.D_h / mu_air(T_m)
        f = CORRELATIONS_F[self.correlation_f](Re, self)
        s2 = self.sigma ** 2
        dp = G * G / (2.0 * r_in) * (
            (self.Kc + 1.0 - s2)
            + 2.0 * (r_in / r_out - 1.0)
            + f * 4.0 * self.profondeur / self.D_h * r_in / r_m
            - (1.0 - s2 - self.Ke) * r_in / r_out)
        return dp, Re, f


@dataclass
class EchangeurGyroide:
    """Échangeur gyroïde deux fluides : Δp et UA tirés de la même géométrie.

    Côté air : corrélations f et j de Qureshi (Leeds, 2026) sur Dh et la
    porosité du réseau air. Côté propane : coefficient h imposé (donnée
    d'entrée, aucune corrélation diphasique gyroïde connue). Paroi :
    conduction plane sur l'épaisseur moyenne calculée.
    """
    largeur: float           # m
    hauteur: float           # m
    profondeur: float        # m, sens de l'air
    geo: GeometrieGyroide
    Kc: float
    Ke: float
    h_propane: float         # W/m²/K
    k_paroi: float           # W/m/K
    correlation_f: str = "leeds_gyroide"

    @property
    def A_frontale(self):
        return self.largeur * self.hauteur

    @property
    def V_coeur(self):
        return self.A_frontale * self.profondeur

    @property
    def sigma(self):
        return self.geo.phi_air

    @property
    def D_h(self):
        return self.geo.Dh_air

    @property
    def volume_propane_L(self):
        return self.geo.phi_propane * self.V_coeur * 1e3

    def _G_Re(self, Q, T_in, T_m):
        m = Q * rho_air_sec(T_in)
        G = m / (self.sigma * self.A_frontale)
        return G, G * self.D_h / mu_air(T_m)

    def dp(self, Q: float, T_in: float, T_out: float):
        r_in, r_out = rho_air_sec(T_in), rho_air_sec(T_out)
        r_m = 2.0 / (1.0 / r_in + 1.0 / r_out)
        G, Re = self._G_Re(Q, T_in, 0.5 * (T_in + T_out))
        f = _leeds_gyroide(Re, self)
        s2 = self.sigma ** 2
        dp = G * G / (2.0 * r_in) * (
            (self.Kc + 1.0 - s2) + 2.0 * (r_in / r_out - 1.0)
            + f * 4.0 * self.profondeur / self.D_h * r_in / r_m
            - (1.0 - s2 - self.Ke) * r_in / r_out)
        return dp, Re, f

    def UA(self, debit_m3h: float, T_in: float):
        """(UA W/K, détail, alertes) au débit d'air donné."""
        Q = debit_m3h / 3600.0
        G, Re = self._G_Re(Q, T_in, T_in)
        Pr = CP_AIR * mu_air(T_in) / k_air(T_in)
        j = j_leeds_gyroide(Re)
        h_air = j * G * CP_AIR * Pr ** (-2.0 / 3.0)
        A_air = self.geo.beta_air * self.V_coeur
        A_ref = self.geo.beta_propane * self.V_coeur
        e = self.geo.epaisseur_paroi
        R_air = 1.0 / (h_air * A_air)
        R_paroi = e / (self.k_paroi * 0.5 * (A_air + A_ref))
        R_ref = 1.0 / (self.h_propane * A_ref)
        UA = 1.0 / (R_air + R_paroi + R_ref)
        alertes = alertes_domaine_leeds(Re) + self._alertes_geometrie()
        return UA, dict(Re=Re, j=j, h_air=h_air, A_air=A_air, A_propane=A_ref,
                        part_R_air=R_air * UA, part_R_paroi=R_paroi * UA,
                        part_R_propane=R_ref * UA), alertes

    def _alertes_geometrie(self):
        a = []
        L_mm = self.geo.L * 1e3
        if not 5.0 <= L_mm <= 40.0:
            a.append(f"L = {L_mm:.1f} mm hors domaine Leeds (5-40 mm)")
        if not 0.0 <= self.geo.n_air <= 0.6:
            a.append(f"niveau air {self.geo.n_air:+.2f} hors domaine Leeds (0 à 0,6) : extrapolation")
        return a


# --------------------------------------------------------------------------
# Ventilateur réel
# --------------------------------------------------------------------------
@dataclass
class CourbeVitesse:
    n: float                 # tr/min
    q: list                  # m³/h, décroissant avec la pression
    dp: list                 # Pa, pression statique libre
    P: list                  # W électriques

    def dp_de_q(self, q):
        """Pression statique à q (interpolation linéaire, None hors courbe)."""
        pts = sorted(zip(self.q, self.dp, self.P))
        if q < pts[0][0] or q > pts[-1][0]:
            return None
        for (q1, d1, p1), (q2, d2, p2) in zip(pts, pts[1:]):
            if q1 <= q <= q2:
                x = (q - q1) / (q2 - q1) if q2 > q1 else 0.0
                return d1 + x * (d2 - d1), p1 + x * (p2 - p1)
        return None


@dataclass
class Ventilateur:
    nom: str
    courbes: list                     # CourbeVitesse, plusieurs vitesses
    n_max: float
    n_min: float
    source: str = ""

    def point(self, q: float, dp: float):
        """(n, P électrique, alertes) pour délivrer q (m³/h) sous dp (Pa)."""
        alertes, estim = [], []
        for c in self.courbes:
            # vitesse n telle que dp = (n/n0)² dp0(q n0/n)
            def ecart(n):
                r = n / c.n
                v = c.dp_de_q(q / r)
                return None if v is None else r * r * v[0] - dp

            lo, hi = 0.2 * c.n, 3.0 * c.n
            ns = [lo + (hi - lo) * i / 200 for i in range(201)]
            vals = [(n, ecart(n)) for n in ns]
            racine = None
            for (n1, e1), (n2, e2) in zip(vals, vals[1:]):
                if e1 is not None and e2 is not None and e1 * e2 <= 0:
                    racine = brentq(lambda n: ecart(n), n1, n2) if e1 != e2 else n1
                    break
            if racine is None:
                continue
            r = racine / c.n
            P = r ** 3 * c.dp_de_q(q / r)[1]
            estim.append((c.n, racine, P))
        if not estim:
            return float("nan"), float("nan"), [
                f"{self.nom} : point ({q:.0f} m³/h, {dp:.0f} Pa) hors des courbes constructeur, "
                "ventilateur inadapté à ce circuit (pression insuffisante ou zone de décrochage)"]
        # vitesse : estimation issue de la courbe mesurée la plus proche
        n = min(estim, key=lambda e: abs(e[1] - e[0]) / e[0])[1]
        # puissance : interpolation entre courbes mesurées selon la vitesse
        estim.sort()
        if n <= estim[0][0]:
            P = estim[0][2]
        elif n >= estim[-1][0]:
            P = estim[-1][2]
        else:
            for (na, _, Pa), (nb, _, Pb) in zip(estim, estim[1:]):
                if na <= n <= nb:
                    P = Pa + (Pb - Pa) * (n - na) / (nb - na)
                    break
        if n > self.n_max * 1.001:
            alertes.append(f"{self.nom} : vitesse requise {n:.0f} tr/min > max {self.n_max:.0f}")
        if n < self.n_min * 0.999:
            alertes.append(f"{self.nom} : vitesse requise {n:.0f} tr/min < min {self.n_min:.0f}")
        return n, P, alertes


@dataclass
class VentilateurRendementConstant:
    """HYPOTHÈSE de pré-dimensionnement, pas un ventilateur réel :
    P électrique = débit × Δp / η, η constant. Sert à explorer les géométries
    avant d'avoir choisi un ventilateur ; à remplacer par une courbe réelle."""
    nom: str
    eta: float

    def point(self, q: float, dp: float):
        return float("nan"), q / 3600.0 * dp / self.eta, []


# --------------------------------------------------------------------------
# Circuit d'air complet
# --------------------------------------------------------------------------
@dataclass
class CircuitAir:
    echangeur: GeometrieEchangeur
    ventilateur: Ventilateur
    nombre_ventilateurs: int = 1
    accessoires: list = field(default_factory=list)  # [{"nom", "K", "A"}]

    def dp(self, Q: float, T_in: float, T_out: float):
        dp_ech, Re, f = self.echangeur.dp(Q, T_in, T_out)
        r = rho_air_sec(T_in)
        dp_acc = sum(a["K"] * r * (Q / a["A"]) ** 2 / 2.0 for a in self.accessoires)
        return dp_ech + dp_acc, dict(dp_echangeur=dp_ech, dp_accessoires=dp_acc, Re=Re, f=f)

    @property
    def couple_UA(self) -> bool:
        return hasattr(self.echangeur, "UA")

    def UA(self, debit_m3h: float, T_in: float):
        return self.echangeur.UA(debit_m3h, T_in)

    def puissance(self, debit_m3h: float, T_in: float, T_out: float):
        Q = debit_m3h / 3600.0
        dp, det = self.dp(Q, T_in, T_out)
        q_un = debit_m3h / self.nombre_ventilateurs
        n, P_un, alertes = self.ventilateur.point(q_un, dp)
        det.update(dp_total=dp, n=n)
        return P_un * self.nombre_ventilateurs, det, alertes


def _ventilateur(d):
    if d.get("type") == "rendement_constant":
        return VentilateurRendementConstant(d.get("nom", f"η constant {d['eta']:.2f}"), float(d["eta"]))
    courbes = [CourbeVitesse(float(c["n_tr_min"]), list(map(float, c["q_m3h"])),
                             list(map(float, c["dp_Pa"])), list(map(float, c["P_W"])))
               for c in d["courbes"]]
    return Ventilateur(d["nom"], courbes, float(d["n_max_tr_min"]), float(d["n_min_tr_min"]),
                       d.get("source", ""))


def _geometrie_simple(e) -> GeometrieEchangeur:
    geo = GeometrieEchangeur(
        A_frontale=e["A_frontale_m2"], profondeur=e["profondeur_m"], sigma=e["sigma"],
        D_h=e["D_h_m"], Kc=e["Kc"], Ke=e["Ke"], correlation_f=e["correlation_f"],
        L_cellule=e.get("L_cellule_m"), R_offset=e.get("R_offset_m"))
    if geo.correlation_f not in CORRELATIONS_F:
        raise ValueError(f"corrélation inconnue : {geo.correlation_f}")
    return geo


def _circuit(d, dossier: str) -> CircuitAir:
    e = d["echangeur"]
    if e.get("type") == "gyroide":
        geo = EchangeurGyroide(
            largeur=e["largeur_m"], hauteur=e["hauteur_m"], profondeur=e["profondeur_m"],
            geo=GeometrieGyroide(e["L_cellule_m"], e["niveau_air"], e["niveau_propane"]),
            Kc=e["Kc"], Ke=e["Ke"], h_propane=e["h_propane_W_m2K"], k_paroi=e["k_paroi_W_mK"])
    else:
        geo = _geometrie_simple(e)
    if "ventilateur_fichier" in d:
        with open(os.path.join(dossier, d["ventilateur_fichier"]), encoding="utf-8") as f:
            v = json.load(f)
    else:
        v = d["ventilateur"]
    return CircuitAir(geo, _ventilateur(v),
                      int(d.get("nombre_ventilateurs", 1)), d.get("accessoires", []))


def charger_aeraulique(chemin: str) -> dict:
    """{'int': CircuitAir, 'ext': CircuitAir} depuis un JSON."""
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)
    dossier = os.path.dirname(os.path.abspath(chemin))
    return {"int": _circuit(d["interieur"], dossier), "ext": _circuit(d["exterieur"], dossier),
            "nom": d.get("nom", chemin), "exemple": bool(d.get("exemple", False))}
