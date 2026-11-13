#!/usr/bin/env python3
"""
Fiche de conception de la PAC de fenêtre 9 000 BTU/h (R290) : objectif +50 % sur Midea et Gradient.

Démarche en 5 étapes, chaque chiffre calculé ici (CoolProp, propane HEOS et air humide) :
  0. cibles de COP tirées des fiches constructeurs (×1,5) aux points de certification US (AHRI / DOE) ;
  1. puissance → débit de propane → compresseur ;
  2. COP cible → budget électrique → COP du cycle → températures Te et Tc ;
  3. Te et Tc → efficacité, NTU et hA requis côté air, par échangeur et par mode ;
  4. hA → surface d'échange, surface frontale, perte de charge admise (ventilateurs) ;
  5. côté propane : perte de charge admise, budget de charge → volume, tubes, surface secondaire.

    .venv/bin/python conception_echangeur/outils/analytique/fiche_pac_9000.py   → pac_9000btu.html (racine du dépôt)
"""
from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charge_propane as cp  # noqa: E402
from pac_calc import (CSS, APPROCHE_ADP, SOUS_REFROID, SURCHAUFFE, air, batterie_humide,  # noqa: E402
                      batterie_seche, cycle, dp_circuit, fmt as f, rho_moy, sat, table)

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE.parent / "pac_9000btu.html"   # racine du dépôt : document de conception général

# ---------------------------------------------------------------- sources
SRC = {
    "midea": ("Midea, fiche technique Packaged Window Heat Pump MAH09H1AGR (juin 2024)",
              "https://midea.com/content/dam/midea-aem/us/air-conditioners/pwhp/mah09h1agr/PWHP-Product-Specs-20240612-v2-0.pdf"),
    "grad_fiche": ("Gradient, fiche technique All-Weather 120V (V4, sept. 2023)",
                   "https://cdn.shopify.com/s/files/1/0558/4925/5070/files/All_Weather_120V_Spec_Sheet.pdf"),
    "grad_page": ("Gradient, page produit All-Weather 120V (EER 13,6, COP 4,04 / 2,37 / 2,06 / 1,59)",
                  "https://www.gradientcomfort.com/products/gradient-all-weather-120v-window-heat-pump"),
    "grad_faq": ("Gradient, FAQ : CEER 16,8 et HEER 9,4",
                 "https://faq.gradientcomfort.com/hc/en-us/articles/31293494685851-What-is-the-CEER-and-HEER-of-the-All-Weather-120V-heat-pump"),
    "grad_ev": ("Efficiency Vermont, fiche produit Gradient",
                "https://www.efficiencyvermont.com/Media/Default/docs/products/gradient-product-specifications.pdf"),
    "iec": ("IEC 60335-2-40 : limite m1 = 4 × LFL (propane : 4 × 38 g/m³ = 152 g)",
            None),
    "coolprop": ("CoolProp (propriétés du propane, équation HEOS ; air humide HAPropsSI)", "http://www.coolprop.org/"),
}
ORDRE_SRC = list(SRC)


def ref(*cles):
    return "".join(f'<sup><a href="#src-{c}">[{ORDRE_SRC.index(c) + 1}]</a></sup>' for c in cles)


# ---------------------------------------------------------------- objectif
BTU = 0.29307107
Q_NOM = 9000 * BTU                                  # W, froid en clim et chaleur en chauffage
GAIN = 1.5
CONCURRENTS = [  # (point, Midea, Gradient fiche 2023, Gradient page actuelle) : COP W/W (EER / 3,412)
    ("clim", 11.81 / 3.412, 10.0 / 3.412, 13.6 / 3.412),
    ("ch47", 4.00, 4.00, 4.04),
    ("ch17", 2.42, 2.60, 2.37),
    ("ch5", 2.00, 2.35, 2.06),
]
# Points de certification US (AHRI 310/380, DOE) : air intérieur et extérieur (T sèche, T humide en °C)
POINTS = {
    "clim": dict(nom="Clim 95 °F (35 °C)", mode="froid", int=(26.7, 19.4), ext=(35.0, 23.9)),
    "ch47": dict(nom="Chauffage 47 °F (8,3 °C)", mode="chaud", int=(21.1, 15.6), ext=(8.3, 6.1)),
    "ch17": dict(nom="Chauffage 17 °F (−8,3 °C)", mode="chaud", int=(21.1, 15.6), ext=(-8.3, -9.4)),
    "ch5": dict(nom="Chauffage 5 °F (−15 °C)", mode="chaud", int=(21.1, 15.6), ext=(-15.0, -15.6)),
}
# ---------------------------------------------------------------- choix de conception (à itérer)
ETA_IS, ETA_V = 0.75, 0.90             # compresseur haut de gamme (hypothèse à confirmer par une carte)
DP_AIR, ETA_VENT = 25.0, 0.30          # Pa par échangeur (batterie + grille), rendement ventilateur + moteur EC
CHOIX = {  # Te, Tc (°C), débits d'air intérieur / extérieur (m³/h)
    "clim": dict(Te=14.0, Tc=40.0, Vi=600, Ve=2500),
    "ch47": dict(Te=3.5, Tc=32.0, Vi=800, Ve=2500),
    "ch17": dict(Te=-12.0, Tc=32.0, Vi=800, Ve=2500),
    "ch5": dict(Te=-19.0, Tc=32.0, Vi=800, Ve=2500),
}
N_NOM = 60.0                            # tr/s en clim
HA_U = [30.0, 50.0, 80.0]               # W/m²K : η₀·h côté air (hypothèses)
U_FACE = [1.0, 1.5, 2.0]                # m/s : vitesse frontale de l'air
DT_SAT_MAX = 0.5                        # K de saturation admis par échangeur côté propane
LIMITE = cp.LIMITE_G
HORS_ECH = cp.hors_tubes_g()
PAROI = 0.5e-3
D_INT = [1.5e-3, 2.0e-3, 2.5e-3, 3.0e-3, 4.0e-3, 5.0e-3]


def tf(x):
    """Température : entière sans décimale, sinon une décimale."""
    return f(x, 0) if abs(x - round(x)) < 1e-9 else f(x, 1)


def ventilateurs(Vi, Ve):
    return (Vi + Ve) / 3600 * DP_AIR / ETA_VENT


def cible(k):
    _, mi, g1, g2 = next(c for c in CONCURRENTS if c[0] == k)
    return GAIN * max(mi, g1, g2), max(mi, g1, g2)


def cop_unite(k, Te, Tc, Vi, Ve, eta=ETA_IS):
    c = cycle(Te, Tc, eta)
    froid = POINTS[k]["mode"] == "froid"
    m = Q_NOM / (c["q_e"] if froid else c["q_c"])
    W = m * c["w"]
    return Q_NOM / (W + ventilateurs(Vi, Ve)), c, m, W


# ---------------------------------------------------------------- calculs
def calculer():
    R = dict(pts={})
    for k, pt in POINTS.items():
        ch = CHOIX[k]
        cop, c, m, W = cop_unite(k, ch["Te"], ch["Tc"], ch["Vi"], ch["Ve"])
        froid = pt["mode"] == "froid"
        ai, ae = air(*pt["int"]), air(*pt["ext"])
        Qe, Qc = m * c["q_e"], m * c["q_c"]
        if froid:
            b_int, b_ext = batterie_humide(ai, ch["Vi"], Qe, c["Te"]), batterie_seche(ae, ch["Ve"], Qc, c["Tc"])
        else:
            b_int, b_ext = batterie_seche(ai, ch["Vi"], Qc, c["Tc"]), batterie_humide(ae, ch["Ve"], Qe, c["Te"])
        cib, best = cible(k)
        P_v = ventilateurs(ch["Vi"], ch["Ve"])
        R["pts"][k] = dict(c=c, m=m, W=W, Qe=Qe, Qc=Qc, cop=cop, cible=cib, best=best, P_v=P_v,
                           W_max=Q_NOM / cib - P_v, cop_cycle_req=Q_NOM / (Q_NOM / cib - P_v),
                           ai=ai, ae=ae, b_int=b_int, b_ext=b_ext, V_asp=m / c["s1"]["rho"], **ch)
    p = R["pts"]
    # compresseur : cylindrée fixée par la clim à N_NOM ; vitesse nécessaire aux autres points
    R["cyl"] = p["clim"]["V_asp"] / (ETA_V * N_NOM)
    for k in p:
        p[k]["n"] = p[k]["V_asp"] / (ETA_V * R["cyl"])
    # sensibilité du COP de l'unité à Te et Tc (pas de 1 K) autour du choix, deux rendements
    R["balayage"] = {}
    for k in ("clim", "ch47"):
        ch = CHOIX[k]
        lignes = []
        for dTe, dTc in ((-2, 2), (0, 2), (0, 0), (1, -1), (2, -2), (3, -3)):
            Te, Tc = ch["Te"] + dTe, ch["Tc"] + dTc
            lignes.append((Te, Tc, cop_unite(k, Te, Tc, ch["Vi"], ch["Ve"], 0.65)[0],
                           cop_unite(k, Te, Tc, ch["Vi"], ch["Ve"], 0.75)[0]))
        R["balayage"][k] = lignes
    # clim à ×1,5 Gradient (6,0) : Te / Tc nécessaires
    R["clim6"] = []
    for Te, Tc in ((12, 42), (13, 41), (14, 40)):
        cop_, c_, m_, _ = cop_unite("clim", Te, Tc, CHOIX["clim"]["Vi"], CHOIX["clim"]["Ve"])
        bi = batterie_humide(air(*POINTS["clim"]["int"]), CHOIX["clim"]["Vi"], Q_NOM, Te)
        be = batterie_seche(air(*POINTS["clim"]["ext"]), CHOIX["clim"]["Ve"], m_ * c_["q_c"], Tc)
        R["clim6"].append((Te, Tc, cop_, bi["sensible"] / Q_NOM, bi["eau"], bi["hA"], be["hA"]))
    # sensibilité des deux cas qui dimensionnent au débit d'air
    R["hA_int"] = max(p, key=lambda k: p[k]["b_int"]["hA"] or 0)
    R["hA_ext"] = max(p, key=lambda k: p[k]["b_ext"]["hA"] or 0)
    ki, ke = R["hA_int"], R["hA_ext"]

    def sens(k, cote, debits):
        q = p[k]
        froid = POINTS[k]["mode"] == "froid"
        out = []
        for V in debits:
            if cote == "int":
                b = batterie_humide(q["ai"], V, q["Qe"], q["c"]["Te"]) if froid else batterie_seche(q["ai"], V, q["Qc"], q["c"]["Tc"])
            else:
                b = batterie_seche(q["ae"], V, q["Qc"], q["c"]["Tc"]) if froid else batterie_humide(q["ae"], V, q["Qe"], q["c"]["Te"])
            out.append(b)
        return out
    R["sens_int"] = sens(ki, "int", [500, 600, 700, 800, 1000, 1200])
    R["sens_ext"] = sens(ke, "ext", [1500, 2000, 2500, 3000, 3500])
    # côté propane : tubes
    budget = LIMITE - HORS_ECH
    roles = [(k, r) for k in ("clim", "ch47") for r in ("e", "c")]
    T_role = lambda k, r: p[k]["c"]["Te"] if r == "e" else p[k]["c"]["Tc"]
    tubes = []
    for D in D_INT:
        A_i = math.pi * D ** 2 / 4
        for n in range(1, 500):
            rho = {k: rho_moy("e", p[k]["c"]["Te"], p[k]["m"] / (n * A_i), p[k]["c"]["x4"])
                   + rho_moy("c", p[k]["c"]["Tc"], p[k]["m"] / (n * A_i), 0) for k in ("clim", "ch47")}
            V = budget * 1e-3 / max(rho.values())
            L = V / A_i
            dts = {(k, r): dp_circuit(r, T_role(k, r), p[k]["m"] / (n * A_i), D, L / n, p[k]["c"]["x4"])
                   / sat(T_role(k, r))["dPdT"] for k, r in roles}
            if max(dts.values()) <= DT_SAT_MAX:
                Do = D + 2 * PAROI
                A_t = math.pi * Do * L
                hi, he = p[ki]["b_int"]["hA"], p[ke]["b_ext"]["hA"]
                tubes.append(dict(D=D, Do=Do, n=n, V=V, L=L, Lc=L / n, G=p["clim"]["m"] / (n * A_i), dts=dts,
                                  rho=rho, A_t=A_t, r_int=hi / 50 / A_t, r_ext=he / 50 / A_t))
                break
    R["tubes"], R["budget"] = tubes, budget
    return R


# ---------------------------------------------------------------- page
def calc_air(q, cote, k):
    """Exemple détaillé, ligne par ligne, du calcul de hA pour un échangeur."""
    b = q["b_" + cote]
    a = q["ai"] if cote == "int" else q["ae"]
    froid = POINTS[k]["mode"] == "froid"
    humide = (cote == "int") == froid
    Q = q["Qe"] if humide else q["Qc"]
    T_sat = q["c"]["Te"] if humide else q["c"]["Tc"]
    V = q["Vi"] if cote == "int" else q["Ve"]
    rho = 1 / a["v"]
    l = [f"① débit d'air      ṁ = {f(V,0)} m³/h ÷ 3 600 × {f(rho,3)} kg/m³ = {f(b['m_air'],3)} kg/s"]
    if humide:
        l.append(f"② enthalpie         Δh = Q / ṁ = {f(Q,0)} / {f(b['m_air'],3)} = {f(b['dh']/1e3,2)} kJ/kg  "
                 f"(air {f(a['h']/1e3,1)} → {f((a['h']-b['dh'])/1e3,1)} kJ/kg)")
        l.append(f"③ efficacité        ε = Δh / (h_air − h_sat(Te = {tf(T_sat)} °C)) = {f(b['dh']/1e3,2)} / ({f(a['h']/1e3,1)} − "
                 f"{f(b['h_se']/1e3,1)}) = {f(b['eps'],3)}")
    else:
        l.append(f"② échauffement      ΔT = Q / (ṁ cp) = {f(Q,0)} / ({f(b['m_air'],3)} × {f(a['cp'],0)}) = {f(b['dT'],1)} K  "
                 f"(air {f(a['T'],1)} → {f(b['T_out'],1)} °C)")
        l.append(f"③ efficacité        ε = ΔT / (Tc − T_air) = {f(b['dT'],1)} / ({tf(T_sat)} − {f(a['T'],1)}) = {f(b['eps'],3)}")
    if b["NTU"]:
        l.append(f"④ taille            NTU = −ln(1 − ε) = {f(b['NTU'],2)}  →  hA = NTU × ṁ × cp = {f(b['NTU'],2)} × "
                 f"{f(b['m_air'],3)} × {f(a['cp'],0)} = {f(b['hA'],0)} W/K")
    else:
        l.append("④ ε ≥ 1 : impossible avec ce débit d'air")
    return '<span class="f">' + "\n".join(l) + "</span>"


def page(R):
    p = R["pts"]
    K = list(POINTS)
    nom = lambda k: POINTS[k]["nom"]
    ki, ke = R["hA_int"], R["hA_ext"]
    hAi, hAe = p[ki]["b_int"]["hA"], p[ke]["b_ext"]["hA"]
    t = R["tubes"]
    t25 = next(x for x in t if abs(x["D"] - 2.5e-3) < 1e-9)
    o = [f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PAC fenêtre 9000 BTU</title>
<style>{CSS}</style></head><body><main>
<h1>PAC de fenêtre R290, 9 000 BTU/h : fiche de conception générale</h1>
<p class="sous">Objectif : COP 50 % au-dessus de Midea et Gradient aux points de certification US · calculé le
{date.today().strftime('%d/%m/%Y')} par <code>conception_echangeur/outils/analytique/fiche_pac_9000.py</code>{ref('coolprop')}</p>
<nav class="carte"><ol>
<li><a href="#e0">Objectif chiffré</a></li><li><a href="#e1">Étape 1 · Débit de propane</a></li>
<li><a href="#e2">Étape 2 · Te et Tc imposées par le COP</a></li><li><a href="#e3">Étape 3 · hA côté air</a></li>
<li><a href="#e4">Étape 4 · Surface, façade, ventilateurs</a></li><li><a href="#e5">Étape 5 · Côté propane et charge</a></li>
<li><a href="#bilan">Cahier des charges</a></li><li><a href="#hyp">Hypothèses et limites</a></li>
<li><a href="#sources">Sources</a></li></ol></nav>"""]

    # ---------------- 0
    o.append('<h2 id="e0">Objectif chiffré</h2><div class="carte">')
    rows = []
    for k, mi, g1, g2 in CONCURRENTS:
        rows.append([nom(k), f(mi, 2), f(g1, 2), f(g2, 2), f(max(mi, g1, g2), 2), f"<b>{f(p[k]['cible'],2)}</b>"])
    o.append(table(["Point (COP en W/W, ventilateurs inclus)", "Midea PWHP 9k" + ref("midea"),
                    "Gradient, fiche 2023" + ref("grad_fiche"), "Gradient, page actuelle" + ref("grad_page", "grad_ev"),
                    "Meilleur", "Cible ×1,5"], rows))
    o.append(f"""<p class="note">EER (BTU/Wh) ÷ 3,412 = COP (W/W). Capacité visée : 9 000 BTU/h = {f(Q_NOM,0)} W à chaque
point (Midea la garde jusqu'à 5 °F, Gradient descend à 7 200 BTU/h à 5 °F). Clim saisonnière : CEER 16 (Midea) et 16,8
(Gradient){ref('grad_faq')}, cible ≈ 25. Conditions de l'air (AHRI / DOE) : clim 35 °C dehors, 26,7 / 19,4 °C dedans
(sèche / humide) ; chauffage 21,1 / 15,6 °C dedans, dehors 8,3 / 6,1 · −8,3 / −9,4 · −15 / −15,6 °C.</p></div>""")

    # ---------------- 1
    o.append('<h2 id="e1">Étape 1 · Puissance → débit de propane → compresseur</h2><div class="carte">')
    o.append('<span class="f">clim : ṁ = Q_froid / q_évap   ·   chauffage : ṁ = Q_chaud / q_cond\n'
             'q_évap = h1 − h4 (évaporation + surchauffe)   ·   q_cond = h2 − h3   ·   débit aspiré = ṁ / ρ_aspiration\n'
             'cylindrée = débit aspiré (clim) / (η_v × 60 tr/s)   ·   vitesse aux autres points = débit aspiré / (η_v × cylindrée)</span>')
    rows = [[nom(k), tf(p[k]["c"]["Te"]) + " / " + tf(p[k]["c"]["Tc"]), f(p[k]["c"]["x4"], 3), f(p[k]["c"]["q_e"] / 1e3, 1),
             f(p[k]["c"]["q_c"] / 1e3, 1), f(p[k]["m"] * 1e3, 2), f(p[k]["c"]["s1"]["rho"], 2), f(p[k]["V_asp"] * 3600, 2),
             f(p[k]["n"], 0)] for k in K]
    o.append(table(["Point", "Te / Tc °C (étape 2)", "Titre après détente", "q_évap kJ/kg", "q_cond kJ/kg", "ṁ g/s",
                    "ρ aspiration kg/m³", "Débit aspiré m³/h", "Vitesse tr/s"], rows))
    o.append(f"""<p class="note">Le débit ne dépend que de la puissance et des enthalpies : ≈ 7 à 10 g/s. Cylindrée :
<b>{f(R['cyl']*1e6,1)} cm³/tr</b>. Par grand froid la vapeur aspirée est 2 fois moins dense : la vitesse doit monter à
{f(p['ch5']['n'],0)} tr/s pour garder 9 000 BTU/h (à vérifier dans l'enveloppe du compresseur choisi).</p></div>""")

    # ---------------- 2
    o.append('<h2 id="e2">Étape 2 · Le COP cible fixe Te et Tc</h2><div class="carte">')
    o.append(f'<span class="f">puissance électrique totale = Q / COP_cible\n'
             f'compresseur = totale − ventilateurs        (ventilateurs = débit × {f(DP_AIR,0)} Pa / {f(ETA_VENT,2)}, voir étape 4)\n'
             f'COP du cycle requis = Q / compresseur  →  Te et Tc telles que le cycle (η_is = {f(ETA_IS,2)}) l\'atteigne\n'
             f'plus Tc − Te est petit, moins le compresseur travaille ; mais plus Te et Tc sont proches de l\'air, plus l\'échangeur est grand</span>')
    rows = []
    for k in K:
        q = p[k]
        ok = q["cop"] >= q["cible"] - 1e-9
        rows.append([nom(k).replace(" (", "<br>("), f(q["cible"], 2), f(Q_NOM / q["cible"], 0), f(q["P_v"], 0), f(q["W_max"], 0), f(q["cop_cycle_req"], 2),
                     tf(q["c"]["Te"]) + " / " + tf(q["c"]["Tc"]), tf(q["c"]["Tc"] - q["c"]["Te"]),
                     f(q["c"]["COP_froid" if POINTS[k]["mode"] == "froid" else "COP_chaud"], 2),
                     f'<span class="{"ok" if ok else "alerte"}">{f(q["cop"],2)}</span>'])
    o.append(table(["Point", "Cible", "Élec. W", "Vent. W", "Comp. max W", "Cycle requis",
                    "Te / Tc °C", "Écart K", "Cycle obtenu", "COP unité"], rows))
    for k, titre in (("clim", "clim 35 °C"), ("ch47", "chauffage 8,3 °C")):
        rows = [[tf(Te), tf(Tc), tf(Tc - Te), f(c65, 2), f(c75, 2)] for Te, Tc, c65, c75 in R["balayage"][k]]
        o.append(f"<h3>Sensibilité, {titre} : COP de l'unité selon Te et Tc</h3>")
        o.append(table(["Te °C", "Tc °C", "Tc − Te", "η_is 0,65", "η_is 0,75"], rows, num={0, 1, 2, 3, 4}, retenu=2))
    rows = [[tf(Te), tf(Tc), f(c, 2), f(sh, 2), f(eau, 2), f(hi, 0) if hi else "—", f(he, 0) if he else "—"]
            for Te, Tc, c, sh, eau, hi, he in R["clim6"]]
    o.append(f"""<p class="note">Avec un compresseur moyen (η_is = 0,65), aucune cible n'est tenue : <b>le compresseur est
la première condition</b>. En clim, la cible ({f(p['clim']['cible'],2)}, ×1,5 de la page Gradient) impose Te = 14 °C :
la paroi (Te + {f(APPROCHE_ADP,0)} K) est au-dessus du point de rosée de la pièce ({f(p['clim']['ai']['Tdp'],1)} °C),
l'appareil ne déshumidifie plus à ce point. Un jour humide, la régulation baisse Te et le COP descend
(tableau ci-dessous, débits d'air de la clim) :</p>""")
    o.append(table(["Te °C", "Tc °C", "COP unité", "Part sensible", "Condensat kg/h", "hA int. W/K", "hA ext. W/K"], rows,
                   num=set(range(7)), retenu=2))
    o.append("</div>")

    # ---------------- 3
    o.append('<h2 id="e3">Étape 3 · Te et Tc → hA requis côté air</h2><div class="carte">')
    o.append('<span class="f">hA (W/K) = conductance côté air : surface × coefficient d\'échange. Elle dit combien de W passent par K d\'écart air / propane.\n'
             'condenseur (air sec) : ε = ΔT_air / (Tc − T_air,entrée)            NTU = −ln(1 − ε)      hA = NTU × ṁ_air × cp\n'
             'évaporateur (humide) : ε = Δh_air / (h_air,entrée − h_sat(Te))    (méthode enthalpique, Lewis = 1)\n'
             'ε → 1 quand l\'air sort presque à Tc (ou Te) : le hA tend vers l\'infini.</span>')
    o.append(f"<h3>Exemple détaillé : intérieur, {nom(ki)} (cas qui dimensionne)</h3>" + calc_air(p[ki], "int", ki))
    o.append(f"<h3>Exemple détaillé : extérieur, {nom(ke)} (cas qui dimensionne)</h3>" + calc_air(p[ke], "ext", ke))
    rows = []
    for k in K:
        for cote in ("int", "ext"):
            q, b = p[k], p[k]["b_" + cote]
            froid = POINTS[k]["mode"] == "froid"
            role = ("évaporateur" if froid else "condenseur") if cote == "int" else ("condenseur" if froid else "évaporateur")
            hum = role == "évaporateur"
            Q = q["Qe"] if hum else q["Qc"]
            rows.append([f"{nom(k)} · {'intérieur' if cote == 'int' else 'extérieur'} · {role}", f(Q, 0),
                         tf(q["c"]["Te"] if hum else q["c"]["Tc"]), f(q["Vi"] if cote == "int" else q["Ve"], 0),
                         f((q["ai"] if cote == "int" else q["ae"])["T"], 1) + " → " + f(b["T_out"], 1),
                         f(b["eps"], 3), f(b["NTU"], 2) if b["NTU"] else '<span class="alerte">impossible</span>',
                         f"<b>{f(b['hA'],0)}</b>" if b["hA"] else "—",
                         f(b["sensible"] / Q, 2) if hum else "1,00",
                         (f(b["eau"], 2) + (" givre" if b.get("givre") else "")) if hum else "—"])
    o.append("<h3>Tous les modes</h3>")
    o.append(table(["Point · échangeur · rôle", "Q W", "T sat °C", "Air m³/h", "Air °C", "ε", "NTU", "hA W/K",
                    "Part sensible", "Eau kg/h"], rows))
    ai_ = p["clim"]["b_int"]
    o.append(f"""<p class="note">Clim : {f(ai_['sensible'],0)} W sensibles + {f(ai_['latent'],0)} W latents
({f(ai_['eau'],2)} kg/h de condensat). Par grand froid le givre n'est pas compté : il réduit le hA et impose des dégivrages.</p>""")
    for titre, k, lst, cote in ((f"intérieur, {nom(ki)}", ki, R["sens_int"], "int"), (f"extérieur, {nom(ke)}", ke, R["sens_ext"], "ext")):
        Vref = p[k]["Vi"] if cote == "int" else p[k]["Ve"]
        rows = [[f(b["V"], 0), f(b["V"] / 1.699, 0), f(b["T_out"], 1), f(b["eps"], 3),
                 f(b["NTU"], 2) if b["NTU"] else '<span class="alerte">impossible</span>', f(b["hA"], 0) if b["hA"] else "—",
                 f(b["V"] / 3600 * DP_AIR / ETA_VENT, 0)] for b in lst]
        o.append(f"<h3>Débit d'air ↔ hA, {titre}</h3>")
        o.append(table(["m³/h", "CFM", "Air sortie °C", "ε", "NTU", "hA W/K", f"Ventil. W ({f(DP_AIR,0)} Pa)"], rows,
                       num=set(range(7)), retenu=[b["V"] for b in lst].index(Vref) if Vref in [b["V"] for b in lst] else None))
    o.append("<p class=\"note\">Plus d'air : hA plus faible mais ventilateur plus gourmand et plus bruyant. Le débit retenu est le compromis.</p></div>")

    # ---------------- 4
    o.append('<h2 id="e4">Étape 4 · hA → surface d\'échange, façade, ventilateurs</h2><div class="carte">')
    o.append(f'<span class="f">surface côté air  A = hA / (η₀ × h)        (h : coefficient d\'échange côté air ; η₀ : rendement de surface des ailettes)\n'
             f'surface frontale  S = débit d\'air / vitesse frontale\n'
             f'ventilateur       P = débit × Δp / η_vent  →  Δp admis = P × η_vent / débit</span>')
    rows = [["Intérieur (hA " + f(hAi, 0) + " W/K)"] + [f(hAi / u, 1) for u in HA_U],
            ["Extérieur (hA " + f(hAe, 0) + " W/K)"] + [f(hAe / u, 1) for u in HA_U]]
    o.append(table(["Surface côté air m²"] + [f"η₀h = {f(u,0)} W/m²K" for u in HA_U], rows))
    Vi_max = max(p[k]["Vi"] for k in K)
    Ve_max = max(p[k]["Ve"] for k in K)
    rows = [[f"Intérieur ({f(Vi_max,0)} m³/h)"] + [f(Vi_max / 3600 / u, 3) for u in U_FACE],
            [f"Extérieur ({f(Ve_max,0)} m³/h)"] + [f(Ve_max / 3600 / u, 3) for u in U_FACE]]
    o.append(table(["Surface frontale m²"] + [f"{f(u,1)} m/s" for u in U_FACE], rows))
    o.append(f"""<p class="note">η₀h ≈ 50 W/m²K est un ordre de grandeur pour des ailettes à 1–2 m/s ; la CFD des formes
(TPMS, ailettes ondulées) donne la vraie valeur, et la perte de charge associée. Budget ventilateurs aux débits max :
{f(ventilateurs(Vi_max, Ve_max),0)} W, soit <b>{f(DP_AIR,0)} Pa par échangeur</b> avec η = {f(ETA_VENT,2)} : c'est la
contrainte la plus serrée. Profondeur d'échangeur ≈ surface / (surface frontale × densité de surface m²/m³).</p></div>""")

    # ---------------- 5
    o.append('<h2 id="e5">Étape 5 · Côté propane : perte de charge et charge</h2><div class="carte">')
    o.append(f'<span class="f">Δp admis = (dP/dT)_sat × {f(DT_SAT_MAX,1)} K\n'
             f'budget de charge des échangeurs = {f(LIMITE,0)} g{ref("iec")} − {f(HORS_ECH,0)} g (ligne liquide, carter, huile) = {f(R["budget"],0)} g\n'
             f'deux échangeurs de même volume V : charge d\'un mode = V × (ρ_moy évaporateur + ρ_moy condenseur)  →  V_max = budget / max des modes\n'
             f'longueur de tube L = V_max / (π D²/4)   ·   circuits n : le plus petit tel que ΔT_sat ≤ {f(DT_SAT_MAX,1)} K   ·   surface du tube = π D_ext L\n'
             f'rapport de surface = surface côté air (η₀h = 50) / surface du tube  =  ce que les ailettes ou le TPMS doivent ajouter</span>')
    Ts = sorted({p[k]["c"]["Te"] for k in ("clim", "ch47")} | {p[k]["c"]["Tc"] for k in ("clim", "ch47")})
    rows = []
    for T in Ts:
        s = sat(T)
        rows.append([tf(T), f(s["P"] / 1e5, 2), f(s["rl"], 0), f(s["rv"], 1), f(s["dPdT"] / 1e3, 1), f(s["dPdT"] * DT_SAT_MAX / 1e3, 1)])
    o.append(table(["T sat °C", "P bar", "ρ liquide kg/m³", "ρ vapeur kg/m³", "dP/dT kPa/K", "Δp admis kPa"], rows))
    rows = [[f(x["D"] * 1e3, 1) + " / " + f(x["Do"] * 1e3, 1), f(x["V"] * 1e6, 0), f(x["L"], 1), str(x["n"]), f(x["Lc"], 2),
             f(x["G"], 0), f(max(x["dts"].values()), 2), f(x["A_t"], 2), f(x["r_int"], 1), f(x["r_ext"], 1)] for x in t]
    o.append("<h3>Choix du tube (par échangeur)</h3>")
    o.append(table(["Ø int. / ext. mm", "V max cm³", "L tube m", "Circuits", "L/circuit m", "G kg/m²s",
                    "ΔT_sat max K", "Surface tube m²", "Rapport int.", "Rapport ext."], rows,
                   retenu=[x["D"] for x in t].index(t25["D"])))
    o.append("""<p class="note">Un tube fin loge plus de longueur, donc plus de surface primaire, dans le même volume
(surface ∝ D_ext / D_int²) : il faut moins de surface secondaire, mais plus de circuits à alimenter également.
Le volume des distributeurs et collecteurs n'est pas compté : il s'ajoute.</p></div>""")

    # ---------------- bilan
    o.append('<h2 id="bilan">Cahier des charges des échangeurs</h2><div class="carte">')
    o.append(table(["Exigence", "Échangeur intérieur", "Échangeur extérieur"], [
        ["Cas qui dimensionne", nom(ki), nom(ke)],
        ["hA côté air", f"<b>{f(hAi,0)} W/K</b>", f"<b>{f(hAe,0)} W/K</b>"],
        ["Surface côté air (η₀h = 50)", f"{f(hAi/50,1)} m²", f"{f(hAe/50,1)} m²"],
        ["Débit d'air max", f"{f(Vi_max,0)} m³/h", f"{f(Ve_max,0)} m³/h"],
        ["Perte de charge air", f"≤ {f(DP_AIR,0)} Pa", f"≤ {f(DP_AIR,0)} Pa"],
        ["Volume intérieur propane", f"≤ {f(t25['V']*1e6,0)} cm³", f"≤ {f(t25['V']*1e6,0)} cm³"],
        ["Perte de charge propane", f"≤ {f(DT_SAT_MAX,1)} K de saturation", f"≤ {f(DT_SAT_MAX,1)} K de saturation"],
        ["Exemple Ø int. 2,5 mm", f"{f(t25['L'],0)} m, {t25['n']} circuits, rapport de surface {f(t25['r_int'],0)}",
         f"{f(t25['L'],0)} m, {t25['n']} circuits, rapport de surface {f(t25['r_ext'],0)}"],
        ["Autres contraintes", "condensat : 0 au point de certification, jusqu'à " + f(max(x[4] for x in R['clim6']), 2)
         + " kg/h quand la régulation baisse Te à 12 °C (jour humide)",
         "givre sous ≈ 5 °C, dégivrage ; réversible (condenseur l'été)"],
        ["Hors échangeurs", f"compresseur {f(R['cyl']*1e6,1)} cm³/tr, η_is ≥ {f(ETA_IS,2)}", f"ventilateurs ≤ {f(ventilateurs(Vi_max, Ve_max),0)} W au total"],
    ], num=set()))
    o.append("</div>")

    # ---------------- hypothèses
    o.append('<h2 id="hyp">Hypothèses et limites</h2><div class="carte"><ul>')
    for li in [
        f"Te et Tc sont choisies (table de l'étape 2) pour tenir la cible ; le hA en découle. Le simulateur <code>pac_fenetre</code> fait le calcul couplé inverse.",
        f"Compresseur : η_is = {f(ETA_IS,2)} et η_v = {f(ETA_V,2)} constants (haut de gamme) ; surchauffe {f(SURCHAUFFE,0)} K, sous-refroidissement {f(SOUS_REFROID,0)} K.",
        f"Ventilateurs : {f(DP_AIR,0)} Pa par échangeur, rendement {f(ETA_VENT,2)} ; pertes moteur, électronique, veille et lignes non comptées (les COP constructeurs les incluent).",
        f"Évaporateur humide : paroi à Te + {f(APPROCHE_ADP,0)} K pour la droite de soufflage, Lewis = 1. Givre non modélisé.",
        "hA côté air seul : la résistance côté propane et la paroi s'ajoutent (prévoir une marge de 10 à 30 %).",
        f"Charge : limite m1 = {f(LIMITE,0)} g{ref('iec')} ; {f(HORS_ECH,0)} g hors échangeurs (valeurs du simulateur). Zones des tubes en fractions de longueur fixes.",
        "Les valeurs Gradient diffèrent entre la fiche 2023 et la page actuelle : la cible prend la meilleure des deux.",
    ]:
        o.append(f"<li>{li}</li>")
    o.append("</ul></div>")
    o.append('<h2 id="sources">Sources</h2><div class="carte"><ol>')
    for k in ORDRE_SRC:
        t_, u = SRC[k]
        o.append(f'<li id="src-{k}"><a href="{u}">{t_}</a></li>' if u else f'<li id="src-{k}">{t_} (norme payante, IEC Webstore)</li>')
    o.append("</ol></div></main></body></html>")
    return "".join(o)


def main():
    R = calculer()
    SORTIE.write_text(page(R))
    print(SORTIE, f"{SORTIE.stat().st_size/1e3:.0f} ko")
    for k, q in R["pts"].items():
        print(f"{k}: COP {q['cop']:.2f} / cible {q['cible']:.2f}, ṁ {q['m']*1e3:.2f} g/s, n {q['n']:.0f} tr/s, "
              f"hA int {q['b_int']['hA']}, ext {q['b_ext']['hA']}")
    print("dimensionne :", R["hA_int"], R["hA_ext"], "cyl", R["cyl"] * 1e6)
    for x in R["tubes"]:
        print(f"D {x['D']*1e3}: n {x['n']} V {x['V']*1e6:.0f} L {x['L']:.1f} r_int {x['r_int']:.1f} r_ext {x['r_ext']:.1f}")


if __name__ == "__main__":
    main()
