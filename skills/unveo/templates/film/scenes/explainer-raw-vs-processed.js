/* raw-vs-processed (docs/07 §3.4): { title, raw:{label,columns,rows}, steps:[…], processed:{label,columns,rows}, example_data } */
UNVEO.scene("explainer-raw-vs-processed", {
  build(root, d) {
    const { h, esc, question, exampleTag } = CORE;
    root.__q = question(root, d.title);
    exampleTag(root, d);
    const table = (tb, x, clean) => {
      const cols = (tb.columns || []).slice(0, 4), rows = (tb.rows || []).slice(0, 3);
      const el = h("div", "abs card", null, `left:${x}px;top:330px;width:700px;padding:30px;transform-origin:50% 50%`);
      el.innerHTML = `<div class="eyebrow" style="font-size:22px;${clean ? "" : "color:var(--muted)"}">${esc(tb.label || "")}</div>
        <table style="margin-top:18px;width:100%;border-collapse:collapse;font:400 23px 'Geist Mono'">
        <tr>${cols.map(c => `<th style="text-align:left;padding:10px 8px;color:var(--muted);font-weight:500;border-bottom:2px solid color-mix(in srgb, var(--muted) 30%, transparent)">${esc(c)}</th>`).join("")}</tr>
        ${rows.map(r => `<tr>${cols.map((_, i) => `<td class="${clean ? "cell" : ""}" style="padding:12px 8px;border-radius:8px">${esc(r[i])}</td>`).join("")}</tr>`).join("")}</table>`;
      root.append(el);
      return el;
    };
    root.__raw = table(d.raw || {}, 120, false);
    root.__cln = table(d.processed || {}, 1100, true);
    root.__steps = (d.steps || []).slice(0, 4).map((s, i) => {
      const c = h("div", "abs", esc(s), `left:840px;top:${370 + i * 92}px;width:240px;padding:14px 18px;border-radius:14px;background:var(--ink);color:var(--bg);font:500 22px/1.2 var(--font-display);text-align:center`);
      root.append(c);
      return c;
    });
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, beat, E, drift } = CORE;
    const b = i => beat(d, i, dur, 3);
    riseWords(root.__q, t, 0.1);
    const rk = p(t, b(1), .7, E.outExpo);
    rise(root.__raw, rk, 40);
    root.__raw.style.transform += ` rotate(${-1.4 + drift(t, .3)}deg)`;
    root.__raw.style.filter = `saturate(${1 - 0.6 * rk})`;
    root.__steps.forEach((s, i) => rise(s, p(t, b(1) + 0.8 + i * 0.45, .5, E.outBack), 20));
    rise(root.__cln, p(t, b(2), .8, E.outExpo), 40);
    root.__cln.querySelectorAll(".cell").forEach((c, i) => {
      const k = p(t, b(2) + 0.5 + i * 0.05, .4) * (1 - p(t, b(2) + 1.6 + i * 0.05, .6));
      c.style.background = `color-mix(in srgb, var(--accent2) ${Math.round(28 * k)}%, transparent)`;
    });
  },
});
