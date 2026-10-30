"""Recover individually valid findings without inventing missing citations."""

import json

from pydantic import ValidationError

from research_agent.schemas import AnswerDraft, ComparisonTable, Finding


def recover_draft(raw: str) -> tuple[AnswerDraft, int] | None:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("key_findings"), list):
        return None
    valid: list[Finding] = []
    invalid = 0
    for candidate in data["key_findings"]:
        try:
            finding = Finding.model_validate(candidate)
            if len(valid) < 12:
                valid.append(finding)
            else:
                invalid += 1
        except ValidationError:
            invalid += 1
    if not valid or not invalid:
        return None
    candidate = dict(data)
    candidate["key_findings"] = [finding.model_dump() for finding in valid]
    try:
        if candidate.get("comparison_table") is not None:
            ComparisonTable.model_validate(candidate["comparison_table"])
    except ValidationError:
        candidate["comparison_table"] = None
    try:
        answer = AnswerDraft.model_validate(candidate)
    except ValidationError:
        return None
    answer.limitations.append(
        f"Removed {invalid} malformed finding(s); valid findings were preserved and still require citation verification."
    )
    return answer, invalid
