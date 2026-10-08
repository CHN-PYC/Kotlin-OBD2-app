# Remote API Verification

## Purpose, Input and Output

Validate the real provider through POST /qa/vehicle using the synthetic request
fixture, without logging credentials. The output is a validated vehicle answer
or a deterministic fallback, not just a successful HTTP status.

## Configuration

- Runtime reads .env relative to the working directory; .env.example is a template.
- Keep secrets only in the ignored server-v2/.env, never in the template.
- Start commands with `uv run --directory ./server-v2 ...` from the repository root.
- Local provider: openai_compatible; configured model: deepseek-v4-flash.
- Local JSON mode: true; local output budget: 2048 tokens.
- The template keeps a conservative 512-token default, not a universal optimum.
- Restart the application after configuration changes because settings are cached.

## Data Flow and Choice

Settings -> application.state.chat_options -> VehicleQAPromptBuilder ->
ChatRequest.options -> provider max_tokens -> output parser -> workflow response.

Explicit prompt types reduce ambiguity; JSON mode requests valid JSON but does
not guarantee the application schema. Pydantic remains the final validator.
Increasing the output budget makes truncation less likely, but can increase cost
and latency. It is a ceiling, not a promise that every request uses that many tokens.

## Failures and Debugging

1. Configuration was in .env.example and provider was still ollama. Move local
   values to .env, select openai_compatible, and restore a secret-free template.
2. A 512-token call ended with finish_reason=length and incomplete JSON. Inspect
   finish reason before treating an HTTP 200 as a successful model answer.
3. A 2048-token call finished normally but findings contained objects rather than
   strings. Inspect Pydantic error locations and types without logging raw input.
4. Specify arrays of strings in the prompt; do not loosen validation to hide a bug.

Pseudocode: load settings -> build prompt -> call model -> check finish reason ->
parse JSON -> validate schema -> build answer; on failure -> existing fallback.

## Verification and Evaluation

One real synthetic-fixture request on 2026-09-08 completed in approximately
8.01 seconds: HTTP 200, answer_mode=llm_only, model_output_parse=completed.
This is connectivity and contract verification, not a quality or latency benchmark.
It does not demonstrate retrieval, RAG accuracy, or production reliability.

Unit tests cover default/custom/invalid budgets and prompt type constraints.
API contract tests disable dotenv and model configuration to avoid paid requests.
Existing mocked provider and workflow tests cover provider failures and fallback.
Next evaluate schema success rate, truncation rate, latency and answer correctness
over multiple fixtures before selecting a production budget.

## Possible Replacement

A provider supporting strict JSON Schema output can enforce more constraints
upstream. Local schema validation and fallback are still necessary.
