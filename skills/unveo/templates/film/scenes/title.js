/* title: { title, event, team, backdrop } — 2.5 s opening card. backdrop: the hook scene's id; the title then sits
   over the hook's last frame, washed in the look's ground, so the cold open runs straight into it (docs/16 S1). */
UNVEO.scene("title", {
  build(root, d) {
    const { h, esc, words } = CORE;
    root.__ev = h("div", "abs eyebrow", esc(d.event || ""), "left:160px;top:330px");
    root.__ti = words(h("div", "abs", null, "left:160px;top:380px;width:1600px;font:700 132px/1.02 var(--font-display);letter-spacing:-.04em"), d.title || "");
    root.__bar = h("div", "abs", null, "left:164px;top:560px;height:8px;border-radius:8px;background:var(--accent)");
    root.__tm = h("div", "abs", esc(d.team || ""), "left:164px;top:600px;font:500 34px var(--font-display);color:var(--muted)");
    const motif = ((window.TIMELINE.design || {}).motifs || [])[0];  // the project's world, e.g. a parliament for MPLADS
    root.__mo = h("div", "abs", motif && window.ICON ? ICON(motif, 120) : "", "left:160px;top:190px");
    if (d.backdrop_img) {
      root.__bd = h("div", "abs", null, `inset:0;background:url(${d.backdrop_img}) center/cover`);
      root.__wash = h("div", "abs", null, "inset:0;background:var(--bg)");
      root.append(root.__bd, root.__wash);
    }
    root.append(root.__mo, root.__ev, root.__ti, root.__bar, root.__tm);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, drift, E } = CORE;
    if (root.__bd) {  // the frozen frame blurs and fades under the ground as the title comes in
      const k = p(t, 0, 0.9, E.ioC);
      root.__bd.style.filter = `blur(${k * 10}px)`;
      root.__bd.style.transform = `scale(${1.02 + 0.02 * t / dur})`;
      root.__wash.style.opacity = 0.84 * k;
    }
    root.__ti.style.transform = `translateX(${drift(t, 3, .3)}px)`;  // a barely-there drift keeps the card alive
    rise(root.__mo, p(t, 0, .7), 18);
    rise(root.__ev, p(t, 0.05, .6));
    riseWords(root.__ti, t, 0.15, 0.07, 0.7);
    root.__bar.style.width = `${p(t, 0.55, .9) * 260}px`;
    rise(root.__tm, p(t, 0.8, .6), 20);
  },
});
