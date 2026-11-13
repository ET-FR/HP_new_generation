"""Page HTML 3D du maillage OpenFOAM de l'échangeur Ø 150 (cas créé par creer_cas_d150.py).

Lit, dans le dossier du cas rapatrié :
  VTK_maillage/**.vtp|vtk        surfaces maillées par zone (foamToVTK -noInternal, t = 0)
  postProcessing/coupes/0/*.vtp  coupes du maillage (cellules coupées, sans interpolation)
  log.checkMesh                  qualité du maillage
et écrit <cas>/maillage.html (+ copie dans docs/formes/cylindre_d150_helice/maillage_U5.html).
Arêtes et triangles intégrés en Float32 base64 ; three.js depuis un CDN.

    .venv/bin/python conception_echangeur/outils/cfd_3d/html_maillage_d150.py conception_echangeur/cfd_campagne/d150_helice/U5
"""
import base64
import json
import re
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

RACINE = Path(__file__).resolve().parents[2]
COUL = {"tubes": "#d6336c", "ailette": "#868e96", "parois": "#74c0fc", "entree": "#15aabf", "sortie": "#f59f00"}
COUPES = {"horizontale_bas": "#2b8a3e", "horizontale_mil": "#1c7ed6", "meridienne": "#e8590c"}


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a, dtype=np.float32).tobytes()).decode()


def aretes(m, maxi):
    """Segments (N×2×3) des arêtes des cellules ; sous-échantillonnés au-delà de maxi segments."""
    e = m.extract_all_edges()
    lignes = e.lines.reshape(-1, 3)[:, 1:]
    if len(lignes) > maxi:
        lignes = lignes[np.linspace(0, len(lignes) - 1, maxi).astype(int)]
    return e.points[lignes].reshape(-1, 3), len(e.lines) // 3


def triangles(m, maxi=60000):
    t = m.extract_surface(algorithm="dataset_surface").triangulate()
    if t.n_cells > maxi:
        t = t.decimate_pro(1 - maxi / t.n_cells, preserve_topology=True)
    return t.points[t.faces.reshape(-1, 4)[:, 1:]].reshape(-1, 3)


def main(cas: Path):
    objets, stats = [], {}
    fichiers = [f for f in (cas / "VTK_maillage").rglob("*") if f.suffix in (".vtp", ".vtk")]
    for f in sorted(fichiers):
        nom = next((k for k in COUL if f.stem.startswith(k) or k in f.stem), None)
        if nom is None:
            continue
        m = pv.read(f)
        seg, n_ar = aretes(m, 120000)
        objets.append(dict(nom=nom, titre=f"Surface : {nom}", type="surface", couleur=COUL[nom],
                           tri=b64(triangles(m)), seg=b64(seg), visible=nom in ("tubes", "ailette")))
        stats[nom] = dict(faces=int(m.n_cells), aretes=int(n_ar))
    for f in sorted((cas / "postProcessing/coupes/0").glob("*.vtp")):
        nom = f.stem.split("_p")[0] if f.stem not in COUPES else f.stem
        nom = next((k for k in COUPES if f.stem.startswith(k)), f.stem)
        m = pv.read(f)
        seg, n_ar = aretes(m, 400000)
        objets.append(dict(nom=nom, titre=f"Coupe : {nom.replace('_', ' ')}", type="coupe", couleur=COUPES.get(nom, "#000"),
                           tri=b64(triangles(m, 200000)), seg=b64(seg), visible=True))
        stats[nom] = dict(polygones=int(m.n_cells), aretes=int(n_ar))
    log = (cas / "log.checkMesh").read_text(errors="ignore") if (cas / "log.checkMesh").exists() else ""
    qual = {}
    for cle, motif in (("cellules", r"cells:\s+(\d+)"), ("faces", r"faces:\s+(\d+)"), ("points", r"points:\s+(\d+)"),
                       ("hexaedres", r"hexahedra:\s+(\d+)"), ("polyedres", r"polyhedra:\s+(\d+)"),
                       ("non_orthogonalite_max", r"non-orthogonality Max: ([\d.]+)"),
                       ("asymetrie_max", r"Max skewness = ([\d.]+)")):
        mm = re.search(motif, log)
        qual[cle] = mm.group(1) if mm else "—"
    qual["verdict"] = "Mesh OK" if "Mesh OK" in log else ("contrôles en échec : voir log.checkMesh" if log else "—")
    meta = json.loads((cas / "cas.json").read_text())
    ligne = lambda k, v: f"<tr><td>{k}</td><td class='n'>{v}</td></tr>"
    tab = "".join([ligne("Cellules", f"{int(qual['cellules']):,}".replace(",", " ") if qual["cellules"] != "—" else "—"),
                   ligne("Hexaèdres / polyèdres", f"{qual['hexaedres']} / {qual['polyedres']}"),
                   ligne("Non-orthogonalité max (°)", qual["non_orthogonalite_max"]),
                   ligne("Asymétrie max", qual["asymetrie_max"]), ligne("checkMesh", qual["verdict"]),
                   ligne("Maille de fond", f"{meta['base_mm']} mm"),
                   ligne("Maille aux tubes", f"{meta['maille_tubes_mm']} mm (niveau {meta['niveaux']['tubes']})"),
                   ligne("Maille ailette / parois", f"{meta['base_mm']/2**meta['niveaux']['ailette']:.2f} / {meta['base_mm']/2**meta['niveaux']['parois']:.2f} mm")])
    html = PAGE.replace("__CAS__", f"{cas.name} ({meta['U_conduit']:g} m/s dans le conduit)").replace("__OBJETS__", json.dumps(objets)).replace("__TABLE__", tab).replace(
        "__STATS__", json.dumps(stats, ensure_ascii=False))
    sortie = cas / "maillage.html"
    sortie.write_text(html)
    copie = RACINE / "docs/formes/cylindre_d150_helice" / f"maillage_{cas.name}.html"
    copie.write_text(html)
    print(sortie, f"{sortie.stat().st_size/1e6:.1f} Mo ;", copie, "\n", json.dumps(qual, ensure_ascii=False), "\n", stats)


PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maillage échangeur Ø 150</title>
<style>
:root { --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; --accent:#1c7ed6; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fond:#141517; --carte:#1f2023; --texte:#e9ecef;
  --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; } }
:root[data-theme="dark"] { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; }
* { box-sizing:border-box; }
body { margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1200px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:24px; margin:0 0 4px; } .sous { color:var(--doux); margin:0 0 14px; }
#vue { width:100%; height:680px; background:#fff; border:1px solid var(--trait); border-radius:10px; position:relative; overflow:hidden; }
.ctrl { display:flex; flex-wrap:wrap; gap:6px 16px; margin:10px 0; font-size:14px; }
.ctrl label { display:flex; align-items:center; gap:5px; cursor:pointer; }
.pastille { width:12px; height:12px; border-radius:3px; display:inline-block; }
.ctrl button { font:inherit; padding:3px 10px; border-radius:6px; border:1px solid var(--trait); background:var(--carte); color:var(--texte); cursor:pointer; }
.grille { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; margin-top:14px; }
.carte { background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:12px 14px; }
table { border-collapse:collapse; width:100%; font-size:14px; } td { padding:5px 8px; border-bottom:1px solid var(--trait); }
td.n { text-align:right; font-variant-numeric:tabular-nums; } .aide { color:var(--doux); font-size:13px; }
</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head><body><main>
<h1>Maillage CFD de l'échangeur Ø 150 à canal hélicoïdal</h1>
<p class="sous">snappyHexMesh (OpenFOAM v2606), cas __CAS__ · surfaces maillées par zone et coupes
(cellules coupées par un plan, sans lissage).</p>
<div id="vue"></div>
<div class="ctrl" id="ctrl"></div>
<div class="ctrl" id="vues"></div>
<p class="aide">Pour chaque élément : case = affiché ; « fil » = arêtes des mailles. Rotation libre (clic gauche), zoom (molette),
déplacement (clic droit). Les arêtes des grandes surfaces sont sous-échantillonnées pour la vue (nombre réel dans le tableau).</p>
<div class="grille"><div class="carte"><b>Qualité du maillage</b><table>__TABLE__</table></div>
<div class="carte"><b>Éléments affichés</b><pre id="stats" style="font-size:12px;white-space:pre-wrap;margin:6px 0 0"></pre></div></div>
</main>
<script type="module">
import * as THREE from "three";
import { TrackballControls } from "three/addons/controls/TrackballControls.js";
const OBJETS = __OBJETS__;
document.getElementById("stats").textContent = JSON.stringify(__STATS__, null, 1);
const boite = document.getElementById("vue");
const rendu = new THREE.WebGLRenderer({ antialias: true }); rendu.setPixelRatio(window.devicePixelRatio);
rendu.setClearColor(0xffffff); boite.appendChild(rendu.domElement);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.2));
const sol = new THREE.DirectionalLight(0xffffff, 1.0); sol.position.set(1, -1, 2); scene.add(sol);
const cam = new THREE.PerspectiveCamera(35, 1, 0.001, 10);
const groupe = new THREE.Group(); scene.add(groupe);
const dec = s => new Float32Array(Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer);
const ctrl = document.getElementById("ctrl");
for (const o of OBJETS) {
  const gt = new THREE.BufferGeometry(); gt.setAttribute("position", new THREE.BufferAttribute(dec(o.tri), 3)); gt.computeVertexNormals();
  const surf = new THREE.Mesh(gt, new THREE.MeshStandardMaterial({ color: o.couleur, side: THREE.DoubleSide,
    transparent: true, opacity: o.type === "coupe" ? 0.35 : 0.55, depthWrite: false, polygonOffset: true, polygonOffsetFactor: 1 }));
  const gl = new THREE.BufferGeometry(); gl.setAttribute("position", new THREE.BufferAttribute(dec(o.seg), 3));
  const fil = new THREE.LineSegments(gl, new THREE.LineBasicMaterial({ color: o.type === "coupe" ? 0x222222 : o.couleur,
    transparent: true, opacity: 0.8 }));
  surf.visible = o.visible; fil.visible = o.visible && o.type === "coupe";
  groupe.add(surf, fil);
  const l = document.createElement("label");
  l.innerHTML = `<input type="checkbox" ${o.visible ? "checked" : ""}><span class="pastille" style="background:${o.couleur}"></span>${o.titre}` +
    ` <input type="checkbox" ${fil.visible ? "checked" : ""} title="arêtes"> fil`;
  const [cs, cf] = l.querySelectorAll("input");
  cs.onchange = e => { surf.visible = e.target.checked; if (!e.target.checked) { fil.visible = false; cf.checked = false; } };
  cf.onchange = e => { fil.visible = e.target.checked; };
  ctrl.appendChild(l);
}
const bb = new THREE.Box3().setFromObject(groupe), c = bb.getCenter(new THREE.Vector3()), r = bb.getSize(new THREE.Vector3()).length();
const ctl = new TrackballControls(cam, rendu.domElement); ctl.rotateSpeed = 3; ctl.target.copy(c);
const VUES = [["3D", [1, -1.2, 0.9], [0, 0, 1]], ["Dessus", [0, 0, 1], [0, 1, 0]], ["Face", [0, -1, 0], [0, 0, 1]], ["Côté", [1, 0, 0], [0, 0, 1]]];
const vues = document.getElementById("vues"); vues.append("Vue : ");
function vue(d, u) { cam.position.copy(c).add(new THREE.Vector3(...d).normalize().multiplyScalar(r * 1.4)); cam.up.set(...u);
  ctl.target.copy(c); cam.lookAt(c); ctl.update(); }
for (const [n, d, u] of VUES) { const b = document.createElement("button"); b.textContent = n; b.onclick = () => vue(d, u); vues.append(b); }
vue(VUES[0][1], VUES[0][2]);
function taille() { const w = boite.clientWidth, h = boite.clientHeight; rendu.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); ctl.handleResize(); }
new ResizeObserver(taille).observe(boite); taille();
(function boucle() { requestAnimationFrame(boucle); ctl.update(); rendu.render(scene, cam); })();
</script></body></html>"""

if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
