"""多智能体旅行规划系统 - 使用 LangChain 实现 ReAct 代理协作"""

import asyncio
import time
from typing import List, Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from ..models.schemas import TripRequest, TripPlan
from ..services.amap_service import get_amap_service
from ..services.llm_service import get_llm
from .fallback import create_fallback_plan
from .parsers import parse_trip_plan_response
from .prompts import (
    ATTRACTION_AGENT_PROMPT,
    HOTEL_AGENT_PROMPT,
    PLANNER_AGENT_PROMPT,
    WEATHER_AGENT_PROMPT,
    build_planner_user_query,
)


class MultiAgentTripPlanner:
    """多智能体旅行规划系统

    工作流程：串行执行前 3 个 Agent（共享单一 MCP 连接）→ Planner Agent 整合 → 解析为 TripPlan
    """

    def __init__(self):
        print("🔄 开始初始化LangChain多智能体旅行规划系统...")
        self.llm = get_llm()
        self.amap_service = get_amap_service()
        self._initialized = False
        self._init_lock = asyncio.Lock()
        print("✅ LangChain多智能体系统实例已创建（延迟初始化）")

    async def _ensure_initialized(self):
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return
            await self._initialize_agents()
            self._initialized = True

    async def _initialize_agents(self):
        print("  - 初始化中...")
        mcp_tools = await self.amap_service.get_tools()

        print("  - 创建景点搜索Agent...")
        self.attraction_agent = self._create_agent(
            ATTRACTION_AGENT_PROMPT, mcp_tools, "景点搜索专家"
        )

        print("  - 创建天气查询Agent...")
        self.weather_agent = self._create_agent(
            WEATHER_AGENT_PROMPT, mcp_tools, "天气查询专家"
        )

        print("  - 创建酒店推荐Agent...")
        self.hotel_agent = self._create_agent(
            HOTEL_AGENT_PROMPT, mcp_tools, "酒店推荐专家"
        )

        print("  - 创建行程规划Agent...")
        self.planner_agent = self._create_agent(
            PLANNER_AGENT_PROMPT, [], "行程规划专家"
        )

        print(f"   景点搜索Agent: {len(mcp_tools)} 个工具")
        print(f"   天气查询Agent: {len(mcp_tools)} 个工具")
        print(f"   酒店推荐Agent: {len(mcp_tools)} 个工具")
        print("   行程规划Agent: 0 个工具")
        print("✅ LangChain多智能体系统初始化成功")

    def _create_agent(self, system_prompt: str, tools: List[BaseTool], name: str):
        return create_agent(
            name=name,
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt,
        )

    async def _invoke_agent(self, agent, query: str, step_name: str) -> str:
        """统一 Agent 调用入口"""
        started_at = time.monotonic()
        print(f"  ▶ 调用 {step_name} Agent...", flush=True)

        try:
            result = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
            messages = result.get("messages", [])
            content = messages[-1].content if messages else ""
            elapsed = time.monotonic() - started_at
            preview = content.replace("\n", " ")[:120]
            print(
                f"  ✅ {step_name} 完成 ({elapsed:.1f}s, {len(content)} 字符)"
                + (f" | {preview}..." if preview else ""),
                flush=True,
            )
            return content
        except Exception as e:
            elapsed = time.monotonic() - started_at
            print(f"  ⚠️  {step_name} 失败 ({elapsed:.1f}s): {str(e)}", flush=True)
            return ""

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        await self._ensure_initialized()

        try:
            print(f"\n{'=' * 60}")
            print("🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(
                f"偏好: {', '.join(request.preferences) if request.preferences else '无'}"
            )
            print(f"{'=' * 60}\n", flush=True)

            pipeline_started_at = time.monotonic()
            print(
                "🔁 串行执行 MCP Agent（避免单一 stdio 连接并发）",
                flush=True,
            )

            attraction_response = await self._search_attractions(request)
            weather_response = await self._query_weather(request)
            hotel_response = await self._search_hotels(request)

            print(
                f"⏱️  前 3 步 MCP Agent 总耗时: {time.monotonic() - pipeline_started_at:.1f}s",
                flush=True,
            )

            planner_response = await self._generate_plan(
                request, attraction_response, weather_response, hotel_response
            )

            trip_plan = self._parse_response(planner_response, request)

            print(f"{'=' * 60}")
            print("✅ 旅行计划生成完成!")
            print(f"{'=' * 60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return create_fallback_plan(request)

    async def _search_attractions(self, request: TripRequest) -> str:
        print("📍 [1/4] 搜索景点...", flush=True)
        keywords = request.preferences[0] if request.preferences else "景点"
        query = f"请使用maps_text_search工具搜索{request.city}的{keywords}相关景点。"
        return await self._invoke_agent(self.attraction_agent, query, "景点搜索")

    async def _query_weather(self, request: TripRequest) -> str:
        print("🌤️  [2/4] 查询天气...", flush=True)
        query = f"请使用maps_weather工具查询{request.city}的天气信息。"
        return await self._invoke_agent(self.weather_agent, query, "天气查询")

    async def _search_hotels(self, request: TripRequest) -> str:
        print("🏨 [3/4] 搜索酒店...", flush=True)
        query = (
            f"请使用maps_text_search工具搜索{request.city}的酒店，关键词使用'酒店'。"
        )
        return await self._invoke_agent(self.hotel_agent, query, "酒店搜索")

    async def _generate_plan(
        self, request: TripRequest, attractions: str, weather: str, hotels: str
    ) -> str:
        print("📋 [4/4] 生成行程计划...", flush=True)
        query = build_planner_user_query(request, attractions, weather, hotels)
        return await self._invoke_agent(self.planner_agent, query, "行程规划")

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        try:
            return parse_trip_plan_response(response, request)
        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print("   将使用备用方案生成计划")
            return create_fallback_plan(request)


_trip_planner: Optional[MultiAgentTripPlanner] = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    global _trip_planner

    if _trip_planner is None:
        _trip_planner = MultiAgentTripPlanner()

    return _trip_planner
