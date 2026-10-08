/* unveo privacy: blur personal data on the recorded page before a frame is captured (docs/16 R5).
   Emails, phone numbers and password fields get a frosted box drawn over them in an overlay of our own, so the
   app's DOM is never touched (React and friends keep working). window.__UNVEO_PRIVACY === false turns it off.
   window.__unveoPrivacy holds what was blurred, for record.json. */
(() => {
  if (window.__unveoPrivacy || window.__UNVEO_PRIVACY === false) return;
  const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}/g;
  const PHONE = /\+\d{1,3}[\s.-]?\(?\d{2,5}\)?(?:[\s.-]?\d{2,5}){1,3}|\(\d{3}\)\s?\d{3}[\s.-]\d{4}|\b\d{3}[.-]\d{3}[.-]\d{4}\b/g;
  const DEMO = /@(?:example\.(?:com|org|net)|test\.com|demo\.com)$/i;  // made-up demo data stays readable
  const digits = s => s.replace(/\D/g, "").length;
  const seen = { emails: new Set(), phones: new Set(), passwords: 0 };
  window.__unveoPrivacy = { stats: () => ({ emails: seen.emails.size, phones: seen.phones.size, passwords: seen.passwords }) };
  const hits = text => {
    const out = [];
    for (const m of text.matchAll(EMAIL)) if (!DEMO.test(m[0])) { out.push([m.index, m[0].length]); seen.emails.add(m[0]); }
    for (const m of text.matchAll(PHONE)) {
      const n = digits(m[0]);
      if (n >= 9 && n <= 15) { out.push([m.index, m[0].length]); seen.phones.add(m[0]); }
    }
    return out;
  };
  let layer, found = [], dirty = true;
  const ours = e => e && e.closest && e.closest("[data-unveo], #__unveo_guide");
  function collect() {  // which text nodes and fields hold personal data; redone only when the page changes
    found = [];
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n; (n = tw.nextNode());) {
      const p = n.parentElement;
      if (!p || ours(p) || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(p.tagName) || n.data.length < 6) continue;
      for (const [i, len] of hits(n.data)) found.push({ node: n, i, len });
    }
    let pw = 0;
    for (const f of document.querySelectorAll("input, textarea")) {
      if (ours(f)) continue;
      if (f.type === "password" && f.value) { found.push({ el: f }); pw++; }
      else if (f.value && hits(f.value).length) found.push({ el: f });
    }
    seen.passwords = Math.max(seen.passwords, pw);
    dirty = false;
  }
  function paint() {
    if (!document.body) return requestAnimationFrame(paint);
    if (!layer || !layer.isConnected) {
      layer = document.createElement("div");
      layer.dataset.unveo = "privacy";
      layer.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483645";
      document.documentElement.append(layer);
    }
    if (dirty) collect();
    const boxes = [];
    for (const f of found) {
      if (f.el) { if (f.el.isConnected) boxes.push(f.el.getBoundingClientRect()); continue; }
      if (!f.node.isConnected || f.i + f.len > f.node.length) { dirty = true; continue; }
      const r = document.createRange();
      r.setStart(f.node, f.i); r.setEnd(f.node, f.i + f.len);
      boxes.push(...r.getClientRects());
    }
    while (layer.children.length < boxes.length) {
      const b = document.createElement("div");
      b.style.cssText = "position:fixed;border-radius:5px;backdrop-filter:blur(9px);-webkit-backdrop-filter:blur(9px);background:rgba(128,128,128,.28)";
      layer.append(b);
    }
    [...layer.children].forEach((b, k) => {
      const r = boxes[k];
      b.style.display = r && r.width ? "block" : "none";
      if (r) Object.assign(b.style, { left: r.left - 3 + "px", top: r.top - 2 + "px", width: r.width + 6 + "px", height: r.height + 4 + "px" });
    });
    requestAnimationFrame(paint);
  }
  // ponytail: a full text walk on every DOM change; fine for demo-sized pages, index changed subtrees if it ever lags
  new MutationObserver(() => { dirty = true; }).observe(document, { subtree: true, childList: true, characterData: true });
  addEventListener("input", () => { dirty = true; }, true);
  paint();
})();
