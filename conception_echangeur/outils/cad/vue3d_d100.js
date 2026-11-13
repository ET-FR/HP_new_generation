// Vue 3D de l'échangeur Ø 100 : pièces, règles graduées, marqueur, mesure entre deux points,
// animation du chemin de l'air. Gabarit lu par outils/cad/html_d100.py, qui remplace les
// emplacements des pièces, des STL et de la géométrie (en majuscules, ci-dessous).
import * as THREE from "three";
import { TrackballControls } from "three/addons/controls/TrackballControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

const PIECES = __PIECES__;
const STL = __STL__;
const G = __GEOM__;   // géométrie utile à l'animation (mm, repère FreeCAD avant rotation)

const boite = document.getElementById("vue3d");
const rendu = new THREE.WebGLRenderer({ antialias: true, alpha: true });
rendu.setPixelRatio(window.devicePixelRatio);
boite.appendChild(rendu.domElement);
const etiq = new CSS2DRenderer();
etiq.domElement.className = "etiquettes";
boite.appendChild(etiq.domElement);

const scene = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(35, 1, 1, 5000);
cam.up.set(0, 0, 1);
cam.position.set(420, -620, 330);
// rotation libre dans tous les sens (TrackballControls) + vues standard
const ctl = new TrackballControls(cam, rendu.domElement);
ctl.target.set(150, 0, 0);
ctl.rotateSpeed = 3.0; ctl.zoomSpeed = 1.2; ctl.panSpeed = 0.8; ctl.dynamicDampingFactor = 0.15;
const VUES = [["3D", [420, -620, 330], [0, 0, 1]], ["Dessus", [150, 0, 900], [0, 1, 0]], ["Face", [150, -900, 0], [0, 0, 1]],
  ["Bout entrée", [900, 0, 0], [0, 0, 1]], ["Bout sortie", [-600, 0, 0], [0, 0, 1]]];
const barreVues = document.createElement("span");
barreVues.className = "vues";
barreVues.innerHTML = "Vue : ";
for (const [nom, p, u] of VUES) {
  const b = document.createElement("button");
  b.textContent = nom;
  b.onclick = () => { ctl.target.set(...[150, 0, 0]); cam.position.set(...p); cam.up.set(...u); cam.lookAt(ctl.target); ctl.update(); };
  barreVues.appendChild(b);
}
document.getElementById("outils").prepend(barreVues);
scene.add(new THREE.HemisphereLight(0xffffff, 0x667788, 1.1));
const sol = new THREE.DirectionalLight(0xffffff, 1.4); sol.position.set(300, -400, 600); scene.add(sol);
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
const cibles = [];   // maillages visibles que le marqueur et la règle peuvent toucher
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
  const obj = new THREE.Mesh(g, m); obj.renderOrder = p.opacite < 1 ? 1 : 0; scene.add(obj);
  cibles.push(obj);
  interrupteur(p.titre, p.couleur, true, v => { obj.visible = v; });
}

// ---------- Règles graduées (mm) ----------
// Repère de la vue : x = axe du tube principal (0 = début de la zone d'échange, l'air avance vers +x),
// z = vertical. Une règle le long de l'axe sous l'échangeur, une règle verticale au bout gauche.
const regles = new THREE.Group(); scene.add(regles);
const cT = coul("--texte");
function regle(debut, dir, perp, long, pas, pasEtiq, nom) {
  const pts = [], d = dir.clone().normalize(), n = perp.clone().normalize();
  pts.push(debut.clone(), debut.clone().addScaledVector(d, long));
  for (let s = 0; s <= long + 1e-6; s += pas) {
    const k = Math.round(s / pas), grand = Math.abs(s % pasEtiq) < 1e-6, moyen = k % 5 === 0;
    const a = debut.clone().addScaledVector(d, s);
    pts.push(a, a.clone().addScaledVector(n, grand ? 9 : moyen ? 6 : 3));
    if (grand) {
      const t = texte(String(Math.round(s + nom.zero)), "et regle");
      t.position.copy(a.clone().addScaledVector(n, -7)); regles.add(t);
    }
  }
  regles.add(ligne(pts, cT, 0.9));
  const t = texte(nom.titre, "et regle titre");
  t.position.copy(debut.clone().addScaledVector(d, long + 14)); t.element.classList.add("bout"); regles.add(t);
}
const yR = -G.ri - G.ep - 25;                    // devant l'échangeur, côté caméra
const zR = -G.ri - G.ep - 12;                    // sous l'échangeur
const xMin = Math.floor(G.x_min / 10) * 10, xMax = Math.ceil(G.x_max / 10) * 10;
regle(new THREE.Vector3(xMin, yR, zR), new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 1),
  xMax - xMin, 10, 50, { zero: xMin, titre: "x (mm), 0 = début de la zone d’échange" });
const zMin = -60, zMax = 60;
regle(new THREE.Vector3(xMin - 15, yR, zMin), new THREE.Vector3(0, 0, 1), new THREE.Vector3(1, 0, 0),
  zMax - zMin, 5, 20, { zero: zMin, titre: "z (mm)" });
// Trièdre au point (0, 0, 0) : origine de la zone d'échange, sur l'axe
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
const geoBille = new THREE.SphereGeometry(1.6, 16, 12);
const matBille = new THREE.MeshBasicMaterial({ color: coul("--accent"), depthTest: false });
let premier = null;
const f1 = v => v.toFixed(1).replace(".", ",");
function decrire(q) {
  const r = Math.hypot(q.y, q.z);
  return `x ${f1(q.x)} · y ${f1(q.y)} · z ${f1(q.z)} · r ${f1(r)} mm`;
}
function bille(q) {
  const b = new THREE.Mesh(geoBille, matBille); b.position.copy(q); b.renderOrder = 10; marques.add(b);
}
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
  if (Math.hypot(e.clientX - appui[0], e.clientY - appui[1]) > 4) return;   // c'était une rotation
  const r = rendu.domElement.getBoundingClientRect();
  souris.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  lancer.setFromCamera(souris, cam);
  const h = lancer.intersectObjects(cibles.filter(o => o.visible), false)[0];
  if (!h) return;
  const q = h.point.clone();
  bille(q);
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

// ---------- Animation du chemin de l'air ----------
// Trajectoire idéale d'une particule (repère FreeCAD : axe z, puis tourné comme les pièces) :
// conduit d'entrée incliné → hélice dans l'anneau (sens trigonométrique vu de +z) → conduit de sortie.
// Vitesse constante le long du chemin : à débit égal, la vitesse dans l'hélice ≈ la vitesse du conduit.
const vers = (x, y, z) => new THREE.Vector3(z, y, -x);   // rotation de 90° autour de Y, comme le modèle
const ta = Math.tan(G.angle * Math.PI / 180);
function chemin(rp, tours) {
  const pts = [], xc = G.ri - G.w / 2, z0 = -G.P / 2, z1 = G.L + G.P / 2;
  for (let i = 0; i <= 20; i++) { const y = -G.lc + G.lc * i / 20; pts.push(vers(xc, y, z0 + y * ta)); }
  const th1 = 2 * Math.PI * tours, n = Math.max(80, Math.round(tours * 60));
  for (let i = 1; i <= n; i++) {
    const u = i / n, th = th1 * u;
    const pont = Math.min(1, Math.min(u, 1 - u) / 0.04);           // passe du rayon du conduit à celui de la particule
    const r = xc + (rp - xc) * pont;
    pts.push(vers(r * Math.cos(th), r * Math.sin(th), z0 + (z1 - z0) * u));
  }
  for (let i = 1; i <= 20; i++) { const y = -G.lc * i / 20; pts.push(vers(-xc, y, z1 - y * ta)); }
  return new THREE.CatmullRomCurve3(pts, false, "centripetal");
}
const N_PART = 360, N_CHEM = 24;
const air = new THREE.Group(); scene.add(air);
let chemins = [], traces = null;
const geoP = new THREE.SphereGeometry(1.4, 8, 6);
const matP = new THREE.MeshBasicMaterial({ vertexColors: false });
const parts = new THREE.InstancedMesh(geoP, matP, N_PART); air.add(parts);
const depart = Array.from({ length: N_PART }, () => Math.random());
const voie = Array.from({ length: N_PART }, (_, i) => i % N_CHEM);
const cA = new THREE.Color(coul("--air-debut")), cB = new THREE.Color(coul("--air-fin")), cTmp = new THREE.Color();
function construire(tours) {
  chemins = [];
  const r0 = G.r_noyau + 2.5, r1 = G.ri - 2.5;
  for (let k = 0; k < N_CHEM; k++) chemins.push(chemin(r0 + (r1 - r0) * (k + 0.5) / N_CHEM, tours));
  if (traces) { air.remove(traces); traces.geometry.dispose(); }
  const seg = [];
  for (const c of [chemins[3], chemins[N_CHEM - 4]]) {
    const p = c.getPoints(Math.round(tours * 80) + 60);
    for (let i = 1; i < p.length; i++) seg.push(p[i - 1], p[i]);
  }
  traces = ligne(seg, coul("--air-fin"), 0.35); air.add(traces);
  longueur = chemins[Math.floor(N_CHEM / 2)].getLength();
}
let longueur = 1;
const tSlider = document.getElementById("tours"), tVal = document.getElementById("tours_val");
const vSlider = document.getElementById("vitesse");
function majTours() {
  const t = Number(tSlider.value) + 0.5;      // demi-tour en plus : la sortie est à l'opposé de l'entrée
  tVal.textContent = t.toLocaleString("fr-FR") + (Math.abs(t - G.tours_ideal) < 0.6 ? " (idéal, sans perte de rotation)" : "");
  construire(t);
}
tSlider.max = Math.ceil(G.tours_ideal);
tSlider.value = Math.round(G.tours_ideal - 0.5);
tSlider.addEventListener("input", majTours); majTours();
let anime = true;
interrupteur("Chemin de l'air (animation)", coul("--air-fin"), true, v => { anime = v; air.visible = v; });

const mat4 = new THREE.Matrix4(), hor = new THREE.Clock();
let temps = 0;
function avancer(dt) {
  // vSlider : vitesse affichée en mm/s du chemin (ralenti), 1 tour de cycle ≈ longueur / vitesse
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
  const dt = Math.min(hor.getDelta(), 0.1);
  if (anime) avancer(dt);
  ctl.update(); rendu.render(scene, cam); etiq.render(scene, cam);
})();
