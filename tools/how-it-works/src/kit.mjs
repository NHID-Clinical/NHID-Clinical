// Clay-render kit: materials, primitives, figures, props, path, lights, camera
// rig, label overlay. Every animated value is set from a time t by the caller;
// nothing here keeps its own clock.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

export { THREE };
export const C = {
  clay: '#f6f7f9', clay2: '#e6e9ee', clay3: '#d7dce3', teal: '#14B8A6', tealDeep: '#0e9484', amber: '#F5B840',
  coral: '#f2907f', mint: '#cfeee8', sky: '#cfdcf0', rose: '#f3d9dc', navy: '#243049', sand: '#f1e4d2', hair: '#c9a27e',
};
export const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
export const smooth = v => { v = clamp(v); return v * v * (3 - 2 * v); };
export const easeOut = v => { v = clamp(v); return 1 - (1 - v) * (1 - v) * (1 - v); };
export const easeIn = v => { v = clamp(v); return v * v * v; };
export const lerp = (a, b, p) => a + (b - a) * p;
export const seg = (t, a, b) => clamp((t - a) / (b - a));           // 0..1 across [a,b]
export const pop = v => { v = clamp(v); return v < .7 ? 1.18 * easeOut(v / .7) : lerp(1.18, 1, (v - .7) / .3); }; // overshoot scale

export const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: .9, metalness: 0, envMapIntensity: .12, ...o });
export const glow = (color, i = 1) => new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: i * .38, roughness: .6, metalness: 0, envMapIntensity: .05 });

export function mesh(geo, m, x = 0, y = 0, z = 0) { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; return o; }
export const box = (w, h, d, r, m, x, y, z) => mesh(new RoundedBoxGeometry(w, h, d, 4, Math.min(r, w / 2, h / 2, d / 2)), m, x, y, z);
export const cyl = (r, h, m, x, y, z, rt = r) => mesh(new THREE.CylinderGeometry(rt, r, h, 32), m, x, y, z);
export const ball = (r, m, x, y, z) => mesh(new THREE.SphereGeometry(r, 28, 20), m, x, y, z);
export const capsule = (r, len, m, x, y, z) => mesh(new THREE.CapsuleGeometry(r, len, 6, 20), m, x, y, z);
export const group = (...kids) => { const g = new THREE.Group(); kids.forEach(k => g.add(k)); return g; };

// ── Figures ───────────────────────────────────────────────────────────────────
export function robot() {
  const g = new THREE.Group();
  const white = mat(C.clay), dark = mat(C.navy, { roughness: .6 });
  const body = box(.64, .6, .44, .14, white, 0, .62, 0);
  const head = box(.58, .46, .5, .15, white, 0, 1.2, 0);
  const eyeL = cyl(.055, .03, dark, -.13, 1.24, .25), eyeR = cyl(.055, .03, dark, .13, 1.24, .25);
  eyeL.rotation.x = eyeR.rotation.x = Math.PI / 2;
  const earL = cyl(.09, .06, mat(C.clay2), -.31, 1.2, 0), earR = cyl(.09, .06, mat(C.clay2), .31, 1.2, 0);
  earL.rotation.z = earR.rotation.z = Math.PI / 2;
  const stem = cyl(.025, .2, mat(C.clay2), 0, 1.52, 0); const bulb = ball(.075, glow(C.teal, .9), 0, 1.64, 0);
  const badgeMat = mat(C.clay2); const badge = box(.3, .2, .05, .04, badgeMat, 0, .72, .24);
  const neck = cyl(.14, .1, mat(C.clay2), 0, .95, 0);
  const legL = capsule(.1, .16, mat(C.clay2), -.17, .18, 0), legR = capsule(.1, .16, mat(C.clay2), .17, .18, 0);
  const armL = new THREE.Group(), armR = new THREE.Group(); armL.position.set(-.4, .84, 0); armR.position.set(.4, .84, 0);
  armL.add(capsule(.085, .3, mat(C.clay2), 0, -.2, 0)); armR.add(capsule(.085, .3, mat(C.clay2), 0, -.2, 0));
  const hand = new THREE.Group(); hand.position.set(0, -.42, 0); armR.add(hand);
  g.add(body, head, eyeL, eyeR, earL, earR, stem, bulb, badge, neck, legL, legR, armL, armR);
  return {
    g, hand, badgeMat,
    walk(phase, moving) { const s = moving ? Math.sin(phase * 10) : 0; legL.position.z = .12 * s; legR.position.z = -.12 * s; armL.rotation.x = -.5 * s; if (!this._hold) armR.rotation.x = .5 * s; g.position.y = this._baseY + (moving ? Math.abs(Math.sin(phase * 10)) * .05 : 0); },
    _baseY: 0, _hold: 0,
    hold(a) { this._hold = a; armR.rotation.x = -2.0 * a; armR.rotation.z = -.25 * a; },
    light(a) { badgeMat.color.set(C.clay2).lerp(new THREE.Color(C.teal), a); badgeMat.emissive.set(C.teal); badgeMat.emissiveIntensity = a * .9; bulb.material.emissiveIntensity = .6 + .5 * a; },
  };
}

export function person({ color = C.sky, hat = 'none' } = {}) {
  const g = new THREE.Group(); const skin = mat(C.clay);
  const body = capsule(.21, .36, mat(color), 0, .6, 0);
  const head = ball(.2, skin, 0, 1.08, 0);
  const legL = capsule(.08, .18, mat(C.clay2), -.12, .17, 0), legR = capsule(.08, .18, mat(C.clay2), .12, .17, 0);
  const armL = capsule(.07, .26, mat(color), -.3, .64, 0), armR = capsule(.07, .26, mat(color), .3, .64, 0);
  g.add(body, head, legL, legR, armL, armR);
  if (hat === 'nurse') { const cap = cyl(.16, .1, mat(C.clay), 0, 1.27, 0, .19); const c1 = box(.12, .035, .025, .01, mat(C.teal), 0, 1.3, .17), c2 = box(.035, .12, .025, .01, mat(C.teal), 0, 1.3, .17); g.add(cap, c1, c2); }
  if (hat === 'officer') { const cap = cyl(.2, .12, mat(C.navy), 0, 1.25, 0, .21); const brim = box(.3, .03, .22, .01, mat(C.navy), 0, 1.2, .16); const band = cyl(.21, .03, mat(C.teal), 0, 1.21, 0); g.add(cap, brim, band); }
  if (hat === 'teacher') { const hair = ball(.215, mat(C.hair), 0, 1.11, -.03); hair.scale.set(1, .85, 1); const bun = ball(.11, mat(C.hair), 0, 1.22, -.18); g.add(hair, bun); }
  if (hat === 'child') { g.scale.set(.7, .7, .7); const hair = ball(.215, mat(C.hair), 0, 1.11, -.03); hair.scale.set(1, .8, 1); g.add(hair); }
  return { g, walk(phase, moving) { const s = moving ? Math.sin(phase * 10) : 0; legL.position.z = .1 * s; legR.position.z = -.1 * s; armL.rotation.x = -.6 * s; armR.rotation.x = .6 * s; } };
}

// ── Props ─────────────────────────────────────────────────────────────────────
export function gate(w = 2.2) {
  const g = new THREE.Group(); const white = mat(C.clay);
  const pL = box(.2, 1.5, .2, .06, white, -w / 2, .75, 0), pR = box(.2, 1.5, .2, .06, white, w / 2, .75, 0);
  const beam = box(w + .2, .18, .22, .06, white, 0, 1.55, 0);
  const stripMat = glow(C.amber, .9); const strip = box(w - .3, .05, .06, .02, stripMat, 0, 1.45, .1); strip.castShadow = false;
  const panel = box(w - .22, 1.25, .08, .05, mat(C.clay2), 0, .64, 0);
  const grip = box(.5, .06, .1, .02, mat(C.clay3), 0, .9, .06); grip.castShadow = false;
  panel.add(grip); grip.position.set(0, .3, .06);
  const baseL = cyl(.22, .08, mat(C.clay2), -w / 2, .04, 0), baseR = cyl(.22, .08, mat(C.clay2), w / 2, .04, 0);
  g.add(pL, pR, beam, strip, panel, baseL, baseR);
  return { g, strip: stripMat, open(a) { panel.position.y = lerp(.64, -.9, easeIn(a)); }, ok(a) { stripMat.color.set(C.amber).lerp(new THREE.Color(C.teal), a); stripMat.emissive.copy(stripMat.color); } };
}

export function arch() {
  const g = new THREE.Group(); const white = mat(C.clay);
  const pL = cyl(.14, 1.9, white, -.75, .95, 0), pR = cyl(.14, 1.9, white, .75, .95, 0);
  const top = box(1.8, .3, .32, .1, white, 0, 2.0, 0);
  const ringMat = glow(C.teal, .7); const ring = box(1.3, .06, .1, .02, ringMat, 0, 1.83, .12); ring.castShadow = false;
  const bL = cyl(.26, .1, mat(C.clay2), -.75, .05, 0), bR = cyl(.26, .1, mat(C.clay2), .75, .05, 0);
  const lamp = ball(.1, ringMat, 0, 2.2, 0);
  g.add(pL, pR, top, ring, bL, bR, lamp);
  return { g, ring: ringMat, alarm(a) { ringMat.color.set(C.teal).lerp(new THREE.Color(C.amber), a); ringMat.emissive.copy(ringMat.color); ringMat.emissiveIntensity = .7 + a * .6; } };
}

export function button() {
  const g = new THREE.Group();
  const post = cyl(.16, .8, mat(C.clay), 0, .4, 0); const top = cyl(.34, .12, mat(C.clay2), 0, .86, 0);
  const domeMat = mat(C.coral, { roughness: .7 }); const dome = ball(.22, domeMat, 0, .95, 0); dome.scale.y = .7;
  const ring = cyl(.3, .04, mat(C.clay3), 0, .93, 0, .3);
  g.add(post, top, dome, ring);
  return { g, press(a) { dome.position.y = .95 - .08 * a; }, lit(a) { domeMat.emissive.set(C.coral); domeMat.emissiveIntensity = .6 * a; } };
}

export function book() {
  const g = new THREE.Group();
  const stand = box(1.0, .95, .62, .1, mat(C.clay), 0, .475, 0);
  const top = box(1.12, .08, .72, .03, mat(C.clay2), 0, .99, 0);
  const pageL = box(.48, .06, .62, .02, mat('#ffffff'), -.25, 1.06, 0), pageR = box(.48, .06, .62, .02, mat('#ffffff'), .25, 1.06, 0);
  pageL.rotation.z = .12; pageR.rotation.z = -.12;
  const ticks = []; for (let i = 0; i < 5; i++) { const tk = box(.12, .03, .05, .01, glow(C.teal, .8), .1 + (i % 3) * .14, 1.1, -.18 + Math.floor(i / 3) * .2); tk.scale.setScalar(0); tk.castShadow = false; g.add(tk); ticks.push(tk); }
  const lines = []; for (let i = 0; i < 4; i++) { const ln = box(.32, .012, .03, .005, mat(C.clay3), -.28, 1.1, -.2 + i * .13); g.add(ln); }
  const stamp = new THREE.Group(); stamp.position.set(.2, 1.75, 0);
  stamp.add(cyl(.09, .22, mat(C.clay2), 0, 0, 0), cyl(.14, .06, mat(C.clay), 0, -.14, 0), ball(.06, mat(C.teal), 0, .14, 0));
  g.add(stand, top, pageL, pageR, stamp);
  return { g, ticks, stamp, tick(i, a) { ticks[i].scale.setScalar(pop(a)); }, stampAt(a) { stamp.position.y = 1.75 - .5 * Math.sin(clamp(a) * Math.PI); } };
}

export function padlock() {
  const g = new THREE.Group();
  const body = box(.26, .22, .1, .05, mat(C.amber), 0, .11, 0);
  const shackle = mesh(new THREE.TorusGeometry(.085, .028, 12, 24, Math.PI), mat(C.clay3), 0, .22, 0);
  const key = cyl(.03, .02, mat(C.navy), 0, .09, .052); key.rotation.x = Math.PI / 2;
  g.add(body, shackle, key);
  return { g, open(a) { shackle.position.y = .22 + .1 * a; shackle.rotation.y = a * 1.2; body.material.color.set(C.amber).lerp(new THREE.Color(C.teal), a); } };
}

export function folder() {
  const g = new THREE.Group();
  const f = box(.7, .1, .5, .03, mat(C.sky), 0, .05, 0); const tab = box(.24, .11, .14, .03, mat(C.sky), -.2, .055, -.3);
  const sheet = box(.6, .02, .4, .01, mat('#ffffff'), 0, .11, .02);
  g.add(f, tab, sheet); return g;
}

export function suitcase() {
  const g = new THREE.Group();
  g.add(box(.7, .5, .3, .08, mat(C.sky), 0, .25, 0), box(.26, .08, .1, .03, mat(C.clay3), 0, .54, 0), box(.5, .06, .32, .02, mat(C.clay3), 0, .25, 0));
  return g;
}

export function card({ w = .36, h = .44, color = C.sand, face = true } = {}) {
  const g = new THREE.Group();
  g.add(box(w, h, .03, .04, mat(color), 0, 0, 0));
  if (face) { const dark = mat(C.navy, { roughness: .6 }); const e1 = cyl(.03, .02, dark, -.08, .08, .02), e2 = cyl(.03, .02, dark, .08, .08, .02); e1.rotation.x = e2.rotation.x = Math.PI / 2; const mouth = mesh(new THREE.TorusGeometry(.08, .016, 8, 20, Math.PI), dark, 0, -.04, .02); mouth.rotation.z = Math.PI; g.add(e1, e2, mouth); }
  return g;
}

export function tray() {
  const g = new THREE.Group();
  g.add(box(.9, .1, .7, .03, mat(C.clay2), 0, .05, 0), box(.9, .18, .06, .02, mat(C.clay2), 0, .12, .32), box(.9, .18, .06, .02, mat(C.clay2), 0, .12, -.32), box(.06, .18, .7, .02, mat(C.clay2), -.42, .12, 0));
  return g;
}

export function receipt() { const g = new THREE.Group(); g.add(box(.34, .02, .5, .01, mat('#ffffff'), 0, .01, 0), box(.12, .03, .05, .01, glow(C.teal, .8), 0, .03, -.12), box(.2, .012, .03, .005, mat(C.clay3), 0, .03, .02), box(.2, .012, .03, .005, mat(C.clay3), 0, .03, .1)); return g; }

export function tree(x, z, s = 1) { const g = new THREE.Group(); g.add(cyl(.05, .35, mat(C.clay3), 0, .17, 0), ball(.32, mat(C.mint), 0, .55, 0), ball(.22, mat(C.mint), .18, .72, .08)); g.position.set(x, 0, z); g.scale.setScalar(s); return g; }
export function sign(w = 1.2, h = .36, y = 1.9) { const g = new THREE.Group(); g.add(cyl(.07, y, mat(C.clay2), 0, y / 2, 0), box(w, h, .06, .05, mat(C.clay), 0, y, 0)); return g; }

// ── Path ──────────────────────────────────────────────────────────────────────
export function path(points, { width = .9, y = .012 } = {}) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(p[0], y, p[1])), false, 'centripetal', .5);
  const N = 160, pos = [], idx = [], up = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i <= N; i++) { const u = i / N, p = curve.getPointAt(u), tg = curve.getTangentAt(u), n = new THREE.Vector3().crossVectors(up, tg).normalize().multiplyScalar(width / 2); pos.push(p.x - n.x, y, p.z - n.z, p.x + n.x, y, p.z + n.z); if (i < N) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.setIndex(idx); geo.computeVertexNormals();
  const ribbon = new THREE.Mesh(geo, mat(C.clay2, { roughness: .95 })); ribbon.receiveShadow = true;
  const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 200, .03, 10, false), glow(C.tealDeep, 1.0)); tube.position.y = .03;
  const halo = new THREE.Mesh(new THREE.TubeGeometry(curve, 200, .075, 10, false), new THREE.MeshBasicMaterial({ color: C.teal, transparent: true, opacity: .16, depthWrite: false })); halo.position.y = .03;
  const pills = []; const g = group(tube, halo);
  for (let i = 0; i < 9; i++) { const p = capsule(.045, .14, glow('#8fe9dc', 1.3), 0, .05, 0); p.castShadow = false; g.add(p); pills.push(p); }
  return {
    g, curve, len: curve.getLength(),
    at(u) { return curve.getPointAt(clamp(u)); }, tan(u) { return curve.getTangentAt(clamp(u)); },
    flow(t, speed = .06) { pills.forEach((p, i) => { const u = (t * speed + i / pills.length) % 1; const pt = curve.getPointAt(u), tg = curve.getTangentAt(u); p.position.set(pt.x, .05, pt.z); p.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tg); }); },
  };
}
// nearest u on the curve to a world xz point
export function uNear(p, x, z) { let best = 0, bd = 1e9; for (let i = 0; i <= 400; i++) { const q = p.curve.getPointAt(i / 400); const d = (q.x - x) ** 2 + (q.z - z) ** 2; if (d < bd) { bd = d; best = i / 400; } } return best; }

// ── Stage: renderer, lights, plate, camera, composer ──────────────────────────
// Renders into a caller-supplied canvas at any size. Framing is defined for a
// 16:9 view, so the camera keeps the films' composition at every width; `k` is
// the label scale (1 at the films' 1920 px). `view` adds the visitor's orbit.
export function stage({ canvas, W, H, plate: [pw, pd] = [17, 10.5], ao = true, dpr = 1, bg = '#eef0f3' }) {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  r.setPixelRatio(dpr); r.setSize(W, H, false); r.shadowMap.enabled = true; r.shadowMap.type = THREE.VSMShadowMap; r.outputColorSpace = THREE.SRGBColorSpace;
  r.toneMapping = THREE.NoToneMapping;
  const scene = new THREE.Scene(); scene.background = new THREE.Color(bg);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.ShadowMaterial({ opacity: .12 })); ground.rotation.x = -Math.PI / 2; ground.position.y = -.5; ground.receiveShadow = true; scene.add(ground);
  const plate = box(pw, .5, pd, .22, mat(C.clay), 0, -.25, 0); scene.add(plate);
  const world = new THREE.Group(); scene.add(world);
  scene.add(new THREE.HemisphereLight('#ffffff', '#cdd4dd', 1.9));
  const key = new THREE.DirectionalLight('#fff8ee', 1.35); key.position.set(-10, 16, 7); key.castShadow = true; key.shadow.mapSize.set(1536, 1536); key.shadow.bias = -.0002; key.shadow.normalBias = .02; key.shadow.radius = 6; key.shadow.blurSamples = 8;
  Object.assign(key.shadow.camera, { left: -13, right: 13, top: 13, bottom: -13, near: 1, far: 50 }); key.shadow.camera.updateProjectionMatrix(); scene.add(key);
  const fill = new THREE.DirectionalLight('#e8f0ff', .7); fill.position.set(9, 7, -5); scene.add(fill);
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 200);
  const EL = 33 * Math.PI / 180, AZ = 38 * Math.PI / 180, D = 60;
  const st = { r, scene, world, cam, W, H, k: W / 1920, view: { az: 0, el: 0 } };
  st.setCam = (h, tx, ty, tz) => { const asp = st.W / st.H, el = EL + st.view.el, az = AZ + st.view.az; cam.left = -h * asp / 2; cam.right = h * asp / 2; cam.top = h / 2; cam.bottom = -h / 2; cam.position.set(tx + D * Math.cos(el) * Math.sin(az), ty + D * Math.sin(el), tz + D * Math.cos(el) * Math.cos(az)); cam.lookAt(tx, ty, tz); cam.updateProjectionMatrix(); };
  st.setCam(12, 0, 0, 0);
  let composer = null, gtao = null;
  st.setAO = on => {
    if (on && !composer) { composer = new EffectComposer(r); composer.addPass(new RenderPass(scene, cam)); gtao = new GTAOPass(scene, cam, st.W, st.H); gtao.output = GTAOPass.OUTPUT.Default; gtao.blendIntensity = .75; gtao.updateGtaoMaterial({ radius: .9, distanceExponent: 1, thickness: 1, distanceFallOff: 1, scale: 1, samples: 8, screenSpaceRadius: false }); composer.addPass(gtao); composer.addPass(new OutputPass()); composer.setPixelRatio(r.getPixelRatio()); composer.setSize(st.W, st.H); }
    if (!on && composer) { composer.dispose(); gtao.dispose(); composer = gtao = null; }
    st.ao = !!composer;
  };
  st.setAO(ao);
  st.resize = (w, h) => { st.W = w; st.H = h; st.k = w / 1920; r.setSize(w, h, false); if (composer) composer.setSize(w, h); };
  st.render = () => { if (composer) composer.render(); else r.render(scene, cam); };
  st.project = v => { const p = v.clone().project(cam); return [(p.x + 1) / 2 * st.W, (1 - p.y) / 2 * st.H]; };
  // Empty the diorama between settings; the plate, lights and ground stay.
  st.clear = () => { world.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) [].concat(o.material).forEach(m => m.dispose()); }); world.clear(); };
  st.dispose = () => { st.clear(); st.setAO(false); r.dispose(); };
  return st;
}

// camera keyframes: [{ t, target:[x,y,z], h, dur }] — the move to each key starts at its t and takes dur
export function camAt(keys, T) {
  let i = 0; while (i + 1 < keys.length && keys[i + 1].t <= T) i++;
  const k = keys[i], p = keys[Math.max(0, i - 1)]; const a = i === 0 ? 1 : smooth((T - k.t) / (k.dur || 1.4));
  return { h: lerp(p.h, k.h, a), x: lerp(p.target[0], k.target[0], a), y: lerp(p.target[1], k.target[1], a), z: lerp(p.target[2], k.target[2], a) };
}

// ── Labels (DOM overlay) ──────────────────────────────────────────────────────
// Offsets are written in the films' 1920 px space and scaled by stg.k, so a
// label sits in the same place relative to the diorama at any width.
export function labels(stg, root) {
  const items = new Map();
  return {
    add(key, { anchor, cls = 'pill', html = '', dx = 0, dy = 0 }) { const el = document.createElement('div'); el.className = cls; el.innerHTML = html; el.setAttribute('aria-hidden', 'true'); root.appendChild(el); items.set(key, { el, anchor, dx, dy, cls }); return el; },
    offset(key, dx, dy) { const it = items.get(key); if (it) { it.dx = dx; it.dy = dy; } },
    set(key, { opacity, html, cls }) { const it = items.get(key); if (!it) return; if (opacity !== undefined) it.base = opacity; if (html !== undefined) it.el.innerHTML = html; if (cls !== undefined && cls !== it.cls) { it.el.className = it.cls = cls; } },
    update() { const k = stg.k, W = stg.W, H = stg.H; for (const it of items.values()) { if (!it.anchor) continue; const a = typeof it.anchor === 'function' ? it.anchor() : it.anchor; const [x, y] = stg.project(a); const px = x + it.dx * k, py = y + it.dy * k, w = it.el.offsetWidth || 0, h = it.el.offsetHeight || 0;
      const fade = clamp((py - 8) / 24) * clamp((H - 8 - py - h) / 24) * clamp((px - 8) / 24) * clamp((W - 8 - px - w) / 24);
      const op = (it.base ?? 1) * fade; it.el.style.opacity = op.toFixed(3); it.el.style.visibility = op < .01 ? 'hidden' : 'visible'; it.el.style.transform = `translate(${px.toFixed(1)}px, ${py.toFixed(1)}px)`; } },
    clear() { for (const it of items.values()) it.el.remove(); items.clear(); },
  };
}

// ── Extra props for the airport and school dioramas ───────────────────────────
export function car(color = C.sky) {
  const g = new THREE.Group();
  const body = box(1.5, .5, .9, .16, mat(color), 0, .45, 0); const hood = box(.6, .3, .8, .12, mat(color), -.65, .4, 0);
  const seat = box(.5, .3, .6, .08, mat(C.clay2), .25, .55, 0); const dash = box(.1, .25, .7, .04, mat(C.clay2), -.2, .75, 0);
  const wheels = []; [[-.55, .42], [-.55, -.42], [.5, .42], [.5, -.42]].forEach(([x, z]) => { const w = cyl(.17, .14, mat(C.navy, { roughness: .8 }), x, .17, z); w.rotation.x = Math.PI / 2; const hub = cyl(.07, .16, mat(C.clay3), x, .17, z); hub.rotation.x = Math.PI / 2; g.add(w, hub); wheels.push(w, hub); });
  const lampL = ball(.06, glow('#fff3c4', .8), -.98, .45, .28), lampR = ball(.06, glow('#fff3c4', .8), -.98, .45, -.28);
  g.add(body, hood, seat, dash, lampL, lampR);
  g.rotation.y = Math.PI / 2;   // body is built along x; the kit's "forward" is +z
  return { g, roll(a) { wheels.forEach(w => { w.rotation.y = a; }); } };
}
export function cone(x, z) { const g = group(cyl(.02, .5, mat(C.coral), 0, .25, 0, .12), box(.34, .05, .34, .02, mat(C.coral), 0, .025, 0), cyl(.085, .06, mat('#ffffff'), 0, .3, 0, .11)); g.position.set(x, 0, z); return g; }
export function stanchion(x, z) { const g = group(cyl(.03, 1.0, mat(C.clay2), 0, .5, 0), cyl(.16, .06, mat(C.clay2), 0, .03, 0), ball(.06, mat(C.clay3), 0, 1.02, 0)); g.position.set(x, 0, z); return g; }
export function rope(a, b) { const v = new THREE.Vector3(b[0] - a[0], 0, b[1] - a[1]); const len = v.length(); const m = mesh(new THREE.CapsuleGeometry(.022, len - .1, 4, 8), mat(C.coral), (a[0] + b[0]) / 2, .9, (a[1] + b[1]) / 2); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v.normalize()); m.castShadow = false; return m; }
export function fence(w = 2.4) { const g = new THREE.Group(); for (let i = 0; i <= 6; i++) g.add(box(.08, .7, .08, .03, mat(C.clay), -w / 2 + i * w / 6, .35, 0)); g.add(box(w + .1, .07, .07, .03, mat(C.clay), 0, .55, 0), box(w + .1, .07, .07, .03, mat(C.clay), 0, .22, 0)); return g; }
export function plane() { const g = new THREE.Group(); const w = mat(C.clay);
  const body = capsule(.28, 1.8, w, 0, .7, 0); body.rotation.z = Math.PI / 2;
  const wingL = box(.7, .06, 1.3, .03, mat(C.clay2), 0, .62, .75), wingR = box(.7, .06, 1.3, .03, mat(C.clay2), 0, .62, -.75);
  const tail = box(.5, .55, .06, .03, mat(C.teal), .95, 1.05, 0); const tailW = box(.4, .05, .7, .02, mat(C.clay2), .95, .8, 0);
  const nose = ball(.2, mat(C.navy), -1.25, .7, 0); const wheels = [cyl(.1, .08, mat(C.navy), -.7, .1, 0), cyl(.1, .08, mat(C.navy), .4, .1, .3), cyl(.1, .08, mat(C.navy), .4, .1, -.3)]; wheels.forEach(c => c.rotation.x = Math.PI / 2);
  const strut = cyl(.03, .35, mat(C.clay3), -.7, .3, 0);
  g.add(body, wingL, wingR, tail, tailW, nose, strut, ...wheels); return g; }
export function building({ w = 5, h = 2.2, d = 2.4, color = C.clay, win = C.sky, rows = 1, cols = 4 } = {}) {
  const g = new THREE.Group(); g.add(box(w, h, d, .1, mat(color), 0, h / 2, 0));
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) g.add(box(.5, .5, .06, .04, mat(win), -w / 2 + (c + .5) * w / cols, h - .7 - r * .9, d / 2 + .02));
  g.add(box(.8, 1.3, .06, .04, mat(C.clay3), 0, .65, d / 2 + .02));
  return g;
}
export function flagpole(x, z) { const g = group(cyl(.035, 2.6, mat(C.clay2), 0, 1.3, 0), box(.6, .36, .03, .02, mat(C.teal), .33, 2.4, 0), cyl(.14, .06, mat(C.clay2), 0, .03, 0)); g.position.set(x, 0, z); return g; }
export function bench(x, z, ry = 0) { const g = group(box(1.4, .1, .5, .04, mat(C.clay2), 0, .45, 0), box(1.4, .45, .1, .04, mat(C.clay2), 0, .72, -.22), cyl(.05, .45, mat(C.clay3), -.6, .22, .15), cyl(.05, .45, mat(C.clay3), .6, .22, .15), cyl(.05, .45, mat(C.clay3), -.6, .22, -.15), cyl(.05, .45, mat(C.clay3), .6, .22, -.15)); g.position.set(x, 0, z); g.rotation.y = ry; return g; }
export function cart(x, z) { const g = group(box(.9, .08, .6, .03, mat(C.clay2), 0, .3, 0), box(.06, .9, .6, .02, mat(C.clay2), .44, .7, 0), box(.5, .4, .4, .08, mat(C.sky), -.1, .55, 0), box(.4, .3, .35, .08, mat(C.rose), -.05, .9, 0)); [[-.3, .25], [-.3, -.25], [.3, .25], [.3, -.25]].forEach(([a, b]) => { const w = cyl(.08, .06, mat(C.navy), a, .08, b); w.rotation.x = Math.PI / 2; g.add(w); }); g.position.set(x, 0, z); return g; }
