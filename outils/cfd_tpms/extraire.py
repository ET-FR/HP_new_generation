#!/usr/bin/env python3
"""
Lit un ou plusieurs cas CFD terminés (creer_cas.py + Allrun) et calcule j et f côté air.

    NTU   = ln((T_paroi − T_entrée) / (T_paroi − T_sortie))      (paroi à 1, entrée à 0)
    j     = St · Pr^(2/3),  St = h / (G cp) = NTU · σ A_front / A_air
    f_app = Δp / (½ ρ u_c²) · Dh / (4 D)     (frottement apparent : entrée, sortie et
                                               développement compris, pour une profondeur D)

A_air comprend la surface du réseau air dans le noyau et les deux faces frontales du solide.

    python extraire.py cas/*            -> tableau, et resultats.csv dans le dossier courant
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path


def serie(dossier: Path, nom: str) -> list[float]:
    fichiers = sorted((dossier / "postProcessing" / nom).glob("*/surfaceFieldValue.dat"))
    if not fichiers:
        raise FileNotFoundError(f"{dossier}: postProcessing/{nom} absent")
    lignes = [l for l in fichiers[-1].read_text().splitlines() if l.strip() and not l.startswith("#")]
    return [float(l.split()[1]) for l in lignes]


def moyenne_finale(dossier: Path, nom: str, fraction=0.25) -> tuple[float, float]:
    """Moyenne et écart-type relatif sur la dernière fraction des itérations
    (l'écoulement oscille légèrement au-dessus de Re ≈ 150 : pas de convergence stricte)."""
    v = serie(dossier, nom)
    v = v[-max(1, int(len(v) * fraction)):]
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
    return m, (sd / abs(m) if m else 0.0)


def convergence(dossier: Path) -> dict:
    log = dossier / "log.simpleFoam"
    if not log.exists():
        return dict(termine=False, converge=False, iterations=0)
    t = log.read_text(errors="replace")
    iters = [l for l in t.splitlines() if l.startswith("Time = ")]
    return dict(termine="End" in t[-2000:], converge="SIMPLE solution converged" in t,
                iterations=int(float(iters[-1].split()[-1])) if iters else 0)


def resultat(dossier) -> dict:
    d = Path(dossier)
    m = json.loads((d / "cas.json").read_text())
    air = m["air"]
    p_in, sd_p = moyenne_finale(d, "pEntree")
    dp = (p_in - moyenne_finale(d, "pSortie")[0]) * air["rho"]
    T_out, sd_T = moyenne_finale(d, "TSortie")
    Q = -moyenne_finale(d, "debit")[0]                     # m³/s (flux entrant négatif)
    NTU = -math.log(max(1.0 - T_out, 1e-12))
    sigma = m["phi_air"]
    u_c = Q / (sigma * m["A_front"])                       # vitesse réelle dans les pores
    Re = u_c * m["Dh"] / air["nu"]
    j = NTU * sigma * m["A_front"] / m["A_air"] * air["Pr"] ** (2 / 3)
    f = dp / (0.5 * air["rho"] * u_c ** 2) * m["Dh"] / (4 * m["profondeur"])
    h = j * air["rho"] * u_c * air["cp"] * air["Pr"] ** (-2 / 3)
    return dict(cas=d.name, surface=m["surface"], phi_air=sigma, Dh_mm=m["Dh"] * 1e3, L_mm=m["L"] * 1e3,
                profondeur_mm=m["profondeur"] * 1e3, Re_consigne=m["Re"], Re=Re, turbulent=m["turbulent"],
                finesse=m["finesse"], raffinement=m["niveau_raff"], dp_Pa=dp, T_sortie=T_out, NTU=NTU,
                j=j, f=f, j_sur_f=j / f, h_air=h, fluct_dp=sd_p, fluct_T=sd_T, **convergence(d))


def main(dossiers):
    lignes = []
    for d in dossiers:
        try:
            lignes.append(resultat(d))
        except (FileNotFoundError, KeyError, ValueError, IndexError) as exc:
            print(f"ignoré {d}: {exc}", file=sys.stderr)
    if not lignes:
        return
    print(f"{'cas':28s} {'Re':>7s} {'Δp Pa':>8s} {'NTU':>6s} {'j':>8s} {'f_app':>8s} {'j/f':>6s} {'h W/m²K':>8s} conv")
    for r in lignes:
        print(f"{r['cas']:28s} {r['Re']:7.1f} {r['dp_Pa']:8.3f} {r['NTU']:6.3f} {r['j']:8.5f} {r['f']:8.5f} "
              f"{r['j_sur_f']:6.3f} {r['h_air']:8.1f} {'oui' if r['converge'] else 'stable' if max(r['fluct_dp'], r['fluct_T']) < 0.01 else 'NON'}"
              f" ({r['iterations']} it., fluct. {100 * max(r['fluct_dp'], r['fluct_T']):.2f} %)")
    with open("resultats.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print("-> resultats.csv")


if __name__ == "__main__":
    main(sys.argv[1:])
