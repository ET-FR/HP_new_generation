"""
Géométrie d'un échangeur gyroïde à deux fluides.

Fonction gyroïde, coordonnées réduites X = 2πx/L :
    F = sin X cos Y + sin Y cos Z + sin Z cos X      (F ∈ [-1,5 ; 1,5] environ)

Partition du volume (niveaux sans dimension, n_propane <= n_air) :
    air      : F > n_air
    paroi    : n_propane < F < n_air
    propane  : F < n_propane

Le « paramètre d'offset R » de la thèse de Leeds est un tel niveau sans
dimension (noté en mm dans la thèse, à tort). Leur sheet-gyroïde « R = ±0,3 »
correspond ici à n_air = +0,3, n_propane = -0,3.

Toutes les grandeurs sont calculées numériquement sur une cellule (grille
régulière, périodique) puis mises à l'échelle par L :
    fraction de volume φ, surface spécifique β = A / V_total (m²/m³),
    diamètre hydraulique Dh = 4 φ / β, épaisseur moyenne de paroi.
La surface est obtenue par A = ∫ |∇F| δ(F - n) dV (noyau gaussien étroit).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

N_GRILLE = 128


@lru_cache(maxsize=4)
def _champ(N: int = N_GRILLE):
    s = (np.arange(N) + 0.5) * 2.0 * np.pi / N
    X, Y, Z = np.meshgrid(s, s, s, indexing="ij")
    sx, cx, sy, cy, sz, cz = np.sin(X), np.cos(X), np.sin(Y), np.cos(Y), np.sin(Z), np.cos(Z)
    F = sx * cy + sy * cz + sz * cx
    gx = cx * cy - sz * sx
    gy = -sx * sy + cy * cz
    gz = -sy * sz + cz * cx
    G = np.sqrt(gx * gx + gy * gy + gz * gz)   # |∇F| en coordonnées réduites
    return F, G


@lru_cache(maxsize=256)
def proprietes_reduites(n: float, N: int = N_GRILLE):
    """Pour l'isosurface F = n, sur une cellule de côté 2π (coordonnées réduites) :
    (fraction de volume F > n, surface / (2π)², |∇F| moyen sur la surface)."""
    F, G = _champ(N)
    frac = float(np.mean(F > n))
    h = 2.0 * np.pi / N
    eps = 1.5 * h * float(np.mean(G))           # largeur du noyau ~ 1,5 maille
    k = np.exp(-0.5 * ((F - n) / eps) ** 2) / (eps * math.sqrt(2.0 * math.pi))
    w = k * G
    aire_red = float(np.sum(w)) * h ** 3        # surface en coordonnées réduites
    G_moy = float(np.sum(w * G) / np.sum(w))
    return frac, aire_red / (2.0 * np.pi) ** 2, G_moy


@dataclass(frozen=True)
class GeometrieGyroide:
    L: float          # m, période de la cellule
    n_air: float      # niveau sans dimension, frontière côté air
    n_propane: float  # niveau sans dimension, frontière côté propane

    def __post_init__(self):
        if not self.n_propane <= self.n_air:
            raise ValueError("il faut n_propane <= n_air (la paroi est entre les deux)")
        if not (-1.4 < self.n_propane and self.n_air < 1.4):
            raise ValueError("niveaux hors de l'intervalle utile de la fonction gyroïde")

    # Air ---------------------------------------------------------------
    @property
    def phi_air(self) -> float:
        return proprietes_reduites(round(self.n_air, 6))[0]

    @property
    def beta_air(self) -> float:
        """Surface mouillée côté air par m³ de cœur (m²/m³)."""
        return proprietes_reduites(round(self.n_air, 6))[1] / self.L

    @property
    def Dh_air(self) -> float:
        return 4.0 * self.phi_air / self.beta_air

    # Propane -----------------------------------------------------------
    @property
    def phi_propane(self) -> float:
        return 1.0 - proprietes_reduites(round(self.n_propane, 6))[0]

    @property
    def beta_propane(self) -> float:
        return proprietes_reduites(round(self.n_propane, 6))[1] / self.L

    @property
    def Dh_propane(self) -> float:
        return 4.0 * self.phi_propane / self.beta_propane

    # Paroi -------------------------------------------------------------
    @property
    def phi_paroi(self) -> float:
        return 1.0 - self.phi_air - self.phi_propane

    @property
    def epaisseur_paroi(self) -> float:
        """Épaisseur moyenne (m) : volume de paroi / surface moyenne des deux faces."""
        return self.phi_paroi / (0.5 * (self.beta_air + self.beta_propane))

    def resume(self) -> dict:
        return dict(L_mm=self.L * 1e3, n_air=self.n_air, n_propane=self.n_propane,
                    phi_air=self.phi_air, phi_propane=self.phi_propane, phi_paroi=self.phi_paroi,
                    beta_air=self.beta_air, beta_propane=self.beta_propane,
                    Dh_air_mm=self.Dh_air * 1e3, Dh_propane_mm=self.Dh_propane * 1e3,
                    paroi_mm=self.epaisseur_paroi * 1e3)
