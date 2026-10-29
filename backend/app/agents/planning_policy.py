"""Structured, bounded LLM policy for selecting controller-approved actions."""

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ..models.planning import PlanningAction, PlanningDecision, PlanningObservation


class PlanningPolicyError(RuntimeError):
    """A safe policy failure that never includes provider or prompt content."""


class _PolicySelection(BaseModel):
    action: PlanningAction
    reason: str


class LangChainPlanningPolicy:
    def __init__(self, model: BaseChatModel) -> None:
        self._model = model.with_structured_output(
            _PolicySelection, method="json_mode"
        )

    async def choose(
        self,
        observation: PlanningObservation,
        allowed_actions: tuple[PlanningAction, ...],
    ) -> PlanningDecision:
        if not allowed_actions:
            raise PlanningPolicyError("Planning policy received no allowed actions.")
        payload = {
            "observation": observation.model_dump(mode="json"),
            "allowed_actions": [action.value for action in allowed_actions],
        }
        messages = [
            SystemMessage(content=(
                "Select exactly one action from allowed_actions. Use only the supplied "
                "sanitized observation metrics. Return a short user-safe reason and a "
                "JSON object matching the required schema."
            )),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        try:
            result = await self._model.ainvoke(messages)
            if isinstance(result, dict):
                result = _PolicySelection.model_validate(result)
            if not isinstance(result, _PolicySelection):
                raise ValueError("unexpected structured result")
            if result.action not in allowed_actions:
                raise PlanningPolicyError("Planning policy selected an invalid action.")
            reason = " ".join(result.reason.split()).strip()[:240]
            if not reason:
                reason = "Selected from the available planning actions."
            return PlanningDecision(action=result.action, reason=reason)
        except PlanningPolicyError:
            raise
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise PlanningPolicyError("Planning policy returned an invalid action.") from exc
            raise PlanningPolicyError("Planning policy is temporarily unavailable.") from exc

