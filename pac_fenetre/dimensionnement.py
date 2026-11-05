"""
Dimensionnement des échangeurs : géométrie + matériau -> UA, perte de charge,
puissance ventilateur, volume interne (charge R290), masse, coût ; puis
recherche du meilleur couple (batterie intérieure, batterie extérieure) en
évaluant le cycle complet (`PompeAChaleur`) sur des points normalisés.

Corrélations côté air de la forme j = Cj Re^-nj, f = Cf Re^-nf (Fanning),
Re sur le diamètre hydraulique du noyau (Kays & London). Les coefficients sont
des ordres de grandeur issus de la littérature (Kays & London, Wang 2000,
Chang & Wang 1997, travaux récents sur les gyroïdes imprimés) : ils doivent être
recalés sur essais ou CFD avant toute décision de conception.

Recherche en deux étages :
  1. Tous les échangeurs candidats d'un côté sont classés par une estimation
     rapide (Carnot x 0,5 avec un pincement fixe de l'autre côté + ventilateur).
  2. Les meilleurs, plus les meilleurs de chaque technologie / matériau et le
     front coût / performance, sont combinés et évalués avec le vrai cycle.
"""

from __future__ import annotations

import itertools
import math
import threading
import time

from .physique import T0, Conception, Conditions, PompeAChaleur, Propane

AIR = dict(rho=1.18, mu=1.85e-5, cp=1007.0, Pr=0.71)
ETA_VENTILATEUR = 0.20  # rendement global ventilateur + moteur EC (petits ventilateurs)
K_SYSTEME = 10.0        # pertes de charge hors batterie (grille, filtre, volute), en ρ u_face² / 2

MATERIAUX = {
    "Aluminium (brasé)": dict(k=190.0, rho=2730.0, cout_kg=12.0, e_min=0.08, impression=False),
    "Cuivre": dict(k=390.0, rho=8940.0, cout_kg=18.0, e_min=0.10, impression=False),
    "AlSi10Mg (LPBF)": dict(k=130.0, rho=2670.0, cout_kg=250.0, e_min=0.25, impression=True),
    "Inox 316L (LPBF)": dict(k=15.0, rho=7990.0, cout_kg=180.0, e_min=0.20, impression=True),
    "CuCrZr (LPBF)": dict(k=320.0, rho=8900.0, cout_kg=400.0, e_min=0.30, impression=True),
    "Ti6Al4V (LPBF)": dict(k=7.0, rho=4430.0, cout_kg=450.0, e_min=0.20, impression=True),
}

FAMILLES = {
    "tube_ailettes": dict(
        nom="Tube-ailettes", detail="tubes cuivre Ø7 mm, ailettes persiennées",
        materiaux=["Aluminium (brasé)", "Cuivre"],
        Cj=0.25, nj=0.42, Cf=1.2, nf=0.45, h_ref=3500.0, k_givre=1.0, cout_fixe=15.0,
        grille=dict(Fp=[1.2, 1.6, 2.0], rangs=[1, 2, 3]),
        notes="Référence industrielle, robuste, se draine bien. Volume interne élevé (charge).",
    ),
    "microcanaux": dict(
        nom="Microcanaux", detail="tubes plats aluminium multiports, ailettes persiennées",
        materiaux=["Aluminium (brasé)"],
        Cj=0.30, nj=0.42, Cf=1.25, nf=0.45, h_ref=4000.0, k_givre=0.8, cout_fixe=20.0,
        grille=dict(Fp=[1.0, 1.4, 1.8], P=[16, 24, 32]),
        notes="Faible charge et bon UA. En évaporateur : drainage des condensats, givrage et "
              "distribution du fluide plus délicats (réversible).",
    ),
    "tpms": dict(
        nom="Gyroïde TPMS", detail="échangeur deux fluides imprimé (paroi = surface primaire)",
        materiaux=["AlSi10Mg (LPBF)", "Inox 316L (LPBF)", "CuCrZr (LPBF)", "Ti6Al4V (LPBF)"],
        Cj=0.35, nj=0.40, Cf=1.5, nf=0.30, h_ref=4000.0, k_givre=0.7, cout_fixe=80.0,
        grille=dict(a=[3.0, 4.0, 6.0], e=["min", 0.4], phi=[0.2, 0.35], P=[10, 20, 30]),
        notes="Très compact, pas d'ailette donc la conductivité du matériau compte peu. "
              "Perte de charge élevée, volume côté propane important, coût d'impression.",
    ),
}

DEBITS = {"int": [300, 420, 550, 700], "ext": [700, 1000, 1300, 1700]}  # m3/h
FRACTIONS_FACE = [0.6, 0.8, 1.0]

# Points d'évaluation du cycle (fréquence fixe, comme une évaluation normalisée)
POINTS = {
    "clim": Conditions(mode="clim", T_ext=35.0, T_int=27.0, HR_ext=0.40, HR_int=0.47, freq=60.0),
    "chauffage": Conditions(mode="chauffage", T_ext=7.0, T_int=20.0, HR_ext=0.87, HR_int=0.50, freq=60.0),
    "grand_froid": Conditions(mode="chauffage", T_ext=-7.0, T_int=20.0, HR_ext=0.75, HR_int=0.50, freq=90.0),
}

OBJECTIFS = {
    "mixte": "Mixte : 50 % EER 35/27, 50 % chauffage",
    "clim": "EER climatisation 35/27",
    "chauffage": "Chauffage : 60 % COP 7/20, 40 % COP −7/20",
}

CONTRAINTES_DEFAUT = dict(
    puissance_kW=3.0, objectif="mixte",
    int_L=600, int_H=300, int_P=60, ext_L=600, ext_H=400, ext_P=80,  # mm
    v_max=2.5, charge_max_g=297.0, budget=1000.0,
    familles=list(FAMILLES), materiaux=list(MATERIAUX),
)


# --------------------------------------------------------------------------
# Géométrie -> grandeurs volumiques
# --------------------------------------------------------------------------
def geometrie(famille: str, materiau: str, p: dict):
    """Grandeurs par unité de volume du noyau, ou None si la géométrie est irréalisable.

    beta : surface côté air (m²/m³), sigma : fraction de passage de l'air,
    A_ref_v / V_ref_v : surface / volume côté propane par m³, metal : [(fraction, matériau)].
    """
    m = MATERIAUX[materiau]
    if famille == "tube_ailettes":
        Pt, Pl, d, di, t, tw = 21e-3, 12.7e-3, 7e-3, 6.4e-3, 0.1e-3, 0.3e-3
        Fp = p["Fp"] * 1e-3
        trou = math.pi * d ** 2 / 4 / (Pt * Pl)
        beta_f = 2 / Fp * (1 - trou)
        beta = beta_f + math.pi * d / (Pt * Pl) * (1 - t / Fp)
        return dict(
            D=p["rangs"] * Pl, beta=beta, sigma=(1 - d / Pt) * (1 - t / Fp),
            fin_frac=beta_f / beta, L_fin=0.5 * (1.13 * math.sqrt(Pt * Pl) - d), t_fin=t, k_fin=m["k"],
            A_ref_v=math.pi * di / (Pt * Pl), V_ref_v=math.pi * di ** 2 / 4 / (Pt * Pl),
            e_paroi=tw, k_paroi=MATERIAUX["Cuivre"]["k"],
            metal=[(t / Fp * (1 - trou), materiau), (math.pi * d * tw / (Pt * Pl), "Cuivre")],
        )
    if famille == "microcanaux":
        Tp, Td, t, Dh_r, vide = 10e-3, 1.8e-3, 0.08e-3, 0.8e-3, 0.5
        Fp = p["Fp"] * 1e-3
        beta_f = 2 * (Tp - Td) / (Tp * Fp)
        beta = beta_f + 2 / Tp * (1 - t / Fp)
        return dict(
            D=p["P"] * 1e-3, beta=beta, sigma=(1 - Td / Tp) * (1 - t / Fp),
            fin_frac=beta_f / beta, L_fin=(Tp - Td) / 2, t_fin=t, k_fin=m["k"],
            A_ref_v=Td / Tp * vide * 4 / Dh_r, V_ref_v=Td / Tp * vide,
            e_paroi=0.3e-3, k_paroi=m["k"],
            metal=[(t / Fp * (Tp - Td) / Tp, materiau), (Td / Tp * (1 - vide), materiau)],
        )
    if famille == "tpms":
        a = p["a"] * 1e-3
        e = (m["e_min"] if p["e"] == "min" else max(p["e"], m["e_min"])) * 1e-3
        beta = 3.1 / a           # surface du gyroïde par unité de volume
        solide = beta * e
        sigma = 1 - p["phi"] - solide
        if sigma < 0.3:
            return None
        return dict(
            D=p["P"] * 1e-3, beta=beta, sigma=sigma, fin_frac=0.0, L_fin=0.0, t_fin=e, k_fin=m["k"],
            A_ref_v=beta, V_ref_v=p["phi"], e_paroi=e, k_paroi=m["k"], metal=[(solide, materiau)],
        )
    raise ValueError(famille)


def performance(famille: str, g: dict, W: float, H: float, debit: float) -> dict:
    """UA (W/K), perte de charge (Pa), puissance ventilateur (W), volume interne (L), masse, coût."""
    F = FAMILLES[famille]
    V = W * H * g["D"]
    q = debit / 3600.0
    u_face = q / (W * H)
    u_c = u_face / g["sigma"]
    Dh = 4 * g["sigma"] / g["beta"]
    Re = AIR["rho"] * u_c * Dh / AIR["mu"]
    j = F["Cj"] * Re ** -F["nj"]
    f = F["Cf"] * Re ** -F["nf"]
    h = j * AIR["rho"] * u_c * AIR["cp"] * AIR["Pr"] ** (-2 / 3)
    A_air = g["beta"] * V
    eta_f = 1.0
    if g["fin_frac"] > 0:
        mL = math.sqrt(2 * h / (g["k_fin"] * g["t_fin"])) * g["L_fin"]
        eta_f = math.tanh(mL) / mL
    eta_o = 1 - g["fin_frac"] * (1 - eta_f)
    A_ref = g["A_ref_v"] * V
    R_air = 1 / (eta_o * h * A_air)
    R_ref = 1 / (F["h_ref"] * A_ref)
    R_paroi = g["e_paroi"] / (g["k_paroi"] * A_ref)
    UA = 1 / (R_air + R_ref + R_paroi)
    dP = f * 4 * g["D"] / Dh * AIR["rho"] * u_c ** 2 / 2 + K_SYSTEME * AIR["rho"] * u_face ** 2 / 2
    masse = sum(fr * V * MATERIAUX[mat]["rho"] for fr, mat in g["metal"])
    cout = sum(fr * V * MATERIAUX[mat]["rho"] * MATERIAUX[mat]["cout_kg"] for fr, mat in g["metal"]) + F["cout_fixe"]
    return dict(
        u_face=u_face, Re=Re, j=j, f=f, h_air=h, eta_ailette=eta_f, Dh_mm=Dh * 1e3, A_air=A_air,
        UA=UA, part_air=R_air / (R_air + R_ref + R_paroi), dP=dP, P_vent=q * dP / ETA_VENTILATEUR,
        V_ref_L=g["V_ref_v"] * V * 1e3, volume_L=V * 1e3, masse=masse, cout=cout,
    )


def _libelle_params(famille, p, materiau):
    if famille == "tube_ailettes":
        return f"{p['rangs']} rang(s), pas d'ailette {p['Fp']} mm"
    if famille == "microcanaux":
        return f"pas d'ailette {p['Fp']} mm"
    e = MATERIAUX[materiau]["e_min"] if p["e"] == "min" else max(p["e"], MATERIAUX[materiau]["e_min"])
    return f"cellule {p['a']:g} mm, paroi {e:g} mm, {p['phi'] * 100:.0f} % côté propane"


def candidats(cote: str, ct: dict):
    """Tous les échangeurs réalisables pour un côté ('int' ou 'ext')."""
    Lmax, Hmax, Pmax = (ct[f"{cote}_{k}"] * 1e-3 for k in "LHP")
    out = []
    for fam in ct["familles"]:
        F = FAMILLES[fam]
        noms, valeurs = zip(*F["grille"].items())
        for mat in F["materiaux"]:
            if mat not in ct["materiaux"]:
                continue
            for combo in itertools.product(*valeurs):
                p = dict(zip(noms, combo))
                g = geometrie(fam, mat, p)
                if g is None or g["D"] > Pmax + 1e-9:
                    continue
                for fl, fh in itertools.product(FRACTIONS_FACE, FRACTIONS_FACE):
                    W, H = Lmax * fl, Hmax * fh
                    for debit in DEBITS[cote]:
                        if debit / 3600 / (W * H) > ct["v_max"]:
                            continue
                        perf = performance(fam, g, W, H, debit)
                        out.append(dict(
                            id=f"{cote}{len(out)}", cote=cote, famille=fam, materiau=mat,
                            techno=F["nom"], geometrie=_libelle_params(fam, p, mat),
                            L=round(W * 1e3), H=round(H * 1e3), P=round(g["D"] * 1e3, 1), debit=debit, **perf,
                        ))
    return out


# --------------------------------------------------------------------------
# Estimation rapide (étage 1)
# --------------------------------------------------------------------------
PINCEMENT_AUTRE = 8.0  # K, pincement supposé de l'autre batterie
RENDEMENT_CARNOT = 0.5


def _poids(objectif):
    return {"mixte": {"clim": 0.5, "chauffage": 0.3, "grand_froid": 0.2},
            "clim": {"clim": 1.0},
            "chauffage": {"chauffage": 0.6, "grand_froid": 0.4}}[objectif]


def estimation(c: dict, Q: float, objectif: str) -> float:
    """Puissance électrique approchée (W) pour fournir Q, avec cet échangeur."""
    C = AIR["rho"] * c["debit"] / 3600 * AIR["cp"]
    epsC = (1 - math.exp(-c["UA"] / C)) * C
    total = 0.0
    for nom, w in _poids(objectif).items():
        pt = POINTS[nom]
        dT = min(Q / epsC, 40.0)
        evap_ici = (pt.mode == "clim") == (c["cote"] == "int")
        T_air = pt.T_int if c["cote"] == "int" else pt.T_ext
        T_autre = pt.T_ext if c["cote"] == "int" else pt.T_int
        if evap_ici:
            Te, Tc = T_air - dT, T_autre + PINCEMENT_AUTRE
        else:
            Tc, Te = T_air + dT, T_autre - PINCEMENT_AUTRE
        cop = RENDEMENT_CARNOT * ((Tc if pt.mode == "chauffage" else Te) + T0) / max(Tc - Te, 1.0)
        total += w * (Q / cop + c["P_vent"])
    return total


def _selection(liste, n_top=10, n_par_techno=2, n_front=10):
    """Meilleurs candidats + meilleurs par technologie / matériau + front coût / estimation."""
    tries = sorted(liste, key=lambda c: c["estim"])
    garde = {c["id"]: c for c in tries[:n_top]}
    par = {}
    for c in tries:
        k = (c["famille"], c["materiau"])
        if len(par.setdefault(k, [])) < n_par_techno:
            par[k].append(c)
    for cs in par.values():
        garde.update((c["id"], c) for c in cs)
    front, meilleur = [], math.inf
    for c in sorted(liste, key=lambda c: c["cout"]):
        if c["estim"] < meilleur - 1e-6:
            front.append(c)
            meilleur = c["estim"]
    pas = max(1, len(front) // n_front)
    garde.update((c["id"], c) for c in front[::pas])
    return list(garde.values())


# --------------------------------------------------------------------------
# Évaluation du cycle complet (étage 2)
# --------------------------------------------------------------------------
def evaluer_couple(ci: dict, ce: dict, fl: Propane, ct: dict) -> dict:
    c = Conception(
        UA_int_ref=ci["UA"], UA_ext_ref=ce["UA"], debit_int_nom=ci["debit"], debit_ext_nom=ce["debit"],
        P_vent_int_nom=ci["P_vent"], P_vent_ext_nom=ce["P_vent"], V_bat_int=ci["V_ref_L"], V_bat_ext=ce["V_ref_L"],
        multiplicateurs=dict(k_UA=1.0, k_vent=1.0, k_vol=1.0, k_givre=FAMILLES[ce["famille"]]["k_givre"]),
    )
    pac = PompeAChaleur(c, fl)
    res, raisons = {}, []
    for nom, cond in POINTS.items():
        e = pac.resoudre(cond)
        if not e.ok:
            return dict(i=ci["id"], e=ce["id"], faisable=False, score=None, raisons=[f"{nom} : {e.message}"])
        res[nom] = e
    eer = res["clim"].COP
    cop7 = res["chauffage"].COP_integre
    cop_7 = res["grand_froid"].COP_integre
    chauff = 0.6 * cop7 + 0.4 * cop_7
    score = {"mixte": 0.5 * eer + 0.5 * chauff, "clim": eer, "chauffage": chauff}[ct["objectif"]]
    Q_clim, Q_ch = res["clim"].Q_utile / 1e3, res["chauffage"].Q_utile / 1e3
    charge = max(e.charge_g for e in res.values())
    cout = ci["cout"] + ce["cout"]
    if Q_clim < ct["puissance_kW"] * 0.995:
        raisons.append(f"froid {Q_clim:.2f} kW < {ct['puissance_kW']:g} kW")
    if Q_ch < ct["puissance_kW"] * 0.995:
        raisons.append(f"chaud {Q_ch:.2f} kW < {ct['puissance_kW']:g} kW")
    if charge > ct["charge_max_g"]:
        raisons.append(f"charge {charge:.0f} g > {ct['charge_max_g']:.0f} g")
    if cout > ct["budget"]:
        raisons.append(f"coût {cout:.0f} € > {ct['budget']:.0f} €")
    alarmes = sorted({a for e in res.values() for a in e.alarmes})
    return dict(
        i=ci["id"], e=ce["id"], faisable=not raisons, raisons=raisons, score=score,
        EER=eer, COP7=cop7, COP_7=cop_7, Q_clim=Q_clim, Q_chauf=Q_ch, Q_froid7=res["grand_froid"].Q_utile / 1e3,
        charge_g=charge, cout=cout, masse=ci["masse"] + ce["masse"], P_vent=res["clim"].P_vent,
        Te_clim=res["clim"].Te, Tc_clim=res["clim"].Tc, Te_ch=res["chauffage"].Te, Tc_ch=res["chauffage"].Tc,
        alarmes=alarmes,
    )


def _cle(r):
    """Classement : faisables d'abord, puis score décroissant."""
    return (not r["faisable"], -(r["score"] or 0))


def optimiser(ct: dict, progres=lambda frac, msg: None) -> dict:
    t0 = time.time()
    Q = ct["puissance_kW"] * 1e3
    progres(0.0, "Génération des géométries")
    cands = {}
    for cote in ("int", "ext"):
        cands[cote] = candidats(cote, ct)
        for c in cands[cote]:
            c["estim"] = estimation(c, Q, ct["objectif"])
    if not cands["int"] or not cands["ext"]:
        cote = "intérieur" if not cands["int"] else "extérieur"
        raise ValueError(f"Aucun échangeur {cote} possible avec ces contraintes "
                         "(dimensions, vitesse d'air, technologies et matériaux autorisés).")
    sel = {cote: _selection(cands[cote]) for cote in cands}
    fl = Propane()
    resultats = {}
    n_prevu = len(sel["int"]) * 2 + len(sel["ext"]) + 36 + len(sel["ext"])
    n_fait = 0

    def ev(ci, ce):
        nonlocal n_fait
        k = (ci["id"], ce["id"])
        if k not in resultats:
            resultats[k] = evaluer_couple(ci, ce, fl, ct)
            n_fait += 1
            progres(min(0.99, n_fait / n_prevu), f"Cycle complet : {n_fait} couples évalués")
        return resultats[k]

    def meilleur(rs):
        return min(rs, key=_cle)

    # Ancrage : extérieur le mieux estimé, puis on alterne les côtés
    ext0 = min(sel["ext"], key=lambda c: c["estim"])
    r_int = {ci["id"]: ev(ci, ext0) for ci in sel["int"]}
    best_i = next(c for c in sel["int"] if c["id"] == meilleur(r_int.values())["i"])
    r_ext = {ce["id"]: ev(best_i, ce) for ce in sel["ext"]}
    best_e = next(c for c in sel["ext"] if c["id"] == meilleur(r_ext.values())["e"])
    r_int = {ci["id"]: ev(ci, best_e) for ci in sel["int"]}
    top_i = sorted(sel["int"], key=lambda c: _cle(r_int[c["id"]]))[:6]
    top_e = sorted(sel["ext"], key=lambda c: _cle(r_ext[c["id"]]))[:6]
    for ci, ce in itertools.product(top_i, top_e):
        ev(ci, ce)
    best = meilleur(resultats.values())
    best_i = next(c for c in sel["int"] if c["id"] == best["i"])
    for ce in sel["ext"]:
        ev(best_i, ce)

    couples = sorted(resultats.values(), key=_cle)
    utilises = {c["id"]: c for cote in sel for c in sel[cote]}
    par_techno = {}
    for cote, cle_id in (("int", "i"), ("ext", "e")):
        groupes = {}
        for r in couples:
            c = utilises[r[cle_id]]
            groupes.setdefault((c["famille"], c["materiau"]), r)
        par_techno[cote] = [dict(famille=f, materiau=m, techno=FAMILLES[f]["nom"], couple=couples.index(r))
                            for (f, m), r in groupes.items()]
    progres(1.0, "Terminé")
    return dict(
        couples=couples, candidats=utilises, par_techno=par_techno,
        stats=dict(n_int=len(cands["int"]), n_ext=len(cands["ext"]), n_couples=len(couples),
                   duree=time.time() - t0),
        contraintes=ct,
    )


def hypotheses() -> dict:
    """Données affichées dans l'onglet (familles, matériaux, objectifs, valeurs par défaut)."""
    return dict(
        familles={k: {x: v[x] for x in ("nom", "detail", "materiaux", "Cj", "nj", "Cf", "nf", "h_ref", "notes")}
                  for k, v in FAMILLES.items()},
        materiaux=MATERIAUX, objectifs=OBJECTIFS, defaut=CONTRAINTES_DEFAUT,
        air=dict(eta_ventilateur=ETA_VENTILATEUR, K_systeme=K_SYSTEME), debits=DEBITS,
    )


# --------------------------------------------------------------------------
# Exécution en tâche de fond (pour le serveur web)
# --------------------------------------------------------------------------
class Optimiseur:
    def __init__(self):
        self._verrou = threading.Lock()
        self._etat = dict(statut="inactif", progression=0.0, message="", resultats=None, erreur=None)

    def _maj(self, **kw):
        with self._verrou:
            self._etat.update(kw)

    def lancer(self, demande: dict) -> bool:
        with self._verrou:
            if self._etat["statut"] == "en cours":
                return False
            self._etat.update(statut="en cours", progression=0.0, message="Démarrage", erreur=None)
        ct = dict(CONTRAINTES_DEFAUT)
        for k, v in demande.items():
            if k in ("familles", "materiaux"):
                ct[k] = [x for x in v if x in (FAMILLES if k == "familles" else MATERIAUX)]
            elif k == "objectif":
                ct[k] = v if v in OBJECTIFS else "mixte"
            elif k in ct:
                ct[k] = max(float(v), 1e-3)
        threading.Thread(target=self._executer, args=(ct,), daemon=True).start()
        return True

    def _executer(self, ct):
        try:
            res = optimiser(ct, lambda frac, msg: self._maj(progression=frac, message=msg))
            self._maj(statut="terminé", resultats=res, progression=1.0)
        except Exception as exc:  # erreur affichée dans l'onglet
            self._maj(statut="erreur", erreur=str(exc))

    def instantane(self) -> dict:
        with self._verrou:
            return dict(self._etat)
