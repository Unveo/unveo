/* pipeline-flow (docs/07 §3.2): { title, trigger?:{label}, stages:[{name,label,tool}], payloads:[…] } — a token travels stage to stage */
UNVEO.scene("explainer-pipeline-flow", {
  build(root, d) {
    const { h, esc, question, exampleTag } = CORE;
    root.__q = question(root, d.title);
    exampleTag(root, d);
    const st = (d.stages || []).slice(0, 6), n = Math.max(1, st.length);
    const gap = 56, w = Math.min(330, (1680 - gap * (n - 1)) / n), y = 470;
    const left0 = 120 + (1680 - (w * n + gap * (n - 1))) / 2;
    const track = h("div", "abs", null, `left:${left0 + w / 2}px;top:${y + 100}px;height:6px;border-radius:6px;background:var(--accent);width:0`);
    root.append(track);
    root.__track = track; root.__trackW = (n - 1) * (w + gap);
    root.__boxes = st.map((s, i) => {
      const b = h("div", "abs card", null, `left:${left0 + i * (w + gap)}px;top:${y}px;width:${w}px;height:200px;padding:26px;display:flex;flex-direction:column;gap:8px;z-index:2`);
      b.innerHTML = `<div class="mono" style="font:600 22px 'Geist Mono';color:var(--accent)">0${i + 1}</div>
        <div style="font:600 34px/1.15 var(--font-display)">${esc(s.label || s.name)}</div>
        <div class="mono" style="margin-top:auto;font:400 21px 'Geist Mono';color:var(--muted)">${esc(s.tool || s.name || "")}</div>`;
      root.append(b);
      return { b, cx: left0 + i * (w + gap) + w / 2 };
    });
    if (d.trigger) {
      root.__trig = h("div", "abs", `⏱ ${esc(d.trigger.label)}`, `left:${left0}px;top:${y - 90}px;padding:12px 24px;border-radius:999px;background:var(--ink);color:var(--bg);font:500 26px var(--font-display)`);
      root.append(root.__trig);
    }
    root.__tok = h("div", "abs mono", "", `top:${y + 250}px;padding:14px 24px;border-radius:16px;background:var(--accent2);color:#fff;font:600 26px 'Geist Mono';white-space:nowrap;transform:translateX(-50%);z-index:3`);
    root.append(root.__tok);
    root.__pay = (d.payloads || []).map(String);
  },
  draw(t, d, dur, root) {
    const { p, riseWords, rise, beat, E, lerp, clamp } = CORE;
    const n = root.__boxes.length;
    riseWords(root.__q, t, 0.1);
    if (root.__trig) rise(root.__trig, p(t, 0.6, .6), 20);
    const t1 = beat(d, 1, dur, 3), t2 = beat(d, 2, dur, 3), tEnd = dur - 1.0;
    root.__boxes.forEach((b, i) => rise(b.b, p(t, t1 + i * 0.18, .7, E.outExpo), 40));
    root.__track.style.width = `${root.__trackW * p(t, t1 + 0.3, n * 0.18 + 0.5, E.ioC)}px`;
    // token: spends equal time at each stage between t2 and the end
    const k = clamp((t - t2) / Math.max(0.5, tEnd - t2)) * (n - 1);
    const i = Math.min(n - 1, Math.floor(k)), f = E.ioC(clamp((k - i) * 1.6));
    const x = n > 1 ? lerp(root.__boxes[i].cx, root.__boxes[Math.min(n - 1, i + 1)].cx, i < n - 1 ? f : 0) : root.__boxes[0].cx;
    root.__tok.style.left = x + "px";
    root.__tok.textContent = root.__pay[Math.min(root.__pay.length - 1, Math.round(k))] || "";
    root.__tok.style.opacity = root.__pay.length ? p(t, t2, .4) : 0;
    root.__boxes.forEach((b, j) => {
      const on = t >= t2 && Math.abs(k - j) < 0.5;
      b.b.style.boxShadow = on ? "0 0 0 4px var(--accent), 0 18px 50px rgba(0,0,0,.08)" : "";
    });
  },
});
