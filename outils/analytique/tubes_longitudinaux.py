#!/usr/bin/env python3
"""
Estimation sans CFD : tubes ronds parallèles au flux d'air (écoulement longitudinal).

L'air glisse le long des tubes, rangés en réseau triangulaire de pas P dans le plan de la face.
Mêmes règles d'équité que la CFD 2D : même tube (Dh intérieur 4 mm, paroi 1 mm, Ø ext 6 mm) et
même charge de propane par m² de face que la batterie de référence (4 rangs, Pt = 12 mm), donc
la même longueur de tube par m² de face : la profondeur L découle du pas P.

Modèle :
  * cellule hexagonale autour d'un tube remplacée par un anneau de même section (rayon r_o),
    paroi du tube à r_i (non-glissement, température imposée), bord extérieur r_o en symétrie
    (glissement, adiabatique). Approximation classique, bonne pour P / D ≥ 1,5 (Sparrow et al.).
  * écoulement laminaire en développement simultané (vitesse et température uniformes à l'entrée) :
    équations de couche limite (parabolisées) résolues en marchant selon x, pression uniforme
    dans la section, débit conservé (méthode de Patankar et Spalding).
  * pertes d'entrée et de sortie aux bouts des tubes (plaque perforée de taux de vide σ) :
    contraction Kc = 0,5 (1 - σ), élargissement brusque Ke = (1 - σ)² (Borda-Carnot), bouts plats.
  * collecteurs ignorés (volume de propane et obstacle à l'air) : estimation optimiste.

Vérification : le même solveur en canal plan retrouve f·Re = 24 et Nu = 7,54 en régime établi.

    python outils/analytique/tubes_longitudinaux.py      → docs/formes/longitudinal/
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "formes" / "longitudinal"

AIR = dict(nu=1.516e-5, rho=1.204, cp=1006.0, Pr=0.71)
D_EXT = 6e-3                        # m, tube rond de référence
PT_REF, RANGS_REF = 12e-3, 4        # batterie de référence (CFD 2D)
LONGUEUR_PAR_FACE = RANGS_REF / PT_REF     # m de tube par m² de face (= 333 m/m²)
DT_REF = 10.0


def thomas(a, b, c, d):
    """Système tridiagonal a[i] x[i-1] + b[i] x[i] + c[i] x[i+1] = d[i]."""
    n = len(d)
    cp, dp = np.empty(n), np.empty(n)
    cp[0], dp[0] = c[0] / b[0], d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x = np.empty(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def marcher(r_i, r_o, L, V, plan=False, n=161, nx=1500):
    """Écoulement en développement simultané entre une paroi (r_i : u = 0, θ = 1) et une
    symétrie (r_o : glissement, adiabatique), vitesse V et θ = 0 uniformes à l'entrée.
    plan=True : canal plan (y de r_i à r_o, métrique 1) ; sinon anneau (métrique r).
    Volumes finis, implicite en r, marche en x (coefficients de convection retardés d'un pas).
    Renvoie (Δp en Pa, θ de mélange en sortie = efficacité, profils)."""
    nu, alpha = AIR["nu"], AIR["nu"] / AIR["Pr"]
    s = np.linspace(0, 1, n)
    r = r_i + (r_o - r_i) * (1 - np.cos(0.5 * math.pi * s))     # resserré contre la paroi
    rf = np.r_[r[0], 0.5 * (r[1:] + r[:-1]), r[-1]]              # faces des volumes de contrôle
    if plan:
        w, gf, g = np.diff(rf), np.ones(n + 1), np.ones(n)
    else:
        w, gf, g = 0.5 * np.diff(rf ** 2), rf, r
    debit = V * w.sum()
    dW = np.zeros(n); dW[1:] = gf[1:n] / np.diff(r)              # conductance face ouest (i-1 | i)
    dE = np.zeros(n); dE[:-1] = dW[1:]                            # face est ; 0 à la symétrie
    xs = np.unique(np.r_[0.0, np.geomspace(L * 1e-7, L, nx), np.linspace(0.0, L, 2 * nx)])
    u = np.full(n, V); u[0] = 0.0
    T = np.zeros(n)
    dudx = np.zeros(n)
    p = 0.0
    for k in range(1, len(xs)):
        dx = xs[k] - xs[k - 1]
        # vitesse transversale par continuité : g v = -∫ g ∂u/∂x dr depuis la paroi
        gv = -np.r_[0.0, np.cumsum(0.5 * (dudx[1:] * g[1:] + dudx[:-1] * g[:-1]) * np.diff(r))]
        v = gv / g
        # convection transversale amont : v (φ_i - φ_voisin) / Δr, ramenée au volume w
        dr_w = np.r_[1.0, np.diff(r)]; dr_e = np.r_[np.diff(r), 1.0]
        cw = np.where(v > 0, v / dr_w, 0.0) * w
        ce = np.where(v < 0, -v / dr_e, 0.0) * w
        cw[0] = ce[-1] = 0.0
        ap0 = np.maximum(u, 1e-9 * V) * w / dx

        def resoudre(phi_o, diff, source, val_paroi):
            a = -(diff * dW + cw)
            c = -(diff * dE + ce)
            b = ap0 + diff * (dW + dE) + cw + ce
            d = ap0 * phi_o + source * w
            a[0], b[0], c[0], d[0] = 0.0, 1.0, 0.0, val_paroi
            return thomas(a, b, c, d)

        A = resoudre(u, nu, 0.0, 0.0)
        B = resoudre(np.zeros(n), nu, 1.0, 0.0)
        G = (debit - (A * w).sum()) / (B * w).sum()                # -dp/dx / ρ
        u_new = A + G * B
        T = resoudre(T, alpha, 0.0, 1.0)
        dudx = (u_new - u) / dx
        u = u_new
        p += AIR["rho"] * G * dx
    theta_b = (u * T * w).sum() / (u * w).sum()
    return p, theta_b, (r, u, T)


def geometrie(P):
    """Cellule hexagonale de pas P autour d'un tube → anneau équivalent ; profondeur à charge égale."""
    A_cell = P * P * math.sqrt(3) / 2
    r_i = D_EXT / 2
    r_o = math.sqrt(A_cell / math.pi)
    sigma = 1 - math.pi * r_i ** 2 / A_cell
    L = LONGUEUR_PAR_FACE * A_cell
    Dh = 4 * (A_cell - math.pi * r_i ** 2) / (math.pi * D_EXT)
    return dict(P=P, A_cell=A_cell, r_i=r_i, r_o=r_o, sigma=sigma, L=L, Dh=Dh)


def cas(P, U=1.0, L=None):
    g = geometrie(P)
    if L is not None:
        g["L"] = L
    Vc = U / g["sigma"]
    dp_canal, eps, _ = marcher(g["r_i"], g["r_o"], g["L"], Vc)
    q = 0.5 * AIR["rho"] * Vc ** 2
    Kc, Ke = 0.5 * (1 - g["sigma"]), (1 - g["sigma"]) ** 2
    dp_bouts = q * ((Kc + 1 - g["sigma"] ** 2) - (1 - g["sigma"] ** 2 - Ke))
    dp = dp_canal + dp_bouts
    rcpU = AIR["rho"] * AIR["cp"] * U
    NTU = -math.log(1 - eps)
    A_air = math.pi * D_EXT * g["L"] / g["A_cell"]                  # m² d'air par m² de face
    return dict(P_mm=1e3 * P, P_sur_D=P / D_EXT, U=U, profondeur_mm=1e3 * g["L"], Dh_air_mm=1e3 * g["Dh"],
                sigma=g["sigma"], Re_Dh=Vc * g["Dh"] / AIR["nu"],
                x_etoile=g["L"] / (g["Dh"] * Vc * g["Dh"] / AIR["nu"] * AIR["Pr"]),
                dp_Pa=dp, dp_bouts_Pa=dp_bouts, T_sortie=eps, NTU=NTU, h=NTU * rcpU / A_air,
                P_vent_sur_Q=dp / (AIR["rho"] * AIR["cp"] * eps * DT_REF),
                Q_face_kW_m2=rcpU * eps * DT_REF / 1e3)


def verification():
    """Canal plan de demi-hauteur b, très long : f·Re → 24, Nu → 7,54 (Dh = 4 b)."""
    b, V = 1e-3, 0.2
    Dh = 4 * b
    Re = V * Dh / AIR["nu"]
    L1, L2 = 0.1 * Re * Dh, 0.2 * Re * Dh               # au-delà des longueurs d'établissement
    p1, t1, _ = marcher(0.0, b, L1, V, plan=True)
    p2, t2, _ = marcher(0.0, b, L2, V, plan=True)
    dpdx = (p2 - p1) / (L2 - L1)
    fRe = dpdx * Dh / (0.5 * AIR["rho"] * V ** 2) / 4 * Re        # Fanning
    # Nu établi : dθb/dx = 4 h (1 - θb) / (ρ cp V Dh)  → h depuis la pente de ln(1 - θb)
    k_air = AIR["nu"] / AIR["Pr"] * AIR["rho"] * AIR["cp"]
    m = (math.log(1 - t1) - math.log(1 - t2)) / (L2 - L1)
    h = m * AIR["rho"] * AIR["cp"] * V * b                      # par paroi, demi-canal
    return dict(fRe=fRe, Nu=h * Dh / k_air)


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    ver = verification()
    print(f"vérification canal plan : f·Re = {ver['fRe']:.2f} (24), Nu = {ver['Nu']:.3f} (7,541)")
    pas = [7.5e-3, 8e-3, 9e-3, 10e-3, 12e-3, 14e-3, 16e-3, 20e-3]
    res = [cas(P) for P in pas]
    vit = [cas(12e-3, U) for U in (0.5, 2.0, 3.0)] + [cas(9e-3, U) for U in (0.5, 2.0, 3.0)]
    for r in res + vit:
        print(f"P = {r['P_mm']:4.1f} mm  U = {r['U']:3.1f}  L = {r['profondeur_mm']:5.1f} mm  Re = {r['Re_Dh']:5.0f}  "
              f"Δp = {r['dp_Pa']:5.2f} Pa  h = {r['h']:5.1f}  ε = {100 * r['T_sortie']:4.1f} %  "
              f"P/Q = {1e3 * r['P_vent_sur_Q']:.3f} ‰")
    (SORTIE / "resultat.json").write_text(json.dumps(dict(
        modele="anneau équivalent, laminaire, développement simultané, pertes aux bouts, sans collecteurs",
        verification=ver, charge_egale=res, vitesses=vit), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
