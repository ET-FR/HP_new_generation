"""
Balayage de géométries gyroïdes côté air : UA et perte de charge.

Pour chaque combinaison (face carrée, profondeur, période L, niveau air),
calcule UA (facteur j) et Δp (facteur f) avec les corrélations de Qureshi
(Leeds, 2026), puis liste les plus petits volumes qui respectent une cible
d'UA et un budget de perte de charge.

    python conception_echangeur/outils/balayage_gyroide.py --debit 520 --UA 416 --dp-max 40
    python conception_echangeur/outils/balayage_gyroide.py --debit 1300 --UA 672 --dp-max 40 --face-max 0.2

HYPOTHÈSES (à remplacer par des données réelles) : h propane, conductivité de
paroi, épaisseur de paroi, Kc / Ke. Les niveaux d'air négatifs (réseau air
plus grand que la moitié du volume) sont hors du domaine de la thèse.
"""

from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # dépôt

from pac_fenetre.aeraulique import EchangeurGyroide  # noqa: E402
from pac_fenetre.gyroide import GeometrieGyroide, proprietes_reduites  # noqa: E402


def niveau_propane(n_air: float, L: float, paroi: float) -> float:
    """Niveau côté propane donnant l'épaisseur de paroi visée (approx. |∇F|)."""
    G = proprietes_reduites(round(n_air, 6))[2]
    return n_air - paroi * 2.0 * math.pi * G / L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debit", type=float, required=True, help="m³/h")
    ap.add_argument("--UA", type=float, required=True, help="W/K visé")
    ap.add_argument("--dp-max", type=float, required=True, help="Pa, échangeur seul")
    ap.add_argument("--T", type=float, default=20.0, help="°C entrée d'air")
    ap.add_argument("--face-max", type=float, default=0.8, help="m, côté max de la face")
    ap.add_argument("--paroi", type=float, default=0.4e-3, help="m (HYPOTHÈSE)")
    ap.add_argument("--h-propane", type=float, default=2000.0, help="W/m²/K (HYPOTHÈSE)")
    ap.add_argument("--k-paroi", type=float, default=120.0, help="W/m/K (HYPOTHÈSE)")
    ap.add_argument("--Kc", type=float, default=0.5, help="(HYPOTHÈSE)")
    ap.add_argument("--Ke", type=float, default=0.15, help="(HYPOTHÈSE)")
    ap.add_argument("-n", type=int, default=10)
    a = ap.parse_args()

    faces = [x for x in (0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8) if x <= a.face_max + 1e-9]
    lignes = []
    for cote in faces:
        for L in (0.005, 0.006, 0.008, 0.010, 0.015, 0.020):
            for n_air in (-0.6, -0.3, 0.0, 0.3, 0.6):
                n_p = niveau_propane(n_air, L, a.paroi)
                if n_p <= -1.4:
                    continue
                g = GeometrieGyroide(L, n_air, n_p)
                for prof in (0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.08, 0.12, 0.2):
                    e = EchangeurGyroide(cote, cote, prof, g, a.Kc, a.Ke, a.h_propane, a.k_paroi)
                    UA, det, al = e.UA(a.debit, a.T)
                    dp = e.dp(a.debit / 3600.0, a.T, a.T + 10.0)[0]
                    lignes.append((cote * cote * prof * 1e3, cote, L, n_air, prof, UA, dp,
                                   det["Re"], e.volume_propane_L, g.epaisseur_paroi, bool(al)))
    ok = sorted(l for l in lignes if l[5] >= a.UA and l[6] <= a.dp_max)
    print(f"{len(ok)} géométries sur {len(lignes)} respectent UA ≥ {a.UA:.0f} W/K et Δp ≤ {a.dp_max:.0f} Pa")
    print("V cœur [L] | face [m] | L [mm] | niveau air | prof [mm] | UA [W/K] | Δp [Pa] | Re | propane [L] | hors domaine")
    for l in ok[: a.n]:
        print(f"{l[0]:7.1f} | {l[1]:.2f} | {l[2]*1e3:4.0f} | {l[3]:+.1f} | {l[4]*1e3:5.0f} | "
              f"{l[5]:6.0f} | {l[6]:5.1f} | {l[7]:5.0f} | {l[8]:.2f} | {'oui' if l[10] else 'non'}")
    if not ok:
        meilleur = max((l for l in lignes if l[6] <= a.dp_max), key=lambda l: l[5], default=None)
        if meilleur:
            print(f"Meilleur UA sous {a.dp_max:.0f} Pa : {meilleur[5]:.0f} W/K "
                  f"(face {meilleur[1]:.2f} m, L {meilleur[2]*1e3:.0f} mm, prof {meilleur[4]*1e3:.0f} mm)")


if __name__ == "__main__":
    main()
