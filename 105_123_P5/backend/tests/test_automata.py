import pytest

from automata.classifier import classify_issue
from automata.dfa import ACCEPTING_STATE, DEAD_STATE, validate_bus_identifier
from automata.regex_validator import compare_validators, validate_with_regex


@pytest.mark.parametrize("identifier", ["BUS1234-ROUTEA12", "BUS0000-ROUTEZ99"])
def test_valid_identifiers_are_accepted_by_both_validators(identifier):
    comparison = compare_validators(identifier)

    assert comparison["dfa"]["accepted"] is True
    assert comparison["regex"]["accepted"] is True
    assert comparison["agree"] is True
    assert comparison["dfa"]["final_state"] == ACCEPTING_STATE
    assert comparison["dfa_transition_path"][0]["state"] == "q0"


@pytest.mark.parametrize(
    "identifier",
    [
        "BUS123-ROUTEA12",
        "BUS1234-ROUTE12",
        "BUS1234ROUTEA12",
        "BUS1234-ROUTEA1",
        "BUS1234-ROUTEA123",
    ],
)
def test_malformed_identifiers_are_rejected(identifier):
    comparison = compare_validators(identifier)

    assert comparison["dfa"]["accepted"] is False
    assert comparison["regex"]["accepted"] is False
    assert comparison["agree"] is True


def test_lowercase_identifier_is_rejected():
    assert validate_bus_identifier("bus1234-ROUTEA12")["accepted"] is False
    assert validate_with_regex("BUS1234-routeA12")["accepted"] is False
    assert validate_bus_identifier("BUS1234-ROUTEa12")["final_state"] == DEAD_STATE


def test_unsupported_explicit_code_is_rejected():
    result = classify_issue("BODY", "engine has stopped")

    assert result["valid"] is False
    assert result["category"] is None
    assert "Unsupported" in result["reason"]


def test_unmapped_description_is_rejected():
    result = classify_issue(description="The passenger display is dim.")

    assert result["valid"] is False
    assert result["category"] is None


def test_conflicting_description_patterns_use_priority():
    result = classify_issue(
        description="A collision damaged the battery, engine, tyre, and fuel system."
    )

    assert result["category"] == "Accident"


def test_explicit_code_takes_precedence_over_description():
    result = classify_issue("FUEL", "A collision caused an electrical failure.")

    assert result["valid"] is True
    assert result["category"] == "Fuel"
