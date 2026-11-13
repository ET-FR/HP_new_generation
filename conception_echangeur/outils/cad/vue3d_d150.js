// Vue 3D de l'échangeur Ø 150 à canal hélicoïdal : pièces, règles graduées, marqueur, mesure entre
// deux points, animation de l'air le long du canal. Gabarit lu par outils/cad/html_d150.py, qui remplace
// les emplacements des pièces, des STL et de la géométrie (en majuscules, ci-dessous).
// Repère du modèle FreeCAD : axe z vertical, z = 0 sur la face intérieure du fond bas.
import * as THREE from "three";
import { TrackballControls } from "three/addons/controls/TrackballControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

const PIECES = __PIECES__;
const STL = __STL__;
const G = __GEOM__;

const boite = document.getElementById("vue3d");
const rendu = new THREE.WebGLRenderer({ antialias: true, alpha: true });
rendu.setPixelRatio(window.devicePixelRatio);
boite.appendChild(rendu.domElement);
const etiq = new CSS2DRenderer();
etiq.domElement.className = "etiquettes";
boite.appendChild(etiq.domElement);

const scene = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(35, 1, 1, 6000);
cam.up.set(0, 0, 1);
cam.position.set(620, -720, 520);
// rotation libre dans tous les sens (TrackballControls) + vues standard
const ctl = new TrackballControls(cam, rendu.domElement);
ctl.target.set(0, 0, G.Lint / 2);
ctl.rotateSpeed = 3.0; ctl.zoomSpeed = 1.2; ctl.panSpeed = 0.8; ctl.dynamicDampingFactor = 0.15;
const VUES = [["3D", [620, -720, 520], [0, 0, 1]], ["Dessus", [0, 0, 1100], [0, 1, 0]], ["Dessous", [0, 0, -900], [0, 1, 0]],
  ["Face", [0, -1100, 0], [0, 0, 1]], ["Côté", [1100, 0, 0], [0, 0, 1]]];
const barreVues = document.createElement("span");
barreVues.className = "vues";
barreVues.innerHTML = "Vue : ";
for (const [nom, p, u] of VUES) {
  const b = document.createElement("button");
  b.textContent = nom;
  b.onclick = () => { ctl.target.set(...[0, 0, G.Lint / 2]); cam.position.set(...p); cam.up.set(...u); cam.lookAt(ctl.target); ctl.update(); };
  barreVues.appendChild(b);
}
document.getElementById("outils").prepend(barreVues);
scene.add(new THREE.HemisphereLight(0xffffff, 0x667788, 1.1));
const sol = new THREE.DirectionalLight(0xffffff, 1.4); sol.position.set(300, -400, 700); scene.add(sol);
const sol2 = new THREE.DirectionalLight(0xffffff, 0.5); sol2.position.set(-300, 400, -200); scene.add(sol2);

const css = getComputedStyle(document.documentElement);
const coul = n => css.getPropertyValue(n).trim() || "#888";
function texte(t, cls = "et") {
  const e = document.createElement("div"); e.className = cls; e.textContent = t;
  return new CSS2DObject(e);
}
function ligne(points, couleur, opacite = 1) {
  const g = new THREE.BufferGeometry().setFromPoints(points);
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: couleur, transparent: opacite < 1, opacity: opacite }));
}

// ---------- Pièces ----------
const lecteur = new STLLoader();
const ctrl = document.getElementById("ctrl");
const cibles = [];
function interrupteur(titre, couleur, coche, action) {
  const l = document.createElement("label");
  l.innerHTML = `<input type="checkbox" ${coche ? "checked" : ""}>` +
    (couleur ? `<span class="pastille" style="background:${couleur}"></span>` : "") + titre;
  l.querySelector("input").addEventListener("change", e => action(e.target.checked));
  ctrl.appendChild(l);
}
for (const p of PIECES) {
  const bin = Uint8Array.from(atob(STL[p.nom]), c => c.charCodeAt(0)).buffer;
  const g = lecteur.parse(bin); g.computeVertexNormals();
  const m = new THREE.MeshStandardMaterial({ color: p.couleur, roughness: 0.45, metalness: 0.15,
    transparent: p.opacite < 1, opacity: p.opacite, depthWrite: p.opacite >= 1, side: THREE.DoubleSide });
  const obj = new THREE.Mesh(g, m); obj.renderOrder = p.opacite < 1 ? 1 : 0; obj.visible = p.visible; scene.add(obj);
  cibles.push(obj);
  interrupteur(p.titre, p.couleur, p.visible, v => { obj.visible = v; });
}

// ---------- Règles graduées (mm) ----------
const regles = new THREE.Group(); scene.add(regles);
const cT = coul("--texte");
function regle(debut, dir, perp, long, pas, pasEtiq, zero, titre) {
  const pts = [], d = dir.clone().normalize(), n = perp.clone().normalize();
  pts.push(debut.clone(), debut.clone().addScaledVector(d, long));
  for (let s = 0; s <= long + 1e-6; s += pas) {
    const k = Math.round(s / pas), grand = Math.abs(((s + zero) % pasEtiq + pasEtiq) % pasEtiq) < 1e-6;
    const a = debut.clone().addScaledVector(d, s);
    pts.push(a, a.clone().addScaledVector(n, grand ? 9 : k % 5 === 0 ? 6 : 3));
    if (grand) {
      const t = texte(String(Math.round(s + zero)), "et regle");
      t.position.copy(a.clone().addScaledVector(n, -9)); regles.add(t);
    }
  }
  regles.add(ligne(pts, cT, 0.9));
  const t = texte(titre, "et regle titre bout");
  t.position.copy(debut.clone().addScaledVector(d, long + 16)); regles.add(t);
}
// règle verticale le long de l'axe, devant le tube ; règle horizontale du diamètre, sous le tube
const yR = -G.Ro - 30;
regle(new THREE.Vector3(-G.Ro - 20, yR, 0), new THREE.Vector3(0, 0, 1), new THREE.Vector3(-1, 0, 0),
  Math.floor(G.Lint / 10) * 10, 10, 50, 0, "z (mm), 0 = intérieur du fond bas");
regle(new THREE.Vector3(-G.Ro, yR, -G.ep - 25), new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, -1),
  2 * G.Ro, 5, 25, -G.Ro, "x (mm), 0 = axe");
const triedre = new THREE.AxesHelper(40); scene.add(triedre);
for (const [t, v] of [["x", [46, 0, 0]], ["y", [0, 46, 0]], ["z", [0, 0, 46]]]) {
  const o = texte(t, "et axe"); o.position.set(...v); triedre.add(o);
}
interrupteur("Règles et repère", null, true, v => { regles.visible = v; triedre.visible = v; });

// ---------- Marqueur et mesure ----------
const outils = document.getElementById("outils");
const info = document.getElementById("mesure");
let mode = "aucun";
const marques = new THREE.Group(); scene.add(marques);
const geoBille = new THREE.SphereGeometry(1.8, 16, 12);
const matBille = new THREE.MeshBasicMaterial({ color: coul("--accent"), depthTest: false });
let premier = null;
const f1 = v => v.toFixed(1).replace(".", ",");
const decrire = q => `x ${f1(q.x)} · y ${f1(q.y)} · z ${f1(q.z)} · r ${f1(Math.hypot(q.x, q.y))} mm`;
function choisir(m) {
  mode = mode === m ? "aucun" : m; premier = null;
  for (const b of outils.querySelectorAll("button[data-mode]")) b.classList.toggle("actif", b.dataset.mode === mode);
  info.textContent = mode === "marqueur" ? "Cliquer sur une pièce pour poser un marqueur."
    : mode === "regle" ? "Cliquer sur deux points pour mesurer la distance." : "";
  rendu.domElement.style.cursor = mode === "aucun" ? "" : "crosshair";
}
outils.querySelector("[data-mode=marqueur]").onclick = () => choisir("marqueur");
outils.querySelector("[data-mode=regle]").onclick = () => choisir("regle");
outils.querySelector("[data-act=effacer]").onclick = () => {
  for (const o of [...marques.children]) { marques.remove(o); if (o.element) o.element.remove(); }
  premier = null; info.textContent = "";
};
const lancer = new THREE.Raycaster(), souris = new THREE.Vector2();
let appui = null;
rendu.domElement.addEventListener("pointerdown", e => { appui = [e.clientX, e.clientY]; });
rendu.domElement.addEventListener("pointerup", e => {
  if (!appui || mode === "aucun" || e.button !== 0) return;
  if (Math.hypot(e.clientX - appui[0], e.clientY - appui[1]) > 4) return;
  const r = rendu.domElement.getBoundingClientRect();
  souris.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  lancer.setFromCamera(souris, cam);
  const h = lancer.intersectObjects(cibles.filter(o => o.visible), false)[0];
  if (!h) return;
  const q = h.point.clone();
  const b = new THREE.Mesh(geoBille, matBille); b.position.copy(q); b.renderOrder = 10; marques.add(b);
  if (mode === "marqueur") {
    const t = texte(decrire(q), "et marque"); t.position.copy(q); marques.add(t);
    info.textContent = decrire(q);
  } else if (!premier) {
    premier = q; info.textContent = "Premier point : " + decrire(q) + ". Cliquer le second.";
  } else {
    const l = ligne([premier, q], coul("--accent")); l.material.depthTest = false; l.renderOrder = 10; marques.add(l);
    const dd = q.clone().sub(premier);
    const t = texte(`${f1(dd.length())} mm`, "et marque");
    t.position.copy(premier.clone().add(q).multiplyScalar(0.5)); marques.add(t);
    info.textContent = `Distance ${f1(dd.length())} mm · Δx ${f1(dd.x)} · Δy ${f1(dd.y)} · Δz ${f1(dd.z)} mm`;
    premier = null;
  }
});

// ---------- Animation de l'air ----------
// conduit d'entrée (colonne x = r, de y = −Ld à 0) → hélice de rayon r, z monte d'un pas par tour,
// sur G.tours tours → conduit de sortie, tangent à θ_fin. Vitesse constante le long du chemin.
function chemin(r, dz) {
  const pts = [], z0 = dz, th1 = 2 * Math.PI * G.tours;
  const ta = G.ta || 0;                         // conduits inclinés de la pente de l'hélice
  for (let i = 0; i <= 12; i++) { const y = -G.Ld + G.Ld * i / 12; pts.push(new THREE.Vector3(r, y, z0 + y * ta)); }
  const n = Math.round(G.tours * 90);
  for (let i = 1; i <= n; i++) {
    const th = th1 * i / n;
    pts.push(new THREE.Vector3(r * Math.cos(th), r * Math.sin(th), z0 + G.pas * th / (2 * Math.PI)));
  }
  const fin = pts[pts.length - 1].clone(), tx = -Math.sin(th1), ty = Math.cos(th1);
  for (let i = 1; i <= 12; i++) pts.push(new THREE.Vector3(fin.x + tx * G.Ld * i / 12, fin.y + ty * G.Ld * i / 12, fin.z + G.Ld * i / 12 * ta));
  const c = new THREE.CatmullRomCurve3(pts, false, "centripetal");
  c.arcLengthDivisions = pts.length * 4;
  return c;
}
const N_CHEM = 30, N_PART = 420;
const chemins = [];
for (let k = 0; k < N_CHEM; k++) {
  const r = G.Rc + 3 + (G.Ri - G.Rc - 6) * ((k * 0.618034) % 1);
  const dz = 6 + (G.gap - 12) * ((k * 0.381966 + 0.5) % 1);
  chemins.push(chemin(r, dz));
}
const longueur = chemins[0].getLength();
const air = new THREE.Group(); scene.add(air);
const parts = new THREE.InstancedMesh(new THREE.SphereGeometry(1.6, 8, 6), new THREE.MeshBasicMaterial(), N_PART);
air.add(parts);
const seg = [];
for (const c of [chemins[3], chemins[11]]) {
  const p = c.getPoints(400);
  for (let i = 1; i < p.length; i++) seg.push(p[i - 1], p[i]);
}
air.add(ligne(seg, coul("--air-fin"), 0.35));
const depart = Array.from({ length: N_PART }, () => Math.random());
const voie = Array.from({ length: N_PART }, (_, i) => i % N_CHEM);
const cA = new THREE.Color(coul("--air-debut")), cB = new THREE.Color(coul("--air-fin")), cTmp = new THREE.Color();
let anime = true;
interrupteur("Chemin de l'air (animation)", coul("--air-fin"), true, v => { anime = v; air.visible = v; });
const vSlider = document.getElementById("vitesse");
const mat4 = new THREE.Matrix4(), hor = new THREE.Clock();
let temps = 0;
function avancer(dt) {
  temps += dt * Number(vSlider.value) / longueur;
  for (let i = 0; i < N_PART; i++) {
    const s = (depart[i] + temps) % 1;
    parts.setMatrixAt(i, mat4.makeTranslation(chemins[voie[i]].getPointAt(s)));
    parts.setColorAt(i, cTmp.copy(cA).lerp(cB, s));
  }
  parts.instanceMatrix.needsUpdate = true;
  if (parts.instanceColor) parts.instanceColor.needsUpdate = true;
}

function taille() {
  const w = boite.clientWidth, h = boite.clientHeight;
  rendu.setSize(w, h); etiq.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); ctl.handleResize();
}
new ResizeObserver(taille).observe(boite); taille();
(function boucle() {
  requestAnimationFrame(boucle);
  if (anime) avancer(Math.min(hor.getDelta(), 0.1)); else hor.getDelta();
  ctl.update(); rendu.render(scene, cam); etiq.render(scene, cam);
})();
