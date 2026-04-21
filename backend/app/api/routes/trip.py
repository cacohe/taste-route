"""旅行规划API路由 - 处理 /api/trip/* 路径的请求"""

from fastapi import APIRouter, HTTPException
from ...models.schemas import TripRequest, TripPlanResponse, ErrorResponse
from ...agents.trip_planner_agent import get_trip_planner_agent

router = APIRouter(prefix="/trip", tags=["旅行规划"])


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求,生成详细的旅行计划",
)
async def plan_trip(request: TripRequest):
    """生成旅行计划

    接收用户旅行需求，调用多智能体系统生成完整旅行计划。

    Args:
        request: TripRequest，包含城市、日期、偏好等旅行需求

    Returns:
        TripPlanResponse: 包含成功状态、消息和完整旅行计划
    """
    try:
        print(f"\n{'=' * 60}")
        print(f"📥 收到旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"{'=' * 60}\n")

        # 获取多智能体旅行规划器
        agent = get_trip_planner_agent()

        print("🚀 开始生成旅行计划...")

        # 调用Agent生成旅行计划（异步）
        trip_plan = await agent.plan_trip(request)

        print("✅ 旅行计划生成成功,准备返回响应\n")

        return TripPlanResponse(
            success=True, message="旅行计划生成成功", data=trip_plan
        )

    except Exception as e:
        print(f"❌ 生成旅行计划失败: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成旅行计划失败: {str(e)}")


@router.get("/health", summary="健康检查", description="检查旅行规划服务是否正常")
async def health_check():
    """旅行规划服务健康检查

    验证Agent系统是否可正常响应。

    Returns:
        包含健康状态和服务信息的字典
    """
    try:
        agent = get_trip_planner_agent()

        return {
            "status": "healthy",
            "service": "trip-planner",
            "agent_type": "MultiAgentTripPlanner",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务不可用: {str(e)}")
