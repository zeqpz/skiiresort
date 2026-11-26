// High Peaks: the ICE BONG (owner, 2026-11-23: "make the gas pump that makes the entire row multipliers just be an ice
// bong that drops down and has the multiplier on it - animated as if it's being ripped, where the bowl burns and smoke
// moves through the ice bong - facing directly forward").
//
// It takes the place of the Snow Cannon and its dial. One drawing, in SVG, in the game's flat cartoon hand - a bong
// carved from ice, seen square from the front: a round flask of icy water, a straight tube with an ice pinch and ice
// cubes stacked in it, a fat rim under a cap of snow, icicles, and its bowl out front on a short stem - used twice:
//
//   * the symbol's picture: tools/highpeaks/icebong.py photographs IceBong.svg({ still: true }) into
//     art/highpeaks/symbols_static/GP.png, and symrig.py rigs and animates that like every other symbol;
//   * the show when it fires (index.html pumpShow): a big one drops into its column, and is RIPPED - the bowl's cherry
//     burns hot and flickers, the water bubbles, and smoke climbs from the flask up through the tube (IceBong's own
//     CSS, on .rip); when the roll is in (.landed) the smoke leaves the mouthpiece in puffs and the multiplier slams
//     onto the flask, where it stays until the column has taken it.
//
//   IceBong.svg({ still })   -> the markup (a fresh id set each call: several can show at once)
//   IceBong.css              -> its stylesheet, added to the page once by the first svg() call
(function () {
  "use strict";
  const INK = "#0C0C12";
  let seq = 0, styled = false;

  const css = `
    .icebong svg { width: 100%; height: 100%; overflow: visible; display: block; }
    .icebong .ib-ember, .icebong .ib-core, .icebong .ib-flame, .icebong .ib-glow { transform-box: fill-box; transform-origin: 50% 60%; }
    .icebong .ib-glow { opacity: .14; }
    .icebong .ib-flame { opacity: 0; transform-origin: 50% 100%; }
    .icebong .ib-rise { transform: translateY(420px); }
    .icebong .ib-bub { opacity: 0; }
    .icebong .ib-out { opacity: 0; transform-box: fill-box; transform-origin: 50% 100%; }
    .icebong .ib-mult { opacity: 0; transform-box: fill-box; transform-origin: 50% 50%; }
    .icebong .ib-puff { transform-box: fill-box; transform-origin: 50% 50%; animation: ibSwirl 1.6s ease-in-out infinite alternate; }
    .icebong .ib-puff:nth-child(2n) { animation-duration: 2.1s; animation-direction: alternate-reverse; }
    .icebong .ib-puff:nth-child(3n) { animation-duration: 1.3s; }
    @keyframes ibSwirl { from { transform: translate(-7px, 5px) scale(.9); } to { transform: translate(7px, -6px) scale(1.12); } }
    /* being ripped: the cherry burns, the water bubbles, the smoke climbs the ice */
    .icebong.rip .ib-ember { animation: ibBurn .16s ease-in-out infinite alternate; }
    .icebong.rip .ib-core { animation: ibBurn .11s ease-in-out infinite alternate-reverse; }
    .icebong.rip .ib-glow { animation: ibGlow .22s ease-in-out infinite alternate; }
    .icebong.rip .ib-flame { animation: ibFlame .19s ease-in-out infinite alternate; }
    .icebong.rip .ib-rise { transform: translateY(0); transition: transform calc(1.35s * var(--tempo, 1)) cubic-bezier(.45, .05, .35, 1) calc(.1s * var(--tempo, 1)); }
    .icebong.rip .ib-bub { animation: ibBub .55s linear infinite; animation-delay: var(--d, 0s); }
    @keyframes ibBurn { from { transform: scale(.9); filter: brightness(1); } to { transform: scale(1.14); filter: brightness(1.35); } }
    @keyframes ibGlow { from { opacity: .45; transform: scale(.95); } to { opacity: .85; transform: scale(1.3); } }
    @keyframes ibFlame { from { opacity: .75; transform: scale(.85, .8) skewX(-6deg); } to { opacity: 1; transform: scale(1.1, 1.25) skewX(7deg); } }
    @keyframes ibBub { 0% { opacity: 0; transform: translateY(0); } 15% { opacity: .95; } 100% { opacity: 0; transform: translateY(-58px); } }
    /* the roll is in: the hit is let go out of the mouthpiece, and the multiplier slams onto the flask */
    .icebong.landed .ib-ember, .icebong.landed .ib-core { animation: ibBurn .9s ease-in-out infinite alternate; }
    .icebong.landed .ib-flame { animation: none; opacity: 0; }
    .icebong.landed .ib-glow { animation: none; opacity: .4; }
    .icebong.landed .ib-rise { transform: translateY(-390px); transition: transform calc(.9s * var(--tempo, 1)) cubic-bezier(.4, 0, .7, .5); }
    .icebong.landed .ib-bub { animation: none; opacity: 0; }
    .icebong.landed .ib-out { animation: ibOut calc(1.25s * var(--tempo, 1)) cubic-bezier(.2, .7, .3, 1) both; animation-delay: var(--d, 0s); }
    .icebong.landed .ib-mult { animation: ibSlam calc(.34s * var(--tempo, 1)) cubic-bezier(.5, 0, .8, .4) both; }
    @keyframes ibOut { 0% { opacity: 0; transform: translate(0, 10px) scale(.3); } 22% { opacity: .95; }
      100% { opacity: 0; transform: translate(var(--dx, 0px), -120px) scale(1.9); } }
    @keyframes ibSlam { 0% { opacity: 0; transform: scale(3) rotate(-10deg); } 60% { opacity: 1; transform: scale(.84) rotate(2deg); } 100% { opacity: 1; transform: scale(1) rotate(-3deg); } }
    .icebong.fulltank .ib-multfill { fill: url(#IBGOLD); }
    @media (prefers-reduced-motion: reduce) {
      .icebong * { animation: none !important; transition: none !important; }
      .icebong.rip .ib-rise, .icebong.landed .ib-rise { transform: translateY(420px); }
      .icebong.landed .ib-mult { opacity: 1; }
    }
  `;

  function shared() {                                       // the shared stylesheet and keyframes, once
    if (styled || typeof document === "undefined") return;
    const st = document.createElement("style");
    st.textContent = css;
    document.head.appendChild(st);
    styled = true;
  }
  // THE SYMBOL'S PICTURE is the same bong, short (owner, 2026-11-24: "redo the art for our bong"): tall() drawn in a
  // 200 x ICON_H box - the lip and its icicles, a short tube, the collar bowl packed green, the chamber, the foot.
  // (The first icon, a faceted flask with a bowl on a side stem and black ink outlines, is in git history.) Put it in
  // an element with the classes "icebong tallbong": the show's parts (smoke, flame, ash) are hidden by that sheet.
  const ICON_H = 470;
  function svg() { return tall(ICON_H, true); }

  // ---------------------------------------------------------------- the tall one: the show when it fires
  // (owner, 2026-11-23, with a picture: "it should just look like this shape" - a tall straight tube standing over
  // the whole column on a round base, its bowl burning at the bottom, smoke climbing the tube, the multiplier in
  // the middle - "still cartoon style", "slightly transparent".) Same hand as the symbol: cut ice, ink outline, snow
  // on the rim; the tube and the flask are see-through, so the column shows behind them.
  //
  // IT IS AS TALL AS ITS COLUMN (owner: "make sure the bong takes up the entire board ... dont make it too short, we
  // want it from top to bottom"): tall(vh) draws it in a 200 x vh box - the rim stays at the top, the flask, the bowl
  // and the foot go down with the bottom, and the TUBE is whatever length lies between - so pumpShow asks for exactly
  // its column's shape and nothing is scaled down to fit.
  //
  // Its smoke and its fire are not drawn shapes (owner: "make the smoke more realistic", "make the flame for the bowl
  // more realistic"): the smoke is a noise texture of billows and wisps (tools/highpeaks/smoke_tile.py) scrolling up
  // the tube in two layers, thinning to nothing at its front; the flame is twelve looping frames of fire
  // (tools/highpeaks/flame_sheet.py) over a heap of glowing coals, with sparks going up.
  const tallCss = `
    .tallbong .tb-rise { transform: translateY(var(--rise, 840px)); }
    .tallbong .tb-bub, .tallbong .tb-spark { opacity: 0; }
    .tallbong .tb-out { opacity: 0; transform-box: fill-box; transform-origin: 50% 100%; }
    .tallbong .tb-mult { opacity: 0; transform-box: fill-box; transform-origin: 50% 50%; }
    .tallbong .tb-ember, .tallbong .tb-glow { transform-box: fill-box; transform-origin: 50% 70%; }
    .tallbong .tb-glow { opacity: 0; }   /* unlit: no glow */
    /* The flame grows from the bowl: its group sits AT the bowl (a translate on its parent), so it scales about that
       fixed point. (It used to scale about its own fill-box, and that box holds the whole 12-frame strip sliding
       through its window - shrunk to .45 after the hit, the flame wandered about the bowl as the strip moved: owner,
       2026-11-24, "the flame shouldn't spin / move around after the bong".) */
    .tallbong .tb-fire { opacity: 0; transform: scale(.3); transition: opacity .18s ease, transform .28s cubic-bezier(.2, .9, .3, 1.3); }
    .tallbong .tb-cherry { opacity: 0; transition: opacity .3s ease; }
    .tallbong .tb-ash, .tallbong .tb-speck, .tallbong .tb-wisp { opacity: 0; }
    .tallbong .tb-herb { transition: filter .5s ease; }
    .tallbong .tb-wisp { transform-box: fill-box; transform-origin: 50% 50%; }
    /* the strip is 12 frames in a row: its window must cut the other 11 off (.icebong svg is overflow: visible) */
    .tallbong .tb-fire > svg { overflow: hidden; }
    .tallbong .tb-firestrip { animation: tbFire .74s steps(12) infinite; }
    @keyframes tbFire { to { transform: translateX(-1536px); } }
    .tallbong .tb-puff { transform-box: fill-box; transform-origin: 50% 50%; animation: ibSwirl 1.6s ease-in-out infinite alternate; }
    .tallbong .tb-puff:nth-child(2n) { animation-duration: 2.1s; animation-direction: alternate-reverse; }
    .tallbong .tb-puff:nth-child(3n) { animation-duration: 1.3s; }
    .tallbong .tb-scroll.a { animation: tbScrollA 2.6s linear infinite; }
    .tallbong .tb-scroll.b { animation: tbScrollB 4.3s linear infinite; }
    @keyframes tbScrollA { from { transform: translateY(0); } to { transform: translateY(-440px); } }
    @keyframes tbScrollB { from { transform: translate(-8px, 0); } 50% { transform: translate(8px, -340px); } to { transform: translate(-8px, -680px); } }
    /* being ripped: the fire stands up, the coals pulse, the water bubbles, sparks go up, the smoke climbs the tube */
    .tallbong.rip .tb-fire { opacity: 1; transform: scale(1); }
    .tallbong.rip .tb-cherry { opacity: 1; }
    .tallbong.rip .tb-herb { filter: brightness(.55) saturate(.7); }
    .tallbong.rip .tb-ember { animation: ibBurn .16s ease-in-out infinite alternate; animation-delay: var(--d, 0s); }
    .tallbong.rip .tb-glow { animation: ibGlow .22s ease-in-out infinite alternate; }
    .tallbong.rip .tb-spark { animation: tbSpark .9s ease-out infinite; animation-delay: var(--d, 0s); }
    @keyframes tbSpark { 0% { opacity: 0; transform: translate(0, 0); } 12% { opacity: 1; } 100% { opacity: 0; transform: translate(var(--sx, 0px), -190px); } }
    .tallbong.rip .tb-rise { transform: translateY(0); transition: transform calc(1.1s * var(--tempo, 1)) cubic-bezier(.45, .05, .35, 1); }
    .tallbong.rip .tb-bub { animation: ibBub .55s linear infinite; animation-delay: var(--d, 0s); }
    /* the roll is in: the hit leaves the rim and the bowl is spent - the flame goes OUT (it does not linger or move),
       the cherry cools from orange to grey and what is left in the bowl is ash, a few last specks winking out and a
       thin wisp of smoke going up (owner, 2026-11-24: "the bowl should be more realistic and turn into ash") */
    .tallbong.landed .tb-fire { opacity: 0; transform: scale(.75, .1); transition: opacity .26s ease-in, transform .3s ease-in; }
    .tallbong.landed .tb-ember { animation: none; }
    .tallbong.landed .tb-herb { opacity: 0; }
    .tallbong.landed .tb-cherry { opacity: 0; filter: saturate(.4) brightness(.7); transition: opacity .8s ease-in .08s, filter .7s ease-in; }
    .tallbong.landed .tb-ash { opacity: 1; transition: opacity .35s ease-out; }
    .tallbong.landed .tb-speck { animation: tbSpeck 1.7s ease-in both; animation-delay: var(--d, 0s); }
    @keyframes tbSpeck { 0% { opacity: 0; } 18% { opacity: 1; } 55% { opacity: .8; } 100% { opacity: 0; } }
    .tallbong.landed .tb-wisp { animation: tbWisp 2.1s ease-out both; animation-delay: var(--d, 0s); }
    @keyframes tbWisp { 0% { opacity: 0; transform: translate(0, 0) scale(.45, .6); } 22% { opacity: .55; }
      100% { opacity: 0; transform: translate(var(--dx, 0px), -150px) scale(1.2, 1.9); } }
    .tallbong.landed .tb-glow { animation: none; opacity: 0; transition: opacity 1.1s ease-in; }
    .tallbong.landed .tb-spark { animation: none; opacity: 0; }
    .tallbong.landed .tb-rise { transform: translateY(calc(var(--rise, 840px) * -1.1)); opacity: 0;
      transition: transform calc(1.05s * var(--tempo, 1)) cubic-bezier(.4, 0, .7, .5), opacity calc(.6s * var(--tempo, 1)) ease-in calc(.2s * var(--tempo, 1)); }   /* it thins as it leaves: no hard foot to the column of smoke */
    .tallbong.landed .tb-bub { animation: none; opacity: 0; }
    .tallbong.landed .tb-out { animation: ibOut calc(1.25s * var(--tempo, 1)) cubic-bezier(.2, .7, .3, 1) both; animation-delay: var(--d, 0s); }
    .tallbong.landed .tb-mult { animation: ibSlam calc(.34s * var(--tempo, 1)) cubic-bezier(.5, 0, .8, .4) both; }
    .tallbong.fulltank .ib-multfill { fill: url(#IBGOLD); }
    @media (prefers-reduced-motion: reduce) {
      .tallbong.rip .tb-rise, .tallbong.landed .tb-rise { transform: translateY(var(--rise, 840px)); }
      .tallbong.landed .tb-mult { opacity: 1; }
      .tallbong .tb-fire { opacity: 0; }
    }
  `;
  let tallStyled = false;
  function tall(vh, icon = false) {
    shared();
    if (!tallStyled && typeof document !== "undefined") {
      const st = document.createElement("style");
      st.textContent = tallCss;
      document.head.appendChild(st);
      tallStyled = true;
    }
    const id = "tb" + (++seq);
    const VH = icon ? Math.round(vh) : Math.max(640, Math.min(1800, Math.round(vh || 920))), D = VH - 920;   // D: what the tube gains or gives up
    // (2026-11-24, owner, with a picture of the shape he wants: "redo the art for our bong ... with icicles hanging off
    // of it ... the bowl ... doesn't even [have] a big black outline and actually looks connected to the bong and the
    // bong has a bottom piece instead of just a round bottom ... more realistic shading") A straight tube with a lip
    // at its mouth, a round chamber, the bowl a collar where the two meet - one piece of the same ice - and a foot
    // under it. Drawn in the ice's own blues with soft light (gradients, blurred highlights, a rim of bounce light),
    // its contours a deep blue, not the black ink; icicles hang off the lip and the collar.
    const E = "#2A6FA0", TW = 76, TX = 100 - TW / 2, CY = 792 + D, R = 84, TH = 672 + D;
    const rise = 840 + D;
    const tiles = (h0, th) => Array.from({ length: Math.ceil((VH - h0 + th) / th) + 1 }, (_, i) => h0 + i * th);
    const puffs = [];
    for (let y = 150, i = 0; y < VH - 130; y += 170, i++) puffs.push(`<circle class="tb-puff" cx="${i % 2 ? 118 : 84}" cy="${y}" r="${44 + (i % 3) * 6}" fill="url(#${id}p)"/>`);
    const bubbles = [[52, 846, 7, 0], [78, 858, 5, .18], [128, 852, 6, .33], [150, 838, 5, .09], [100, 862, 4, .41]]
      .map(([x, y, r, d]) => `<circle class="tb-bub" style="--d:${d}s" cx="${x}" cy="${y}" r="${r}" fill="#E8FBFF" fill-opacity=".8" stroke="#8FD0F0" stroke-width="1.5"/>`).join("");
    const outs = [[100, 18, 30, 0, 0], [78, 24, 22, .1, -40], [124, 22, 24, .18, 36], [100, 12, 34, .3, 10], [86, 20, 20, .42, -60], [118, 18, 22, .5, 54]]
      .map(([x, y, r, d, dx]) => `<image class="tb-out" style="--d:${d}s;--dx:${dx}px" href="assets/fx/smoke_soft.webp" x="${x - r * 2}" y="${y - r * 2}" width="${r * 4}" height="${r * 4}"/>`).join("");
    // the cherry: a heap of glowing coals on the bowl (hot in the middle, dark at the crust), not flat orange lumps
    const coals = [[68, 722, 17], [100, 708, 20], [132, 722, 17], [84, 732, 16], [116, 732, 16], [100, 727, 13]]
      .map(([x, y, r], i) => `<ellipse class="tb-ember" style="--d:${(i * .037).toFixed(3)}s" cx="${x}" cy="${y}" rx="${r}" ry="${r * .8}" fill="url(#${id}c)" stroke="#7A1E06" stroke-width="2"/>`).join("");
    // what is in the bowl: a packed heap of green (chunky nugs, a few orange hairs), and the same heap as ash
    const HEAP = [[66, 735, 18, 14], [134, 735, 18, 14], [84, 743, 17, 12], [116, 743, 17, 12], [100, 722, 23, 18], [100, 740, 15, 11]];
    const GREEN = ["#43A035", "#3B8E2E", "#51B43F", "#3F9A32", "#5CC246", "#6BD052"], GREY = ["#A9AEB7", "#989EA8", "#C2C6CD", "#B3B8C0", "#D2D6DC", "#E4E7EB"];
    const heap = (cols, ink) => HEAP.map(([x, y, rx, ry], i) => `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${cols[i]}" stroke="${ink}" stroke-width="2.4"/>`).join("");
    const herb = heap(GREEN, "#256B1C") +
      [[92, 714, 104, 708], [112, 726, 122, 722], [72, 730, 64, 726], [128, 738, 138, 733], [98, 736, 106, 733]]
        .map(([a, b, c, d]) => `<path d="M${a} ${b} Q${(a + c) / 2 + 3} ${Math.min(b, d) - 5} ${c} ${d}" fill="none" stroke="#F0962E" stroke-width="2.4" stroke-linecap="round"/>`).join("") +
      [[90, 724, 2.6], [110, 716, 2.2], [70, 738, 2], [130, 730, 2.2], [102, 742, 1.8]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="#C6F7A6"/>`).join("");
    const ash = heap(GREY, "#6A7079") +
      [[88, 720, 110, 726], [70, 736, 80, 732], [118, 740, 132, 736], [96, 742, 104, 738]]
        .map(([a, b, c, d]) => `<path d="M${a} ${b} L${c} ${d}" stroke="#6B717A" stroke-width="2" stroke-linecap="round"/>`).join("") +
      [[94, 716, 3], [112, 730, 2.4], [72, 732, 2.2], [128, 742, 2], [104, 744, 1.8]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff"/>`).join("") +
      [[86, 728, 3.4, 0], [116, 720, 3, .25], [100, 738, 2.8, .5], [72, 742, 2.4, .1], [130, 734, 2.6, .4]]
        .map(([x, y, r, d]) => `<circle class="tb-speck" style="--d:${d}s" cx="${x}" cy="${y}" r="${r}" fill="#FF8A2A" stroke="#FFD27A" stroke-width="1.2"/>`).join("");
    const wisps = [[100, 0, -14, 34], [92, .35, 12, 28], [108, .75, -6, 30]]
      .map(([x, d, dx, r]) => `<image class="tb-wisp" style="--d:${d}s;--dx:${dx}px" href="assets/fx/smoke_soft.webp" x="${x - r}" y="${660 - r}" width="${r * 2}" height="${r * 2}"/>`).join("");
    const sparks = [[78, 0, -22], [100, .22, 8], [122, .41, 26], [90, .6, -8], [112, .78, 14]]
      .map(([x, d, sx]) => `<circle class="tb-spark" style="--d:${d}s;--sx:${sx}px" cx="${x}" cy="660" r="3.2" fill="#FFE08A"/>`).join("");
    // an icicle: a spike of ice with light down one side (x, where it hangs from, how wide, how long)
    const icicle = (x, y, w, len) => `<path d="M${x - w / 2} ${y} Q${x - w * .2} ${y + len * .55} ${x} ${y + len} Q${x + w * .2} ${y + len * .55} ${x + w / 2} ${y} Z" fill="url(#${id}n)" stroke="#5FA6D2" stroke-width="2" stroke-linejoin="round"/>` +
      `<path d="M${x - w * .16} ${y + 3} L${x - w * .05} ${y + len * .55}" stroke="#fff" stroke-width="${Math.max(1.4, w * .16).toFixed(1)}" stroke-linecap="round" opacity=".9"/>`;
    const lipIce = [[52, 9, 24], [63, 8, 42], [77, 7, 18], [121, 7, 28], [134, 9, 50], [147, 8, 20]].map(([x, w, l]) => icicle(x, 61, w, l)).join("");
    return `<svg viewBox="0 0 200 ${VH}" preserveAspectRatio="xMidYMid meet" style="--rise:${rise}px" aria-hidden="true">
    <defs>
      <clipPath id="${id}b"><rect x="${TX}" y="56" width="${TW}" height="${TH}"/><circle cx="100" cy="${CY}" r="${R}"/></clipPath>
      <clipPath id="${id}i"><rect x="${TX + 4}" y="60" width="${TW - 8}" height="${TH}"/><circle cx="100" cy="${CY}" r="${R - 5}"/></clipPath>
      <linearGradient id="${id}g" gradientUnits="userSpaceOnUse" x1="0" y1="100" x2="0" y2="330"><stop offset="0" stop-color="#000"/><stop offset=".45" stop-color="#777"/><stop offset="1" stop-color="#fff"/></linearGradient>
      <mask id="${id}m" maskUnits="userSpaceOnUse" x="-80" y="80" width="360" height="${VH + 200}"><rect x="-80" y="80" width="360" height="${VH + 200}" fill="url(#${id}g)"/></mask>
      <radialGradient id="${id}p"><stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset=".6" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
      <radialGradient id="${id}c" cx=".45" cy=".4" r=".7"><stop offset="0" stop-color="#FFF6C0"/><stop offset=".3" stop-color="#FFC23C"/><stop offset=".62" stop-color="#FF6A12"/><stop offset=".86" stop-color="#C12A06"/><stop offset="1" stop-color="#6E1204"/></radialGradient>
      <radialGradient id="${id}w"><stop offset="0" stop-color="#FFC460" stop-opacity=".95"/><stop offset=".45" stop-color="#FF8A1E" stop-opacity=".5"/><stop offset="1" stop-color="#FF6A00" stop-opacity="0"/></radialGradient>
      <linearGradient id="IBGOLD" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF6CF"/><stop offset=".5" stop-color="#FFC233"/><stop offset="1" stop-color="#E08A00"/></linearGradient>
      <!-- the ice: a round tube (dark at its edges, clear down its middle), a round chamber lit from the upper left -->
      <linearGradient id="${id}t" gradientUnits="userSpaceOnUse" x1="${TX}" y1="0" x2="${TX + TW}" y2="0">
        <stop offset="0" stop-color="#3E8FC2" stop-opacity=".78"/><stop offset=".16" stop-color="#8CCBED" stop-opacity=".5"/><stop offset=".5" stop-color="#E4F6FF" stop-opacity=".22"/>
        <stop offset=".82" stop-color="#9AD3F1" stop-opacity=".46"/><stop offset="1" stop-color="#3683B6" stop-opacity=".82"/></linearGradient>
      <radialGradient id="${id}u" cx=".36" cy=".3" r=".82"><stop offset="0" stop-color="#F4FCFF" stop-opacity=".62"/><stop offset=".5" stop-color="#A5DAF5" stop-opacity=".42"/>
        <stop offset=".86" stop-color="#4E9FCF" stop-opacity=".7"/><stop offset="1" stop-color="#2C78AC" stop-opacity=".88"/></radialGradient>
      <linearGradient id="${id}k" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#C9ECFC"/><stop offset=".45" stop-color="#7FC3EA"/><stop offset="1" stop-color="#3A88BC"/></linearGradient>
      <linearGradient id="${id}f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C4E9FB"/><stop offset=".55" stop-color="#74BBE4"/><stop offset="1" stop-color="#3C89BC"/></linearGradient>
      <linearGradient id="${id}n" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".5" stop-color="#C9EBFB"/><stop offset="1" stop-color="#86C8EC"/></linearGradient>
      <linearGradient id="${id}r" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EAF8FF"/><stop offset=".55" stop-color="#A2D8F4"/><stop offset="1" stop-color="#5AA9D8"/></linearGradient>
      <filter id="${id}s" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3"/></filter>
    </defs>
    <!-- the foot: a short neck and a slab, the shadow it stands in -->
    <g transform="translate(0 ${D})">
      ${icon ? "" : `<ellipse cx="100" cy="911" rx="74" ry="7" fill="#06142E" opacity=".3"/>`}
      <path d="M74 864 L68 893 L132 893 L126 864 Z" fill="url(#${id}f)" stroke="${E}" stroke-width="3.5" stroke-linejoin="round"/>
      <rect x="38" y="888" width="124" height="23" rx="9.5" fill="url(#${id}f)" stroke="${E}" stroke-width="3.5"/>
      <rect x="50" y="892.5" width="58" height="5" rx="2.5" fill="#fff" opacity=".75"/>
      <path d="M82 870 L79 886" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".6"/>
    </g>
    <!-- the ice: see-through tube and chamber -->
    <rect x="${TX}" y="56" width="${TW}" height="${TH}" fill="url(#${id}t)"/>
    <circle cx="100" cy="${CY}" r="${R}" fill="url(#${id}u)"/>
    <g clip-path="url(#${id}i)">
      <!-- icy water in the chamber -->
      <g transform="translate(0 ${D})">
        <path d="M0 808 Q30 798 60 808 T120 808 T200 808 L200 900 L0 900 Z" fill="#38C6E8" opacity=".8"/>
        <path d="M0 828 Q50 818 100 830 T200 826 L200 900 L0 900 Z" fill="#1FA0D2" opacity=".8"/>
        <path d="M0 808 Q30 798 60 808 T120 808 T200 808" fill="none" stroke="#E8FBFF" stroke-width="4" opacity=".9"/>
        ${bubbles}
      </g>
      <!-- the hit: smoke climbing the tube -->
      <g class="tb-rise"><g mask="url(#${id}m)">
        <rect x="0" y="90" width="200" height="${VH}" fill="#E9F1F8" opacity=".5"/>
        <g class="tb-scroll a">${tiles(90, 440).map(y => `<image href="assets/fx/smoke.webp" x="-10" y="${y}" width="220" height="440" preserveAspectRatio="none"/>`).join("")}</g>
        <g class="tb-scroll b" opacity=".8">${tiles(90, 680).map(y => `<image href="assets/fx/smoke.webp" x="-70" y="${y}" width="340" height="680" preserveAspectRatio="none" transform="translate(200 0) scale(-1 1)"/>`).join("")}</g>
        ${puffs.join("")}
      </g></g>
    </g>
    <!-- the glass in front of what is in it: its round sides in shade, light down its front, bounce light low in the chamber -->
    <g clip-path="url(#${id}b)">
      <rect x="${TX}" y="56" width="10" height="${TH}" fill="#2A75AA" opacity=".34"/>
      <rect x="${TX + TW - 9}" y="56" width="9" height="${TH}" fill="#2A75AA" opacity=".3"/>
      <rect x="${TX + TW - 17}" y="56" width="6" height="${TH}" fill="#fff" opacity=".2"/>
      <g transform="translate(0 ${D})">
        <path d="M18 806 A84 84 0 0 0 176 826 A92 92 0 0 1 18 806 Z" fill="#1C6BA2" opacity=".38"/>
        <ellipse cx="62" cy="768" rx="20" ry="34" fill="#fff" opacity=".6" filter="url(#${id}s)" transform="rotate(24 62 768)"/>
        <path d="M164 772 Q176 800 162 834" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".5" filter="url(#${id}s)"/>
        <path d="M70 858 Q100 870 132 858" fill="none" stroke="#DDF5FF" stroke-width="4" stroke-linecap="round" opacity=".5"/>
      </g>
    </g>
    <path d="M${TX + 13} 84 L${TX + 13} ${Math.min(322, 640 + D)}" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".85"/>
    ${icon ? "" : `<path d="M${TX + 13} 356 L${TX + 13} ${430 + Math.max(0, D * .5)}" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".7"/>
    <path d="M${TX + TW - 11} 190 L${TX + TW - 16} 214 L${TX + TW - 10} 234" fill="none" stroke="#fff" stroke-width="2.6" stroke-linejoin="round" opacity=".8"/>
    <circle cx="${TX + 22}" cy="${520 + D * .6}" r="2.2" fill="#fff" opacity=".9"/>`}
    <circle cx="${TX + TW - 14}" cy="112" r="2.6" fill="#fff" opacity=".9"/>
    <!-- its contours, in the ice's own deep blue -->
    <path d="M${TX} 62 L${TX} ${716 + D} M${TX + TW} 62 L${TX + TW} ${716 + D}" fill="none" stroke="${E}" stroke-width="4" stroke-linecap="round"/>
    <circle cx="100" cy="${CY}" r="${R}" fill="none" stroke="${E}" stroke-width="4"/>
    <!-- the lip at its mouth, snow on its shoulders, icicles hanging off it -->
    <rect x="47" y="38" width="106" height="25" rx="10" fill="url(#${id}r)" stroke="${E}" stroke-width="3.5"/>
    <ellipse cx="100" cy="40" rx="51" ry="10.5" fill="#E2F5FF" stroke="${E}" stroke-width="3.5"/>
    <ellipse cx="100" cy="41" rx="37" ry="6.2" fill="#3A82B4"/>
    <ellipse cx="100" cy="43" rx="31" ry="4" fill="#245F8C"/>
    <rect x="58" y="51" width="46" height="4.5" rx="2.2" fill="#fff" opacity=".85"/>
    ${lipIce}
    <path d="M40 44 C32 30 48 20 60 28 C68 22 80 28 76 38 C70 42 52 46 40 44 Z" fill="#fff" stroke="#7FB6DA" stroke-width="2.5" stroke-linejoin="round"/>
    <path d="M160 44 C170 32 156 20 142 28 C134 22 122 30 126 38 C134 42 150 46 160 44 Z" fill="#fff" stroke="#7FB6DA" stroke-width="2.5" stroke-linejoin="round"/>
    <path d="M46 40 C54 36 64 38 70 35" fill="none" stroke="#CDE6F7" stroke-width="3" stroke-linecap="round"/>
    <!-- the bowl: a collar of the same ice where the tube meets the chamber - packed green; lit, a heap of glowing
         coals under a real flame; spent, ash -->
    <g transform="translate(0 ${D})">
      <circle class="tb-glow" cx="100" cy="668" r="120" fill="url(#${id}w)"/>
      <ellipse cx="100" cy="712" rx="53" ry="17" fill="#2B72A4" stroke="${E}" stroke-width="3"/>
      <ellipse cx="100" cy="716" rx="44" ry="11" fill="#1D5580"/>
      <g transform="translate(0 -31)">
        <g class="tb-herb">${herb}</g>
        <g class="tb-ash">${ash}</g>
        <g class="tb-cherry">${coals}</g>
      </g>
      <path d="M47 712 C49 744 60 768 76 776 L124 776 C140 768 151 744 153 712 C139 735 61 735 47 712 Z" fill="url(#${id}k)" stroke="${E}" stroke-width="3.5" stroke-linejoin="round"/>
      <path d="M52 718 C68 737 132 737 148 718" fill="none" stroke="#EAF8FF" stroke-width="4" stroke-linecap="round" opacity=".95"/>
      <path d="M60 738 C64 752 71 763 80 768" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".65"/>
      <path d="M140 742 C137 754 131 764 123 769" fill="none" stroke="#2F7DB2" stroke-width="5" stroke-linecap="round" opacity=".55"/>
      ${icicle(51, 722, 7, 22)}${icicle(149, 722, 8, 30)}${icicle(140, 742, 6, 16)}
      <g transform="translate(100 710)"><g class="tb-fire"><svg x="-86" y="-244" width="172" height="258" viewBox="0 0 128 192" preserveAspectRatio="none" overflow="hidden">
        <image class="tb-firestrip" href="assets/fx/flame.webp" x="0" y="0" width="1536" height="192" preserveAspectRatio="none"/></svg></g></g>
      ${sparks}
      ${wisps}
    </g>
    ${outs}
    <g class="tb-mult"><text class="ib-multtext" x="100" y="${470 + Math.round(D / 2)}" text-anchor="middle" font-family="Fredoka, 'Arial Rounded MT Bold', sans-serif" font-weight="700" font-size="92"
      stroke="#143A5C" stroke-width="20" stroke-linejoin="round" fill="#143A5C"> </text>
      <text class="ib-multtext ib-multfill" x="100" y="${470 + Math.round(D / 2)}" text-anchor="middle" font-family="Fredoka, 'Arial Rounded MT Bold', sans-serif" font-weight="700" font-size="92" fill="#CFF1FF"> </text></g>
  </svg>`;
  }
  // write the multiplier on the flask (the figure shrinks to fit: "x2" ... "x64", "MAX")
  function label(el, text) {
    for (const t of el.querySelectorAll(".ib-multtext")) {
      t.textContent = text;
      const tallOne = !!t.closest(".tallbong");
      t.setAttribute("font-size", tallOne ? (text.length <= 2 ? 120 : text.length === 3 ? 96 : 74) : (text.length <= 2 ? 96 : text.length === 3 ? 78 : 62));
    }
  }

  window.IceBong = { svg, tall, label, css };
})();
