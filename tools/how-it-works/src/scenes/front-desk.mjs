// front-desk: the diorama, its path, stations and choreography. Moved out of the
// render page unchanged so the films and the interactive player share one source.
import { THREE, C, mat, glow, box, cyl, ball, capsule, group, robot, person, gate, arch, button, book, padlock, folder, card, tray, receipt, tree, sign, path, uNear, clamp, smooth, easeOut, lerp, seg, pop } from '../kit.mjs';
import { WALK, beatAt as beat } from '../story.mjs';

export function build(stg) {


  const W = stg.world;

  // ── Path and stations ─────────────────────────────────────────────────────────
  const P = path([[-7.9, 3.5], [-4.6, 2.7], [-2.4, 2.0], [-2.4, .3], [.4, .1], [3.0, .9], [5.4, 1.8], [7.3, 2.5], [8.3, 3.0]]);
  W.add(P.g);
  const stops = [uNear(P, -7.4, 3.4), uNear(P, -4.6, 2.7), uNear(P, -2.4, 1.75), uNear(P, .4, .1), uNear(P, 3.0, .9), uNear(P, 5.4, 1.8)];

  // ── Set ───────────────────────────────────────────────────────────────────────
  // front desk
  const desk = group(box(2.2, 1.0, .8, .12, mat(C.clay), 0, .5, 0), box(2.4, .1, 1.0, .04, mat(C.clay2), 0, 1.05, 0), box(.6, .4, .05, .04, mat(C.sky), .55, 1.35, -.1), box(.4, .06, .3, .02, mat(C.clay2), .55, 1.13, -.05), box(.5, .08, .35, .02, mat('#ffffff'), -.5, 1.14, .1), ball(.07, mat(C.coral), -.8, 1.17, -.2));
  desk.position.set(-4.6, 0, 1.25); W.add(desk);
  const deskSign = sign(1.5, .4, 2.3); deskSign.position.set(-4.6, 0, .55); W.add(deskSign);
  const receptionist = person({ color: C.mint }); receptionist.g.position.set(-4.6, 0, .35); receptionist.g.rotation.y = 0; W.add(receptionist.g);
  const chair = (x, z) => { const g = group(box(.6, .1, .6, .04, mat(C.clay2), 0, .45, 0), box(.6, .5, .1, .04, mat(C.clay2), 0, .72, -.25), cyl(.05, .45, mat(C.clay3), -.22, .22, .2), cyl(.05, .45, mat(C.clay3), .22, .22, .2), cyl(.05, .45, mat(C.clay3), -.22, .22, -.2), cyl(.05, .45, mat(C.clay3), .22, .22, -.2)); g.position.set(x, 0, z); return g; };
  W.add(chair(-6.9, .0), chair(-6.2, .0), chair(-5.5, 0)); const patient = person({ color: C.rose }); patient.g.position.set(-6.2, .4, .05); patient.g.scale.set(1, .8, 1); W.add(patient.g);
  W.add(tree(-7.6, -1.2, 1.1), tree(7.2, -3.8, 1.3), tree(-1.0, -4.3, .9));
  // water cooler + plant
  W.add(group(cyl(.22, 1.0, mat(C.clay), 0, .5, 0), cyl(.2, .5, mat(C.sky), 0, 1.2, 0, .16)).translateX(-3.3).translateZ(-.9));
  // gate + records booth
  const G = gate(2.4); G.g.position.set(-2.4, 0, 1.05); W.add(G.g);
  const booth = group(box(2.6, 1.5, .18, .08, mat(C.clay), 0, .75, -1.0), box(.18, 1.5, 2.0, .08, mat(C.clay), -1.3, .75, 0), box(.18, 1.5, 2.0, .08, mat(C.clay), 1.3, .75, 0), box(1.3, .8, .7, .08, mat(C.clay2), 0, .4, .3), box(.5, .5, .06, .04, mat(C.sky), -.9, 1.0, -.88), box(.5, .5, .06, .04, mat(C.mint), -.3, 1.0, -.88), box(.5, .5, .06, .04, mat(C.sky), .3, 1.0, -.88), box(.5, .5, .06, .04, mat(C.rose), .9, 1.0, -.88));
  booth.position.set(-2.4, 0, -1.6); W.add(booth);
  const F = folder(); F.position.set(-2.4, .8, -1.3); F.scale.setScalar(1.4); W.add(F); const LK = padlock(); LK.g.position.set(-2.4, .95, -.98); LK.g.scale.setScalar(1.5); W.add(LK.g);
  const boothSign = sign(1.5, .4, 2.1); boothSign.position.set(-2.4, 0, -2.75); W.add(boothSign);
  // scanner arch
  const A = arch(); A.g.position.set(.4, 0, .1); A.g.rotation.y = Math.PI / 2; W.add(A.g);
  const flag = group(cyl(.045, .5, mat(C.clay3), 0, .25, 0), box(.46, .26, .04, .04, mat(C.amber), 0, .6, 0)); flag.position.set(.4, 2.15, .1); flag.rotation.y = Math.PI / 2; flag.scale.setScalar(0); W.add(flag);
  // nurse-call button + nurse
  const B = button(); B.g.position.set(3.0, 0, -.3); W.add(B.g);
  const nurse = person({ color: C.sky, hat: 'nurse' }); nurse.g.position.set(3.6, 0, -4.0); W.add(nurse.g);
  const nurseDoor = group(box(1.6, 2.3, .2, .08, mat(C.clay), 0, 1.15, 0), box(.7, 1.9, .06, .05, mat(C.clay2), -.35, .95, .12), box(.7, 1.9, .06, .05, mat(C.clay2), .35, .95, .12), box(.16, .16, .05, .04, mat(C.teal), 0, 1.7, .15)); nurseDoor.position.set(3.6, 0, -4.4); W.add(nurseDoor);
  // sign-in book + evidence tray
  const K = book(); K.g.position.set(5.4, 0, .55); W.add(K.g);
  const TR = tray(); TR.position.set(7.3, 0, 1.35); W.add(TR); const R = receipt(); R.position.set(5.4, 1.1, .55); R.scale.setScalar(0); W.add(R);
  // robot + mask
  const rb = robot(); W.add(rb.g); const mask = card({ color: C.sand }); mask.position.set(0, .12, .05); mask.scale.setScalar(0); rb.hand.add(mask);
  // a little clay bench and a frame on the back wall of the clinic
  const wall = box(11.4, 1.5, .25, .1, mat(C.clay), -1.2, .75, -4.9); W.add(wall);
  W.add(box(1.0, .6, .06, .04, mat(C.sky), -4.5, .85, -4.72), box(1.0, .6, .06, .04, mat(C.mint), -2.9, .85, -4.72), box(.34, .34, .06, .04, mat(C.teal), .2, .9, -4.72));

  const anchors = { badge: new THREE.Vector3(), flag: new THREE.Vector3(.4, 2.9, .1), tray: new THREE.Vector3(7.3, .2, 1.9), hand: new THREE.Vector3() };

  // ── Choreography ──────────────────────────────────────────────────────────────
  let lastShake = 0;
  function act(T, b, ru) {
    const lt = b.lt, i = b.i;
    // badge / gate (beat 1); badge stays lit afterwards
    const lit = i === 1 ? seg(lt, 2.2, 2.8) : i > 1 ? 1 : 0; rb.light(lit);
    const pulse = .55 + .45 * Math.sin(T * 7);
    G.strip.emissiveIntensity = i <= 1 && lit < 1 ? pulse : .9;
    G.ok(i === 1 ? seg(lt, 3.0, 3.6) : i > 1 ? 1 : 0); G.open(i === 1 ? seg(lt, 3.5, 4.6) : i > 1 ? 1 : 0);
    // padlock / folder (beat 2)
    const shake = i === 2 && lt > 1.8 && lt < 3.1 ? Math.sin(lt * 40) * .18 * (1 - seg(lt, 2.6, 3.1)) : 0; LK.g.rotation.z = shake;
    const unlocked = i === 2 ? seg(lt, 3.3, 3.9) : i > 2 ? 1 : 0; LK.open(easeOut(unlocked));
    F.position.y = .8 + .25 * smooth(unlocked); F.rotation.x = -.3 * smooth(unlocked);
    // mask / arch (beat 3)
    const hold = i === 3 ? Math.min(seg(lt, 1.8, 2.6), 1 - seg(lt, 4.0, 4.8)) : 0; rb.hold(smooth(hold)); mask.scale.setScalar(pop(hold));
    const alarm = i === 3 ? Math.min(seg(lt, 2.7, 3.0), 1 - seg(lt, 4.6, 5.4)) : 0; A.alarm(alarm * (.7 + .3 * Math.sin(T * 14)));
    flag.scale.setScalar(i === 3 ? pop(seg(lt, 2.9, 3.4)) * (1 - seg(lt, 5.2, 5.8)) : 0);
    // button / nurse (beat 4)
    const press = i === 4 ? Math.sin(Math.PI * seg(lt, 1.8, 2.3)) : 0; B.press(press); B.lit(i === 4 ? seg(lt, 1.9, 2.2) : i > 4 ? 1 : 0);
    const nw = i === 4 ? seg(lt, 2.2, 4.6) : i > 4 ? 1 : 0; const nz = lerp(-4.0, -.95, smooth(nw)); nurse.g.position.set(3.6, 0, nz); nurse.walk(T, nw > 0 && nw < 1); nurse.g.rotation.y = nw < 1 ? 0 : lerp(0, -1.2, smooth((lt - 4.6) / .5));
    if (i === 4 && lt > 4.6) rb.g.position.z += .5 * smooth((lt - 4.6) / .7); else if (i > 4) { /* walked on */ }
    // stamps / receipt (beat 5)
    for (let k = 0; k < 5; k++) { const s0 = 1.7 + k * .55; const a = i === 5 ? seg(lt, s0, s0 + .45) : i > 5 ? 1 : 0; K.tick(k, a); if (i === 5 && lt >= s0 && lt < s0 + .45) K.stampAt((lt - s0) / .45); }
    if (i !== 5 || lt < 1.7 || lt > 4.5) K.stampAt(0);
    const rs = i === 5 ? seg(lt, 4.6, 6.0) : i > 5 ? 1 : 0; R.scale.setScalar(i >= 5 ? pop(seg(lt, 4.4, 4.8)) || (i > 5 ? 1 : 0) : 0);
    const e = smooth(rs); R.position.set(lerp(5.4, 7.3, e), lerp(1.12, .13, e) + Math.sin(e * Math.PI) * .5, lerp(.55, 1.35, e)); R.rotation.y = e * .4;
    // badge label anchor follows the robot's chest
    rb.g.updateMatrixWorld(); anchors.badge.set(0, .72, .3).applyMatrix4(rb.g.matrixWorld);
    // payoff (beat 6): the lock goes away, the folder glides to the robot's hands, then rides with it
    if (i >= 6) { const l6 = i === 6 ? lt : 10; LK.g.scale.setScalar(1.5 * (1 - smooth(seg(l6, 0, .4)))); const g = smooth(seg(l6, .4, 2.2));
      const chest = new THREE.Vector3(0, .95, .5).applyMatrix4(rb.g.matrixWorld);
      F.position.set(lerp(-2.4, chest.x, g), lerp(1.05, chest.y, g) + Math.sin(g * Math.PI) * .9, lerp(-1.3, chest.z, g)); F.rotation.set(-.3 + .1 * g, rb.g.rotation.y * g, 0); rb.hold(g); }
    anchors.hand.set(F.position.x, F.position.y + .3, F.position.z);
  }

  const sc = {
    title: 'The clinic front desk', center: [0, 0, -.4], wideH: 13.8,
    path: P, stops, robot: rb, act,
    intro: { line: 'A robot calls the clinic.', tell: 'It wants to talk about a patient. Here is what has to happen first.' },
    tell: [
      'Before it can ask for anything, the robot has to say “I’m a robot.” Then the gate opens.',
      'The patient’s folder stays locked until the robot has said who it is. Not before.',
      'A robot can’t wear a doctor’s face. The scanner catches it.',
      'There is always a button that brings a real person, and it has to work.',
      'Every step gets stamped in the sign-in book, so anyone can check later.',
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
    payoff: { line: 'Then, and only then.', tell: 'Now the folder can be handed over, and the robot goes on its way.', tag: 'HANDED OVER' },
    handAnchor: () => anchors.hand, handOn: T => { const { i, lt } = beat(T); return i === 6 ? easeOut(seg(lt, 2.3, 2.7)) : i === 7 ? 1 - seg(lt, 0, .8) : 0; },
    trayAnchor: () => anchors.tray, trayOn: T => { const { i, lt } = beat(T); return i === 5 ? easeOut(seg(lt, 5.2, 5.7)) : i > 5 ? 1 : 0; },
    extraTags: [
      { anchor: new THREE.Vector3(-4.6, 2.3, .55), dx: -60, dy: -14, html: 'FRONT DESK' },
      { anchor: new THREE.Vector3(-2.4, 2.3, -2.75), dx: -56, dy: -14, html: 'RECORDS' },
      { anchor: new THREE.Vector3(3.6, 2.4, -4.4), dx: -40, dy: -14, html: 'STAFF' },
    ],
    closing: { head: 'The front desk for AI callers.', sub: 'Five rules a robot has to follow before it can talk about a patient, and a record that proves it did.' },
  };
  return sc;
}
