// Shared five-beat timeline, the same one the films were rendered from. A scene
// supplies its diorama, its path, where the robot stops, what each station is
// called in that analogy, and an act(T) that moves its props. The story owns
// the in-scene labels and the camera. Captions live in the page, not the canvas,
// so they stay readable text at every width; the player writes them from
// `caption(i)` when the beat changes.
import { C, clamp, smooth, easeOut, lerp, camAt, labels } from './kit.mjs';

export const BEATS = [[0, 3], [3, 9], [9, 15], [15, 21], [21, 27], [27, 33], [33, 39], [39, 44]];   // 6 = handover, 7 = wide view
export const TOTAL = 44;
export const LEAVE = 3.5;  // seconds into the handover beat when the robot moves on
export const WALK = 1.6;   // seconds the robot takes to reach each station at the start of its beat
export const CONTROLS = [
  { line: 'Say who you are.', pill: 'Say who you are', id: 'IDG-01', name: 'Identity Disclosure Gate' },
  { line: 'Nothing moves until you do.', pill: 'Nothing moves until you do', id: 'PDX-01', name: 'Pre-Data Exchange Gate' },
  { line: 'No pretending.', pill: 'No pretending', id: 'DBC-01', name: 'Deceptive Behavior Check' },
  { line: 'Ask for a person.', pill: 'Ask for a person', id: 'EIT-01', name: 'Escalation Implementation Test' },
  { line: 'Write it down.', pill: 'Write it down', id: 'ATR-01', name: 'Audit Trail' },
];

export function beatAt(T) { for (let i = 0; i < BEATS.length; i++) if (T < BEATS[i][1]) return { i, lt: T - BEATS[i][0], len: BEATS[i][1] - BEATS[i][0] }; return { i: 7, lt: T - 39, len: 5 }; }

export function story(stg, sc, root) {
  const L = labels(stg, root);
  CONTROLS.forEach((c, i) => L.add('p' + i, { anchor: sc.stations[i].anchor, dx: sc.stations[i].dx ?? 40, dy: sc.stations[i].dy ?? -140, cls: 'hiw-pill', html: `<b>${i + 1}</b><span><em>${c.pill}</em><small>${c.id}</small></span>` }));
  L.add('badge', { anchor: () => sc.badgeAnchor(), dx: 30, dy: -34, cls: 'hiw-tag', html: 'I’m a robot' });
  L.add('flag', { anchor: () => sc.flagAnchor(), dx: -200, dy: -60, cls: 'hiw-tag is-warn', html: 'Not a person' });
  L.add('tray', { anchor: () => sc.trayAnchor(), dx: 0, dy: 24, cls: 'hiw-tag is-soft', html: 'Evidence' });
  L.add('hand', { anchor: () => sc.handAnchor(), dx: -40, dy: -60, cls: 'hiw-tag', html: sc.payoff.tag.toLowerCase().replace(/^./, m => m.toUpperCase()) });
  (sc.extraTags || []).forEach((t, i) => L.add('x' + i, { anchor: t.anchor, dx: t.dx, dy: t.dy, cls: 'hiw-tag is-soft', html: t.html.toLowerCase().replace(/^./, m => m.toUpperCase()) }));

  const center = sc.center || [0, 0, 0];
  const keys = [{ t: 0, target: center, h: sc.wideH || 12.5 }];
  sc.stations.forEach((s, i) => keys.push({ t: BEATS[i + 1][0], target: s.cam || [s.anchor.x, .6, s.anchor.z], h: s.h || 7, dur: 1.5 }));
  keys.push({ t: 33, target: sc.payoff.cam || [1.6, .6, .4], h: sc.payoff.h || 8.5, dur: 1.8 });
  keys.push({ t: 39, target: center, h: (sc.wideH || 12.5) + .8, dur: 2.2 });

  function robotU(T) {
    const { i, lt } = beatAt(T); if (i === 0) return { u: sc.stops[0], moving: false };
    if (i === 6) return { u: lerp(sc.stops[5], 1, smooth((lt - LEAVE) / 2.5)), moving: lt > LEAVE && lt < LEAVE + 2.5 };
    if (i === 7) return { u: 1, moving: false };
    const from = sc.stops[i - 1], to = sc.stops[i]; const a = smooth(lt / WALK); return { u: lerp(from, to, a), moving: lt < WALK };
  }

  // What the caption under the stage says during beat i.
  function caption(i) {
    if (i === 0) return { n: '', line: sc.intro.line, tell: sc.intro.tell };
    if (i <= 5) { const c = CONTROLS[i - 1]; return { n: String(i), line: c.line, tell: sc.tell[i - 1], id: `${c.id} · ${c.name}` }; }
    if (i === 6) return { n: '✓', line: sc.payoff.line, tell: sc.payoff.tell };
    return { n: '', line: sc.closing.head, tell: sc.closing.sub };
  }

  function render(T) {
    const b = beatAt(T);
    const c = camAt(keys, T); stg.setCam(c.h, c.x, c.y, c.z);
    const ru = robotU(T); const p = sc.path.at(ru.u), tg = sc.path.tan(ru.u);
    const rb = sc.robot; rb.g.position.set(p.x, 0, p.z); rb._baseY = 0;
    const yawPath = Math.atan2(tg.x, tg.z);
    let yaw = yawPath; if (!ru.moving && b.i >= 1 && b.i <= 5) { const f = sc.stations[b.i - 1].face; if (f !== undefined) yaw = lerp(yawPath, f, smooth((b.lt - WALK) / .5)); }
    if (b.i === 6) yaw = lerp(sc.stations[4].face ?? yawPath, yawPath, smooth((b.lt - LEAVE) / .5));
    rb.g.rotation.y = yaw; rb.walk(T, ru.moving);
    sc.path.flow(T);
    sc.act(T, b, ru);
    // pills: hidden, then active in their beat, then done
    CONTROLS.forEach((_, i) => { const bi = i + 1; let op = 0, cls = 'hiw-pill';
      if (b.i === bi) { op = easeOut((b.lt - WALK + .4) / .5); cls = 'hiw-pill is-on'; }
      else if (b.i > bi) { op = .82; cls = 'hiw-pill is-done'; }
      if (b.i >= 6) { op = 1; cls = 'hiw-pill is-done'; }
      const st = sc.stations[i], ep = smooth((T - 39) / 2.2); if (st.end) L.offset('p' + i, lerp(st.dx ?? 40, st.end[0], ep), lerp(st.dy ?? -140, st.end[1], ep));
      L.set('p' + i, { opacity: op, cls }); });
    L.set('badge', { opacity: sc.badgeOn(T) });
    L.set('flag', { opacity: sc.flagOn(T) });
    L.set('tray', { opacity: sc.trayOn(T) });
    L.set('hand', { opacity: sc.handOn(T) });
    (sc.extraTags || []).forEach((t, i) => L.set('x' + i, { opacity: (t.on ? t.on(T) : 1) * (1 - smooth((T - 39.2) / 1.2)) }));
    L.update();
    stg.render();
    return b;
  }
  return { render, caption, L };
}
