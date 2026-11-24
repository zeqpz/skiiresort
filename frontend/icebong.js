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

  // the body's outline, and its inside (where water stands and smoke climbs), in a 300 x 520 box
  // (cut ice, not blown glass: the flask is a many-sided block and every edge is a straight cut)
  const FLASK = [[110, 282], [72, 300], [46, 340], [38, 392], [48, 440], [80, 478], [128, 494], [172, 494], [220, 478], [252, 440], [262, 392],
                 [254, 340], [228, 300], [190, 282]];
  const BODY = "M110 80 L110 205 L119 215 L110 225 " + FLASK.map(p => "L" + p[0] + " " + p[1]).join(" ") + " L190 225 L181 215 L190 205 L190 80 Z";
  const INSIDE = "M122 88 L122 200 L130 215 L122 230 L122 292 L82 311 L60 345 L52 392 L61 434 L88 467 L131 481 L169 481 L212 467 L239 434 L248 392 " +
    "L240 345 L218 311 L178 292 L178 230 L170 215 L178 200 L178 88 Z";
  // the flask's faces: one cut from its middle to each side, lit from the upper right
  const TINT = ["#9BD9F7", "#84CCF2", "#6DBFEC", "#62B7E8", "#74C3EE", "#8ED3F6", "#A9DFF9", "#C4EBFC", "#D9F3FF", "#E8F8FF", "#DDF4FF", "#C9EDFD", "#B4E4FA"];
  const FACES = FLASK.slice(0, -1).map((p, i) => `<path d="M150 388 L${p[0]} ${p[1]} L${FLASK[i + 1][0]} ${FLASK[i + 1][1]} Z" fill="${TINT[i]}"/>`).join("") +
    FLASK.map(p => `<path d="M150 388 L${p[0]} ${p[1]}" stroke="#F2FBFF" stroke-width="2" opacity=".55"/>`).join("");

  function svg({ still = false } = {}) {
    if (!styled && typeof document !== "undefined") {
      const st = document.createElement("style");
      st.textContent = css;
      document.head.appendChild(st);
      styled = true;
    }
    const id = "ib" + (++seq);
    const puffs = [[96, 40, 30], [150, 22, 34], [204, 44, 28], [120, 96, 26], [182, 104, 30], [150, 160, 30], [136, 222, 24], [166, 262, 26],
                   [150, 320, 26], [140, 372, 24], [162, 60, 24], [92, 120, 22], [210, 130, 22]]
      .map(([x, y, r], i) => `<circle class="ib-puff" cx="${x}" cy="${y + 96}" r="${r}" fill="${i % 3 ? "#F4FAFF" : "#D3E6F5"}"/>`).join("");
    const bubbles = [[92, 462, 7, 0], [128, 470, 5, .18], [176, 466, 6, .33], [206, 456, 5, .09], [150, 474, 4, .41], [112, 448, 4, .27]]
      .map(([x, y, r, d]) => `<circle class="ib-bub" style="--d:${d}s" cx="${x}" cy="${y}" r="${r}" fill="#E8FBFF" stroke="${INK}" stroke-width="2"/>`).join("");
    const outs = [[150, 34, 26, 0, 0], [132, 40, 20, .1, -34], [170, 38, 22, .18, 30], [150, 30, 30, .3, 8], [140, 36, 18, .42, -52], [164, 34, 20, .5, 46]]
      .map(([x, y, r, d, dx]) => `<g class="ib-out" style="--d:${d}s;--dx:${dx}px"><circle cx="${x}" cy="${y}" r="${r}" fill="#F4FAFF" stroke="${INK}" stroke-width="4"/>` +
        `<circle cx="${x - r * .28}" cy="${y + r * .2}" r="${r * .5}" fill="#D3E6F5"/></g>`).join("");
    return `<svg viewBox="0 0 300 520" aria-hidden="true">
    <defs>
      <clipPath id="${id}b"><path d="${BODY}"/></clipPath>
      <clipPath id="${id}i"><path d="${INSIDE}"/></clipPath>
      <linearGradient id="IBGOLD" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF6CF"/><stop offset=".5" stop-color="#FFC233"/><stop offset="1" stop-color="#E08A00"/></linearGradient>
    </defs>
    <!-- foot -->
    <rect x="98" y="484" width="104" height="24" rx="10" fill="#7CC8F2" stroke="${INK}" stroke-width="9"/>
    <rect x="108" y="490" width="60" height="6" rx="3" fill="#D9F2FF"/>
    <!-- the stem to the bowl, behind the flask's ink -->
    <path d="M196 418 L240 372" stroke="${INK}" stroke-width="34" stroke-linecap="round"/>
    <path d="M196 418 L240 372" stroke="#8FD3F5" stroke-width="18" stroke-linecap="round"/>
    <path d="M200 408 L236 370" stroke="#E4F7FF" stroke-width="5" stroke-linecap="round"/>
    <!-- the ice: body, facets cut into it, then what is inside it -->
    <path d="${BODY}" fill="#BDE8FC" stroke="${INK}" stroke-width="10" stroke-linejoin="round"/>
    <g clip-path="url(#${id}b)">
      <path d="M110 80 L132 80 L126 300 L110 300 Z" fill="#8ED3F6"/>
      <path d="M172 80 L190 80 L190 300 L178 300 Z" fill="#DDF4FF"/>
      ${FACES}
      <path d="M110 150 L128 138 L128 80 L110 80 Z" fill="#74C3EE"/>
      <path d="M172 120 L190 104 L190 80 L172 80 Z" fill="#F2FBFF"/>
      <path d="M110 282 L150 300 L190 282 L178 262 L122 262 Z" fill="#CDEEFF"/>
    </g>
    <g clip-path="url(#${id}i)">
      <!-- icy water in the flask -->
      <path d="M40 418 Q78 408 112 418 T184 418 T262 418 L262 500 L40 500 Z" fill="#38C6E8"/>
      <path d="M40 440 Q90 430 150 442 T262 438 L262 500 L40 500 Z" fill="#1FA6D6"/>
      <path d="M40 418 Q78 408 112 418 T184 418 T262 418" fill="none" stroke="#E8FBFF" stroke-width="5"/>
      ${still ? "" : bubbles}
      <!-- ice cubes stacked on the pinch -->
      <g stroke="${INK}" stroke-width="4" stroke-linejoin="round">
        <path d="M127 178 L150 170 L160 196 L137 205 Z" fill="#EAF9FF"/>
        <path d="M150 150 L174 156 L170 184 L146 178 Z" fill="#CDEEFF"/>
        <path d="M128 132 L152 126 L158 152 L134 158 Z" fill="#EAF9FF"/>
      </g>
      <path d="M133 140 L147 136" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
      <path d="M152 160 L166 163" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
      <!-- the hit: smoke climbing from the water to the mouthpiece -->
      ${still ? "" : `<g class="ib-rise"><path d="M30 104 Q70 84 110 104 T190 104 T270 104 L270 520 L30 520 Z" fill="#EDF6FD" opacity=".78"/>${puffs}</g>`}
    </g>
    <!-- light on the ice -->
    <path d="M119 96 L119 190" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".9"/>
    <path d="M119 238 L119 268" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".9"/>
    <path d="M64 372 L74 340 L98 314" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity=".92"/>
    <path d="M60 394 L62 404" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".92"/>
    <!-- cracks in the ice, and frost -->
    <path d="M232 318 L218 336 L226 352 L210 372" fill="none" stroke="#fff" stroke-width="3.5" stroke-linejoin="round" opacity=".9"/>
    <path d="M218 336 L204 340" stroke="#fff" stroke-width="3" opacity=".9"/>
    <path d="M176 118 L168 136 L176 150" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round" opacity=".9"/>
    <path d="M70 446 L88 456 L84 470" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round" opacity=".75"/>
    <!-- icicles off the flask's shoulders and the pinch -->
    <g stroke="${INK}" stroke-width="5" stroke-linejoin="round" fill="#DDF4FF">
      <path d="M44 396 L50 426 L58 398 Z"/><path d="M246 398 L253 430 L260 396 Z"/>
      <path d="M103 218 L109 240 L116 220 Z"/><path d="M184 220 L191 244 L197 218 Z"/>
    </g>
    <g fill="#fff" opacity=".85"><circle cx="205" cy="322" r="3"/><circle cx="222" cy="344" r="2.4"/><circle cx="96" cy="462" r="2.6"/><circle cx="181" cy="252" r="2.4"/><circle cx="168" cy="118" r="2.4"/></g>
    <!-- the rim, its icicles and its cap of snow -->
    <g stroke="${INK}" stroke-width="5" stroke-linejoin="round" fill="#DDF4FF">
      <path d="M100 82 L106 108 L113 82 Z"/><path d="M186 82 L193 112 L200 82 Z"/><path d="M146 84 L150 98 L155 84 Z"/>
    </g>
    <rect x="92" y="48" width="116" height="38" rx="17" fill="#A6DDF8" stroke="${INK}" stroke-width="10"/>
    <rect x="104" y="56" width="62" height="8" rx="4" fill="#EAF9FF"/>
    <path d="M90 56 C84 38 104 26 118 34 C126 20 152 18 162 30 C176 20 204 26 204 42 C216 46 214 60 206 62 L96 62 C90 62 88 60 90 56 Z" fill="#fff" stroke="${INK}" stroke-width="8" stroke-linejoin="round"/>
    <path d="M104 56 C116 50 130 56 142 52 C156 48 170 56 196 54" fill="none" stroke="#C5E2F8" stroke-width="5" stroke-linecap="round"/>
    <!-- the bowl, out front: the cherry and its glow -->
    <circle class="ib-glow" cx="244" cy="352" r="46" fill="#FF9A2E"/>
    <path d="M212 352 C212 384 230 396 244 396 C258 396 276 384 276 352 Z" fill="#8FD3F5" stroke="${INK}" stroke-width="9" stroke-linejoin="round"/>
    <path d="M222 362 C224 376 234 384 244 384" fill="none" stroke="#E4F7FF" stroke-width="5" stroke-linecap="round"/>
    <ellipse cx="244" cy="352" rx="34" ry="17" fill="#3E9A2B" stroke="${INK}" stroke-width="9"/>
    <path d="M222 350 Q230 340 238 350 T254 350 T268 350" fill="none" stroke="#7CD957" stroke-width="5" stroke-linecap="round"/>
    <ellipse class="ib-ember" cx="244" cy="350" rx="17" ry="9" fill="#FF6A14" stroke="${INK}" stroke-width="4"/>
    <ellipse class="ib-core" cx="244" cy="349" rx="8" ry="4" fill="#FFE27A"/>
    ${still ? "" : `<path class="ib-flame" d="M232 346 C226 326 240 322 238 304 C252 316 262 328 256 346 Z" fill="#FFB02E" stroke="${INK}" stroke-width="4" stroke-linejoin="round"/>`}
    ${still ? `<path d="M246 330 C240 318 254 310 248 296 C244 286 254 280 252 270" fill="none" stroke="${INK}" stroke-width="11" stroke-linecap="round"/>
      <path d="M246 330 C240 318 254 310 248 296 C244 286 254 280 252 270" fill="none" stroke="#E6EDF5" stroke-width="5" stroke-linecap="round"/>` : outs}
    ${still ? "" : `<g class="ib-mult"><text class="ib-multtext" x="140" y="404" text-anchor="middle" font-family="Fredoka, 'Arial Rounded MT Bold', sans-serif" font-weight="700" font-size="92"
      stroke="${INK}" stroke-width="20" stroke-linejoin="round" fill="${INK}"> </text>
      <text class="ib-multtext ib-multfill" x="140" y="404" text-anchor="middle" font-family="Fredoka, 'Arial Rounded MT Bold', sans-serif" font-weight="700" font-size="92" fill="#fff"> </text></g>`}
  </svg>`;
  }

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
  const T_OUT = [[32, 700], [18, 728], [8, 765], [6, 800], [16, 838], [40, 866], [72, 882], [128, 882], [160, 866], [184, 838], [194, 800], [192, 765], [182, 728], [168, 700]];
  const T_INS = [[43, 704], [29, 732], [18, 768], [17, 800], [26, 834], [47, 858], [76, 871], [124, 871], [153, 858], [174, 834], [183, 800], [182, 768], [171, 732], [157, 704]];
  const tallCss = `
    .tallbong .tb-rise { transform: translateY(var(--rise, 840px)); }
    .tallbong .tb-bub, .tallbong .tb-spark { opacity: 0; }
    .tallbong .tb-out { opacity: 0; transform-box: fill-box; transform-origin: 50% 100%; }
    .tallbong .tb-mult { opacity: 0; transform-box: fill-box; transform-origin: 50% 50%; }
    .tallbong .tb-ember, .tallbong .tb-glow { transform-box: fill-box; transform-origin: 50% 70%; }
    .tallbong .tb-glow { opacity: .22; }
    .tallbong .tb-fire { opacity: 0; transform-box: fill-box; transform-origin: 50% 100%; transform: scale(.3); transition: opacity .18s ease, transform .28s cubic-bezier(.2, .9, .3, 1.3); }
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
    .tallbong.rip .tb-ember { animation: ibBurn .16s ease-in-out infinite alternate; animation-delay: var(--d, 0s); }
    .tallbong.rip .tb-glow { animation: ibGlow .22s ease-in-out infinite alternate; }
    .tallbong.rip .tb-spark { animation: tbSpark .9s ease-out infinite; animation-delay: var(--d, 0s); }
    @keyframes tbSpark { 0% { opacity: 0; transform: translate(0, 0); } 12% { opacity: 1; } 100% { opacity: 0; transform: translate(var(--sx, 0px), -190px); } }
    .tallbong.rip .tb-rise { transform: translateY(0); transition: transform calc(1.1s * var(--tempo, 1)) cubic-bezier(.45, .05, .35, 1); }
    .tallbong.rip .tb-bub { animation: ibBub .55s linear infinite; animation-delay: var(--d, 0s); }
    /* the roll is in: the hit leaves the rim, the fire dies back to its coals, the multiplier slams onto the tube */
    .tallbong.landed .tb-fire { opacity: .75; transform: scale(.45); transition-duration: .5s; }
    .tallbong.landed .tb-ember { animation: ibBurn .9s ease-in-out infinite alternate; }
    .tallbong.landed .tb-glow { animation: none; opacity: .45; }
    .tallbong.landed .tb-spark { animation: none; opacity: 0; }
    .tallbong.landed .tb-rise { transform: translateY(calc(var(--rise, 840px) * -1.1)); transition: transform calc(1.05s * var(--tempo, 1)) cubic-bezier(.4, 0, .7, .5); }
    .tallbong.landed .tb-bub { animation: none; opacity: 0; }
    .tallbong.landed .tb-out { animation: ibOut calc(1.25s * var(--tempo, 1)) cubic-bezier(.2, .7, .3, 1) both; animation-delay: var(--d, 0s); }
    .tallbong.landed .tb-mult { animation: ibSlam calc(.34s * var(--tempo, 1)) cubic-bezier(.5, 0, .8, .4) both; }
    .tallbong.fulltank .ib-multfill { fill: url(#IBGOLD); }
    @media (prefers-reduced-motion: reduce) {
      .tallbong.rip .tb-rise, .tallbong.landed .tb-rise { transform: translateY(var(--rise, 840px)); }
      .tallbong.landed .tb-mult { opacity: 1; }
      .tallbong .tb-fire { opacity: .8; transform: scale(.45); }
    }
  `;
  let tallStyled = false;
  function tall(vh) {
    svg({ still: true });                                    // (adds the shared stylesheet and keyframes once)
    if (!tallStyled && typeof document !== "undefined") {
      const st = document.createElement("style");
      st.textContent = tallCss;
      document.head.appendChild(st);
      tallStyled = true;
    }
    const id = "tb" + (++seq);
    const VH = Math.max(640, Math.min(1800, Math.round(vh || 920))), D = VH - 920;   // D: what the tube gains or gives up
    const pts = a => a.map(p => `L${p[0]} ${p[1] + D}`).join(" ");
    const BODY2 = `M32 62 ${pts(T_OUT)} L168 62 Z`, IN2 = `M43 70 ${pts(T_INS)} L157 70 Z`;
    const rise = 840 + D;
    const tiles = (h0, th) => Array.from({ length: Math.ceil((VH - h0 + th) / th) + 1 }, (_, i) => h0 + i * th);
    const puffs = [];
    for (let y = 150, i = 0; y < VH - 130; y += 170, i++) puffs.push(`<circle class="tb-puff" cx="${i % 2 ? 126 : 76}" cy="${y}" r="${52 + (i % 3) * 6}" fill="url(#${id}p)"/>`);
    const bubbles = [[40, 846, 7, 0], [70, 856, 5, .18], [132, 852, 6, .33], [160, 842, 5, .09], [100, 860, 4, .41]]
      .map(([x, y, r, d]) => `<circle class="tb-bub" style="--d:${d}s" cx="${x}" cy="${y}" r="${r}" fill="#E8FBFF" stroke="${INK}" stroke-width="2"/>`).join("");
    const outs = [[100, 18, 30, 0, 0], [78, 24, 22, .1, -40], [124, 22, 24, .18, 36], [100, 12, 34, .3, 10], [86, 20, 20, .42, -60], [118, 18, 22, .5, 54]]
      .map(([x, y, r, d, dx]) => `<image class="tb-out" style="--d:${d}s;--dx:${dx}px" href="assets/fx/smoke_soft.webp" x="${x - r * 2}" y="${y - r * 2}" width="${r * 4}" height="${r * 4}"/>`).join("");
    // the cherry: a heap of glowing coals on the bowl (hot in the middle, dark at the crust), not flat orange lumps
    const coals = [[68, 722, 17], [100, 708, 20], [132, 722, 17], [84, 732, 16], [116, 732, 16], [100, 727, 13]]
      .map(([x, y, r], i) => `<ellipse class="tb-ember" style="--d:${(i * .037).toFixed(3)}s" cx="${x}" cy="${y}" rx="${r}" ry="${r * .8}" fill="url(#${id}c)" stroke="#3A0C04" stroke-width="2.5"/>`).join("");
    const sparks = [[78, 0, -22], [100, .22, 8], [122, .41, 26], [90, .6, -8], [112, .78, 14]]
      .map(([x, d, sx]) => `<circle class="tb-spark" style="--d:${d}s;--sx:${sx}px" cx="${x}" cy="690" r="3.2" fill="#FFE08A"/>`).join("");
    return `<svg viewBox="0 0 200 ${VH}" preserveAspectRatio="xMidYMid meet" style="--rise:${rise}px" aria-hidden="true">
    <defs>
      <clipPath id="${id}b"><path d="${BODY2}"/></clipPath>
      <clipPath id="${id}i"><path d="${IN2}"/></clipPath>
      <linearGradient id="${id}g" gradientUnits="userSpaceOnUse" x1="0" y1="100" x2="0" y2="330"><stop offset="0" stop-color="#000"/><stop offset=".45" stop-color="#777"/><stop offset="1" stop-color="#fff"/></linearGradient>
      <mask id="${id}m" maskUnits="userSpaceOnUse" x="-80" y="80" width="360" height="${VH + 200}"><rect x="-80" y="80" width="360" height="${VH + 200}" fill="url(#${id}g)"/></mask>
      <radialGradient id="${id}p"><stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset=".6" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
      <radialGradient id="${id}c" cx=".45" cy=".4" r=".7"><stop offset="0" stop-color="#FFF6C0"/><stop offset=".3" stop-color="#FFC23C"/><stop offset=".62" stop-color="#FF6A12"/><stop offset=".86" stop-color="#C12A06"/><stop offset="1" stop-color="#6E1204"/></radialGradient>
      <radialGradient id="${id}w"><stop offset="0" stop-color="#FFC460" stop-opacity=".95"/><stop offset=".45" stop-color="#FF8A1E" stop-opacity=".5"/><stop offset="1" stop-color="#FF6A00" stop-opacity="0"/></radialGradient>
      <linearGradient id="IBGOLD" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF6CF"/><stop offset=".5" stop-color="#FFC233"/><stop offset="1" stop-color="#E08A00"/></linearGradient>
    </defs>
    <!-- foot -->
    <g transform="translate(0 ${D})">
      <rect x="52" y="874" width="96" height="30" rx="11" fill="#7CC8F2" stroke="${INK}" stroke-width="9"/>
      <rect x="62" y="882" width="52" height="7" rx="3.5" fill="#D9F2FF"/>
    </g>
    <!-- the ice: see-through tube and flask -->
    <path d="${BODY2}" fill="#BDE8FC" fill-opacity=".34" stroke="${INK}" stroke-width="9" stroke-linejoin="round"/>
    <g clip-path="url(#${id}b)">
      <rect x="32" y="62" width="21" height="${650 + D}" fill="#8ED3F6" opacity=".5"/>
      <rect x="147" y="62" width="21" height="${650 + D}" fill="#EAF9FF" opacity=".55"/>
      <g transform="translate(0 ${D})">
        <path d="M100 792 L6 800 L8 765 L18 728 L32 700 Z" fill="#8ED3F6" opacity=".45"/>
        <path d="M100 792 L16 838 L40 866 L72 882 L128 882 Z" fill="#62B7E8" opacity=".4"/>
        <path d="M100 792 L194 800 L192 765 L182 728 L168 700 Z" fill="#EAF9FF" opacity=".5"/>
      </g>
    </g>
    <g clip-path="url(#${id}i)">
      <!-- icy water in the flask -->
      <g transform="translate(0 ${D})">
        <path d="M0 834 Q30 824 60 834 T120 834 T200 834 L200 900 L0 900 Z" fill="#38C6E8" opacity=".85"/>
        <path d="M0 852 Q50 842 100 854 T200 850 L200 900 L0 900 Z" fill="#1FA6D6" opacity=".85"/>
        <path d="M0 834 Q30 824 60 834 T120 834 T200 834" fill="none" stroke="#E8FBFF" stroke-width="5"/>
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
    <!-- light, cracks and frost on the ice -->
    <path d="M45 100 L45 330" stroke="#fff" stroke-width="9" stroke-linecap="round" opacity=".95"/>
    <path d="M45 372 L45 ${440 + Math.max(0, D * .5)}" stroke="#fff" stroke-width="9" stroke-linecap="round" opacity=".95"/>
    <path d="M162 200 L152 226 L162 248 L150 270" fill="none" stroke="#fff" stroke-width="3.5" stroke-linejoin="round" opacity=".9"/>
    <g fill="#fff" opacity=".9"><circle cx="150" cy="118" r="3"/><circle cx="140" cy="140" r="2.4"/></g>
    <g transform="translate(0 ${D})">
      <path d="M156 520 L156 600" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".8"/>
      <path d="M28 772 L38 742" stroke="#fff" stroke-width="9" stroke-linecap="round" opacity=".95"/>
      <path d="M40 580 L50 600 L42 620" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round" opacity=".8"/>
      <g fill="#fff" opacity=".9"><circle cx="52" cy="668" r="2.6"/><circle cx="168" cy="760" r="2.6"/><circle cx="150" cy="420" r="2.4"/></g>
    </g>
    <!-- the rim, its icicles and its cap of snow -->
    <g stroke="${INK}" stroke-width="5" stroke-linejoin="round" fill="#DDF4FF">
      <path d="M16 66 L23 106 L31 66 Z"/><path d="M169 66 L177 112 L184 66 Z"/><path d="M92 68 L97 86 L103 68 Z"/>
    </g>
    <rect x="12" y="32" width="176" height="38" rx="17" fill="#A6DDF8" stroke="${INK}" stroke-width="9"/>
    <rect x="26" y="40" width="92" height="8" rx="4" fill="#EAF9FF"/>
    <path d="M10 40 C2 20 30 8 48 18 C60 2 96 0 110 14 C128 2 170 8 174 26 C190 30 190 46 180 48 L18 48 C10 48 8 44 10 40 Z" fill="#fff" stroke="${INK}" stroke-width="8" stroke-linejoin="round"/>
    <path d="M26 40 C46 34 68 40 88 36 C110 32 132 40 170 38" fill="none" stroke="#C5E2F8" stroke-width="5" stroke-linecap="round"/>
    <!-- the bowl, out front on the flask: glowing coals and a real flame over them -->
    <g transform="translate(0 ${D})">
      <circle class="tb-glow" cx="100" cy="700" r="120" fill="url(#${id}w)"/>
      <path d="M52 744 C52 790 76 812 100 812 C124 812 148 790 148 744 Z" fill="#8FD3F5" stroke="${INK}" stroke-width="9" stroke-linejoin="round"/>
      <path d="M66 760 C70 780 84 794 100 796" fill="none" stroke="#E4F7FF" stroke-width="6" stroke-linecap="round"/>
      <ellipse cx="100" cy="744" rx="50" ry="19" fill="#3E9A2B" stroke="${INK}" stroke-width="9"/>
      ${coals}
      <g class="tb-fire"><svg x="14" y="482" width="172" height="258" viewBox="0 0 128 192" preserveAspectRatio="none" overflow="hidden">
        <image class="tb-firestrip" href="assets/fx/flame.webp" x="0" y="0" width="1536" height="192" preserveAspectRatio="none"/></svg></g>
      ${sparks}
    </g>
    ${outs}
    <g class="tb-mult"><text class="ib-multtext" x="100" y="${470 + Math.round(D / 2)}" text-anchor="middle" font-family="Fredoka, 'Arial Rounded MT Bold', sans-serif" font-weight="700" font-size="92"
      stroke="${INK}" stroke-width="22" stroke-linejoin="round" fill="${INK}"> </text>
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
