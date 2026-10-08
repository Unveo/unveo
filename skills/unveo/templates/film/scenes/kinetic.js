/* kinetic: { text, word_times? } — big type, one or two words at a time, cut on the voice's words (docs/16 MO1, S3).
   For 2–3 s punch scenes between longer ones, and hooks. render.py fills word_times from the voice; **a word** gets the motion language's emphasis. */
UNVEO.scene("kinetic", {
  build(root, d) {
    const { h, esc } = CORE;
    const marked = String(d.text || "").replace(/\*\*(.+?)\*\*/, (_, g) => g.split(/\s+/).map(w => "\u0001" + w).join(" ")).replace(/\*\*/g, "");
    const toks = marked.split(/\s+/).filter(Boolean), chunks = [];
    for (let i = 0; i < toks.length;) {  // two short words share a beat; a long one stands alone
      const two = i + 1 < toks.length && toks[i].length + toks[i + 1].length <= 11 && !/[.,!?:;]$/.test(toks[i]);
      chunks.push({ i, words: toks.slice(i, i + (two ? 2 : 1)) });
      i += two ? 2 : 1;
    }
    root.__chunks = chunks.map(c => {
      const el = h("div", "abs", c.words.map(w => w[0] === "\u0001" ? `<span class="em">${esc(w.slice(1))}</span>` : esc(w)).join(" "),
        "left:120px;right:120px;top:0;bottom:0;display:flex;align-items:center;justify-content:center;text-align:center;" +
        "font:800 calc(200px * min(var(--type-scale, 1), 1.3))/1 var(--font-display);letter-spacing:-.045em;opacity:0;white-space:nowrap");
      root.append(el);
      return { el, i: c.i };
    });
    root.__n = toks.length;
  },
  fit(root) {  // a chunk too wide for the frame shrinks until it fits
    root.__chunks.forEach(({ el }) => {
      for (let k = 0; k < 30 && el.scrollWidth > el.clientWidth + 1; k++) el.style.fontSize = parseFloat(getComputedStyle(el).fontSize) * 0.93 + "px";
    });
  },
  draw(t, d, dur, root) {
    const { p, E, clamp } = CORE;
    const wt = d.word_times && d.word_times.length === root.__n ? d.word_times : null;
    const at = c => (wt ? wt[c.i] : 0.15 + (c.i / Math.max(1, root.__n)) * dur * 0.85);
    root.__chunks.forEach((c, j) => {
      const t0 = at(c), t1 = j + 1 < root.__chunks.length ? at(root.__chunks[j + 1]) : dur + 1;
      const on = t >= t0 && t < t1, k = p(t, t0, 0.22, E.outExpo);
      c.el.style.opacity = on ? clamp(k * 4) : 0;
      c.el.style.transform = `scale(${1.14 - 0.14 * k})`;
    });
  },
});
