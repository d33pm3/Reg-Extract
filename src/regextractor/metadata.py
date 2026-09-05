from __future__ import annotations

import re
from typing import List, Optional, Tuple

REPLACEMENT = "\ufffd"

PROHIBITORY_PATTERNS = [
    re.compile(r"\bshall not\b", re.I),
    re.compile(r"\bmust not\b", re.I),
    re.compile(r"\bmay not\b", re.I),
    re.compile(r"\bprohibited\b", re.I),
]
MANDATORY_PATTERNS = [
    re.compile(r"\bshall\b", re.I),
    re.compile(r"\bmust\b", re.I),
    re.compile(r"\bis required to\b", re.I),
    re.compile(r"\bare required to\b", re.I),
]
DISCRETIONARY_PATTERNS = [
    re.compile(r"\bat its discretion\b", re.I),
    re.compile(r"\bmay consider\b", re.I),
    re.compile(r"\bmay\b", re.I),
]

ENTITY_PATTERNS = [
    re.compile(r"\bthe Board\b", re.I),
    re.compile(r"\bBranch Manager\b", re.I),
    re.compile(r"\bRegulated Entit(?:y|ies)\b", re.I),
    re.compile(r"\bA bank\b"),
    re.compile(r"\bThe bank\b", re.I),
    re.compile(r"\bbanks\b", re.I),
    re.compile(r"\bthe borrower(?:s)?\b", re.I),
    re.compile(r"\bthe customer(?:s)?\b", re.I),
    re.compile(r"\bCommercial Banks\b"),
]

Q_PATTERNS = [
    re.compile(r"\u20b9\s*[\d,]+(?:\.\d+)?(?:\s*/-\s*)?(?:\s+for each day[^.]+)?"),
    re.compile(r"\bINR\s*[\d,]+(?:\.\d+)?"),
    re.compile(r"\bRs\.?\s*[\d,]+(?:\.\d+)?"),
    re.compile(r"\b\d{1,3}(?:,\d{2,3})+(?:\.\d+)?\b"),
    re.compile(r"\b\d+(?:\.\d+)?\s*%"),
    re.compile(r"\b(?:within\s+)?(?:a\s+)?(?:period of\s+)?\d+\s+(?:calendar\s+|working\s+)?(?:day|days|month|months|year|years|fortnight)s?\b", re.I),
    re.compile(r"\bno later than\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}", re.I),
    re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}"),
    re.compile(r"\bbeyond\s+\d+\s+days\b", re.I),
    re.compile(r"\b(?:lakh|crore)s?\b", re.I),
    re.compile(r"\bcompensat\w+[^.]*", re.I),
    re.compile(r"\bpenalt\w+[^.]*", re.I),
    re.compile(r"\binterest at the rate[^.]+"),
]


def classify_obligation(text: str) -> str:
    if any(p.search(text) for p in PROHIBITORY_PATTERNS):
        return "Prohibitory"
    if any(p.search(text) for p in MANDATORY_PATTERNS):
        return "Mandatory"
    if any(p.search(text) for p in DISCRETIONARY_PATTERNS):
        return "Discretionary"
    return "Informational"


def extract_entity(text: str) -> str:
    hits = []
    for p in ENTITY_PATTERNS:
        m = p.search(text)
        if m:
            hits.append(m.group(0))
    if not hits:
        return "N/A"
    if len(set(h.lower() for h in hits)) > 3:
        return "SOURCE_TEXT_AMBIGUOUS"
    return hits[0]


def extract_action(text: str) -> str:
    sentences = re.split(r"(?<=[\.\;])\s+", text.strip())
    for sent in sentences:
        if any(p.search(sent) for p in PROHIBITORY_PATTERNS + MANDATORY_PATTERNS + DISCRETIONARY_PATTERNS):
            return sent.strip()
    compact = " ".join(text.split())
    if not compact:
        return "N/A"
    return compact if len(compact) <= 400 else compact[:397] + "..."


def extract_quantitative(text: str) -> str:
    found: List[str] = []
    seen = set()
    for p in Q_PATTERNS:
        for m in p.finditer(text):
            span = m.group(0).strip()
            key = re.sub(r"\s+", " ", span)
            if key.lower() not in seen:
                seen.add(key.lower())
                found.append(span)
    return "; ".join(found) if found else "N/A"


def ocr_flags(text: str) -> List[str]:
    flags = []
    if REPLACEMENT in text or "\ufffd" in text:
        flags.append("OCR_VALIDATION_REQUIRED")
    if re.search(r"\d\?\d|\?\d|\d\?", text):
        flags.append("OCR_VALIDATION_REQUIRED")
    return list(dict.fromkeys(flags))


def excerpt(text: str, limit: int = 280) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


AMENDMENT_DATE = re.compile(
    r"with effect from\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)


def extract_amendment_date(text: str) -> Optional[str]:
    m = AMENDMENT_DATE.search(text or "")
    return m.group(1) if m else None
