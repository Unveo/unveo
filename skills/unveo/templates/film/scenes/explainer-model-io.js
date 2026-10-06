/* model-io (docs/07 §3.3): { title, input:{kind,label,example}, preprocess:[…], model:{name,where,label}, output:{label,example,confidence,alternatives:[{label,p}]}, example_data } */
UNVEO.scene("explainer-model-io", {
  build(root, d) {
    const { h, esc, question, exampleTag } = CORE;
    root.__q = question(root, d.title);
    exampleTag(root, d);
    const i = d.input || {}, m = d.model || {}, o = d.output || {};
    root.__in = h("div", "abs card", null, "left:120px;top:330px;width:560px;height:330px;padding:34px;display:flex;flex-direction:column;gap:16px");
    root.__in.innerHTML = `<div class="eyebrow" style="font-size:22px">Input · ${esc(i.kind || "")}</div>
      <div style="font:550 32px Geist">${esc(i.label || "")}</div>
      <div class="mono" style="font:400 26px/1.4 'Geist Mono';color:var(--muted);overflow:hidden">${esc(i.example == null ? "" : typeof i.example === "object" ? JSON.stringify(i.example) : i.example)}</div>`;
    root.__pre = (d.preprocess || []).slice(0, 4).map((s, k) => {
      const c = h("div", "abs mono", esc(s), `left:${120 + k * 145}px;top:690px;padding:10px 16px;border-radius:12px;background:var(--surface);font:500 20px 'Geist Mono';color:var(--muted)`);
      root.append(c);
      return c;
    });
    root.__m = h("div", "abs", null, "left:780px;top:360px;width:360px;height:280px;border-radius:36px;background:var(--ink);color:var(--bg);display:flex;flex-direction:column;justify-content:center;align-items:center;gap:14px;text-align:center;padding:24px");
    root.__m.innerHTML = `<div style="font:650 40px/1.1 Geist">${esc(m.label || "Model")}</div>
      <div class="mono" style="font:400 21px/1.3 'Geist Mono';opacity:.75">${esc(m.name || "")}</div>
      <div class="mono" style="font:500 19px 'Geist Mono';opacity:.6">${esc(m.where === "api" ? "via API" : m.where || "")}</div>`;
    root.__ring = h("div", "abs", null, "left:760px;top:340px;width:400px;height:320px;border-radius:44px;border:4px solid var(--accent)");
    root.__out = h("div", "abs card", null, "left:1240px;top:330px;width:560px;height:330px;padding:34px;display:flex;flex-direction:column;gap:14px");
    const alts = (o.alternatives || []).slice(0, 2).map(a => `<div class="mono" style="font:400 22px 'Geist Mono';color:var(--muted)">${esc(a.label)} · ${esc(a.p)}</div>`).join("");
    root.__out.innerHTML = `<div class="eyebrow" style="font-size:22px">Output</div>
      <div style="font:550 30px Geist">${esc(o.label || "")}</div>
      <div style="font:700 60px/1.05 Geist;color:var(--accent)">${esc(o.example == null ? "" : o.example)}</div>
      ${o.confidence != null ? `<div style="height:14px;border-radius:14px;background:color-mix(in srgb, var(--accent2) 22%, transparent)"><div class="bar" style="height:14px;border-radius:14px;background:var(--accent2);width:0"></div></div>
      <div class="mono conf" style="font:600 24px 'Geist Mono';color:var(--accent2)"></div>` : ""}${alts}`;
    root.__a1 = h("div", "abs", "→", "left:700px;top:445px;font:600 64px Geist;color:var(--muted)");
    root.__a2 = h("div", "abs", "→", "left:1165px;top:445px;font:600 64px Geist;color:var(--muted)");
    root.append(root.__in, root.__ring, root.__m, root.__out, root.__a1, root.__a2);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, beat, E, num } = CORE;
    const b = i => beat(d, i, dur, 4);
    riseWords(root.__q, t, 0.1);
    rise(root.__in, p(t, b(1), .7, E.outExpo), 40);
    root.__pre.forEach((c, i) => rise(c, p(t, b(1) + 0.6 + i * 0.2, .5), 14));
    rise(root.__a1, p(t, b(2) - 0.2, .5), 0);
    rise(root.__m, p(t, b(2), .7, E.outBack), 30);
    const pulse = Math.max(0, Math.sin((t - b(2)) * 4)) * p(t, b(2) + 0.4, .4) * (1 - p(t, b(3), .5));
    root.__ring.style.opacity = pulse;
    root.__ring.style.transform = `scale(${1 + pulse * 0.04})`;
    rise(root.__a2, p(t, b(3) - 0.2, .5), 0);
    rise(root.__out, p(t, b(3), .7, E.outExpo), 40);
    const c = (d.output || {}).confidence;
    if (c != null) {
      const k = p(t, b(3) + 0.4, 1.2, E.outExpo);
      root.__out.querySelector(".bar").style.width = `${Math.min(1, Number(c)) * 100 * k}%`;
      root.__out.querySelector(".conf").textContent = `confidence ${num(Number(c) * k, 2)}`;
    }
  },
});
