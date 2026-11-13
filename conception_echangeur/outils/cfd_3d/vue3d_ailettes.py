#!/usr/bin/env python3
"""Vue 3D interactive (HTML autonome, plotly) des cas à ailettes plates : on tourne et on zoome à la souris.

    python conception_echangeur/outils/cfd_3d/vue3d_ailettes.py sortie.html cas1 [cas2 ...]

Pour chaque cas : tubes, deux ailettes translucides, coupe horizontale à mi-distance entre les ailettes
(température), coupe verticale à travers les tubes 1 et 3 (vitesse), lignes de courant colorées par la
température. L'épaisseur entre ailettes (1,6 mm) est dilatée pour être visible ; un menu choisit le cas.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import pyvista as pv

OPENFOAM = "/usr/lib/openfoam/openfoam2412/etc/bashrc"
DILATATION = 4.0        # facteur appliqué à z pour la lisibilité


def charger(cas):
    cas = Path(cas)
    if not (cas / "VTK_resultats").exists():
        subprocess.run(f"source {OPENFOAM} >/dev/null 2>&1; foamToVTK -latestTime -fields '(U T p)' "
                       "-name VTK_resultats > log.vtk 2>&1", shell=True, cwd=cas, check=True, executable="/bin/bash")
    d = sorted([p for p in (cas / "VTK_resultats").glob("*_[0-9]*") if p.is_dir()],
               key=lambda p: int(p.name.rsplit("_", 1)[1]))[-1]
    return json.loads((cas / "cas.json").read_text()), json.loads((cas / "resultat.json").read_text()), d


def maillage_tri(surf, champ=None, cible=None):
    """Surface pyvista -> (points en mm, triangles, valeurs aux points), allégée à `cible` triangles."""
    s = surf.extract_surface(algorithm=None)
    if champ is not None and champ not in s.point_data:
        s = s.cell_data_to_point_data()
    f, tris, i = s.faces, [], 0                    # triangulation en éventail, lignes ignorées
    while i < len(f):
        n = f[i]; ids = f[i + 1:i + 1 + n]
        tris += [(ids[0], ids[k], ids[k + 1]) for k in range(1, n - 1)]
        i += n + 1
    tri = np.array(tris)
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]
    t = pv.PolyData(s.points, np.c_[np.full(len(tri), 3), tri].ravel())
    for nom in s.point_data:
        t.point_data[nom] = s.point_data[nom]
    v0 = None
    if champ is not None:
        v0 = t.point_data[champ]
        v0 = np.linalg.norm(v0, axis=1) if v0.ndim > 1 else np.asarray(v0)
    p0 = t.points.copy()
    if cible and t.n_cells > cible:
        t = t.decimate(1 - cible / t.n_cells)
    p = t.points * 1e3
    faces = t.faces.reshape(-1, 4)[:, 1:]
    v = None
    if v0 is not None:                                   # valeurs reprises au point d'origine le plus proche
        from scipy.spatial import cKDTree
        v = v0[cKDTree(p0).query(t.points)[1]]
    return p, faces, v


def mesh3d(p, f, v=None, couleur=None, nom="", echelle=None, cmin=None, cmax=None, opacite=1.0, barre=None,
           visible=True):
    p = np.round(p, 3)                                   # 1 µm : largement assez pour l'affichage, fichier 2 × plus léger
    kw = dict(x=p[:, 0], y=p[:, 1], z=np.round(p[:, 2] * DILATATION, 3), i=f[:, 0], j=f[:, 1], k=f[:, 2], name=nom,
              opacity=opacite, visible=visible, flatshading=False, hoverinfo="skip", showlegend=bool(nom),
              lighting=dict(ambient=0.75, diffuse=0.5, specular=0.1))
    if v is not None:
        kw.update(intensity=np.round(v, 3), colorscale=echelle, cmin=cmin, cmax=cmax, showscale=barre is not None,
                  colorbar=barre)
    else:
        kw.update(color=couleur)
    return go.Mesh3d(**kw)


def traces_cas(cas, visible):
    """Retourne (traces, titre) ; chaque trace porte sa visibilité par défaut dans trace.meta."""
    m, r, d = charger(cas)
    ecart, Pt = m["epaisseur_mm"] * 1e-3, m["Pt"]
    xa, xb = m["x_noyau"][0] - 0.008, m["x_noyau"][1] + 0.012          # batterie + un peu d'avant / après
    vol = pv.read(d / "internal.vtu").clip_box((xa, xb, -1, 1, -1, 1), invert=False).cell_data_to_point_data()
    tr = []
    # tubes (paroi) et ailettes (translucides)
    p, f, _ = maillage_tri(pv.read(d / "boundary" / "paroi.vtp"), cible=12000)
    tr.append(mesh3d(p, f, couleur="#c0392b", nom="tubes", visible=visible))
    tpms = m.get("tpms")
    for nom in (("ailette",) if tpms else ("ailette_bas", "ailette_haut")):
        p, f, _ = maillage_tri(pv.read(d / "boundary" / f"{nom}.vtp"), cible=40000 if tpms else 8000)
        tr.append(mesh3d(p, f, couleur="#9aa5b1", nom=("surface TPMS" if tpms else "ailettes") if nom != "ailette_haut" else "",
                         opacite=0.45 if tpms else 0.25, visible=visible))
    # coupe horizontale à mi-distance : température
    s = vol.slice(normal="z", origin=(0, 0, 0.5 * ecart))
    p, f, v = maillage_tri(s, "T", cible=35000)
    tr.append(mesh3d(p, f, v, nom="température (mi-distance)", echelle="Inferno", cmin=0, cmax=1,
                     barre=dict(title="T", x=1.0, len=0.45, y=0.75), visible=visible))
    # coupe verticale à travers les tubes 1 et 3 : vitesse
    s = vol.slice(normal="y", origin=(0, 0.5 * Pt, 0))
    p, f, v = maillage_tri(s, "U", cible=12000)
    tr.append(mesh3d(p, f, v, nom="vitesse (coupe verticale)", echelle="Turbo", cmin=0,
                     cmax=float(np.percentile(v, 99.5)),
                     barre=dict(title="|U| m/s", x=1.08, len=0.45, y=0.25), visible=visible))
    # autres hauteurs : température près de l'ailette et au quart de l'écart (masquées au départ)
    for zr, nom in ((0.05e-3, "température à 0,05 mm de l'ailette"), (0.25 * ecart, "température au quart de l'écart")):
        s = vol.slice(normal="z", origin=(0, 0, zr))
        p, f, v = maillage_tri(s, "T", cible=10000)
        t = mesh3d(p, f, v, nom=nom, echelle="Inferno", cmin=0, cmax=1, visible=visible)
        t.meta = "legendonly"; tr.append(t)
    # maillage : arêtes de la coupe verticale y = 0,2 Pt, bord d attaque de l ailette (on y voit les tranches)
    x0f = m["x_noyau"][0]
    s = vol.slice(normal="y", origin=(0, 0.2 * Pt, 0)).clip_box((x0f - 0.002, x0f + 0.005, -1, 1, -1, 1),
                                                                invert=False).extract_all_edges()
    seg = s.lines.reshape(-1, 3)[:, 1:]
    pts = s.points * 1e3
    xyz = np.full((3 * len(seg), 3), np.nan)
    xyz[0::3], xyz[1::3] = pts[seg[:, 0]], pts[seg[:, 1]]
    xyz = np.round(xyz, 3)
    t = go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1] - 0.01, z=np.round(xyz[:, 2] * DILATATION, 3), mode="lines",
                     line=dict(color="#1c3d6e", width=1.5), name=(f"maillage : {m['tranches']['n']} tranches (coupe)" if not tpms else "maillage (coupe)"),
                     hoverinfo="skip", visible=visible)
    t.meta = "legendonly"; tr.append(t)
    # lignes de courant depuis l'entrée, colorées par la température
    x0 = m["x_noyau"][0] - 0.004
    graine = pv.Line((x0, 0.05 * Pt, 0.5 * ecart), (x0, 0.95 * Pt, 0.5 * ecart), resolution=14)
    graine = graine + pv.Line((x0, 0.05 * Pt, 0.15 * ecart), (x0, 0.95 * Pt, 0.15 * ecart), resolution=8)
    try:
        sl = vol.streamlines_from_source(graine, vectors="U", max_steps=4000, integration_direction="forward",
                                         max_length=0.2)
        for k in range(sl.n_cells):
            c = sl.get_cell(k)
            ids = c.point_ids
            pts = sl.points[ids] * 1e3
            T = sl.point_data["T"][ids]
            tr.append(go.Scatter3d(x=pts[:, 0], y=pts[:, 1], z=pts[:, 2] * DILATATION, mode="lines",
                                   line=dict(color=T, colorscale="Inferno", cmin=0, cmax=1, width=4),
                                   name="ligne de courant", showlegend=False, hoverinfo="skip", visible=visible))
    except Exception as e:                                       # noqa: BLE001
        print("lignes de courant :", e)
    q = 1.2 * 1006 * m["U"] * r["T_sortie"] * 10 / 1e3
    desc = f"{m['rangs']} rangs" if tpms else f"pas {m['pas_ailettes_mm']:g} mm, {m['rangs']} rangs"
    titre = (f"{m['nom']} ({desc}) : Δp {r['dp_Pa']:.1f} Pa, "
             f"efficacité {100 * r['T_sortie']:.0f} %, {q:.1f} kW/m² de face, ailettes {100 * r['part_ailettes']:.0f} %")
    return tr, titre


def figure(cas_liste, hauteur=820):
    """Figure plotly (menu pour choisir le cas)."""
    traces, titres, bornes = [], [], []
    for k, cas in enumerate(cas_liste):
        tr, t = traces_cas(cas, visible=(k == 0))
        bornes.append((len(traces), len(traces) + len(tr)))
        traces += tr; titres.append(t)
        print(Path(cas).name, len(tr), "objets")
    defaut = [t.meta if t.meta == "legendonly" else True for t in traces]
    for t, d0 in zip(traces, defaut):
        if t.visible and d0 == "legendonly":
            t.visible = "legendonly"
        t.meta = None
    boutons = []
    for k, (a, b) in enumerate(bornes):
        vis = [defaut[i] if a <= i < b else False for i in range(len(traces))]
        boutons.append(dict(label=Path(cas_liste[k]).name, method="update",
                            args=[{"visible": vis}, {"title.text": titres[k]}]))
    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text=titres[0], x=0.02, font=dict(size=15)),
        # mêmes échelles en x et y (z dilaté, voir DILATATION)
        scene=dict(aspectmode="data", xaxis_title="x, sens de l'air (mm)", yaxis_title="y (mm)",
                   zaxis_title=f"z (mm × {DILATATION:g})", camera=dict(eye=dict(x=-0.9, y=-1.3, z=0.9)),
                   bgcolor="white"),
        updatemenus=[dict(buttons=boutons, direction="down", x=0.02, y=0.98, xanchor="left", yanchor="top")]
        if len(boutons) > 1 else [],
        margin=dict(l=0, r=0, t=60, b=40), height=hauteur,
        annotations=[dict(text="Souris : glisser = tourner, molette = zoom, clic droit = déplacer. "
                               "Légende : un clic masque ou affiche un objet. Épaisseur entre ailettes dilatée "
                               f"× {DILATATION:g}.", x=0.02, y=0.01, xref="paper", yref="paper",
                          showarrow=False, font=dict(size=12, color="#495057"))],
        legend=dict(x=0.02, y=0.88, bgcolor="rgba(255,255,255,0.7)"))
    return fig


def main(sortie, cas_liste):
    fig = figure(cas_liste)
    fig.write_html(sortie, include_plotlyjs=True, full_html=True, config=dict(displaylogo=False))
    print(sortie, f"{Path(sortie).stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
