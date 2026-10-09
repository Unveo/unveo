/* unveo film runtime: one page, every frame a pure function of time.
   ?scene=sNN renders one scene in its own clock (0..dur); no parameter plays the whole timeline (preview).
   &w=960 renders smaller (draft). */
(function () {
  const SCENES = {};
  window.__unveoScenes = SCENES;  // story.js builds on compose
  const q = new URLSearchParams(location.search);
  const only = q.get("scene"), W = Number(q.get("w") || 1920);
  const built = {};
  window.UNVEO = {
    scene(name, def) { SCENES[name] = def; },
    start() {
      const T = window.TIMELINE;
      const stage = document.getElementById("stage");
      const D = T.design || {};
      if (D.background && D.background !== "plain") stage.classList.add("bg-" + D.background);
      window.CORE_SPEED = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--motion-speed")) || 1;
      window.MOTION_STYLE = D.motion_style || "glide";
      stage.style.transform = `scale(${W / 1920})`;
      document.body.style.width = W + "px";
      const list = T.scenes.filter(s => (only ? s.id === only : true));
      const at = t => {
        if (only) return [list[0], t];
        let s = list[list.length - 1];
        for (const x of list) if (t < x.start_s + x.dur_s) { s = x; break; }
        return [s, t - s.start_s];
      };
      const root = s => {
        if (built[s.id]) return built[s.id];
        const el = document.createElement("div");
        el.className = "scene";
        el.dataset.id = s.id;
        el.dataset.template = s.template;
        stage.append(el);
        const def = SCENES[s.template] || SCENES.placeholder;
        def.build(el, s.data || {}, s);
        if (s.data && s.data.backdrop_img && s.template !== "title") {  // the recording just shown, frozen behind (MO2)
          el.__bd = document.createElement("div");
          el.__bd.className = "abs";
          el.__bd.style.cssText = `inset:0;background:url(${s.data.backdrop_img}) center/cover`;
          el.prepend(el.__bd);
        }
        // the camera layer (docs/16 MO1): everything the scene built moves as one, by the motion language
        const cam = document.createElement("div");
        cam.className = "cam";
        cam.append(...el.childNodes);
        el.append(cam);
        return (built[s.id] = { el, cam, def, s });
      };
      let shown = null;
      window.seek = t => {
        const [s, lt] = at(Math.max(0, t));
        const r = root(s);
        if (shown && shown !== r) shown.el.style.visibility = "hidden";
        r.el.style.visibility = "inherit";
        shown = r;
        const tt = Math.min(lt, s.dur_s), d = s.data || {};
        if (r.el.__bd) {
          const k = CORE.p(tt, 0, 0.7, CORE.E.ioC);
          r.el.__bd.style.filter = `blur(${k * 14}px)`;
          r.el.__bd.style.transform = `scale(${1 + 0.05 * k})`;  // exactly the frame it fades in over, then oversized under the blur
          r.el.__bd.style.opacity = 1 - 0.7 * k;
        }
        CORE.cursor.reset();
        r.def.draw(tt, d, s.dur_s, r.el);
        const emAt = typeof d.emphasis_at === "number" ? d.emphasis_at : Math.max(1.4, Math.min(s.dur_s * 0.4, 3));
        CORE.emphasis(r.el, CORE.p(tt, emAt, 0.6, CORE.E.ioC));
        r.cam.style.transform = s.visual === "anim" && d.camera !== false ? CORE.camera(tt, s.dur_s, r.focus) : "";
        const T = (s.start_s || 0) + tt;  // the film's own clock, so a moving background runs on across cuts
        stage.style.setProperty("--bx", `${(Math.sin(T * 0.07) * 6).toFixed(3)}%`);
        stage.style.setProperty("--by", `${(Math.cos(T * 0.05) * 4).toFixed(3)}%`);
        return lt;
      };
      // build every scene up front so fonts and images load before the first capture
      list.forEach(root);
      const imgs = [...document.images].map(i => (i.complete ? null : new Promise(r => { i.onload = i.onerror = r; })));
      Promise.all([document.fonts.ready, ...imgs]).then(() => {
        Object.values(built).forEach(r => r.def.fit && r.def.fit(r.el));  // re-fit text now the real fonts are in
        Object.values(built).forEach(r => {  // where the explainer's answer is, for its last-moment zoom (MO3)
          const f = r.el.__focus;
          if (!f) return;
          r.el.style.visibility = "inherit";
          const a = f.getBoundingClientRect(), st = stage.getBoundingClientRect(), k = W / 1920;
          r.focus = { x: (a.left + a.width / 2 - st.left) / k, y: (a.top + a.height / 2 - st.top) / k, z: r.el.__focusZ || 0.1 };
          // the answer's box at the scene's end (after its zoom), for the match cut into the next recording (docs/16 MO2)
          const z = 1 + r.focus.z, bw = a.width / k * z, bh = a.height / k * z;
          (window.__unveoFocus = window.__unveoFocus || {})[r.s.id] = [r.focus.x - bw / 2, r.focus.y - bh / 2, bw, bh].map(v => Math.round(v));
          r.el.style.visibility = "hidden";
        });
        window.seek(0);
        window.ready = true;
      });
      // preview controls (the render never uses them): Space play/pause, arrows step a frame, R restart
      if (!navigator.webdriver) {
        const total = only ? list[0].dur_s : list.reduce((a, s) => a + s.dur_s, 0);
        let t = 0, playing = false, last = 0;
        const hud = document.getElementById("hud");
        const show = () => { window.seek(t); hud.textContent = `${t.toFixed(2)} / ${total.toFixed(2)} s  (space, arrows, R)`; };
        const loop = now => { if (playing) { t = Math.min(total, t + (now - last) / 1000); last = now; show(); requestAnimationFrame(loop); } };
        addEventListener("keydown", e => {
          if (e.key === " ") { playing = !playing; last = performance.now(); requestAnimationFrame(loop); }
          if (e.key === "ArrowRight") { t = Math.min(total, t + 1 / 30); show(); }
          if (e.key === "ArrowLeft") { t = Math.max(0, t - 1 / 30); show(); }
          if (e.key === "r" || e.key === "R") { t = 0; show(); }
        });
        setTimeout(show, 300);
      }
    },
  };
})();
