/* placeholder: { shot_id, what_to_record } — stands in for a clip that hasn't been recorded */
UNVEO.scene("placeholder", {
  build(root, d) {
    const { h, esc } = CORE;
    const c = h("div", "abs", null, "left:360px;top:50%;width:1200px;transform:translateY(-50%);border:4px dashed var(--muted);border-radius:36px;display:flex;flex-direction:column;gap:24px;padding:64px 80px");
    c.innerHTML = `<div class="eyebrow">Recording needed · ${esc(d.shot_id || "")}</div>
      <div style="font:600 46px/1.25 Geist">${esc(d.what_to_record || "This part of the demo is recorded by the team.")}</div>`;
    root.append(c);
    root.__c = c;
  },
  draw(t, d, dur, root) {
    const k = CORE.p(t, 0, .6);
    root.__c.style.opacity = Math.min(1, k * 1.4);
    root.__c.style.transform = `translateY(calc(-50% + ${(1 - k) * 20}px))`;  // keep the vertical centring
  },
});
