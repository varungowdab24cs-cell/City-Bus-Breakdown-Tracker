"""Deterministic finite automaton for city bus route identifiers."""

from collections.abc import Callable


DEAD_STATE = "dead"
INITIAL_STATE = "q0"
ACCEPTING_STATE = "q16"


def _literal(expected: str) -> Callable[[str], bool]:
    return lambda character: character == expected


def _digit(character: str) -> bool:
    return "0" <= character <= "9"


def _uppercase(character: str) -> bool:
    return "A" <= character <= "Z"


TRANSITIONS = {
    "q0": (_literal("B"), "q1"),
    "q1": (_literal("U"), "q2"),
    "q2": (_literal("S"), "q3"),
    "q3": (_digit, "q4"),
    "q4": (_digit, "q5"),
    "q5": (_digit, "q6"),
    "q6": (_digit, "q7"),
    "q7": (_literal("-"), "q8"),
    "q8": (_literal("R"), "q9"),
    "q9": (_literal("O"), "q10"),
    "q10": (_literal("U"), "q11"),
    "q11": (_literal("T"), "q12"),
    "q12": (_literal("E"), "q13"),
    "q13": (_uppercase, "q14"),
    "q14": (_digit, "q15"),
    "q15": (_digit, ACCEPTING_STATE),
}


def transition_path(identifier: str) -> list[dict[str, str]]:
    """Return each consumed character and resulting state, including q0."""
    state = INITIAL_STATE
    path = [{"index": "-", "character": "", "state": state}]

    for index, character in enumerate(identifier):
        if state == DEAD_STATE:
            path.append(
                {"index": str(index), "character": character, "state": DEAD_STATE}
            )
            continue

        transition = TRANSITIONS.get(state)
        if transition is None or not transition[0](character):
            state = DEAD_STATE
        else:
            state = transition[1]
        path.append(
            {"index": str(index), "character": character, "state": state}
        )

    return path


def validate_bus_identifier(identifier: str) -> dict[str, object]:
    """Validate an identifier by processing it character by character."""
    if not isinstance(identifier, str):
        return {
            "accepted": False,
            "reason": "Bus identifier must be a string.",
            "final_state": DEAD_STATE,
            "path": [],
        }

    path = transition_path(identifier)
    final_state = path[-1]["state"]
    accepted = final_state == ACCEPTING_STATE and len(identifier) == 16
    reason = (
        "Identifier accepted by the DFA."
        if accepted
        else (
            f"Identifier rejected by the DFA at state {final_state}; "
            "expected BUS[4-digit]-ROUTE[uppercase alphabet][2-digit]."
        )
    )
    return {
        "accepted": accepted,
        "reason": reason,
        "final_state": final_state,
        "path": path,
    }
