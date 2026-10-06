/* formula-breakdown (docs/07 §3.1): { title, inputs:[{name,label,example,weight}], expression, result:{name,label,example,scale,bands:[{max,label,tone}]}, example_data }
   beats: question · inputs · weights · combine · result */
UNVEO.scene("explainer-formula-breakdown", {
  build(root, d) {
    const { h, esc, question, exampleTag } = CORE;
    root.__q = question(root, d.title);
    exampleTag(root, d);
    const ins = (d.inputs || []).slice(0, 5), n = Math.max(1, ins.length);
    const gap = 28, w = Math.min(420, (1680 - gap * (n - 1)) / n);
    const left0 = 120 + (1680 - (w * n + gap * (n - 1))) / 2;
    const maxW = Math.max(...ins.map(i => Number(i.weight) || 0), 0.0001);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", 1920); svg.setAttribute("height", 1080);
    svg.style.cssText = "position:absolute;inset:0;overflow:visible";
    root.append(svg);
    const node = { x: 760, y: 760 };
    root.__chips = ins.map((it, i) => {
      const x = left0 + i * (w + gap);
      const c = h("div", "abs chip", null, `left:${x}px;top:300px;width:${w}px;height:210px`);
      c.innerHTML = `<div style="font:550 32px/1.15 Geist">${esc(it.label || it.name)}</div>
        <div class="mono" style="font:400 21px 'Geist Mono';color:var(--muted)">${esc(it.name)}</div>
        <div class="v mono" style="margin-top:auto;font:600 46px 'Geist Mono';color:var(--accent)"></div>`;
      const wt = h("div", "abs", null, `left:${x}px;top:530px;width:${w}px`);
      const has = it.weight != null;
      wt.innerHTML = has ? `<div style="height:12px;border-radius:12px;background:color-mix(in srgb, var(--accent2) 22%, transparent)">
          <div class="bar" style="height:12px;border-radius:12px;background:var(--accent2);width:0"></div></div>
          <div class="mono" style="margin-top:10px;font:600 26px 'Geist Mono';color:var(--accent2)">× ${esc(it.weight)}</div>` : "";
      root.append(c, wt);
      const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const sx = x + w / 2, sy = 600;
      line.setAttribute("d", `M${sx},${sy} C${sx},${sy + 90} ${node.x},${node.y - 120} ${node.x},${node.y - 70}`);
      line.setAttribute("fill", "none"); line.setAttribute("stroke", "var(--muted)"); line.setAttribute("stroke-width", "3");
      svg.append(line);
      const L = line.getTotalLength();
      line.style.strokeDasharray = L; line.style.strokeDashoffset = L;
      return { c, wt, line, L, it, ratio: has ? (Number(it.weight) || 0) / maxW : 0 };
    });
    const sig = h("div", "abs", "Σ", `left:${node.x - 70}px;top:${node.y - 70}px;width:140px;height:140px;border-radius:50%;background:var(--ink);color:var(--bg);display:flex;align-items:center;justify-content:center;font:600 72px Geist`);
    const ex = h("div", "abs mono", "", `left:120px;top:${node.y + 110}px;width:1280px;text-align:center;font:500 30px 'Geist Mono';color:var(--muted)`);
    const r = d.result || {};
    const res = h("div", "abs card", null, "left:1080px;top:650px;width:620px;height:230px;padding:30px 40px;display:flex;flex-direction:column;gap:10px");
    res.innerHTML = `<div style="font:550 30px Geist">${esc(r.label || r.name || "Result")}</div>
      <div style="display:flex;align-items:baseline;gap:22px"><div class="v" style="font:700 100px/1 Geist;letter-spacing:-.03em"></div>
      <div class="mono" style="font:500 26px 'Geist Mono';color:var(--muted)">${esc(r.scale || "")}</div>
      <div class="band" style="margin-left:auto;padding:10px 22px;border-radius:999px;font:600 28px Geist;color:#fff"></div></div>`;
    root.append(sig, ex, res);
    Object.assign(root, { __sig: sig, __ex: ex, __res: res, __expr: String(d.expression || "") });
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, num, beat, E, clamp } = CORE;
    const b = i => beat(d, i, dur, 4);
    riseWords(root.__q, t, 0.1);
    root.__chips.forEach((c, i) => {
      rise(c.c, p(t, b(1) + i * 0.15, .7, E.outExpo), 50);
      const k = p(t, b(1) + 0.3 + i * 0.15, 1.0, E.outExpo);
      c.c.querySelector(".v").textContent = c.it.example != null ? num(Number(c.it.example) * k || c.it.example) : "";
      const wk = p(t, b(2) + i * 0.15, .8, E.outExpo);
      rise(c.wt, wk, 20);
      const bar = c.wt.querySelector(".bar");
      if (bar) bar.style.width = `${c.ratio * 100 * wk}%`;
      c.line.style.strokeDashoffset = c.L * (1 - p(t, b(3) + i * 0.08, .9, E.ioC));
    });
    const sk = p(t, b(3) + 0.5, .6, E.outBack);
    root.__sig.style.transform = `scale(${sk})`;
    root.__sig.style.opacity = clamp(sk * 2);
    const n = Math.round(root.__expr.length * p(t, b(3) + 0.6, 1.4, E.lin));
    root.__ex.textContent = root.__expr.slice(0, n);
    const rk = p(t, b(4), .8, E.outExpo);
    rise(root.__res, rk, 40);
    const r = d.result || {};
    const val = Number(r.example);
    const cur = isFinite(val) ? val * p(t, b(4) + 0.1, 1.3, E.outExpo) : r.example;
    root.__res.querySelector(".v").textContent = cur == null ? "" : num(cur, isFinite(val) && Number.isInteger(val) ? 0 : undefined);
    const band = (r.bands || []).find(x => isFinite(val) && val <= x.max);
    const bandEl = root.__res.querySelector(".band");
    bandEl.textContent = band ? band.label : "";
    bandEl.style.background = band ? `var(--${band.tone === "good" ? "good" : band.tone === "bad" ? "bad" : "accent"})` : "transparent";
    bandEl.style.opacity = band ? p(t, b(4) + 1.2, .5) : 0;
  },
});
