# A2 development record: claim-level evidence for OBD explanations

> Draft for the IIS A2 submission. Check every statement below against your own memory of the
> work before submitting; edit anything that is not accurate.

## What A2 adds to the existing project

The OBD app and `server-v2` existed before A2. A2 changes how an answer is presented: instead of
one paragraph followed by a reference list, the answer is split into short claims, and the
passage each claim was linked to is shown directly under that claim (A1: supporting selective,
claim-by-claim reliance).

| Layer | Change | Where |
|---|---|---|
| Model output schema | `answer` + `claims[]`, each with `kind`, `source_chunk_ids`, optional `quote`, `uses_vehicle_data` | `server-v2/app/schemas/generation.py` |
| Server checks | Drop chunk IDs not sent to the model; accept a quote only if found in a cited passage (case/whitespace tolerant); label each claim `quoted` / `cited` / `vehicle_data` / `unsupported` | `server-v2/app/services/generation/claim_citations.py` |
| Trace | New `claim_citation_check` step records rejected IDs and unfound quotes | `server-v2/app/agent/nodes.py` |
| Compatibility | Legacy `findings` / `recommendations` are derived from claims | same |
| Android | Parses `claims` from the stored backend response; shows one card per claim with its citation status and the linked passage, quote highlighted, full passage on tap | `app/.../data/repository/VehicleQaClaims.kt`, `app/.../ui/history/DiagnosticReportActivity.kt` |
| Evaluation record | Smoke run against the configured hosted model, raw proposal and filtered result stored separately | `server-v2/scripts/smoke_claim_citations.py`, `server-v2/docs/evaluation/` |

Citation status describes whether a claim can be traced to supplied evidence. It does not say the
claim is true, and `vehicle_data` is declared by the model, not checked against recorded values.

## Timeline

| Date | Commit | Step |
|---|---|---|
| 2026-04 – 2026-06 | `d9edaca` … `0a57a1c` | Android OBD app, rule diagnosis, remote LLM integration, first RAG backend link |
| 2026-10-08 | `c5a39e9` | `server-v2` agent backend: explicit workflow nodes, hybrid retrieval, evidence gate |
| 2026-11-09 | `6d4993d` | Exception fallback and readiness health check |
| 2026-11-15 | `d30a25e` | Claim-level answers; chunk IDs validated against the evidence actually sent |
| 2026-11-15 | `9b5520a` | Quote verification; `vehicle_data` label |
| 2026-11-15 | after `9b5520a` | Android claim cards; smoke script, recorded run and this record |

## Evidence of behaviour

- Automated tests: `cd server-v2 && uv run pytest` (claim-citation unit tests in
  `tests/test_claim_citations.py`); Android JVM tests in
  `app/src/test/.../VehicleQaClaimParserTest.kt`.
- Smoke record `server-v2/docs/evaluation/claim_citation_smoke_20261115.json`
  (deepseek-v4-flash, BM25 top-5 over the HELLA air-mass-sensor guide, 4 questions):
  - 3 of 4 questions answered; 1 returned an invalid model response.
  - Raw model proposal: 26 cited IDs, 0 outside the evidence; 26 quotes, 0 not found.
  - Filtered response: 28 claims — 26 quoted, 1 vehicle data, 1 unsupported.
  - Limits seen in the record: three P0101 "cause" claims quote only the lead-in line
    "Causes for failure of the air-mass sensor can be:", so the highlighted text does not itself
    state the cause; the P0420 (catalytic converter) answer is built from air-mass-sensor checks
    that are all correctly quoted but do not address the question.

## Authorship and AI use

- **Android app**: designed by me; implementation built with assistance from OpenAI Codex.
- **server-v2**: written by me by hand; Codex reviewed the code and gave feedback.
- **A2 changes (2026-11-15)**: I chose the design (claim-level evidence, from my A1 review) and
  directed the changes; Claude Code (Anthropic) drafted the schema, citation checks, Android claim
  cards, tests and smoke script, which I reviewed. Commits it helped write carry a
  `Co-Authored-By: Claude` trailer.
- No API keys or personal data are committed; the model key lives in the git-ignored
  `server-v2/.env`.
