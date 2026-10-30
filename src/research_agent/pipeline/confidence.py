"""Monotonic heuristic score, not a calibrated probability of correctness."""

from research_agent.schemas import Confidence, Evidence, Finding


def compute_confidence(
    evidence: list[Evidence],
    findings: list[Finding],
    *,
    grounding_rate: float,
    judge_score: float | None,
    failure_rate: float,
    gaps: int,
    mock: bool = False,
) -> Confidence:
    cited = {source_id for finding in findings for source_id in finding.source_ids}
    usable = [e for e in evidence if e.source.id in cited]
    domains = {
        e.source.domain.removeprefix("www.") for e in usable if e.source.quality_score >= 0.6
    }
    independent = min(len(domains) / 3, 1.0)
    # Conservative proxy: independent citations to the SAME finding. Not consensus proof.
    agreement = (
        sum(
            min(len({e.source.domain for e in usable if e.source.id in f.source_ids}) / 2, 1.0)
            for f in findings
        )
        / len(findings)
        if findings
        else 0
    )
    quality = sum(e.source.quality_score for e in usable) / len(usable) if usable else 0
    completeness = 1 / (1 + gaps)
    judge_signal = judge_score if judge_score is not None else 0.4
    factors = {
        "independent_sources": independent,
        "quality": quality,
        "grounding": grounding_rate,
        "agreement_proxy": agreement,
        "judge": judge_signal,
        "tool_health": 1 - failure_rate,
        "gap_coverage": completeness,
    }
    score = (
        0.20 * independent
        + 0.15 * quality
        + 0.25 * grounding_rate
        + 0.10 * agreement
        + 0.10 * judge_signal
        + 0.10 * (1 - failure_rate)
        + 0.10 * completeness
    )
    if not findings:
        score = min(score, 0.2)
    if judge_score is not None and judge_score < 0.5:
        score = min(score, 0.54)
        factors["judge_quality_guardrail"] = 0.54
    if mock:
        score = min(score, 0.5)  # Authored fixtures cannot justify real-world confidence.
    score = round(max(0, min(1, score)), 4)
    return Confidence(
        score=score,
        level="high" if score >= 0.8 else "medium" if score >= 0.55 else "low",
        factors=factors,
    )
