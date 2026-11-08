"""
Comparateur de surfaces d'échange : même enveloppe, mêmes débits d'air, même puissance
et mêmes conditions pour chaque technologie ; cycle complet résolu pour chacune.

Candidats :
  * référence  : batteries tube-ailettes du simulateur temps réel (modèle UA nominal)
  * tpms:<surface>:feuillet / tpms:<surface>:hybride  (gyroïde, Diamond, FKS, I-WP, Primitive)
  * tubes_nus  : faisceau de tubes nus ronds fins (VDI)
Les TPMS sans corrélation côté air (campagne CFD non faite) sont listés « à calibrer ».
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import replace

from .aeraulique import CircuitAir, VentilateurRendementConstant
from .dimensionnement import MATERIAUX
from .echangeurs_air import EchangeurTPMS, EchangeurTubesNus, correlation_air
from .physique import Conception, Conditions, PompeAChaleur
from .simu_gyroide import _resoudre_puissance
from .tpms import SURFACES

DEFAUT = dict(
    mode="chauffage", T_ext=7.0, T_int=20.0, HR_ext=0.87, HR_int=0.50, puissance_kW=2.0, eta_vent=0.25,
    int=dict(largeur_mm=600, hauteur_mm=350, profondeur_mm=25, debit_m3h=450),
    ext=dict(largeur_mm=700, hauteur_mm=450, profondeur_mm=30, debit_m3h=1000),
    tpms=dict(phi_air=0.6, Dh_mm=4.0, phi_propane=0.10, materiau="AlSi10Mg (LPBF)", h_propane=2500,
              d_tube_mm=3.0, e_tube_mm=0.4, pas_tube_mm=12.0),
    tubes=dict(d_mm=1.0, e_mm=0.15, a=2.0, b=1.75, materiau="Aluminium (brasé)", h_propane=3000),
)


def _fusion(base: dict, req: dict) -> dict:
    out = {}
    for k, v in base.items():
        if isinstance(v, dict):
            out[k] = _fusion(v, req.get(k) or {})
        else:
            r = req.get(k, v)
            out[k] = type(v)(r) if isinstance(v, (int, float)) and not isinstance(v, bool) else r
    return out


def candidats():
    lst = [("reference", "Référence tube-ailettes (simulateur)")]
    for s, d in SURFACES.items():
        lst.append((f"tpms:{s}:feuillet", f"{d['nom']} feuillet (2 fluides)"))
        lst.append((f"tpms:{s}:hybride", f"{d['nom']} hybride (tubes noyés)"))
    lst.append(("tubes_nus", "Tubes nus ronds fins"))
    return lst


def _echangeur(cid: str, p: dict, cote: str):
    c = p[cote]
    W, H, D = c["largeur_mm"] / 1e3, c["hauteur_mm"] / 1e3, c["profondeur_mm"] / 1e3
    if cid == "tubes_nus":
        t = p["tubes"]
        m = MATERIAUX[t["materiau"]]
        return EchangeurTubesNus(W, H, D, t["d_mm"] / 1e3, t["e_mm"] / 1e3, t["a"], t["b"],
                                 m["k"], m["rho"], t["h_propane"])
    _, surface, mode = cid.split(":")
    t = p["tpms"]
    m = MATERIAUX[t["materiau"]]
    return EchangeurTPMS(surface, W, H, D, t["phi_air"], t["Dh_mm"] / 1e3, m["k"], m["rho"], t["h_propane"],
                         mode=mode, phi_propane=t["phi_propane"], d_tube=t["d_tube_mm"] / 1e3,
                         e_tube=t["e_tube_mm"] / 1e3, pas_tube=t["pas_tube_mm"] / 1e3)


def _conditions(p, debits=True):
    return Conditions(mode=p["mode"], T_ext=p["T_ext"], T_int=p["T_int"], HR_ext=p["HR_ext"], HR_int=p["HR_int"],
                      debit_int=p["int"]["debit_m3h"] if debits else None,
                      debit_ext=p["ext"]["debit_m3h"] if debits else None)


def evaluer(cid: str, p: dict) -> dict:
    Q = p["puissance_kW"] * 1e3
    if cid == "reference":
        pac = PompeAChaleur(Conception(technologie="Tube-ailettes Cu/Al"))
        e, alerte = _resoudre_puissance(pac, _conditions(p, debits=False), Q)
        return dict(ok=bool(e.ok), source="modèle UA nominal du simulateur", alerte_f=alerte,
                    COP=e.COP, Te=e.Te, Tc=e.Tc, freq=e.freq, P_comp=e.P_comp, P_vent=e.P_vent,
                    charge_g=e.charge_g, debit_int=e.debit_int, debit_ext=e.debit_ext, batteries=None,
                    alarmes=e.alarmes)
    if cid.startswith("tpms:") and correlation_air(cid.split(":")[1], p["tpms"]["phi_air"]) is None:
        return dict(ok=False, a_calibrer=True, source="aucune corrélation côté air : campagne CFD à lancer")
    echs = {c: _echangeur(cid, p, c) for c in ("int", "ext")}
    aero = {c: CircuitAir(echs[c], VentilateurRendementConstant("η", p["eta_vent"]), 1,
                          [{"nom": "grille", "K": 1.0, "A": echs[c].A_frontale}]) for c in ("int", "ext")}
    aero.update(nom=cid, exemple=False)
    conc = replace(Conception(), aeraulique=aero, technologie="Impression 3D métal (TPMS)",
                   multiplicateurs=dict(k_UA=1.0, k_vent=1.0, k_vol=1.0, k_givre=0.7),
                   debit_int_nom=p["int"]["debit_m3h"], debit_ext_nom=p["ext"]["debit_m3h"],
                   V_bat_int=echs["int"].volume_propane_L, V_bat_ext=echs["ext"].volume_propane_L)
    e, alerte = _resoudre_puissance(PompeAChaleur(conc), _conditions(p), Q)
    bat = {}
    for c in ("int", "ext"):
        T_in = p["T_int"] if c == "int" else p["T_ext"]
        UA, det, al = echs[c].UA(p[c]["debit_m3h"], T_in)
        a = e.aero.get(c, {})
        bat[c] = dict(UA=UA, dp=a.get("dp_total"), P_vent=a.get("P"), Re=det.get("Re"), h_air=det.get("h_air"),
                      eta_ailette=det.get("eta_ailette"), part_R_air=det.get("part_R_air"),
                      A_air=det.get("A_air"), volume_propane_L=echs[c].volume_propane_L,
                      masse_kg=echs[c].masse_kg, alertes=al,
                      u_face=p[c]["debit_m3h"] / 3600 / echs[c].A_frontale)
    src = ("VDI Heat Atlas (Gnielinski, Gaddis–Gnielinski)" if cid == "tubes_nus"
           else correlation_air(cid.split(":")[1], p["tpms"]["phi_air"])[2])
    return dict(ok=bool(e.ok), source=src, alerte_f=alerte, COP=e.COP, Te=e.Te, Tc=e.Tc, freq=e.freq,
                P_comp=e.P_comp, P_vent=e.P_vent, charge_g=e.charge_g, batteries=bat, alarmes=e.alarmes,
                debit_int=e.debit_int, debit_ext=e.debit_ext)


class Comparateur:
    def __init__(self):
        self._v = threading.Lock()
        self._etat = dict(statut="inactif", progression=0.0, message="", params=None, resultats=[])

    def lancer(self, req: dict) -> bool:
        with self._v:
            if self._etat["statut"] == "en cours":
                return False
            p = _fusion(DEFAUT, req or {})
            choix = req.get("candidats") or [c for c, _ in candidats()]
            self._etat = dict(statut="en cours", progression=0.0, message="", params=p, resultats=[])
        threading.Thread(target=self._executer, args=(p, choix), daemon=True).start()
        return True

    def _executer(self, p, choix):
        noms = dict(candidats())
        for i, cid in enumerate(choix):
            with self._v:
                self._etat.update(progression=i / len(choix), message=noms.get(cid, cid))
            try:
                r = evaluer(cid, p)
            except Exception as exc:  # un candidat qui échoue ne bloque pas les autres
                r = dict(ok=False, source=f"échec : {exc}", trace=traceback.format_exc(limit=2))
            with self._v:
                self._etat["resultats"].append(dict(r, id=cid, nom=noms.get(cid, cid)))
        with self._v:
            self._etat.update(statut="terminé", progression=1.0, message="")

    def instantane(self) -> dict:
        with self._v:
            return dict(self._etat, resultats=list(self._etat["resultats"]))


def hypotheses_ui() -> dict:
    return dict(defaut=DEFAUT, candidats=candidats(),
                materiaux_tpms=[k for k, v in MATERIAUX.items() if v["impression"]],
                materiaux_tubes=[k for k, v in MATERIAUX.items() if not v["impression"]])
