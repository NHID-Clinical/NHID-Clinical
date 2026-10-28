# Interactive how-it-works diorama

Source for the interactive version of the three how-it-works films on
`about.html#how-it-works`. The films were rendered from the same scenes: every
prop, label and camera move is a function of time `T`, and here the visitor
controls `T` (step rule by rule, scrub, play), turns the view by dragging, and
clicks a station to jump to its rule. Switching setting keeps the moment.

- `src/kit.mjs`: clay materials, props, stage, label overlay.
- `src/story.mjs`: the shared five-beat timeline and in-scene labels.
- `src/scenes/*.mjs`: the clinic front desk, airport checkpoint and school pickup line.
- `src/player.mjs`: controls, accessibility, film fallback, adaptive quality.

Build (output is committed; the site is static and CI has no Node step):

    cd tools/how-it-works && npm ci && ./build.sh

The page loads `assets/js/how-it-works/player.js` only as the section
approaches and only where WebGL works. Without JavaScript, without WebGL, or
after a lost GPU context, the MP4 films are shown as before. With reduced
motion it never autoplays, and each rule jumps to its key moment instead of
animating.
