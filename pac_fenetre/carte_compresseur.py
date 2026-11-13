"""
Carte compresseur constructeur (polynômes 10 coefficients EN 12900 / AHRI 540).

    X = C1 + C2·S + C3·D + C4·S² + C5·S·D + C6·D² + C7·S³ + C8·S²·D + C9·S·D² + C10·D³

S : température de rosée à l'aspiration du compresseur, D : température de
rosée au refoulement. Une carte donne au minimum le débit massique et la
puissance électrique absorbée, pour une ou plusieurs vitesses (compresseur
inverter) ; entre deux vitesses, interpolation linéaire.

Les valeurs de la carte sont valables aux conditions de référence du
constructeur (surchauffe ou température de gaz aspiré, sous-refroidissement).
La correction vers les conditions réelles du cycle est faite dans
`PompeAChaleur.compresseur` (densité d'aspiration et travail isentropique).

Format JSON : voir `compresseurs/MODELE_carte.json`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

# Conversions vers SI (°C, kg/s, W)
_T = {"C": lambda t: t, "F": lambda t: (t - 32.0) * 5.0 / 9.0}
_T_INV = {"C": lambda t: t, "F": lambda t: t * 9.0 / 5.0 + 32.0}
_M = {"kg/s": 1.0, "kg/h": 1.0 / 3600.0, "g/s": 1e-3, "lb/h": 0.45359237 / 3600.0}
_P = {"W": 1.0, "kW": 1000.0}


def polynome10(c, S: float, D: float) -> float:
    return (c[0] + c[1] * S + c[2] * D + c[3] * S * S + c[4] * S * D + c[5] * D * D
            + c[6] * S ** 3 + c[7] * S * S * D + c[8] * S * D * D + c[9] * D ** 3)


def _dans_polygone(x: float, y: float, poly) -> bool:
    """Ray casting. poly : [[x, y], ...] (Te, Tc) en °C, fermé implicitement."""
    dedans = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xc:
                dedans = not dedans
    return dedans


@dataclass
class CarteCompresseur:
    nom: str
    vitesses: list                      # tr/s, triées
    coef_m: dict                        # vitesse -> 10 coefficients (débit)
    coef_P: dict                        # vitesse -> 10 coefficients (puissance)
    surchauffe_ref: float | None = None  # K, si la carte est à surchauffe fixe
    T_aspiration_ref: float | None = None  # °C, si la carte est à gaz aspiré fixe
    sous_refroid_ref: float = 0.0       # K (n'affecte pas ṁ ni P, documenté)
    puissance_inclut_variateur: bool = False
    cylindree_cm3: float | None = None
    enveloppe: list = field(default_factory=list)  # [[Te, Tc], ...] °C
    unite_T: str = "C"
    unite_m: str = "kg/h"
    unite_P: str = "W"
    source: str = ""
    synthetique: bool = False

    # ------------------------------------------------------------------
    @classmethod
    def depuis_json(cls, chemin: str) -> "CarteCompresseur":
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        ref = d.get("reference", {})
        u = d.get("unites", {})
        coefs = d["coefficients"]
        vit = sorted(float(v) for v in coefs["debit_massique"])
        cm = {float(v): list(map(float, c)) for v, c in coefs["debit_massique"].items()}
        cp = {float(v): list(map(float, c)) for v, c in coefs["puissance_electrique"].items()}
        for v in vit:
            if len(cm[v]) != 10 or v not in cp or len(cp[v]) != 10:
                raise ValueError(f"{chemin} : 10 coefficients requis pour chaque vitesse ({v} tr/s)")
        if ref.get("surchauffe_K") is None and ref.get("T_aspiration_C") is None:
            raise ValueError(f"{chemin} : donner reference.surchauffe_K ou reference.T_aspiration_C")
        return cls(
            nom=d.get("nom", os.path.basename(chemin)),
            vitesses=vit, coef_m=cm, coef_P=cp,
            surchauffe_ref=ref.get("surchauffe_K"),
            T_aspiration_ref=ref.get("T_aspiration_C"),
            sous_refroid_ref=ref.get("sous_refroidissement_K", 0.0) or 0.0,
            puissance_inclut_variateur=bool(d.get("puissance_inclut_variateur", False)),
            cylindree_cm3=d.get("cylindree_cm3"),
            enveloppe=d.get("enveloppe_Te_Tc_C", []),
            unite_T=u.get("temperature", "C"),
            unite_m=u.get("debit_massique", "kg/h"),
            unite_P=u.get("puissance", "W"),
            source=d.get("source", ""),
            synthetique=bool(d.get("synthetique", False)),
        )

    # ------------------------------------------------------------------
    @property
    def v_min(self) -> float:
        return self.vitesses[0]

    @property
    def v_max(self) -> float:
        return self.vitesses[-1]

    def T_aspiration_reference(self, S: float) -> float:
        """Température du gaz aspiré aux conditions de la carte (°C)."""
        if self.T_aspiration_ref is not None:
            return self.T_aspiration_ref
        return S + self.surchauffe_ref

    def _eval(self, coefs: dict, S: float, D: float, f: float) -> float:
        Su, Du = _T_INV[self.unite_T](S), _T_INV[self.unite_T](D)
        v = self.vitesses
        if len(v) == 1 or f <= v[0]:
            # une seule vitesse : proportionnalité à la vitesse (hypothèse)
            # sous la plus basse : extrapolation proportionnelle également
            return polynome10(coefs[v[0]], Su, Du) * f / v[0]
        if f >= v[-1]:
            return polynome10(coefs[v[-1]], Su, Du) * f / v[-1]
        for a, b in zip(v, v[1:]):
            if a <= f <= b:
                xa, xb = polynome10(coefs[a], Su, Du), polynome10(coefs[b], Su, Du)
                return xa + (xb - xa) * (f - a) / (b - a)
        raise RuntimeError("interpolation")  # pragma: no cover

    def evaluer(self, S: float, D: float, f: float):
        """(ṁ kg/s, P électrique W, alertes) aux conditions de la carte."""
        m = self._eval(self.coef_m, S, D, f) * _M[self.unite_m]
        P = self._eval(self.coef_P, S, D, f) * _P[self.unite_P]
        alertes = []
        if f < self.v_min - 1e-6 or f > self.v_max + 1e-6:
            alertes.append(f"Vitesse {f:.0f} tr/s hors carte ({self.v_min:.0f}-{self.v_max:.0f})")
        if self.enveloppe and not _dans_polygone(S, D, self.enveloppe):
            alertes.append("Point (Te, Tc) hors enveloppe constructeur")
        return m, P, alertes
