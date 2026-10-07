/* What the person sees in the browser unveo opens: a yellow bar and a dotted pointer while they log in, a yellow
   "Recording…" screen before each scene, a green "Done" screen at the end. capture.py removes it before the camera
   starts, so none of it is ever in the video. Lives in a shadow root so the app's CSS can't touch it. */
(() => {
  if (window.__unveo) return;
  const YELLOW = "#fdfa8d", INK = "#111111";
  const SIGN_IN = /sign\s?in|log\s?in|login|continue with|google|github/i;
  let host, root, raf = 0, target = null, box = null;

  function mount() {
    if (host && host.isConnected) return;
    host = document.createElement("div");
    host.id = "__unveo_guide";
    host.style.cssText = "position:fixed;inset:0;z-index:2147483647;pointer-events:none";
    root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>
      * { box-sizing: border-box; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
      .bar { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); max-width: calc(100% - 32px);
             background: ${YELLOW}; color: ${INK}; padding: 12px 20px; border-radius: 14px; border: 1.5px solid ${INK};
             font: 600 15px/1.4 system-ui, sans-serif; display: flex; gap: 12px; align-items: center; box-shadow: 0 8px 24px rgba(0,0,0,.18); }
      .logo { font: 800 16px/1 system-ui, sans-serif; letter-spacing: -.04em; }
      .ring { position: fixed; border: 3px dashed ${INK}; border-radius: 12px; box-shadow: 0 0 0 4px ${YELLOW};
              animation: pulse 1.4s ease-in-out infinite; }
      .tip { position: fixed; background: ${INK}; color: #fff; font: 600 14px system-ui, sans-serif; padding: 7px 12px; border-radius: 8px; white-space: nowrap; }
      svg { position: fixed; overflow: visible; }
      .screen { position: fixed; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; color: ${INK}; }
      .screen .big { font: 700 44px/1.1 system-ui, sans-serif; letter-spacing: -.02em; }
      .screen .small { font: 500 18px system-ui, sans-serif; opacity: .75; }
      .rec { width: 14px; height: 14px; border-radius: 50%; background: #e5484d; display: inline-block; margin-right: 12px; vertical-align: middle; animation: blink 1s infinite; }
      @keyframes pulse { 50% { transform: scale(1.04); } }
      @keyframes blink { 50% { opacity: .25; } }
    </style><div class="layer"></div>`;
    document.documentElement.appendChild(host);
  }
  const layer = () => root.querySelector(".layer");

  function findSignIn() {
    const els = [...document.querySelectorAll('button, a, [role="button"], input[type="submit"], iframe')];
    return els.find(el => {
      const r = el.getBoundingClientRect();
      if (r.width < 8 || r.height < 8 || getComputedStyle(el).visibility === "hidden") return false;
      if (el.tagName === "IFRAME") return /accounts\.google\.com|github\.com/.test(el.src || "");
      return SIGN_IN.test((el.innerText || el.value || el.getAttribute("aria-label") || "").trim());
    }) || null;
  }

  function place() {
    const ring = root.querySelector(".ring");
    if (!ring) return;
    const r = target && target.isConnected ? target.getBoundingClientRect() : box;
    const tip = root.querySelector(".tip"), svg = root.querySelector("svg");
    if (!r) { ring.style.display = tip.style.display = svg.style.display = "none"; return; }
    const pad = 10, x = r.x - pad, y = r.y - pad, w = r.width + 2 * pad, h = r.height + 2 * pad;
    Object.assign(ring.style, { display: "block", left: x + "px", top: y + "px", width: w + "px", height: h + "px" });
    const above = y > 120;  // put the hint above the ring when there's room, else below
    const tx = Math.max(12, x - 40), ty = above ? y - 86 : y + h + 48;
    Object.assign(tip.style, { display: "block", left: tx + "px", top: ty + "px" });
    const sx = tx + 30, sy = above ? ty + 36 : ty - 4, ex = x + Math.min(48, w / 2), ey = above ? y - 6 : y + h + 6;
    const a = Math.atan2(ey - sy, ex - sx), head = (d) => `${ex - 12 * Math.cos(a + d)} ${ey - 12 * Math.sin(a + d)}`;
    svg.style.display = "block";
    svg.innerHTML = `<path d="M${sx} ${sy} L${ex} ${ey}" fill="none" stroke="${INK}" stroke-width="3" stroke-dasharray="6 6"/>
      <path d="M${head(0.5)} L${ex} ${ey} L${head(-0.5)}" fill="none" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/>`;
  }
  function loop() { place(); raf = requestAnimationFrame(loop); }

  window.__unveo = {
    login(message, point) {  // point: null = find the sign-in button, false = no pointer, {x,y,width,height} = this box
      mount();
      if (!root.querySelector(".bar")) {
        layer().innerHTML = `<div class="bar"><span class="logo">/u.</span><span class="msg"></span></div>
          <div class="ring"></div><div class="tip">Click here to log in</div><svg width="1" height="1"></svg>`;
        cancelAnimationFrame(raf); loop();
      }
      root.querySelector(".msg").textContent = message;
      box = point || null;
      target = point === null ? findSignIn() : null;
      place();
      return true;
    },
    screen(kind, big, small) {  // kind: "rec" (yellow, before a scene) or "done" (green)
      mount(); cancelAnimationFrame(raf); target = box = null;
      const bg = kind === "done" ? "#e7f6ec" : YELLOW;
      layer().innerHTML = `<div class="screen" style="background:${bg}"><div class="big">${kind === "rec" ? '<span class="rec"></span>' : ""}</div><div class="small"></div></div>`;
      root.querySelector(".big").append(big);
      root.querySelector(".small").textContent = small || "";
      return true;
    },
    clear() { cancelAnimationFrame(raf); target = box = null; if (host) host.remove(); host = root = null; return true; },
  };
})();
