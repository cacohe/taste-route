import asyncio

import pytest

from app.agents.planning_policy import LangChainPlanningPolicy, PlanningPolicyError
from app.models.planning import PlanningAction, PlanningObservation


class FakeStructuredModel:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        if self.error:
            raise self.error
        return self.result


class FakeModel:
    def __init__(self, structured: FakeStructuredModel) -> None:
        self.structured = structured
        self.schema = None
        self.options = None

    def with_structured_output(self, schema, **kwargs):
        self.schema = schema
        self.options = kwargs
        return self.structured


def observation() -> PlanningObservation:
    return PlanningObservation(
        iteration=3,
        stage="discovery",
        remaining_decisions=5,
        has_locality=True,
        discovery_attempts=1,
        candidate_count=2,
        rejected_count=1,
        day_count=0,
        stop_count=0,
        routing_available=True,
        route_count=0,
        warnings_count=0,
    )


@pytest.mark.anyio
async def test_policy_returns_a_structured_allowed_decision():
    structured = FakeStructuredModel({"action": "discover_nearby", "reason": "Need more local options."})
    model = FakeModel(structured)
    policy = LangChainPlanningPolicy(model)

    decision = await policy.choose(
        observation(),
        (PlanningAction.DISCOVER_NEARBY, PlanningAction.FAIL),
    )

    assert decision.action is PlanningAction.DISCOVER_NEARBY
    assert decision.reason == "Need more local options."
    prompt = "\n".join(message.content for message in structured.messages)
    assert "discover_nearby" in prompt
    assert "Need more local options" not in prompt
    assert model.options == {"method": "json_mode"}


@pytest.mark.anyio
async def test_policy_rejects_an_action_outside_the_allowed_set():
    policy = LangChainPlanningPolicy(FakeModel(FakeStructuredModel({
        "action": "finish", "reason": "Done",
    })))

    with pytest.raises(PlanningPolicyError, match="invalid action"):
        await policy.choose(observation(), (PlanningAction.DISCOVER_NEARBY,))


@pytest.mark.anyio
async def test_policy_truncates_reason_to_the_public_safe_limit():
    policy = LangChainPlanningPolicy(FakeModel(FakeStructuredModel({
        "action": "fail", "reason": "x" * 500,
    })))

    decision = await policy.choose(observation(), (PlanningAction.FAIL,))

    assert len(decision.reason) == 240


@pytest.mark.anyio
async def test_policy_maps_timeout_without_exposing_provider_text():
    policy = LangChainPlanningPolicy(FakeModel(FakeStructuredModel(
        error=asyncio.TimeoutError("raw prompt and secret"),
    )))

    with pytest.raises(PlanningPolicyError) as captured:
        await policy.choose(observation(), (PlanningAction.FAIL,))

    assert "raw prompt" not in str(captured.value)
    assert "secret" not in str(captured.value)

