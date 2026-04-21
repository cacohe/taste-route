"""高德地图MCP服务 - 使用langchain-mcp-adapters连接高德地图MCP服务器"""

import asyncio
from typing import List, Dict, Any, Optional
from langchain_mcp_adapters.tools import load_mcp_tools  # 加载MCP工具的核心函数
from langchain_mcp_adapters.sessions import (
    StdioConnection,
)  # 用于创建STDIO连接的连接对象
from langchain_core.tools import BaseTool  # LangChain工具基类
from ..config import get_settings  # 获取应用配置
from ..models.schemas import Location, POIInfo, WeatherInfo

# MCP工具单例，全局缓存已加载的工具列表
_mcp_tools: Optional[List[BaseTool]] = None


async def get_mcp_tools() -> List[BaseTool]:
    """获取高德地图MCP工具（单例模式，延迟初始化）

    首次调用时创建StdioConnection连接到amap-mcp-server，
    后续调用直接返回缓存的工具列表。

    Returns:
        BaseTool列表，包含所有可用的MCP工具

    Raises:
        ValueError: 当AMAP_API_KEY未配置时抛出
    """
    global _mcp_tools

    if _mcp_tools is None:
        settings = get_settings()

        # 检查API Key配置
        if not settings.amap_api_key:
            raise ValueError("高德地图API Key未配置，请在.env文件中设置AMAP_API_KEY")

        # 创建STDIO连接，用于与amap-mcp-server子进程通信
        connection = StdioConnection(
            command="uvx",
            args=["amap-mcp-server"],
            env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
            cwd=None,
            transport="stdio",
        )

        # 通过连接加载MCP工具
        _mcp_tools = await load_mcp_tools(session=None, connection=connection)

        print(f"✅ 高德地图MCP工具初始化成功")
        print(f"   工具数量: {len(_mcp_tools)}")
        # 打印前5个工具名称用于调试
        for tool in _mcp_tools[:5]:
            print(f"     - {tool.name}")
        if len(_mcp_tools) > 5:
            print(f"     ... 还有 {len(_mcp_tools) - 5} 个工具")

    return _mcp_tools


class AmapService:
    """高德地图服务封装类，封装MCP工具的异步调用"""

    def __init__(self):
        self._tools: Optional[List[BaseTool]] = None

    async def get_tools(self) -> List[BaseTool]:
        """获取工具列表（延迟初始化）"""
        if self._tools is None:
            self._tools = await get_mcp_tools()
        return self._tools

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """根据工具名称查找工具

        Args:
            name: 工具名称，如 'maps_text_search'

        Returns:
            找到的工具对象，未找到返回None
        """
        if self._tools is None:
            return None
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    async def search_poi(
        self, keywords: str, city: str, citylimit: bool = True
    ) -> List[POIInfo]:
        """搜索POI（兴趣点）

        使用 maps_text_search 工具搜索指定城市的关键词POI。

        Args:
            keywords: 搜索关键词
            city: 城市名称
            citylimit: 是否限制在城市范围内搜索

        Returns:
            POIInfo列表，包含搜索到的兴趣点信息
        """
        try:
            search_tool = self.get_tool_by_name("maps_text_search")
            if not search_tool:
                print("⚠️  maps_text_search tool not found")
                return []

            # 调用MCP工具并传入参数
            result = await search_tool.ainvoke(
                {
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower(),
                }
            )

            print(f"POI搜索结果: {str(result)[:200]}...")
            return self._parse_poi_result(result)

        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []

    def _parse_poi_result(self, result: Any) -> List[POIInfo]:
        """解析POI搜索结果

        从MCP工具返回的原始字符串中提取JSON数组并转换为POIInfo列表。

        Args:
            result: MCP工具返回的原始结果（可能是字符串或字典）

        Returns:
            解析后的POIInfo列表
        """
        pois = []
        try:
            if isinstance(result, str):
                import json
                import re

                # 使用正则提取JSON数组部分
                json_match = re.search(r"\[.*\]", result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    for item in data:
                        pois.append(
                            POIInfo(
                                id=item.get("id", ""),
                                name=item.get("name", ""),
                                type=item.get("type", ""),
                                address=item.get("address", ""),
                                location=Location(
                                    longitude=item.get("location", {}).get(
                                        "longitude", 0
                                    ),
                                    latitude=item.get("location", {}).get(
                                        "latitude", 0
                                    ),
                                ),
                            )
                        )
        except Exception as e:
            print(f"⚠️  解析POI结果失败: {str(e)}")
        return pois

    async def get_weather(self, city: str) -> List[WeatherInfo]:
        """查询城市天气

        使用 maps_weather 工具查询指定城市的天气信息。

        Args:
            city: 城市名称

        Returns:
            WeatherInfo列表，包含多天的天气信息
        """
        try:
            weather_tool = self.get_tool_by_name("maps_weather")
            if not weather_tool:
                print("⚠️  maps_weather tool not found")
                return []

            result = await weather_tool.ainvoke({"city": city})
            print(f"天气查询结果: {str(result)[:200]}...")
            return self._parse_weather_result(result)

        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []

    def _parse_weather_result(self, result: Any) -> List[WeatherInfo]:
        """解析天气查询结果

        Args:
            result: MCP工具返回的原始结果

        Returns:
            解析后的WeatherInfo列表
        """
        weather_list = []
        try:
            if isinstance(result, str):
                import json
                import re

                json_match = re.search(r"\[.*\]", result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    for item in data:
                        weather_list.append(
                            WeatherInfo(
                                date=item.get("date", ""),
                                day_weather=item.get("day_weather", ""),
                                night_weather=item.get("night_weather", ""),
                                day_temp=item.get("day_temp", 0),
                                night_temp=item.get("night_temp", 0),
                                wind_direction=item.get("wind_direction", ""),
                                wind_power=item.get("wind_power", ""),
                            )
                        )
        except Exception as e:
            print(f"⚠️  解析天气结果失败: {str(e)}")
        return weather_list

    async def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking",
    ) -> Dict[str, Any]:
        """规划两点之间的路线

        根据指定的交通方式（步行/驾车/公交）规划路线。

        Args:
            origin_address: 出发地地址
            destination_address: 目的地地址
            origin_city: 出发地所在城市
            destination_city: 目的地所在城市
            route_type: 路线类型，可选 'walking'|'driving'|'transit'

        Returns:
            路线规划结果，包含路线详情
        """
        # 交通方式对应的工具名称映射
        tool_map = {
            "walking": "maps_direction_walking_by_address",
            "driving": "maps_direction_driving_by_address",
            "transit": "maps_direction_transit_integrated_by_address",
        }

        tool_name = tool_map.get(route_type, "maps_direction_walking_by_address")

        try:
            route_tool = self.get_tool_by_name(tool_name)
            if not route_tool:
                print(f"⚠️  {tool_name} tool not found")
                return {}

            arguments = {
                "origin_address": origin_address,
                "destination_address": destination_address,
            }

            # 公交路线需要额外的城市参数
            if route_type == "transit":
                if origin_city:
                    arguments["origin_city"] = origin_city
                if destination_city:
                    arguments["destination_city"] = destination_city
            else:
                if origin_city:
                    arguments["origin_city"] = origin_city
                if destination_city:
                    arguments["destination_city"] = destination_city

            result = await route_tool.ainvoke(arguments)
            print(f"路线规划结果: {str(result)[:200]}...")
            return self._parse_route_result(result)

        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            return {}

    def _parse_route_result(self, result: Any) -> Dict[str, Any]:
        """解析路线规划结果

        Args:
            result: MCP工具返回的原始结果

        Returns:
            解析后的路线信息字典
        """
        try:
            if isinstance(result, str):
                import json
                import re

                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            print(f"⚠️  解析路线结果失败: {str(e)}")
        return {}


# 全局单例实例
_amap_service: Optional[AmapService] = None


def get_amap_service() -> AmapService:
    """获取AmapService单例实例

    Returns:
        AmapService实例
    """
    global _amap_service

    if _amap_service is None:
        _amap_service = AmapService()

    return _amap_service
