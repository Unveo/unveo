/* title: { title, event, team, backdrop } — the opening card: 1.4 s when silent, as long as its line when voiced. backdrop: the hook scene's id; the title then sits
   over the hook's last frame, washed in the look's ground, so the cold open runs straight into it (docs/16 S1). */
UNVEO.scene("title", {
  build(root, d) {
    const { h, esc, words } = CORE;
    // one column, centred on the frame's height: a long title wraps and everything below follows it
    const col = h("div", "abs", null, "left:160px;top:0;bottom:0;width:1600px;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;gap:26px");
    const motif = ((window.TIMELINE.design || {}).motifs || [])[0];  // the project's world, e.g. a parliament for MPLADS
    root.__mo = h("div", null, motif && window.ICON ? ICON(motif, 120) : "");
    root.__ev = h("div", "eyebrow", esc(d.event || ""));
    root.__ti = words(h("div", "h", null, "font:700 calc(var(--h1) * 1.15)/1.02 var(--font-display);letter-spacing:-.04em;text-wrap:balance"), d.title || "");
    root.__bar = h("div", null, null, "height:8px;border-radius:8px;background:var(--accent);margin-left:4px;width:0");
    root.__tm = h("div", null, esc(d.team || ""), "margin-left:4px;font:500 34px var(--font-display);color:var(--muted)");
    col.append(...[root.__mo, root.__ev, root.__ti, root.__bar, root.__tm].filter(e => e.innerHTML !== "" || e === root.__bar || e === root.__ti));
    if (d.backdrop_img) {
      root.__bd = h("div", "abs", null, `inset:0;background:url(${d.backdrop_img}) center/cover`);
      root.__wash = h("div", "abs", null, "inset:0;background:var(--bg)");
      root.append(root.__bd, root.__wash);
    }
    root.append(col);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, drift, E } = CORE;
    if (root.__bd) {  // the frozen frame blurs and fades under the ground as the title comes in
      const k = p(t, 0, 0.9, E.ioC);
      root.__bd.style.filter = `blur(${k * 10}px)`;
      root.__bd.style.transform = `scale(${1 + 0.03 * t / dur})`;  // from 1, so it lines up with the frame it fades in over
      root.__wash.style.opacity = 0.84 * k;
    }
    root.__ti.style.transform = `translateX(${drift(t, 3, .3)}px)`;  // a barely-there drift keeps the card alive
    rise(root.__mo, p(t, 0, .6), 18);  // all of it in by about 0.9 s: a silent title only lasts 1.4 s
    rise(root.__ev, p(t, 0.05, .5));
    riseWords(root.__ti, t, 0.08, 0.05, 0.6);
    root.__bar.style.width = `${p(t, 0.3, .6) * 260}px`;
    rise(root.__tm, p(t, 0.4, .5), 20);
  },
});
