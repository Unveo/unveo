"""priority_score = 100 * strength * (0.5 + 0.5 * exposure). The rank of each finding follows it."""
import math

def strength(severity, weight):
    return severity * weight

def priority_score(finding, sc):
    s = strength(finding["severity"], sc.get("weight", 1.0))
    exposure = min(math.log10(finding.get("amount", 1e5) / 1e5) / 2, 1)
    priority_score = 100 * s * (0.5 + 0.5 * exposure)
    return priority_score

def rank(findings):
    ranked = sorted(findings, key=lambda f: f["rank"])
    return ranked
