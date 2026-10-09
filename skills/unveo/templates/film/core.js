/* unveo film helpers. Adapted from howseen-ai/claude-motion-design core.js (MIT, see NOTICE):
   every visual value is a pure function of scene time t (seconds). No timers, no Date, no Math.random.
   Motion languages (docs/16 MO1): one per video (design.json "motion_style"). Every template routes its entrances
   (rise), its text (riseWords), its one emphasis (**word**) and the camera through the style, so the same scene
   moves differently in a Snap video than in a Cinematic one. */
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
    // a spring with no overshoot (critically damped), mapped onto 0..1
    soft: k => (k >= 1 ? 1 : (1 - (1 + 6 * k) * Math.exp(-6 * k)) / (1 - 7 * Math.exp(-6))),  // exactly 1 at the end
  };
  // closed-form spring 0 -> 1 (underdamped), t in seconds since start
  const spring = (t, f = 2.0, z = 0.6) => (t <= 0 ? 0 : 1 - Math.exp(-z * 2 * Math.PI * f * t) * Math.cos(2 * Math.PI * f * Math.sqrt(1 - z * z) * t));

  const sfx = (el, k, dy, f) => {  // set opacity and transform, and clear filter or clip once arrived
    el.style.opacity = clamp(f.o);
    el.style.transform = f.tf || "";
    el.style.filter = k < 0.999 && f.filter ? f.filter : "";
    el.style.clipPath = k < 0.999 && f.clip ? f.clip : "";
  };
  // entrance, text, emphasis and camera per motion language; the camera never moves more than 5%
  const STYLES = {
    glide: { speed: 1, ease: null, text: "rise", emph: "underline",
      enter: (k, dy) => ({ o: k * 1.4, tf: `translateY(${(1 - k) * dy * 0.7}px)` }),
      cam: q => ({ s: 1 + 0.03 * q }) },  // a steady push: an eased one barely moves for the first quarter of a long scene
    snap: { speed: 1.45, ease: E.outExpo, text: "pop", emph: "pill",
      enter: k => ({ o: k * 2.5, tf: `scale(${0.92 + 0.08 * E.outBack(k)})` }),
      cam: () => ({ s: 1 }) },
    cinematic: { speed: 0.72, ease: E.ioC, text: "blur", emph: "spot",
      enter: (k, dy) => ({ o: k * 1.2, tf: `translateY(${(1 - k) * dy * 0.3}px)`, filter: `blur(${(1 - k) * 12}px)` }),
      cam: q => ({ s: 1 + 0.05 * E.ioC(q), x: 10 - 20 * q }) },
    // typed text steps a character at a time; everything else eases in like the rest (a stepped card looks broken)
    typewriter: { speed: 1.2, ease: E.outC, text: "type", emph: "box",
      enter: (k, dy) => ({ o: k * 1.6, tf: `translateY(${(1 - k) * dy * 0.5}px)` }),
      cam: q => ({ s: 1 + 0.02 * q }) },
    draw: { speed: 0.95, ease: E.outC, text: "wipe", emph: "circle",
      enter: k => ({ o: k * 3, clip: `inset(-4% ${(1 - k) * 104}% -4% -4%)` }),
      cam: (q, t) => ({ s: 1.01, x: Math.sin(t * 0.5) * 6, y: Math.cos(t * 0.4) * 4 }) },
    blueprint: { speed: 0.9, ease: E.outC, text: "fade", emph: "dash",
      enter: k => ({ o: k * 1.5, clip: `inset(-4% -4% ${(1 - k) * 104}% -4%)` }),
      cam: q => ({ s: 1.02, x: 15 - 30 * q }) },
    stack: { speed: 1.1, ease: E.soft, text: "phrase", emph: "lift",
      enter: k => ({ o: k * 1.6, tf: `translateX(${(1 - k) * 140}px) scale(${0.97 + 0.03 * k})` }),
      cam: q => ({ s: 1.01, x: 24 - 48 * q }) },
    kinetic: { speed: 1.8, ease: E.outExpo, text: "cut", emph: "invert",
      enter: k => ({ o: k * 3, tf: `scale(${1.12 - 0.12 * k})` }),
      cam: q => ({ s: 1 + 0.05 * E.outC(q) }) },
  };
  const style = () => STYLES[window.MOTION_STYLE] || STYLES.glide;
  const speed = () => (window.CORE_SPEED || 1) * style().speed;  // design.json "motion": calm 1, lively 1.25
  // eased progress of an entrance that starts at t0 and lasts d; the motion language swaps the house easings
  const p = (t, t0, d = 0.6, e = E.outC) => {
    const st = style();
    return (st.ease && (e === E.outC || e === E.outExpo) ? st.ease : e)(inv(t0, t0 + d / speed(), t));
  };
  const h = (tag, cls, html, style) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (html != null) el.innerHTML = html;
    if (style) el.style.cssText = style;
    return el;
  };
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // text with its one emphasis: **the key words** become one <span class="em"> (CORE.emphasis draws it)
  const rich = s => esc(String(s == null ? "" : s)).replace(/\*\*(.+?)\*\*/, '<span class="em">$1</span>').replace(/\*\*/g, "");
  // word-by-word text: build once, then animate per frame. The **marked** phrase is one .em around its words, so its
  // box or underline is one shape per line, not one per word
  function words(el, text) {
    const word = w => `<span class="mask"><span class="w">${esc(w)}</span></span>`;
    const run = t => t.split(/\s+/).filter(Boolean).map(word).join(" ");
    const m = String(text == null ? "" : text).match(/^([\s\S]*?)\*\*(.+?)\*\*([\s\S]*)$/);
    el.innerHTML = m ? [run(m[1]), `<span class="em">${run(m[2])}</span>`, run(m[3].replace(/\*\*/g, ""))].filter(Boolean).join(" ")
      : run(String(text == null ? "" : text).replace(/\*\*/g, ""));
    el.__w = [...el.querySelectorAll(".w")];
    el.__ls = el.style.letterSpacing || "0em";
    return el;
  }
  function riseWords(el, t, t0, stagger = 0.055, d = 0.55) {
    const mode = style().text, W = el.__w;
    if (mode === "type") {  // typed a character at a time at speech pace; a block cursor rides the line being typed
      const cps = 30 * speed(), lens = W.map(w => w.textContent.length + 1), all = lens.reduce((a, b) => a + b, 0);
      let n = Math.max(0, Math.floor((t - t0) * cps)), cur = null;
      W.forEach((w, i) => {
        const f = clamp(n / lens[i]);
        n -= lens[i];
        w.style.opacity = f > 0 ? 1 : 0;
        w.style.clipPath = f < 1 ? `inset(-10% ${(1 - f) * 100}% -10% 0)` : "";
        w.parentElement.classList.remove("cur");
        if (f > 0 && f < 1) cur = [w, f];
      });
      const left = t - t0 - all / cps;  // seconds since the line finished: the cursor stays 0.4 s, then goes
      if (!cur && left >= 0 && left < 0.4) cur = [W[W.length - 1], 1];
      if (cur) cursor.claim(t0, () => { cur[0].parentElement.classList.add("cur"); cur[0].parentElement.style.setProperty("--f", cur[1]); },
                            () => cur[0].parentElement.classList.remove("cur"));
      return;
    }
    if (mode === "blur") {  // the line sharpens out of a blur while its letter-spacing tightens
      W.forEach((w, i) => {
        const k = p(t, t0 + i * stagger * 0.5, d * 1.8, E.ioC);
        w.style.opacity = k; w.style.filter = k < 0.999 ? `blur(${(1 - k) * 10}px)` : ""; w.style.transform = "";
      });
      el.style.letterSpacing = `calc(${el.__ls} + ${(1 - p(t, t0, d * 2.4, E.ioC)) * 0.06}em)`;
      return;
    }
    W.forEach((w, i) => {
      if (mode === "pop") {
        const k = p(t, t0 + i * stagger * 0.8, d * 0.8, E.outExpo);
        w.style.transform = `translateY(${(1 - k) * 60}%) scale(${0.8 + 0.2 * E.outBack(k)})`;
        w.style.opacity = clamp(k * 3);
      } else if (mode === "wipe") {
        const k = p(t, t0 + i * stagger * 1.4, d, E.outC);
        w.style.clipPath = k < 0.999 ? `inset(-10% ${(1 - k) * 100}% -10% 0)` : "";
        w.style.opacity = k > 0 ? 1 : 0;
      } else if (mode === "fade") {
        w.style.opacity = p(t, t0 + i * stagger, d * 1.4, E.outC);
      } else if (mode === "phrase") {  // groups of three words travel together
        const k = p(t, t0 + Math.floor(i / 3) * stagger * 3, d, E.outC);
        w.style.transform = `translateY(${(1 - k) * 80}%)`;
        w.style.opacity = clamp(k * 1.5);
      } else if (mode === "cut") {
        const k = p(t, t0 + i * stagger * 0.7, 0.25, E.outExpo);
        w.style.transform = `scale(${1.25 - 0.25 * k})`;
        w.style.opacity = clamp(k * 4);
      } else {
        const k = p(t, t0 + i * stagger, d, E.outExpo);
        w.style.transform = `translateY(${(1 - k) * 105}%) rotate(${(1 - k) * 4}deg)`;
        w.style.opacity = k > 0 ? 1 : 0;
      }
    });
  }
  function rise(el, k, dy = 36) { sfx(el, k, dy, style().enter(k, dy)); }
  // one cursor on screen at most: the line that started typing last keeps it (film.js resets this every frame).
  // key: when it started, in scene seconds (bigger = later)
  const cursor = {
    owner: null,
    reset() { this.owner = null; },
    claim(key, show, hide) {
      if (this.owner && this.owner.key > key) return hide();
      if (this.owner) this.owner.hide();
      this.owner = { key, hide };
      show();
    },
  };
  // the scene's one emphasis (docs/16 MO1): drawn on the .em phrase once it has arrived; k 0..1. The .em is inline,
  // and box-decoration-break: clone gives a phrase that wraps one clean shape per line. A box or pill only suits
  // a few words: a longer phrase gets the underline
  function emphasis(root, k) {
    const ems = [...root.querySelectorAll(".em")];
    if (!ems.length) return;
    const acc = "var(--accent)", mix = (c, a) => `color-mix(in srgb, ${c} ${Math.round(clamp(a) * 100)}%, transparent)`;
    ems.forEach((em, i) => {
      let kind = style().emph;
      if (["box", "pill", "invert", "circle"].includes(kind) && em.textContent.trim().split(/\s+/).length > 3) kind = "underline";
      const s = em.style;
      if (kind === "spot") root.querySelectorAll(".w").forEach(w => { if (!w.closest(".em")) w.style.opacity = Math.min(Number(w.style.opacity || 1), 1 - 0.3 * k); });
      if (kind === "underline" || kind === "dash") {
        s.backgroundImage = kind === "dash" ? `repeating-linear-gradient(90deg, ${acc} 0 .3em, transparent .3em .5em)` : `linear-gradient(${acc}, ${acc})`;
        s.backgroundRepeat = "no-repeat"; s.backgroundPosition = "0 100%"; s.backgroundSize = `${clamp(k) * 100}% .08em`;
      } else if (kind === "box") {  // a ring drawn with box-shadow: unlike outline, it follows each line of the phrase
        s.boxShadow = `0 0 0 .08em ${mix(acc, k * 3)}`;
        s.borderRadius = ".08em";
      } else if (kind === "pill" || kind === "invert") {
        const c = kind === "pill" ? acc : "var(--ink)";
        s.backgroundColor = mix(c, k);
        s.boxShadow = `0 0 0 .12em ${mix(c, k)}`;
        s.borderRadius = kind === "pill" ? ".18em" : "0";
        s.color = k > 0.5 ? (kind === "pill" ? "var(--on-accent)" : "var(--bg)") : "";
      } else if (kind === "spot" || kind === "lift") {
        s.color = `color-mix(in srgb, ${acc} ${Math.round(k * 100)}%, var(--ink))`;
        if (kind === "lift") { s.position = "relative"; s.top = `${-0.08 * k}em`; }
      } else if (kind === "circle" && i === 0) {  // a hand-drawn ring around the phrase
        let svg = em.__ring;
        if (!svg) {
          svg = em.__ring = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          svg.setAttribute("viewBox", "0 0 100 40"); svg.setAttribute("preserveAspectRatio", "none");
          svg.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible;pointer-events:none";
          svg.innerHTML = `<path d="M-4 22 C -6 0, 74 -6, 102 8 C 114 18, 92 46, 46 45 C 2 44, -12 30, 4 6" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round" pathLength="1" stroke-dasharray="1" vector-effect="non-scaling-stroke"/>`;
          em.style.position = "relative"; em.style.display = "inline-block";  // ≤ 3 words: one line, so the ring has one box
          em.append(svg);
        }
        svg.firstChild.style.strokeDashoffset = 1 - k;
      }
    });
  }
  // the camera: one transform for the whole scene, plus a last-moment zoom into the answer (MO3)
  function camera(t, dur, focus) {
    const c = style().cam(clamp(t / Math.max(0.1, dur)), t);
    const s = c.s || 1, dx = c.x || 0, dy = c.y || 0, cx = 960, cy = 540;
    let z = 1, fx = cx, fy = cy;
    if (focus) {
      z = 1 + (focus.z || 0.1) * E.ioC(inv(dur - 0.75, dur - 0.1, t));
      fx = focus.x; fy = focus.y;
    }
    // scale s about the centre, shift, then zoom z about the focus: x -> z*s*x + z*(c(1-s) + d - f) + f
    const tx = fx + z * (cx * (1 - s) + dx - fx), ty = fy + z * (cy * (1 - s) + dy - fy);
    return `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${(z * s).toFixed(5)})`;
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
    const q = h("div", "abs h", null, "left:120px;top:96px;width:1500px;font:600 var(--h2)/1.12 var(--font-display);letter-spacing:-.02em");
    words(q, text || "");
    root.append(q);
    return q;
  }
  window.CORE = { clamp, lerp, inv, E, spring, p, h, esc, rich, words, riseWords, rise, emphasis, camera, drift, num, beat, exampleTag,
                  question, cursor, STYLES, style };
})();
