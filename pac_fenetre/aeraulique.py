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

R_AIR = 287.05


def rho_air_sec(T: float) -> float:
    return 101325.0 / (R_AIR * (T + 273.15))


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


def _leeds_gyroide(Re: float, geo) -> float:
    """Corrélation Qureshi (Leeds, 2026), f(Re, L, R).
    Domaine : 5 < L < 40 mm, 0 < R < 0,6 mm, 20 < Re < 8000.
    À compléter avec la forme et les coefficients publiés dans la thèse."""
    raise NotImplementedError(
        "Corrélation de Leeds non saisie : renseigner sa forme et ses coefficients "
        "dans pac_fenetre/aeraulique.py (_leeds_gyroide)")


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

    def puissance(self, debit_m3h: float, T_in: float, T_out: float):
        Q = debit_m3h / 3600.0
        dp, det = self.dp(Q, T_in, T_out)
        q_un = debit_m3h / self.nombre_ventilateurs
        n, P_un, alertes = self.ventilateur.point(q_un, dp)
        det.update(dp_total=dp, n=n)
        if not 20.0 <= det["Re"] <= 8000.0 and self.echangeur.correlation_f == "leeds_gyroide":
            alertes.append(f"Re = {det['Re']:.0f} hors domaine de la corrélation de Leeds")
        return P_un * self.nombre_ventilateurs, det, alertes


def _ventilateur(d) -> Ventilateur:
    courbes = [CourbeVitesse(float(c["n_tr_min"]), list(map(float, c["q_m3h"])),
                             list(map(float, c["dp_Pa"])), list(map(float, c["P_W"])))
               for c in d["courbes"]]
    return Ventilateur(d["nom"], courbes, float(d["n_max_tr_min"]), float(d["n_min_tr_min"]),
                       d.get("source", ""))


def _circuit(d, dossier: str) -> CircuitAir:
    e = d["echangeur"]
    geo = GeometrieEchangeur(
        A_frontale=e["A_frontale_m2"], profondeur=e["profondeur_m"], sigma=e["sigma"],
        D_h=e["D_h_m"], Kc=e["Kc"], Ke=e["Ke"], correlation_f=e["correlation_f"],
        L_cellule=e.get("L_cellule_m"), R_offset=e.get("R_offset_m"))
    if geo.correlation_f not in CORRELATIONS_F:
        raise ValueError(f"corrélation inconnue : {geo.correlation_f}")
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
