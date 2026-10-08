/* unveo building blocks: small, restrained pieces the agent combines into a scene that fits the story.
   Each block: build(props) -> element (text marked data-fit shrinks to fit its area); draw(el, t, start, props).
   Entrances: rise (default) · fade · draw (bars, flows, dividers grow) · count (numbers count up). */
(function () {
  const { h, esc, rich, p, E, num, clamp } = CORE;
  const T = (tag, cls, html, style) => h(tag, cls, html, style);
  const parseNum = v => { const m = String(v).match(/^([^\d-]*)(-?[\d.,]+)(.*)$/); return m ? { pre: m[1], n: Number(m[2].replace(/,/g, "")), post: m[3], dec: (m[2].split(".")[1] || "").length } : null; };

  // an icon from film/icons.js (open-licence, fetched by render.py); coloured by CSS, so it follows the look.
  // Brand logos (logos:react, logos:claude-icon…) keep their real colours.
  const icon = (name, size, color) => window.ICONS && window.ICONS[name]
    ? `<span class="ico${String(name).startsWith("logos:") ? " brand" : ""}" style="width:${size}px;height:${size}px;${color ? `color:${color}` : ""}">${window.ICONS[name]}</span>` : "";
  window.ICON = icon;
  const B = {
    kicker: { build: pr => T("div", "eyebrow", esc(pr.text)) },
    // the look's type scale (design.css --type-scale) sizes headings; auto-fit still shrinks or grows them to the area
    heading: { build: pr => T("div", null, rich(pr.text), `font:650 calc(${pr.size || 64}px * var(--type-scale, 1))/1.1 var(--font-display);letter-spacing:-.02em;text-wrap:balance`), fit: true },
    text: { build: pr => T("div", null, rich(pr.text), "font:450 calc(34px * min(var(--type-scale, 1), 1.2))/1.4 var(--font-body);color:var(--ink);opacity:.86"), fit: true },
    "big-number": {
      build: pr => {
        const el = T("div");
        el.innerHTML = `<div class="v" style="font:700 132px/1 var(--font-display);letter-spacing:-.03em;color:var(--accent)"></div>
          <div style="margin-top:14px;font:500 32px/1.25 var(--font-body)">${esc(pr.label || "")}</div>
          ${pr.source ? `<div class="mono" style="margin-top:10px;font:400 20px 'Geist Mono';color:var(--muted)">${esc(pr.source)}</div>` : ""}`;
        el.__num = parseNum(pr.value); el.__raw = String(pr.value);
        el.querySelector(".v").textContent = el.__raw;  // measured at its final width, so auto-fit sizes it right
        return el;
      },
      draw: (el, k) => { el.querySelector(".v").textContent = el.__num ? el.__num.pre + num(el.__num.n * k, el.__num.dec) + el.__num.post : el.__raw; },
    },
    list: {
      build: pr => T("div", null, (pr.items || []).slice(0, 5).map((x, i) =>
        `<div class="li" style="display:flex;gap:22px;align-items:baseline;padding:12px 0;border-bottom:1px solid color-mix(in srgb, var(--muted) 22%, transparent)">
          <span class="mono" style="font:600 22px 'Geist Mono';color:var(--accent)">0${i + 1}</span><span style="font:500 34px/1.3 var(--font-body)">${esc(x)}</span></div>`).join("")),
      fit: true,
      draw: (el, k) => [...el.querySelectorAll(".li")].forEach((li, i) => { const q = clamp(k * 1.6 - i * 0.18); li.style.opacity = q; li.style.transform = `translateY(${(1 - q) * 16}px)`; }),
    },
    card: { build: pr => T("div", "card", `<div style="font:600 34px/1.2 var(--font-display)">${esc(pr.title || "")}</div><div style="margin-top:10px;font:450 28px/1.4 var(--font-body);color:var(--muted)">${esc(pr.text || "")}</div>`, "padding:30px 34px"), fit: true },
    chip: { build: pr => T("div", "chip", esc(pr.text), "display:inline-block;align-self:flex-start;padding:12px 22px;border-radius:999px;font:500 26px var(--font-body);border:1.5px solid color-mix(in srgb, var(--muted) 40%, transparent)") },
    bar: {
      build: pr => {
        const items = (pr.items || []).slice(0, 6), max = Math.max(pr.max || 0, ...items.map(x => Number(x.value) || 0), 1e-9);
        const el = T("div");
        el.innerHTML = items.map(x => `<div style="margin:14px 0"><div style="display:flex;justify-content:space-between;font:500 26px var(--font-body)"><span>${esc(x.label)}</span><span class="mono" style="color:var(--muted)">${esc(x.value)}</span></div>
          <div style="height:12px;border-radius:12px;margin-top:8px;background:color-mix(in srgb, var(--muted) 18%, transparent)"><div class="fill" data-w="${(Number(x.value) || 0) / max}" style="height:12px;border-radius:12px;background:var(--accent);width:0"></div></div></div>`).join("");
        return el;
      },
      draw: (el, k) => el.querySelectorAll(".fill").forEach((f, i) => { f.style.width = `${Number(f.dataset.w) * 100 * clamp(k * 1.3 - i * 0.12)}%`; }),
    },
    flow: {
      build: pr => T("div", null, (pr.steps || []).slice(0, 6).map((s, i, a) =>
        `<span class="st card" style="display:inline-block;padding:16px 22px;font:550 28px var(--font-body)">${esc(s)}</span>${i < a.length - 1 ? `<span class="ar" style="display:inline-block;margin:0 14px;font:500 30px var(--font-body);color:var(--muted)">→</span>` : ""}`).join(""),
        "white-space:nowrap"), fit: true,
      draw: (el, k) => [...el.children].forEach((c, i) => { c.style.opacity = clamp(k * 2.2 - i * 0.22); }),
    },
    quote: { build: pr => T("div", null, `<div style="font:500 44px/1.3 var(--font-display)">“${esc(pr.text)}”</div>${pr.by ? `<div style="margin-top:14px;font:500 24px var(--font-body);color:var(--muted)">${esc(pr.by)}</div>` : ""}`), fit: true },
    divider: { build: () => T("div", null, "", "height:3px;width:140px;background:var(--accent);transform-origin:0 50%"), draw: (el, k) => { el.style.transform = `scaleX(${k})`; } },
    diagram: {
      build: pr => {
        const nodes = (pr.nodes || []).slice(0, 5), el = T("div", null, null, "position:relative;height:200px");
        const xs = nodes.map((_, i) => (i + 0.5) / nodes.length * 100);
        el.innerHTML = `<svg viewBox="0 0 100 40" preserveAspectRatio="none" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible">${(pr.edges || []).map(([a, b]) =>
          `<path class="e" d="M${xs[a]},20 Q${(xs[a] + xs[b]) / 2},${Math.abs(b - a) > 1 ? 0 : 20} ${xs[b]},20" fill="none" stroke="var(--muted)" stroke-width=".35" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>`).join("")}</svg>` +
          nodes.map((n, i) => `<div class="n card" style="position:absolute;left:${xs[i]}%;top:50%;transform:translate(-50%,-50%);padding:16px 24px;font:550 26px var(--font-body);white-space:nowrap">${esc(n)}</div>`).join("");
        return el;
      },
      draw: (el, k) => { el.querySelectorAll(".n").forEach((n, i) => { n.style.opacity = clamp(k * 2 - i * 0.2); }); el.querySelectorAll(".e").forEach(e => { e.style.strokeDashoffset = 1 - clamp(k * 1.4 - 0.3); }); },
    },
    screenshot: {
      build: pr => {
        const hl = pr.highlight;
        return T("div", "card", `<img src="${esc(pr.src)}" style="display:block;width:100%;height:100%;object-fit:cover;object-position:top">` +
          (hl ? `<div class="hl" style="position:absolute;left:${hl.x * 100}%;top:${hl.y * 100}%;width:${hl.w * 100}%;height:${hl.h * 100}%;border:3px solid var(--accent);border-radius:10px;box-shadow:0 0 0 9999px rgba(0,0,0,.28);opacity:0"></div>` : ""),
          "position:relative;overflow:hidden;height:100%;min-height:280px;padding:0");
      },
      draw: (el, k) => { const hl = el.querySelector(".hl"); if (hl) hl.style.opacity = clamp(k * 2 - 1); },
    },
    icon: {
      build: pr => T("div", null, `${icon(pr.icon, pr.size || 150)}${pr.label ? `<div style="margin-top:18px;font:600 36px/1.2 var(--font-display)">${esc(pr.label)}</div>` : ""}`,
        "display:flex;flex-direction:column;align-items:flex-start"),
      draw: (el, k) => { const i = el.querySelector(".ico"); if (i) i.style.transform = `scale(${0.85 + 0.15 * k})`; },
    },
    "icon-row": {
      build: pr => T("div", null, (pr.items || []).slice(0, 6).map(x =>  // size: the icon's px (88; ~140 for a wall of logos)
        `<div class="it" style="display:flex;flex-direction:column;align-items:center;gap:14px;flex:1;text-align:center">${icon(x.icon, pr.size || 88)}
          <div style="font:550 28px/1.25 var(--font-body)">${esc(x.label || "")}</div></div>`).join(""), "display:flex;gap:28px;align-items:flex-start"),
      fit: true,
      draw: (el, k) => [...el.querySelectorAll(".it")].forEach((it, i) => { const q = clamp(k * 1.8 - i * 0.2); it.style.opacity = q; it.style.transform = `translateY(${(1 - q) * 18}px)`; }),
    },
    stat: {
      build: pr => {
        const el = T("div", null, null, "display:flex;gap:28px;align-items:center");
        el.innerHTML = `${icon(pr.icon, 96)}<div style="min-width:0"><div class="v" style="font:700 104px/1 var(--font-display);letter-spacing:-.03em;white-space:nowrap"></div>
          <div style="margin-top:10px;font:500 30px/1.25 var(--font-body);color:var(--muted)">${esc(pr.label || "")}</div></div>`;
        el.__num = parseNum(pr.value); el.__raw = String(pr.value);
        el.querySelector(".v").textContent = el.__raw;  // measured at its final width, so auto-fit sizes it right
        return el;
      },
      draw: (el, k) => { el.querySelector(".v").textContent = el.__num ? el.__num.pre + num(el.__num.n * k, el.__num.dec) + el.__num.post : el.__raw; },
      fit: true,
    },
    timeline: {
      build: pr => {
        const items = (pr.items || []).slice(0, 5), el = T("div", null, null, "position:relative;padding-top:40px");
        el.innerHTML = `<div class="tl" style="position:absolute;left:0;right:0;top:52px;height:4px;background:var(--accent);transform-origin:0 50%"></div>
          <div style="display:flex;justify-content:space-between;gap:16px">${items.map(x => `<div class="pt" style="flex:1">
          <div style="width:28px;height:28px;border-radius:50%;background:var(--bg);border:4px solid var(--accent)"></div>
          <div style="margin-top:20px;font:700 32px var(--font-display)">${esc(x.when || "")}</div>
          <div style="margin-top:6px;font:450 26px/1.3 var(--font-body);color:var(--muted)">${esc(x.what || "")}</div></div>`).join("")}</div>`;
        return el;
      },
      fit: true,
      draw: (el, k) => { el.querySelector(".tl").style.transform = `scaleX(${clamp(k * 1.2)})`; el.querySelectorAll(".pt").forEach((pt, i, a) => { pt.style.opacity = clamp(k * 1.4 * a.length - i); }); },
    },
    compare: {
      build: pr => {
        const col = (c, on) => `<div class="col card" style="flex:1;padding:30px 34px;${on ? "box-shadow:inset 0 0 0 3px var(--accent)" : "opacity:.9"}">
          <div style="font:650 34px var(--font-display);${on ? "color:var(--accent)" : "color:var(--muted)"}">${esc((c || {}).title || "")}</div>
          ${((c || {}).items || []).slice(0, 4).map(x => `<div style="margin-top:16px;font:500 28px/1.3 var(--font-body)">${on ? "✓" : "–"}&nbsp; ${esc(x)}</div>`).join("")}</div>`;
        return T("div", null, col(pr.before, false) + col(pr.after, true), "display:flex;gap:28px");
      },
      fit: true,
      draw: (el, k) => [...el.querySelectorAll(".col")].forEach((c, i) => { const q = clamp(k * 2 - i * 0.6); c.style.opacity = q; c.style.transform = `translateX(${(1 - q) * (i ? 30 : -30)}px)`; }),
    },
    callout: {
      build: pr => T("div", "card", `<img src="${esc(pr.src)}" style="display:block;width:100%;height:100%;object-fit:cover;object-position:top">` +
        (pr.pins || []).slice(0, 5).map((pin, i) => `<div class="pin" style="position:absolute;left:${pin.x * 100}%;top:${pin.y * 100}%;transform:translate(-50%,-50%);display:flex;align-items:center;gap:12px">
          <span style="width:48px;height:48px;border-radius:50%;background:var(--accent);color:var(--bg);display:grid;place-items:center;font:700 24px var(--font-body);box-shadow:0 0 0 6px color-mix(in srgb, var(--bg) 70%, transparent)">${i + 1}</span>
          <span style="background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:10px;font:600 24px var(--font-body);white-space:nowrap">${esc(pin.label || "")}</span></div>`).join(""),
        "position:relative;overflow:hidden;height:100%;min-height:300px;padding:0"),
      draw: (el, k) => el.querySelectorAll(".pin").forEach((p_, i) => { const q = clamp(k * 2 - i * 0.35); p_.style.opacity = q; }),
    },
    device: {
      build: pr => {
        const phone = pr.kind === "phone";
        return T("div", null, `<div style="${phone ? "width:300px;height:620px;border-radius:44px;padding:14px" : "width:100%;aspect-ratio:16/10;border-radius:18px;padding:14px"};background:#151517;box-shadow:0 24px 60px rgba(0,0,0,.18)">
          <img src="${esc(pr.src)}" style="display:block;width:100%;height:100%;object-fit:cover;object-position:top;border-radius:${phone ? 32 : 8}px"></div>`,
          "display:flex;justify-content:center;align-items:center;height:100%");
      },
    },
    "badge-cloud": {
      build: pr => T("div", null, (pr.items || []).slice(0, 10).map(x => {  // "Text" or {text, icon} (a logo beside it)
        const it = typeof x === "string" ? { text: x } : x || {};
        return `<span class="bd chip" style="display:inline-flex;flex-direction:row;align-items:center;gap:12px;margin:0 14px 14px 0;padding:12px 22px;border-radius:999px;font:550 26px var(--font-body)">${it.icon ? icon(it.icon, 32) : ""}${esc(it.text || "")}</span>`;
      }).join("")),
      fit: true,
      draw: (el, k) => [...el.querySelectorAll(".bd")].forEach((b, i) => { b.style.opacity = clamp(k * 2.5 - i * 0.15); }),
    },
    // ---- round 8 (docs/16 MO4). Blocks that play out over time get el's seconds since it started (4th draw arg).
    "logo-wall": {  // { items: [icon or {icon, label}], size } — up to 12 logos assembling in a grid
      build: pr => T("div", null, (pr.items || []).slice(0, 12).map(x => {
        const it = typeof x === "string" ? { icon: x } : x || {};
        return `<div class="lg" style="display:flex;flex-direction:column;align-items:center;gap:12px">${icon(it.icon, pr.size || 96)}${it.label ? `<div style="font:550 24px var(--font-body);color:var(--muted)">${esc(it.label)}</div>` : ""}</div>`;
      }).join(""), `display:grid;grid-template-columns:repeat(${Math.min(6, Math.max(3, Math.ceil((pr.items || []).length / 2)))}, 1fr);gap:40px 28px;justify-items:center;align-items:center`),
      draw: (el, k) => [...el.querySelectorAll(".lg")].forEach((g, i, a) => {
        const q = clamp(k * 1.6 - (i / a.length) * 0.6);
        g.style.opacity = q; g.style.clipPath = q < 1 ? `circle(${q * 75}% at 50% 50%)` : ""; g.style.transform = `scale(${0.85 + 0.15 * q})`;
      }),
    },
    ticker: {  // { items: [{value, label, source}] } — numbers roll in like an odometer (real, sourced figures only)
      build: pr => T("div", null, (pr.items || []).slice(0, 4).map(x => `<div style="flex:1;min-width:0">
          <div class="odo" data-clip style="display:flex;align-items:flex-start;font:700 calc(96px * min(var(--type-scale, 1), 1.3))/1.1 var(--font-display);letter-spacing:-.03em;color:var(--accent);overflow:hidden;height:1.1em">${[...String(x.value)].map(c =>
            /\d/.test(c) ? `<span class="dg" data-d="${c}" style="display:flex;flex-direction:column">${[...Array(10).keys()].map(n => `<span style="display:block;height:1.1em">${n}</span>`).join("")}</span>` : `<span style="display:block;height:1.1em">${esc(c)}</span>`).join("")}</div>
          <div style="margin-top:14px;font:500 28px/1.25 var(--font-body)">${esc(x.label || "")}</div>
          ${x.source ? `<div class="mono" style="margin-top:8px;font:400 19px 'Geist Mono';color:var(--muted)">${esc(x.source)}</div>` : ""}</div>`).join(""),
        "display:flex;gap:56px"),
      fit: true,
      draw: (el, k) => [...el.querySelectorAll(".dg")].forEach((g, i, a) => {
        const q = E.outC(clamp(k * 1.3 - (a.length - 1 - i) * 0.05));  // the last digit settles first, like a counter
        g.style.transform = `translateY(${-Number(g.dataset.d) * q * 1.1}em)`;
      }),
    },
    chat: {  // { messages: [{from: "user"|"bot", text}], name? } — a conversation; the bot types, then answers
      build: pr => T("div", null, (pr.messages || []).slice(0, 5).map(m => {
        const me = m.from === "user";
        return `<div class="msg" style="display:flex;${me ? "justify-content:flex-end" : ""};margin:12px 0"><div style="max-width:76%;padding:18px 24px;border-radius:26px;${me
          ? "background:var(--accent);color:var(--on-accent);border-bottom-right-radius:8px" : "background:var(--surface);border-bottom-left-radius:8px"};font:500 30px/1.35 var(--font-body)">
          <span class="dots" style="display:none;letter-spacing:.2em">•••</span><span class="tx">${esc(m.text)}</span></div></div>`;
      }).join(""), "display:flex;flex-direction:column"),
      fit: true, timed: true,
      draw: (el, k, pr, s) => {
        let at = 0;
        [...el.querySelectorAll(".msg")].forEach((m, i) => {
          const bot = ((pr.messages || [])[i] || {}).from !== "user", wait = bot ? 0.7 : 0.15, dur = 0.35;
          const on = s - at, q = clamp(on / dur);
          m.style.opacity = on > 0 ? 1 : 0; m.style.transform = `translateY(${(1 - E.outC(q)) * 24}px)`;
          m.querySelector(".dots").style.display = on > 0 && on < wait && bot ? "inline" : "none";
          m.querySelector(".tx").style.display = on >= wait || !bot ? "inline" : "none";
          at += wait + 0.4 + String(((pr.messages || [])[i] || {}).text || "").length / 45;
        });
      },
    },
    code: {  // { code: "real lines", start: 12, highlight: [14], source: "file.py:12-18" } — revealed line by line, key line marked
      build: pr => {
        const hl = line => esc(line).replace(/(&quot;.*?&quot;|'[^']*'|`[^`]*`)|(\/\/.*$|#.*$|--.*$)|(\b\d+(?:\.\d+)?\b)|\b(def|return|if|else|elif|for|while|import|from|const|let|var|function|async|await|class|new|try|catch|except|with|as|in|of|export|SELECT|FROM|WHERE|INSERT|BEGIN|COMMIT)\b/g,
          (m, str, com, n, k) => str ? `<span style="color:var(--accent2)">${m}</span>` : com ? `<span style="color:var(--muted)">${m}</span>` : n ? `<span style="color:var(--accent2)">${m}</span>` : `<span style="color:var(--accent);font-weight:600">${m}</span>`);
        const lines = String(pr.code || "").split("\n").slice(0, 14), start = pr.start || 1, mark = new Set(pr.highlight || []);
        return T("div", "card", `<div class="mono" style="font:500 20px 'Geist Mono';color:var(--muted);margin-bottom:16px">${esc(pr.source || "")}</div>` +
          lines.map((l, i) => `<div class="ln${mark.has(start + i) ? " key" : ""}" style="display:flex;gap:26px;padding:3px 12px;border-radius:8px;font:450 26px/1.5 'Geist Mono';white-space:pre">
            <span style="color:var(--muted);opacity:.6;min-width:2.2ch;text-align:right">${start + i}</span><span>${hl(l)}</span></div>`).join(""), "padding:30px 34px");
      },
      fit: true, timed: true,
      draw: (el, k, pr, s) => [...el.querySelectorAll(".ln")].forEach((l, i, a) => {
        l.style.opacity = s > i * 0.12 ? 1 : 0;
        const done = a.length * 0.12 + 0.4;
        if (l.classList.contains("key")) l.style.background = `color-mix(in srgb, var(--accent) ${Math.round(18 * clamp((s - done) / 0.4))}%, transparent)`;
      }),
    },
    "map-pins": {  // { pins: [{x, y, label}] (0..1 of the map), src?: a map image } — pins drop onto a simple map
      build: pr => T("div", "card", (pr.src ? `<img src="${esc(pr.src)}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.9">`
        : `<div style="position:absolute;inset:0;background-image:radial-gradient(color-mix(in srgb, var(--muted) 35%, transparent) 1.5px, transparent 2px);background-size:26px 26px"></div>`) +
        (pr.pins || []).slice(0, 8).map(pin => `<div class="pin" style="position:absolute;left:${pin.x * 100}%;top:${pin.y * 100}%;transform:translate(-50%,-100%)">
          <svg width="40" height="54" viewBox="0 0 40 54" style="display:block;margin:0 auto"><path d="M20 53 C 8 36, 2 28, 2 19 A 18 18 0 0 1 38 19 C 38 28, 32 36, 20 53Z" fill="var(--accent)"/><circle cx="20" cy="19" r="7" fill="var(--bg)"/></svg>
          ${pin.label ? `<div style="margin-top:6px;padding:6px 12px;border-radius:10px;background:var(--ink);color:var(--bg);font:600 22px var(--font-body);white-space:nowrap">${esc(pin.label)}</div>` : ""}</div>`).join(""),
        "position:relative;overflow:hidden;height:100%;min-height:360px;padding:0"),
      draw: (el, k) => [...el.querySelectorAll(".pin")].forEach((pn, i) => {
        const q = clamp(k * 1.8 - i * 0.12);
        pn.style.opacity = q > 0 ? 1 : 0; pn.style.transform = `translate(-50%, ${-100 - (1 - E.outBack(q)) * 60}%)`;
      }),
    },
    "line-chart": {  // { points: [numbers], labels?: [first, last], unit?, source? } — the line draws in, the last value lands
      build: pr => {
        const pts = (pr.points || []).map(Number).filter(isFinite).slice(0, 40), lo = Math.min(...pts), hi = Math.max(...pts), n = Math.max(1, pts.length - 1);
        const xy = pts.map((v, i) => [i / n * 1000, 380 - (hi > lo ? (v - lo) / (hi - lo) : 0.5) * 340]);
        const d = xy.map((q, i) => `${i ? "L" : "M"}${q[0].toFixed(1)},${q[1].toFixed(1)}`).join(" ");
        const last = xy[xy.length - 1] || [0, 0];
        return T("div", null, `<svg viewBox="-10 0 1030 420" style="width:100%;overflow:visible">
          <path class="ar" d="${d} L1000,400 L0,400Z" fill="color-mix(in srgb, var(--accent) 14%, transparent)" opacity="0"/>
          <path class="ln" d="${d}" fill="none" stroke="var(--accent)" stroke-width="6" stroke-linejoin="round" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>
          <circle class="dt" cx="${last[0]}" cy="${last[1]}" r="12" fill="var(--accent)" opacity="0"/></svg>
          <div style="display:flex;justify-content:space-between;font:500 24px var(--font-body);color:var(--muted)"><span>${esc((pr.labels || [])[0] || "")}</span>
          <span class="v" style="font:700 40px var(--font-display);color:var(--ink);opacity:0">${esc(pts.length ? num(pts[pts.length - 1]) + (pr.unit || "") : "")}</span><span>${esc((pr.labels || [])[1] || "")}</span></div>
          ${pr.source ? `<div class="mono" style="margin-top:8px;font:400 19px 'Geist Mono';color:var(--muted)">${esc(pr.source)}</div>` : ""}`);
      },
      draw: (el, k) => {
        el.querySelector(".ln").style.strokeDashoffset = 1 - clamp(k * 1.2);
        el.querySelector(".ar").setAttribute("opacity", clamp(k * 2 - 1));
        el.querySelector(".dt").setAttribute("opacity", clamp(k * 3 - 2));
        el.querySelector(".v").style.opacity = clamp(k * 3 - 2);
      },
    },
    donut: {  // { items: [{label, value}], center?: "label" } — arcs draw one after another
      build: pr => {
        const items = (pr.items || []).slice(0, 5), tot = items.reduce((a, x) => a + (Number(x.value) || 0), 0) || 1;
        const cols = ["var(--accent)", "var(--accent2)", "var(--ink)", "var(--muted)", "color-mix(in srgb, var(--accent) 45%, var(--bg))"];
        let acc = 0;
        const arcs = items.map((x, i) => { const f = (Number(x.value) || 0) / tot, a = acc; acc += f;
          return `<circle class="arc" r="80" cx="100" cy="100" fill="none" stroke="${cols[i]}" stroke-width="34" pathLength="1" data-a="${a}" data-f="${f}"
            stroke-dasharray="0 1" transform="rotate(${a * 360 - 90} 100 100)"/>`; }).join("");
        return T("div", null, `<svg viewBox="0 0 200 200" style="width:340px;flex:none">${arcs}<text x="100" y="108" text-anchor="middle" style="font:700 26px var(--font-display);fill:var(--ink)">${esc(pr.center || "")}</text></svg>
          <div>${items.map((x, i) => `<div class="lg" style="display:flex;gap:16px;align-items:center;margin:14px 0;font:500 30px var(--font-body)"><i style="width:22px;height:22px;border-radius:6px;background:${cols[i]}"></i>${esc(x.label)}<span class="mono" style="color:var(--muted)">${esc(x.value)}</span></div>`).join("")}</div>`,
          "display:flex;gap:56px;align-items:center");
      },
      fit: true,
      draw: (el, k) => {
        el.querySelectorAll(".arc").forEach(c => { const f = Number(c.dataset.f), a = Number(c.dataset.a), q = clamp((k * 1.2 - a) / Math.max(0.05, f)); c.setAttribute("stroke-dasharray", `${f * q} 1`); });
        el.querySelectorAll(".lg").forEach((l, i) => { l.style.opacity = clamp(k * 2.5 - i * 0.3); });
      },
    },
    "phone-stack": {  // { srcs: [2–3 screenshots] } — phones fanned out (mobile projects)
      build: pr => T("div", null, (pr.srcs || []).slice(0, 3).map((src, i, a) => `<div class="ph" style="position:absolute;left:50%;top:50%;width:250px;height:520px;margin:-260px 0 0 -125px;border-radius:38px;padding:11px;background:#151517;box-shadow:0 24px 60px rgba(0,0,0,.2)" data-r="${(i - (a.length - 1) / 2) * 9}" data-x="${(i - (a.length - 1) / 2) * 230}">
          <img src="${esc(src)}" style="display:block;width:100%;height:100%;object-fit:cover;object-position:top;border-radius:28px"></div>`).join(""), "position:relative;height:100%;min-height:600px"),
      draw: (el, k) => [...el.querySelectorAll(".ph")].forEach((ph, i) => {
        const q = E.outC(clamp(k * 1.5 - i * 0.2));
        ph.style.opacity = clamp(q * 2); ph.style.transform = `translateX(${Number(ph.dataset.x) * q}px) rotate(${Number(ph.dataset.r) * q}deg) translateY(${(1 - q) * 60}px)`;
      }),
    },
    terminal: {  // { command, output: [lines] or "text", prompt?: "$", title? } — the real command typed, then its real output
      build: pr => {
        const out = Array.isArray(pr.output) ? pr.output : String(pr.output || "").split("\n");
        return T("div", null, `<div style="display:flex;gap:9px;padding:16px 20px;background:color-mix(in srgb, #fff 8%, #111214)">${["#ff5f57", "#febc2e", "#28c840"].map(c => `<i style="width:13px;height:13px;border-radius:50%;background:${c}"></i>`).join("")}
            <span class="mono" style="margin-left:14px;font:500 18px 'Geist Mono';color:#8b8f98">${esc(pr.title || "terminal")}</span></div>
          <div style="padding:26px 30px;font:450 25px/1.55 'Geist Mono';color:#e6e6e3;overflow-wrap:anywhere">` +
          `<div><span style="color:#7cdb8a">${esc(pr.prompt || "$")}</span> <span class="cmd" data-full="${esc(pr.command || "")}"></span><span class="cur" style="display:inline-block;width:.55em;height:1.1em;vertical-align:-.15em;background:#e6e6e3"></span></div>` +
          out.slice(0, 14).map(l => `<div class="out" style="opacity:0;white-space:pre-wrap">${esc(l) || "&nbsp;"}</div>`).join("") + `</div>`,
          "border-radius:16px;overflow:hidden;background:#111214;box-shadow:0 24px 60px rgba(0,0,0,.18)");
      },
      fit: true, timed: true,
      draw: (el, k, pr, s) => {
        const c = el.querySelector(".cmd"), full = c.dataset.full, typed = Math.floor(Math.max(0, s) * 24);
        c.textContent = full.slice(0, typed);
        const done = full.length / 24 + 0.35;
        el.querySelectorAll(".out").forEach((o, i) => { o.style.opacity = s > done + i * 0.07 ? 1 : 0; });
        el.querySelector(".cur").style.opacity = s < done ? 1 : Math.floor(s * 2) % 2;
      },
    },
  };
  window.BLOCKS = B;
})();
