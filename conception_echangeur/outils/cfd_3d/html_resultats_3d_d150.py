"""Page HTML 3D des résultats d'un cas CFD Ø 150 : coupes X, Y, Z déplaçables dans tout le volume.

Entrée : <cas>/grille.json et <cas>/grille_<champ>.u8.gz (grille_resultats_d150.py, lancé sur la machine de calcul),
plus les STL des tubes et de l'enveloppe pour situer les coupes. Les données restent compressées dans la page
et sont décompressées par le navigateur (DecompressionStream).
Sortie : docs/formes/cylindre_d150_helice/resultats_3d_<cas>.html

    .venv/bin/python conception_echangeur/outils/cfd_3d/html_resultats_3d_d150.py conception_echangeur/cfd_campagne/d150_helice/U2_5
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
D = RACINE / "docs/formes/cylindre_d150_helice"


def stl_b64(f, reduction=0.0):
    import pyvista as pv
    m = pv.read(f).triangulate().clean()
    if reduction:
        m = m.decimate(reduction)
    tri = m.points[m.faces.reshape(-1, 4)[:, 1:]].astype(np.float32).reshape(-1)
    return base64.b64encode(tri.tobytes()).decode()


def main(cas: Path):
    meta = json.loads((cas / "grille.json").read_text())
    res = json.loads((cas / "resultat.json").read_text())
    donnees = {k: base64.b64encode((cas / f"grille_{k}.u8.gz").read_bytes()).decode() for k in meta["champs"]}
    geo = {"tubes": stl_b64(D / "tubes.stl"), "enveloppe": stl_b64(D / "enveloppe.stl"), "noyau": stl_b64(D / "noyau.stl"),
           "ailette": stl_b64(D / "ailette.stl", 0.75)}
    info = dict(cas=cas.name, U=res["U_conduit"], debit=round(res["debit_m3h"], 1), dp=round(res["perte_charge_Pa"], 1),
                eps=round(res["Tf"]["epsilon"], 4), eps_p=round(res["Tp"]["epsilon"], 4),
                mcp=round(res["mCp_W_K"], 3), mailles=meta["mailles"])
    fp = cas / "profils.json"
    prof = json.loads(fp.read_text()) if fp.exists() else None
    if prof:
        dim = json.loads((D / "dimensions.json").read_text())
        prof["meta"].update(gap_mm=dim["helice"]["pas_mm"] - dim["parametres"]["ep_ailette"],
                            Lint_mm=dim["longueur_interieure_mm"], th_fin=dim["helice"]["tours"] * 2 * 3.141592653589793,
                            debit_ref=res["debit_m3h"])
        prof["profils"] = [dict(s=d["s_mm"], Tf=round(d["Tf"], 4), Tp=round(d["Tp"], 4), p=round(d["p_Pa"], 2),
                                q=round(d["debit_m3h"], 2)) for d in prof["profils"]]
    html = (MODELE.replace("__PROFILS__", json.dumps(prof)).replace("__META__", json.dumps(meta)).replace("__DONNEES__", json.dumps(donnees))
            .replace("__GEO__", json.dumps(geo)).replace("__INFO__", json.dumps(info))
            .replace("__TITRE__", f"{res['U_conduit']:g}".replace(".", ",")))
    out = D / f"resultats_3d_{cas.name}.html"
    out.write_text(html)
    print(out, round(len(html) / 1e6, 1), "Mo")


MODELE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Coupes CFD Ø150</title>
<style>
:root { --fond:#f8f9fa; --carte:#fff; --texte:#212529; --doux:#5c636a; --trait:#dee2e6; --accent:#1c7ed6; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; } }
:root[data-theme="dark"] { --fond:#141517; --carte:#1f2023; --texte:#e9ecef; --doux:#adb5bd; --trait:#373a40; --accent:#4dabf7; }
:root { --s1:#2a78d6; --s2:#eb6834; --bande:#00000008; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --s1:#3987e5; --s2:#d95926; --bande:#ffffff0a; } }
:root[data-theme="dark"] { --s1:#3987e5; --s2:#d95926; --bande:#ffffff0a; }
.graphes { display:grid; grid-template-columns:1fr; gap:12px; }
.graphe { background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:10px 12px; position:relative; }
.graphe h3 { font-size:14px; margin:0 0 2px; } .graphe svg { width:100%; height:auto; display:block; touch-action:none; }
.graphe svg text { fill:var(--doux); font-size:11px; font-family:system-ui,sans-serif; }
.legende-g { display:flex; gap:14px; font-size:13px; color:var(--doux); margin-bottom:2px; }
.legende-g i { display:inline-block; width:14px; height:3px; border-radius:2px; vertical-align:middle; margin-right:5px; }
#bulle { position:fixed; pointer-events:none; background:var(--carte); color:var(--texte); border:1px solid var(--trait); border-radius:8px;
  padding:6px 9px; font-size:13px; font-variant-numeric:tabular-nums; box-shadow:0 2px 8px #0002; display:none; z-index:10; white-space:nowrap; }
.alerte { border-left:4px solid #c92a2a; }
* { box-sizing:border-box; }
body { margin:0; background:var(--fond); color:var(--texte); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1300px; margin:0 auto; padding:20px 16px 48px; }
h1 { font-size:22px; margin:0 0 4px; } .sous { color:var(--doux); margin:0 0 12px; font-size:14px; }
.haut { display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:14px; }
@media (max-width:860px) { .haut { grid-template-columns:1fr; } }
#vue { width:100%; height:620px; background:#fff; border:1px solid var(--trait); border-radius:10px; position:relative; overflow:hidden; }
#lecture { position:absolute; left:10px; top:8px; font:13px/1.4 ui-monospace,monospace; color:#222; background:#ffffffcc; padding:3px 7px; border-radius:6px; pointer-events:none; }
.panneau { background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:12px 14px; display:flex; flex-direction:column; gap:10px; }
.panneau label { display:flex; align-items:center; gap:6px; font-size:14px; }
.curseur { display:grid; grid-template-columns:auto 1fr; gap:2px 8px; align-items:center; font-size:14px; }
.curseur input[type=range] { grid-column:1 / 3; width:100%; }
.curseur b { font-variant-numeric:tabular-nums; text-align:right; }
select, button { font:inherit; padding:3px 8px; border-radius:6px; border:1px solid var(--trait); background:var(--carte); color:var(--texte); }
#barre { width:100%; height:16px; border-radius:4px; border:1px solid var(--trait); }
.echelle { display:flex; justify-content:space-between; font-size:12px; color:var(--doux); font-variant-numeric:tabular-nums; }
.coupes { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:14px; }
@media (max-width:860px) { .coupes { grid-template-columns:1fr; } }
.coupe { background:var(--carte); border:1px solid var(--trait); border-radius:10px; padding:8px 10px; }
.coupe canvas { width:100%; height:auto; display:block; background:#fff; border-radius:6px; cursor:crosshair; image-rendering:pixelated; }
.coupe h3 { font-size:14px; margin:0 0 6px; } .aide { color:var(--doux); font-size:13px; }
.temp { display:grid; grid-template-columns:1fr 1fr; gap:6px 10px; font-size:14px; }
.temp input[type=number] { width:100%; font:inherit; padding:2px 6px; border-radius:6px; border:1px solid var(--trait); background:var(--carte); color:var(--texte); }
.bilan { font-size:13px; font-variant-numeric:tabular-nums; margin:0; } .bilan td { padding:2px 4px; border-bottom:1px solid var(--trait); } .bilan td.n { text-align:right; }
.vues, .elements { display:flex; flex-wrap:wrap; gap:6px; }
.elements button[aria-pressed="false"] { opacity:.45; text-decoration:line-through; }
.elements button[aria-pressed="true"] { border-color:var(--accent); }
.elements button .pastille { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head><body><main>
<h1>CFD de l'échangeur Ø 150 à __TITRE__ m/s : coupes dans tout le volume</h1>
<p class="sous" id="sous"></p>
<div class="haut">
  <div id="vue"><div id="lecture">survoler une coupe pour lire la valeur</div></div>
  <div class="panneau">
    <label>Champ <select id="champ"></select></label>
    <div><canvas id="barre" width="256" height="1"></canvas><div class="echelle"><span id="emin"></span><span id="emil"></span><span id="emax"></span></div></div>
    <div><div style="font-size:14px;margin-bottom:4px">Températures réelles</div>
      <div class="temp"><label style="display:block">Air entrant (°C)<input type="number" id="ta" value="20" step="0.5"></label>
      <label style="display:block">Propane (°C)<input type="number" id="tr" value="32" step="0.5"></label></div>
      <label style="margin-top:4px"><input type="checkbox" id="degC" checked> Afficher Tf et Tp en °C</label>
      <table class="bilan" id="bilan"></table></div>
    <div class="curseur"><span>Coupe X</span><b id="tx"></b><input type="range" id="cx"></div>
    <div class="curseur"><span>Coupe Y</span><b id="ty"></b><input type="range" id="cy"></div>
    <div class="curseur"><span>Coupe Z</span><b id="tz"></b><input type="range" id="cz"></div>
    <div><div style="font-size:14px;margin-bottom:4px">Afficher / masquer</div><div class="elements" id="elements"></div>
    <div class="elements" style="margin-top:6px"><button id="tout">Tout afficher</button><button id="seules">Coupes seules</button></div></div>
    <div class="vues" id="vues">Vue : </div>
    <p class="aide" style="margin:0">Cliquer dans une coupe 2D (en bas) place les deux autres coupes sur ce point. Flèches du clavier :
    déplacer la coupe Z. Rotation libre au clic gauche, zoom à la molette, déplacement au clic droit.</p>
  </div>
</div>
<div class="coupes">
  <div class="coupe"><h3 id="hz">Coupe Z (vue de dessus)</h3><canvas id="kz"></canvas></div>
  <div class="coupe"><h3 id="hx">Coupe X (plan Y-Z)</h3><canvas id="kx"></canvas></div>
  <div class="coupe"><h3 id="hy">Coupe Y (plan X-Z)</h3><canvas id="ky"></canvas></div>
</div>
<div id="profils" style="display:none">
<h2 style="font-size:18px;margin:26px 0 4px">Profils le long du chemin d'air, de l'entrée à la sortie</h2>
<p class="aide" style="margin:0 0 10px">Abscisse : distance parcourue sur le chemin moyen (rayon 47 mm), conduit d'entrée, puis
2,9 tours d'hélice, puis conduit de sortie. Chaque point est une coupe exacte du maillage : demi-plan méridien tous les 3° dans l'hélice,
plan tous les 5 mm dans les conduits. Température de mélange pondérée par le débit, pression moyenne sur la section. Survoler un graphe
place un repère rouge dans la vue 3D.</p>
<div class="graphes">
  <div class="graphe"><h3 id="g_t_titre">Température de l'air</h3>
    <div class="legende-g"><span><i style="background:var(--s1)"></i>ailette froide (Tf)</span><span><i style="background:var(--s2)"></i>ailette passive (Tp)</span></div>
    <svg id="g_t" viewBox="0 0 900 250"></svg></div>
  <div class="graphe"><h3>Pression statique moyenne (Pa, relative à la sortie)</h3><svg id="g_p" viewBox="0 0 900 220"></svg></div>
  <div class="graphe alerte"><h3>Débit traversant chaque section (m³/h) : contrôle</h3><svg id="g_q" viewBox="0 0 900 220"></svg>
    <p class="aide" style="margin:4px 0 0">Il devrait être constant (pointillés : débit d'entrée). Il ne l'est pas : <b>une partie de l'air court-circuite
    l'hélice</b>. Le conduit d'entrée traverse le fond du cylindre sous la fin du premier tour, sans paroi entre les deux : environ un tiers de
    l'air monte directement dans la fin du tour 1. De même, environ un cinquième de l'air sort par le conduit de sortie dès le début du
    tour 3. C'est un défaut du modèle CAO (les deux remplissages sous et sur l'hélice sont percés par les conduits), et la chute de
    température vers 400 mm en est la trace : l'air froid du raccourci se mélange à l'air déjà chauffé.</p></div>
</div></div>
<div id="bulle"></div>
<p class="aide">Chaque pixel est une maille OpenFOAM échantillonnée tous les <span id="pas"></span> mm, avec la valeur exacte de la maille et sans
lissage. Les mailles de 3 mm apparaissent en blocs de 2 × 2 pixels. Les mailles plus fines (0,375 mm le long des tubes, 0,75 mm le long de l'ailette)
sont représentées par celle qui contient le point. Le champ « taille de maille » montre ce raffinement. En blanc : le métal (tubes,
ailette, parois) et l'extérieur. Tf : tubes et ailette à 1, air entrant à 0. Tp : ailette adiabatique, seuls les tubes chauffent.</p>
</main>
<script type="module">
import * as THREE from "three";
import { TrackballControls } from "three/addons/controls/TrackballControls.js";
const PROFILS = __PROFILS__;
const META = __META__, DONNEES = __DONNEES__, GEO = __GEO__, INFO = __INFO__;
const [nx, ny, nz] = META.dim, pas = META.pas_mm, o = META.origine_mm;
document.getElementById("pas").textContent = pas.toString().replace(".", ",");
document.getElementById("sous").textContent = `Cas ${INFO.cas} · ${(INFO.mailles / 1e6).toFixed(2).replace(".", ",")} M mailles · débit ${INFO.debit} m³/h · Δp ${String(INFO.dp).replace(".", ",")} Pa · ε ${String(INFO.eps).replace(".", ",")} · grille ${nx} × ${ny} × ${nz}`;

// ---------- palettes ----------
const PAL = {
  viridis: [[68,1,84],[72,40,120],[62,74,137],[49,104,142],[38,130,142],[31,158,137],[53,183,121],[109,205,89],[180,222,44],[253,231,37]],
  inferno: [[0,0,4],[31,12,72],[85,15,109],[136,34,106],[186,54,85],[227,89,51],[249,140,10],[249,201,50],[252,255,164]],
  coolwarm: [[59,76,192],[98,130,234],[141,176,254],[184,208,249],[221,221,221],[245,196,173],[244,154,123],[222,96,77],[180,4,38]],
  cividis: [[0,34,78],[39,62,108],[87,92,109],[125,124,120],[166,157,117],[210,193,99],[254,232,56]],
};
const CHOIX = { p: "coolwarm", U: "viridis", Uz: "viridis", Tf: "inferno", Tp: "inferno", taille: "cividis" };
function palette(nom) { const s = PAL[nom], t = new Uint8Array(256 * 4);
  for (let i = 0; i < 255; i++) { const x = i / 254 * (s.length - 1), a = Math.floor(Math.min(x, s.length - 2)), f = x - a;
    for (let c = 0; c < 3; c++) t[i * 4 + c] = Math.round(s[a][c] * (1 - f) + s[a + 1][c] * f); t[i * 4 + 3] = 255; }
  return t; }

// ---------- données ----------
const cache = {};
async function charger(cle) {
  if (cache[cle]) return cache[cle];
  const brut = Uint8Array.from(atob(DONNEES[cle]), c => c.charCodeAt(0));
  const flux = new Blob([brut]).stream().pipeThrough(new DecompressionStream("gzip"));
  const v = new Uint8Array(await new Response(flux).arrayBuffer());
  const tex = new THREE.Data3DTexture(v, nx, ny, nz);
  tex.format = THREE.RedFormat; tex.type = THREE.UnsignedByteType; tex.minFilter = tex.magFilter = THREE.NearestFilter;
  tex.unpackAlignment = 1; tex.needsUpdate = true;
  return (cache[cle] = { v, tex });
}
const mmt = x => (Math.abs(x) < 0.05 ? 0 : x).toFixed(1).replace(".", ",");
const idx = (i, j, k) => i + nx * (j + ny * k);
const valeur = (cle, q) => { const c = META.champs[cle]; return c.min + q / 254 * (c.max - c.min); };
const TA = () => +document.getElementById("ta").value, TR = () => +document.getElementById("tr").value;
const enC = cle => (cle === "Tf" || cle === "Tp") && document.getElementById("degC").checked;
const reel = th => TA() + th * (TR() - TA());
const deg = x => x.toFixed(1).replace(".", ",") + " °C";
function fmt(cle, x) { if (enC(cle)) return deg(reel(x));
  const c = META.champs[cle], e = Math.abs(c.max - c.min);
  return x.toFixed(e < 2 ? 3 : e < 20 ? 2 : 1).replace(".", ","); }

// ---------- scène ----------
const boite = document.getElementById("vue");
const rendu = new THREE.WebGLRenderer({ antialias: true }); rendu.setPixelRatio(window.devicePixelRatio);
rendu.setClearColor(0xffffff); boite.appendChild(rendu.domElement);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.3));
const sol = new THREE.DirectionalLight(0xffffff, 0.9); sol.position.set(1, -1, 2); scene.add(sol);
const cam = new THREE.PerspectiveCamera(35, 1, 1, 5000);
const dec = s => new Float32Array(Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer);
function solide(b64, couleur, opacite) {
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(dec(b64), 3)); g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: couleur, side: THREE.DoubleSide, transparent: opacite < 1,
    opacity: opacite, depthWrite: opacite >= 1, metalness: 0.2, roughness: 0.6 }));
  scene.add(m); return m; }
const tubes = solide(GEO.tubes, 0x9aa5b1, 1), env = solide(GEO.enveloppe, 0x7a8896, 0.12), noyau = solide(GEO.noyau, 0x6c7a89, 1);
const ailette = solide(GEO.ailette, 0xc9a227, 0.35); ailette.visible = false;

const lutTex = new THREE.DataTexture(new Uint8Array(256 * 4), 256, 1); lutTex.minFilter = lutTex.magFilter = THREE.NearestFilter;
const uni = { vol: { value: null }, lut: { value: lutTex }, o: { value: new THREE.Vector3(...o) },
  dim: { value: new THREE.Vector3(nx, ny, nz) }, pas: { value: pas } };
const mat = new THREE.ShaderMaterial({ glslVersion: THREE.GLSL3, uniforms: uni, side: THREE.DoubleSide,
  vertexShader: `out vec3 vp; void main(){ vp = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `precision highp float; precision highp sampler3D;
    uniform sampler3D vol; uniform sampler2D lut; uniform vec3 o, dim; uniform float pas; in vec3 vp; out vec4 fc;
    void main(){ vec3 u = (floor((vp - o) / pas + 0.5) + 0.5) / dim;
      if (any(lessThan(u, vec3(0.0))) || any(greaterThan(u, vec3(1.0)))) discard;
      float k = floor(texture(vol, u).r * 255.0 + 0.5); if (k > 254.5) discard;
      fc = texture(lut, vec2((k + 0.5) / 256.0, 0.5)); }` });
const L = [nx, ny, nz].map(n => (n - 1) * pas), hi = o.map((a, i) => a + L[i]);
function plan(axe) {
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(12), 3));
  g.setIndex([0, 1, 2, 0, 2, 3]); const m = new THREE.Mesh(g, mat); m.userData.axe = axe; scene.add(m);
  const bord = new THREE.LineLoop(g, new THREE.LineBasicMaterial({ color: [0xe03131, 0x2f9e44, 0x1c7ed6][axe] })); scene.add(bord);
  m.userData.bord = bord; return m; }
const plans = [plan(0), plan(1), plan(2)];
const pos = [0, 0, 0];   // indices des coupes
function placer(axe) {
  const c = o[axe] + pos[axe] * pas, a = plans[axe].geometry.attributes.position, p = [];
  const [u, v] = [[1, 2], [0, 2], [0, 1]][axe];
  for (const [su, sv] of [[0, 0], [1, 0], [1, 1], [0, 1]]) { const q = [0, 0, 0]; q[axe] = c;
    q[u] = su ? hi[u] : o[u]; q[v] = sv ? hi[v] : o[v]; p.push(...q); }
  a.array.set(p); a.needsUpdate = true; plans[axe].geometry.computeBoundingSphere(); plans[axe].geometry.computeBoundingBox();
}

// ---------- interface ----------
const sel = document.getElementById("champ");
for (const [k, c] of Object.entries(META.champs)) sel.add(new Option(c.titre, k));
sel.value = "Tf";
const curs = ["cx", "cy", "cz"].map(id => document.getElementById(id)), txt = ["tx", "ty", "tz"].map(id => document.getElementById(id));
const nom = ["X", "Y", "Z"];
[nx, ny, nz].forEach((n, a) => { curs[a].min = 0; curs[a].max = n - 1; curs[a].step = 1; });
pos[0] = Math.round(-o[0] / pas); pos[1] = Math.round(-o[1] / pas); pos[2] = Math.round(nz / 2);
pos.forEach((p, a) => { pos[a] = Math.max(0, Math.min([nx, ny, nz][a] - 1, p)); curs[a].value = pos[a]; });
curs.forEach((c, a) => c.oninput = () => { pos[a] = +c.value; maj(a); });
addEventListener("keydown", e => { if (e.target.tagName === "SELECT") return;
  const d = { ArrowUp: 1, ArrowDown: -1, PageUp: 10, PageDown: -10 }[e.key]; if (!d) return; e.preventDefault();
  pos[2] = Math.max(0, Math.min(nz - 1, pos[2] + d)); curs[2].value = pos[2]; maj(2); });

let champ = "Tf", donnees = null;
async function changerChamp() {
  champ = sel.value; donnees = await charger(champ);
  const t = palette(CHOIX[champ]); lutTex.image.data.set(t); lutTex.needsUpdate = true; uni.vol.value = donnees.tex;
  const b = document.getElementById("barre").getContext("2d"), im = b.createImageData(256, 1);
  for (let i = 0; i < 256; i++) { const q = Math.min(254, Math.round(i / 255 * 254)); im.data.set(t.subarray(q * 4, q * 4 + 4), i * 4); }
  b.putImageData(im, 0, 0);
  legende();
  for (let a = 0; a < 3; a++) dessiner(a);
}
const titre = cle => enC(cle) ? `T réelle (${cle === "Tf" ? "ailette froide" : "ailette passive"})` : META.champs[cle].titre;
function legende() {
  const c = META.champs[champ];
  document.getElementById("emin").textContent = fmt(champ, c.min); document.getElementById("emax").textContent = fmt(champ, c.max);
  document.getElementById("emil").textContent = titre(champ);
  const dT = TR() - TA(), w = x => Math.round(Math.abs(x)).toString() + " W", ligne = (n, e) =>
    `<tr><td>${n}</td><td class="n">${deg(TA() + e * dT)}</td><td class="n">${w(e * INFO.mcp * dT)}</td></tr>`;
  document.getElementById("bilan").innerHTML = `<tr><td></td><td class="n">Air sortant</td><td class="n">Puissance</td></tr>` +
    ligne("Ailette froide", INFO.eps) + ligne("Ailette passive", INFO.eps_p) +
    `<tr><td colspan="3" class="aide">${dT >= 0 ? "puissance cédée à l'air" : "puissance prise à l'air"} · ${String(INFO.debit).replace(".", ",")} m³/h</td></tr>`;
}
for (const id of ["ta", "tr", "degC"]) document.getElementById(id).addEventListener("input", () => { legende(); tracerProfils(); });
sel.onchange = changerChamp;

// ---------- coupes 2D ----------
const ECH = 3;
const K = [document.getElementById("kx"), document.getElementById("ky"), document.getElementById("kz")];
const AX2 = [[1, 2], [0, 2], [0, 1]];          // axes horizontal / vertical de chaque coupe
const N = [nx, ny, nz], hors = document.createElement("canvas");
K.forEach((k, a) => { const [u, v] = AX2[a]; k.width = N[u] * ECH; k.height = N[v] * ECH; });
function dessiner(a) {
  if (!donnees) return;
  const [u, v] = AX2[a], W = N[u], H = N[v], t = lutTex.image.data;
  hors.width = W; hors.height = H; const cx = hors.getContext("2d"), im = cx.createImageData(W, H);
  const ijk = [0, 0, 0]; ijk[a] = pos[a];
  for (let jv = 0; jv < H; jv++) for (let iu = 0; iu < W; iu++) {
    ijk[u] = iu; ijk[v] = jv; const q = donnees.v[idx(...ijk)], d = ((H - 1 - jv) * W + iu) * 4;
    if (q === 255) { im.data[d] = im.data[d + 1] = im.data[d + 2] = 255; im.data[d + 3] = 255; }
    else { im.data[d] = t[q * 4]; im.data[d + 1] = t[q * 4 + 1]; im.data[d + 2] = t[q * 4 + 2]; im.data[d + 3] = 255; }
  }
  cx.putImageData(im, 0, 0);
  const k = K[a], g = k.getContext("2d"); g.imageSmoothingEnabled = false; g.drawImage(hors, 0, 0, W * ECH, H * ECH);
  g.lineWidth = 1; g.setLineDash([5, 4]);
  for (const b of [u, v]) {          // position des deux autres coupes
    g.strokeStyle = ["#e03131", "#2f9e44", "#1c7ed6"][b]; g.beginPath();
    if (b === u) { const x = (pos[b] + 0.5) * ECH; g.moveTo(x, 0); g.lineTo(x, H * ECH); }
    else { const y = (H - 1 - pos[b] + 0.5) * ECH; g.moveTo(0, y); g.lineTo(W * ECH, y); }
    g.stroke(); }
  const mm = x => mmt(o[a] + x * pas);
  document.getElementById(["hx", "hy", "hz"][a]).textContent =
    [`Coupe X = ${mm(pos[0])} mm (plan Y-Z)`, `Coupe Y = ${mm(pos[1])} mm (plan X-Z)`, `Coupe Z = ${mm(pos[2])} mm (vue de dessus)`][a];
}
function lire(ijk) { if (!donnees) return "";
  const q = donnees.v[idx(...ijk)], xyz = ijk.map((n, a) => mmt(o[a] + n * pas)).join(" ; ");
  return `(${xyz}) mm · ` + (q === 255 ? "métal / hors fluide" : `${titre(champ)} = ${fmt(champ, valeur(champ, q))}`); }
const lecture = document.getElementById("lecture");
K.forEach((k, a) => {
  const ijk = e => { const r = k.getBoundingClientRect(), [u, v] = AX2[a];
    const iu = Math.floor((e.clientX - r.left) / r.width * N[u]), jv = N[v] - 1 - Math.floor((e.clientY - r.top) / r.height * N[v]);
    const p = [0, 0, 0]; p[a] = pos[a]; p[u] = Math.max(0, Math.min(N[u] - 1, iu)); p[v] = Math.max(0, Math.min(N[v] - 1, jv)); return p; };
  k.onmousemove = e => { lecture.textContent = lire(ijk(e)); };
  k.onclick = e => { const p = ijk(e); for (const b of AX2[a]) { pos[b] = p[b]; curs[b].value = p[b]; maj(b); } };
});
function maj(a) { placer(a); txt[a].textContent = mmt(o[a] + pos[a] * pas) + " mm"; for (let b = 0; b < 3; b++) dessiner(b); }

// lecture au survol dans la 3D
const ray = new THREE.Raycaster(), souris = new THREE.Vector2();
rendu.domElement.addEventListener("pointermove", e => {
  const r = rendu.domElement.getBoundingClientRect(); souris.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
  ray.setFromCamera(souris, cam);
  for (const h of ray.intersectObjects(plans.filter(p => p.visible))) {
    const ijk = [0, 1, 2].map(a => Math.round((h.point.getComponent(a) - o[a]) / pas));
    if (ijk.some((n, a) => n < 0 || n >= N[a])) continue;
    if (donnees.v[idx(...ijk)] === 255) continue;
    lecture.textContent = lire(ijk); return; }
});

// ---------- caméra ----------
const centre = new THREE.Vector3(...o.map((a, i) => a + L[i] / 2)), R = Math.hypot(...L);
const ctl = new TrackballControls(cam, rendu.domElement); ctl.rotateSpeed = 3; ctl.target.copy(centre);
const VUES = [["3D", [1, -1.2, 0.8], [0, 0, 1]], ["Dessus", [0, 0, 1], [0, 1, 0]], ["Face", [0, -1, 0], [0, 0, 1]], ["Côté", [1, 0, 0], [0, 0, 1]]];
function vue(d, u) { cam.position.copy(centre).add(new THREE.Vector3(...d).normalize().multiplyScalar(R * 1.5)); cam.up.set(...u);
  ctl.target.copy(centre); cam.lookAt(centre); ctl.update(); }
for (const [n, d, u] of VUES) { const b = document.createElement("button"); b.textContent = n; b.onclick = () => vue(d, u); document.getElementById("vues").append(b); }
vue(VUES[0][1], VUES[0][2]);
const axes = new THREE.AxesHelper(40); scene.add(axes);
const ELEMENTS = [
  ["Tube principal", "#7a8896", [env]], ["Tubes d'échange", "#9aa5b1", [tubes]], ["Noyau", "#6c7a89", [noyau]],
  ["Ailette", "#c9a227", [ailette]], ["Coupe X", "#e03131", [plans[0], plans[0].userData.bord]],
  ["Coupe Y", "#2f9e44", [plans[1], plans[1].userData.bord]], ["Coupe Z", "#1c7ed6", [plans[2], plans[2].userData.bord]],
  ["Axes", "#888888", [axes]]];
const boutons = ELEMENTS.map(([t, c, objs]) => {
  const b = document.createElement("button"); b.innerHTML = `<span class="pastille" style="background:${c}"></span>${t}`;
  const regler = v => { objs.forEach(o => o.visible = v); b.setAttribute("aria-pressed", v); };
  regler(objs[0].visible); b.onclick = () => regler(!objs[0].visible);
  document.getElementById("elements").append(b); return regler; });
document.getElementById("tout").onclick = () => boutons.forEach(f => f(true));
document.getElementById("seules").onclick = () => boutons.forEach((f, i) => f(ELEMENTS[i][0].startsWith("Coupe")));
function taille() { const w = boite.clientWidth, h = boite.clientHeight; rendu.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); ctl.handleResize(); }
new ResizeObserver(taille).observe(boite); taille();
// ---------- profils le long du chemin ----------
const NS = "http://www.w3.org/2000/svg";
const el = (n, a = {}, parent) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (parent) parent.append(e); return e; };
const num = (x, n = 1) => x.toFixed(n).replace(".", ",");
const repere = new THREE.Mesh(new THREE.SphereGeometry(4, 20, 14), new THREE.MeshBasicMaterial({ color: 0xe03131 }));
repere.visible = false; scene.add(repere);
let graphes = [];
function pointChemin(s) {        // position (mm) sur le chemin moyen à l'abscisse s
  const M = PROFILS.meta, rm = M.r_moyen_mm, g = M.gap_mm, Le = M.L_entree_mm, Lh = M.L_helice_mm;
  if (s <= Le) return [rm, s - Le, g / 2];
  if (s <= Le + Lh) { const th = (s - Le) / M.ds_par_tour_mm * 2 * Math.PI;
    return [rm * Math.cos(th), rm * Math.sin(th), M.pas_mm * th / (2 * Math.PI) + g / 2]; }
  const d = s - Le - Lh, c = Math.cos(M.th_fin), sn = Math.sin(M.th_fin);
  return [rm * c - d * sn, rm * sn + d * c, M.Lint_mm - g / 2];
}
function graphe(svg, series, opt) {
  svg.replaceChildren();
  const W = 900, H = +svg.getAttribute("viewBox").split(" ")[3], g = { l: 52, r: 14, t: 20, b: 28 };
  const D = PROFILS.profils, M = PROFILS.meta, smax = M.L_entree_mm + M.L_helice_mm + M.L_sortie_mm;
  let lo = Infinity, hi = -Infinity;
  for (const s of series) for (const d of D) { const v = s.f(d); lo = Math.min(lo, v); hi = Math.max(hi, v); }
  if (opt.ref !== undefined) { lo = Math.min(lo, opt.ref); hi = Math.max(hi, opt.ref); }
  if (opt.zero) lo = Math.min(lo, 0);
  const e = (hi - lo) || 1; lo -= e * 0.05; hi += e * 0.08;
  const X = s => g.l + s / smax * (W - g.l - g.r), Y = v => H - g.b - (v - lo) / (hi - lo) * (H - g.t - g.b);
  // bandes : entrée, tours, sortie
  const bornes = [[0, M.L_entree_mm, "entrée"]];
  for (let k = 0; k < Math.ceil(M.tours); k++) bornes.push([M.L_entree_mm + k * M.ds_par_tour_mm,
    M.L_entree_mm + Math.min(k + 1, M.tours) * M.ds_par_tour_mm, `tour ${k + 1}`]);
  bornes.push([M.L_entree_mm + M.L_helice_mm, smax, "sortie"]);
  bornes.forEach(([a, b, t], i) => { if (i % 2 === 0) el("rect", { x: X(a), y: g.t, width: X(b) - X(a), height: H - g.t - g.b, fill: "var(--bande)" }, svg);
    el("text", { x: (X(a) + X(b)) / 2, y: g.t - 6, "text-anchor": "middle" }, svg).textContent = t; });
  // grille et axes
  const pasY = (() => { const brut = (hi - lo) / 6, p10 = 10 ** Math.floor(Math.log10(brut)); return [1, 2, 5, 10].map(m => m * p10).find(m => m >= brut); })();
  for (let v = Math.ceil(lo / pasY) * pasY; v <= hi; v += pasY) {
    el("line", { x1: g.l, x2: W - g.r, y1: Y(v), y2: Y(v), stroke: "var(--trait)", "stroke-width": 1 }, svg);
    el("text", { x: g.l - 6, y: Y(v) + 4, "text-anchor": "end" }, svg).textContent = num(v, pasY < 1 ? 1 : 0); }
  for (let s = 0; s <= smax; s += 200) el("text", { x: X(s), y: H - 8, "text-anchor": "middle" }, svg).textContent = s + (s === 0 ? "" : "");
  el("text", { x: W - g.r, y: H - 8, "text-anchor": "end" }, svg).textContent = "mm";
  if (opt.ref !== undefined) el("line", { x1: g.l, x2: W - g.r, y1: Y(opt.ref), y2: Y(opt.ref), stroke: "var(--doux)", "stroke-dasharray": "5 4" }, svg);
  for (const s of series) el("path", { d: D.map((d, i) => (i ? "L" : "M") + X(d.s).toFixed(1) + "," + Y(s.f(d)).toFixed(1)).join(""),
    fill: "none", stroke: s.c, "stroke-width": 2, "stroke-linejoin": "round" }, svg);
  const croix = el("line", { y1: g.t, y2: H - g.b, stroke: "var(--doux)", "stroke-width": 1, visibility: "hidden" }, svg);
  const points = series.map(s => el("circle", { r: 4.5, fill: s.c, stroke: "var(--carte)", "stroke-width": 2, visibility: "hidden" }, svg));
  const zone = el("rect", { x: g.l, y: 0, width: W - g.l - g.r, height: H, fill: "transparent" }, svg);
  const info = { svg, series, X, Y, croix, points, smax, g, W };
  zone.addEventListener("pointermove", ev => survol(info, ev));
  zone.addEventListener("pointerleave", () => cacher());
  return info;
}
function survol(info, ev) {
  const r = info.svg.getBoundingClientRect(), xv = (ev.clientX - r.left) / r.width * info.W;
  const s = (xv - info.g.l) / (info.W - info.g.l - info.g.r) * info.smax, D = PROFILS.profils;
  let i = 0; for (let j = 1; j < D.length; j++) if (Math.abs(D[j].s - s) < Math.abs(D[i].s - s)) i = j;
  const d = D[i];
  for (const G of graphes) { G.croix.setAttribute("x1", G.X(d.s)); G.croix.setAttribute("x2", G.X(d.s)); G.croix.setAttribute("visibility", "visible");
    G.series.forEach((se, k) => { G.points[k].setAttribute("cx", G.X(d.s)); G.points[k].setAttribute("cy", G.Y(se.f(d))); G.points[k].setAttribute("visibility", "visible"); }); }
  const M = PROFILS.meta, Le = M.L_entree_mm, Lh = M.L_helice_mm;
  const ou = d.s < Le ? "conduit d'entrée" : d.s <= Le + Lh ? `hélice, ${num((d.s - Le) / M.ds_par_tour_mm, 2)} tour` : "conduit de sortie";
  const T = th => enCelsius() ? num(reel(th)) + " °C" : num(th, 3);
  const b = document.getElementById("bulle");
  b.innerHTML = `<b>${Math.round(d.s)} mm</b> · ${ou}<br>T ailette froide <b>${T(d.Tf)}</b><br>T ailette passive <b>${T(d.Tp)}</b><br>` +
    `p <b>${num(d.p)} Pa</b><br>débit <b>${num(d.q)} m³/h</b>`;
  b.style.display = "block"; b.style.left = Math.min(ev.clientX + 14, innerWidth - b.offsetWidth - 8) + "px"; b.style.top = (ev.clientY + 14) + "px";
  repere.position.set(...pointChemin(d.s)); repere.visible = true;
}
function cacher() { document.getElementById("bulle").style.display = "none"; repere.visible = false;
  for (const G of graphes) { G.croix.setAttribute("visibility", "hidden"); G.points.forEach(p => p.setAttribute("visibility", "hidden")); } }
const enCelsius = () => document.getElementById("degC").checked;
function tracerProfils() {
  if (!PROFILS) return;
  document.getElementById("profils").style.display = "";
  const T = th => enCelsius() ? reel(th) : th;
  document.getElementById("g_t_titre").textContent = enCelsius() ?
    `Température de mélange de l'air (°C), air entrant ${num(TA())} °C, propane ${num(TR())} °C` : "Température de mélange θ (0 = air entrant, 1 = propane)";
  graphes = [
    graphe(document.getElementById("g_t"), [{ f: d => T(d.Tf), c: "var(--s1)" }, { f: d => T(d.Tp), c: "var(--s2)" }], {}),
    graphe(document.getElementById("g_p"), [{ f: d => d.p, c: "var(--s1)" }], { zero: true }),
    graphe(document.getElementById("g_q"), [{ f: d => d.q, c: "var(--s1)" }], { ref: PROFILS.meta.debit_ref, zero: true })];
}
tracerProfils();
await changerChamp(); for (let a = 0; a < 3; a++) maj(a);
(function boucle() { requestAnimationFrame(boucle); ctl.update(); rendu.render(scene, cam); })();
</script></body></html>"""

if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
