/* compose: a scene the agent designs for this story from building blocks (DESIGN.md).
   data: { layout: "split"|"stack"|"grid-2x2"|"center"|"hero", blocks: [{ type, area, props, at, enter }] } */
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
  };
  function fitArea(area) {  // shrink every text in the area together until it fits; never overflow
    const els = [...area.querySelectorAll("[data-fit], [data-fit] *")].filter(e => e.style.fontSize || getComputedStyle(e).fontSize);
    for (let k = 0; k < 40; k++) {
      const over = area.scrollHeight > area.clientHeight + 1 || [...area.querySelectorAll("[data-fit]")].some(e => e.scrollWidth > e.clientWidth + 1);
      if (!over) return;
      els.forEach(e => { e.style.fontSize = Math.max(14, parseFloat(getComputedStyle(e).fontSize) * 0.93) + "px"; });
    }
  }
  window.COMPOSE_AREAS = AREAS;
  UNVEO.scene("compose", {
    build(root, d) {
      const layout = AREAS[d.layout] || AREAS.stack;
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
      root.__blocks.forEach(({ el, def, b }, i) => {
        const at = typeof b.at === "number" ? b.at : 0.15 + i * 0.25;
        const enter = b.enter || "rise";
        const k = p(t, at, enter === "count" || enter === "draw" ? 1.1 : 0.7, E.outExpo);
        if (enter === "fade") el.style.opacity = k;
        else if (enter === "draw" || enter === "count") el.style.opacity = Math.min(1, k * 3);
        else rise(el, k, 28);
        if (def.draw) def.draw(el, k, b.props || {});
      });
    },
  });
})();
