/* title: { title, event, team } — 2.5 s opening card */
UNVEO.scene("title", {
  build(root, d) {
    const { h, esc, words } = CORE;
    root.append(h("div", "abs", null, "inset:0;background:radial-gradient(1200px 700px at 72% 30%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 70%)"));
    root.__blob = root.lastChild;
    root.__ev = h("div", "abs eyebrow", esc(d.event || ""), "left:160px;top:330px");
    root.__ti = words(h("div", "abs", null, "left:160px;top:380px;width:1600px;font:700 132px/1.02 Geist;letter-spacing:-.04em"), d.title || "");
    root.__bar = h("div", "abs", null, "left:164px;top:560px;height:8px;border-radius:8px;background:var(--accent)");
    root.__tm = h("div", "abs", esc(d.team || ""), "left:164px;top:600px;font:500 34px Geist;color:var(--muted)");
    root.append(root.__ev, root.__ti, root.__bar, root.__tm);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, drift } = CORE;
    root.__blob.style.transform = `translate(${drift(t, 30, .5)}px, ${drift(t, 18, .4, 1)}px)`;
    rise(root.__ev, p(t, 0.05, .6));
    riseWords(root.__ti, t, 0.15, 0.07, 0.7);
    root.__bar.style.width = `${p(t, 0.55, .9) * 260}px`;
    rise(root.__tm, p(t, 0.8, .6), 20);
  },
});
