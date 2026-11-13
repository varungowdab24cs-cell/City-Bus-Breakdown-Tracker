"""Deterministic breakdown priority rules."""

PRIORITY_RANK = {"Critical": 0, "High": 1, "Normal": 2}


def determine_priority(
    category: str,
    *,
    emergency: bool = False,
    severe_accident: bool = False,
    dangerous_electrical_fault: bool = False,
) -> dict[str, str]:
    """Return priority and the recorded reason for any override."""
    if emergency:
        return {"priority": "Critical", "reason": "Emergency flag overrides category priority."}
    if category == "Accident" and severe_accident:
        return {"priority": "Critical", "reason": "Severe accident overrides standard accident priority."}
    if category == "Accident":
        return {"priority": "High", "reason": "Accident reports receive High priority."}
    if category == "Electrical" and dangerous_electrical_fault:
        return {
            "priority": "High",
            "reason": "Dangerous electrical fault overrides the normal category priority.",
        }
    return {"priority": "Normal", "reason": "No critical or high-priority override applies."}
