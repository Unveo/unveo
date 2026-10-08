/* unveo building blocks: small, restrained pieces the agent combines into a scene that fits the story.
   Each block: build(props) -> element (text marked data-fit shrinks to fit its area); draw(el, t, start, props).
   Entrances: rise (default) · fade · draw (bars, flows, dividers grow) · count (numbers count up). */
(function () {
  const { h, esc, p, E, num, clamp } = CORE;
  const T = (tag, cls, html, style) => h(tag, cls, html, style);
  const parseNum = v => { const m = String(v).match(/^([^\d-]*)(-?[\d.,]+)(.*)$/); return m ? { pre: m[1], n: Number(m[2].replace(/,/g, "")), post: m[3], dec: (m[2].split(".")[1] || "").length } : null; };

  // an icon from film/icons.js (open-licence, fetched by render.py); coloured by CSS, so it follows the look.
  // Brand logos (logos:react, logos:claude-icon…) keep their real colours.
  const icon = (name, size, color) => window.ICONS && window.ICONS[name]
    ? `<span class="ico${String(name).startsWith("logos:") ? " brand" : ""}" style="width:${size}px;height:${size}px;${color ? `color:${color}` : ""}">${window.ICONS[name]}</span>` : "";
  window.ICON = icon;
  const B = {
    kicker: { build: pr => T("div", "eyebrow", esc(pr.text)) },
    heading: { build: pr => T("div", null, esc(pr.text), `font:650 ${pr.size || 64}px/1.1 var(--font-display);letter-spacing:-.02em;text-wrap:balance`), fit: true },
    text: { build: pr => T("div", null, esc(pr.text), "font:450 34px/1.4 var(--font-body);color:var(--ink);opacity:.86"), fit: true },
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
  };
  window.BLOCKS = B;
})();
