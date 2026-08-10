from app.agents.fallback import create_fallback_plan
from app.models.schemas import TripRequest


def test_create_fallback_plan_uses_request_metadata():
    request = TripRequest(
        city="上海",
        start_date="2025-07-01",
        end_date="2025-07-03",
        travel_days=3,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=[],
        free_text_input="",
    )

    plan = create_fallback_plan(request)

    assert plan.city == "上海"
    assert len(plan.days) == 3
    assert plan.days[0].transportation == "公共交通"
    assert len(plan.days[0].attractions) == 2
    assert plan.days[0].meals[0].type == "breakfast"
