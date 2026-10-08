/* context: { eyebrow?, headline, points: [≤3 strings or {text, icon}], stat?: { value, label, source } } */
UNVEO.scene("context", {
  build(root, d) { CORE_LIST.build(root, d, d.eyebrow || "The field", false); },
  draw(t, d, dur, root) { CORE_LIST.draw(t, d, dur, root); },
});
/* shared by context and problem: headline, a list of points, an optional big stat */
window.CORE_LIST = {
  build(root, d, eyebrow, isProblem) {
    const { h, esc, words, num } = CORE;
    const hasStat = d.stat && d.stat.value != null;
    root.__eb = h("div", "abs eyebrow", esc(eyebrow), "left:120px;top:120px" + (isProblem ? ";color:var(--bad)" : ""));
    root.__hl = words(h("div", "abs", null, `left:120px;top:176px;width:${hasStat ? 1020 : 1560}px;font:650 calc(70px * min(var(--type-scale, 1), 1.2))/1.08 var(--font-display);letter-spacing:-.03em`), d.headline || "");
    root.append(root.__eb, root.__hl);
    const items = d.points || d.pains || [];
    root.__items = items.slice(0, 3).map((it, i) => {
      const txt = typeof it === "string" ? it : (it || {}).text || "";
      const logo = typeof it === "object" && it && it.icon ? ICON(it.icon, 56) : "";
      const row = h("div", "abs card", null, `left:120px;top:${500 + i * 150}px;width:${hasStat ? 1020 : 1560}px;height:124px;display:flex;align-items:center;gap:30px;padding:0 40px`);
      const mark = logo || (isProblem
        ? `<div style="width:18px;height:18px;border-radius:50%;background:var(--bad);flex:none"></div>`
        : `<div class="mono" style="font:600 30px 'Geist Mono';color:var(--accent);flex:none">0${i + 1}</div>`);
      row.innerHTML = `${mark}<div style="font:500 40px/1.2 var(--font-display)">${esc(txt)}</div>`;
      root.append(row);
      return row;
    });
    if (hasStat) {
      const s = h("div", "abs", null, "left:1240px;top:430px;width:560px");
      s.innerHTML = `<div class="v" style="font:700 150px/1 var(--font-display);letter-spacing:-.04em;color:${isProblem ? "var(--bad)" : "var(--accent)"}"></div>
        <div style="margin-top:20px;font:500 36px/1.2 var(--font-display)">${esc(d.stat.label || "")}</div>
        <div class="mono" style="margin-top:18px;font:400 22px 'Geist Mono';color:var(--muted)">${esc(d.stat.source || "")}</div>`;
      root.append(s);
      root.__stat = s;
      const m = String(d.stat.value).match(/^([^\d-]*)(-?[\d.,]+)(.*)$/);
      root.__num = m ? { pre: m[1], n: Number(m[2].replace(/,/g, "")), post: m[3], dec: (m[2].split(".")[1] || "").length } : null;
      root.__raw = String(d.stat.value);
    }
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, num, beat, E } = CORE;
    rise(root.__eb, p(t, 0.05, .6), 16);
    riseWords(root.__hl, t, 0.2);
    root.__items.forEach((r, i) => rise(r, p(t, Math.max(1.0, beat(d, i + 1, dur, root.__items.length + 1)), .7, E.outExpo), 50));
    if (root.__stat) {
      const k = p(t, Math.min(dur * 0.35, 1.6), 1.4, E.outExpo);
      rise(root.__stat, Math.min(1, k * 2), 40);
      const v = root.__stat.querySelector(".v");
      v.textContent = root.__num ? root.__num.pre + num(root.__num.n * k, root.__num.dec) + root.__num.post : root.__raw;
    }
  },
};
