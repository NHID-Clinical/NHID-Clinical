// The interactive version of the three how-it-works films.
//
// The films were rendered from a deterministic render(T): every prop, label and
// camera move is a function of time. Here the visitor owns T. They can step
// rule by rule, scrub, or let it play, drag to turn the diorama, and click a
// station to jump to its rule. Switching setting keeps the moment, so the same
// rule can be compared across the clinic, the airport and the school.
//
// It mounts only when WebGL is available and replaces nothing permanently: the
// films stay in the page, one click away, and are what a visitor without
// JavaScript, without WebGL, or after a lost GPU context sees.
import { stage } from './kit.mjs';
import { story, BEATS, TOTAL, CONTROLS } from './story.mjs';

const SCENES = {
  'front-desk': { load: () => import('./scenes/front-desk.mjs'), name: 'the clinic front desk' },
  airport: { load: () => import('./scenes/airport.mjs'), name: 'the airport checkpoint' },
  school: { load: () => import('./scenes/school.mjs'), name: 'the school pickup line' },
};
const STEPS = [
  { beat: 0, short: 'Start', label: 'Start: the robot arrives' },
  ...CONTROLS.map((c, i) => ({ beat: i + 1, short: String(i + 1), label: `Rule ${i + 1}: ${c.pill} (${c.id})` })),
  { beat: 6, short: '✓', label: 'Then, and only then: the handover' },
];
const stepOfBeat = b => Math.min(b, 6);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

function webglOK() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}

const h = (tag, attrs = {}, ...kids) => { const el = document.createElement(tag); for (const [k, v] of Object.entries(attrs)) { if (k === 'class') el.className = v; else if (k === 'text') el.textContent = v; else el.setAttribute(k, v); } kids.forEach(k => el.append(k)); return el; };

export function mount(band) {
  if (!band || band.querySelector('.hiw') || !webglOK()) return null;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarse = matchMedia('(pointer: coarse)').matches;
  const saveData = navigator.connection && navigator.connection.saveData;

  // ── markup ────────────────────────────────────────────────────────────────
  const canvas = h('canvas', { class: 'hiw-canvas', 'aria-hidden': 'true' });
  const labelRoot = h('div', { class: 'hiw-labels' });
  const loading = h('div', { class: 'hiw-loading', text: 'Building the diorama…' });
  const reset = h('button', { type: 'button', class: 'hiw-reset', text: 'Reset view' }); reset.hidden = true;
  const hint = h('p', { class: 'hiw-hint', text: coarse ? 'Drag to turn it. Tap a station to see its rule.' : 'Drag to turn it. Click a station to see its rule.' });
  const stageEl = h('div', { class: 'hiw-stage', tabindex: '0', role: 'group', 'aria-roledescription': 'interactive diorama' }, canvas, labelRoot, loading, reset, hint);
  const play = h('button', { type: 'button', class: 'hiw-play', 'aria-label': 'Play' });
  const steps = h('ol', { class: 'hiw-steps', 'aria-label': 'Step through the rules' });
  const stepBtns = STEPS.map((s, i) => { const b = h('button', { type: 'button', class: 'hiw-step', 'aria-label': s.label, title: s.label, text: s.short }); b.dataset.step = i; steps.append(h('li', {}, b)); return b; });
  const scrub = h('input', { type: 'range', class: 'hiw-scrub', min: '0', max: String(TOTAL), step: '0.01', value: '0', 'aria-label': 'Position in the walkthrough' });
  const bar = h('div', { class: 'hiw-bar' }, play, steps, scrub);
  const capN = h('span', { class: 'hiw-n' }), capLine = h('p', { class: 'hiw-line' }), capTell = h('p', { class: 'hiw-tell' }), capId = h('p', { class: 'hiw-id' });
  const caption = h('div', { class: 'hiw-caption', 'aria-live': 'polite' }, capN, h('div', {}, capLine, capTell, capId));
  const toFilm = h('button', { type: 'button', class: 'hiw-switch', text: 'Watch it as a 44-second film instead' });
  const root = h('div', { class: 'hiw' }, stageEl, bar, caption, h('p', { class: 'hiw-alt' }, toFilm));
  const toLive = h('button', { type: 'button', class: 'hiw-switch hiw-back', text: 'Back to the interactive version' });
  const filmStage = band.querySelector('.film-stage');
  filmStage.before(root);
  filmStage.after(h('p', { class: 'hiw-alt hiw-alt-film' }, toLive));

  // ── renderer ──────────────────────────────────────────────────────────────
  const size = () => { const w = Math.max(280, Math.round(stageEl.clientWidth)); return [w, Math.round(w * 9 / 16)]; };
  let [W0, H0] = size();
  const wantAO = !coarse && !saveData && W0 >= 640;
  const stg = stage({ canvas, W: W0, H: H0, ao: wantAO, dpr: Math.min(devicePixelRatio || 1, wantAO ? 1.5 : 2) });

  const S = { T: 0, playing: false, stopAt: null, dirty: true, inView: false, raf: 0, last: 0, beat: -1, key: null, sc: null, st: null, loading: false, frames: [], drag: null, autoplayed: false };

  function setCaption(b) {
    const c = S.st.caption(b);
    capN.textContent = c.n; capN.hidden = !c.n; capLine.textContent = c.line; capTell.textContent = c.tell; capId.textContent = c.id || ''; capId.hidden = !c.id;
    const cur = stepOfBeat(b);
    stepBtns.forEach((btn, i) => { btn.classList.toggle('is-current', i === cur); btn.classList.toggle('is-done', i < cur || (b === 7 && i === 6)); if (i === cur) btn.setAttribute('aria-current', 'step'); else btn.removeAttribute('aria-current'); });
  }

  function draw() {
    if (!S.st) return;
    const b = S.st.render(S.T);
    if (b.i !== S.beat) { S.beat = b.i; setCaption(b.i); }
    scrub.value = S.T.toFixed(2); scrub.style.setProperty('--p', (S.T / TOTAL * 100).toFixed(2) + '%');
    S.dirty = false;
  }

  function tick(now) {
    S.raf = 0;
    const dt = S.last ? Math.min((now - S.last) / 1000, .1) : 0; S.last = now;
    if (S.playing) {
      // Adaptive quality: drop ambient occlusion if this machine cannot hold ~30 fps with it.
      if (stg.ao && dt) { S.frames.push(dt); if (S.frames.length === 45) { const avg = S.frames.reduce((a, v) => a + v, 0) / S.frames.length; if (avg > .034) stg.setAO(false); } }
      S.T += dt;
      if (S.stopAt !== null && S.T >= S.stopAt) { S.T = S.stopAt; pause(); }
      if (S.T >= TOTAL - .001) { S.T = TOTAL - .001; pause(); }
      S.dirty = true;
    }
    if (S.dirty) draw();
    if ((S.playing || S.dirty) && S.inView) kick();
  }
  function kick() { if (!S.raf && S.inView) S.raf = requestAnimationFrame(tick); }
  function invalidate() { S.dirty = true; kick(); }

  function setPlaying(on) {
    S.playing = on; S.last = 0;
    play.classList.toggle('is-playing', on); play.setAttribute('aria-label', on ? 'Pause' : (S.T >= TOTAL - .01 ? 'Replay' : 'Play'));
    if (on) kick();
  }
  function pause() { setPlaying(false); }
  function playAll() { if (S.T >= TOTAL - .01) S.T = 0; S.stopAt = null; setPlaying(true); }

  function goStep(i) {
    const s = STEPS[clamp(i, 0, STEPS.length - 1)], [a, b] = BEATS[s.beat];
    const end = s.beat === 6 ? TOTAL - .01 : b - .02;
    // Without motion, show the moment the rule visibly happens: the gate open,
    // the lock open, the scanner's flag up, the person arriving, the stamps down.
    if (reduce) { S.T = s.beat === 0 ? 2.5 : s.beat === 6 ? 36 : a + 4.5; S.stopAt = null; pause(); invalidate(); return; }
    S.T = a; S.stopAt = end; setPlaying(true);
  }
  const currentStep = () => stepOfBeat(Math.max(0, S.beat));

  // ── settings ──────────────────────────────────────────────────────────────
  async function load(key) {
    if (!SCENES[key] || key === S.key || S.loading) return;
    S.loading = true; S.key = key; loading.hidden = false; stageEl.classList.add('is-loading');
    try {
      const mod = await SCENES[key].load();
      if (S.st) S.st.L.clear();
      stg.clear();
      S.sc = mod.build(stg);
      S.st = story(stg, S.sc, labelRoot);
      stageEl.setAttribute('aria-label', `Interactive diorama of ${SCENES[key].name}. Use the rule buttons below to step through, or the arrow keys. Drag to turn the view.`);
      S.beat = -1; draw();
    } catch (e) { fallback(); throw e; }
    finally { S.loading = false; loading.hidden = true; stageEl.classList.remove('is-loading'); }
    if (S.key !== key) return;
  }
  const activeKey = () => { const t = band.querySelector('.film-tab[aria-selected="true"]'); return t ? (t.getAttribute('aria-controls') || '').replace(/^film-/, '') : 'front-desk'; };
  new MutationObserver(() => { const k = activeKey(); if (k !== S.key) load(k); })
    .observe(band.querySelector('.film-tabs') || band, { subtree: true, attributes: true, attributeFilter: ['aria-selected'] });

  // ── interaction ───────────────────────────────────────────────────────────
  play.addEventListener('click', () => (S.playing ? pause() : playAll()));
  steps.addEventListener('click', e => { const b = e.target.closest('.hiw-step'); if (b) goStep(+b.dataset.step); });
  scrub.addEventListener('input', () => { S.T = +scrub.value; S.stopAt = null; pause(); invalidate(); });

  function nearestStation(x, y) {
    if (!S.sc) return -1; let best = -1, bd = Math.max(36, 70 * stg.k * 1.6) ** 2;
    S.sc.stations.forEach((st, i) => { const [px, py] = stg.project(st.anchor); const d = (px - x) ** 2 + (py - y + 30 * stg.k) ** 2; if (d < bd) { bd = d; best = i; } });
    return best;
  }
  const local = e => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  const viewChanged = () => { reset.hidden = Math.abs(stg.view.az) < .01 && Math.abs(stg.view.el) < .01; invalidate(); };
  canvas.addEventListener('pointerdown', e => { const [x, y] = local(e); S.drag = { x, y, az: stg.view.az, el: stg.view.el, moved: false, id: e.pointerId }; });
  canvas.addEventListener('pointermove', e => {
    const [x, y] = local(e);
    if (S.drag && S.drag.id === e.pointerId) {
      const dx = x - S.drag.x, dy = y - S.drag.y;
      if (!S.drag.moved && dx * dx + dy * dy > 25) { S.drag.moved = true; canvas.setPointerCapture(e.pointerId); stageEl.classList.add('is-dragging'); hint.classList.add('is-gone'); }
      if (S.drag.moved) { stg.view.az = clamp(S.drag.az - dx * .006, -.75, .75); stg.view.el = clamp(S.drag.el + dy * .004, -.3, .32); viewChanged(); }
      return;
    }
    if (e.pointerType === 'mouse') stageEl.classList.toggle('is-over-station', nearestStation(x, y) >= 0);
  });
  const end = e => {
    if (!S.drag || S.drag.id !== e.pointerId) return;
    const moved = S.drag.moved; S.drag = null; stageEl.classList.remove('is-dragging');
    if (!moved && e.type === 'pointerup') { const i = nearestStation(...local(e)); if (i >= 0) { hint.classList.add('is-gone'); goStep(i + 1); } }
  };
  canvas.addEventListener('pointerup', end); canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('dblclick', () => { stg.view.az = stg.view.el = 0; viewChanged(); });
  reset.addEventListener('click', () => { stg.view.az = stg.view.el = 0; viewChanged(); stageEl.focus(); });
  stageEl.addEventListener('keydown', e => {
    if (e.target !== stageEl) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); goStep(currentStep() + 1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); goStep(currentStep() - (S.T - BEATS[STEPS[currentStep()].beat][0] > 1.5 ? 0 : 1)); }
    else if (e.key === ' ' || e.key === 'k') { e.preventDefault(); S.playing ? pause() : playAll(); }
    else if (e.key === 'Home') { e.preventDefault(); goStep(0); }
    else if (e.key === 'r') { stg.view.az = stg.view.el = 0; viewChanged(); }
  });

  // ── film fallback ─────────────────────────────────────────────────────────
  function setMode(live) {
    band.classList.toggle('hiw-on', live);
    if (live) { band.querySelectorAll('.film-video').forEach(v => v.pause()); invalidate(); }
    else pause();
  }
  function fallback() { pause(); band.classList.remove('hiw-on'); band.classList.add('hiw-failed'); }
  toFilm.addEventListener('click', () => { setMode(false); const v = band.querySelector('.film:not([hidden]) .film-video'); if (v) v.focus(); });
  toLive.addEventListener('click', () => { setMode(true); stageEl.focus(); });
  canvas.addEventListener('webglcontextlost', e => { e.preventDefault(); fallback(); });

  // ── visibility and size ───────────────────────────────────────────────────
  new IntersectionObserver(es => {
    const e = es[es.length - 1]; S.inView = e.isIntersecting;
    if (!S.inView) { if (S.raf) cancelAnimationFrame(S.raf); S.raf = 0; S.last = 0; return; }
    if (!S.autoplayed && e.intersectionRatio >= .45 && !reduce && band.classList.contains('hiw-on') && S.st) { S.autoplayed = true; S.T = 0; playAll(); }
    kick();
  }, { threshold: [0, .45] }).observe(stageEl);
  new ResizeObserver(() => { const [w, hh] = size(); if (w !== stg.W) { stg.resize(w, hh); stageEl.classList.toggle('is-compact', w < 640); invalidate(); } }).observe(stageEl);
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });

  stageEl.classList.toggle('is-compact', W0 < 640);
  setMode(true);
  load(activeKey()).then(() => { if (!S.autoplayed && S.inView && !reduce) { S.autoplayed = true; S.T = 0; playAll(); } });
  return { goStep, load, state: S, stage: stg };
}
