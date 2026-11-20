"""High Peaks: Power Outage's intro, its three intro boxes and its HUD, unchanged (owner, 2026-11-19: "use the
poweroutage github and copy the black and white smukiez introduction, the 3 boxes, the hud and dont change these -
the front end can be reskinned").

Both games come from the same base frontend, so the pieces line up section for section. This copies them across:

* the HUD - Power Outage's whole "the bar (HUD v3)" stylesheet section in place of ours (keeping our ACTIVATE pill,
  our phone no-blur rule and our scene offset, which are not the bar), its :root paint (navy .88 bar, black
  outline, gold for what is on) and its owner-pass-4 layout (three fixed figure columns that hudfit.js shrinks to
  fit, the bonus emblem kept clear of the bar), plus hudfit.js itself. Our own white-outline HUD override goes. The
  Buy Bonus treasure chest is set the way Power Outage sets its bonus emblem (same size, bob and placement).
* the 3 boxes - Power Outage's features screen: the game's title over three cream feature cards (feature_box.webp,
  the title in the yellow band, an icon, a long description and a short one for small cards), dealt out from a
  stack, drifting, tilting under the mouse, CLICK TO PLAY under them. Its card styles come over verbatim; the cards
  say what High Peaks does (jackpot ?, FS scatter, XFS scatter). Our three picture cards and fuel-gauge bar go.
* the intro - the B&W SMUKIEZ ident was already Power Outage's (same letters, same CSS, same markup); it now also
  holds while the game loads, its thin white bar filling, as Power Outage's does (ours handed over after 3.3 s to
  the old cards, whose bar showed the loading).

Exact-string edits on frontend/index.html; every one must match once.
usage:  python tools/highpeaks/port_po_ui.py <path to zeqpz/poweroutage/frontend>
"""
import pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
if len(sys.argv) < 2:
    sys.exit(__doc__)
PO = pathlib.Path(sys.argv[1])

po = (PO / "index.html").read_text(encoding="utf-8")
s = (FE / "index.html").read_text(encoding="utf-8")


def one(text, needle, what):
    n = text.count(needle)
    if n != 1:
        sys.exit(f"{what}: expected 1 match, found {n}: {needle[:100]!r}")
    return text.index(needle)


def span(text, start, end, what):
    """[i, j): from `start` (inclusive) to the first `end` after it (exclusive)"""
    i = one(text, start, what + " start")
    j = text.index(end, i + len(start))
    return i, j


def sub(old, new, what):
    global s
    one(s, old, what)
    s = s.replace(old, new)


# ------------------------------------------------------------------------------------------------ the HUD
BAR0, BAR1 = "  /* ---------- the bar (HUD v3, 2026-11-03) ----------", "  /* ---------- from Tipsy Harvest"
pi, pj = span(po, BAR0, BAR1, "PO bar")
hi, hj = span(s, BAR0, BAR1, "HP bar")
hp_bar, po_bar = s[hi:hj], po[pi:pj]
# ours that are not the bar's look: the ACTIVATE pill, the phone's no-blur veil, the scene's offset
a = one(hp_bar, "  /* an ACTIVATE mode that is on (paintActive)", "actpill")
b = hp_bar.index("\n", one(hp_bar, "  #bonusWrap .bc.on {", "bc.on")) + 1
actpill = hp_bar[a:b]
noblur_hp = re.search(r"  /\* a phone: no blur at all.*?\n  @media [^\n]*\{\n    #bonusWrap, #infoWrap \{[^\n]*\n", hp_bar, re.S).group(0)
noblur_po = re.search(r"  @media \(max-width: 760px\), \(max-height: 520px\) \{\n    #bonusWrap, #infoWrap \{ -webkit-backdrop-filter: blur\(6px\); backdrop-filter: blur\(6px\); \}\n", po_bar).group(0)
wallx_hp = re.search(r"    :root \{ --wall-x: 6%; \}[^\n]*\n", hp_bar).group(0)
wallx_po = re.search(r"    #walltag, \.tagfx \{ top: var\(--tag-top, 24%\); \}[^\n]*\n", po_bar).group(0)
new_bar = po_bar.replace(noblur_po, noblur_hp, 1).replace(wallx_po, wallx_hp, 1)
new_bar = new_bar.replace(BAR1, "") + actpill
s = s[:hi] + new_bar + s[hj:]

# our white-outline HUD override goes; Power Outage's own late HUD rules come in its place
HUD0, HUD1 = "  /* ---------- High Peaks HUD (owner, 2026-11-18", "  /* ---------- High Peaks Buy Bonus"
hi, hj = span(s, HUD0, HUD1, "HP HUD override")
po_late = po[one(po, '  .hud .bonusbtn.up { bottom: calc(100% + 2px); }', "PO .up"):]
po_late = po_late[:po_late.index("  /* ---- owner pass 5 (2026-11-19) ---- */")]
s = s[:hi] + """  /* ---------- the HUD: Power Outage's, unchanged (owner, 2026-11-19: "copy ... the hud and dont change these") ----------
     zeqpz/poweroutage's last word on the bar's paint (its :root, after the bar section above) and its owner-pass-4
     layout: hudfit.js keeps the bonus emblem off the bar (.up / .sm) and shrinks a long figure to its fixed column */
  :root { --hud-on: #FFD54A; --hud-fill: rgba(16, 22, 48, .88); --hud-soft: #c9d4ee; --hud-ink: #fbf8ee; }
  #balance.up { color: #FFD54A; }   /* (Power Outage's --fs-green, which is its gold; ours is a red) */
  /* the pop-ups' info panel keeps its own dark paint, so its text stays easy to read */
  html .infopanel { background: rgba(8, 8, 10, .9) !important; border-color: rgba(255, 255, 255, .6) !important; }
""" + po_late + "\n" + s[hj:]

# the Buy Bonus chest, set as Power Outage sets its emblem (176 px, the gentle bob, nothing behind or round it)
CH0, CH1 = "  /* ---------- High Peaks Buy Bonus: the treasure chest", "  /* ---------- High Peaks board:"
hi, hj = span(s, CH0, CH1, "HP chest")
s = s[:hi] + """  /* ---------- High Peaks Buy Bonus: the treasure chest of buds (art/highpeaks/raw/bonus_btn.png), in Power Outage's
     emblem slot: the same size, bob and hover, only its picture (hudfit.js moves it off the bar on a narrow window) ---------- */
  .bonusbtn, .bonusbtn:hover, .bonusbtn:active, .bonusbtn:focus, .bonusbtn:focus-visible, .bonusbtn:disabled {
    background: none !important; background-color: transparent !important; border: 0 !important; outline: 0 !important;
    box-shadow: none !important; -webkit-tap-highlight-color: transparent; appearance: none; -webkit-appearance: none; }
  .bonusbtn::before { content: none !important; }
  .bonusbtn { width: calc(176px * var(--hs, 1)); height: calc(176px * var(--hs, 1)); overflow: visible !important;
    display: block; border-radius: 0; isolation: auto; animation: bonusFloat 9s ease-in-out infinite; transition: scale .2s ease; }
  .bonusbtn::after { content: ""; position: absolute; inset: 0; top: 0; bottom: 0; left: 0; width: auto; z-index: 1; transform: none;
    background: url("assets/bonus_btn.webp") center / contain no-repeat; filter: none;
    animation: bonusIconBob 2.6s ease-in-out infinite; }
  .bonusbtn .bb1, .bonusbtn .bb2 { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
  @keyframes bonusFloat {
    0%, 100% { translate: 0 0; rotate: 0deg; } 25% { translate: 1px -1.5px; rotate: .25deg; }
    50% { translate: -.5px 1px; rotate: -.2deg; } 75% { translate: -1.5px -.5px; rotate: .15deg; }
  }
  @keyframes bonusIconBob { 0%, 100% { translate: 0 0; scale: 1; } 50% { translate: 0 -3%; scale: 1.04; } }
  .bonusbtn:hover:not(:disabled) { scale: 1.04; filter: none; }
  .bonusbtn:hover:not(:disabled)::after { filter: brightness(1.14); }
  @media (prefers-reduced-motion: reduce) { .bonusbtn, .bonusbtn::after { animation: none !important; } }

""" + s[hj:]

sub('<script src="boardgl.js"></script>\n', '<script src="boardgl.js"></script>\n<script src="hudfit.js"></script>\n', "hudfit tag")
# the bar's size on screen: Power Outage's (fitToScreen raises it to .72 of full HD wherever the page fits smaller; we
# had moved that to .8 for Falcos's taller chrome frame)
sub("""    // .72 was the fit under which the bar grows back; Falcos's chrome board frame makes the page ~11% taller,
    // so the threshold moves with it (.72 x 1.11) and the bar keeps the size on screen it had before
    let hs = Math.min(1.5, Math.max(1, .8 / fit));""", """    let hs = Math.min(1.5, Math.max(1, .72 / fit));   // (Power Outage's: the bar lands at its size on screen)""", "hud scale")
# the bar's last blues (the WIN figure's glow, its count-up, a chosen autoplay count) in Power Outage's gold
for old, new, what in [
        ("    text-shadow: 0 2px 0 rgba(0, 0, 0, .35), 0 0 14px rgba(79, 155, 255, .4);", "    text-shadow: 0 2px 0 rgba(0, 0, 0, .35), 0 0 14px rgba(255, 213, 74, .4);", "win glow"),
        ('      { color: "#fff", textShadow: "0 2px 0 rgba(0, 0, 0, .35), 0 0 14px rgba(79, 155, 255, .4)" },',
         '      { color: "#fff", textShadow: "0 2px 0 rgba(0, 0, 0, .35), 0 0 14px rgba(255, 213, 74, .4)" },', "win count glow"),
        ("  .autoopts button.on, .autoopts button.on:hover:not(:disabled) { border-color: var(--hud-on); background: rgba(79, 155, 255, .14); color: #fff; }",
         "  .autoopts button.on, .autoopts button.on:hover:not(:disabled) { border-color: var(--hud-on); background: rgba(255, 213, 74, .14); color: #fff; }", "auto chip")]:
    sub(old, new, what)
# an empty WIN reads in the currency ($0.00), as Power Outage's bar has it
sub("""  $("betVal").textContent = fmt(shown);
  fitFigure($("betVal"), fmt(shown));
  const st = $("betVal").closest(".hudstat");""", """  $("betVal").textContent = fmt(shown);
  fitFigure($("betVal"), fmt(shown));
  if (!state.playing && !(shownWin > 0)) $("roundWin").textContent = fmt(0);   // an empty WIN, in the currency
  const st = $("betVal").closest(".hudstat");""", "empty win")

# ------------------------------------------------------------------------------------------------ the 3 boxes (CSS)
FS0, FS1 = "  /* ---------- features screen ---------- */", "\n  .info {\n"
pi, pj = span(po, FS0, FS1, "PO features css")
hi, hj = span(s, FS0, FS1, "HP features css")
po_feat = po[pi:pj]
# (Power Outage's characters and wall tag fade with the game there; High Peaks has neither)
for old, new in [("""  body.features-fade #app, body.features-fade .charfx, body.features-fade .charshadow { transition: opacity .7s ease; }
  body.features-up #app, body.features-up .charfx, body.features-up .charshadow { opacity: 0; }
  /* and the wall's SMUKIEZ tag (its neon, drips and light with it) steps out too: the title stands
     over the plates (owner, 2026-11-08); it fades back in with the game */
  body.features-fade #walltag, body.features-fade .tagfx, body.features-fade #walllight { transition: opacity .7s ease, visibility .7s; }
  body.features-up #walltag, body.features-up .tagfx { opacity: 0 !important; }
  body.features-up #walllight { visibility: hidden; }
""", """  body.features-fade #app { transition: opacity .7s ease; }
  body.features-up #app { opacity: 0; }
"""), ("    body.features-fade #app, body.features-fade .charfx, .features { transition: none !important; }\n",
       "    body.features-fade #app, .features { transition: none !important; }\n")]:
    one(po_feat, old, "PO-only features lines")
    po_feat = po_feat.replace(old, new)
# Power Outage's review fixes for the cards (its later stylesheet): cream cards, navy lettering, the title in the band,
# the short description on small cards
r0 = one(po, "  /* ---- Power Outage review fixes (2026-11-18) ---- */", "PO review fixes")
r1 = po.index("  /* (owner, 2026-11-18) the multiplier values stay in the background", r0)
po_review = po[r0:r1]
s = s[:hi] + po_feat + "\n" + po_review + """  /* High Peaks: every face on Power Outage's cards is Fredoka (its other font names all point at Fredoka); ours
     are real fonts, so the cards ask for Fredoka by name */
  .features .fcont { font-family: "Fredoka", var(--disp); }
  /* the jackpot card: the ? coin, with the four prizes going round under its ? in their own colours */
  .fbox .fjp {
    position: absolute; left: -8%; right: -8%; bottom: -4%; display: flex; flex-direction: column; align-items: center;
    font-family: "Fredoka", var(--num); font-weight: 700; line-height: .95; color: var(--heat, #FFD23F);
    -webkit-text-stroke: 1.15cqw #141B33; paint-order: stroke fill; text-shadow: 0 .7cqw 0 #141B33;
  }
  .fbox .fjp .jl { font-size: 5.6cqw; letter-spacing: .12em; }
  .fbox .fjp .jv { font-size: 9.5cqw; letter-spacing: .02em; }
  .fbox .fjp.tick { animation: fmultpop .38s cubic-bezier(.2,.9,.3,1.3); }
  @media (prefers-reduced-motion: reduce) { .fbox .fjp { animation: none !important; } }
""" + s[hj:]

# ------------------------------------------------------------------------------------------------ the 3 boxes (JS)
JS0, JS1 = "/* ---------- features screen ---------- */\n// Before the game shows:", "/* ---------- bonus intro ---------- */"
hi, hj = span(s, JS0, JS1, "HP features js")
hp_js = s[hi:hj]
# ours: the cell multiplier's table and its cycle (the game information's tiles run it), and tiltPlates (the buy cards)
keep0 = one(hp_js, "const FEATURE_VALUES = ", "FEATURE_VALUES")
keep1 = one(hp_js, 'tiltPlates(document.querySelectorAll(".bonuscard"));', "tiltPlates call")
keep1 = hp_js.index("\n", keep1) + 1
kept = hp_js[keep0:keep1]
# Power Outage's: the deal from a stack (fanPlates), decodeIn and runFeatures, with High Peaks's cards
p0 = one(po, "function fanPlates(wrap) {", "PO fanPlates")
p0 = po.rindex("// The intro plates arrive as one stack", 0, p0)
p1 = one(po, "// The plates in 3D. Each one carries", "PO tilt comment")
fan = po[p0:p1]
d0 = one(po, "// (mobile) every picture under `root` decoded", "PO decodeIn")
d1 = one(po, "function runFeatures() {", "PO runFeatures")
decode = po[d0:d1]
r0 = d1
r1 = one(po, "runFeatures();\nintroDone = introDone.then(() => featuresDone);", "PO runFeatures end")
run = po[r0:r1]
# High Peaks's cards in Power Outage's boxes: the jackpot ?, the FS scatter (PEAK Token), the XFS scatter (Black
# Diamond Token)
po_cards0 = one(run, "  wrap.innerHTML =\n", "PO cards")
po_cards1 = one(run, "  document.body.appendChild(wrap);\n", "PO cards end")
run = run[:po_cards0] + """  wrap.innerHTML =
    `<img class="ftitle" src="assets/logo.webp" alt="${T("High Peaks")}" draggable="false">` +
    `<div class="fboxes">` +
      box(`<img src="assets/jackpot/q.webp" alt="?" draggable="false"><div class="fjp" id="featJp" aria-hidden="true"><span class="jl"></span><span class="jv"></span></div>`,
        T("Jackpot"),
        T(`A <b>?</b> can drop onto the board on any spin, and more often in the bonuses. When the spin has played out, the jackpot bar spins and stops on <b>MINI x10</b>, <b>MINOR x50</b>, <b>MAJOR x250</b> or <b>GRAND x2,500</b> the bet.`),
        T(`A <b>?</b> spins the jackpot bar: <b>MINI</b> to <b>GRAND</b>, up to <b>x2,500</b>.`)) +
      box(`<img src="${SYM.BS.img}" alt="${T("FS scatter")}" draggable="false">`,
        T("FS scatter \\u00b7 Bonus"),
        T(`<b>3</b> anywhere start <b>STASH</b>: sticky Buds worth <b>x0.2</b> to <b>x500</b> pile up while the spin gauge lasts. <b>4</b> or more start <b>FRESH POWDER</b>: <b>10</b> free spins where every cell multiplier stays for the whole bonus.`),
        T(`<b>3</b> start <b>STASH</b>, <b>4</b> or more <b>FRESH POWDER</b>: <b>10</b> free spins, sticky multipliers.`)) +
      box(`<img src="${SYM.DS.img}" alt="${T("XFS scatter")}" draggable="false">`,
        T("XFS scatter \\u00b7 Extreme"),
        T(`<b>3</b> anywhere - or <b>3</b> or more tokens of both kinds together - start <b>BLACK DIAMOND</b>: <b>10</b> free spins with sticky cell multipliers, every cell starting at <b>x4</b>, and Snow Cannons landing far more often.`),
        T(`<b>3</b> start <b>BLACK DIAMOND</b>: <b>10</b> free spins, every cell from <b>x4</b>.`)) +
    `</div>` +
    `<div class="fcont"><span class="fhit"><span class="ftxt">${T("Click to play")}</span></span></div>`;
""" + run[po_cards1:]
run = run.replace("""  // the Multi's value climbs the table and warms with it, round and round
  const stopMult = cycleMult(wrap.querySelector("#featMult"));
""", """  // the four jackpots go round under the ?, each in its own colour (the jackpot bar's)
  const stopMult = cycleJackpots(wrap.querySelector("#featJp"));
""")
if "cycleJackpots" not in run:
    sys.exit("PO runFeatures: the Multi cycle line moved")
cycle_jp = """// The jackpot card's prizes, round and round under the ?, each in the jackpot bar's colour. Returns a stop.
const FEATURE_JACKPOTS = [["MINI", 10, "#7CFF4F"], ["MINOR", 50, "#4FC3FF"], ["MAJOR", 250, "#C46BFF"], ["GRAND", 2500, "#FFD23F"]];
function cycleJackpots(face) {
  if (!face) return () => {};
  let i = 0;
  const show = () => {
    const [name, mult, colour] = FEATURE_JACKPOTS[i];
    face.querySelector(".jl").textContent = T(name);
    face.querySelector(".jv").textContent = "x" + mult.toLocaleString("en-US");
    face.style.setProperty("--heat", colour);
  };
  show();
  const id = setInterval(() => {
    i = (i + 1) % FEATURE_JACKPOTS.length;
    show();
    face.classList.remove("tick"); restyle(face); face.classList.add("tick");
  }, REDUCED_MOTION ? 1600 : 1100);
  return () => clearInterval(id);
}
"""
new_js = ("""/* ---------- features screen ---------- */
// Before the game shows (zeqpz/poweroutage's intro boxes, 2026-11-19): the game's title over three cards and nothing
// else - no board, no bar. The jackpot ?, the FS scatter and the XFS scatter, and what each one does. They are dealt
// out from a stack, drift, and the one under the mouse tips toward it. It fades up as the opening screen goes (once
// the game has loaded), and a click (or Space / Enter) fades the cards out and the game in. A replay is a viewer, so
// it never shows this.
""" + kept + fan + decode + cycle_jp + run +
          "runFeatures();\nintroDone = introDone.then(() => featuresDone);   // a resumed round waits for this screen too\n"
          "introDone.then(() => setTimeout(releaseGonePics, 1500));   // its cards are gone for good: let their pictures go\n\n")
s = s[:hi] + new_js + s[hj:]
# the features screen's pictures are let go once it is gone (its own selectors now)
sub("if (sels.length && sels.every(s => /\\.lcard|\\.lbar|\\.features/.test(s))) return true;",
    "if (sels.length && sels.every(s => /\\.fbox|\\.features/.test(s))) return true;", "releaseGonePics")

# ------------------------------------------------------------------------------------------------ the intro
# it holds until the game has loaded, its own thin bar filling (Power Outage's); the cards come up after it
sub("""    after(600, finish);
  } else {
    // film grain""", """    loaded.then(() => after(600, finish));
  } else {
    // film grain""", "intro reduced")
sub("    ready.then(() => after(Math.max(0, IDENT - (performance.now() - beganAt)), finish));",
    "    Promise.all([loaded, ready]).then(() => after(Math.max(0, IDENT - (performance.now() - beganAt)), finish));", "intro hold")

(FE / "index.html").write_text(s, encoding="utf-8", newline="\n")

# ------------------------------------------------------------------------------------------------ files
shutil.copy2(PO / "hudfit.js", FE / "hudfit.js")
# High Peaks's log frame is wider than Power Outage's steel one: on a small window (800x600) neither the corner nor the
# bar's shoulder is clear of both the bar and the frame, and the bar's tabs would cover the chest. One more step, a
# size smaller (.xs), keeps Power Outage's rule - the bar never covers the emblem.
hf = (FE / "hudfit.js").read_text(encoding="utf-8")
for old, new in [('for (const cls of [[], ["up"], ["up", "sm"], ["sm"]]) {\n        bonus.classList.remove("up", "sm");',
                  'for (const cls of [[], ["up"], ["up", "sm"], ["sm"], ["xs"], ["up", "xs"]]) {   // (High Peaks: .xs for its wider frame)\n        bonus.classList.remove("up", "sm", "xs");'),
                 ('      bonus.classList.remove("up", "sm");                     // nowhere is clear',
                  '      bonus.classList.remove("up", "sm", "xs");               // nowhere is clear')]:
    if hf.count(old) != 1:
        sys.exit("hudfit.js: " + old[:60])
    hf = hf.replace(old, new)
(FE / "hudfit.js").write_text(hf, encoding="utf-8", newline="\n")
s2 = (FE / "index.html").read_text(encoding="utf-8")
anchor = "  .hud .bonusbtn.sm { width: calc(118px * var(--hs, 1)); height: calc(118px * var(--hs, 1)); }\n"
if s2.count(anchor) != 1:
    sys.exit("index.html: .sm anchor")
s2 = s2.replace(anchor, anchor + "  .hud .bonusbtn.xs { width: calc(84px * var(--hs, 1)); height: calc(84px * var(--hs, 1)); }   /* (High Peaks: see hudfit.js) */\n")
(FE / "index.html").write_text(s2, encoding="utf-8", newline="\n")
shutil.copy2(PO / "assets" / "feature_box.webp", FE / "assets" / "feature_box.webp")
old = FE / "assets" / "load"   # the old picture cards and the fuel-gauge bar: nothing draws them now
if old.exists():
    shutil.rmtree(old)
print("ported: HUD, intro boxes, intro hold")
