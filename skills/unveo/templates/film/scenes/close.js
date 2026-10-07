/* close: { title, impact_line, links: [{label, url}], extra_line } — links typeset exactly as given */
UNVEO.scene("close", {
  build(root, d) {
    const { h, esc, words } = CORE;
    root.__im = words(h("div", "abs", null, "left:120px;top:150px;width:1560px;font:650 74px/1.12 var(--font-display);letter-spacing:-.03em"), d.impact_line || "");
    root.append(root.__im);
    root.__links = (d.links || []).slice(0, 3).map((l, i) => {
      const c = h("div", "abs card", null, `left:120px;top:${560 + i * 128}px;width:1300px;height:104px;display:flex;align-items:center;gap:36px;padding:0 40px`);
      c.innerHTML = `<div style="font:500 30px var(--font-display);color:var(--muted);width:240px;flex:none">${esc(l.label)}</div>
        <div class="mono link" style="font:500 38px 'Geist Mono';color:var(--accent);white-space:nowrap">${esc(l.url)}</div>`;
      root.append(c);
      return c;
    });
    root.__ti = h("div", "abs", `${esc(d.title || "")}${d.extra_line ? `<span style="color:var(--muted);font-weight:500"> · ${esc(d.extra_line)}</span>` : ""}`,
      "left:120px;bottom:90px;font:700 34px var(--font-display)");
    root.append(root.__ti);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, drift, E } = CORE;
    riseWords(root.__im, t, 0.15, 0.05, 0.6);
    const t0 = Math.max(1.2, dur - 4.2);  // links arrive as the voice ends, then hold
    root.__links.forEach((c, i) => rise(c, p(t, t0 + i * 0.18, .7, E.outExpo), 40));
    rise(root.__ti, p(t, t0 + 0.5, .7), 16);
  },
});
