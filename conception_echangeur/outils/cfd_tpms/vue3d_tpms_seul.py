#!/usr/bin/env python3
"""Vue 3D interactive (HTML, plotly) d'un ou plusieurs cas « TPMS seul » terminés : paroi, lignes de courant
colorées par la température de l'air, coupes de température et de vitesse. Un menu choisit le cas.

La cellule calculée est répétée 2 × 2 dans le plan de la face (périodicité exacte) pour la lecture.

    python outils/cfd_tpms/vue3d_tpms_seul.py sortie.html cas1 [cas2 ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import pyvista as pv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cfd_3d"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vue3d_ailettes import maillage_tri  # noqa: E402
from figure_tpms_seul import vtk  # noqa: E402

REPET = 2
ECHELLE_T = [[0, "#000004"], [0.25, "#57106e"], [0.5, "#bc3754"], [0.75, "#f98e09"], [1, "#fcffa4"]]


def copies(p, L):
    """Points (n, 3) en mm -> liste des translations 2 × 2 en (y, z)."""
    return [p + np.array([0, i * L, j * L]) for i in range(REPET) for j in range(REPET)]


def surface(s, champ, L, cible, **kw):
    p, f, v = maillage_tri(s, champ, cible)
    P, F, V = [], [], []
    for k, q in enumerate(copies(p, L)):
        P.append(q); F.append(f + k * len(p)); V.append(v if v is not None else np.zeros(len(p)))
    P, F, V = np.round(np.vstack(P), 3), np.vstack(F), np.round(np.concatenate(V), 3)
    return go.Mesh3d(x=P[:, 0], y=P[:, 1], z=P[:, 2], i=F[:, 0], j=F[:, 1], k=F[:, 2],
                     intensity=V if champ else None, hoverinfo="skip", **kw)


def lignes(vol, m, n=70, pavage=4):
    """Lignes de courant calculées dans un pavage pavage × pavage de la cellule (périodicité exacte en y et z) :
    elles passent d'une cellule à la voisine sans coupure. Graines au centre du pavage, en amont du bloc."""
    L = m["cellule_tpms_mm"] * 1e-3
    x0, x1 = m["x_domaine"]
    v = vol.cell_data_to_point_data()
    blocs = [v.translate((0, i * L, j * L), inplace=False) for i in range(pavage) for j in range(pavage)]
    pav = blocs[0].merge(blocs[1:], merge_points=False)
    c = L                                        # graines dans les cellules 1 et 2 : 2 × 2 cellules affichées
    rng = np.random.default_rng(1)
    graines = np.c_[np.full(n, 0.6 * x0), c + rng.uniform(0.02, 1.98, n) * L, c + rng.uniform(0.02, 1.98, n) * L]
    st = pav.streamlines_from_source(pv.PolyData(graines), vectors="U", integration_direction="forward",
                                     max_length=3 * (x1 - x0), initial_step_length=0.1, max_step_length=0.15,
                                     step_unit="cl", max_steps=6000)
    ech = pv.PolyData(st.points).sample(pav)                      # T ré-échantillonnée aux points des lignes
    Tst = np.array(ech.point_data["T"], dtype=float)
    Tst[np.asarray(ech.point_data["vtkValidPointMask"]) == 0] = np.nan   # points sur les jointures du pavage
    xs, ys, zs, cs = [], [], [], []
    for k in range(st.n_cells):
        ids = st.get_cell(k).point_ids
        P = st.points[ids] * 1e3 - np.array([0, c, c]) * 1e3
        T = Tst[ids]
        ok = ~np.isnan(T)
        if not ok.any():
            continue
        T = np.interp(np.arange(len(T)), np.flatnonzero(ok), T[ok])   # comble les trous par interpolation
        if P[:, 0].max() - P[:, 0].min() < 1.0:
            continue
        xs += list(P[:, 0]) + [None]; ys += list(P[:, 1]) + [None]; zs += list(P[:, 2]) + [None]
        cs += list(T) + [T[-1]]
    r = lambda a: [None if x is None else round(float(x), 3) for x in a]
    return go.Scatter3d(x=r(xs), y=r(ys), z=r(zs), mode="lines", name="lignes de courant (couleur = T)",
                        line=dict(color=[round(float(c), 3) for c in cs], colorscale=ECHELLE_T, cmin=0, cmax=1,
                                  width=4, colorbar=dict(title="T (-)", x=1.0, len=0.6)),
                        hoverinfo="skip")


def traces(cas):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    r = json.loads((cas / "resultat.json").read_text())
    vol, d = vtk(cas)
    L, D = m["cellule_tpms_mm"], m["profondeur_mm"]
    tr = [surface(pv.read(d / "boundary" / "paroi.vtp"), None, L, 30_000, color="#c9a227", opacity=0.35,
                  name="paroi (côté air)", showlegend=True, flatshading=False),
          lignes(vol, m)]
    for k, (nrm, orig, champ, nom, vis) in enumerate((
            ("x", (0.5 * D * 1e-3, 0, 0), "T", "température, plan à mi-bloc", "legendonly"),
            ("x", (0.95 * D * 1e-3, 0, 0), "T", "température, plan en sortie de bloc", "legendonly"),
            ("z", (0, 0, 0.5 * L * 1e-3), "T", "température, coupe dans le sens de l'air", "legendonly"),
            ("z", (0, 0, 0.5 * L * 1e-3), "U", "vitesse |U|, coupe dans le sens de l'air", "legendonly"))):
        s = vol.slice(normal=nrm, origin=orig)
        if champ == "U":
            umax = float(np.percentile(np.linalg.norm(vol.cell_data["U"], axis=1), 99.5))
            tr.append(surface(s, "U", L, 15_000, colorscale="Turbo", cmin=0, cmax=umax, name=nom, showlegend=True,
                              visible=vis, colorbar=dict(title="|U| (m/s)", x=1.08, len=0.6), opacity=1))
        else:
            tr.append(surface(s, "T", L, 15_000, colorscale=ECHELLE_T, cmin=0, cmax=1, name=nom, showlegend=True,
                              visible=vis, showscale=False, opacity=1))
    titre = (f"{m['nom']}, bloc {D:.1f} mm : Δp {r['dp_Pa']:.0f} Pa, efficacité {100 * r['T_sortie']:.0f} % "
             f"(ailettes plates, même charge : 5,4 Pa, 72 %)")
    return tr, titre


def main(sortie, *cas):
    fig = go.Figure()
    groupes, titres = [], []
    for c in cas:
        tr, t = traces(c)
        groupes.append(len(tr)); titres.append(t)
        for x in tr:
            fig.add_trace(x)
    n = sum(groupes)
    boutons, debut = [], 0
    for g, t, c in zip(groupes, titres, cas):
        vis = [False] * n
        for k in range(debut, debut + g):
            vis[k] = True if k - debut < 2 else "legendonly"
        boutons.append(dict(label=Path(c).name.replace("_L", " ").replace("fks", "Fischer-Koch S")
                            .replace("gyroide", "gyroïde") + " mm", method="update",
                            args=[{"visible": vis}, {"title.text": t}]))
        debut += g
    for k, tr in enumerate(fig.data):
        tr.visible = boutons[0]["args"][0]["visible"][k]
    fig.update_layout(
        title=dict(text=titres[0], x=0.02, font=dict(size=15)),
        updatemenus=[dict(buttons=boutons, direction="down", x=0.02, y=1.0, xanchor="left", yanchor="top")],
        scene=dict(aspectmode="data", xaxis_title="x, sens de l'air (mm)", yaxis_title="y (mm)",
                   zaxis_title="z (mm)", camera=dict(eye=dict(x=-1.5, y=-1.3, z=0.9)), bgcolor="white"),
        legend=dict(x=0.02, y=0.88), margin=dict(l=0, r=0, t=50, b=30), height=880,
        annotations=[dict(text="Menu en haut à gauche : choix du cas. Légende : un clic affiche ou masque les coupes. "
                               "Glisser = tourner, molette = zoom. Air de x < 0 vers x > 0 ; 2 × 2 cellules affichées.",
                          x=0.02, y=0.01, xref="paper", yref="paper", showarrow=False, font=dict(size=12))])
    fig.write_html(sortie, include_plotlyjs=True, config=dict(displaylogo=False))
    print(sortie, f"{Path(sortie).stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main(sys.argv[1], *sys.argv[2:])
