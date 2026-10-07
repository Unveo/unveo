/* product-intro: { name, one_liner, screenshot?: "assets/probe.png" } — ends zooming into the app */
UNVEO.scene("product-intro", {
  build(root, d) {
    const { h, esc, words } = CORE;
    const col = h("div", "abs", null, "left:120px;top:0;bottom:0;width:760px;display:flex;flex-direction:column;justify-content:center;gap:24px");
    root.__eb = h("div", "eyebrow", "Introducing");
    root.__nm = words(h("div", null, null, "font:700 104px/1.02 var(--font-display);letter-spacing:-.04em"), d.name || "");
    root.__ol = h("div", null, esc(d.one_liner || ""), "margin-top:8px;font:500 40px/1.3 var(--font-display);color:var(--muted)");
    col.append(root.__eb, root.__nm, root.__ol);
    root.append(col);
    if (d.screenshot) {
      const f = h("div", "abs card", null, "left:930px;top:200px;width:880px;height:560px;overflow:hidden;transform-origin:50% 50%");
      f.innerHTML = `<div style="height:44px;background:color-mix(in srgb, var(--ink) 7%, var(--surface));display:flex;gap:10px;align-items:center;padding:0 18px">
        <i style="width:13px;height:13px;border-radius:50%;background:#ff5f57"></i><i style="width:13px;height:13px;border-radius:50%;background:#febc2e"></i><i style="width:13px;height:13px;border-radius:50%;background:#28c840"></i></div>
        <img src="${esc(d.screenshot)}" style="width:100%;height:calc(100% - 44px);object-fit:cover;object-position:top">`;
      root.append(f);
      root.__shot = f;
    }
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, lerp, E, drift } = CORE;
    rise(root.__eb, p(t, 0.05, .5), 14);
    riseWords(root.__nm, t, 0.15, 0.06, 0.65);
    rise(root.__ol, p(t, 0.7, .7), 24);
    if (root.__shot) {
      const k = p(t, 0.4, .9, E.outExpo);
      const z = p(t, dur - 1.1, 1.1, E.ioC);  // hand-off: grow to fill the frame
      const x = lerp(930, 0, z), y = lerp(200, 0, z), w = lerp(880, 1920, z), hh = lerp(560, 1080, z);
      Object.assign(root.__shot.style, { left: x + "px", top: y + drift(t, 4) * (1 - z) + "px", width: w + "px", height: hh + "px",
        opacity: k, borderRadius: lerp(28, 0, z) + "px", transform: `translateY(${(1 - k) * 60}px)` });
      [root.__eb, root.__nm, root.__ol].forEach(el => { el.style.opacity = String(Math.min(Number(el.style.opacity || 1), 1 - z)); });
    }
  },
});
