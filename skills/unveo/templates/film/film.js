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
        return (built[s.id] = { el, def, s });
      };
      let shown = null;
      window.seek = t => {
        const [s, lt] = at(Math.max(0, t));
        const r = root(s);
        if (shown && shown !== r) shown.el.style.visibility = "hidden";
        r.el.style.visibility = "inherit";
        shown = r;
        r.def.draw(Math.min(lt, s.dur_s), s.data || {}, s.dur_s, r.el);
        return lt;
      };
      // build every scene up front so fonts and images load before the first capture
      list.forEach(root);
      const imgs = [...document.images].map(i => (i.complete ? null : new Promise(r => { i.onload = i.onerror = r; })));
      Promise.all([document.fonts.ready, ...imgs]).then(() => {
        Object.values(built).forEach(r => r.def.fit && r.def.fit(r.el));  // re-fit text now the real fonts are in
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
