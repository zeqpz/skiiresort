// Power Outage: the bar's three figures always fit their slots (owner pass 4, 2026-11-18: "the win amount overlaps
// the balance ... the sizing always stays the same, the win always stays within the bars, and the size decreases when
// the amount goes up").
//
// The bar's columns are fixed in the stylesheet (BALANCE | WIN | BET: the WIN slot one set width between its
// dividers, the other two sharing the rest), so nothing moves or grows whatever the figures are. This sets each
// figure's size: at its own size while it fits, stepped down just enough to fit when it doesn't (never under 38%).
// A figure is only measured again when its number of characters changes or the bar is resized - a win counting up
// keeps its length for many frames (the digits are tabular), so a count costs no layout.
(function () {
  "use strict";
  const ids = ["balance", "roundWin", "betVal"];
  const els = ids.map(id => document.getElementById(id)).filter(Boolean);
  const bar = document.querySelector(".hudbar");
  if (!els.length || !bar) return;
  const key = new Map();
  const slotWidth = el => {
    const slot = el.closest(".hudstat");
    if (!slot) return 0;
    const cs = getComputedStyle(slot);
    return slot.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  };
  const fitOne = (el, force) => {
    const k = el.textContent.length + "|" + bar.clientWidth;
    if (!force && key.get(el) === k) return;
    key.set(el, k);
    el.style.fontSize = "";                                   // back to the stylesheet's size, then measure
    // the WIN keeps room for its 1.1 pop, the balance and the bet for their 1.05 one (High Peaks, 2026-11-19: a long
    // balance's pop ran out of its column and was cut off)
    const avail = slotWidth(el) * (el.id === "roundWin" ? .9 : .94);
    const w = el.scrollWidth;
    if (avail > 8 && w > avail) {
      const base = parseFloat(getComputedStyle(el).fontSize);
      el.style.fontSize = Math.max(base * .38, Math.floor(base * avail / w * 10) / 10) + "px";
    }
  };
  const fitAll = force => els.forEach(el => fitOne(el, force));
  const mo = new MutationObserver(recs => { for (const r of recs) { const el = r.target.nodeType === 3 ? r.target.parentElement : r.target; const v = el && el.closest && el.closest("#balance, #roundWin, #betVal"); if (v) fitOne(v); } });
  els.forEach(el => mo.observe(el, { childList: true, characterData: true, subtree: true }));
  new ResizeObserver(() => fitAll(true)).observe(bar);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => fitAll(true));
  fitAll(true);
  window.__hudfit = () => fitAll(true);                       // (QA)

  // The bonus emblem is never under the bar. It sits in the corner beside the bar; on a window narrow enough for
  // the bar to reach it (the bar's dark buttons then lay over it like a black box round it) it moves up onto the
  // bar's left shoulder (.up), and a size smaller there if the frame's corner is in the way (.sm).
  const bonus = document.getElementById("bonusBtn"), hudframe = document.querySelector(".hudframe"), board = document.getElementById("board");
  if (bonus && hudframe) {
    const hits = (a, b, pad) => a.left < b.right - pad && a.right > b.left + pad && a.top < b.bottom - pad && a.bottom > b.top + pad;
    const frameSolid = () => {                                // the frame's steel round the board (not its loose cables)
      if (!board) return null;
      const r = board.getBoundingClientRect();
      return { left: r.left - r.width * .07, right: r.right + r.width * .07, top: r.top - r.height * .1, bottom: r.bottom + r.height * .115 };
    };
    const clear = () => {
      const b = bonus.getBoundingClientRect(), f = frameSolid();
      return b.width > 4 && !hits(b, hudframe.getBoundingClientRect(), 3) && !(f && hits(b, f, 3)) && b.left >= -2 && b.top >= -2;
    };
    let queued = false;
    const place = () => {
      queued = false;
      for (const cls of [[], ["up"], ["up", "sm"], ["sm"], ["xs"], ["up", "xs"]]) {   // (High Peaks: .xs for its wider frame)
        bonus.classList.remove("up", "sm", "xs");
        bonus.classList.add(...cls);
        if (clear()) return;
      }
      bonus.classList.remove("up", "sm", "xs");               // nowhere is clear (a tiny window): where it always was
    };
    const ask = () => { if (!queued) { queued = true; requestAnimationFrame(place); } };
    new ResizeObserver(ask).observe(hudframe);
    if (board) new ResizeObserver(ask).observe(board);
    addEventListener("resize", ask);
    new MutationObserver(ask).observe(document.documentElement, { attributes: true, attributeFilter: ["style"] });   // --fit, --hs
    ask();
  }
})();
