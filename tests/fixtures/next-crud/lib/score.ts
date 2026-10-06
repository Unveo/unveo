// Risk score: weighted sum of delay, cost overrun and missing documents.
const WEIGHTS = { delay: 0.4, overrun: 0.35, missingDocs: 0.25 };
export function computeRisk(p) {
  const delay = Math.min(p.delayDays / 365, 1);
  const overrun = p.costOverrunPct / 100;
  const missing = p.missingDocs / 5;
  const riskScore = Math.round(100 * (WEIGHTS.delay * delay + WEIGHTS.overrun * overrun + WEIGHTS.missingDocs * missing));
  return { riskScore };
}
