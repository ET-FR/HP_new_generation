"""Génère conception_ventilateur/ventilateurs.html : recherches, figures et résultats du dossier.

Les figures (matplotlib, SVG) sont intégrées dans la page : un seul fichier à ouvrir ou à envoyer.
Lancer : .venv/bin/python conception_ventilateur/outils/fiche_ventilateurs.py
"""
from __future__ import annotations

import io
import subprocess
import json
import math
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402
import numpy as np  # noqa: E402

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import predimensionnement as pd  # noqa: E402

RACINE = ICI.parents[1]
SORTIE = ICI.parent / "ventilateurs.html"
ANIMATION = ICI.parent / "animation_ventilateur.html"
MOYEU = 0.35
C = dict(bleu="#1c7ed6", orange="#e8590c", vert="#2b8a3e", gris="#868e96", violet="#7048e8", rouge="#c92a2a")

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "svg.fonttype": "none",
                     "font.family": "DejaVu Sans"})


def fr(x, n=1):
    s = f"{x:,.{n}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


def svg(fig):
    b = io.StringIO()
    fig.savefig(b, format="svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    t = b.getvalue()
    return t[t.index("<svg"):]


def dp_total(q_h, D, recup=0.0):
    a = math.pi / 4 * D**2 * (1 - MOYEU**2)
    c = q_h / 3600 / a
    return pd.DP_BATTERIE + (1 - recup) * 0.5 * pd.RHO * c**2, c


# ---------------------------------------------------------------- figures
def fig_cop():
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    pv = np.linspace(20, 100, 81)
    for cop, col in zip(pd.COP_CIBLES, (C["gris"], C["bleu"])):
        p_tot = pd.Q_UTILE / cop
        p_comp = p_tot - 76
        ax.plot(pv, pd.Q_UTILE / (p_comp + pv), color=col, lw=2, label=f"COP {fr(cop, 0)} avec 76 W")
        ax.plot([76], [cop], "o", color=col)
        ax.plot([40], [pd.Q_UTILE / (p_comp + 40)], "s", color=C["vert"])
        ax.annotate(f"{fr(pd.Q_UTILE / (p_comp + 40), 2)}", (40, pd.Q_UTILE / (p_comp + 40)),
                    xytext=(6, 4), textcoords="offset points", color=C["vert"])
    ax.axvline(76, color=C["gris"], ls=":", lw=1)
    ax.axvline(40, color=C["vert"], ls=":", lw=1)
    ax.text(78, 4.6, "budget actuel\n76 W (η 0,30)", fontsize=8.5, color=C["gris"])
    ax.text(42, 4.6, "cible\n40 W", fontsize=8.5, color=C["vert"])
    ax.set_xlabel("Puissance des deux ventilateurs (W)")
    ax.set_ylabel("COP de l'unité")
    ax.legend(frameon=False, loc="upper right")
    return svg(fig)


def fig_perte_sortie():
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, (nom, q) in zip(axs, pd.POINTS.items()):
        D = np.linspace(0.15 if nom == "intérieur" else 0.25, 0.40 if nom == "intérieur" else 0.65, 100)
        pdyn = np.array([dp_total(q, d)[0] - pd.DP_BATTERIE for d in D])
        ax.fill_between(D * 1000, 0, pd.DP_BATTERIE, color=C["bleu"], alpha=0.15, lw=0)
        ax.fill_between(D * 1000, pd.DP_BATTERIE, pd.DP_BATTERIE + pdyn, color=C["orange"], alpha=0.25, lw=0)
        ax.plot(D * 1000, pd.DP_BATTERIE + pdyn, color=C["orange"], lw=2, label="+ perte de sortie ½ρc²")
        ax.plot(D * 1000, pd.DP_BATTERIE + 0.5 * pdyn, color=C["vert"], lw=2, ls="--",
                label="avec diffuseur (50 % récupéré)")
        ax.axhline(pd.DP_BATTERIE, color=C["bleu"], lw=2, label="batterie 25 Pa")
        ax.set_title(f"{nom.capitalize()} · {fr(q, 0)} m³/h", fontsize=10.5)
        ax.set_xlabel("Diamètre du rotor (mm), moyeu 0,35 D")
        ax.set_ylim(0, 110)
    axs[0].set_ylabel("Pression totale à fournir (Pa)")
    axs[1].legend(frameon=False, fontsize=8.5)
    return svg(fig)


def fig_puissance():
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
    for ax, (nom, q) in zip(axs, pd.POINTS.items()):
        D = np.linspace(0.18 if nom == "intérieur" else 0.28, 0.40 if nom == "intérieur" else 0.65, 100)
        dpt = np.array([dp_total(q, d, 0.5)[0] for d in D])
        for eta, col in ((0.30, C["gris"]), (0.45, C["orange"]), (0.60, C["vert"])):
            ax.plot(D * 1000, q / 3600 * dpt / eta, color=col, lw=2, label=f"η = {fr(eta, 2)}")
        u = np.sqrt(2 * dpt / (pd.RHO * 0.2))
        ax2 = ax.twinx()
        ax2.plot(D * 1000, u / (np.pi * D) * 60, color=C["violet"], lw=1.2, ls=":")
        ax2.set_ylabel("tr/min (ψ = 0,2)", color=C["violet"])
        ax2.tick_params(axis="y", colors=C["violet"])
        ax2.grid(False)
        ax2.spines["right"].set_visible(True)
        ax.set_title(f"{nom.capitalize()} · {fr(q, 0)} m³/h", fontsize=10.5)
        ax.set_xlabel("Diamètre du rotor (mm)")
        ax.set_ylim(0, None)
    axs[0].set_ylabel("Puissance électrique (W)")
    axs[0].legend(frameon=False, fontsize=8.5)
    fig.tight_layout()
    return svg(fig)


def fig_ebm():
    d = json.loads((RACINE / "ventilateurs" / "W1G200-EC87-20.json").read_text(encoding="utf-8"))
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.2))
    for c, col in zip(d["courbes"], (C["bleu"], C["orange"])):
        q, dp, p = map(np.array, (c["q_m3h"], c["dp_Pa"], c["P_W"]))
        axs[0].plot(q, dp, "o-", color=col, label=f"{c['n_tr_min']} tr/min")
        axs[1].plot(dp, q / 3600 * dp / p, "o-", color=col)
    axs[0].set_xlabel("Débit (m³/h)")
    axs[0].set_ylabel("Pression statique (Pa)")
    axs[0].legend(frameon=False)
    axs[1].axhline(0.30, color=C["gris"], ls=":", lw=1)
    axs[1].text(0.5, 0.31, "hypothèse du cahier des charges", fontsize=8.5, color=C["gris"])
    axs[1].axhspan(0.50, 0.60, color=C["vert"], alpha=0.15, lw=0)
    axs[1].text(0.5, 0.535, "cible du dossier", fontsize=8.5, color=C["vert"])
    axs[1].set_ylim(0, 0.65)
    axs[1].set_xlabel("Pression statique (Pa)")
    axs[1].set_ylabel("Rendement statique global")
    fig.suptitle(d["nom"] + " (EC axial 200 mm), valeurs fabricant", fontsize=10.5)
    fig.tight_layout()
    return svg(fig)


def _pale(ax, bord_attaque=None, bord_fuite=None, titre=""):
    """Pale vue en plan : corde 1, envergure 3 ; bords modifiables."""
    y = np.linspace(0, 3, 400)
    xa = np.zeros_like(y) if bord_attaque is None else bord_attaque(y)
    xf = np.ones_like(y) if bord_fuite is None else bord_fuite(y)
    pts = np.vstack([np.c_[xa, y], np.c_[xf, y][::-1]])
    ax.add_patch(Polygon(pts[:, ::-1], closed=True, fc="#d0ebff", ec=C["bleu"], lw=1.3))
    ax.annotate("air", xy=(1.5, -0.3), xytext=(1.5, -1.2), ha="center", va="top", fontsize=8.5, color=C["gris"],
                arrowprops=dict(arrowstyle="->", color=C["gris"]))
    ax.set_xlim(-0.2, 3.2)
    ax.set_ylim(-1.6, 1.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(titre, fontsize=9.5)


def fig_biomim():
    fig, axs = plt.subplots(2, 3, figsize=(9.6, 4.6))
    dents = lambda y: -0.18 * (1 - np.abs(((y * 6) % 1) * 2 - 1))  # noqa: E731
    _pale(axs[0, 0], titre="Pale de base (profil lisse)")
    _pale(axs[0, 1], bord_attaque=lambda y: 0.12 * (1 - np.cos(2 * np.pi * y / 0.5)) / 2 - 0.12,
          titre="Baleine à bosse :\ntubercules de bord d'attaque")
    _pale(axs[0, 2], bord_attaque=dents, titre="Chouette :\ndents de bord d'attaque")
    _pale(axs[1, 0], bord_fuite=lambda y: 1 + 0.18 * (1 - np.abs(((y * 8) % 1) * 2 - 1)),
          titre="Chouette / FE2owlet :\nbord de fuite dentelé")
    # coupe ondulée (libellule)
    ax = axs[1, 1]
    x = np.linspace(0, 3, 600)
    base = 0.25 * np.sin(np.pi * x / 3)
    ond = base + 0.09 * np.abs(np.sin(2 * np.pi * x / 0.45))
    ax.fill_between(x, base - 0.03, ond, color="#d0ebff", ec=C["bleu"])
    ax.set_xlim(-0.2, 3.2)
    ax.set_ylim(-0.6, 1.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Libellule :\nsection ondulée (coupe)", fontsize=9.5)
    # winglet
    ax = axs[1, 2]
    _pale(ax, titre="Oiseau : winglet / faucille\n(bout de pale relevé)")
    ax.add_patch(Polygon([[3.0, 0], [3.0, 1], [3.15, 0.9], [3.15, 0.25]], closed=True,
                         fc="#ffe8cc", ec=C["orange"], lw=1.3))
    fig.text(0.5, 0.01, "Vues en plan : bord d'attaque en bas (l'air arrive par la flèche), "
             "envergure horizontale.", ha="center", fontsize=8.5, color=C["gris"])
    return svg(fig)


def fig_moteurs():
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    data = [("Pôles ombragés", 15, 25, C["rouge"]), ("PSC (condensateur)", 30, 50, C["orange"]),
            ("EC / BLDC + FOC", 60, 90, C["vert"])]
    for i, (n, a, b, col) in enumerate(data):
        ax.barh(i, b - a, left=a, color=col, alpha=0.8, height=0.55)
        ax.text(b + 1.5, i, f"{a}–{b} %", va="center", fontsize=9)
    ax.set_yticks(range(len(data)), [d[0] for d in data])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Rendement du moteur de ventilateur (%)")
    ax.grid(axis="y", visible=False)
    return svg(fig)



# ---------------------------------------------------------------- modèle de l'animation (même code JS)
CAS_MODELE = {
    "W1G200 (banc, modèle)": dict(D=200, nu=0.40, N=5, corde=60, beta=32, n=1300, Qnom=320, dpNom=23, moteur="ec"),
    "Extérieur 300 mm": dict(D=300, nu=0.30, N=7, corde=70, beta=28, n=0, Qnom=2500, dpNom=25),
    "Extérieur 500 mm, base": dict(D=500, nu=0.30, N=7, corde=110, beta=28, n=0, Qnom=2500, dpNom=25),
    "Extérieur 500 mm, optimisé": dict(D=500, nu=0.30, N=7, corde=110, beta=28, n=0, Qnom=2500, dpNom=25,
                                       anneau="labyrinthe", diffuseur=True, stator=True, profil="basRe"),
    "Intérieur 280 mm, optimisé": dict(D=280, nu=0.32, N=7, corde=65, beta=28, n=0, Qnom=800, dpNom=25,
                                       anneau="labyrinthe", diffuseur=True, stator=True, profil="basRe"),
}
DEFAUT = dict(givre=1, faucille=20, jeu=2, anneau="non", diffuseur=False, stator=False,
              ba="lisse", bf="lisse", profil="plaque", moteur="foc")


def modele_animation(cas_modele=None):
    """Exécute le modèle JavaScript de l'animation (node) sur les cas types ; None si node manque."""
    html = ANIMATION.read_text(encoding="utf-8")
    js = html[html.index("// ===== MODELE (début) ====="):html.index("// ===== MODELE (fin) =====")]
    cas = {k: {**DEFAUT, **v} for k, v in (cas_modele or CAS_MODELE).items()}
    js += ("\nconst CAS = " + json.dumps(cas) + ";\nconst out = {};\n"
           "for (const [k, p] of Object.entries(CAS)) { if (!p.n) p.n = vitessePourDebit(p);"
           " const r = pointFonctionnement(p); out[k] = { n: p.n, Q: r.Qh, Pel: r.Pel, eta: r.eta, utile: r.utile,"
           " pertes: r.pertes, Re: r.Re, dh: r.dh, decroche: r.decroche }; }\n"
           "console.log(JSON.stringify(out));")
    try:
        res = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return json.loads(res.stdout)


POSTES = [("utile", "pression utile", C["vert"]), ("moteur", "moteur + électronique", "#495057"),
          ("profil", "profil (traînée)", C["orange"]), ("bout", "bout de pale / fuite", "#f59f00"),
          ("sortie", "air sortant ½ρc²", C["violet"]), ("giration", "giration", "#c2255c"),
          ("friction", "roulements, anneau", "#1098ad")]


def fig_pertes(mod):
    lignes = [("W1G200, estimation\n(fiche : 8 W, η 0,26)",
               dict(utile=2.04, moteur=3.3, profil=1.4, bout=0.3, sortie=0.67, giration=0.2, friction=0.1))]
    if mod:
        for k in ("Extérieur 300 mm", "Extérieur 500 mm, base", "Extérieur 500 mm, optimisé"):
            r = mod[k]
            lignes.append((f"{k}\n(modèle : {fr(r['Pel'], 0)} W, η {fr(r['eta'], 2)})", {**r["pertes"], "utile": r["utile"]}))
    fig, ax = plt.subplots(figsize=(9.2, 0.75 * len(lignes) + 1.1))
    for i, (nom, v) in enumerate(lignes[::-1]):
        tot = sum(max(0, v[k]) for k, _, _ in POSTES)
        x = 0
        for k, lab, col in POSTES:
            l = max(0, v[k]) / tot * 100
            ax.barh(i, l, left=x, color=col, height=0.62, label=lab if i == 0 else None)
            if l > 6:
                ax.text(x + l / 2, i, f"{l:.0f} %", ha="center", va="center", color="white", fontsize=8.5, weight="bold")
            x += l
    ax.set_yticks(range(len(lignes)), [n for n, _ in lignes[::-1]], fontsize=8.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Part de l'électricité absorbée (%)")
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=4, frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.45, -0.2))
    return svg(fig)


def fig_jeu():
    fig, axs = plt.subplots(1, 3, figsize=(9.6, 3.3))
    titres = ["Pales libres : l'air contourne\nle bout de pale (tourbillon)",
              "Anneau tournant + labyrinthe :\nreste une petite fuite (retenu)",
              "Rim-driven : moteur dans l'anneau,\nplus de moyeu (trop cher)"]
    gris, bleu, carter = "#868e96", "#74c0fc", "#ced4da"
    for k, (ax, tit) in enumerate(zip(axs, titres)):
        ax.set_xlim(-1.2, 2.2)
        ax.set_ylim(-0.3, 3.3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(tit, fontsize=9.5)
        ax.add_patch(Rectangle((-1.0, 2.75), 3.0, 0.35, color=carter))          # carter
        moyeu = 0.0 if k == 2 else 0.9
        if k != 2:
            ax.add_patch(Rectangle((-0.35, 0), 1.2, moyeu, color="#495057"))    # moyeu / moteur
        ax.add_patch(Rectangle((0, moyeu), 0.5, 2.6 - moyeu, fc=bleu, ec="#1864ab"))  # pale (coupe)
        if k == 0:
            ax.annotate("", xy=(0.05, 2.45), xytext=(0.45, 2.45),
                        arrowprops=dict(arrowstyle="->", color=C["rouge"], connectionstyle="arc3,rad=-1.6", lw=1.5))
            ax.text(0.25, 3.18, "jeu", ha="center", fontsize=8, color=gris)
        else:
            ax.add_patch(Rectangle((-0.15, 2.6), 0.8, 0.1, fc="#1864ab"))      # anneau
            if k == 1:
                for x in (-0.05, 0.2, 0.45):
                    ax.add_patch(Rectangle((x, 2.72), 0.08, 0.1, fc="#1864ab"))  # dents du labyrinthe
                ax.annotate("", xy=(-0.4, 2.67), xytext=(0.95, 2.67),
                            arrowprops=dict(arrowstyle="->", color=C["rouge"], lw=1, ls="--"))
            else:
                ax.add_patch(Rectangle((-0.05, 2.7), 0.6, 0.05, fc="#c2255c"))  # aimants
                ax.add_patch(Rectangle((-0.1, 2.78), 0.7, 0.3, fc="#e8590c", alpha=0.8))  # bobinage
                ax.text(1.35, 1.2, "pas de moyeu :\n+14 % de section", ha="center", fontsize=8, color=gris)
        ax.add_patch(FancyArrowPatch((-1.0, 1.7), (-0.45, 1.7), arrowstyle="->", mutation_scale=12, color=gris))
        ax.text(-0.75, 1.85, "air", ha="center", fontsize=8, color=gris)
        ax.add_patch(Circle((1.6, 0.15), 0.001, color="white"))
    return svg(fig)


OPT_EXT = dict(D=500, nu=0.30, beta=34, n=0, Qnom=2500, dpNom=25, anneau="labyrinthe", diffuseur=True, stator=True)
CAS_PALES = {f"{N} pales, corde {c} mm, {'profil bas Re' if pr == 'basRe' else 'plaque'}":
             dict(OPT_EXT, N=N, corde=c, profil=pr)
             for N, c in ((9, 85), (7, 110), (5, 150), (4, 190), (3, 250)) for pr in ("plaque", "basRe")}


def _roue(ax, titre, z, r1, courbure, longueur_rel=None, flux="radial"):
    """Roue vue de face ; rotation antihoraire. courbure > 0 : aubes inclinées vers l'avant en sortie."""
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.set_title(titre, fontsize=9.5)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, ec="#adb5bd", lw=0.8, ls=":"))
    ax.add_patch(Circle((0, 0), r1 * 0.55, color="#495057"))
    r = np.linspace(r1, 1.0, 30)
    for i in range(z):
        a0 = 2 * np.pi * i / z
        th = a0 + courbure * ((r - r1) / (1 - r1)) ** 1.3
        ax.plot(r * np.cos(th), r * np.sin(th), color="#1864ab", lw=1.6 if z < 20 else 1.0)
    ax.add_patch(FancyArrowPatch((1.18, -0.35), (1.18, 0.35), connectionstyle="arc3,rad=0.35",
                                 arrowstyle="->", mutation_scale=10, color="#868e96"))
    ax.text(1.27, 0, "rotation", rotation=90, va="center", fontsize=7, color="#868e96")
    if flux == "travers":
        ax.add_patch(FancyArrowPatch((-1.3, -0.9), (1.3, -0.9), arrowstyle="->", mutation_scale=12, color=C["orange"]))
        ax.text(0, -1.25, "l'air traverse deux fois la roue", ha="center", fontsize=7.5, color=C["orange"])
    elif flux == "radial":
        ax.text(0, -1.3, "entrée au centre, sortie sur le pourtour", ha="center", fontsize=7.5, color="#868e96")


def fig_familles():
    fig, axs = plt.subplots(1, 5, figsize=(11, 2.9))
    _roue(axs[0], "Roue « blower » (sirocco)\naubes avant, nombreuses et courtes", 40, 0.78, 0.55)
    _roue(axs[1], "Centrifuge\naubes arrière (profilées)", 8, 0.40, -1.1)
    _roue(axs[2], "Centrifuge\naubes radiales", 10, 0.40, 0.0)
    _roue(axs[3], "Tangentielle (cross-flow)\nmême tambour, flux traversant", 32, 0.78, 0.55, flux="travers")
    ax = axs[4]
    ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-1.35, 1.35); ax.set_ylim(-1.35, 1.35)
    ax.set_title("Axiale / diagonale\npales en hélice", fontsize=9.5)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, ec="#adb5bd", lw=0.8, ls=":"))
    rr = np.linspace(0.3, 1.0, 30)
    for i in range(4):
        a0 = 2 * np.pi * i / 4
        th1, th2 = a0 + 0.25 * rr ** 2, a0 + 0.25 * rr ** 2 + 0.55 + 0.1 * rr
        pts = np.vstack([np.c_[rr * np.cos(th1), rr * np.sin(th1)], np.c_[rr * np.cos(th2), rr * np.sin(th2)][::-1]])
        ax.add_patch(Polygon(pts, closed=True, fc="#d0ebff", ec="#1864ab", lw=1.2))
    ax.add_patch(Circle((0, 0), 0.3, color="#495057"))
    ax.text(0, -1.3, "air parallèle à l'axe", ha="center", fontsize=7.5, color="#868e96")
    fig.tight_layout()
    return svg(fig)


def table_interieur():
    """Taille et vitesse de chaque famille pour l'intérieur : 800 m³/h sous ≈ 40 Pa
    (25 Pa de batterie + ≈ 15 Pa de grille et de virage de l'air dans une unité compacte)."""
    Q, dp = 800 / 3600, 40.0
    lignes = []
    for nom, psi, phi, D, forme, eta in (
            ("Roue blower (aubes avant)", 2.5, 0.5, 0.16, "large", "0,55–0,68 (grandes roues)"),
            ("Centrifuge aubes arrière", 1.0, 0.25, 0.25, "large", "≤ 0,80 (grandes roues)"),
            ("Tangentielle", 2.0, 0.6, 0.10, "longue", "faible, à vérifier"),
            ("Axiale (avec virage dans un caisson)", 0.2, None, 0.28, "axiale", "0,45–0,60 avec diffuseur")):
        u = math.sqrt(2 * dp / (pd.RHO * psi))
        n = u / (math.pi * D) * 60
        if forme == "axiale":
            dim = f"Ø {D*1000:.0f} mm"
        else:
            b = Q / (phi * math.pi * D * u) if forme == "large" else Q / (phi * D * u)
            dim = f"Ø {D*1000:.0f} × {b*1000:.0f} mm de large"
        lignes.append([nom, fr(psi, 1), dim, f"{n:.0f}", fr(u, 1), eta])
    return tableau(["Famille", "ψ (coef. de pression)", "Taille pour 800 m³/h", "tr/min", "u bout m/s", "Rendement statique de pointe publié"],
                   lignes, num=(1, 3, 4))


def section_module():
    """Même batterie et même ventilateur des deux côtés (outils/module_commun.py)."""
    try:
        import module_commun as mc
        fp = mc.fp
        hA_ref, L = mc.calculer()
        debits = sorted({l["V"] for l in L if l["V"]} | {1000, 1200, 1500})
        P = mc.puissances(debits)
    except Exception as e:  # noqa: BLE001
        return f'<div class="carte"><p class="alerte">Calcul du module commun indisponible : {e}</p></div>'
    par_point = {}
    for l in L:
        par_point.setdefault(l["point"], {})[l["cote"]] = l
    lignes, budget = [], []
    for nom, d in par_point.items():
        i, e = d["int"], d["ext"]
        pi, pe = P[str(i["V"])], P[str(e["V"])]
        b76 = (i["V_fiche"] + e["V_fiche"]) / 3600 * fp.DP_AIR / fp.ETA_VENT
        lignes.append([nom, f"{fr(i['V'], 0)} m³/h · {pi['n']:.0f} tr/min · {fr(pi['Pel'], 1)} W",
                       f"{fr(e['V'], 0)} m³/h · {pe['n']:.0f} tr/min · {fr(pe['Pel'], 1)} W",
                       f"<b>{fr(pi['Pel'] + pe['Pel'], 0)} W</b>", f"{fr(b76, 0)} W"])
    # baisse de Tc permise par la batterie intérieure surdimensionnée (chauffage 8,3 °C)
    R = fp.calculer()
    pt = R["pts"]["ch47"]
    tc_l = []
    W0 = None
    for V in debits:
        if V < 800 or (V > 1500 and V != 2500):
            continue
        disp = hA_ref * (V / mc.Q_REF) ** mc.EXPOSANT
        best = None
        for tc10 in range(320, 240, -1):
            Tc = tc10 / 10
            _, c, m, W = fp.cop_unite("ch47", pt["Te"], Tc, V, pt["Ve"])
            b = fp.batterie_seche(pt["ai"], V, m * c["q_c"], Tc)
            if b["hA"] and b["hA"] <= disp:
                best = (Tc, W, b["T_out"])
            else:
                break
        if not best:
            continue
        W0 = W0 or best[1] + P[str(V)]["Pel"]
        tot = best[1] + P[str(V)]["Pel"]
        tc_l.append([f"{fr(V, 0)}", fr(best[0], 1), fr(best[2], 1), fr(best[1], 0), fr(P[str(V)]["Pel"], 1),
                     f"<b>{fr(tot - W0, 0)} W</b>"])
    return f"""<div class="carte">
<p><b>Attention : le ventilateur n'est pas encore dessiné.</b> Les puissances ci-dessous viennent du modèle de l'animation appliqué à la pale de départ proposée (axiale 500 mm, 3 pales), une hypothèse de travail, pas une conception.</p>
<p>Idée : un seul <b>module</b> (batterie + ventilateur de 500 mm) monté deux fois, l'un côté pièce, l'autre côté façade.
Il est dimensionné sur le cas le plus dur côté extérieur. Avec les Te et Tc actuels de la fiche échangeur, ce cas n'est plus
le chauffage à −8,3 °C mais <b>la clim à 35 °C</b> : {fr(hA_ref, 0)} W/K à 2 500 m³/h (contre 897 W/K à −8,3 °C).
Les deux côtés ont alors le même circuit d'air : seule la vitesse du ventilateur change.
Calcul : <code>conception_ventilateur/outils/module_commun.py</code> (besoins de la fiche échangeur, hA ∝ débit^0,6, modèle
du ventilateur de l'animation).</p>
<h3>Débits et puissances avec le module commun</h3>
{tableau(["Point", "Intérieur", "Extérieur", "Ventilateurs", "Budget actuel (fiche)"], lignes, num=(3, 4))}
<ul>
<li><b>Le ventilateur reste à son point de dessin à toutes les vitesses</b> : même batterie, même circuit, donc mêmes
triangles des vitesses. Seul le Reynolds baisse à bas régime (≈ 36 000 à 125 tr/min), d'où un rendement plus faible côté
pièce, sur une puissance de 1 à 2 W.</li>
<li><b>Côté pièce, il tourne à 125–180 tr/min</b> : vitesse en bout de pale de 3 à 5 m/s, quasi inaudible.</li>
<li><b>La batterie intérieure est plus grande que nécessaire</b>, et c'est une chance : on peut baisser la température de
condensation (tableau ci-dessous).</li></ul>
<h3>Ce que permet la batterie intérieure plus grande (chauffage 8,3 °C)</h3>
{tableau(["Débit intérieur m³/h", "Tc possible °C", "Air soufflé °C", "Compresseur W", "Ventilateur intérieur W", "Bilan"], tc_l, num=range(6))}
<p class="note">Tc la plus basse pour laquelle la batterie intérieure du module suffit, cycle de la fiche échangeur (Te = {fr(pt['Te'], 1)} °C,
η_is = {fr(fp.ETA_IS, 2)}). À 1 200 m³/h, on gagne ≈ 35 W, soit ≈ 10 % de la puissance électrique, pour un air soufflé un peu
moins chaud ; au-delà, le gain continue mais l'air soufflé descend sous 27 °C (sensation de courant d'air tiède). À confirmer avec la fiche échangeur (résistance côté propane, givre).</p>
<h3>Points à vérifier</h3>
{tableau(["Point", "Pourquoi", "Avec qui"],
 [["Encombrement côté pièce", "une batterie de ≈ 0,4–0,5 m² de façade et un rotor de 500 mm aussi à l'intérieur", "géométrie de la fenêtre"],
  ["Charge de propane", "deux batteries identiques au volume maximal : le cahier des charges admet déjà ≤ 279 cm³ chacune ; plus de surface d'ailettes pour le même volume", "dossier échangeur"],
  ["Eau", "le module doit évacuer le condensat (clim, côté pièce) et dégivrer (chauffage, côté façade) : il le doit déjà, l'échangeur étant réversible", "dossier échangeur"],
  ["Moteur", "le même BLDC doit tourner de 125 à 500 tr/min et fournir de 1,4 à 30 W : FOC sans capteur possible avec un moteur multipolaire (fréquence électrique suffisante) ; reprise d'un rotor que le vent fait tourner, côté façade", "électronique"],
  ["Jet d'air dans la pièce", "≈ 0,5 m/s en façade de batterie : la grille de soufflage doit porter l'air", "conception"]])}
</div>"""


# ---------------------------------------------------------------- page
SOURCES = [
    ("agrawal", "Agrawal et Sharma, bords d'attaque dentelés type chouette (AIAA 2016), Iowa State",
     "https://dr.lib.iastate.edu/entities/publication/7628929b-0c75-4202-8ecc-9e165a324645"),
    ("chiba", "Chiba University, dentelures et incidence (Bioinspir. Biomim. 2017)",
     "https://www.sciencedaily.com/releases/2017/07/170704093621.htm"),
    ("helice", "Hélice à dentelures de chouette bord d'attaque + fuite (Phys. Fluids 2025)",
     "https://www.ebsco.com/articles/chemistry/a2779745-54b9-5e5a-a4fc-1d678df0ef2d/experimental-investigation-of-a-biomimetic-propeller-coupled-with-owl-inspired-leading-and-trailing-edges-serrations"),
    ("polyu", "Mémoire PolyU, densité et longueur des dentelures (2019)", "https://theses.lib.polyu.edu.hk/handle/200/10116"),
    ("falchi", "Falchi et al., tubercules sur hélices marines (Ocean Eng. 2022)",
     "https://strathprints.strath.ac.uk/80727/1/Falchi_etal_OE_2022_effect_of_leading_edge_tubercles_on_the_performance_of_marine_propellers.pdf"),
    ("whalepower", "WhalePower, tubercules (MIT Technology Review 2008)",
     "https://www.technologyreview.com/2008/03/06/221447/whale-inspired-wind-turbines/"),
    ("sinus", "Revue : rotors axiaux à bord d'attaque sinusoïdal (Energies 2024)",
     "https://doaj.org/article/49e25c189677480097639621c0b9dfc4"),
    ("revue_bruit", "Revue : bio-inspiration et bruit aérodynamique (Appl. Sci. 2019)", "https://mdpi.com/2076-3417/9/11/2224"),
    ("revue_2025", "Revue : pales bio-inspirées éolien et marin (2025)",
     "https://tethys-engineering.pnnl.gov/sites/default/files/publications/RevathiRamakrishnan-2025.pdf"),
    ("axiblade", "ebm-papst, AxiBlade.Perform (2025)",
     "https://www.ebmpapst.com/ae/en/newsroom/news/2025/new-axiblade-perform-ec-technology.html"),
    ("axiblade_mag", "ebm-papst, genèse de l'AxiBlade", "https://mag.ebmpapst.com/en/?p=11258"),
    ("axitop", "ebm-papst, diffuseur AxiTop",
     "https://www.climatecontrolnews.com.au/news/axitop-sets-new-standard-in-acoustics"),
    ("ebm_pac", "ebm-papst, axial ou centrifuge pour PAC",
     "https://www.ebmpapst.com.cn/en/newsroom/news/2020/fans-for-air-water-heat-pumps.html"),
    ("za", "Ziehl-Abegg, bionique", "https://www.ziehl-abegg.com/en/glossary/bionics-biomimetics"),
    ("bluefin", "Ziehl-Abegg, ZAbluefin",
     "https://www.climatecontrolnews.com.au/interviews/bionic-profiling-delivers-peak-efficiency"),
    ("mahle", "Mahle, ventilateur « chouette » (New Atlas)", "https://newatlas.com/automotive/mahle-biomimetic-owl-cooling-fan"),
    ("sharp", "Sharp, roue sirocco « libellule » (rapport technique)", "https://corporate.jp.sharp/rd/n39/pdf/107_09.pdf"),
    ("sharp_ext", "Sharp, biomimétisme de l'unité extérieure",
     "https://www.vn.sharp/en/microsite/biomimetic/air-conditioner-outdoor"),
    ("harle", "Roue tangentielle à pales d'aile de harle (Xi'an Jiaotong)",
     "https://scholar.xjtu.edu.cn/zh/publications/%E9%87%87%E7%94%A8%E4%BB%BF%E7%A7%8B%E6%B2%99%E9%B8%AD%E7%BF%BC%E5%9E%8B%E5%8F%B6%E7%89%87%E8%B4%AF%E6%B5%81%E9%A3%8E%E6%9C%BA%E7%9A%84%E6%B0%94%E5%8A%A8%E6%80%A7%E8%83%BD%E6%95%B0%E5%80%BC%E7%A0%94%E7%A9%B6/"),
    ("lg", "LG, biomimétisme dans le HVAC", "https://www.lghvacstory.com/?p=3076"),
    ("vanaei", "Vanaei et al., revue des ventilateurs tangentiels (Energies 2023)",
     "https://sam.ensam.eu/bitstream/10985/26216/2/LIFSE_E_2023_VANAEI.pdf"),
    ("himeur", "Himeur et al., performance des ventilateurs tangentiels (Energies 2022)",
     "https://mdpi.com/1996-1073/15/14/5134/htm"),
    ("wang", "Wang, Ravelet, Bakir, ventilateurs contrarotatifs (2015)",
     "https://sam.ensam.eu/bitstream/10985/9486/3/Dynfluid-JEPS-WANG-2015-1.pdf"),
    ("contra", "Contrarotatif : espacement et répartition de charge", "https://pdf.arxiv.org/pdf/1208.6396"),
    ("jeu", "Jeu en bout de pale, winglets, hauteur de virole (IIR)",
     "https://iifiir.org/en/fridoc/effect-of-tip-clearance-winglets-and-shroud-height-on-the-tip-141441"),
    ("jeu_kr", "Jeu en bout de pale, ventilateur de 806 mm", "https://koreascience.kr/article/JAKO200806135603722.page?lang=ko"),
    ("jeu_core", "Jeu en bout de pale : 0,3 % → 0,1 % du diamètre", "https://core.ac.uk/download/357550149.pdf"),
    ("diaforce", "ebm-papst DiaForce, ventilateur diagonal (DigiKey)",
     "https://www.digikey.com/en/articles/high-performance-cooling-diagonal-compact-fans"),
    ("digikey", "DigiKey, rendements EC / PSC / pôles ombragés",
     "https://www.digikey.com/en/articles/ac-input-electronically-commutated-fans"),
    ("mcf", "TI MCF8316A, FOC sans capteur", "https://www.ti.com/product/MCF8316A"),
    ("mcfd", "TI MCF8316D", "https://www.ti.com/product/MCF8316D"),
    ("ft8132", "Fortior FT8132, fiche technique", "https://shop.mev-elektronik.com/wp-content/uploads/FT8132Q.pdf"),
    ("balla", "Balla et Vad, coefficients de portance et traînée des plaques cambrées à bas Reynolds (AIAA J. 2022)",
     "https://real.mtak.hu/205592/1/Balla_Vad_resubmit_final_repositoriumba.pdf"),
    ("koning", "Koning, Romander, Johnson, profils à très bas Reynolds (NASA Ames, AIAA 2020)",
     "https://rotorcraft.arc.nasa.gov/Publications/files/koningAIAA2020.pdf"),
    ("selig", "McGranahan et Selig, profils bas Reynolds (AIAA 2003, UIUC)",
     "https://m-selig.web.engr.illinois.edu/pubs/McGranahanSelig-2003-AIAA-2003-4067-LRN-Airfoils.pdf"),
    ("frontiers", "Ventilateur axial à faucille avant pour PAC, optimisation (Frontiers Energy Res. 2021)",
     "https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2021.700365/full"),
    ("twente", "Jie Wang, ventilateurs axiaux basse pression : faucille et distribution de tourbillon (thèse Twente 2021)",
     "https://www.utwente.nl/en/et/events/2021/12/258645/phd-defence-jie-wang-design-for-high-efficiency-of-low-pressure-axial-fans-use-of-blade-sweep-and-vortex-distribution"),
    ("jafm_cv", "Tourbillon contrôlé à partir d'un tourbillon libre : +4,2 points (J. Appl. Fluid Mech. 2025)",
     "https://doaj.org/article/ad577dee349946238ff246414e6c18b2"),
    ("vad_sweep", "Faucille avant et pales à tourbillon contrôlé, ventilateurs sans stator (Vad et al.)",
     "https://katalog.lib.cas.cz/KNAV/EdsRecord/edsair,edsair.doi.dedup.....99d0ad5fba65dabcd33e17d129c3a276"),
    ("sanjose", "Sanjosé et al., faucille et bruit, ventilateur de 495 mm (Lattice Boltzmann, ETS 2022)",
     "https://espace2.etsmtl.ca/26128/1/Sanjose-M-2022-26128.pdf"),
    ("revue_sweep", "Revue : faucille, bruit et rendement des ventilateurs basse pression (Acoustics 2020)",
     "https://mdpi.com/2624-599X/2/4/43"),
    ("demi_carene", "Iwase et Kishitani, hélice semi-carénée d'unité extérieure, optimisation CFD + algorithme génétique",
     "https://www.jstage.jst.go.jp/article/tsj/43/6/43_325/_article/-char/en"),
    ("ijr", "Optimisation de pales en tenant compte de l'unité extérieure (Int. J. Refrig., vol. 175)",
     "https://iifiir.org/en/fridoc/aerodynamic-optimization-of-axial-fans-mounted-on-outdoor-air-151002"),
    ("pavillon", "Pavillon redessiné : +1,2 % de rendement d'unité extérieure (IIR)",
     "https://iifiir.org/en/fridoc/aerodynamic-performance-improvement-of-up-flow-outdoor-unit-of-air-137908"),
    ("genes", "Ventilateurs à virole tournante : bruit de fuite (Gênes, ETC 2019)", "https://iris.unige.it/bitstream/11567/963706/4/ETC2019-368.pdf"),
    ("brevet_ring", "Brevet US9903387B2, ventilateur à anneau et carénage", "https://patents.google.com/patent/US9903387"),
    ("friedrich", "Friedrich, manuel de service : moteur à double arbre, roue blower intérieure, hélice « slinger » extérieure",
     "https://lawnandgarden.manualsonline.com/manuals/mfg/friedrich/cp24n30.html?p=7"),
    ("fasco", "Moteur PSC à double arbre pour climatiseur de fenêtre (Fasco D367)",
     "https://www.supplyhouse.com/Fasco-D367-3-Speed-1550-RPM-Window-A-C-Motor-115V"),
    ("bee", "Bureau of Energy Efficiency (Inde), ventilateurs : rendements par famille", "https://beeindia.gov.in/sites/default/files/3Ch5.pdf"),
    ("ashrae", "ASHRAE Handbook, chapitre 21 : ventilateurs", "https://handbook.ashrae.org/Handbooks/S20/IP/s20_ch21/s20_ch21_ip.aspx"),
    ("yaskawa", "Sélection des ventilateurs de traitement d'air (rapport d'application J1000)",
     "https://www.precision-elec.com/wp-content/uploads/2020/11/J1000-Application-Report-Fan-Selection-for-Air-Handling.pdf"),
    ("radical", "ebm-papst K3G250-RR02-I2, centrifuge EC aubes arrière 250 mm : rendement global 56 %",
     "https://media.onlinecomponents.com/upload/globalresourcefiles/ebm-papst%20-%20k3g250-rr02-i2.pdf"),
    ("radical11", "ebm-papst R3G250-AM50-01, centrifuge EC 250 mm à 11 aubes : rendement global 47 %",
     "https://www.mouser.com/catalog/specsheets/ebm_papst_R3G250AM5001.pdf"),
    ("volute", "Optimisation de la volute d'une roue sirocco : +5 % de rendement (Du et al.)", "https://scite.ai/authors/shouhua-du-6gv30k"),
    ("volute_xjtu", "Volute courbe d'une roue multi-aubes : −4,6 % de puissance, −6,4 dB (Xi'an Jiaotong 2025)",
     "https://scholar.xjtu.edu.cn/en/publications/numerical-and-experimental-study-on-the-effects-of-curved-volute-/"),
    ("greenheck", "Greenheck, sélection de base d'un ventilateur", "https://webcontent.greenheck.com/atg-cms-prod/docs/default-source/pdf-downloads/industry-articles/hpac_basic-fan-selection.pdf"),
]
NUM = {k: i + 1 for i, (k, _, _) in enumerate(SOURCES)}


def s(*cles):
    return "".join(f'<sup><a href="#src-{k}">[{NUM[k]}]</a></sup>' for k in cles)


def tableau(entetes, lignes, num=()):
    h = "".join(f'<th class="{"n" if i in num else ""}">{e}</th>' for i, e in enumerate(entetes))
    corps = "".join("<tr>" + "".join(f'<td class="{"n" if i in num else ""}">{c}</td>'
                                     for i, c in enumerate(l)) + "</tr>" for l in lignes)
    return f"<table><tr>{h}</tr>{corps}</table>"


def table_balayage():
    lignes = []
    for nom, q in pd.POINTS.items():
        for D in ((0.20, 0.25, 0.30) if nom == "intérieur" else (0.30, 0.40, 0.50)):
            dp0, c = dp_total(q, D)
            dpt, _ = dp_total(q, D, 0.5)
            u = math.sqrt(2 * dpt / (pd.RHO * 0.2))
            phi = q / 3600 / (math.pi * D**2 / 4 * u)
            ok = 0.15 <= phi <= 0.35
            lignes.append([nom, f"{D*1000:.0f}", fr(c), fr(dp0 - pd.DP_BATTERIE), fr(dpt), fr(u),
                           f"{u / (math.pi * D) * 60:.0f}",
                           f'<span class="{"ok" if ok else "alerte"}">{fr(phi, 2)}</span>',
                           " / ".join(fr(q / 3600 * dpt / e, 0) for e in (0.30, 0.45, 0.60))])
    return tableau(["Échangeur", "D mm", "c sortie m/s", "½ρc² Pa", "Δp_t avec diffuseur Pa", "u bout m/s",
                    "tr/min", "φ", "P élec. W (η 0,30 / 0,45 / 0,60)"], lignes, num=range(1, 9))


CSS = """
:root { --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; --accent:#1c7ed6;
  --ok:#2b8a3e; --alerte:#c92a2a; --surligne:#e7f5ff; --cle:#fff9db; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fond:#141517; --carte:#1f2023;
  --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; --ok:#69db7c; --alerte:#ff8787; --surligne:#1b3550; --cle:#2b2a1d; } }
:root[data-theme="dark"] { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40;
  --accent:#4dabf7; --ok:#69db7c; --alerte:#ff8787; --surligne:#1b3550; --cle:#2b2a1d; }
* { box-sizing:border-box; }
body { margin:0; background:var(--fond); color:var(--texte); font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1100px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:26px; margin:0 0 4px; } h2 { font-size:19px; margin:36px 0 8px; border-bottom:2px solid var(--trait); padding-bottom:4px; }
h3 { font-size:16px; margin:18px 0 6px; }
a { color:var(--accent); }
.sous { color:var(--doux); margin:0 0 18px; }
.carte { background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:14px 16px; margin:10px 0; overflow-x:auto; }
.cle { background:var(--cle); }
.cle ol { margin:4px 0; padding-left:22px; } .cle li { margin:6px 0; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { text-align:left; padding:6px 9px; border-bottom:1px solid var(--trait); vertical-align:top; }
th { color:var(--doux); font-weight:600; }
td.n, th.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
code, .f { font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:13px; }
.f { display:block; background:var(--fond); border:1px solid var(--trait); border-radius:6px; padding:8px 10px; margin:8px 0; white-space:pre-wrap; line-height:1.6; }
.note { color:var(--doux); font-size:13.5px; margin:6px 0; }
.alerte { color:var(--alerte); font-weight:600; } .ok { color:var(--ok); font-weight:600; }
.com { color:var(--doux); font-style:italic; }
figure { margin:12px 0; } figure .img { background:#fff; border-radius:8px; padding:6px; }
figure svg { width:100%; height:auto; display:block; }
figcaption { color:var(--doux); font-size:13.5px; margin-top:6px; }
nav ol { margin:0; padding-left:20px; columns:2; font-size:14px; }
sup a { text-decoration:none; font-size:11px; }
@media (max-width:640px) { nav ol { columns:1; } }
"""


def fig_html(svg_txt, legende, largeur=None):
    st = f' style="max-width:{largeur}px"' if largeur else ""
    return f'<figure{st}><div class="img">{svg_txt}</div><figcaption>{legende}</figcaption></figure>'


def page():
    com = '<span class="com">(chiffre fabricant)</span>'
    sections = []
    sections.append(("resume", "L'essentiel", f"""<div class="carte cle"><ol>
<li><b>Les ventilateurs pèsent lourd</b> : à COP 6, les 76 W du budget actuel font 17 % de la puissance électrique.
Les ramener à 40 W donne <b>COP 6,5</b>.</li>
<li><b>Le budget de 76 W est faux</b> : il ne compte que les 25 Pa de la batterie. Un ventilateur axial
perd aussi l'énergie de l'air qui sort (½ρc²) : à l'extérieur, de 10 Pa (rotor de 500 mm) à 75 Pa (300 mm).
<b>Le diamètre disponible dans la fenêtre décide de tout.</b></li>
<li><b>Le premier gain vient de ce qu'il y a autour de la pale</b> : grand rotor lent, diffuseur, stator
redresseur, faible jeu en bout de pale. Un diffuseur fait passer un axial de 42 % à plus de 50 %{s("axitop", "axiblade_mag")}.</li>
<li><b>Le biomimétisme sert d'abord le bruit</b> (−2,5 à −5 dB) ; les gains de rendement indépendants sont de
3 à 8 %. Les tubercules de baleine aident quand la batterie extérieure givre (le ventilateur ne décroche pas).</li>
<li><b>Moteur BLDC à commande vectorielle sans capteur : le bon choix.</b> 60–90 % de rendement contre 30–50 %
pour un moteur à condensateur, et efficace à bas régime, là où la PAC tourne le plus{s("digikey")}.</li>
<li><b>Pourquoi un petit ventilateur rend si mal</b> : pression utile faible (l'air sortant emporte l'énergie), faible Reynolds (profils peu efficaces), bout de pale, petit moteur. Le ventilateur EC du commerce du dépôt plafonne à 0,26. <b>Cible revue : 0,45–0,55.</b></li>
<li><b>Bout de pale</b> : anneau tournant fixé aux pales, oui ; roulement en périphérie, non ; moteur en périphérie (rim-driven), intéressant mais trop cher pour le premier prototype.</li>
<li><b>Un seul module (même batterie, même ventilateur) des deux côtés : ça tient</b>, et les ventilateurs ne consomment plus que ≈ 12 à 30 W au total ; la batterie intérieure plus grande permet de baisser Tc (≈ −35 W de compresseur à 8,3 °C). Voir <a href="#module">Même ventilateur et même échangeur</a>.</li>
<li><b>Pour essayer les variantes</b> : <a href="animation_ventilateur.html">ventilateur interactif</a> (géométrie, vitesse, anneau, diffuseur, motifs bio-inspirés, moteur ; bilan des pertes en direct).</li>
</ol></div>"""))

    sections.append(("cdc", "Cahier des charges", f"""<div class="carte">{tableau(
        ["", "Intérieur", "Extérieur"],
        [["Débit max", "800 m³/h", "2 500 m³/h"],
         ["Perte de charge de la batterie", "≤ 25 Pa", "≤ 25 Pa, davantage quand elle givre"],
         ["Cas qui dimensionne", "chauffage 8,3 °C", "chauffage −8,3 °C (air à 1,33 kg/m³, +11 % de pression)"],
         ["Budget actuel", "76 W au total, η = 0,30, perte de sortie non comptée", ""],
         ["Cible du dossier", "η global 0,45–0,55 → ≈ 45–55 W au total", ""],
         ["Moteur", "BLDC rotor extérieur, FOC sans capteur", ""]])}
<p class="note">Source : <code>pac_9000btu.html</code>, cahier des charges des échangeurs (9 000 BTU/h = 2 638 W).</p></div>"""))

    sections.append(("cop", "Pourquoi chaque watt compte", f"""<div class="carte">
{fig_html(fig_cop(), "COP de l'unité selon la puissance des ventilateurs, compresseur inchangé. "
          "Ronds : budget actuel ; carrés verts : cible de 40 W.", 620)}
{tableau(["COP visé", "P élec. totale W", "Ventilateurs 76 W", "Ventilateurs 40 W", "COP si 76 → 40 W"],
         [[fr(c), fr(pd.Q_UTILE / c, 0), f"{fr(76 / (pd.Q_UTILE / c) * 100, 0)} %",
           f"{fr(40 / (pd.Q_UTILE / c) * 100, 0)} %", f"<b>{fr(pd.Q_UTILE / (pd.Q_UTILE / c - 36), 2)}</b>"]
          for c in pd.COP_CIBLES], num=range(5))}</div>"""))

    sections.append(("archi", "Architecture : la perte de sortie et le diamètre", f"""<div class="carte">
<span class="f">pression totale à fournir  Δp_t = Δp_batterie + ½ ρ c²   (c = débit / section annulaire du rotor)
puissance électrique        P = Q × Δp_t / η_global
similitude                  Q ∝ n D³   Δp ∝ n² D²   P ∝ n³ D⁵   bruit ∝ u⁵ à u⁶ (u = vitesse en bout de pale)</span>
{fig_html(fig_perte_sortie(), "Pression totale qu'un axial doit fournir selon son diamètre. Bleu : la batterie ; "
          "orange : énergie perdue par l'air qui sort ; vert : avec un diffuseur qui en récupère la moitié.")}
{fig_html(fig_puissance(), "Puissance électrique selon le diamètre (diffuseur à 50 %) pour trois rendements ; "
          "en pointillé violet, la vitesse de rotation pour un coefficient de pression ψ = 0,2.")}
{table_balayage()}
<p class="note">φ = Q / (π D²/4 · u) : coefficient de débit, en vert dans la plage usuelle d'un axial basse
pression (0,15–0,35), en rouge si le diamètre est mal adapté au débit. ψ = 2 Δp_t / (ρ u²) = 0,2.
Calcul : <code>conception_ventilateur/outils/predimensionnement.py</code>.</p>
<p><b>Lecture.</b> À l'extérieur, un rotor de 300 mm est hors jeu (φ trop grand, 145 W à η = 0,3). À 500 mm on
tourne à 600 tr/min, silencieux, pour 35 W à η = 0,6. À l'intérieur, 250–300 mm à 1 000–1 300 tr/min,
11 à 16 W.</p></div>"""))

    sections.append(("familles", "Quelle famille de ventilateur", f"""<div class="carte">{tableau(
        ["Famille", "Où elle gagne", "Rendement global typique", "Pour nous"],
        [["<b>Axial à virole + diffuseur / stator</b>", "grand débit, faible pression (notre cas)",
          "0,45–0,60 avec diffuseur" + s("axitop"), "<b>extérieur : choix de base</b>"],
         ["Contrarotatif (2 rotors)", "plus de pression dans le même diamètre, giration récupérée",
          "63–65 % mesurés sur petits rotors" + s("wang", "contra"), "si la fenêtre limite le diamètre"],
         ["Diagonal (hélico-centrifuge)", "pression moyenne, compact", "≈ 0,48–0,56 " + com + s("diaforce"),
          "intérieur si la batterie résiste plus que prévu"],
         ["Centrifuge à aubes arrière", "pression élevée, débit moyen", "> 0,70 en grande taille " + com + s("bluefin"),
          "intérieur possible, encombrant"],
         ["Tangentiel (cross-flow)", "nappe d'air large, très plat, silencieux", "faible (≈ 0,2–0,4, à vérifier)" + s("vanaei", "himeur"),
          "standard des splits ; à éviter pour gagner des watts"]])}
<h3>Jeu en bout de pale</h3>
<p>Passer de 0,3 % à 0,1 % du diamètre gagne ≈ 2 points de rendement{s("jeu_core")} ; en dessous de 5 % de la
hauteur de pale, le rendement baisse linéairement avec le jeu{s("jeu_kr")}. Avec une virole partielle, il existe
un jeu optimal non nul{s("jeu")}. Les solutions (anneau tournant, roulement périphérique, rim-driven) sont comparées plus bas, section <a href="#jeu">Jeu en bout de pale</a>.</p></div>"""))

    sections.append(("fabricants", "Pales récentes des fabricants", f"""<div class="carte">{tableau(
        ["Produit", "Ce qui change", "Gain annoncé " + com],
        [["ebm-papst AxiBlade / AxiBlade.Perform (2025)" + s("axiblade", "axiblade_mag"),
          "profil aile, winglets intégrés, aubes directrices, diffuseur", "jusqu'à +54 % de rendement, −8 dB ; η statique ≤ 53 %"],
         ["ebm-papst AxiTop" + s("axitop"), "diffuseur seul", "−27 % de puissance et −7,2 dB(A), ou +9 % de débit"],
         ["Ziehl-Abegg FE2owlet" + s("za", "mahle"), "pales en faucille, bord de fuite dentelé, winglets",
          "−4 dB(A) ; version Mahle : +10 % de rendement, −10 % de masse"],
         ["Ziehl-Abegg ZAbluefin" + s("bluefin"), "centrifuge, bord d'attaque ondulé (nageoire de baleine)", "+10 à +15 % selon les sources"],
         ["LG MULTI V 5" + s("lg"), "pales inspirées de la baleine", "−20 % de consommation"],
         ["Sharp" + s("sharp", "sharp_ext"), "roue sirocco « aile de libellule » ; hélice extérieure aigle / albatros / martinet",
          "−2,5 dB mesurés (sirocco) ; extérieur : qualitatif"]])}
<p class="note">Aucun de ces chiffres n'est accompagné d'une norme d'essai ou d'une référence de comparaison publiée.</p></div>"""))

    sections.append(("biomim", "Biomimétisme : ce que dit la recherche", f"""<div class="carte">
{fig_html(fig_biomim(), "Les motifs bio-inspirés, dessinés schématiquement sur une même pale.")}
{tableau(["Modèle naturel", "Motif", "Effet mesuré", "Prix à payer"],
         [["<b>Chouette</b>", "dents de bord d'attaque, peigne de bord de fuite",
           "−3 à −5 dB à moyenne et haute fréquence" + s("agrawal") + " ; hélice avec les deux : −3,1 dB et +7,9 % de rendement de poussée" + s("helice"),
           "sous 15° d'incidence, l'aéro se dégrade" + s("chiba") + " ; dents longues = moins de bruit mais moins de rendement" + s("polyu")],
          ["<b>Baleine à bosse</b>", "tubercules sinusoïdaux au bord d'attaque",
           "décrochage retardé, tourbillons de bout réduits, couple réduit (hélices, CFD)" + s("falchi", "sinus") + " ; ventilateurs : chiffres commerciaux seulement" + s("whalepower"),
           "léger déficit au point nominal ; gain surtout hors nominal"],
          ["<b>Libellule</b>", "section ondulée", "−2,5 dB (sirocco Sharp)" + s("sharp") + " ; rigidité d'une pale très mince", "profil plus délicat à mouler"],
          ["<b>Harle (oiseau)</b>", "profil d'aile sur roue tangentielle", "−3,3 % de puissance à débit égal" + s("harle"), "gain modeste"],
          ["<b>Bout d'aile d'oiseau</b>", "winglets, faucille", "réduit le tourbillon de bout de pale" + s("jeu"), "—"]])}
<p><b>Pour nous.</b> Quand la batterie extérieure givre, sa perte de charge monte et le ventilateur passe à faible
débit et forte incidence : c'est là que tubercules et dentelures sont favorables (décrochage retardé, moins de bruit
de décrochage tournant). C'est l'argument le plus solide pour un motif bio-inspiré dans la PAC.
Revues générales : {s("revue_bruit", "revue_2025", "sinus")}.</p></div>"""))

    sections.append(("moteur", "Moteur : petit BLDC piloté en FOC sans capteur", f"""<div class="carte">
{fig_html(fig_moteurs(), "Rendement des moteurs de ventilateur, ordres de grandeur" + s("digikey") + ".", 620)}
<ul><li><b>Pourquoi</b> : rendement élevé et presque plat en charge partielle, vitesse continue (on suit la
puissance de la PAC au lieu de trois vitesses), démarrage doux, et le couple mesuré à vitesse donnée révèle
l'encrassement ou le givre.</li>
<li><b>Moteur</b> : rotor extérieur intégré au moyeu, la cloche sert de moyeu.</li>
<li><b>Alimentation</b> : bus DC commun (24 V, ou bus haute tension de l'onduleur du compresseur) : à trancher
avec l'électronique de la PAC.</li></ul>
{tableau(["Circuit", "Type", "Points forts", "Usage"],
         [["TI MCF8316A / C / D" + s("mcf", "mcfd"), "FOC sans capteur, MOSFET intégrés, 4,5–35 V, 8 A crête",
           "aucun code, identification automatique du moteur, consigne PWM / analogique / I²C", "prototype"],
          ["Fortior FT8132" + s("ft8132"), "pré-driver FOC sans capteur, MOSFET externes, 28 V",
           "réglage par interface graphique, paramètres en EEPROM ; famille FT8213 / FT8215 / FS9276", "grande série, bas coût"],
          ["Infineon iMOTION IMD110, ST STSPIN32", "contrôleur FOC intégré", "à évaluer", "alternatives"]])}
</div>"""))

    sections.append(("commerce", "Un ventilateur EC du commerce, mesuré", f"""<div class="carte">
{fig_html(fig_ebm(), "Courbes fabricant du ventilateur déjà utilisé par le simulateur (<code>ventilateurs/W1G200-EC87-20.json</code>).")}
<p>Même un bon ventilateur EC de 200 mm plafonne à <b>η = 0,26</b> à son meilleur point : l'hypothèse de 0,30 du
cahier des charges correspond à un bon produit standard, pas à un objectif ambitieux.</p></div>"""))

    mod = modele_animation()
    lignes_mod = []
    if mod:
        for k, r in mod.items():
            lignes_mod.append([k, f"{r['n']:.0f}", fr(r["Q"], 0), fr(r["Pel"], 1), f"<b>{fr(r['eta'], 2)}</b>",
                               fr(r["Re"] / 1000, 0) + " k",
                               f'<span class="{"alerte" if r["decroche"] else "ok"}">{fr(r["dh"], 2)}</span>'])
    sections.append(("pertes", "Pourquoi le rendement est si bas", f"""<div class="carte">
<p>Quatre causes se cumulent ; les deux premières sont physiques et nous suivent quel que soit le dessin.</p>
<ol>
<li><b>Pression utile faible : l'air qui sort emporte une grosse part de l'énergie.</b> Le rendement statique ne compte
que la pression gagnée sur la batterie. W1G200 à 320 m³/h : section annulaire ≈ 250 cm², air sortant à 3,5 m/s,
½ρc² ≈ 7,5 Pa perdus, soit 25 % de la pression totale. À 1 000 Pa (centrifuge) ce serait négligeable ; à 25 Pa
c'est structurel.</li>
<li><b>Faible nombre de Reynolds.</b> Re = vitesse × corde / viscosité ≈ 55 000 pour le W1G200, ≈ 100 000 pour un
rotor de 500 mm à 600 tr/min, contre ≈ 10⁷ pour une aile d'avion. Sous ≈ 10⁵ la finesse d'un profil tombe de
≈ 100 à 20–40 (couche limite laminaire, bulle de décollement). C'est le régime des oiseaux et des insectes :
profils minces cambrés, dentelures et ondulations y sont adaptés.</li>
<li><b>Bout de pale et giration.</b> 1 à 2 mm de jeu sur 200 mm, c'est 3 à 10 fois plus en proportion que sur un
grand ventilateur ; sans stator, la rotation de l'air en sortie est perdue.</li>
<li><b>Petit moteur et électronique.</b> À 8 W, roulements, pertes fer, alimentation de la commande et redresseur
230 V pèsent lourd : ≈ 60–70 % pour le moteur, contre plus de 90 % à 1 kW.</li></ol>
{fig_html(fig_pertes(mod), "Où part l'électricité. Première ligne : estimation pour le W1G200 (seules l'entrée et "
          "la sortie viennent de la fiche). Lignes suivantes : modèle de l'animation, à la vitesse qui donne 2 500 m³/h.")}
{tableau(["Cas (modèle de l'animation)", "tr/min", "m³/h", "P élec. W", "η global", "Reynolds", "w₂/w₁ (décroche &lt; 0,62)"],
         lignes_mod, num=range(1, 7)) if lignes_mod else ""}
<p>Ce que nous pouvons attaquer : le moteur et l'électronique (BLDC + FOC à 15–40 W : 80–85 %), l'air sortant et la
giration (diffuseur, stator), le bout de pale (anneau). Le faible Reynolds ne se supprime pas, il se repousse :
grand diamètre, corde large, profil choisi pour ce régime. D'où la <b>cible revue de 0,45–0,55</b>. Le modèle de
l'animation donne ≈ 0,6 pour la version optimisée : il est optimiste (une seule section de pale, écoulement idéal
derrière la batterie).</p></div>"""))

    sections.append(("jeu", "Jeu en bout de pale : anneau, roulement, rim-driven", f"""<div class="carte">
{fig_html(fig_jeu(), "Coupes schématiques du bout de pale. Rouge : fuite d'air de l'aval vers l'amont.")}
{tableau(["Solution", "Pour", "Contre", "Décision"],
         [["Pales libres, jeu serré", "simple", "perte ≈ 2,85 × jeu / hauteur de pale" + s("jeu_kr") + " ; bruit de jeu ; tolérances serrées", "référence"],
          ["<b>Anneau tournant fixé aux pales</b> (« ring fan », ventilateurs automobiles)",
           "plus de tourbillon de bout de pale ; la fuite passe entre anneau et carter, moins nuisible, freinée par un joint "
           "sans contact (lèvre dans une gorge du pavillon, labyrinthe) ; pales rigidifiées, donc plus minces ; 2–3 mm de jeu tolérés (fabrication, givre)",
           "frottement de l'air sur l'anneau ≈ 1 W à 500 mm ; un peu d'inertie",
           '<span class="ok">retenu : à comparer en CFD (jeu 1 à 3 mm)</span>'],
          ["Anneau porté par un roulement en périphérie", "—",
           "couple de frottement ∝ diamètre : graisse et joints d'un roulement fin de 500 mm, quelques à plusieurs dizaines "
           "de W à 600 tr/min (à vérifier sur catalogue) ; givre, eau et poussière dans le contact ; bruit transmis au carter ; coût",
           '<span class="alerte">écarté</span>'],
          ["Moteur en périphérie (rim-driven)", "plus de moyeu : +14 % de section (moyeu 0,35 D), −23 % d'énergie de l'air sortant",
           "entrefer ≈ 1 mm sur 500 mm de diamètre, aimants coûteux, paliers à l'air froid et humide",
           "intéressant mais <b>trop cher</b> : hors premier prototype"]])}
<p class="note">Gain attendu de l'anneau : quelques points de rendement (2 à 5 estimés, pas encore de mesure sur un
ventilateur comparable).</p></div>"""))

    modp = modele_animation(CAS_PALES)
    lignes_p = []
    if modp:
        for k, r in modp.items():
            lignes_p.append([k, f"{r['n']:.0f}", fr(r["Re"] / 1000, 0) + " k", fr(r["Pel"], 1), f"<b>{fr(r['eta'], 3)}</b>"])
    sections.append(("pale", "Quelle pale pour notre système", f"""<div class="carte">
<p>Notre cas : axial basse pression (25 Pa), rotor de 500 mm à ≈ 500–600 tr/min à l'extérieur, 280 mm à ≈ 1 000 tr/min
à l'intérieur, Reynolds de pale 50 000–150 000. Ce que dit la recherche, point par point :</p>
{tableau(["Choix", "Ce que dit la recherche", "Pour nous"],
 [["<b>Profil</b>", "Sous Re ≈ 10⁵, la plaque cambrée mince (arc de cercle, ≈ 3 % d'épaisseur, bord d'attaque arrondi) "
   "vaut ou bat les profils épais type NACA : leur traînée explose à bas Reynolds, pas celle de la plaque" + s("balla", "koning") +
   ". Modèles mesurés de portance et traînée : Re 40 000–140 000, cambrure 0–8 %, C_L 0–1,3, C_D 0,02–0,14" + s("balla") +
   ". Au-dessus de ≈ 1,5·10⁵, les profils minces dessinés pour le bas Reynolds (famille SD, Selig) deviennent intéressants" + s("selig") + ".",
   "<b>plaque cambrée 4–7 %, épaisseur 3 %</b>, bords arrondis : simple à imprimer et à mouler, légère"],
  ["<b>Nombre de pales et corde</b>", "Les hélices d'unités extérieures de PAC sont à 3 pales très larges, semi-carénées" + s("demi_carene") +
   ". Exemple publié : 401 mm, 3 pales, moyeu 0,25, corde 67 → 318 mm du pied au bout, calage 46 → 69°, 839 tr/min, "
   "1 780 m³/h, rendement total 65 → 68 % après optimisation" + s("frontiers") + ".",
   "<b>3 à 4 pales larges</b> : à solidité égale, la corde double et le Reynolds aussi (≈ 150 000 au lieu de 75 000)"],
  ["<b>Répartition le long de la pale</b>", "Passer d'un tourbillon libre à un tourbillon contrôlé (pied de pale moins chargé) : "
   "+4,2 points" + s("jafm_cv") + " ; à faible rapport moyeu / diamètre, +3,9 à 4,6 points de rendement" + s("twente") +
   ". Un tourbillon contrôlé crée des migrations radiales : il faut redessiner les sections en conséquence" + s("vad_sweep") + ".",
   "<b>tourbillon contrôlé</b>, moyeu 0,25–0,30 (le BLDC à rotor extérieur tient dans 100–150 mm)"],
  ["<b>Faucille</b>", "Faucille avant au bout de pale : +3 points et −1,1 dB sur le ventilateur de PAC de 401 mm" + s("frontiers") +
   " ; moins de fluctuations de pression en paroi et moins de bruit sur un 495 mm" + s("sanjose") +
   ". Hors point nominal (faible débit), la faucille arrière est plus silencieuse" + s("revue_sweep") + ".",
   "<b>faucille avant modérée</b> ; à vérifier en conditions de givre"],
  ["<b>Bout de pale</b>", "Anneau tournant + chevauchement axial avec le carter = joint à labyrinthe ; l'anneau améliore le "
   "rendement volumétrique, la fuite résiduelle fait du bruit quand la pale est très chargée" + s("brevet_ring", "genes") + ".",
   "<b>anneau tournant + labyrinthe</b> (déjà retenu)"],
  ["<b>Pavillon et installation</b>", "Pavillon redessiné : +1,2 %" + s("pavillon") + ". Une pale optimisée montée dans "
   "l'unité fait mieux qu'une pale optimisée seule ; les gros changements sont au bout de pale" + s("ijr") +
   ". L'air qui arrive de la batterie n'est pas uniforme : décollements et bruit" + s("demi_carene") + ".",
   "<b>optimiser la pale avec la batterie et le pavillon</b> dans la CFD, pas isolée"],
  ["<b>Bords</b>", "Bord de fuite dentelé : −2 à −4 dB, petit coût ; tubercules : marge au décrochage (voir Biomimétisme).",
   "bord de fuite dentelé ; tubercules en option pour le givre"]])}
<h3>Nombre de pales, avec le modèle de l'animation</h3>
{tableau(["Rotor extérieur 500 mm optimisé (anneau, diffuseur, stator, calage 34°)", "tr/min", "Reynolds", "P élec. W", "η global"],
         lignes_p, num=range(1, 5)) if lignes_p else ""}
<p class="note">À solidité comparable, moins de pales plus larges gagnent ≈ 1,5 point et tournent moins vite (moins de
bruit) ; le profil bas Reynolds gagne 3 à 4 points sur la plaque standard. Ces écarts viennent directement de la loi de
traînée supposée dans le modèle (voir les hypothèses de l'animation) : ce sont des tendances, que la CFD devra chiffrer.</p>
<h3>Pale de départ proposée</h3>
<span class="f">extérieur : Ø 500 mm, moyeu 0,25–0,30, 3 à 4 pales, corde ≈ 150 mm au pied → 220–250 mm au bout
            plaque cambrée arc de cercle 3 % d'épaisseur, cambrure 5–6 %, bords arrondis
            tourbillon contrôlé, faucille avant modérée, anneau tournant + labyrinthe, pavillon soigné
            bord de fuite dentelé ; ≈ 500–550 tr/min ; BLDC rotor extérieur + FOC
intérieur : Ø 280 mm, même famille, 5 pales, corde ≈ 90–110 mm (Re ≈ 70 000–100 000 : la plaque cambrée s’impose)</span>
</div>"""))

    sections.append(("familles2", "Les autres formes de roue : blower, centrifuge, tangentielle", f"""<div class="carte">
{fig_html(fig_familles(), "Les grandes formes de roue, vues de face (schémas).")}
<h3>Ce que fait un climatiseur de fenêtre classique</h3>
<p>Un seul moteur à double arbre, en général asynchrone PSC à 3 vitesses, entraîne à la fois
la <b>roue blower</b> côté pièce et l'<b>hélice « slinger »</b> côté extérieur{s("friedrich", "fasco")}.
La roue blower est une centrifuge à aubes avant ; elle souffle l'air de la pièce à travers l'évaporateur.
La slinger est une hélice axiale à <b>anneau en bout de pales</b> : c'est déjà un « ring fan ». Elle aspire l'air
à travers le condenseur et projette l'eau de condensation du bac sur la batterie.</p>
{tableau(["", "Fenêtre classique", "Notre PAC"],
 [["Moteurs", "1 moteur PSC à double arbre (30–50 %)", "2 BLDC + FOC indépendants (80–85 %)"],
  ["Vitesses", "liées entre elles, 3 crans", "continues, réglées séparément (dégivrage : extérieur seul, intérieur arrêté)"],
  ["Intérieur", "roue blower : compacte, lente, silencieuse, tourne l'air de 90°", "à choisir (tableau ci-dessous)"],
  ["Extérieur", "hélice axiale à anneau (slinger)", "axiale à anneau + labyrinthe (même famille, mieux dessinée)"],
  ["Eau de condensation", "projetée sur le condenseur (gain de capacité en clim)", "piste à garder en clim ; en chauffage, la batterie extérieure givre : pas de slinger"]])}
<h3>Familles de roues</h3>
{tableau(["Famille", "Forme des aubes", "Coef. de pression ψ", "Rendement de pointe publié", "Points forts", "Points faibles"],
 [["<b>Roue blower</b> (sirocco, centrifuge aubes avant)", "36 à 60 aubes courtes, courbées vers l'avant", "≈ 2–3",
   "statique 0,55–0,68" + s("bee", "yaskawa") + " (grandes roues)", "très compacte et lente pour un débit donné, silencieuse, courbe plate",
   "rendement plus bas ; puissance qui monte avec le débit ; la volute compte beaucoup (+5 %" + s("volute") + ", −6,4 dB" + s("volute_xjtu") + ")"],
  ["<b>Centrifuge aubes arrière</b> (roue libre, EC)", "6 à 12 aubes longues, courbées vers l'arrière, parfois profilées", "≈ 0,8–1,1",
   "statique ≤ 0,80, profilée ≤ 0,84" + s("yaskawa", "ashrae") + " ; module EC de 250 mm : global 0,47–0,56" + s("radical", "radical11"),
   "le meilleur rendement, courbe stable, puissance plafonnée", "plus grosse et plus rapide qu'une blower ; à l'aise à des centaines de Pa, pas à 25 Pa"],
  ["Centrifuge aubes radiales", "aubes droites", "≈ 1–2", "plus bas", "robuste, s'encrasse peu", "rendement et bruit : sans intérêt ici"],
  ["<b>Tangentielle</b> (cross-flow)", "tambour à aubes avant, l'air le traverse", "≈ 2", "faible" + s("vanaei", "himeur"),
   "nappe d'air large et plate, silencieuse : le standard des splits muraux", "rendement le plus bas, sensible au tourbillon interne"],
  ["<b>Diagonale</b>", "pales en hélice sur un moyeu conique", "≈ 0,4–0,6", "≈ 0,48–0,56" + s("diaforce"), "entre les deux", "encombrement axial"],
  ["<b>Axiale</b>", "pales en hélice", "≈ 0,1–0,3", "0,45–0,60 avec diffuseur", "grand débit, faible pression : <b>notre extérieur</b>", "besoin de diamètre ; l'air ne tourne pas tout seul de 90°"]])}
<p class="note">ψ = 2Δp / (ρu²), avec u la vitesse en bout de roue. Plus ψ est grand, plus la roue est petite et lente pour une même
pression. Les rendements publiés sont ceux de grandes roues ; à petite taille, tous perdent des points, pour les raisons de la
section « Pourquoi le rendement est si bas ».</p>
<h3>Côté intérieur : quelle roue pour 800 m³/h ?</h3>
{table_interieur()}
<p class="note">Hypothèses : 40 Pa à fournir (25 Pa de batterie + ≈ 15 Pa de grille et de virage de l'air) ; coefficients de débit
supposés de 0,5 (blower), 0,25 (aubes arrière) et 0,6 (tangentielle) ; diamètre choisi pour chaque famille. Ce sont des ordres de
grandeur pour comparer les encombrements, pas un dimensionnement.</p>
<p><b>Lecture.</b> À l'extérieur, l'axiale à anneau reste le bon choix : grand débit, 25 Pa, et la place existe côté façade.
À l'intérieur, tout dépend de la place dans la fenêtre. La roue blower fait 800 m³/h avec une roue de Ø 160 mm à ≈ 600 tr/min :
c'est pour cela que les climatiseurs l'utilisent. Elle tourne l'air de 90° sans caisson et reste très silencieuse, mais
rend moins bien. L'axiale de 280 mm rend mieux, à condition d'avoir la profondeur et un caisson pour tourner l'air.
La centrifuge à aubes arrière n'est intéressante que si la perte de charge intérieure dépasse nettement 25 Pa
(filtre, grilles). <b>À trancher avec la géométrie de la fenêtre</b> : c'est la même question que le diamètre maximal.</p></div>"""))

    sections.append(("module", "Même ventilateur et même échangeur des deux côtés", section_module()))

    sections.append(("suite", "Étapes suivantes", """<div class="carte"><ol>
<li><b>Fixer le diamètre maximal</b> disponible dans la fenêtre pour chaque ventilateur.</li>
<li>Refaire le budget de ventilation avec la pression totale (batterie + perte de sortie − récupération du
diffuseur), aussi dans <code>conception_echangeur/outils/analytique/pac_calc.py</code>.</li>
<li>Pale axiale de base (méthode de l'élément de pale, ψ ≈ 0,2), puis comparaison en CFD 3D (OpenFOAM, MRF) :
stator redresseur, diffuseur, tubercules, bord de fuite dentelé, winglets, anneau tournant (jeu 1 à 3 mm, avec et sans labyrinthe). Profil choisi pour Re ≈ 50 000–100 000.</li>
<li>Batterie extérieure givrée : vérifier que la pale ne décroche pas quand la perte de charge double.</li>
<li>Prototype : pale imprimée en 3D, moteur BLDC rotor extérieur, carte d'évaluation MCF8316, banc
débit / pression / puissance (ISO 5801).</li></ol></div>"""))

    nav = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t, _ in sections)
    corps = "".join(f'<h2 id="{i}">{t}</h2>{h}' for i, t, h in sections)
    src = "".join(f'<li id="src-{k}"><a href="{u}">{t}</a></li>' for k, t, u in SOURCES)
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Ventilateurs PAC fenêtre</title>
<style>{CSS}</style></head><body><main>
<h1>Ventilateurs de la PAC de fenêtre : pales, biomimétisme, moteur BLDC</h1>
<p class="sous">Recherches et pré-dimensionnement · généré le {date.today().strftime('%d/%m/%Y')} par
<code>conception_ventilateur/outils/fiche_ventilateurs.py</code> · <a href="animation_ventilateur.html"><b>ventilateur interactif</b></a></p>
<nav class="carte"><ol>{nav}<li><a href="#sources">Sources</a></li></ol></nav>
{corps}
<h2 id="sources">Sources</h2><div class="carte"><ol>{src}</ol></div>
</main></body></html>"""


if __name__ == "__main__":
    SORTIE.write_text(page(), encoding="utf-8")
    print(f"{SORTIE} ({SORTIE.stat().st_size / 1024:.0f} ko)")
