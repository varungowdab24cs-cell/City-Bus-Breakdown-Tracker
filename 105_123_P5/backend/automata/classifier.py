"""Deterministic breakdown issue classification."""

import re


ISSUE_CODE_MAPPING = {
    "MECH": "Mechanical",
    "TYRE": "Tyre",
    "ACC": "Accident",
    "FUEL": "Fuel",
    "ELEC": "Electrical",
}

# Patterns are evaluated in this order to make conflicting descriptions stable.
DESCRIPTION_PATTERNS = (
    ("Accident", re.compile(r"\b(accident|crash|collision|crashed)\b", re.I)),
    (
        "Electrical",
        re.compile(r"\b(electrical|battery|alternator|wiring|starter)\b", re.I),
    ),
    (
        "Mechanical",
        re.compile(r"\b(mechanical|engine|brake|gearbox|overheating)\b", re.I),
    ),
    ("Tyre", re.compile(r"\b(tyre|tire|puncture|flat)\b", re.I)),
    ("Fuel", re.compile(r"\b(fuel|diesel|petrol|empty tank)\b", re.I)),
)


def classify_issue(
    issue_code: str | None = None, description: str | None = None
) -> dict[str, object]:
    """Classify an issue from an explicit code or supported description patterns."""
    if issue_code is not None:
        normalized_code = issue_code.strip().upper() if isinstance(issue_code, str) else ""
        if normalized_code not in ISSUE_CODE_MAPPING:
            return {
                "category": None,
                "valid": False,
                "reason": f"Unsupported explicit issue code: {issue_code!r}.",
            }
        category = ISSUE_CODE_MAPPING[normalized_code]
        return {
            "category": category,
            "valid": True,
            "reason": f"Explicit issue code {normalized_code} mapped to {category}.",
        }

    if isinstance(description, str):
        for category, pattern in DESCRIPTION_PATTERNS:
            match = pattern.search(description)
            if match:
                return {
                    "category": category,
                    "valid": True,
                    "reason": f"Description keyword matched: {match.group(0)!r}.",
                }

    return {
        "category": None,
        "valid": False,
        "reason": "No supported issue code or description keyword was found.",
    }
