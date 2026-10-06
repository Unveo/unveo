/* placeholder: { shot_id, what_to_record } — stands in for a clip that hasn't been recorded */
UNVEO.scene("placeholder", {
  build(root, d) {
    const { h, esc } = CORE;
    const c = h("div", "abs", null, "left:360px;top:300px;width:1200px;height:480px;border:4px dashed var(--muted);border-radius:36px;display:flex;flex-direction:column;justify-content:center;padding:0 80px;gap:24px");
    c.innerHTML = `<div class="eyebrow">Recording needed · ${esc(d.shot_id || "")}</div>
      <div style="font:600 52px/1.2 Geist">${esc(d.what_to_record || "This part of the demo is recorded by the team.")}</div>`;
    root.append(c);
    root.__c = c;
  },
  draw(t, d, dur, root) { CORE.rise(root.__c, CORE.p(t, 0, .6), 20); },
});
