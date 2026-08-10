from app.agents.parsers import (
    extract_json_from_text,
    fix_and_validate_plan,
    format_json_for_prompt,
    parse_trip_plan_response,
)
from app.models.schemas import TripRequest


def _sample_request() -> TripRequest:
    return TripRequest(
        city="北京",
        start_date="2025-06-01",
        end_date="2025-06-02",
        travel_days=2,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=["历史文化"],
        free_text_input="",
    )


def test_extract_json_from_text_supports_markdown_fence():
    response = """说明文字
```json
{"city": "北京", "days": []}
```
"""

    data = extract_json_from_text(response)

    assert data == {"city": "北京", "days": []}


def test_format_json_for_prompt_returns_pretty_json():
    response = '{"city":"北京","days":[]}'

    formatted = format_json_for_prompt(response)

    assert '"city": "北京"' in formatted


def test_fix_and_validate_plan_fills_missing_defaults():
    request = _sample_request()

    plan = fix_and_validate_plan(
        {
            "days": [
                {
                    "date": "2025-06-01",
                    "description": "第一天",
                    "attractions": [
                        {
                            "name": "故宫",
                            "address": "东城区",
                            "location": {"longitude": 0, "latitude": 0},
                        }
                    ],
                }
            ]
        },
        request,
    )

    assert plan.city == "北京"
    assert plan.days[0].day_index == 0
    assert plan.days[0].attractions[0].visit_duration == 120
    assert plan.days[0].attractions[0].location.longitude != 0


def test_parse_trip_plan_response_raises_when_json_missing():
    request = _sample_request()

    try:
        parse_trip_plan_response("没有结构化数据", request)
        raised = False
    except ValueError as exc:
        raised = True
        assert "JSON" in str(exc)

    assert raised
