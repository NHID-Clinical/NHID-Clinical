// school: the diorama, its path, stations and choreography. Moved out of the
// render page unchanged so the films and the interactive player share one source.
import { THREE, C, mat, glow, box, cyl, ball, capsule, group, robot, person, gate, arch, button, book, padlock, card, tray, receipt, tree, sign, path, uNear, clamp, smooth, easeOut, lerp, seg, pop, car, cone, fence, building, flagpole, bench } from '../kit.mjs';
import { WALK, beatAt as beat } from '../story.mjs';

export function build(stg) {


  const W = stg.world;

  // ── Path and stations ─────────────────────────────────────────────────────────
  const P = path([[-7.9, 3.5], [-4.6, 2.7], [-2.4, 2.0], [-2.4, .3], [.4, .1], [3.0, .9], [5.4, 1.8], [7.3, 2.5], [8.3, 3.0]]);
  W.add(P.g);
  const stops = [uNear(P, -7.4, 3.4), uNear(P, -4.6, 2.7), uNear(P, -2.4, 1.75), uNear(P, .4, .1), uNear(P, 3.0, .9), uNear(P, 5.4, 1.8)];

  // ── Set ───────────────────────────────────────────────────────────────────────
  // pickup stand: the teacher at a little podium under a sign, cones along the lane
  const stand = group(box(1.0, 1.0, .7, .1, mat(C.clay), 0, .5, 0), box(1.15, .08, .8, .03, mat(C.clay2), 0, 1.04, 0), box(.5, .06, .36, .02, mat('#ffffff'), 0, 1.1, .05));
  stand.position.set(-4.6, 0, 1.25); W.add(stand);
  const standSign = sign(1.6, .4, 2.3); standSign.position.set(-4.6, 0, .5); W.add(standSign);
  const teacher1 = person({ color: C.mint, hat: 'teacher' }); teacher1.g.position.set(-4.6, 0, .35); W.add(teacher1.g);
  [[-7.4, 2.4], [-6.4, 2.0], [-7.6, 4.5], [-6.6, 4.2], [-5.4, 3.9]].forEach(([x, z]) => W.add(cone(x, z)));
  // school gate (the kit gate) + the child waiting behind a fence with a padlock
  const G = gate(2.4); G.g.position.set(-2.4, 0, 1.05); W.add(G.g);
  const F = fence(2.6); F.position.set(-2.4, 0, -.9); W.add(F);
  const kid = person({ color: C.rose, hat: 'child' }); kid.g.position.set(-2.4, 0, -1.5); kid.g.rotation.y = Math.PI; W.add(kid.g);
  const bag = box(.3, .34, .18, .06, mat(C.sky), -2.4, .5, -1.68); W.add(bag);
  const LK = padlock(); LK.g.position.set(-2.4, .6, -.82); LK.g.scale.setScalar(1.5); W.add(LK.g);
  const yardSign = sign(1.5, .4, 2.1); yardSign.position.set(-2.4, 0, -2.75); W.add(yardSign);
  // ID check arch
  const A = arch(); A.g.position.set(.4, 0, .1); A.g.rotation.y = Math.PI / 2; W.add(A.g);
  const flag = group(cyl(.045, .5, mat(C.clay3), 0, .25, 0), box(.46, .26, .04, .04, mat(C.amber), 0, .6, 0)); flag.position.set(.4, 2.15, .1); flag.rotation.y = Math.PI / 2; flag.scale.setScalar(0); W.add(flag);
  // office phone button + staff member from the school door
  const B = button(); B.g.position.set(3.0, 0, -.3); W.add(B.g);
  const staff = person({ color: C.sky, hat: 'teacher' }); staff.g.position.set(3.6, 0, -4.0); W.add(staff.g);
  // pickup log + evidence tray
  const K = book(); K.g.position.set(5.4, 0, .55); W.add(K.g);
  const TR = tray(); TR.position.set(7.3, 0, 1.35); W.add(TR); const R = receipt(); R.position.set(5.4, 1.1, .55); R.scale.setScalar(0); W.add(R);
  // the robot drives a little car along the lane
  const rbInner = robot(); const CAR = car(C.sky); rbInner.g.scale.setScalar(.72); rbInner.g.position.set(.12, .6, 0); rbInner.g.rotation.y = -Math.PI / 2; CAR.g.add(rbInner.g);
  const mask = card({ color: C.sand }); mask.position.set(0, .12, .05); mask.scale.setScalar(0); rbInner.hand.add(mask);
  const carRig = new THREE.Group(); carRig.add(CAR.g); W.add(carRig);
  const rb = { g: carRig, hand: rbInner.hand, badgeMat: rbInner.badgeMat, _baseY: 0, _hold: 0,
    walk(phase, moving) { CAR.roll(moving ? phase * 6 : CAR._last || 0); if (moving) CAR._last = phase * 6; rbInner.walk(0, false); carRig.position.y = this._baseY; },
    hold(a) { rbInner.hold(a); }, light(a) { rbInner.light(a); } };
  // school building, flag, trees, crosswalk
  const school = building({ w: 7.5, h: 2.4, d: 2.2, win: C.sky, rows: 2, cols: 6 }); school.position.set(1.2, 0, -4.0); W.add(school);
  W.add(flagpole(-3.6, -4.2), tree(-7.4, -3.2, 1.1), tree(7.4, -3.6, 1.2), tree(6.6, -1.2, .8), bench(6.4, -2.8, -.3));
  for (let i = 0; i < 6; i++) W.add(box(.5, .02, 1.2, .01, mat('#ffffff'), 2.8 + i * .7, .01, -2.4));

  const anchors = { badge: new THREE.Vector3(), flag: new THREE.Vector3(.4, 2.9, .1), tray: new THREE.Vector3(7.3, .2, 1.9), hand: new THREE.Vector3() };

  // ── Choreography ──────────────────────────────────────────────────────────────
  function act(T, b, ru) {
    const lt = b.lt, i = b.i;
    const lit = i === 1 ? seg(lt, 2.2, 2.8) : i > 1 ? 1 : 0; rb.light(lit);
    const pulse = .55 + .45 * Math.sin(T * 7);
    G.strip.emissiveIntensity = i <= 1 && lit < 1 ? pulse : .9;
    G.ok(i === 1 ? seg(lt, 3.0, 3.6) : i > 1 ? 1 : 0); G.open(i === 1 ? seg(lt, 3.5, 4.6) : i > 1 ? 1 : 0);
    const shake = i === 2 && lt > 1.8 && lt < 3.1 ? Math.sin(lt * 40) * .18 * (1 - seg(lt, 2.6, 3.1)) : 0; LK.g.rotation.z = shake;
    const unlocked = i === 2 ? seg(lt, 3.3, 3.9) : i > 2 ? 1 : 0; LK.open(easeOut(unlocked));
    // the child hops and waves once the gate is unlocked
    const hop = i === 2 ? Math.abs(Math.sin(Math.max(0, lt - 3.9) * 6)) * (1 - seg(lt, 5.2, 6)) * unlocked : 0; kid.g.position.y = hop * .18; kid.walk(T, i === 2 && lt > 3.9 && lt < 5.2);
    const hold = i === 3 ? Math.min(seg(lt, 1.8, 2.6), 1 - seg(lt, 4.0, 4.8)) : 0; rb.hold(smooth(hold)); mask.scale.setScalar(pop(hold) * 1.4);
    const alarm = i === 3 ? Math.min(seg(lt, 2.7, 3.0), 1 - seg(lt, 4.6, 5.4)) : 0; A.alarm(alarm * (.7 + .3 * Math.sin(T * 14)));
    flag.scale.setScalar(i === 3 ? pop(seg(lt, 2.9, 3.4)) * (1 - seg(lt, 5.2, 5.8)) : 0);
    const press = i === 4 ? Math.sin(Math.PI * seg(lt, 1.8, 2.3)) : 0; B.press(press); B.lit(i === 4 ? seg(lt, 1.9, 2.2) : i > 4 ? 1 : 0);
    const nw = i === 4 ? seg(lt, 2.2, 4.6) : i > 4 ? 1 : 0; const nz = lerp(-4.0, -.95, smooth(nw)); staff.g.position.set(3.6, 0, nz); staff.walk(T, nw > 0 && nw < 1); staff.g.rotation.y = nw < 1 ? 0 : lerp(0, -1.2, smooth((lt - 4.6) / .5));
    if (i === 4 && lt > 4.6) rb.g.position.z += .5 * smooth((lt - 4.6) / .7);
    for (let k = 0; k < 5; k++) { const s0 = 1.7 + k * .55; const a = i === 5 ? seg(lt, s0, s0 + .45) : i > 5 ? 1 : 0; K.tick(k, a); if (i === 5 && lt >= s0 && lt < s0 + .45) K.stampAt((lt - s0) / .45); }
    if (i !== 5 || lt < 1.7 || lt > 4.5) K.stampAt(0);
    const rs = i === 5 ? seg(lt, 4.6, 6.0) : i > 5 ? 1 : 0; R.scale.setScalar(i >= 5 ? pop(seg(lt, 4.4, 4.8)) || (i > 5 ? 1 : 0) : 0);
    const e = smooth(rs); R.position.set(lerp(5.4, 7.3, e), lerp(1.12, .13, e) + Math.sin(e * Math.PI) * .5, lerp(.55, 1.35, e)); R.rotation.y = e * .4;
    carRig.updateMatrixWorld(true); anchors.badge.set(0, .72, .3).applyMatrix4(rbInner.g.matrixWorld);
    // payoff (beat 6): the lock goes, the child runs along the yard to the car, hops, and rides in the passenger seat
    if (i >= 6) { const l6 = i === 6 ? lt : 10; LK.g.scale.setScalar(1.5 * (1 - smooth(seg(l6, 0, .4))));
      if (l6 >= 3.3) { if (kid.g.parent !== CAR.g) CAR.g.add(kid.g); kid.g.position.set(.12, .5, .42); kid.g.rotation.y = -Math.PI / 2; kid.walk(0, false); }
      else { if (kid.g.parent !== W) W.add(kid.g);
        const WP = [[-2.4, -1.5, .3], [-.6, -1.7, 1.0], [2.0, -1.4, 1.8], [4.7, 1.0, 2.8]]; let k = 0; while (k < WP.length - 2 && l6 > WP[k + 1][2]) k++;
        const a = WP[k], b2 = WP[k + 1], p = smooth(seg(l6, a[2], b2[2])); kid.g.position.set(lerp(a[0], b2[0], p), 0, lerp(a[1], b2[1], p));
        const moving = l6 > .3 && l6 < 2.8; if (moving) kid.g.rotation.y = Math.atan2(b2[0] - a[0], b2[1] - a[1]); kid.walk(T, moving);
        kid.g.position.y = Math.abs(Math.sin(seg(l6, 2.8, 3.3) * Math.PI)) * .35; } }
    else if (kid.g.parent !== W) { W.add(kid.g); kid.g.position.set(-2.4, 0, -1.5); kid.g.rotation.y = Math.PI; }
    anchors.hand.set(carRig.position.x, 1.75, carRig.position.z);
  }

  const sc = {
    title: 'The school pickup line', center: [0, 0, -.4], wideH: 13.8,
    path: P, stops, robot: rb, act,
    intro: { line: 'A robot comes to pick up a child.', tell: 'Someone small is waiting. Here is what has to happen first.' },
    tell: [
      'Before anyone is handed over, the driver has to say “I’m a robot.” Then the gate opens.',
      'The child stays behind the gate until the driver has said who it is. Not before.',
      'A robot can’t wear a parent’s face. The check catches it.',
      'There is always a phone that brings a real teacher, and it has to work.',
      'Every pickup gets written in the log, so anyone can check later.',
    ],
    stations: [
      { anchor: new THREE.Vector3(-4.6, 2.5, 1.2), face: Math.PI, h: 6.6, dx: 90, dy: -130, end: [-40, -160], cam: [-4.2, .5, 2.0] },
      { anchor: new THREE.Vector3(-1.1, 1.3, -1.6), face: Math.PI, h: 6.4, dx: 50, dy: -110, end: [40, -190], cam: [-2.0, .6, -.3] },
      { anchor: new THREE.Vector3(.4, 2.9, .1), face: Math.PI / 2, h: 6.4, dx: 150, dy: 0, end: [120, -40], cam: [.7, .7, .3] },
      { anchor: new THREE.Vector3(3.0, 2.0, -.3), face: Math.PI, h: 6.8, dx: 70, dy: -120, end: [110, -30], cam: [3.3, .5, .0] },
      { anchor: new THREE.Vector3(5.4, 2.1, .55), face: Math.PI, h: 6.6, dx: 60, dy: -100, end: [90, 30], cam: [6.1, .5, 1.1] },
    ],
    badgeAnchor: () => anchors.badge, badgeOn: T => { const { i, lt } = beat(T); return i === 1 ? Math.min(easeOut(seg(lt, 2.5, 2.9)), 1 - seg(lt, 5.4, 5.9)) : 0; },
    flagAnchor: () => anchors.flag, flagOn: T => { const { i, lt } = beat(T); return i === 3 ? Math.min(easeOut(seg(lt, 3.1, 3.5)), 1 - seg(lt, 5.1, 5.6)) : 0; },
    payoff: { line: 'Then, and only then.', tell: 'Now the child gets picked up. Hop in.', tag: 'PICKED UP' },
    handAnchor: () => anchors.hand, handOn: T => { const { i, lt } = beat(T); return i === 6 ? easeOut(seg(lt, 3.4, 3.8)) : i === 7 ? 1 - seg(lt, 0, .8) : 0; },
    trayAnchor: () => anchors.tray, trayOn: T => { const { i, lt } = beat(T); return i === 5 ? easeOut(seg(lt, 5.2, 5.7)) : i > 5 ? 1 : 0; },
    extraTags: [
      { anchor: new THREE.Vector3(-4.6, 2.3, .5), dx: -42, dy: -14, html: 'PICKUP' },
      { anchor: new THREE.Vector3(-2.4, 2.3, -2.75), dx: -36, dy: -14, html: 'YARD' },
      { anchor: new THREE.Vector3(1.2, 2.75, -2.9), dx: -44, dy: -14, html: 'OFFICE' },
    ],
    closing: { head: 'The pickup line for AI callers.', sub: 'Five rules a robot has to follow before anyone is handed over, and a log that proves it did. Nobody leaves until all five are done.' },
  };
  return sc;
}
