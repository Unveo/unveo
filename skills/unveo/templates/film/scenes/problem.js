/* problem: { eyebrow?, headline, pains: [≤3 strings], stat?: { value, label, source } } */
UNVEO.scene("problem", {
  build(root, d) { CORE_LIST.build(root, d, d.eyebrow || "The problem", true); },
  draw(t, d, dur, root) { CORE_LIST.draw(t, d, dur, root); },
});
