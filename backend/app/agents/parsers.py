"""Agent 响应解析与行程数据修复"""

import json
from typing import Any, Dict, Optional

from ..models.schemas import TripPlan, TripRequest

DEFAULT_LONGITUDE = 116.397128
DEFAULT_LATITUDE = 39.916527


def extract_json_from_text(response: str) -> Optional[Dict[str, Any]]:
    """从 Agent 响应文本中提取 JSON 对象"""
    if not response:
        return None

    try:
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            json_str = response[json_start:json_end].strip()
        elif "```" in response:
            json_start = response.find("```") + 3
            json_end = response.find("```", json_start)
            json_str = response[json_start:json_end].strip()
        elif "{" in response and "}" in response:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]
        else:
            return None

        data = json.loads(json_str)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def format_json_for_prompt(response: str) -> str:
    """将 Agent 响应格式化为可嵌入提示词的 JSON 字符串"""
    data = extract_json_from_text(response)
    if data is None:
        return response
    return json.dumps(data, ensure_ascii=False, indent=2)


def _normalize_location(location: Any) -> Dict[str, float]:
    """修复不完整的 location 对象"""
    if not isinstance(location, dict):
        location = {}

    longitude = location.get("longitude", 0)
    latitude = location.get("latitude", 0)

    try:
        longitude = float(longitude)
        latitude = float(latitude)
    except (TypeError, ValueError):
        longitude = 0.0
        latitude = 0.0

    if longitude == 0:
        longitude = DEFAULT_LONGITUDE
    if latitude == 0:
        latitude = DEFAULT_LATITUDE

    return {"longitude": longitude, "latitude": latitude}


def fix_and_validate_plan(data: dict, request: TripRequest) -> TripPlan:
    """修复模型返回的不完整数据并验证为 TripPlan"""
    data.setdefault("city", request.city)
    data.setdefault("start_date", request.start_date)
    data.setdefault("end_date", request.end_date)
    data.setdefault("weather_info", [])
    data.setdefault("overall_suggestions", "")

    for index, day in enumerate(data.get("days", [])):
        day.setdefault("day_index", index)
        day.setdefault("transportation", request.transportation)
        day.setdefault("accommodation", request.accommodation)
        day.setdefault("meals", [])
        day.setdefault("attractions", [])

        for attraction in day.get("attractions", []):
            attraction["location"] = _normalize_location(attraction.get("location"))
            attraction.setdefault("visit_duration", 120)
            attraction.setdefault("description", attraction.get("name", "景点"))
            attraction.setdefault("category", "景点")
            attraction.setdefault("ticket_price", 0)
            if attraction.get("poi_id") in (None, "null"):
                attraction["poi_id"] = ""

        hotel = day.get("hotel")
        if isinstance(hotel, dict) and hotel.get("location"):
            hotel["location"] = _normalize_location(hotel.get("location"))

    return TripPlan(**data)


def parse_trip_plan_response(response: str, request: TripRequest) -> TripPlan:
    """解析 Planner Agent 响应为 TripPlan 对象"""
    data = extract_json_from_text(response)
    if data is None:
        raise ValueError("响应中未找到JSON数据")
    return fix_and_validate_plan(data, request)
