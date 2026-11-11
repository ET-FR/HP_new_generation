#!/usr/bin/env python3
"""
Extraction des résultats d'un cas 2D (outils/cfd_2d/creer_cas.py) et comparaison aux références.

  plaques     f·Re et Nu locaux en écoulement établi (champs finaux, foamToVTK)  -> 24 et 7,54
  tube_isole  Cd moyen, Cl efficace, Strouhal, Nu moyen                           -> Hilpert,
              Churchill-Bernstein, Roshko
  batterie    Δp, NTU, h, j, f, Nu sur Ø extérieur, bilan d'énergie                -> Zukauskas

Grandeurs adimensionnelles : T est un scalaire passif (entrée 0, paroi 1), pression cinématique.

    python extraire.py dossier_du_cas [--json resultat.json]
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np


# ------------------------------------------------------------------ lecture des séries
def serie(cas: Path, nom: str, fichier: str = "surfaceFieldValue.dat") -> np.ndarray:
    """Concatène postProcessing/<nom>/<t>/<fichier> et ses variantes de reprise (<fichier>_0.dat,
    ...), triées par date ; pour un même instant, la valeur la plus récente l'emporte."""
    base = fichier[:-4] if fichier.endswith(".dat") else fichier
    fichiers = sorted((cas / "postProcessing" / nom).glob(f"*/{base}*.dat"), key=lambda p: p.stat().st_mtime)
    blocs = []
    for f in fichiers:
        lignes = [l.split() for l in f.read_text().splitlines() if l.strip() and not l.startswith("#")]
        if lignes:
            blocs.append(np.array([[float(x.strip("()")) for x in l] for l in lignes]))
    if not blocs:
        raise FileNotFoundError(f"{cas}/postProcessing/{nom}")
    a = np.vstack(blocs)[::-1]                      # le plus récent d'abord
    _, i = np.unique(a[:, 0], return_index=True)    # première occurrence = la plus récente
    return a[i]


def moyenne(a: np.ndarray, t0: float, col=1):
    """Moyenne temporelle pondérée par les pas de temps (pas variable) et écart-type relatif."""
    m = a[:, 0] >= t0
    t, v = a[m, 0], a[m, col]
    if len(t) < 3:
        return float(v.mean()), 0.0
    dt = np.gradient(t)
    moy = float((v * dt).sum() / dt.sum())
    sd = float(np.sqrt(((v - moy) ** 2 * dt).sum() / dt.sum()))
    return moy, sd / abs(moy) if moy else 0.0


def stabilite(a: np.ndarray, t0: float, col=1) -> float:
    """Écart relatif entre la moyenne de la 1re et de la 2e moitié de la fenêtre de moyenne.
    Moins de 1 % : durée simulée suffisante ; sinon prolonger le calcul (reprise possible)."""
    m = a[:, 0] >= t0
    t = a[m, 0]
    tm = 0.5 * (t[0] + t[-1])
    m1, _ = moyenne(a[(a[:, 0] >= t0) & (a[:, 0] < tm)], t0, col)
    m2, _ = moyenne(a[a[:, 0] >= tm], tm, col)
    return abs(m2 - m1) / abs(0.5 * (m1 + m2)) if (m1 + m2) else 0.0


def k_air(air):
    return air["rho"] * air["cp"] * air["nu"] / air["Pr"]


# ------------------------------------------------------------------ batterie
def zukauskas(Re_max, Pr, ST_sur_SL, N_L, aligne=False):
    """Zukauskas (Incropera, tab. 7.5 et 7.6), faisceau en quinconce, Pr / Pr_paroi = 1.
    Retourne (Nu, domaine). Pour 1e2 < Re < 1e3, Zukauskas renvoie au cylindre isolé ;
    on donne aussi la loi 1e3-2e5 prolongée, à titre de fourchette."""
    C2 = {1: 0.64, 2: 0.76, 3: 0.84, 4: 0.89, 5: 0.92, 7: 0.95, 10: 0.97, 13: 0.98, 16: 0.99}
    if aligne:
        C2 = {1: 0.70, 2: 0.80, 3: 0.86, 4: 0.90, 5: 0.92, 7: 0.95, 10: 0.97, 13: 0.98, 16: 0.99}
    c2 = C2.get(N_L, 1.0) if N_L < 20 else (C2[max(k for k in C2 if k <= N_L)] if N_L < 16 else 1.0)
    cyl = 0.51 * Re_max ** 0.5 * Pr ** 0.37                 # cylindre isolé, 40 < Re < 1e3
    loi = (0.27 * Re_max ** 0.63 if aligne else 0.35 * ST_sur_SL ** 0.2 * Re_max ** 0.6) * Pr ** 0.36
    return dict(Nu_cylindre_isole=cyl * c2, Nu_loi_1e3=loi * c2, C2=c2)


def batterie(cas: Path, m: dict) -> dict:
    air, t0 = m["air"], m["debut_moyenne"]
    dz = m["epaisseur_mm"] * 1e-3
    p_in, sd_pi = moyenne(serie(cas, "pEntree"), t0)
    p_out, _ = moyenne(serie(cas, "pSortie"), t0)
    T_out, sd_T = moyenne(serie(cas, "TSortie"), t0)
    Qv, _ = moyenne(serie(cas, "debit"), t0)
    flux, sd_f = moyenne(serie(cas, "fluxParoi"), t0)
    ailettes = m.get("ailettes", False)
    if ailettes:                                   # étape 3 : flux des deux ailettes en plus des tubes
        noms = sorted(d.name for d in (cas / "postProcessing").glob("fluxAilette*"))   # ailettes ou TPMS
        flux_ail = sum(moyenne(serie(cas, n), t0)[0] for n in noms)
        flux_tubes, flux = flux, flux + flux_ail
    pin_s, pout_s = serie(cas, "pEntree"), serie(cas, "pSortie")
    dp_s = np.c_[pin_s[:, 0], pin_s[:, 1] - np.interp(pin_s[:, 0], pout_s[:, 0], pout_s[:, 1])]
    stab = dict(dp=stabilite(dp_s, t0), T_sortie=stabilite(serie(cas, "TSortie"), t0),
                flux_paroi=stabilite(serie(cas, "fluxParoi"), t0))
    Qv = abs(Qv)                                   # m³/s par épaisseur dz (flux entrant)
    dp = (p_in - p_out) * air["rho"]
    mcp = air["rho"] * Qv * air["cp"]
    eps = min(T_out, 1 - 1e-12)
    NTU = -math.log(1 - eps)
    A_air = m["A_air_domaine"] if ailettes else m["rangs"] * m["P_ext"] * dz   # surface côté air (domaine)
    h = mcp * NTU / A_air                          # UA-LMTD, paroi isotherme
    Q_bilan = mcp * T_out                          # par ΔT = 1 K
    Q_paroi = air["rho"] * air["cp"] * air["nu"] / air["Pr"] * abs(flux)
    U, Umax = m["U"], m["Umax"]                    # U : vitesse frontale (devant la batterie)
    D = 6e-3                                       # Ø extérieur du tube rond de référence
    k = k_air(air)
    Nu_D = h * D / k
    Re_max = Umax * D / air["nu"]
    # j et f sur la vitesse maximale (section minimale), convention des faisceaux
    j = h / (air["rho"] * Umax * air["cp"]) * air["Pr"] ** (2 / 3)
    f_rang = dp / (m["rangs"] * 0.5 * air["rho"] * Umax ** 2)   # Zukauskas : Δp = N_L χ f ρ Vmax²/2
    P_vent = dp * Qv                               # W par épaisseur dz
    r = dict(cas=cas.name, forme=m.get("forme"), U=U, Umax=Umax, Re_max_D6=Re_max,
             dp_Pa=dp, fluct_p=sd_pi, T_sortie=T_out, fluct_T=sd_T, NTU=NTU, h=h, Nu_D6=Nu_D, j=j, f_par_rang=f_rang, j_sur_f=j / f_rang,
             Q_W_par_K=Q_bilan, ecart_bilan=(Q_paroi - Q_bilan) / Q_bilan, fluct_flux=sd_f,
             P_vent_sur_Q=P_vent / Q_bilan, profondeur_mm=(m["x_noyau"][1] - m["x_noyau"][0]) * 1e3,
             A_air=A_air, stabilite_moyenne=stab,
             **(dict(part_ailettes=flux_ail / flux, facteur_surface=m["facteur_surface"]) if ailettes else {}),
             duree_suffisante=max(stab.values()) < 0.01)
    if m.get("forme") == "rond":
        r["zukauskas"] = zukauskas(Re_max, air["Pr"], m["Pt"] / m["Pl"], m["rangs"], m.get("aligne", False))
        try:   # perte de charge : abaques de Zukauskas (1972) numérisés par la bibliothèque ht
            from ht.conv_tube_bank import dP_Zukauskas   # (aligné : seulement pas carré dans ht)
            if m.get("aligne", False):
                raise ImportError
            dpz = dP_Zukauskas(Re=Re_max, n=m["rangs"], ST=m["Pt"], SL=m["Pl"], D=D,
                               rho=air["rho"], Vmax=Umax)
            r["zukauskas"].update(dp_Pa=dpz, f_par_rang=dpz / (m["rangs"] * 0.5 * air["rho"] * Umax ** 2),
                                  ecart_dp=dp / dpz - 1)
        except ImportError:
            pass
    return r


# ------------------------------------------------------------------ tube isolé
def tube_isole(cas: Path, m: dict) -> dict:
    air, t0, U, D = m["air"], m["debut_moyenne"], m["U"], m["D"]
    dz = m["epaisseur_mm"] * 1e-3
    c = serie(cas, "efforts", "coefficient.dat")
    entetes = None
    for f in (cas / "postProcessing" / "efforts").glob("*/coefficient*.dat"):
        for l in f.read_text().splitlines():
            if l.startswith("#") and "Cd" in l:
                entetes = l.lstrip("#").split()
        break
    iCd, iCl = entetes.index("Cd"), entetes.index("Cl")
    Cd, _ = moyenne(c, t0, iCd)
    msk = c[:, 0] >= t0
    t, Cl = c[msk, 0], c[msk, iCl]
    Cl_eff = float(np.sqrt(np.mean((Cl - Cl.mean()) ** 2)))
    tu = np.linspace(t[0], t[-1], 2 ** 14)
    s = np.interp(tu, t, Cl) - Cl.mean()
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s))))
    fr = np.fft.rfftfreq(len(s), tu[1] - tu[0])
    f_tourb = float(fr[1:][np.argmax(sp[1:])])
    St = f_tourb * D / U
    flux, sd_f = moyenne(serie(cas, "fluxParoi"), t0)
    stab = dict(Cd=stabilite(c, t0, iCd), Nu=stabilite(serie(cas, "fluxParoi"), t0))
    Nu = abs(flux) / (math.pi * dz)               # Nu = ∫grad(T)·n dA / (π dz), ΔT = 1
    Re, Pr = U * D / air["nu"], air["Pr"]
    hilpert = 0.683 * Re ** 0.466 * Pr ** (1 / 3)
    cb = 0.3 + 0.62 * Re ** 0.5 * Pr ** (1 / 3) / (1 + (0.4 / Pr) ** (2 / 3)) ** 0.25 * \
        (1 + (Re / 282000) ** (5 / 8)) ** (4 / 5)
    roshko = 0.212 * (1 - 12.7 / Re)
    return dict(cas=cas.name, Re=Re, Cd=Cd, Cl_eff=Cl_eff, f_Hz=f_tourb, St=St, St_Roshko=roshko,
                Nu=Nu, fluct_Nu=sd_f, Nu_Hilpert=hilpert, Nu_Churchill_Bernstein=cb,
                periodes_moyennees=(t[-1] - t[0]) * f_tourb, stabilite_moyenne=stab,
                duree_suffisante=max(stab.values()) < 0.01)


# ------------------------------------------------------------------ plaques
def plaques(cas: Path, m: dict) -> dict:
    import pyvista as pv
    air = m["air"]
    if not (cas / "VTK").exists():
        subprocess.run("foamToVTK -latestTime -fields '(U p T gradT)' > log.foamToVTK 2>&1",
                       shell=True, cwd=cas, check=True, executable="/bin/bash")
    d = sorted([p for p in (cas / "VTK").glob("*_[0-9]*") if p.is_dir()], key=lambda p: int(p.name.rsplit("_", 1)[1]))[-1]
    vol = pv.read(d / "internal.vtu")
    cc = vol.cell_centers().points
    U = vol.cell_data["U"][:, 0]; p = vol.cell_data["p"]; T = vol.cell_data["T"]
    Dh, gap, Ub = m["Dh"], m["ecart_mm"] * 1e-3, m["U"]
    xs = np.unique(np.round(cc[:, 0], 9))
    p_moy, T_b, x_ok = [], [], []
    for x in xs:
        s = np.isclose(cc[:, 0], x)
        dy = np.gradient(np.sort(cc[s, 1]))                 # mailles resserrées : pondérer par dy
        o = np.argsort(cc[s, 1])
        p_moy.append(np.sum(p[s][o] * dy) / np.sum(dy))
        T_b.append(np.sum(U[s][o] * T[s][o] * dy) / np.sum(U[s][o] * dy))
        x_ok.append(x)
    x_ok, p_moy, T_b = map(np.array, (x_ok, p_moy, T_b))
    paroi = pv.read(d / "boundary" / "paroi.vtp")
    fc = paroi.cell_centers().points
    g = paroi.cell_data["gradT"]
    n = np.where(fc[:, 1] > gap / 2, 1.0, -1.0)            # normale sortante (vers les plaques)
    dTdn = g[:, 1] * n
    zone = (x_ok > 0.10) & (x_ok < 0.19)
    pente = -np.polyfit(x_ok[zone], p_moy[zone], 1)[0]
    f = pente * Dh / (2 * Ub ** 2)
    Re = Ub * Dh / air["nu"]
    # Nu local là où (1 - Tb) reste mesurable (zone thermiquement établie, 50 à 110 mm)
    Nu_x = []
    for x in x_ok[(x_ok > 0.05) & (x_ok < 0.11)]:
        sel = np.isclose(fc[:, 0], x, atol=1e-9)
        if sel.any():
            Tb = np.interp(x, x_ok, T_b)
            Nu_x.append(dTdn[sel].mean() * Dh / (1 - Tb))
    Nu_x = np.array(Nu_x)
    # longueur d'établissement dynamique : gradient de pression à 1 % du gradient établi
    grad_loc = -np.gradient(p_moy, x_ok)
    etab = x_ok[np.argmax(np.abs(grad_loc / pente - 1) < 0.01)]
    return dict(cas=cas.name, Re=Re, fRe=f * Re, fRe_exact=24.0, Nu=float(np.median(Nu_x)),
                Nu_min=float(Nu_x.min()), Nu_max=float(Nu_x.max()), Nu_exact=7.541,
                L_etablissement_mm=float(etab * 1e3), L_etab_theorique_mm=0.05 * Re * Dh * 1e3,
                profil=dict(x=x_ok.tolist(), p=p_moy.tolist(), Tb=T_b.tolist()))


def extraire(cas: str | Path) -> dict:
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    return {"plaques": plaques, "tube_isole": tube_isole, "batterie": batterie}[m["cas"]](cas, m)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cas")
    ap.add_argument("--json")
    a = ap.parse_args()
    r = extraire(a.cas)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in r.items() if k != "profil"}, indent=1, ensure_ascii=False))
