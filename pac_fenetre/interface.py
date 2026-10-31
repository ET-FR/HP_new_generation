"""
Interface temps réel du simulateur de pompe à chaleur de fenêtre R290.

Fenêtre matplotlib :
  * schéma animé du circuit (le débit des points suit le débit massique réel),
  * diagramme P-h du propane avec le cycle courant,
  * courbe COP = f(T extérieure) pour la technologie choisie et la référence,
  * historique temps réel (COP, puissances, fréquence inverter),
  * panneau de valeurs, curseurs de charge et sélecteurs.
"""

from __future__ import annotations

import math
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle, Polygon, Rectangle
from matplotlib.widgets import RadioButtons, Slider

from .physique import (TECHNO_REFERENCE, TECHNOLOGIES, Conception, Conditions,
                       PompeAChaleur, Propane)

COUL = dict(refoul="#d62728", cond="#e8590c", liquide="#f59f00",
            diphasique="#1c7ed6", evap="#4dabf7", aspiration="#15aabf")

# Circuit frigorifique : segments (polyligne, nature) dans le sens du fluide
CIRCUIT = {
    "chauffage": [
        ([(6.4, 5.0), (6.4, 7.8)], "refoul"),
        ([(6.4, 7.8), (6.2, 8.2), (1.6, 8.2), (1.6, 7.0)], "refoul"),
        ([(1.6, 7.0), (1.6, 3.0)], "cond"),
        ([(1.6, 3.0), (1.6, 1.2), (6.3, 1.2)], "liquide"),
        ([(6.3, 1.2), (8.4, 1.2), (8.4, 3.0)], "diphasique"),
        ([(8.4, 3.0), (8.4, 7.0)], "evap"),
        ([(8.4, 7.0), (8.4, 8.2), (6.8, 8.2), (6.6, 7.8), (6.6, 5.0)], "aspiration"),
    ],
    "clim": [
        ([(6.4, 5.0), (6.4, 7.8), (6.8, 8.2), (8.4, 8.2), (8.4, 7.0)], "refoul"),
        ([(8.4, 7.0), (8.4, 3.0)], "cond"),
        ([(8.4, 3.0), (8.4, 1.2), (6.3, 1.2)], "liquide"),
        ([(6.3, 1.2), (1.6, 1.2), (1.6, 3.0)], "diphasique"),
        ([(1.6, 3.0), (1.6, 7.0)], "evap"),
        ([(1.6, 7.0), (1.6, 8.2), (6.2, 8.2), (6.6, 7.8), (6.6, 5.0)], "aspiration"),
    ],
}

CONDITIONS_TYPES = {  # conditions de référence proposées au changement de mode
    "chauffage": dict(T_ext=7.0, T_int=20.0, HR_ext=0.87, HR_int=0.50),
    "clim": dict(T_ext=35.0, T_int=27.0, HR_ext=0.40, HR_int=0.47),
}


def _discretiser(segments, n=90):
    """Points régulièrement espacés le long du circuit + nature de chaque point."""
    pts, kinds, longueurs = [], [], []
    for poly, kind in segments:
        for a, b in zip(poly[:-1], poly[1:]):
            L = math.dist(a, b)
            pts.append((a, b))
            kinds.append(kind)
            longueurs.append(L)
    cum = np.concatenate([[0.0], np.cumsum(longueurs)])
    return pts, kinds, cum


def _position(circuit, s):
    pts, kinds, cum = circuit
    s = s % cum[-1]
    i = min(int(np.searchsorted(cum, s, side="right") - 1), len(pts) - 1)
    (ax, ay), (bx, by) = pts[i]
    L = cum[i + 1] - cum[i]
    x = (s - cum[i]) / L if L > 0 else 0.0
    return ax + x * (bx - ax), ay + x * (by - ay), kinds[i]


class Simulateur:
    N_POINTS_FLUX = 70
    RAMPE_HZ_S = 1.5        # vitesse de variation de l'inverter
    DELAI_INVERSION = 120.0  # s, égalisation des pressions avant redémarrage
    T_EXT_COURBE = {"chauffage": np.linspace(-20, 18, 14), "clim": np.linspace(18, 46, 13)}

    def __init__(self):
        self.fluide = Propane()
        self.pac = {t: PompeAChaleur(Conception(technologie=t), self.fluide) for t in TECHNOLOGIES}
        self.mode = "chauffage"
        self.techno = "Impression 3D métal (TPMS)"
        self.controle = "Inverter auto (suit la charge)"
        self.t_sim = 0.0
        self.f_reel = 0.0
        self.f_cible = 0.0
        self.PLR, self.statut, self.besoin = 1.0, "", 0.0
        self.delai = 10.0
        self.phase_flux = 0.0
        self.dirty = True
        self._cache_cle, self._cache_etat = None, None
        self.historique = deque(maxlen=900)
        self.courbe = {}
        self._courbe_iter = None
        self._construire_figure()

    # ------------------------------------------------------------------ figure
    def _construire_figure(self):
        plt.rcParams.update({"font.size": 8.5})
        self.fig = fig = plt.figure(figsize=(16.5, 10))
        fig.canvas.manager.set_window_title("Simulateur PAC de fenêtre R290")
        fig.suptitle("Pompe à chaleur réversible de fenêtre au propane (R290) : simulation physique temps réel",
                     fontsize=12, fontweight="bold", y=0.993)

        self.ax_sch = fig.add_axes([0.01, 0.53, 0.33, 0.43])
        self.ax_ph = fig.add_axes([0.39, 0.555, 0.29, 0.375])
        self.ax_cop = fig.add_axes([0.045, 0.30, 0.285, 0.18])
        self.ax_hist = fig.add_axes([0.39, 0.30, 0.255, 0.18])
        self.ax_hist2 = self.ax_hist.twinx()
        self.ax_txt = fig.add_axes([0.705, 0.255, 0.29, 0.70])
        self.ax_txt.axis("off")

        self._init_schema()
        self._init_ph()
        self._init_cop()
        self._init_hist()
        self.txt = self.ax_txt.text(0.0, 1.0, "", va="top", ha="left", family="monospace",
                                    fontsize=8.3, transform=self.ax_txt.transAxes)
        self._init_widgets()

    def _init_schema(self):
        ax = self.ax_sch
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("auto")
        ax.axis("off")
        ax.add_patch(Rectangle((4.65, 0.2), 0.35, 9.2, color="#adb5bd", alpha=0.6, zorder=1))
        ax.text(4.825, 4.8, "FENÊTRE / KIT D'ÉTANCHÉITÉ", rotation=90, ha="center", va="center",
                fontsize=7, color="#343a40", zorder=2)
        ax.text(2.3, 9.9, "INTÉRIEUR", ha="center", fontweight="bold")
        ax.text(7.4, 9.9, "EXTÉRIEUR", ha="center", fontweight="bold")
        for segs in CIRCUIT["chauffage"]:
            xs, ys = zip(*segs[0])
            ax.plot(xs, ys, color="#ced4da", lw=4, zorder=2, solid_capstyle="round")
        ax.annotate("", xy=(3.4, 5.0), xytext=(0.15, 5.0),
                    arrowprops=dict(arrowstyle="-|>", color="#868e96", lw=2, alpha=0.6), zorder=1)
        ax.annotate("", xy=(9.95, 5.0), xytext=(7.25, 5.0),
                    arrowprops=dict(arrowstyle="-|>", color="#868e96", lw=2, alpha=0.6), zorder=1)
        self.bat_int = Rectangle((1.1, 3.0), 1.0, 4.0, ec="k", lw=1.2, zorder=3)
        self.bat_ext = Rectangle((7.9, 3.0), 1.0, 4.0, ec="k", lw=1.2, zorder=3)
        ax.add_patch(self.bat_int)
        ax.add_patch(self.bat_ext)
        ax.add_patch(Circle((0.55, 5.0), 0.35, fc="white", ec="k", zorder=3))
        ax.add_patch(Circle((9.45, 5.0), 0.35, fc="white", ec="k", zorder=3))
        ax.text(0.55, 5.0, "V", ha="center", va="center", zorder=4, fontsize=7)
        ax.text(9.45, 5.0, "V", ha="center", va="center", zorder=4, fontsize=7)
        self.comp = Circle((6.5, 4.5), 0.5, fc="#e9ecef", ec="k", lw=1.5, zorder=3)
        ax.add_patch(self.comp)
        ax.add_patch(Rectangle((6.1, 7.75), 0.8, 0.5, fc="#fff3bf", ec="k", zorder=3))
        ax.text(6.5, 8.0, "V4V", ha="center", va="center", fontsize=6.5, zorder=4)
        ax.add_patch(Polygon([(6.05, 0.95), (6.05, 1.45), (6.55, 0.95), (6.55, 1.45)],
                             closed=True, fc="#dee2e6", ec="k", zorder=3))
        ax.text(6.3, 0.55, "EEV", ha="center", fontsize=7)

        self.lbl_comp = ax.text(6.5, 3.55, "", ha="center", va="top", fontsize=7.5, zorder=5)
        self.lbl_hp = ax.text(5.15, 7.75, "", ha="left", va="top", fontsize=7.3,
                              color=COUL["refoul"], zorder=5)
        self.lbl_bp = ax.text(8.0, 0.55, "", ha="left", va="center", fontsize=7.5,
                              color=COUL["diphasique"], zorder=5)
        self.lbl_refoul = ax.text(6.3, 6.2, "", ha="right", fontsize=7, color=COUL["refoul"], zorder=5)
        self.lbl_bint = ax.text(2.3, 9.6, "", ha="center", va="top", fontsize=7.3, zorder=5)
        self.lbl_bext = ax.text(7.6, 9.6, "", ha="center", va="top", fontsize=7.3, zorder=5)
        self.lbl_air_int = ax.text(0.05, 2.6, "", ha="left", va="top", fontsize=7.3, zorder=5)
        self.lbl_air_ext = ax.text(9.95, 2.6, "", ha="right", va="top", fontsize=7.3, zorder=5)
        self.flux = ax.scatter(np.zeros(self.N_POINTS_FLUX), np.zeros(self.N_POINTS_FLUX),
                               s=16, zorder=6, edgecolors="none")
        self.circuits = {m: _discretiser(s) for m, s in CIRCUIT.items()}
        self.cmap = plt.get_cmap("coolwarm")

    def _init_ph(self):
        ax = self.ax_ph
        fl = self.fluide
        T = np.linspace(-42, fl.Tcrit - 0.3, 160)
        hl, hv, p = [], [], []
        for t in T:
            pl, h_l, _, _ = fl.sat(t, 0.0)
            _, h_v, _, _ = fl.sat(t, 1.0)
            hl.append(h_l / 1e3)
            hv.append(h_v / 1e3)
            p.append(pl / 1e5)
        ax.plot(hl, p, color="k", lw=1)
        ax.plot(hv, p, color="k", lw=1)
        ax.plot([hl[-1], hv[-1]], [p[-1], p[-1]], color="k", lw=1)
        for t in (-20, 0, 20, 40, 60):
            pl = fl.psat(t) / 1e5
            ax.plot([30, 760], [pl, pl], color="#dee2e6", lw=0.6, zorder=0)
            ax.text(35, pl * 1.03, f"{t} °C", fontsize=6.5, color="#868e96")
        ax.set_yscale("log")
        ax.set_xlim(30, 760)
        ax.set_ylim(0.9, 45)
        ax.set_xlabel("Enthalpie h (kJ/kg)")
        ax.set_ylabel("Pression p (bar)")
        ax.set_title("Diagramme P-h du propane (R290) et cycle courant")
        ax.grid(True, which="both", alpha=0.2)
        self.ph_ligne, = ax.plot([], [], color=COUL["refoul"], lw=2.2, marker="o", ms=0)
        self.ph_fill = None
        self.ph_pts = ax.scatter([], [], s=24, c="k", zorder=5)
        self.ph_lbl = [ax.text(0, 0, str(i + 1), fontsize=8, fontweight="bold") for i in range(4)]

    def _init_cop(self):
        ax = self.ax_cop
        ax.set_title("COP effectif en fonction de T extérieure (T int. fixée)")
        ax.set_xlabel("T extérieure (°C)")
        ax.grid(alpha=0.3)
        self.l_cop_ref, = ax.plot([], [], color="#868e96", lw=1.8, label=TECHNO_REFERENCE)
        self.l_cop, = ax.plot([], [], color="#1c7ed6", lw=2.2, label="Technologie choisie")
        self.l_cop_inst, = ax.plot([], [], color="#1c7ed6", lw=1, ls="--",
                                   label="choisie, sans dégivrage")
        self.pt_cop, = ax.plot([], [], "o", color="#e03131", ms=8, zorder=5, label="point courant")
        ax.legend(fontsize=6.8, loc="best")

    def _init_hist(self):
        ax, ax2 = self.ax_hist, self.ax_hist2
        ax.set_title("Historique temps réel")
        ax.set_xlabel("Temps simulé (min)")
        ax.set_ylabel("COP effectif", color="#1c7ed6")
        ax2.set_ylabel("Puissance (kW) / fréquence (Hz/100)")
        ax.grid(alpha=0.3)
        self.h_cop, = ax.plot([], [], color="#1c7ed6", lw=1.8, label="COP")
        self.h_q, = ax2.plot([], [], color="#e8590c", lw=1.4, label="Q utile kW")
        self.h_p, = ax2.plot([], [], color="#5f3dc4", lw=1.4, label="P élec kW")
        self.h_f, = ax2.plot([], [], color="#868e96", lw=1, ls=":", label="f /100")
        ax2.legend([self.h_cop, self.h_q, self.h_p, self.h_f],
                   ["COP effectif", "Q utile kW", "P élec kW", "f /100"], fontsize=6.5, loc="upper left")

    def _init_widgets(self):
        fig = self.fig
        defs = [
            ("T_ext", "T extérieure (°C)", -20, 46, 7.0),
            ("T_int", "T intérieure (°C)", 10, 32, 20.0),
            ("HR_ext", "HR extérieure (%)", 20, 100, 87.0),
            ("HR_int", "HR intérieure (%)", 20, 90, 50.0),
            ("H", "Déperditions pièce H (W/K)", 20, 200, 90.0),
            ("apports", "Apports internes/solaires (W)", 0, 1500, 300.0),
            ("freq", "Fréquence manuelle (Hz)", 15, 110, 60.0),
            ("vitesse", "Accélération du temps (x)", 1, 120, 20.0),
        ]
        self.sl = {}
        for i, (k, lbl, a, b, v) in enumerate(defs):
            ax = fig.add_axes([0.16, 0.215 - i * 0.027, 0.27, 0.018])
            s = Slider(ax, lbl, a, b, valinit=v, valstep=0.5 if k in ("T_ext", "T_int") else None)
            s.on_changed(self._sur_changement)
            self.sl[k] = s

        ax_m = fig.add_axes([0.465, 0.13, 0.12, 0.09])
        ax_m.set_title("Mode (vanne 4 voies)", fontsize=8)
        self.rb_mode = RadioButtons(ax_m, ["Chauffage", "Climatisation"])
        self.rb_mode.on_clicked(self._sur_mode)

        ax_c = fig.add_axes([0.465, 0.02, 0.12, 0.09])
        ax_c.set_title("Contrôle compresseur", fontsize=8)
        self.rb_ctrl = RadioButtons(ax_c, ["Inverter auto (suit la charge)", "Fréquence manuelle"])
        self.rb_ctrl.on_clicked(self._sur_controle)

        ax_t = fig.add_axes([0.60, 0.02, 0.155, 0.20])
        ax_t.set_title("Technologie des échangeurs", fontsize=8)
        noms = list(TECHNOLOGIES)
        self.rb_tech = RadioButtons(ax_t, noms, active=noms.index(self.techno))
        self.rb_tech.on_clicked(self._sur_techno)

        ax_n = fig.add_axes([0.77, 0.02, 0.225, 0.20])
        ax_n.axis("off")
        ax_n.text(0, 1, self._texte_hypotheses(), va="top", fontsize=6.8, color="#495057",
                  transform=ax_n.transAxes)

    def _texte_hypotheses(self):
        lignes = ["Hypothèses technologies (à valider) :"]
        for k, v in TECHNOLOGIES.items():
            lignes.append(f" {k}")
            lignes.append(f"    UA x{v['k_UA']:.2f}  vent. x{v['k_vent']:.2f}  "
                          f"vol. x{v['k_vol']:.2f}  givre x{v['k_givre']:.2f}")
        lignes += ["", "Compresseur rotatif BLDC 16 cm3, 15-110 Hz,",
                   "EEV surchauffe 5 K, sous-refroid. 4 K.",
                   "Ventilateurs EC asservis à la fréquence."]
        return "\n".join(lignes)

    # --------------------------------------------------------------- callbacks
    def _sur_changement(self, _val):
        self.dirty = True

    def _sur_mode(self, label):
        nouveau = "chauffage" if label == "Chauffage" else "clim"
        if nouveau == self.mode:
            return
        self.mode = nouveau
        for k, v in CONDITIONS_TYPES[nouveau].items():
            self.sl[k].set_val(v * 100 if k.startswith("HR") else v)
        self.f_reel = 0.0
        self.delai = self.DELAI_INVERSION
        self.dirty = True

    def _sur_controle(self, label):
        self.controle = label
        self.dirty = True

    def _sur_techno(self, label):
        self.techno = label
        self.dirty = True

    # --------------------------------------------------------------- calculs
    def conditions(self, f=None) -> Conditions:
        s = self.sl
        return Conditions(mode=self.mode, T_ext=s["T_ext"].val, T_int=s["T_int"].val,
                          HR_ext=s["HR_ext"].val / 100, HR_int=s["HR_int"].val / 100,
                          freq=self.f_reel if f is None else f)

    @property
    def auto(self):
        return self.controle.startswith("Inverter")

    def _consigne(self, pac, cond):
        """(f, PLR, statut, besoin) pour une PAC et des conditions données."""
        besoin = pac.besoin(cond, self.sl["H"].val, self.sl["apports"].val)
        if self.auto:
            f, PLR, statut = pac.regulation(cond, besoin)
        else:
            f, PLR, statut = self.sl["freq"].val, 1.0, "manuel"
        return f, PLR, statut, besoin

    def _maj_cible(self):
        pac = self.pac[self.techno]
        self.f_cible, self.PLR, self.statut, self.besoin = self._consigne(pac, self.conditions())
        self.courbe = {}
        self._courbe_iter = self._generer_courbe()
        self.dirty = False

    def _generer_courbe(self):
        cond0 = self.conditions()
        refs = [self.techno] + ([TECHNO_REFERENCE] if self.techno != TECHNO_REFERENCE else [])
        for T in self.T_EXT_COURBE[self.mode]:
            for t in refs:
                pac = self.pac[t]
                cond = Conditions(**{**cond0.__dict__, "T_ext": float(T)})
                f, PLR, statut, _ = self._consigne(pac, cond)
                if f <= 0:
                    val = (np.nan, np.nan)
                else:
                    e = pac.resoudre(cond, f)
                    k = pac.facteur_cyclage(PLR)
                    val = (e.COP_integre * k, e.COP * k) if e.ok else (np.nan, np.nan)
                self.courbe.setdefault(t, []).append((T, *val))
            yield

    def _etat(self, f):
        pac = self.pac[self.techno]
        cond = self.conditions(f)
        cle = (self.techno, tuple(round(v, 3) for v in cond.__dict__.values() if isinstance(v, float)),
               self.mode)
        if cle != self._cache_cle:
            self._cache_cle, self._cache_etat = cle, pac.resoudre(cond, f)
        return self._cache_etat

    # --------------------------------------------------------------- boucle
    def pas(self, _frame=None, dt_reel=0.1):
        if self.dirty:
            self._maj_cible()
        if self._courbe_iter is not None:
            try:
                next(self._courbe_iter)
            except StopIteration:
                self._courbe_iter = None

        dt = dt_reel * self.sl["vitesse"].val
        self.t_sim += dt
        c = self.pac[self.techno].c
        if self.delai > 0:
            self.delai -= dt
            self.f_reel = 0.0
        elif self.f_cible <= 0:
            self.f_reel = 0.0
        else:
            if self.f_reel < c.f_min:
                self.f_reel = c.f_min  # démarrage
            df = self.f_cible - self.f_reel
            pas_max = self.RAMPE_HZ_S * dt
            self.f_reel += max(-pas_max, min(pas_max, df))

        e = self._etat(self.f_reel) if self.f_reel > 0 else None
        self._afficher(e)
        return []

    # --------------------------------------------------------------- affichage
    def _afficher(self, e):
        marche = e is not None and e.ok
        k_cyc = self.pac[self.techno].facteur_cyclage(self.PLR) if marche else 1.0
        cop_eff = e.COP_integre * k_cyc if marche else np.nan
        q_eff = e.Q_integre * self.PLR if marche else 0.0
        p_eff = (q_eff / cop_eff) if marche and cop_eff > 0 else 0.0
        self.historique.append((self.t_sim / 60, cop_eff, q_eff / 1e3, p_eff / 1e3, self.f_reel / 100))

        self._afficher_schema(e, marche)
        self._afficher_ph(e, marche)
        self._afficher_cop(cop_eff)
        self._afficher_hist()
        self.txt.set_text(self._texte(e, marche, cop_eff, q_eff, p_eff, k_cyc))

    def _afficher_schema(self, e, marche):
        circ = self.circuits[self.mode]
        if marche:
            self.phase_flux += e.m_dot * 1e3 * 0.012 * self.sl["vitesse"].val ** 0.5
        L = circ[2][-1]
        xs, ys, cs = [], [], []
        for i in range(self.N_POINTS_FLUX):
            x, y, kind = _position(circ, (i / self.N_POINTS_FLUX) * L + self.phase_flux)
            xs.append(x)
            ys.append(y)
            cs.append(COUL[kind] if marche else "#adb5bd")
        self.flux.set_offsets(np.c_[xs, ys])
        self.flux.set_color(cs)

        def couleur(T):
            return self.cmap(np.clip((T + 25) / 95, 0, 1))

        cond = self.conditions()
        if marche:
            T_bint = e.Tc if self.mode == "chauffage" else e.Te
            T_bext = e.Te if self.mode == "chauffage" else e.Tc
            self.bat_int.set_facecolor(couleur(T_bint))
            self.bat_ext.set_facecolor(couleur(T_bext))
            self.comp.set_facecolor("#ffc9c9")
            role_i, role_e = (("CONDENSEUR", "ÉVAPORATEUR") if self.mode == "chauffage"
                              else ("ÉVAPORATEUR", "CONDENSEUR"))
            self.lbl_bint.set_text(f"Batterie int. : {role_i}\nT réfrigérant {T_bint:.1f} °C")
            self.lbl_bext.set_text(f"Batterie ext. : {role_e}\nT réfrigérant {T_bext:.1f} °C"
                                   + ("  GIVRAGE" if e.givre else ""))
            self.lbl_comp.set_text(f"Compresseur\n{e.freq:.0f} Hz  {e.P_comp:.0f} W\n"
                                   f"{e.m_dot * 1e3:.1f} g/s")
            self.lbl_hp.set_text(f"HP {e.p_hp / 1e5:.1f} bar\n({e.Tc:.1f} °C sat.)")
            self.lbl_bp.set_text(f"BP {e.p_bp / 1e5:.2f} bar\n({e.Te:.1f} °C sat.)")
            self.lbl_refoul.set_text(f"refoul.\n{e.T_refoul:.0f} °C")
            self.lbl_air_int.set_text(f"Air pièce {e.debit_int:.0f} m³/h\n"
                                      f"{cond.T_int:.1f} → {e.T_air_int_out:.1f} °C")
            self.lbl_air_ext.set_text(f"Air ext. {e.debit_ext:.0f} m³/h\n"
                                      f"{cond.T_ext:.1f} → {e.T_air_ext_out:.1f} °C")
        else:
            for p in (self.bat_int, self.bat_ext):
                p.set_facecolor("#f1f3f5")
            self.comp.set_facecolor("#e9ecef")
            msg = ("Inversion V4V : égalisation\ndes pressions" if self.delai > 0 else "Arrêt")
            self.lbl_comp.set_text(f"Compresseur\n{msg}")
            for lbl in (self.lbl_hp, self.lbl_bp, self.lbl_refoul, self.lbl_bint, self.lbl_bext):
                lbl.set_text("")
            self.lbl_air_int.set_text(f"Air pièce {cond.T_int:.1f} °C")
            self.lbl_air_ext.set_text(f"Air ext. {cond.T_ext:.1f} °C")

    def _afficher_ph(self, e, marche):
        if self.ph_fill is not None:
            self.ph_fill.remove()
            self.ph_fill = None
        if not marche:
            self.ph_ligne.set_data([], [])
            self.ph_pts.set_offsets(np.empty((0, 2)))
            for t in self.ph_lbl:
                t.set_text("")
            return
        h, p = zip(*e.points_ph)
        self.ph_ligne.set_data(h + (h[0],), p + (p[0],))
        self.ph_fill = self.ax_ph.fill(h, p, color="#ffe3e3", alpha=0.6, zorder=0)[0]
        cles = [e.points_ph[0], e.points_ph[5], e.points_ph[9], e.points_ph[10]]
        self.ph_pts.set_offsets(cles)
        decal = [(-8, 0.82), (8, 1.05), (-24, 1.05), (-24, 0.82)]
        for i, (t, (hh, pp), (dx, fy)) in enumerate(zip(self.ph_lbl, cles, decal)):
            t.set_position((hh + dx, pp * fy))
            t.set_text(str(i + 1))

    def _afficher_cop(self, cop_eff):
        ax = self.ax_cop
        ref = self.courbe.get(TECHNO_REFERENCE, []) if self.techno != TECHNO_REFERENCE else []
        cur = self.courbe.get(self.techno, [])
        if cur:
            T, ci, cinst = zip(*cur)
            self.l_cop.set_data(T, ci)
            self.l_cop_inst.set_data(T, cinst if self.mode == "chauffage" else [np.nan] * len(T))
        else:
            self.l_cop.set_data([], [])
            self.l_cop_inst.set_data([], [])
        self.l_cop_inst.set_label("choisie, sans dégivrage" if self.mode == "chauffage" else "_")
        self.l_cop.set_label(self.techno)
        if ref:
            T, ci, _ = zip(*ref)
            self.l_cop_ref.set_data(T, ci)
        else:
            self.l_cop_ref.set_data([], [])
        T_ext = self.sl["T_ext"].val
        self.pt_cop.set_data([T_ext], [cop_eff])
        xs = self.T_EXT_COURBE[self.mode]
        ax.set_xlim(min(xs[0], T_ext) - 1, max(xs[-1], T_ext) + 1)
        vals = [v for line in (cur, ref) for (_, a, b) in line for v in (a, b) if np.isfinite(v)]
        if np.isfinite(cop_eff):
            vals.append(cop_eff)
        ymax = max(vals) if vals else 6
        ax.set_ylim(0, min(max(4, ymax * 1.15), 12))
        ax.set_ylabel("COP" if self.mode == "chauffage" else "EER")
        ax.legend(fontsize=6.8, loc="best")

    def _afficher_hist(self):
        if len(self.historique) < 2:
            return
        t, cop, q, p, f = (np.array(v, dtype=float) for v in zip(*self.historique))
        self.h_cop.set_data(t, cop)
        self.h_q.set_data(t, q)
        self.h_p.set_data(t, p)
        self.h_f.set_data(t, f)
        self.ax_hist.set_xlim(t[0], max(t[-1], t[0] + 1))
        c_ok = cop[np.isfinite(cop)]
        self.ax_hist.set_ylim(0, max(4, (c_ok.max() if c_ok.size else 4) * 1.15))
        m = np.nanmax(np.r_[q, p, f, 1.0])
        self.ax_hist2.set_ylim(0, m * 1.15)

    def _texte(self, e, marche, cop_eff, q_eff, p_eff, k_cyc):
        c = self.pac[self.techno].c
        m_max, m1 = self.pac[self.techno].charge_max_iec()
        mode = "CHAUFFAGE" if self.mode == "chauffage" else "CLIMATISATION"
        L = [f"MODE {mode}   t = {self.t_sim / 60:6.1f} min",
             f"Échangeurs : {self.techno}",
             f"Contrôle   : {'inverter auto' if self.auto else 'manuel'}",
             "",
             "BESOIN DE LA PIÈCE (50 m² max)",
             f" Besoin sensible     {self.besoin / 1e3:6.2f} kW",
             f" Statut régulation   {self.statut}",
             f" Fréquence  {self.f_reel:5.1f} Hz (cible {self.f_cible:5.1f})",
             f" Taux de charge PLR  {self.PLR:6.2f}   (cyclage x{k_cyc:.3f})"]
        if not marche:
            L += ["", "Compresseur à l'arrêt."]
            if e is not None and not e.ok:
                L.append(e.message)
            L += ["", f"Charge max IEC 60335-2-40 : {m_max:.0f} g", f"(m1 = {m1:.0f} g)"]
            return "\n".join(L)
        carnot = f"{e.COP_carnot:6.1f}" if math.isfinite(e.COP_carnot) and e.COP_carnot < 99 else "  >99"
        ex = f"{e.eta_exergie * 100:5.1f} %" if math.isfinite(e.eta_exergie) else "   n/a"
        nom = "COP" if self.mode == "chauffage" else "EER"
        L += ["",
              "CYCLE R290",
              f" T évap {e.Te:6.1f} °C   BP {e.p_bp / 1e5:5.2f} bar",
              f" T cond {e.Tc:6.1f} °C   HP {e.p_hp / 1e5:5.2f} bar",
              f" Taux compression    {e.PR:6.2f}",
              f" T refoulement       {e.T_refoul:6.1f} °C",
              f" Débit massique      {e.m_dot * 1e3:6.2f} g/s",
              f" η vol {e.eta_v:4.2f}  η is {e.eta_is:4.2f}  η mot {e.eta_mot:4.2f}",
              "",
              "PUISSANCES (instantanées)",
              f" Q condenseur        {e.Q_cond / 1e3:6.2f} kW",
              f" Q évaporateur       {e.Q_evap / 1e3:6.2f} kW",
              f" dont latent         {e.Q_lat / 1e3:6.2f} kW",
              f" P compresseur       {e.P_comp:6.0f} W",
              f" P ventilateurs      {e.P_vent:6.0f} W",
              f" P totale            {e.P_tot:6.0f} W",
              "",
              "PERFORMANCES",
              f" {nom} cycle (arbre)    {e.COP_cycle:6.2f}",
              f" {nom} unité            {e.COP:6.2f}",
              f" {nom} effectif         {cop_eff:6.2f}  (dégivrage+cyclage)",
              f" Q effectif          {q_eff / 1e3:6.2f} kW,  P {p_eff:5.0f} W",
              f" {nom} Carnot (air)     {carnot}",
              f" Rendement exergét.  {ex}",
              ""]
        if self.mode == "chauffage":
            L.append(f" Givrage : {'OUI' if e.givre else 'non'}"
                     + (f"  ({e.eau_kg_h:.2f} kg/h, dégivrage {e.frac_degivrage * 100:.0f} % du temps)"
                        if e.givre else ""))
        else:
            shr = e.Q_sensible / e.Q_utile if e.Q_utile > 0 else 1
            L.append(f" Déshumidif. {e.eau_kg_h:5.2f} L/h   SHR {shr:4.2f}")
        L += ["",
              "SÉCURITÉ PROPANE",
              f" Charge estimée      {e.charge_g:6.0f} g",
              f" Max IEC 60335-2-40  {m_max:6.0f} g (h0={c.h0_installation} m, {c.surface_piece:.0f} m²)",
              f" Seuil m1 = 4×LFL    {m1:6.0f} g",
              ]
        if e.charge_g > m_max:
            L.append(" !! CHARGE SUPÉRIEURE À LA LIMITE")
        for a in e.alarmes:
            L.append(f" !! {a}")
        if self.statut == "capacité insuffisante":
            L.append(" !! Capacité insuffisante pour le besoin")
        return "\n".join(L)

    # --------------------------------------------------------------- lancement
    def lancer(self):
        self.anim = FuncAnimation(self.fig, self.pas, interval=100, cache_frame_data=False)
        plt.show()

    def capture(self, chemin, n_pas=80):
        for _ in range(n_pas):
            self.pas()
        while self._courbe_iter is not None:
            self.pas(dt_reel=0.0)
        self.fig.savefig(chemin, dpi=110)
