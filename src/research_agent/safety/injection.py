import re

PATTERNS = (
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"(?:assistant|ai|language model)\s*[:,].*(?:must|ignore|execute)",
    r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]",
    r"</?untrusted",
    r"\[/?(?:SYSTEM|INST)\]",
)


def detect_injection(text: str) -> list[str]:
    return [
        f"pattern_{index}"
        for index, pattern in enumerate(PATTERNS)
        if re.search(pattern, text, re.I | re.S)
    ]


def untrusted_payload(text: str) -> str:
    # JSON encoding is applied by the caller; literal boundary tokens are neutralized too.
    return (
        "<untrusted_evidence>"
        + text.replace("<", "\\u003c").replace(">", "\\u003e")
        + "</untrusted_evidence>"
    )
