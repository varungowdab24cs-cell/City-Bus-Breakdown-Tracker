# Phase 7 Automated Test Report

Executed with:

```powershell
cd backend
python -m pytest
```

The results below are based on the executed Phase 7 test run. All tests use
temporary SQLite database files and do not modify demonstration data.

| Test ID | Description | Expected result | Actual result | Pass/Fail |
|---|---|---|---|---|
| P7-01 | DFA accepts valid identifier | Accepting state `q16` | Accepted at `q16` | PASS |
| P7-02 | Regex accepts valid identifier | Full match succeeds | Full match succeeded | PASS |
| P7-03 | DFA/regex equivalence | Both results agree | Results agreed | PASS |
| P7-04 | Five classification categories | All five codes map correctly | All five mappings passed | PASS |
| P7-05 | Classification conflict priority | Accident wins | Accident selected | PASS |
| P7-06 | Unknown classification code | Rejected without category | Rejected | PASS |
| P7-07 | Unknown routing key | Correction queue | Correction queue decision saved | PASS |
| P7-08 | Nearest depot | D01 for route A | D01 selected | PASS |
| P7-09 | Depot overflow | Next depot selected | D05 selected | PASS |
| P7-10 | Handler unavailable | Next eligible handler/depot | H09 at D05 selected | PASS |
| P7-11 | Handler capacity overflow | Full handler skipped | H09 selected | PASS |
| P7-12 | All depots unavailable | Waiting queue escalation | Waiting entry saved | PASS |
| P7-13 | Critical override | Emergency is Critical | Critical returned | PASS |
| P7-14 | Queue ordering | Critical precedes Normal | Correct order returned | PASS |
| P7-15 | Duplicate assignment | Duplicate rejected | `ValueError`/conflict returned | PASS |
| P7-16 | Invalid report | Stored rejected, no dispatch | `422`, no routing decision | PASS |
| P7-17 | Status transitions | Valid flow succeeds; invalid flow fails | Flow passed; invalid transition `409` | PASS |
| P7-18 | Database persistence | Data survives app restart | Report found after recreation | PASS |
| P7-19 | Resolution capacity release | Workload decrements | Handler workload returned to zero | PASS |
| P7-20 | End-to-end workflow | Submission through analytics works | All assertions passed | PASS |
| P7-21 | Concurrent duplicate assignment | One winner, one conflict | `200` and `409` returned | PASS |

## Result

The authoritative final run is the full `pytest` invocation. The report must
only be considered current when its result matches that command's output.

Final executed result: **54 passed, 0 failed**.
