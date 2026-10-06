/* unveo capture cursor: headless Chromium draws no pointer, so we draw one.
   Injected before every page load; position survives navigations via sessionStorage. */
(() => {
  if (window.__unveoCursor) return;
  const KEY = "__unveo_cursor";
  let pos = JSON.parse(sessionStorage.getItem(KEY) || "null") || { x: innerWidth * 0.55, y: innerHeight * 0.6 };
  let el, ring;
  const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const place = () => { if (el) el.style.transform = `translate(${pos.x}px, ${pos.y}px)`; sessionStorage.setItem(KEY, JSON.stringify(pos)); };
  const mount = () => {
    if (el || !document.body) return;
    el = document.createElement("div");
    el.setAttribute("aria-hidden", "true");
    el.style.cssText = "position:fixed;left:0;top:0;width:28px;height:40px;z-index:2147483647;pointer-events:none;will-change:transform";
    el.innerHTML = '<svg width="28" height="40" viewBox="0 0 28 40" style="overflow:visible;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))">' +
      '<path d="M2 2 L2 31 L9.5 24 L14.5 36 L19 34 L14 22.5 L24 22.5 Z" fill="#000" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>';
    ring = document.createElement("div");
    ring.style.cssText = "position:fixed;left:0;top:0;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;" +
      "border:3px solid rgba(79,70,229,.85);z-index:2147483646;pointer-events:none;opacity:0";
    document.body.append(ring, el);
    place();
  };
  window.__unveoCursor = {
    moveTo(x, y, ms) {
      mount();
      const from = { ...pos }, t0 = performance.now();
      return new Promise(done => {
        const step = now => {
          const k = Math.min(1, (now - t0) / ms), e = ease(k);
          pos = { x: from.x + (x - from.x) * e, y: from.y + (y - from.y) * e };
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
