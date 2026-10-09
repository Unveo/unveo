/* product-intro: { name, one_liner, screenshot?: "assets/probe.png" } — ends zooming into the app. The screenshot sits
   whole (contain) in a box with its own shape, over half the frame wide. The stack's logos belong on the close and
   built-with, not here. */
UNVEO.scene("product-intro", {
  build(root, d) {
    const { h, esc, words } = CORE;
    const col = h("div", "abs", null, "left:120px;top:0;bottom:0;width:600px;display:flex;flex-direction:column;justify-content:center;gap:24px");
    root.__eb = h("div", "eyebrow", "Introducing");
    root.__nm = words(h("div", "h", null, "font:700 var(--h1)/1.02 var(--font-display);letter-spacing:-.04em"), d.name || "");
    root.__ol = h("div", null, esc(d.one_liner || ""), "margin-top:8px;font:500 var(--body)/1.35 var(--font-body);color:var(--muted)");
    col.append(root.__eb, root.__nm, root.__ol);
    root.append(col);
    if (d.screenshot) {
      const f = h("div", "abs card", null, "overflow:hidden;transform-origin:50% 50%;padding:0");
      f.innerHTML = `<div style="height:44px;background:color-mix(in srgb, var(--ink) 7%, var(--surface));display:flex;gap:10px;align-items:center;padding:0 18px">
        <i style="width:13px;height:13px;border-radius:50%;background:#ff5f57"></i><i style="width:13px;height:13px;border-radius:50%;background:#febc2e"></i><i style="width:13px;height:13px;border-radius:50%;background:#28c840"></i></div>
        <img src="${esc(d.screenshot)}" style="display:block;width:100%;height:calc(100% - 44px);object-fit:contain;background:var(--surface)">`;
      root.append(f);
      root.__shot = f;
      root.__box = this.box(16 / 9);
    }
  },
  box(aspect) {  // 1080 px wide (56% of the frame) at the screenshot's own shape, plus the 44 px bar; centred on the right
    let w = 1080, hh = w / aspect + 44;
    if (hh > 860) { hh = 860; w = (hh - 44) * aspect; }
    return { x: 1800 - w, y: (1080 - hh) / 2, w, hh };
  },
  fit(root) {  // fonts and the image have loaded: shrink a long name to its column, give the box its real shape
    const nm = root.__nm;
    for (let k = 0; k < 30 && nm.scrollWidth > nm.clientWidth + 1; k++) nm.style.fontSize = parseFloat(getComputedStyle(nm).fontSize) * 0.94 + "px";
    const img = root.__shot && root.__shot.querySelector("img");
    if (img && img.naturalWidth) root.__box = this.box(img.naturalWidth / img.naturalHeight);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, lerp, E, drift } = CORE;
    rise(root.__eb, p(t, 0.05, .5), 14);
    riseWords(root.__nm, t, 0.12, 0.06, 0.65);
    rise(root.__ol, p(t, 0.6, .7), 24);
    if (root.__shot) {
      const b = root.__box, k = p(t, 0.2, .9, E.outExpo);
      const z = p(t, dur - 1.1, 1.1, E.ioC);  // hand-off: grow to fill the frame
      Object.assign(root.__shot.style, { left: lerp(b.x, 0, z) + "px", top: lerp(b.y, 0, z) + drift(t, 4) * (1 - z) + "px",
        width: lerp(b.w, 1920, z) + "px", height: lerp(b.hh, 1080, z) + "px",
        opacity: k, borderRadius: lerp(24, 0, z) + "px", transform: `translateY(${(1 - k) * 60}px)` });
      [root.__eb, root.__nm, root.__ol].forEach(el => { el.style.opacity = String(Math.min(Number(el.style.opacity || 1), 1 - z)); });
    }
  },
});
