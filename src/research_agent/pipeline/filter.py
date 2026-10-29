"""Transparent ranking and duplicate filtering. Heuristics are not authority proof."""

import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from research_agent.config import Settings
from research_agent.safety.injection import detect_injection
from research_agent.safety.url_guard import validate_url
from research_agent.schemas import DroppedSource, Evidence, FilterResult, SearchHit, Source
from research_agent.tools.base import ToolError

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "what",
    "using",
    "different",
    "find",
    "compare",
    "research",
    "top",
    "building",
}


def canonical_url(url: str) -> str:
    parsed = validate_url(url)
    query = urlencode(
        sorted(
            (k, v)
            for k, v in parse_qsl(parsed.query)
            if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
        )
    )
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", query, "")
    )


def words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) > 2 and word not in STOPWORDS
    }


def score_source(hit: SearchHit, text: str, question: str) -> float:
    host = (urlsplit(hit.url).hostname or "").lower()
    terms = words(question)
    relevance = min(1.0, len(terms & words(hit.title + " " + text)) / max(1, min(len(terms), 7)))
    reputation = 0.55
    if (
        host == "github.com"
        or host == "arxiv.org"
        or host.endswith((".gov", ".edu"))
        or host.startswith("docs.")
        or "/docs" in hit.url
        or "/documentation" in hit.url
    ):
        reputation = 0.9
    if host in {"reddit.com", "www.reddit.com", "quora.com"}:
        reputation = 0.25
    spam = bool(
        re.search(
            r"affiliate|sponsored|buy now|top[- ]?100|best-tools",
            hit.title + " " + text + " " + host,
            re.I,
        )
    )
    recency = 0.5  # Unknown publication date is not 'fresh'.
    if hit.published_at:
        age = (datetime.now(UTC) - hit.published_at.astimezone(UTC)).days
        recency = 1.0 if 0 <= age <= 365 else (0.6 if age <= 1095 else 0.2)
    quality = min(1.0, len(text.strip()) / 350)
    score = 0.35 * relevance + 0.30 * reputation + 0.25 * quality + 0.10 * recency
    if relevance < 0.12:
        score *= 0.3
    return round(max(0, score - (0.55 if spam else 0)), 4)


def filter_sources(
    candidates: list[tuple[SearchHit, str, str, list[str]]],
    question: str,
    settings: Settings,
    *,
    mock: bool = False,
) -> FilterResult:
    result = FilterResult()
    seen: dict[str, Evidence] = {}
    ranked: list[Evidence] = []
    for hit, body, provenance, ids in candidates:
        reason = ""
        try:
            url = canonical_url(hit.url)
        except ToolError:
            result.dropped_sources.append(DroppedSource(url=hit.url, reason="unsafe_url"))
            continue
        if detect_injection(body) or detect_injection(hit.title):
            reason = "injection_quarantined"
        elif url in seen:
            seen[url].sub_question_ids = sorted(set(seen[url].sub_question_ids + ids))
            reason = "duplicate_url"
        elif any(
            SequenceMatcher(
                None, body[:2000].lower(), e.text[:2000].lower(), autojunk=False
            ).ratio()
            > 0.90
            for e in ranked
        ):
            reason = "near_duplicate_text"
        score = score_source(hit, body, question)
        if not reason and (len(body.strip()) < 60 or score < settings.source_threshold):
            reason = "low_quality_or_relevance"
        if reason:
            result.dropped_sources.append(DroppedSource(url=hit.url, reason=reason))
            continue
        source = Source(
            id="pending",
            title=hit.title,
            url=url,
            domain=urlsplit(url).hostname or "",
            quality_score=score,
            retrieved_at=hit.retrieved_at,
            provenance="fixture" if mock else "page" if provenance == "page" else "snippet",
        )
        evidence = Evidence(
            source=source, text=body[: settings.evidence_chars], sub_question_ids=ids
        )
        seen[url] = evidence
        ranked.append(evidence)
    ranked.sort(key=lambda e: (-e.source.quality_score, e.source.url))
    for evidence in ranked[settings.max_evidence :]:
        result.dropped_sources.append(
            DroppedSource(url=evidence.source.url, reason="evidence_budget")
        )
    result.evidence = ranked[: settings.max_evidence]
    for index, evidence in enumerate(result.evidence, 1):
        evidence.source.id = f"S{index}"
    return result
