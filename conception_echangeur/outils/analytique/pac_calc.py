"""Briques de calcul de la PAC de fenêtre (propane R290), partagées par les fiches HTML.

* cycle(Te, Tc, eta_is) : cycle à une compression, surchauffe et sous-refroidissement fixés ;
* air(T, Twb) : état de l'air humide (CoolProp HAPropsSI) ;
* batterie_seche / batterie_humide : ε, NTU et hA côté air requis pour une puissance donnée ;
* rho_moy / dp_circuit : masse volumique moyenne et perte de charge d'un circuit de tube (propane).
Corrélations côté propane reprises de outils/analytique/charge_propane.py.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from CoolProp.CoolProp import PropsSI
from CoolProp.HumidAirProp import HAPropsSI

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charge_propane as cp  # noqa: E402

F = "Propane"
PA = 101325.0
K = 273.15
SURCHAUFFE, SOUS_REFROID = 5.0, 4.0     # K
APPROCHE_ADP = 2.0                      # K : surface humide de l'évaporateur à Te + 2 K


def fmt(x, n=1):
    if x is None:
        return "—"
    s = f"{x:,.{n}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


def _props(P, h=None, T=None, s=None):
    a = ("P", P, "H", h) if h is not None else ("P", P, "T", T + K) if T is not None else ("P", P, "S", s)
    g = lambda k: PropsSI(k, *a, F)
    return dict(T=g("T") - K, h=g("H"), s=g("S"), rho=g("D"))


def sat(T):
    d = cp.sat(T)
    d["T"] = T
    d["P"] = PropsSI("P", "T", T + K, "Q", 0, F)
    return d


def cycle(Te, Tc, eta_is):
    Pe, Pc = PropsSI("P", "T", Te + K, "Q", 1, F), PropsSI("P", "T", Tc + K, "Q", 0, F)
    s1 = _props(Pe, T=Te + SURCHAUFFE)
    s2s = _props(Pc, s=s1["s"])
    h2 = s1["h"] + (s2s["h"] - s1["h"]) / eta_is
    s2 = _props(Pc, h=h2)
    s3 = _props(Pc, T=Tc - SOUS_REFROID)
    hl_e, hv_e = PropsSI("H", "P", Pe, "Q", 0, F), PropsSI("H", "P", Pe, "Q", 1, F)
    hl_c, hv_c = PropsSI("H", "P", Pc, "Q", 0, F), PropsSI("H", "P", Pc, "Q", 1, F)
    q_e, w, q_c = s1["h"] - s3["h"], h2 - s1["h"], h2 - s3["h"]
    return dict(Te=Te, Tc=Tc, eta=eta_is, Pe=Pe, Pc=Pc, s1=s1, s2=s2, s3=s3,
                x4=(s3["h"] - hl_e) / (hv_e - hl_e), q_e=q_e, w=w, q_c=q_c,
                zones_e=dict(diphasique=(hv_e - s3["h"]) / q_e, surchauffe=(s1["h"] - hv_e) / q_e),
                zones_c=dict(desurchauffe=(h2 - hv_c) / q_c, condensation=(hv_c - hl_c) / q_c,
                             sous_refroid=(hl_c - s3["h"]) / q_c),
                COP_froid=q_e / w, COP_chaud=q_c / w,
                carnot_froid=(Te + K) / (Tc - Te), carnot_chaud=(Tc + K) / (Tc - Te))


def air(Tdb, Twb):
    T, B = Tdb + K, Twb + K
    w = HAPropsSI("W", "T", T, "P", PA, "B", B)
    return dict(T=Tdb, Twb=Twb, w=w, h=HAPropsSI("H", "T", T, "P", PA, "W", w),
                v=HAPropsSI("V", "T", T, "P", PA, "W", w), Tdp=HAPropsSI("D", "T", T, "P", PA, "W", w) - K,
                cp=1006.0 + 1860.0 * w)


def w_sat(T):
    return HAPropsSI("W", "T", T + K, "P", PA, "R", 1.0)


def batterie_seche(a, V_m3h, Q, T_sat):
    """Condenseur : l'air chauffe de T_in vers T_sat. ε = ΔT/(T_sat − T_in), NTU = −ln(1 − ε), hA = NTU ṁ cp."""
    m = V_m3h / 3600 / a["v"]
    dT = Q / (m * a["cp"])
    eps = dT / (T_sat - a["T"])
    ntu = -math.log(1 - eps) if 0 < eps < 1 else None
    return dict(V=V_m3h, m_air=m, dT=dT, T_out=a["T"] + dT, eps=eps, NTU=ntu, hA=ntu * m * a["cp"] if ntu else None,
                sature=False, eau=0.0, sensible=Q)


def batterie_humide(a, V_m3h, Q, Te):
    """Évaporateur, méthode enthalpique (Lewis = 1). ε_h = Δh/(h_in − h_sat(Te)), NTU = −ln(1 − ε_h), hA = NTU ṁ cp.
    Soufflage : droite entrée → ADP (air saturé à Te + 2 K)."""
    m = V_m3h / 3600 / a["v"]
    dh = Q / m
    h_out = a["h"] - dh
    h_se = HAPropsSI("H", "T", Te + K, "P", PA, "R", 1.0)
    eps = dh / (a["h"] - h_se)
    ntu = -math.log(1 - eps) if 0 < eps < 1 else None
    Tadp = Te + APPROCHE_ADP
    w_adp, h_adp = w_sat(Tadp), HAPropsSI("H", "T", Tadp + K, "P", PA, "R", 1.0)
    r = dict(V=V_m3h, m_air=m, dh=dh, eps=eps, NTU=ntu, hA=ntu * m * a["cp"] if ntu else None, Tadp=Tadp, h_se=h_se)
    if a["w"] <= w_adp:
        r.update(T_out=a["T"] - Q / (m * a["cp"]), w_out=a["w"], sensible=Q, eau=0.0, sature=False)
    else:
        fr = (a["h"] - h_out) / (a["h"] - h_adp)
        r["sature"] = fr > 1
        fr = min(fr, 1.0)
        T_out = a["T"] - fr * (a["T"] - Tadp)
        w_out = a["w"] - fr * (a["w"] - w_adp)
        r.update(T_out=T_out, w_out=w_out, sensible=m * a["cp"] * (a["T"] - T_out), eau=m * (a["w"] - w_out) * 3600)
    r["latent"] = Q - r["sensible"]
    r["givre"] = Tadp < 0 and r["eau"] > 0
    return r


def rho_moy(role, T_sat, G, x4):
    """Masse volumique moyenne d'un circuit (zones en longueur : évap. 85 % diph. + 15 % vapeur ;
    cond. 12 % vapeur + 78 % diph. + 10 % liquide)."""
    s = sat(T_sat)
    if role == "e":
        xs = np.linspace(x4, 1.0, 200)
        a = cp.fraction_vide(xs, G, s)
        return 0.85 * float(np.mean(a * s["rv"] + (1 - a) * s["rl"])) + 0.15 * s["rv"]
    xs = np.linspace(1.0, 0.0, 200)
    a = cp.fraction_vide(xs, G, s)
    return 0.12 * s["rv"] + 0.78 * float(np.mean(a * s["rv"] + (1 - a) * s["rl"])) + 0.10 * s["rl"]


def dp_circuit(role, T_sat, G, D, L, x4):
    s = sat(T_sat)
    mono = lambda mu, rho, l: cp.frottement_mono(G, D, mu) / rho * l
    if role == "e":
        xs = np.linspace(x4, 1.0, 200)
        return float(np.mean(cp.dpdz_diphasique(xs, G, D, s))) * 0.85 * L + mono(s["mv"], s["rv"], 0.15 * L)
    xs = np.linspace(1.0, 0.0, 200)
    return (mono(s["mv"], s["rv"], 0.12 * L) + float(np.mean(cp.dpdz_diphasique(xs, G, D, s))) * 0.78 * L
            + mono(s["ml"], s["rl"], 0.10 * L))


CSS = """
:root { --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; --accent:#1c7ed6;
  --ok:#2b8a3e; --alerte:#c92a2a; --surligne:#e7f5ff; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fond:#141517; --carte:#1f2023;
  --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; --ok:#69db7c; --alerte:#ff8787; --surligne:#1b3550; } }
:root[data-theme="dark"] { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40;
  --accent:#4dabf7; --ok:#69db7c; --alerte:#ff8787; --surligne:#1b3550; }
* { box-sizing:border-box; }
body { margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1100px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:26px; margin:0 0 4px; } h2 { font-size:19px; margin:34px 0 8px; border-bottom:2px solid var(--trait); padding-bottom:4px; }
h3 { font-size:16px; margin:18px 0 6px; }
a { color:var(--accent); }
.sous { color:var(--doux); margin:0 0 18px; }
.carte { background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:14px 16px; margin:10px 0; overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { text-align:left; padding:6px 9px; border-bottom:1px solid var(--trait); vertical-align:top; }
th { color:var(--doux); font-weight:600; }
td.n, th.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
tr.retenu td { background:var(--surligne); font-weight:600; }
code, .f { font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:13px; }
.f { display:block; background:var(--fond); border:1px solid var(--trait); border-radius:6px; padding:8px 10px; margin:8px 0; white-space:pre-wrap; line-height:1.6; }
.note { color:var(--doux); font-size:13.5px; margin:6px 0; }
.alerte { color:var(--alerte); font-weight:600; } .ok { color:var(--ok); font-weight:600; }
nav ol { margin:0; padding-left:20px; columns:2; font-size:14px; }
sup a { text-decoration:none; font-size:11px; }
"""


def table(entetes, lignes, num=None, retenu=None):
    num = set(range(1, len(entetes))) if num is None else num
    o = ["<table><tr>" + "".join(f'<th class="{"n" if i in num else ""}">{h}</th>' for i, h in enumerate(entetes)) + "</tr>"]
    for j, l in enumerate(lignes):
        cls = ' class="retenu"' if retenu is not None and j == retenu else ""
        o.append(f"<tr{cls}>" + "".join(f'<td class="{"n" if i in num else ""}">{c}</td>' for i, c in enumerate(l)) + "</tr>")
    return "".join(o) + "</table>"
