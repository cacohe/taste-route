"""POI相关API路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from ...services.amap_service import get_amap_service
from ...services.unsplash_service import get_unsplash_service

router = APIRouter(prefix="/poi", tags=["POI"])


class POIDetailResponse(BaseModel):
    """POI详情响应模型"""

    success: bool
    message: str
    data: Optional[dict] = None


@router.get(
    "/detail/{poi_id}",
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片",
)
async def get_poi_detail(poi_id: str):
    """获取POI详情

    根据高德地图的POI ID获取该兴趣点的详细信息。

    Args:
        poi_id: POI ID（高德地图提供的唯一标识符）

    Returns:
        POIDetailResponse: 包含成功状态、消息和POI详情数据
    """
    try:
        # 直接使用异步方法获取POI详情
        amap_service = get_amap_service()
        result = await amap_service.get_poi_detail(poi_id)
        return POIDetailResponse(success=True, message="获取POI详情成功", data=result)

    except Exception as e:
        print(f"❌ 获取POI详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取POI详情失败: {str(e)}")


@router.get("/search", summary="搜索POI", description="根据关键词搜索POI")
async def search_poi(keywords: str, city: str = "北京"):
    """搜索POI

    根据关键词和城市搜索兴趣点（景点、酒店、餐厅等）。

    Args:
        keywords: 搜索关键词，如"景点"、"酒店"、"餐厅"
        city: 城市名称，默认为"北京"

    Returns:
        包含成功状态、消息和POI列表的字典
    """
    try:
        # 直接使用异步方法搜索POI
        amap_service = get_amap_service()
        result = await amap_service.search_poi(keywords, city)
        return {
            "success": True,
            "message": "搜索成功",
            "data": [p.model_dump() for p in result],
        }

    except Exception as e:
        print(f"❌ 搜索POI失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索POI失败: {str(e)}")


@router.get(
    "/photo", summary="获取景点图片", description="根据景点名称从Unsplash获取图片"
)
async def get_attraction_photo(name: str):
    """获取景点图片

    通过Unsplash API根据景点名称获取相关的图片URL。

    Args:
        name: 景点名称

    Returns:
        包含成功状态、消息和图片URL的字典
    """
    try:
        unsplash_service = get_unsplash_service()

        # 优先搜索"名称+China landmark"组合，失败则用纯名称搜索
        photo_url = unsplash_service.get_photo_url(f"{name} China landmark")

        if not photo_url:
            photo_url = unsplash_service.get_photo_url(name)

        return {
            "success": True,
            "message": "获取图片成功",
            "data": {"name": name, "photo_url": photo_url},
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取景点图片失败: {str(e)}")
