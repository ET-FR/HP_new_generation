#!/usr/bin/env python3
"""Vue 3D interactive (HTML) d'un ou plusieurs cas « TPMS seul » : trois coupes (normales x, y, z) déplacées par
des curseurs, champ au choix (T, |U|, p), paroi transparente et lignes de courant activables.

Le champ OpenFOAM est ré-échantillonné sur une grille régulière (points hors de l'air = paroi ou propane, masqués),
quantifié sur 8 bits et embarqué dans la page ; les coupes sont calculées dans le navigateur.
La cellule est répétée 2 × 2 en (y, z) (périodicité exacte).

    python outils/cfd_tpms/vue3d_coupes_tpms.py sortie.html cas1 [cas2 ...]
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import pyvista as pv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vue3d_tpms_seul import surface, lignes  # noqa: E402
from figure_tpms_seul import vtk  # noqa: E402

NX, NYZ = 240, 64


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def donnees(cas):
    cas = Path(cas)
    m = json.loads((cas / "cas.json").read_text())
    r = json.loads((cas / "resultat.json").read_text())
    vol, d = vtk(cas)
    L = m["cellule_tpms_mm"] * 1e-3
    x0, x1 = m["x_domaine"]
    h = L / NYZ
    g = pv.ImageData(dimensions=(NX, NYZ, NYZ), spacing=((x1 - x0) / (NX - 1), h, h), origin=(x0, h / 2, h / 2))
    s = g.sample(vol.cell_data_to_point_data())
    ok = np.asarray(s.point_data["vtkValidPointMask"]) > 0
    champs = {}
    U = np.linalg.norm(np.asarray(s.point_data["U"]), axis=1)
    rho = m["air"]["rho"]
    for nom, v, lo, hi in (("T", np.asarray(s.point_data["T"]), 0.0, 1.0),
                           ("U", U, 0.0, float(np.percentile(U[ok], 99.5))),
                           ("p", rho * np.asarray(s.point_data["p"]), None, None)):
        if lo is None:
            lo, hi = float(np.percentile(v[ok], 0.5)), float(np.percentile(v[ok], 99.5))
        q = np.clip(np.round((v - lo) / (hi - lo) * 254), 0, 254).astype(np.uint8) + 1
        q[~ok] = 0                                         # 0 = hors de l'air
        champs[nom] = dict(b=b64(q), lo=lo, hi=hi)        # ordre VTK : x le plus rapide, puis y, puis z
    Lmm = L * 1e3
    paroi = surface(pv.read(d / "boundary" / "paroi.vtp"), None, Lmm, 30_000, color="#c9a227", opacity=0.25,
                    name="paroi (côté air)", showlegend=True, flatshading=False)
    lc = lignes(vol, m)
    lc.visible = "legendonly"
    return dict(nom=cas.name.replace("_L", " ").replace("fks", "Fischer-Koch S").replace("gyroide", "gyroïde")
                + " mm", titre=f"{m['nom']}, bloc {m['profondeur_mm']:.1f} mm : Δp {r['dp_Pa']:.0f} Pa, "
                f"efficacité {100 * r['T_sortie']:.0f} % (ailettes plates, même charge : 5,4 Pa, 72 %)",
                nx=NX, n=NYZ, x0=x0 * 1e3, x1=x1 * 1e3, L=Lmm, D=m["profondeur_mm"], champs=champs,
                traces=json.loads(go.Figure(data=[paroi, lc]).to_json())["data"])


PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Coupes TPMS seul</title>
<script>__PLOTLY__</script>
<style>
body{margin:0;font-family:system-ui,sans-serif;background:#fff;color:#212529}
#barre{display:flex;flex-wrap:wrap;gap:14px 22px;align-items:center;padding:10px 16px;border-bottom:1px solid #dee2e6}
#barre label{font-size:14px;display:flex;align-items:center;gap:6px}
input[type=range]{width:200px}
.val{font-variant-numeric:tabular-nums;min-width:62px;display:inline-block}
#titre{padding:8px 16px 0;font-weight:600;font-size:15px}
#aide{padding:0 16px 8px;font-size:12px;color:#6c757d}
#fig{height:calc(100vh - 150px);min-height:500px}
</style></head><body>
<div id="barre">
 <label>Cas <select id="cas"></select></label>
 <label>Champ <select id="champ"><option value="T">température T (-)</option>
  <option value="U">vitesse |U| (m/s)</option><option value="p">pression (Pa)</option></select></label>
 <label><input type="checkbox" id="cx" checked> x <input type="range" id="sx"><span class="val" id="vx"></span></label>
 <label><input type="checkbox" id="cy" checked> y <input type="range" id="sy"><span class="val" id="vy"></span></label>
 <label><input type="checkbox" id="cz" checked> z <input type="range" id="sz"><span class="val" id="vz"></span></label>
</div>
<div id="titre"></div>
<div id="aide">Case à cocher : affiche la coupe ; curseur : la déplace. Blanc / vide = paroi ou propane.
Air de x &lt; 0 vers x &gt; 0, bloc entre x = 0 et la profondeur. Légende : paroi, lignes de courant. 2 × 2 cellules.</div>
<div id="fig"></div>
<script>
const CAS = __DONNEES__;
const ECH = {T:[[0,"#000004"],[0.25,"#57106e"],[0.5,"#bc3754"],[0.75,"#f98e09"],[1,"#fcffa4"]], U:"Turbo", p:"Viridis"};
const UNITE = {T:"T (-)", U:"|U| (m/s)", p:"p (Pa)"};
const dec = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
CAS.forEach(c => { for (const k in c.champs) c.champs[k].q = dec(c.champs[k].b); });
const $ = id => document.getElementById(id);
CAS.forEach((c, i) => $("cas").add(new Option(c.nom, i)));
let c = CAS[0], camera = null;

function coupe(axe, i) {
  // renvoie x, y, z, couleur (tableaux 2D) pour la coupe de normale `axe` à l'indice i ; 2 × 2 cellules en (y, z)
  const ch = c.champs[$("champ").value], q = ch.q, nx = c.nx, n = c.n, L = c.L, h = L / n;
  const xs = k => c.x0 + (c.x1 - c.x0) * k / (nx - 1), ys = j => (j + 0.5) * h;
  const val = (a, b, d) => { const v = q[a + nx * (b % n + n * (d % n))]; return v ? ch.lo + (v - 1) / 254 * (ch.hi - ch.lo) : null; };
  const X = [], Y = [], Z = [], C = [];
  if (axe === "x") {
    for (let d = 0; d < 2 * n; d++) { const rx = [], ry = [], rz = [], rc = [];
      for (let b = 0; b < 2 * n; b++) { const v = val(i, b, d); rx.push(v === null ? null : xs(i)); ry.push(ys(b)); rz.push(ys(d)); rc.push(v); }
      X.push(rx); Y.push(ry); Z.push(rz); C.push(rc); }
  } else {
    for (let o = 0; o < 2 * n; o++) { const rx = [], ry = [], rz = [], rc = [];
      for (let a = 0; a < nx; a++) { const v = axe === "y" ? val(a, i, o) : val(a, o, i);
        rx.push(xs(a)); if (axe === "y") { ry.push(v === null ? null : ys(i)); rz.push(ys(o)); } else { ry.push(ys(o)); rz.push(v === null ? null : ys(i)); }
        rc.push(v); }
      X.push(rx); Y.push(ry); Z.push(rz); C.push(rc); }
  }
  return {x: X, y: Y, z: Z, surfacecolor: C};
}

function trace(axe) {
  const ch = c.champs[$("champ").value], k = $("champ").value;
  return Object.assign(coupe(axe, +$("s" + axe).value), {type: "surface", name: "coupe " + axe, showlegend: false,
    colorscale: ECH[k], cmin: ch.lo, cmax: ch.hi, showscale: axe === "x", hoverinfo: "skip",
    colorbar: {title: {text: UNITE[k]}, len: 0.6}, visible: $("c" + axe).checked, lighting: {ambient: 1, diffuse: 0}});
}

function etiquettes() {
  const h = c.L / c.n;
  $("vx").textContent = (c.x0 + (c.x1 - c.x0) * $("sx").value / (c.nx - 1)).toFixed(2) + " mm";
  $("vy").textContent = ((+$("sy").value + 0.5) * h).toFixed(2) + " mm";
  $("vz").textContent = ((+$("sz").value + 0.5) * h).toFixed(2) + " mm";
}

function dessiner() {
  etiquettes();
  const lay = {margin: {l: 0, r: 0, t: 0, b: 0}, legend: {x: 0.01, y: 0.98},
    scene: {aspectmode: "data", xaxis: {title: "x, sens de l'air (mm)"}, yaxis: {title: "y (mm)"}, zaxis: {title: "z (mm)"},
            camera: camera || {eye: {x: -1.5, y: -1.3, z: 0.9}}}, uirevision: "garde"};
  Plotly.react("fig", [trace("x"), trace("y"), trace("z"), ...c.traces], lay, {displaylogo: false, responsive: true});
}

function majCoupe(axe) { etiquettes(); Plotly.restyle("fig", coupe(axe, +$("s" + axe).value), ["xyz".indexOf(axe)]); }

function choisirCas() {
  c = CAS[+$("cas").value];
  $("titre").textContent = c.titre;
  $("sx").max = c.nx - 1; $("sx").value = Math.round((c.nx - 1) * (0.5 * c.D - c.x0) / (c.x1 - c.x0));
  for (const a of "yz") { $("s" + a).max = 2 * c.n - 1; $("s" + a).value = c.n; }
  dessiner();
}
$("cas").onchange = choisirCas;
$("champ").onchange = dessiner;
for (const a of "xyz") {
  $("s" + a).min = 0; $("s" + a).oninput = () => majCoupe(a);
  $("c" + a).onchange = () => Plotly.restyle("fig", {visible: $("c" + a).checked}, ["xyz".indexOf(a)]);
}
choisirCas();
</script></body></html>"""


def main(sortie, *cas):
    import plotly.offline
    lib = plotly.offline.get_plotlyjs()
    d = [donnees(c) for c in cas]
    html = PAGE.replace("__PLOTLY__", lib).replace("__DONNEES__", json.dumps(d, separators=(",", ":")))
    Path(sortie).write_text(html)
    print(sortie, f"{Path(sortie).stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main(sys.argv[1], *sys.argv[2:])
