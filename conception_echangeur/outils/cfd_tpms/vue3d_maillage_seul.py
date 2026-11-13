#!/usr/bin/env python3
"""Vue 3D interactive (HTML, plotly) du maillage d'un cas TPMS seul : paroi, mailles de deux coupes.

    python conception_echangeur/outils/cfd_tpms/vue3d_maillage_seul.py dossier_du_cas sortie.html
"""
import json
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import pyvista as pv

PAROI = 0.3e-3        # épaisseur de paroi (m) entre air et propane, pour l'affichage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cfd_3d"))
from vue3d_ailettes import maillage_tri  # noqa: E402


def aretes(s, nom, couleur, visible=True):
    e = s.extract_all_edges()
    seg = e.lines.reshape(-1, 3)[:, 1:]
    p = e.points * 1e3
    xyz = np.full((3 * len(seg), 3), np.nan)
    xyz[0::3], xyz[1::3] = p[seg[:, 0]], p[seg[:, 1]]
    xyz = np.round(xyz, 4)
    return go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode="lines", line=dict(color=couleur, width=1.2),
                        name=nom, hoverinfo="skip", visible=True if visible else "legendonly")


def main(cas, sortie):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    d = sorted(p for p in (cas / "VTK_m").glob("*_0") if p.is_dir())[0]
    vol = pv.read(d / "internal.vtu")
    L, D = m["L"], m["profondeur"]
    tr = []
    p, f, _ = maillage_tri(pv.read(d / "boundary" / "solide.vtp"))
    tr.append(go.Mesh3d(x=p[:, 0], y=p[:, 1], z=p[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2], color="#c9a227",
                        opacity=1.0, name="paroi (côté air)", showlegend=True, hoverinfo="skip", flatshading=False,
                        lighting=dict(ambient=0.55, diffuse=0.7, specular=0.2)))
    tr.append(aretes(pv.read(d / "boundary" / "solide.vtp"), "mailles sur la paroi", "#5c4a0e", visible=False))
    tr.append(aretes(vol.slice(normal="z", origin=(0, 0, 0.5 * L)), "mailles, coupe z = L/2", "#1c3d6e"))
    tr.append(aretes(vol.slice(normal="x", origin=(0.5 * D, 0, 0)), "mailles, coupe x = mi-noyau", "#2a78d6", False))
    tr.append(aretes(vol.slice(normal="y", origin=(0, 0.5 * L, 0)), "mailles, coupe y = L/2", "#7b3294", False))
    # réseau propane (non calculé : paroi supposée à la température du propane) : F < niveau, à une
    # épaisseur de paroi `PAROI` de la surface côté air (distance signée approchée (F - n) / |∇F|)
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from pac_fenetre.tpms import champ
    N = 90
    xs = np.linspace(0, D, max(30, int(N * D / L))); ys = np.linspace(0, L, N)
    X, Y, Z = np.meshgrid(xs, ys, ys, indexing="ij")
    k = 2 * np.pi / L
    F = champ(m["surface"], k * X, k * Y, k * Z)
    gx, gy, gz = np.gradient(F, xs, ys, ys)
    dist = (F - m["niveau"]) / np.maximum(np.sqrt(gx ** 2 + gy ** 2 + gz ** 2), 1e-9)   # m, < 0 côté solide
    g = pv.StructuredGrid(X, Y, Z); g.point_data["d"] = dist.ravel(order="F")
    prop = g.contour([-PAROI], scalars="d")
    p, f, _ = maillage_tri(prop)
    tr.append(go.Mesh3d(x=p[:, 0], y=p[:, 1], z=p[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2], color="#2a78d6",
                        opacity=0.55, name=f"canaux propane (paroi {PAROI * 1e3:g} mm)", showlegend=True,
                        hoverinfo="skip"))
    fig = go.Figure(tr)
    fig.update_layout(
        title=dict(text=f"Maillage : {m['nom']} seul, cellule {L * 1e3:.1f} mm, porosité air {m['phi_air']:.2f}, "
                        f"noyau {D * 1e3:g} mm, {vol.n_cells:,} mailles".replace(",", " "), x=0.02),
        scene=dict(aspectmode="data", xaxis_title="x, sens de l'air (mm)", yaxis_title="y (mm)", zaxis_title="z (mm)",
                   camera=dict(eye=dict(x=-1.4, y=-1.4, z=1.0)), bgcolor="white"),
        legend=dict(x=0.02, y=0.92), margin=dict(l=0, r=0, t=50, b=30), height=850,
        annotations=[dict(text="Glisser = tourner, molette = zoom, clic droit = déplacer. Légende : un clic affiche ou "
                               "masque un objet. Air : de x < 0 vers x > 0 ; tampons amont / aval sans paroi.",
                          x=0.02, y=0.01, xref="paper", yref="paper", showarrow=False, font=dict(size=12))])
    fig.write_html(sortie, include_plotlyjs=True, config=dict(displaylogo=False))
    print(sortie, f"{Path(sortie).stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
