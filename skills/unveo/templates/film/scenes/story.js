/* story scenes built from blocks (round 4): chapter, stat-hero, before-after, annotated-shot; terminal and notebook (audit round C).
   Each maps its data onto a compose layout, so they inherit auto-fit, the look and the entrances. */
(function () {
  const compose = () => window.__unveoScenes.compose;
  const via = map => ({
    build(root, d) { const c = compose(); c.build.call(c, root, map(d)); },
    fit(root) { const c = compose(); c.fit.call(c, root); },
    draw(t, d, dur, root) { const c = compose(); c.draw.call(c, t, root.__mapped || (root.__mapped = map(d)), dur, root); },
  });
  const motif = d => d.icon || ((window.TIMELINE.design || {}).motifs || [])[0];
  UNVEO.scene("chapter", via(d => ({ layout: "hero-icon", blocks: [
    { type: "icon", area: "icon", props: { icon: motif(d), size: 260 } },
    ...(d.number != null ? [{ type: "kicker", area: "main", props: { text: `Part ${d.number}` }, at: 0.15 }] : []),
    { type: "heading", area: "main", props: { text: d.title || "", size: 104 }, at: 0.3 }] })));
  UNVEO.scene("stat-hero", via(d => ({ layout: "hero-icon", blocks: [
    { type: "icon", area: "icon", props: { icon: motif(d), size: 240 } },
    { type: "big-number", area: "main", props: { value: d.value, label: d.label, source: d.source }, at: 0.2, enter: "count" }] })));
  UNVEO.scene("before-after", via(d => ({ layout: "stack", blocks: [
    ...(d.title ? [{ type: "heading", area: "top", props: { text: d.title } }] : []),
    { type: "compare", area: "middle", props: { before: d.before, after: d.after }, at: 0.3 }] })));
  // built-with (docs/16 S5): the stack's real logos and one cited sentence on the hardest part
  UNVEO.scene("built-with", via(d => ({ layout: "centered-hero", blocks: [
    { type: "kicker", area: "main", props: { text: d.kicker || "Built with" } },
    { type: "logo-wall", area: "main", props: { items: d.logos || [], size: 104 }, at: 0.25 },
    ...(d.line ? [{ type: "text", area: "below", props: { text: d.line }, at: 1.0 }] : [])] })));
  // terminal and notebook (docs/16 CO1, CO3, CO5): render.py fills in the real run from outputs.py; nothing is typed by hand
  const titled = (d, block, layout, side) => ({ layout: d.heading ? layout : "full-type", blocks: [
    ...(d.heading ? [{ type: "heading", area: side, props: { text: d.heading } }] : []),
    { ...block, area: "main", at: d.heading ? 0.3 : 0 }] });
  UNVEO.scene("terminal", via(d => titled(d, { type: "terminal",  // big type; auto-fit shrinks a long output
    props: { command: d.command, output: d.output, title: d.title, key: d.key, size: d.heading ? 32 : 46 } }, "hero", "title")));
  UNVEO.scene("notebook", via(d => titled(d, { type: "notebook", props: { cells: d.cells, path: d.path } }, "left-heavy", "side")));
  UNVEO.scene("annotated-shot", via(d => ({ layout: "full-bleed-shot", blocks: [
    { type: "callout", area: "shot", props: { src: d.src || "assets/probe.png", pins: d.pins || [] }, at: 0.1 },
    { type: "heading", area: "caption", props: { text: d.title || "" }, at: 0.4 }] })));
})();
