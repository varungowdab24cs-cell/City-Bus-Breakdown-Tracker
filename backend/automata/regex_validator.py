"""Regex validation and DFA equivalence helpers."""

import re

from .dfa import transition_path, validate_bus_identifier


BUS_IDENTIFIER_PATTERN = r"^BUS[0-9]{4}-ROUTE[A-Z][0-9]{2}$"


def validate_with_regex(identifier: str) -> dict[str, object]:
    """Validate a bus identifier using the required full-match regex."""
    if not isinstance(identifier, str):
        return {
            "accepted": False,
            "reason": "Bus identifier must be a string.",
        }

    accepted = re.fullmatch(BUS_IDENTIFIER_PATTERN, identifier) is not None
    return {
        "accepted": accepted,
        "reason": (
            "Identifier accepted by the regex validator."
            if accepted
            else (
                "Identifier rejected: expected "
                "BUS[4-digit]-ROUTE[uppercase alphabet][2-digit]."
            )
        ),
    }


def compare_validators(identifier: str) -> dict[str, object]:
    """Run both validators and report whether their results agree."""
    dfa_result = validate_bus_identifier(identifier)
    regex_result = validate_with_regex(identifier)
    agree = dfa_result["accepted"] == regex_result["accepted"]
    return {
        "dfa": dfa_result,
        "regex": regex_result,
        "dfa_transition_path": transition_path(identifier)
        if isinstance(identifier, str)
        else [],
        "agree": agree,
        "validation_message": (
            "DFA and regex validators agree."
            if agree
            else "DFA and regex validators disagree."
        ),
    }
