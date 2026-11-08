"""
Surfaces TPMS (surfaces minimales triplement périodiques) en approximation nodale.

Coordonnées réduites X = 2πx/L (une cellule = [0, 2π]³). Pour chaque surface F,
le réseau d'air est F > n_air ; tout le reste (paroi + propane, ou paroi pleine
d'un hybride) est solide pour l'air.

    Gyroïde          sin X cos Y + sin Y cos Z + sin Z cos X
    Diamond (Sch-D)  sin X sin Y sin Z + sin X cos Y cos Z + cos X sin Y cos Z + cos X cos Y sin Z
    Primitive (Sch-P) cos X + cos Y + cos Z
    I-WP             2 (cos X cos Y + cos Y cos Z + cos Z cos X) − (cos 2X + cos 2Y + cos 2Z)
    Fischer-Koch S   cos 2X sin Y cos Z + cos X cos 2Y sin Z + sin X cos Y cos 2Z

Propriétés géométriques calculées numériquement sur une cellule (grille
périodique) : porosité φ, surface spécifique réduite, d'où β = s / L (m²/m³) et
Dh = 4 φ / β. À porosité et Dh égaux, toutes les surfaces ont la même β : seules
les corrélations j et f (CFD) les distinguent.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

N_GRILLE = 128


def _gyroide(X, Y, Z):
    return np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z) + np.sin(Z) * np.cos(X)


def _diamond(X, Y, Z):
    sx, cx, sy, cy, sz, cz = np.sin(X), np.cos(X), np.sin(Y), np.cos(Y), np.sin(Z), np.cos(Z)
    return sx * sy * sz + sx * cy * cz + cx * sy * cz + cx * cy * sz


def _primitive(X, Y, Z):
    return np.cos(X) + np.cos(Y) + np.cos(Z)


def _iwp(X, Y, Z):
    cx, cy, cz = np.cos(X), np.cos(Y), np.cos(Z)
    return 2.0 * (cx * cy + cy * cz + cz * cx) - (np.cos(2 * X) + np.cos(2 * Y) + np.cos(2 * Z))


def _fks(X, Y, Z):
    return (np.cos(2 * X) * np.sin(Y) * np.cos(Z) + np.cos(X) * np.cos(2 * Y) * np.sin(Z)
            + np.sin(X) * np.cos(Y) * np.cos(2 * Z))


SURFACES = {
    "gyroide": dict(nom="Gyroïde", f=_gyroide),
    "diamond": dict(nom="Diamond (Schwarz-D)", f=_diamond),
    "primitive": dict(nom="Primitive (Schwarz-P)", f=_primitive),
    "iwp": dict(nom="I-WP", f=_iwp),
    "fks": dict(nom="Fischer-Koch S", f=_fks),
}


def champ(surface: str, X, Y, Z):
    return SURFACES[surface]["f"](X, Y, Z)


@lru_cache(maxsize=8)
def _grille(surface: str, N: int = N_GRILLE):
    h = 2.0 * np.pi / N
    s = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(s, s, s, indexing="ij")
    F = champ(surface, X, Y, Z)
    g = [(np.roll(F, -1, a) - np.roll(F, 1, a)) / (2 * h) for a in range(3)]
    G = np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)
    return F, G, h


def niveau_pour_porosite(surface: str, phi_air: float) -> float:
    """Niveau n tel que la fraction de volume F > n vaille phi_air."""
    F, _, _ = _grille(surface)
    return float(np.quantile(F, 1.0 - phi_air))


@lru_cache(maxsize=512)
def proprietes_reduites(surface: str, n: float):
    """(porosité F > n, surface de l'isosurface F = n par volume de cellule, en unités où L = 1)."""
    F, G, h = _grille(surface)
    phi = float(np.mean(F > n))
    eps = 1.5 * h * float(np.mean(G))
    k = np.exp(-0.5 * ((F - n) / eps) ** 2) / (eps * math.sqrt(2.0 * math.pi))
    aire_red = float(np.sum(k * G)) * h ** 3      # coordonnées réduites (cellule de côté 2π)
    return phi, aire_red / (2.0 * np.pi) ** 2      # surface / volume pour L = 1


def geometrie(surface: str, phi_air: float, L: float | None = None, Dh: float | None = None) -> dict:
    """Géométrie côté air pour une porosité donnée ; fixer L (m) ou Dh (m)."""
    n = round(niveau_pour_porosite(surface, phi_air), 6)
    phi, s_red = proprietes_reduites(surface, n)
    if L is None:
        if Dh is None:
            raise ValueError("donner L ou Dh")
        L = Dh * s_red / (4.0 * phi)      # Dh = 4 φ / β et β = s_red / L
    beta = s_red / L
    return dict(surface=surface, niveau=n, phi_air=phi, L=L, beta_air=beta, Dh_air=4.0 * phi / beta)
