# FastAPI Model Wiring Learning Card

## Purpose

Connect the application-scoped chat model to the vehicle QA endpoint while
keeping the route independent of concrete service implementations.

## Input

The current FastAPI `Request`, whose `app.state.chat_model` is initialized by
the application lifespan.

## Output

A `VehicleQAService`: `LLMVehicleQAService` when a model is available, otherwise
`RuleFallbackQAService`.

## Algorithm

1. FastAPI resolves `get_vehicle_qa_service` before invoking the route.
2. The dependency reads the shared chat model from `request.app.state`.
3. A missing model selects the deterministic fallback service.
4. An available model is injected into an LLM service with its prompt builder
   and fallback dependency.
5. The route calls only the common `answer` protocol.

## Reason For Selection

The HTTP client and chat model are expensive application resources and are
shared from lifespan state. The QA service and prompt builder are lightweight
and stateless, so constructing them per request is simple and safe. Dependency
injection also allows tests to replace infrastructure without changing route
logic.

## Failure Cases

- Model not configured at startup: select rule fallback without an outbound call.
- Provider fails during generation: the LLM service handles runtime fallback.
- Lifespan is skipped in a test: required `app.state` resources do not exist.
- Business request and FastAPI `Request` are confused despite serving different
  purposes.

## Debugging

Check `app.state.model_provider_status`, then the concrete service returned by
the dependency, followed by `answer_mode` and `agent_trace`. Use `TestClient` as
a context manager so startup and shutdown hooks execute.

## Evaluation

Integration-test both configured and unconfigured startup paths. Assert whether
an outbound provider request occurred and verify the resulting `answer_mode`.

## Possible Replacement

Services may later be constructed once in lifespan or by a dependency container.
The route should continue depending on the `VehicleQAService` protocol.
