/* system-map (docs/07 §3.5): { title, nodes:[{id,label,kind}], edges:[{from,to,label}], path:[node ids] } */
UNVEO.scene("explainer-system-map", {
  build(root, d) {
    const { h, esc, question, exampleTag } = CORE;
    root.__q = question(root, d.title);
    exampleTag(root, d);
    const col = { client: 0, server: 1, db: 2, model: 2, job: 2, external: 2 };  // clients left, servers middle, everything they call on the right
    const low = { db: 1, job: 1, model: 1 };
    const nodes = (d.nodes || []).slice(0, 7), groups = {};
    nodes.forEach(n => { const k = `${col[n.kind] ?? 1}`; (groups[k] = groups[k] || []).push(n); });
    const pos = {};
    Object.entries(groups).forEach(([c, list]) => {
      list.sort((a, b) => (low[a.kind] || 0) - (low[b.kind] || 0));
      list.forEach((n, i) => { pos[n.id] = { x: 300 + Number(c) * 640, y: list.length === 1 ? 600 : 360 + (i * 520) / (list.length - 1) }; });
    });
    const icon = { client: "▭", server: "◆", db: "◉", external: "☁", job: "⟳", model: "✦" };
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", 1920); svg.setAttribute("height", 1080);
    svg.style.cssText = "position:absolute;inset:0";
    root.append(svg);
    root.__edges = (d.edges || []).filter(e => pos[e.from] && pos[e.to]).map(e => {
      const a = pos[e.from], b = pos[e.to];
      const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
      ln.setAttribute("x1", a.x); ln.setAttribute("y1", a.y); ln.setAttribute("x2", b.x); ln.setAttribute("y2", b.y);
      ln.setAttribute("stroke", "var(--muted)"); ln.setAttribute("stroke-width", "3");
      const L = Math.hypot(b.x - a.x, b.y - a.y);
      ln.style.strokeDasharray = L; ln.style.strokeDashoffset = L;
      svg.append(ln);
      const lab = h("div", "abs mono", esc(e.label || ""), `left:${(a.x + b.x) / 2}px;top:${(a.y + b.y) / 2 - 44}px;transform:translateX(-50%);padding:6px 14px;border-radius:10px;background:var(--bg);font:500 21px 'Geist Mono';color:var(--muted);white-space:nowrap;z-index:2`);
      root.append(lab);
      return { ln, L, lab, e };
    });
    root.__nodes = nodes.map(n => {
      const q = pos[n.id];
      const el = h("div", "abs card", `<span style="font-size:34px;color:var(--accent)">${icon[n.kind] || "◆"}</span><span>${esc(n.label)}</span>`,
        `left:${q.x - 170}px;top:${q.y - 52}px;width:340px;height:104px;display:flex;align-items:center;justify-content:center;gap:16px;font:600 32px var(--font-display);z-index:3`);
      root.append(el);
      return { el, n };
    });
    root.__pos = pos;
    root.__dot = h("div", "abs", null, "width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;background:var(--accent2);box-shadow:0 0 0 10px color-mix(in srgb, var(--accent2) 25%, transparent);z-index:1")  // passes behind node cards;
    root.append(root.__dot);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, beat, E, lerp, clamp } = CORE;
    const b = i => beat(d, i, dur, 3);
    riseWords(root.__q, t, 0.1);
    root.__nodes.forEach((n, i) => rise(n.el, p(t, b(1) + i * 0.12, .6, E.outBack), 24));
    root.__edges.forEach((e, i) => { e.ln.style.strokeDashoffset = e.L * (1 - p(t, b(1) + 0.6 + i * 0.12, .7, E.ioC)); e.lab.style.opacity = 0; });
    const path = (d.path || []).filter(id => root.__pos[id]);
    if (path.length > 1) {
      const t2 = b(2), seg = Math.max(0.4, (dur - 0.8 - t2) / (path.length - 1));
      const k = clamp((t - t2) / seg, 0, path.length - 1), i = Math.min(path.length - 2, Math.floor(k)), f = E.ioC(k - i);
      const a = root.__pos[path[i]], c = root.__pos[path[i + 1]];
      Object.assign(root.__dot.style, { left: lerp(a.x, c.x, f) + "px", top: lerp(a.y, c.y, f) + "px", opacity: p(t, t2, .3) });
      root.__edges.forEach(e => {
        for (let j = 0; j <= Math.min(i, path.length - 2); j++) {
          const x = path[j], y = path[j + 1];
          if ((e.e.from === x && e.e.to === y) || (e.e.from === y && e.e.to === x)) e.lab.style.opacity = j < i || f > 0.5 ? 1 : 0;
        }
      });
    } else {
      root.__dot.style.opacity = 0;
      root.__edges.forEach(e => (e.lab.style.opacity = p(t, b(2), .5)));
    }
  },
});
