/* unveo capture cursor: headless Chromium draws no pointer, so we draw one.
   Injected before every page load; position survives navigations via sessionStorage.
   window.__UNVEO_ACCENT (set by capture.py) colours the click ring with the video's accent. */
(() => {
  if (window.__unveoCursor) return;
  const KEY = "__unveo_cursor";
  let pos = JSON.parse(sessionStorage.getItem(KEY) || "null") || { x: innerWidth * 0.55, y: innerHeight * 0.6 };
  let el, ring;
  const S = 1.2;  // a little larger than life, so it reads at 1080p when the camera isn't zoomed in
  const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const place = () => { if (el) el.style.transform = `translate(${pos.x}px, ${pos.y}px)`; sessionStorage.setItem(KEY, JSON.stringify(pos)); };
  const mount = () => {
    if (el || !document.body) return;
    el = document.createElement("div");
    el.setAttribute("aria-hidden", "true");
    el.dataset.unveo = "cursor";
    el.style.cssText = `position:fixed;left:0;top:0;width:${28 * S}px;height:${40 * S}px;z-index:2147483647;pointer-events:none;will-change:transform`;
    el.innerHTML = `<svg width="${28 * S}" height="${40 * S}" viewBox="0 0 28 40" style="overflow:visible;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))">` +
      '<path d="M2 2 L2 31 L9.5 24 L14.5 36 L19 34 L14 22.5 L24 22.5 Z" fill="#000" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>';
    ring = document.createElement("div");
    ring.style.cssText = "position:fixed;left:0;top:0;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;" +
      `border:3px solid ${window.__UNVEO_ACCENT || "rgba(79,70,229,.85)"};z-index:2147483646;pointer-events:none;opacity:0`;
    ring.dataset.unveo = "cursor";
    document.body.append(ring, el);
    place();
  };
  window.__unveoCursor = {
    moveTo(x, y, ms) {
      mount();
      const from = { ...pos }, t0 = performance.now();
      // a hand never moves in a straight line: bow the path a little to one side (8% of the distance)
      const bx = -(y - from.y) * 0.08, by = (x - from.x) * 0.08;
      return new Promise(done => {
        const step = now => {
          const k = Math.min(1, (now - t0) / ms), e = ease(k);
          const bow = 4 * e * (1 - e);
          pos = { x: from.x + (x - from.x) * e + bx * bow, y: from.y + (y - from.y) * e + by * bow };
          place();
          k < 1 ? requestAnimationFrame(step) : done();
        };
        requestAnimationFrame(step);
      });
    },
    click() {
      mount();
      const t0 = performance.now();
      const step = now => {
        const k = Math.min(1, (now - t0) / 450);
        ring.style.transform = `translate(${pos.x + 2}px, ${pos.y + 2}px) scale(${0.4 + 0.9 * k})`;
        ring.style.opacity = String(1 - k);
        el.firstChild.style.transform = `scale(${k < 0.3 ? 0.88 : 1})`;
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    },
  };
  document.readyState === "loading" ? addEventListener("DOMContentLoaded", mount) : mount();
})();
