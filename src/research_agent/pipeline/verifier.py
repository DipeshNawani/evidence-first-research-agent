"""Quote presence proves provenance, not semantic entailment. No fuzzy acceptance."""

import re
import unicodedata

from research_agent.schemas import AnswerDraft, ComparisonRow, ComparisonTable, Evidence


def attribute_source_claims(answer: AnswerDraft, evidence: list[Evidence]) -> AnswerDraft:
    """Present retrieved claims as source reports, not independent confirmation."""
    by_id = {item.source.id: item.source for item in evidence}
    attributed = answer.model_copy(deep=True)
    for finding in attributed.key_findings:
        source = by_id.get(finding.source_ids[0])
        if source is None or finding.claim.startswith("Source ["):
            continue
        prefix = f"Source [{source.id}] ({source.domain[:100]}) reports: "
        if len(prefix) + len(finding.claim) <= 1500:
            finding.claim = prefix + finding.claim
    attributed, _, _ = verify(attributed, evidence)
    return attributed


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def verify(answer: AnswerDraft, evidence: list[Evidence]) -> tuple[AnswerDraft, float, list[str]]:
    by_id = {item.source.id: item for item in evidence}
    kept = []
    rejected = []
    pruned = 0
    for finding in answer.key_findings:
        quote = normalize(finding.supporting_quote)
        matched_ids = [
            source_id
            for source_id in finding.source_ids
            if source_id in by_id and quote in normalize(by_id[source_id].text)
        ]
        valid = len(quote) >= 12 and bool(matched_ids)
        if valid:
            pruned += len(finding.source_ids) - len(matched_ids)
            kept.append(finding.model_copy(update={"verified": True, "source_ids": matched_ids}))
        else:
            rejected.append(finding.claim)
    rate = len(kept) / len(answer.key_findings) if answer.key_findings else 0.0
    clean = answer.model_copy(deep=True)
    clean.key_findings = kept
    # Model summary and comparison cells could contain claims never cited by findings.
    # Rebuild both from retained findings so every published factual claim is auditable.
    clean.short_answer = (
        " ".join(
            f.claim if f.claim.rstrip().endswith((".", "!", "?")) else f.claim + "."
            for f in kept[:5]
        )
        if kept
        else "Insufficient verified evidence to answer reliably."
    )
    if answer.comparison_table:
        clean.comparison_table = (
            ComparisonTable(
                columns=["Supported observation"],
                rows=[
                    ComparisonRow(
                        item=by_id[f.source_ids[0]].source.title,
                        cells=[f.claim],
                        source_ids=f.source_ids,
                    )
                    for f in kept
                ],
            )
            if kept
            else None
        )
    if rejected:
        clean.limitations.append(
            f"Removed {len(rejected)} finding(s) with invalid or unsupported quotations."
        )
    if pruned:
        clean.limitations.append(
            f"Removed {pruned} citation(s) whose source did not contain the supporting quote."
        )
    return clean, rate, rejected
