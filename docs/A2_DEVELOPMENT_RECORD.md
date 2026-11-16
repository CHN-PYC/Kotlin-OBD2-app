# A2 development record: claim-level evidence for OBD explanations

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
| 2026-11-15 | `07f5bdc` | Android claim cards on the report screen |
| 2026-11-15 | `0135920` | Smoke script, recorded run and this record |
| 2026-11-15 | `2568425` | Android compile fixes and unit-test setup |
| 2026-11-15 | `f986d95` | Debug-only cleartext config so the emulator can reach the local server |
| 2026-11-15 | (no code change) | Full stack run on an Android emulator: P0101 and P0420 answers captured as screenshots and raw responses for the report |
| 2026-11-16 | `559e265` | Query rewriting no longer feeds its own output back into later turns, which had nested follow-up queries until the current question was cut off |
| 2026-11-16 | `f1341f8` | README section pointing to the A2 work; this record completed |
| 2026-11-16 | (report only) | Report reviewed against the brief and the code, then revised (see "Authorship and AI use") |

## Evidence of behaviour

- Automated tests: `cd server-v2 && uv run pytest` (claim-citation unit tests in
`tests/test_claim_citations.py`); Android JVM tests in
`app/src/test/.../VehicleQaClaimParserTest.kt`.
- Smoke record `server-v2/docs/evaluation/claim_citation_smoke_20261115.json`
(deepseek-v4-flash, BM25 top-5 over the English HELLA air-mass-sensor guide, 4 questions):
  - 3 of 4 questions answered; 1 returned an invalid model response.
  - Raw model proposal: 26 citations (chunk-ID references, not 26 distinct passages), 0 outside
  the evidence; 26 quotes, 0 not found.
  - Filtered response: 28 claims — 26 quoted, 1 vehicle data, 1 unsupported.
  - Limits seen in the record: three P0101 "cause" claims quote only the lead-in line
  "Causes for failure of the air-mass sensor can be:", so the highlighted text does not itself
  state the cause; the P0420 (catalytic converter) answer is built from air-mass-sensor checks
  that are all correctly quoted but do not address the question.
- Emulator run (full hybrid retrieval over the 28-chunk knowledge base: Chinese passages adapted
from HELLA, Bosch and EPA material, with English claims): P0101 gave 5 claims (4 quoted,
1 unsupported) and P0420 gave 7 (5 quoted, 1 vehicle data, 1 unsupported). In the P0420 answer, one
"Quote found" claim ("inspect oxygen-sensor circuits…") is linked to a sentence that only lists
fault causes, so the quote was located but does not support the claim. An earlier request
was cut off at 4,096 output tokens and returned the rule-based fallback; the captured answers
used a limit of 8,192.
- Fallback scope: the rule-based answer is used when retrieval fails, the evidence gate rejects
the passages, the prompt exceeds its budget, or the model returns an error, invalid JSON or
truncated output. Query rewriting and the citation check do not fall back.
- Not tested: no user study has been run, so nothing here shows that drivers rely on claims more
appropriately. Citation checks do not test whether a passage supports its claim or answers the
question.

## Authorship and AI use

- **Android app**: designed by me; implementation built with assistance from OpenAI Codex.
- **server-v2**: written by me by hand; Codex reviewed the code and gave feedback.
- **A2 changes (2026-11-15)**: I chose the design (claim-level evidence, from my A1 review) and
directed the changes; Claude Code (Anthropic) drafted the schema, citation checks, Android claim
cards, tests and smoke script, which I reviewed. Commits it helped write carry a
`Co-Authored-By: Claude` trailer.
- **Query-rewrite fix (`559e265`)**: written and committed by me.
- **Report (2026-11-15 – 16)**: Claude Code drafted the abstract and rationale from my A1 review
and my direction, drew the system diagram, and ran the emulator to capture the storyboard
screenshots. The driver thoughts in the storyboards are illustrative, not observations from
participants. I then had the assembled report reviewed by Codex against the brief and the code,
checked its points, and directed the corrections, for example:
  - the abstract and rationale together passed the 1,300-word cut-off, so the rationale was cut
  from 1,015 to 931 words;
  - the rationale said every workflow step could fall back to the rule-based answer, but the code
  shows five can (see "Fallback scope" above);
  - explanations had been placed inside the storyboards, which the brief does not allow, so they
  were reduced to short labels and the driver thoughts were marked as illustrative.
- No API keys or personal data are committed; the model key lives in the git-ignored
`server-v2/.env`.
