# Phase 7 Test Cases

The Phase 7 suite uses isolated temporary SQLite database files. It does not
read from or write to the production `backend/city_bus.db`.

| Test ID | Description | Expected result | Actual result |
|---|---|---|---|
| P7-01 | DFA accepts a valid bus identifier | Accepted at `q16` | Verified by pytest |
| P7-02 | Regex accepts a valid bus identifier | Full match succeeds | Verified by pytest |
| P7-03 | DFA and regex equivalence | Both validators agree | Verified by pytest |
| P7-04 | All five issue-code categories | Each code maps to its documented category | Verified by pytest |
| P7-05 | Conflicting description keywords | Accident priority wins | Verified by pytest |
| P7-06 | Unknown classification code | Rejected with no category | Verified by pytest |
| P7-07 | Unknown route key | Central correction queue decision | Verified by pytest |
| P7-08 | Nearest depot selection | D01 selected for route A | Verified by pytest |
| P7-09 | Depot capacity overflow | Next eligible depot selected | Verified by pytest |
| P7-10 | Handler unavailable | Next eligible depot/handler selected | Verified by pytest |
| P7-11 | Handler capacity overflow | Handler at capacity is skipped | Verified by pytest |
| P7-12 | All depots unavailable | Waiting queue escalation | Verified by pytest |
| P7-13 | Emergency priority override | Report is Critical | Verified by pytest |
| P7-14 | Deterministic queue ordering | Critical before Normal | Verified by pytest |
| P7-15 | Duplicate assignment | Duplicate active assignment rejected | Verified by pytest |
| P7-16 | Invalid report submission | Stored as rejected and never dispatched | Verified by pytest |
| P7-17 | Status transitions | Valid flow succeeds; invalid transition is rejected | Verified by pytest |
| P7-18 | Database persistence | Report remains available after database reuse/restart | Verified by pytest |
| P7-19 | Resolution capacity release | Handler workload decrements to zero | Verified by pytest |
| P7-20 | Complete end-to-end workflow | Submission through analytics succeeds | Verified by pytest |
| P7-21 | Concurrent duplicate assignment | One request succeeds and one conflicts | Verified by pytest |

## Execution

Run the complete suite from `backend`:

```powershell
python -m pytest
```

The authoritative Pass/Fail result is the pytest output from that command.
