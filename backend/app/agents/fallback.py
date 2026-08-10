"""备用旅行计划生成"""

from datetime import datetime, timedelta

from ..models.schemas import (
    TripRequest,
    TripPlan,
    DayPlan,
    Attraction,
    Meal,
    Location,
)


def create_fallback_plan(request: TripRequest) -> TripPlan:
    """当 Agent 执行失败时，生成基础可行的备用计划"""
    start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

    days = []
    for i in range(request.travel_days):
        current_date = start_date + timedelta(days=i)

        day_plan = DayPlan(
            date=current_date.strftime("%Y-%m-%d"),
            day_index=i,
            description=f"第{i + 1}天行程",
            transportation=request.transportation,
            accommodation=request.accommodation,
            attractions=[
                Attraction(
                    name=f"{request.city}景点{j + 1}",
                    address=f"{request.city}市",
                    location=Location(
                        longitude=116.4 + i * 0.01 + j * 0.005,
                        latitude=39.9 + i * 0.01 + j * 0.005,
                    ),
                    visit_duration=120,
                    description=f"这是{request.city}的著名景点",
                    category="景点",
                )
                for j in range(2)
            ],
            meals=[
                Meal(
                    type="breakfast",
                    name=f"第{i + 1}天早餐",
                    description="当地特色早餐",
                ),
                Meal(type="lunch", name=f"第{i + 1}天午餐", description="午餐推荐"),
                Meal(type="dinner", name=f"第{i + 1}天晚餐", description="晚餐推荐"),
            ],
        )
        days.append(day_plan)

    return TripPlan(
        city=request.city,
        start_date=request.start_date,
        end_date=request.end_date,
        days=days,
        weather_info=[],
        overall_suggestions=(
            f"这是为您规划的{request.city}{request.travel_days}日游行程,"
            f"建议提前查看各景点的开放时间。"
        ),
    )
