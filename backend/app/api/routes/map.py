"""地图服务API路由"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...models.schemas import (
    POISearchRequest,
    POISearchResponse,
    RouteRequest,
    RouteResponse,
    WeatherResponse,
)
from ...services.amap_service import get_amap_service

router = APIRouter(prefix="/map", tags=["地图服务"])


@router.get(
    "/poi",
    response_model=POISearchResponse,
    summary="搜索POI",
    description="根据关键词搜索POI(兴趣点)",
)
async def search_poi(
    keywords: str = Query(..., description="搜索关键词", examples=["故宫"]),
    city: str = Query(..., description="城市", examples=["北京"]),
    citylimit: bool = Query(True, description="是否限制在城市范围内"),
):
    """搜索POI（兴趣点）

    使用高德地图文本搜索服务，根据关键词搜索指定城市的兴趣点。

    Args:
        keywords: 搜索关键词
        city: 城市名称
        citylimit: 是否限制在城市范围内搜索

    Returns:
        POISearchResponse: 包含搜索结果的响应
    """
    try:
        # 直接使用异步方法，无需 asyncio.run()
        service = get_amap_service()
        pois = await service.search_poi(keywords, city, citylimit)
        return POISearchResponse(success=True, message="POI搜索成功", data=pois)

    except Exception as e:
        print(f"❌ POI搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"POI搜索失败: {str(e)}")


@router.get(
    "/weather",
    response_model=WeatherResponse,
    summary="查询天气",
    description="查询指定城市的天气信息",
)
async def get_weather(
    city: str = Query(..., description="城市名称", examples=["北京"]),
):
    """查询城市天气

    使用高德地图天气服务，获取指定城市的天气预报。

    Args:
        city: 城市名称

    Returns:
        WeatherResponse: 包含天气信息的响应
    """
    try:
        # 直接使用异步方法
        service = get_amap_service()
        weather_info = await service.get_weather(city)
        return WeatherResponse(success=True, message="天气查询成功", data=weather_info)

    except Exception as e:
        print(f"❌ 天气查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"天气查询失败: {str(e)}")


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="规划路线",
    description="规划两点之间的路线",
)
async def plan_route(request: RouteRequest):
    """规划两点之间的路线

    根据起终点地址和交通方式，使用高德地图路线规划服务计算路线。

    Args:
        request: RouteRequest，包含origin_address、destination_address、route_type等

    Returns:
        RouteResponse: 包含路线规划结果的响应
    """
    try:
        # 直接使用异步方法
        service = get_amap_service()
        route_info = await service.plan_route(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            origin_city=request.origin_city,
            destination_city=request.destination_city,
            route_type=request.route_type,
        )
        return RouteResponse(success=True, message="路线规划成功", data=route_info)

    except Exception as e:
        print(f"❌ 路线规划失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"路线规划失败: {str(e)}")


@router.get("/health", summary="健康检查", description="检查地图服务是否正常")
async def health_check():
    """地图服务健康检查

    检查高德地图MCP服务是否正常运行，通过获取工具列表来验证连接。

    Returns:
        包含健康状态和服务信息的字典
    """
    try:
        # 直接使用异步方法获取工具列表用于健康检查
        service = get_amap_service()
        tools = await service.get_tools()
        return {
            "status": "healthy",
            "service": "map-service",
            "mcp_tools_count": len(tools),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务不可用: {str(e)}")
