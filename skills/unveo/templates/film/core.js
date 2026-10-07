/* unveo film helpers. Adapted from howseen-ai/claude-motion-design core.js (MIT, see NOTICE):
   every visual value is a pure function of scene time t (seconds). No timers, no Date, no Math.random. */
(function () {
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, k) => a + (b - a) * k;
  const inv = (a, b, x) => clamp((x - a) / (b - a));
  const E = {
    lin: k => k,
    outQ: k => 1 - (1 - k) * (1 - k),
    outC: k => 1 - Math.pow(1 - k, 3),
    ioC: k => (k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    outExpo: k => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)),
    outBack: k => { const c = 1.70158, c3 = c + 1; return 1 + c3 * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); },
  };
  // closed-form spring 0 -> 1 (underdamped), t in seconds since start
  const spring = (t, f = 2.0, z = 0.6) => (t <= 0 ? 0 : 1 - Math.exp(-z * 2 * Math.PI * f * t) * Math.cos(2 * Math.PI * f * Math.sqrt(1 - z * z) * t));
  // eased progress of an entrance that starts at t0 and lasts d
  const speed = () => window.CORE_SPEED || 1;  // design.json "motion": calm 1, lively 1.25
  const p = (t, t0, d = 0.6, e = E.outC) => e(inv(t0, t0 + d / speed(), t));
  const h = (tag, cls, html, style) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (html != null) el.innerHTML = html;
    if (style) el.style.cssText = style;
    return el;
  };
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // word-by-word masked rise: build once, then animate per frame
  function words(el, text) {
    el.innerHTML = String(text).split(/\s+/).filter(Boolean)
      .map(w => `<span class="mask"><span class="w">${esc(w)}</span></span>`).join(" ");
    el.__w = [...el.querySelectorAll(".w")];
    return el;
  }
  function riseWords(el, t, t0, stagger = 0.055, d = 0.55) {
    el.__w.forEach((w, i) => {
      const k = p(t, t0 + i * stagger, d, E.outExpo);
      w.style.transform = `translateY(${(1 - k) * 105}%) rotate(${(1 - k) * 4}deg)`;
      w.style.opacity = k > 0 ? 1 : 0;
    });
  }
  function rise(el, k, dy = 36) {
    el.style.opacity = clamp(k * 1.4);
    el.style.transform = `translateY(${(1 - k) * dy}px)`;
  }
  // a slow living drift so no frame is frozen
  const drift = (t, amp = 6, sp = 0.35, ph = 0) => Math.sin(t * sp + ph) * amp;
  const num = (v, digits) => {
    const n = Number(v);
    if (!isFinite(n)) return String(v);
    return n.toLocaleString("en-IN", { maximumFractionDigits: digits == null ? (Math.abs(n) < 10 ? 2 : 0) : digits });
  };
  // when beat i starts: data.beats if given, else spread across the scene
  const beat = (data, i, dur, n) => (data.beats && data.beats[i] != null ? data.beats[i] : (dur * 0.82 * i) / Math.max(1, n));
  function exampleTag(root, data) {
    if (data.example_data) root.append(h("div", "tag", "Example data"));
  }
  function question(root, text) {
    const q = h("div", "abs", null, "left:120px;top:96px;width:1500px;font:600 64px/1.12 var(--font-display);letter-spacing:-.02em");
    words(q, text || "");
    root.append(q);
    return q;
  }
  window.CORE = { clamp, lerp, inv, E, spring, p, h, esc, words, riseWords, rise, drift, num, beat, exampleTag, question };
})();
