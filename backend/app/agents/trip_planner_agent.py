"""多智能体旅行规划系统 - 使用LangChain实现ReAct代理协作"""

import json
import asyncio
from typing import List, Optional
from langchain.agents import create_agent  # LangChain统一的agent创建入口
from langchain_core.messages import HumanMessage  # 人类消息类型
from langchain_core.tools import BaseTool  # LangChain工具基类
from ..services.llm_service import get_llm  # 获取LLM实例
from ..services.amap_service import get_amap_service  # 获取高德地图服务
from ..models.schemas import (
    TripRequest,
    TripPlan,
    DayPlan,
    Attraction,
    Meal,
    WeatherInfo,
    Location,
    Hotel,
)
from ..config import get_settings


# ========== Agent提示词定义 ==========
# 每个Agent负责一个特定任务，通过MCP工具获取真实数据

ATTRACTION_AGENT_PROMPT = """你是一个景点搜索专家。根据城市和用户偏好搜索合适的景点。

你必须使用工具来搜索景点，不要自己编造景点信息。

可用工具：
- maps_text_search: 搜索POI，需要提供keywords和city参数

示例查询：
用户: "搜索北京的历史文化景点"
你应调用: maps_text_search(keywords="历史文化", city="北京")

用户: "搜索上海的公园"
你应调用: maps_text_search(keywords="公园", city="上海")

## 输出要求
搜索完成后，请按以下JSON格式返回景点列表：
```json
{
  "city": "城市名称",
  "attractions": [
    {
      "name": "景点名称",
      "address": "详细地址",
      "location": {"longitude": 116.397128, "latitude": 39.916527},
      "visit_duration": 120,
      "description": "景点描述",
      "category": "景点类别",
      "ticket_price": 60
    }
  ]
}
```

**重要**：
1. location的longitude和latitude必须是真实经纬度坐标
2. visit_duration单位是分钟
3. ticket_price单位是元，没有门票则写0
4. 每个城市返回5-10个景点即可
5. 只返回JSON，不要添加其他解释文字"""

WEATHER_AGENT_PROMPT = """你是一个天气查询专家。查询指定城市的天气信息。

你必须使用工具来查询天气，不要自己编造天气信息。

可用工具：
- maps_weather: 查询天气，需要提供city参数

示例查询：
用户: "查询北京天气"
你应调用: maps_weather(city="北京")

用户: "上海的天气怎么样"
你应调用: maps_weather(city="上海")

## 输出要求
查询完成后，请按以下JSON格式返回天气信息：
```json
{
  "city": "城市名称",
  "weather_info": [
    {
      "date": "2026-04-01",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ]
}
```

**重要**：
1. 日期格式必须是YYYY-MM-DD
2. day_temp和night_temp必须是数字，不要带°C单位
3. 返回3-5天的天气信息
4. 只返回JSON，不要添加其他解释文字"""

HOTEL_AGENT_PROMPT = """你是一个酒店推荐专家。根据城市和景点位置推荐合适的酒店。

你必须使用工具来搜索酒店，不要自己编造酒店信息。

可用工具：
- maps_text_search: 搜索酒店，需要提供keywords和city参数

示例查询：
用户: "搜索北京的酒店"
你应调用: maps_text_search(keywords="酒店", city="北京")

## 输出要求
搜索完成后，请按以下JSON格式返回酒店列表：
```json
{
  "city": "城市名称",
  "hotels": [
    {
      "name": "酒店名称",
      "address": "酒店地址",
      "location": {"longitude": 116.397128, "latitude": 39.916527},
      "price_range": "300-500元",
      "rating": "4.5",
      "type": "经济型酒店",
      "estimated_cost": 400
    }
  ]
}
```

**重要**：
1. location的longitude和latitude必须是真实经纬度坐标
2. price_range格式如"300-500元"
3. rating格式如"4.5"
4. estimated_cost是每晚价格，单位是元
5. 返回5-8个酒店即可
6. 只返回JSON，不要添加其他解释文字"""

PLANNER_AGENT_PROMPT = """你是一个行程规划专家。根据景点信息、天气信息和酒店信息，生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划：
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

重要提示：
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. 必须包含预算信息
"""


class MultiAgentTripPlanner:
    """多智能体旅行规划系统

    使用LangChain的create_agent创建4个专业Agent：
    - Attraction Agent：负责搜索景点
    - Weather Agent：负责查询天气
    - Hotel Agent：负责推荐酒店
    - Planner Agent：负责整合信息生成行程

    工作流程：并行执行前3个Agent → 将结果传给Planner Agent → 生成完整行程
    """

    def __init__(self):
        """初始化多智能体规划器（延迟初始化模式）"""
        print("🔄 开始初始化LangChain多智能体旅行规划系统...")
        self.llm = get_llm()
        self.amap_service = get_amap_service()
        self._initialized = False
        self._init_lock = asyncio.Lock()  # 确保线程安全的延迟初始化
        print(f"✅ LangChain多智能体系统实例已创建（延迟初始化）")

    async def _ensure_initialized(self):
        """确保Agent已初始化（异步，线程安全）

        使用双检查锁定模式：
        1. 快速路径：已初始化则直接返回
        2. 加锁路径：首次初始化时防止多线程同时初始化
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return
            await self._initialize_agents()
            self._initialized = True

    async def _initialize_agents(self):
        """初始化所有Agent

        创建4个LangChain Agent：
        - 前3个Agent共享MCP工具（景点搜索、天气查询）
        - Planner Agent无工具（纯LLM生成）
        """
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
        print(f"   行程规划Agent: 0 个工具")
        print(f"✅ LangChain多智能体系统初始化成功")

    def _create_agent(self, system_prompt: str, tools: List[BaseTool], name: str):
        """创建LangChain Agent的统一入口

        Args:
            system_prompt: 系统提示词，定义Agent角色和能力
            tools: Agent可使用的工具列表
            name: Agent名称，用于标识

        Returns:
            创建的Agent实例（实际是Compiled StateGraph）
        """
        agent = create_agent(
            name=name,
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt,
        )
        return agent

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        """生成旅行计划的主入口

        执行完整的多Agent协作流程：
        1. 并行搜索景点、查询天气、搜索酒店
        2. 将3个Agent的结果整合后发送给Planner Agent
        3. 解析Planner输出为TripPlan对象

        Args:
            request: TripRequest，包含城市、日期、偏好等旅行需求

        Returns:
            TripPlan: 完整的旅行计划对象
        """
        await self._ensure_initialized()

        try:
            print(f"\n{'=' * 60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(
                f"偏好: {', '.join(request.preferences) if request.preferences else '无'}"
            )
            print(f"{'=' * 60}\n")

            # 并行执行前3个Agent
            attraction_response = await self._search_attractions(request)
            weather_response = await self._query_weather(request)
            hotel_response = await self._search_hotels(request)

            # 将结果发送给Planner Agent生成完整行程
            planner_response = await self._generate_plan(
                request, attraction_response, weather_response, hotel_response
            )

            trip_plan = self._parse_response(planner_response, request)

            print(f"{'=' * 60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'=' * 60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return self._create_fallback_plan(request)

    async def _search_attractions(self, request: TripRequest) -> str:
        """步骤1：搜索景点

        使用Attraction Agent + maps_text_search工具搜索用户偏好相关的景点。

        Args:
            request: TripRequest

        Returns:
            Agent返回的原始文本（包含JSON格式的景点列表）
        """
        print("📍 步骤1: 搜索景点...")

        # 从用户偏好中提取关键词，默认为"景点"
        keywords = request.preferences[0] if request.preferences else "景点"
        query = f"请使用maps_text_search工具搜索{request.city}的{keywords}相关景点。"

        try:
            result = await self.attraction_agent.ainvoke(
                {"messages": [HumanMessage(content=query)]}
            )
            messages = result.get("messages", [])
            response = messages[-1].content if messages else ""
        except Exception as e:
            print(f"⚠️  景点搜索失败: {str(e)}")
            response = ""

        return response

    async def _query_weather(self, request: TripRequest) -> str:
        """步骤2：查询天气

        使用Weather Agent + maps_weather工具查询目的地城市的天气预报。

        Args:
            request: TripRequest

        Returns:
            Agent返回的原始文本（包含JSON格式的天气信息）
        """
        print("🌤️  步骤2: 查询天气...")

        query = f"请使用maps_weather工具查询{request.city}的天气信息。"

        try:
            result = await self.weather_agent.ainvoke(
                {"messages": [HumanMessage(content=query)]}
            )
            messages = result.get("messages", [])
            response = messages[-1].content if messages else ""
        except Exception as e:
            print(f"⚠️  天气查询失败: {str(e)}")
            response = ""

        return response

    async def _search_hotels(self, request: TripRequest) -> str:
        """步骤3：搜索酒店

        使用Hotel Agent + maps_text_search工具搜索目的地城市的酒店。

        Args:
            request: TripRequest

        Returns:
            Agent返回的原始文本（包含JSON格式的酒店列表）
        """
        print("🏨 步骤3: 搜索酒店...")

        query = (
            f"请使用maps_text_search工具搜索{request.city}的酒店，关键词使用'酒店'。"
        )

        try:
            result = await self.hotel_agent.ainvoke(
                {"messages": [HumanMessage(content=query)]}
            )
            messages = result.get("messages", [])
            response = messages[-1].content if messages else ""
        except Exception as e:
            print(f"⚠️  酒店搜索失败: {str(e)}")
            response = ""

        return response

    async def _generate_plan(
        self, request: TripRequest, attractions: str, weather: str, hotels: str
    ) -> str:
        """步骤4：生成行程计划

        将前3个Agent的结果整合后发送给Planner Agent，
        Planner Agent无工具，直接使用LLM根据提示词生成完整行程。

        Args:
            request: TripRequest
            attractions: 景点搜索结果（原始文本）
            weather: 天气查询结果（原始文本）
            hotels: 酒店搜索结果（原始文本）

        Returns:
            Planner Agent返回的原始文本（包含JSON格式的完整行程）
        """
        print("📋 步骤4: 生成行程计划...")

        query = self._build_planner_query(request, attractions, weather, hotels)

        try:
            result = await self.planner_agent.ainvoke(
                {"messages": [HumanMessage(content=query)]}
            )
            messages = result.get("messages", [])
            response = messages[-1].content if messages else ""
        except Exception as e:
            print(f"⚠️  行程规划失败: {str(e)}")
            response = ""

        return response

    def _build_planner_query(
        self, request: TripRequest, attractions: str, weather: str, hotels: str
    ) -> str:
        """构建发送给Planner Agent的查询文本

        将前3个Agent的原始输出解析为结构化JSON后，
        与用户需求一起组装成Planner的输入提示词。

        Args:
            request: TripRequest
            attractions: 景点搜索结果（原始文本）
            weather: 天气查询结果（原始文本）
            hotels: 酒店搜索结果（原始文本）

        Returns:
            完整的查询字符串，包含所有上下文信息
        """
        # 从Agent响应中提取JSON数据并格式化
        parsed_attractions = self._extract_json_data(attractions)
        parsed_weather = self._extract_json_data(weather)
        parsed_hotels = self._extract_json_data(hotels)

        query = f"""你是一个行程规划专家。请根据以下信息为{request.city}规划{request.travel_days}天旅行计划。

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {", ".join(request.preferences) if request.preferences else "无"}

**景点信息:**
{parsed_attractions}

**天气信息:**
{parsed_weather}

**酒店信息:**
{parsed_hotels}

**输出要求:**
请生成完整的旅行计划JSON，包含每天的景点安排、餐饮和住宿。严格按照以下JSON格式返回：
```json
{{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {{
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {{"longitude": 116.397128, "latitude": 39.916527}},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      }},
      "attractions": [
        {{
          "name": "景点名称",
          "address": "详细地址",
          "location": {{"longitude": 116.397128, "latitude": 39.916527}},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }}
      ],
      "meals": [
        {{"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30}},
        {{"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50}},
        {{"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}}
      ]
    }}
  ],
  "weather_info": [
    {{
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }}
  ],
  "overall_suggestions": "总体建议",
  "budget": {{
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }}
}}
```

**重要**：
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店
4. 景点的经纬度坐标必须准确
5. 只返回JSON，不要添加其他文字"""
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        return query

    def _extract_json_data(self, response: str) -> str:
        """从Agent响应中提取JSON数据

        Agent可能返回多种格式：
        - ```json ... ```
        - ``` ... ```
        - 直接的 { ... }

        此方法统一提取并重新格式化。

        Args:
            response: Agent返回的原始文本

        Returns:
            格式化后的JSON字符串，如果提取失败则返回原始文本
        """
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
                return response

            data = json.loads(json_str)
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            return response

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """解析Planner Agent的响应

        从Planner返回的文本中提取JSON，转换为TripPlan对象。
        解析失败时使用备用方案生成计划。

        Args:
            response: Planner Agent返回的原始文本
            request: 原始请求（用于生成备用计划）

        Returns:
            TripPlan对象
        """
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
                raise ValueError("响应中未找到JSON数据")

            data = json.loads(json_str)
            trip_plan = self._fix_and_validate_plan(data, request)
            return trip_plan

        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return self._create_fallback_plan(request)

    def _fix_and_validate_plan(self, data: dict, request: TripRequest) -> TripPlan:
        """修复并验证行程计划数据

        由于模型可能返回不完整的location对象（如 longitude: 0），
        此方法使用Pydantic验证并填充默认值。

        Args:
            data: 从JSON解析的原始字典
            request: 原始请求

        Returns:
            验证后的TripPlan对象
        """
        return TripPlan(**data)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用旅行计划

        当Agent执行失败时，使用简单的规则生成一个基本可行的计划。
        景点位置使用估算坐标，餐饮使用默认推荐。

        Args:
            request: TripRequest

        Returns:
            基础TripPlan对象
        """
        from datetime import datetime, timedelta

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
                    Meal(
                        type="dinner", name=f"第{i + 1}天晚餐", description="晚餐推荐"
                    ),
                ],
            )
            days.append(day_plan)

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。",
        )


# 全局单例实例
_trip_planner: Optional[MultiAgentTripPlanner] = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取旅行规划Agent单例

    Returns:
        MultiAgentTripPlanner实例
    """
    global _trip_planner

    if _trip_planner is None:
        _trip_planner = MultiAgentTripPlanner()

    return _trip_planner
