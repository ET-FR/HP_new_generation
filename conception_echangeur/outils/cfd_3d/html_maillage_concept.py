#!/usr/bin/env python3
"""Page 3D interactive du maillage du concept imprimé : coupes x, y, z déplaçables au curseur (mailles en fil de fer),
solide en transparence. Les coupes sont précalculées (pas de 5 mm en x et z, 6 positions en y) et compressées
(gzip, coordonnées en entiers 16 bits) ; le navigateur les décompresse (DecompressionStream).

    .venv/bin/python conception_echangeur/outils/cfd_3d/html_maillage_concept.py <cas_sans> <cas_avec>
    → docs/formes/cylindre_radial/variante_f/imprime/cfd/maillage_3d_<version>.html
"""
import base64
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs/formes/cylindre_radial/variante_f/imprime/cfd"


def aretes(coupe, o, s):
    """Arêtes uniques d'une coupe → Uint16 (x, y, z) relatifs à la boîte, en base64 gzip."""
    if coupe.n_cells == 0:
        return ""
    e = coupe.extract_all_edges()
    L = e.lines.reshape(-1, 3)[:, 1:]
    p = e.points[L].reshape(-1, 3) * 1e3
    q = np.clip(np.round((p - o) / s), 0, 65535).astype("<u2")
    return base64.b64encode(gzip.compress(q.tobytes(), 6)).decode()


def page(cas):
    cas = Path(cas)
    meta = json.loads((cas / "cas.json").read_text())
    v = meta["version"]
    (cas / "cas.foam").touch()
    r = pv.OpenFOAMReader(str(cas / "cas.foam"))
    r.cell_to_point_creation = False
    vol = r.read()["internalMesh"]
    b = np.array(vol.bounds) * 1e3
    o = np.array([b[0], b[2], b[4]])
    s = (np.array([b[1], b[3], b[5]]) - o).max() / 65000
    coupes = {}
    for ax, n, pos in (("x", (1, 0, 0), np.arange(np.ceil(b[0] / 5) * 5, b[1], 5.0)),
                       ("y", (0, 1, 0), [0.25, 1.0, 1.5, 2.5, 3.5, 4.75]),
                       ("z", (0, 0, 1), np.arange(np.ceil(b[4] / 5) * 5, b[5], 5.0))):
        lst = []
        for c in pos:
            org = [0, 0, 0]
            org["xyz".index(ax)] = c * 1e-3
            lst.append([round(float(c), 2), aretes(vol.slice(normal=n, origin=org), o, s)])
            print(v, ax, c, flush=True)
        coupes[ax] = lst
    sol = pv.read(cas / "constant/triSurface/paroi.stl").scale(1e3).triangulate()
    sol = sol.clip_box([b[0] - 1, b[1] + 1, 0, b[3], b[4] - 1, b[5] + 1], invert=False).triangulate()
    if sol.n_cells > 120000:
        sol = sol.decimate(1 - 120000 / sol.n_cells)
    tri = sol.points[sol.faces.reshape(-1, 4)[:, 1:]].reshape(-1, 3)
    tq = np.clip(np.round((tri - o) / s), 0, 65535).astype("<u2")
    donnees = dict(o=o.tolist(), s=float(s), coupes=coupes,
                   solide=base64.b64encode(gzip.compress(tq.tobytes(), 6)).decode(),
                   info=json.loads((SORTIE / f"maillage_{v}.json").read_text()) if (SORTIE / f"maillage_{v}.json").exists() else {})
    titre = f"Maillage CFD 3D, {'sans' if v == 'sans' else 'avec'} stries"
    html = MODELE.replace("__TITRE__", titre).replace("__DONNEES__", json.dumps(donnees)).replace(
        "__AUTRE__", f"maillage_3d_{'avec' if v == 'sans' else 'sans'}.html").replace(
        "__AUTRE_NOM__", "avec stries" if v == "sans" else "sans stries")
    (SORTIE / f"maillage_3d_{v}.json").write_text(json.dumps(donnees))     # repris par html_radial.py (document principal)
    out = SORTIE / f"maillage_3d_{v}.html"
    out.write_text(html)
    print(out, round(len(html) / 1e6, 1), "Mo")


MODELE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITRE__</title>
<style>
:root { --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; } }
:root[data-theme="dark"] { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; }
* { box-sizing:border-box; } body { margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,sans-serif; }
main { max-width:1300px; margin:0 auto; padding:16px; } h1 { font-size:20px; margin:0 0 4px; } .aide { color:var(--doux); font-size:13px; }
#vue { width:100%; height:72vh; min-height:480px; background:#fff; border:1px solid var(--trait); border-radius:10px; overflow:hidden; }
.ctrl { display:grid; grid-template-columns:auto 1fr auto; gap:6px 12px; align-items:center; margin:10px 0; font-size:14px; }
.ctrl input[type=range] { width:100%; } .pastille { width:12px; height:12px; border-radius:3px; display:inline-block; margin-right:4px; }
button { font:inherit; padding:3px 10px; border-radius:6px; border:1px solid var(--trait); background:var(--carte); color:var(--texte); cursor:pointer; }
.ligne { display:flex; flex-wrap:wrap; gap:6px 14px; align-items:center; font-size:14px; margin:6px 0; }
#charge { position:absolute; margin:12px; color:#495057; font-size:14px; }
</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head><body><main>
<h1>__TITRE__</h1>
<p class="aide">Tranche périodique de 5 mm (axe du tube selon y) du concept imprimé, tube Ø 150. Chaque curseur déplace une coupe
(mailles en fil de fer) ; le solide (lamelles décalées et profils) est en transparence. Rotation au clic gauche, zoom à la molette,
déplacement au clic droit. Voir aussi la version <a href="__AUTRE__">__AUTRE_NOM__</a>.</p>
<div id="vue"><div id="charge">Décompression du maillage…</div></div>
<div class="ctrl">
  <label><input type="checkbox" id="cx" checked> <span class="pastille" style="background:#e03131"></span>coupe x</label><input type="range" id="sx"><span id="tx"></span>
  <label><input type="checkbox" id="cy" checked> <span class="pastille" style="background:#1c7ed6"></span>coupe y (le long du tube)</label><input type="range" id="sy"><span id="ty"></span>
  <label><input type="checkbox" id="cz" checked> <span class="pastille" style="background:#2f9e44"></span>coupe z</label><input type="range" id="sz"><span id="tz"></span>
</div>
<div class="ligne"><label><input type="checkbox" id="cs" checked> solide (lamelles, profils)</label>
  <label>opacité <input type="range" id="os" min="0" max="1" step="0.05" value="0.35" style="width:120px"></label>
  <span>Vue :</span><span id="vues"></span></div>
<p class="aide" id="info"></p>
</main>
<script type="module">
import * as THREE from "three";
import { TrackballControls } from "three/addons/controls/TrackballControls.js";
const D = __DONNEES__;
async function degz(b64) {
  if (!b64) return new Uint16Array(0);
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const flux = new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Uint16Array(await new Response(flux).arrayBuffer());
}
const versF = u => { const f = new Float32Array(u.length); for (let i = 0; i < u.length; i += 3) {
  f[i] = D.o[0] + u[i] * D.s; f[i + 1] = D.o[1] + u[i + 1] * D.s; f[i + 2] = D.o[2] + u[i + 2] * D.s; } return f; };
const boite = document.getElementById("vue");
const rendu = new THREE.WebGLRenderer({ antialias: true }); rendu.setPixelRatio(window.devicePixelRatio); rendu.setClearColor(0xffffff);
boite.appendChild(rendu.domElement);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.3));
const sol = new THREE.DirectionalLight(0xffffff, 0.9); sol.position.set(1, -2, 2); scene.add(sol);
const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 5000);
const ctl = new TrackballControls(cam, rendu.domElement); ctl.rotateSpeed = 3;
// solide
const gS = new THREE.BufferGeometry(); gS.setAttribute("position", new THREE.BufferAttribute(versF(await degz(D.solide)), 3)); gS.computeVertexNormals();
const mS = new THREE.MeshStandardMaterial({ color: 0x868e96, transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide });
const solide = new THREE.Mesh(gS, mS); scene.add(solide);
// coupes
const COUL = { x: 0xe03131, y: 0x1c7ed6, z: 0x2f9e44 }, cache = { x: {}, y: {}, z: {} }, lignes = {};
for (const ax of "xyz") {
  lignes[ax] = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: COUL[ax] }));
  scene.add(lignes[ax]);
  const sl = document.getElementById("s" + ax), L = D.coupes[ax];
  sl.min = 0; sl.max = L.length - 1; sl.step = 1; sl.value = Math.floor(L.length / 2);
  const maj = async () => { const i = +sl.value;
    if (!cache[ax][i]) cache[ax][i] = versF(await degz(L[i][1]));
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(cache[ax][i], 3));
    lignes[ax].geometry.dispose(); lignes[ax].geometry = g;
    document.getElementById("t" + ax).textContent = `${ax} = ${L[i][0].toFixed(2).replace(".", ",")} mm`; };
  sl.oninput = maj; await maj();
  document.getElementById("c" + ax).onchange = e => { lignes[ax].visible = e.target.checked; };
}
document.getElementById("cs").onchange = e => { solide.visible = e.target.checked; };
document.getElementById("os").oninput = e => { mS.opacity = +e.target.value; };
document.getElementById("charge").remove();
const bb = new THREE.Box3().setFromObject(solide), c = bb.getCenter(new THREE.Vector3()), r = bb.getSize(new THREE.Vector3()).length();
ctl.target.copy(c);
const VUES = [["3D", [1, -1.4, 0.8], [0, 0, 1]], ["Le long du tube (y)", [0, -1, 0], [0, 0, 1]], ["Dessus (z)", [0, 0, 1], [1, 0, 0]],
              ["Côté (x)", [1, 0, 0], [0, 0, 1]]];
function vue(d, u) { cam.position.copy(c).add(new THREE.Vector3(...d).normalize().multiplyScalar(r * 1.3)); cam.up.set(...u); ctl.target.copy(c); cam.lookAt(c); ctl.update(); }
for (const [n, d, u] of VUES) { const b = document.createElement("button"); b.textContent = n; b.onclick = () => vue(d, u); document.getElementById("vues").append(b, " "); }
vue(VUES[0][1], VUES[0][2]);
const I = D.info;
if (I.cellules) document.getElementById("info").textContent =
  `${(I.cellules / 1e6).toFixed(2).replace(".", ",")} million de mailles ; checkMesh : ${I.checkMesh_ok ? "Mesh OK" : "OK sauf faces très biaisées"} ; ` +
  `non-orthogonalité max ${Math.round(I.non_orthogonalite_max)}° ; centres de mailles dans le solide : ${I.centres_dans_le_solide} sur ${I.echantillon_centres} ; ` +
  `faces périodiques ${Math.round(I.aire_y0_mm2)} / ${Math.round(I.aire_y1_mm2)} mm².`;
function taille() { const w = boite.clientWidth, h = boite.clientHeight; rendu.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); ctl.handleResize(); }
new ResizeObserver(taille).observe(boite); taille();
(function boucle() { requestAnimationFrame(boucle); ctl.update(); rendu.render(scene, cam); })();
</script></body></html>"""

if __name__ == "__main__":
    for c in sys.argv[1:]:
        page(c)
