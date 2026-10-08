/* close: { title, impact_line, links: [{label, url}], extra_line, credits?, built_with?: [icon names, ≤6] } — links typeset exactly as given.
   credits: who made it ("Priya Sharma · Arjun Rao"); render.py fills it from brief.header.team when the data has none. */
UNVEO.scene("close", {
  build(root, d) {
    const { h, esc, words } = CORE;
    root.__im = words(h("div", "abs", null, "left:120px;top:150px;width:1560px;font:650 calc(68px * min(var(--type-scale, 1), 1.2))/1.12 var(--font-display);letter-spacing:-.03em"), d.impact_line || "");
    root.append(root.__im);
    root.__links = (d.links || []).slice(0, 3).map((l, i) => {
      const c = h("div", "abs card", null, `left:120px;top:${560 + i * 128}px;width:1560px;height:104px;display:flex;align-items:center;gap:36px;padding:0 40px`);
      // the URL is typeset exactly as given (never cut): a long one gets a smaller size so it fits the card
      const fs = Math.min(38, Math.floor((1560 - 80 - 240 - 36) / (Math.max(1, String(l.url).length) * 0.62)));
      c.innerHTML = `<div style="font:500 30px var(--font-display);color:var(--muted);width:240px;flex:none">${esc(l.label)}</div>
        <div class="mono link" style="font:500 ${fs}px 'Geist Mono';color:var(--accent);white-space:nowrap;min-width:0">${esc(l.url)}</div>`;
      root.append(c);
      return c;
    });
    root.__ti = h("div", "abs", `${esc(d.title || "")}${d.extra_line ? `<span style="color:var(--muted);font-weight:500"> · ${esc(d.extra_line)}</span>` : ""}` +
      (d.credits ? `<span style="color:var(--muted);font-weight:500"> · Made by ${esc(d.credits)}</span>` : ""),
      "left:120px;bottom:90px;font:700 34px var(--font-display)");
    root.append(root.__ti);
    const motifs = (d.built_with || []).length ? d.built_with.slice(0, 6)  // the stack's logos, else the motifs
      : ((window.TIMELINE.design || {}).motifs || []).slice(0, 3);
    root.__mo = h("div", "abs", window.ICON ? motifs.map(m => ICON(m, (d.built_with || []).length ? 52 : 64, "var(--muted)")).join("") : "",
      "right:120px;bottom:80px;display:flex;gap:26px;opacity:.85");
    root.append(root.__mo);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, drift, E } = CORE;
    riseWords(root.__im, t, 0.15, 0.05, 0.6);
    rise(root.__mo, p(t, 0.6, .8), 14);
    const t0 = Math.max(1.2, dur - 4.2);  // links arrive as the voice ends, then hold
    root.__links.forEach((c, i) => rise(c, p(t, t0 + i * 0.18, .7, E.outExpo), 40));
    rise(root.__ti, p(t, t0 + 0.5, .7), 16);
  },
});
