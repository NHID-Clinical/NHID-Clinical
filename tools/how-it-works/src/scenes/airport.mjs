// airport: the diorama, its path, stations and choreography. Moved out of the
// render page unchanged so the films and the interactive player share one source.
import { THREE, C, mat, glow, box, cyl, ball, capsule, group, robot, person, gate, arch, button, book, padlock, suitcase, card, tray, receipt, tree, sign, path, uNear, clamp, smooth, easeOut, lerp, seg, pop, stanchion, rope, plane, cart, bench } from '../kit.mjs';
import { WALK, beatAt as beat } from '../story.mjs';

export function build(stg) {


  const W = stg.world;

  // ── Path and stations (same layout as the clinic so the three films rhyme) ───
  const P = path([[-7.9, 3.5], [-4.6, 2.7], [-2.4, 2.0], [-2.4, .3], [.4, .1], [3.0, .9], [5.4, 1.8], [7.3, 2.5], [8.3, 3.0]]);
  W.add(P.g);
  const stops = [uNear(P, -7.4, 3.4), uNear(P, -4.6, 2.7), uNear(P, -2.4, 1.75), uNear(P, .4, .1), uNear(P, 3.0, .9), uNear(P, 5.4, 1.8)];

  // ── Set ───────────────────────────────────────────────────────────────────────
  // passport booth: tall counter with a window and an officer inside
  const boothP = group(box(2.2, 1.1, .9, .12, mat(C.clay), 0, .55, 0), box(2.4, .1, 1.1, .04, mat(C.clay2), 0, 1.15, 0), box(2.2, 1.0, .08, .04, mat(C.sky, { transparent: true, opacity: .55 }), 0, 1.7, -.3), box(.1, 1.2, .1, .03, mat(C.clay), -1.1, 1.75, -.3), box(.1, 1.2, .1, .03, mat(C.clay), 1.1, 1.75, -.3), box(2.4, .12, .5, .04, mat(C.clay), 0, 2.4, -.3), box(.5, .3, .05, .04, mat(C.clay2), .55, 1.42, -.1));
  boothP.position.set(-4.6, 0, 1.25); W.add(boothP);
  const boothSign = sign(1.8, .4, 3.0); boothSign.position.set(-4.6, 0, .4); W.add(boothSign);
  const officer1 = person({ color: C.sky, hat: 'officer' }); officer1.g.position.set(-4.6, 0, .35); W.add(officer1.g);
  // queue stanchions with rope leading up to the booth
  W.add(stanchion(-7.2, 1.6), stanchion(-5.9, 1.6), stanchion(-7.2, 4.4), stanchion(-5.9, 4.4), rope([-7.2, 1.6], [-5.9, 1.6]), rope([-7.2, 4.4], [-5.9, 4.4]));
  W.add(cart(-6.6, .0), bench(-7.0, -2.2, .2));
  // barrier (gate) + baggage belt with the locked suitcase
  const G = gate(2.4); G.g.position.set(-2.4, 0, 1.05); W.add(G.g);
  const belt = group(box(3.0, .55, 1.0, .1, mat(C.clay), 0, .28, 0), box(2.9, .06, .8, .02, mat(C.navy, { roughness: .95 }), 0, .58, 0), box(.5, .9, 1.1, .08, mat(C.clay2), 1.5, .45, 0), box(.5, .9, 1.1, .08, mat(C.clay2), -1.5, .45, 0), box(1.0, 1.1, .05, .03, mat(C.clay3), -.4, 1.1, .0));
  belt.position.set(-2.4, 0, -1.4); belt.rotation.y = Math.PI / 2; W.add(belt);
  const SC = suitcase(); SC.position.set(-2.4, .6, -1.0); W.add(SC); const LK = padlock(); LK.g.position.set(-2.4, .85, -.8); LK.g.scale.setScalar(1.5); W.add(LK.g);
  const beltSign = sign(1.5, .4, 2.1); beltSign.position.set(-2.4, 0, -2.9); W.add(beltSign);
  // body scanner arch
  const A = arch(); A.g.position.set(.4, 0, .1); A.g.rotation.y = Math.PI / 2; W.add(A.g);
  const flag = group(cyl(.045, .5, mat(C.clay3), 0, .25, 0), box(.46, .26, .04, .04, mat(C.amber), 0, .6, 0)); flag.position.set(.4, 2.15, .1); flag.rotation.y = Math.PI / 2; flag.scale.setScalar(0); W.add(flag);
  W.add(group(box(.8, .5, .8, .06, mat(C.clay2), 0, .25, 0), box(.7, .1, .7, .03, mat(C.clay3), 0, .55, 0)).translateX(.4).translateZ(-1.6)); // tray table by the scanner
  // "ask an officer" button + officer from the security door
  const B = button(); B.g.position.set(3.0, 0, -.3); W.add(B.g);
  const officer = person({ color: C.navy, hat: 'officer' }); officer.g.position.set(3.6, 0, -4.0); W.add(officer.g);
  const secDoor = group(box(1.6, 2.3, .2, .08, mat(C.clay), 0, 1.15, 0), box(.7, 1.9, .06, .05, mat(C.clay2), -.35, .95, .12), box(.7, 1.9, .06, .05, mat(C.clay2), .35, .95, .12), box(.16, .16, .05, .04, mat(C.teal), 0, 1.7, .15)); secDoor.position.set(3.6, 0, -4.4); W.add(secDoor);
  // passport stamp desk + evidence tray
  const K = book(); K.g.position.set(5.4, 0, .55); W.add(K.g);
  const TR = tray(); TR.position.set(7.3, 0, 1.35); W.add(TR); const R = receipt(); R.position.set(5.4, 1.1, .55); R.scale.setScalar(0); W.add(R);
  // robot + mask
  const rb = robot(); W.add(rb.g); const mask = card({ color: C.sand }); mask.position.set(0, .12, .05); mask.scale.setScalar(0); rb.hand.add(mask);
  // terminal wall with big windows, a departures board, and a parked plane behind
  const wall = box(11.4, 1.5, .25, .1, mat(C.clay), -1.2, .75, -4.9); W.add(wall);
  for (let i = 0; i < 5; i++) W.add(box(1.3, .9, .06, .04, mat(C.sky), -5.8 + i * 1.6, .85, -4.72));
  const boardD = group(box(2.2, .9, .1, .05, mat(C.navy), 0, 2.2, 0), cyl(.05, 1.8, mat(C.clay2), -.8, .9, 0), cyl(.05, 1.8, mat(C.clay2), .8, .9, 0)); for (let i = 0; i < 4; i++) boardD.add(box(1.6, .08, .02, .01, glow(i === 1 ? C.amber : C.teal, .6), 0, 2.5 - i * .2, .06)); boardD.position.set(1.2, 0, -4.2); W.add(boardD);
  const PL = plane(); PL.position.set(6.6, 0, -3.4); PL.rotation.y = -.5; PL.scale.setScalar(1.15); W.add(PL);
  W.add(tree(7.6, -1.0, .9), tree(-7.6, -4.0, 1.0));

  const anchors = { badge: new THREE.Vector3(), flag: new THREE.Vector3(.4, 2.9, .1), tray: new THREE.Vector3(7.3, .2, 1.9), hand: new THREE.Vector3() };

  // ── Choreography (identical beats to the clinic; only the props differ) ──────
  function act(T, b, ru) {
    const lt = b.lt, i = b.i;
    const lit = i === 1 ? seg(lt, 2.2, 2.8) : i > 1 ? 1 : 0; rb.light(lit);
    const pulse = .55 + .45 * Math.sin(T * 7);
    G.strip.emissiveIntensity = i <= 1 && lit < 1 ? pulse : .9;
    G.ok(i === 1 ? seg(lt, 3.0, 3.6) : i > 1 ? 1 : 0); G.open(i === 1 ? seg(lt, 3.5, 4.6) : i > 1 ? 1 : 0);
    const shake = i === 2 && lt > 1.8 && lt < 3.1 ? Math.sin(lt * 40) * .18 * (1 - seg(lt, 2.6, 3.1)) : 0; LK.g.rotation.z = shake;
    const unlocked = i === 2 ? seg(lt, 3.3, 3.9) : i > 2 ? 1 : 0; LK.open(easeOut(unlocked));
    SC.position.y = .6 + .25 * smooth(unlocked); SC.rotation.z = .15 * smooth(unlocked);
    const hold = i === 3 ? Math.min(seg(lt, 1.8, 2.6), 1 - seg(lt, 4.0, 4.8)) : 0; rb.hold(smooth(hold)); mask.scale.setScalar(pop(hold));
    const alarm = i === 3 ? Math.min(seg(lt, 2.7, 3.0), 1 - seg(lt, 4.6, 5.4)) : 0; A.alarm(alarm * (.7 + .3 * Math.sin(T * 14)));
    flag.scale.setScalar(i === 3 ? pop(seg(lt, 2.9, 3.4)) * (1 - seg(lt, 5.2, 5.8)) : 0);
    const press = i === 4 ? Math.sin(Math.PI * seg(lt, 1.8, 2.3)) : 0; B.press(press); B.lit(i === 4 ? seg(lt, 1.9, 2.2) : i > 4 ? 1 : 0);
    const nw = i === 4 ? seg(lt, 2.2, 4.6) : i > 4 ? 1 : 0; const nz = lerp(-4.0, -.95, smooth(nw)); officer.g.position.set(3.6, 0, nz); officer.walk(T, nw > 0 && nw < 1); officer.g.rotation.y = nw < 1 ? 0 : lerp(0, -1.2, smooth((lt - 4.6) / .5));
    if (i === 4 && lt > 4.6) rb.g.position.z += .5 * smooth((lt - 4.6) / .7);
    for (let k = 0; k < 5; k++) { const s0 = 1.7 + k * .55; const a = i === 5 ? seg(lt, s0, s0 + .45) : i > 5 ? 1 : 0; K.tick(k, a); if (i === 5 && lt >= s0 && lt < s0 + .45) K.stampAt((lt - s0) / .45); }
    if (i !== 5 || lt < 1.7 || lt > 4.5) K.stampAt(0);
    const rs = i === 5 ? seg(lt, 4.6, 6.0) : i > 5 ? 1 : 0; R.scale.setScalar(i >= 5 ? pop(seg(lt, 4.4, 4.8)) || (i > 5 ? 1 : 0) : 0);
    const e = smooth(rs); R.position.set(lerp(5.4, 7.3, e), lerp(1.12, .13, e) + Math.sin(e * Math.PI) * .5, lerp(.55, 1.35, e)); R.rotation.y = e * .4;
    rb.g.updateMatrixWorld(); anchors.badge.set(0, .72, .3).applyMatrix4(rb.g.matrixWorld);
    if (i >= 6) { const l6 = i === 6 ? lt : 10; LK.g.scale.setScalar(1.5 * (1 - smooth(seg(l6, 0, .4)))); const g = smooth(seg(l6, .4, 2.2));
      const chest = new THREE.Vector3(0, .55, .55).applyMatrix4(rb.g.matrixWorld);
      SC.position.set(lerp(-2.4, chest.x, g), lerp(.85, chest.y, g) + Math.sin(g * Math.PI) * .9, lerp(-1.0, chest.z, g)); SC.rotation.set(0, rb.g.rotation.y * g, .15 * (1 - g)); rb.hold(g); }
    anchors.hand.set(SC.position.x, SC.position.y + .7, SC.position.z);
  }

  const sc = {
    title: 'The airport checkpoint', center: [0, 0, -.4], wideH: 13.8,
    path: P, stops, robot: rb, act,
    intro: { line: 'A robot arrives at the airport.', tell: 'It wants to carry something through. Here is what has to happen first.' },
    tell: [
      'Before it can go anywhere, the robot has to say “I’m a robot.” Then the barrier opens.',
      'The suitcase stays locked until the robot has said who it is. Not before.',
      'A robot can’t wear a person’s face. The scanner catches it.',
      'There is always a button that brings a real officer, and it has to work.',
      'Every step gets stamped in the passport, so anyone can check later.',
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
    payoff: { line: 'Then, and only then.', tell: 'Now the suitcase comes through, and the robot goes on its way.', tag: 'CLEARED' },
    handAnchor: () => anchors.hand, handOn: T => { const { i, lt } = beat(T); return i === 6 ? easeOut(seg(lt, 2.3, 2.7)) : i === 7 ? 1 - seg(lt, 0, .8) : 0; },
    trayAnchor: () => anchors.tray, trayOn: T => { const { i, lt } = beat(T); return i === 5 ? easeOut(seg(lt, 5.2, 5.7)) : i > 5 ? 1 : 0; },
    extraTags: [
      { anchor: new THREE.Vector3(-4.6, 3.0, .4), dx: -74, dy: -14, html: 'PASSPORT CONTROL' },
      { anchor: new THREE.Vector3(-2.4, 2.3, -2.9), dx: -56, dy: -14, html: 'BAGGAGE' },
      { anchor: new THREE.Vector3(3.6, 2.4, -4.4), dx: -52, dy: -14, html: 'SECURITY' },
    ],
    closing: { head: 'The checkpoint for AI callers.', sub: 'Five rules a robot has to follow before it can carry anything through, and a stamp that proves it did.' },
  };
  return sc;
}
