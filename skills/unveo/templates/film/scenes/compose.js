/* compose: a scene the agent designs for this story from building blocks (DESIGN.md).
   data: { layout, blocks: [{ type, area, props, at, enter }] }. Without a layout, the look's layout family picks one. */
(function () {
  const AREAS = {
    split: { left: [120, 140, 780, 800], right: [1000, 140, 800, 800] },
    stack: { top: [120, 110, 1680, 270], middle: [120, 410, 1680, 370], bottom: [120, 810, 1680, 180] },
    "grid-2x2": { a: [120, 120, 820, 400], b: [980, 120, 820, 400], c: [120, 560, 820, 400], d: [980, 560, 820, 400] },
    center: { main: [360, 200, 1200, 680] },
    hero: { title: [120, 140, 1680, 300], main: [120, 480, 1680, 480] },
    "hero-icon": { icon: [140, 240, 460, 600], main: [680, 180, 1120, 720] },
    "three-col": { a: [120, 160, 520, 760], b: [700, 160, 520, 760], c: [1280, 160, 520, 760] },
    asymmetric: { wide: [120, 140, 1120, 800], side: [1300, 140, 500, 800] },
    "full-bleed-shot": { shot: [0, 0, 1920, 860], caption: [120, 890, 1680, 150] },
    // docs/16 D1: layouts that use the whole canvas
    "centered-hero": { main: [200, 160, 1520, 560], below: [360, 760, 1200, 220] },
    "full-type": { main: [120, 100, 1680, 880] },
    "left-heavy": { main: [120, 120, 1080, 840], side: [1280, 200, 520, 680] },
    diagonal: { a: [120, 100, 1100, 420], b: [700, 560, 1100, 420] },
    bento: { a: [120, 110, 1060, 500], b: [1210, 110, 590, 500], c: [120, 640, 590, 330], d: [740, 640, 1060, 330] },
  };
  const FAMILY = { editorial: "left-heavy", grid: "bento", centered: "centered-hero" };  // design.json layout_family
  // a text block's lines and words per line, at its current size
  const lines = e => Math.max(1, Math.round(e.offsetHeight / (parseFloat(getComputedStyle(e).lineHeight) || parseFloat(getComputedStyle(e).fontSize) * 1.2)));
  const crowded = e => { const n = lines(e), w = e.textContent.trim().split(/\s+/).length; return n > 3 || (n > 1 && w / n < 2); };
  function fitArea(area) {  // grow text a little into a roomy area (at most 1.2x, never past 3 lines or under 2 words a
    // line), then shrink it until it fits and no heading runs past 3 lines; never overflow
    const els = [...area.querySelectorAll("[data-fit], [data-fit] *")].filter(e => e.style.fontSize || getComputedStyle(e).fontSize);
    const texts = [...area.querySelectorAll("[data-fit]")].filter(e => e.textContent.trim() && !e.querySelector(".card, .li, .st, .n"));
    const over = () => area.scrollHeight > area.clientHeight + 1 || [...area.querySelectorAll("[data-fit]")].some(e => e.scrollWidth > e.clientWidth + 1);
    const used = () => [...area.children].reduce((a, c) => a + c.offsetHeight, 0) / Math.max(1, area.clientHeight);
    const scale = f => els.forEach(e => { e.style.fontSize = Math.max(14, parseFloat(getComputedStyle(e).fontSize) * f) + "px"; });
    if (els.length && !area.querySelector('[data-grow="0"]')) {
      for (let k = 0, g = 1; k < 3 && used() < 0.5 && g * 1.06 <= 1.2; k++, g *= 1.06) {
        scale(1.06);
        if (over() || texts.some(crowded)) { scale(1 / 1.06); break; }
      }
    }
    for (let k = 0; k < 40 && (over() || [...area.querySelectorAll(".h")].some(e => lines(e) > 3)); k++) scale(0.93);
  }
  window.COMPOSE_AREAS = AREAS;
  UNVEO.scene("compose", {
    build(root, d) {
      const fam = FAMILY[((window.TIMELINE || {}).design || {}).layout_family];
      const layout = AREAS[d.layout] || AREAS[fam] || AREAS.stack;
      root.__areas = {};
      Object.entries(layout).forEach(([name, [x, y, w, hh]]) => {
        const a = CORE.h("div", "abs area", null, `left:${x}px;top:${y}px;width:${w}px;height:${hh}px;display:flex;flex-direction:column;justify-content:center;gap:22px;overflow:hidden`);
        root.append(a);
        root.__areas[name] = a;
      });
      root.__blocks = (d.blocks || []).slice(0, 12).map(b => {
        const def = BLOCKS[b.type];
        const area = root.__areas[b.area] || Object.values(root.__areas)[0];
        if (!def) return null;
        const el = def.build(b.props || {});
        el.classList.add("block");
        if (def.fit) el.dataset.fit = "1";
        if (b.type === "screenshot") el.style.flex = "1";
        area.append(el);
        return { el, def, b };
      }).filter(Boolean);
      this.fit(root);
    },
    fit(root) { Object.values(root.__areas).forEach(fitArea); },
    draw(t, d, dur, root) {
      const { p, E, rise } = CORE;
      if (!root.__rank) {  // reading order: the layout's areas in the order it lists them (left before right, top before
        // bottom), then each block's place in its area (blocks without an "at" enter in this order)
        const areas = Object.values(root.__areas), key = ({ el }) => areas.indexOf(el.parentElement) * 100 + [...el.parentElement.children].indexOf(el);
        const order = root.__blocks.map((_, i) => i).sort((a, b) => key(root.__blocks[a]) - key(root.__blocks[b]));
        root.__rank = order.reduce((r, i, n) => ((r[i] = n), r), {});
      }
      const lead = Math.min(...root.__blocks.map(({ b }, i) => (["kicker", "divider", "chip"].includes(b.type) ? 99 : root.__rank[i])));
      root.__blocks.forEach(({ el, def, b }, i) => {
        const r = root.__rank[i];
        let at = typeof b.at === "number" ? b.at : 0.15 + r * 0.25;
        // the scene never opens empty under the voice: its first real block (and a kicker above it) is up by 0.25 s
        if (r <= lead) at = Math.min(at, 0.25);
        const enter = b.enter || "rise";
        const k = p(t, at, enter === "count" || enter === "draw" ? 1.1 : 0.7, E.outExpo);
        if (enter === "fade") el.style.opacity = k;
        else if (enter === "draw" || enter === "count") el.style.opacity = Math.min(1, k * 3);
        else rise(el, k, 28);
        if (def.draw) def.draw(el, k, b.props || {}, (t - at) * (window.CORE_SPEED || 1), at);
      });
    },
  });
})();
