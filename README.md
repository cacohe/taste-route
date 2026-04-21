# LangChain智能旅行助手 🌍✈️

基于LangChain框架构建的智能旅行规划助手，集成高德地图MCP服务和MiniMax大模型，提供个性化的旅行计划。

## ✨ 功能特点

- 🤖 **AI驱动的旅行规划**: 基于LangChain ReAct Agent架构，4个专业Agent协作生成详细的多日旅程
- 🗺️ **高德地图集成**: 通过langchain-mcp-adapters接入高德地图服务，支持景点搜索、路线规划、天气查询
- 🧠 **智能工具调用**: Agent自动调用MCP工具，获取实时POI、路线和天气信息
- 🎨 **现代化前端**: Vue3 + TypeScript + Vite，响应式设计，流畅的用户体验
- 📱 **完整功能**: 包含住宿、交通、餐饮和景点游览时间推荐

## 🏗️ 技术栈

### 后端
- **框架**: LangChain + LangGraph
- **LLM**: MiniMax M2.7 (通过OpenAI兼容API)
- **MCP工具**: langchain-mcp-adapters + amap-mcp-server (高德地图)
- **API**: FastAPI

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design Vue
- **地图服务**: 高德地图 JavaScript API
- **HTTP客户端**: Axios

## 📁 项目结构

```
trip-planner/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # Agent实现
│   │   │   └── trip_planner_agent.py
│   │   ├── api/               # FastAPI路由
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── trip.py
│   │   │       ├── poi.py
│   │   │       └── map.py
│   │   ├── services/          # 服务层
│   │   │   ├── amap_service.py
│   │   │   ├── llm_service.py
│   │   │   └── unsplash_service.py
│   │   ├── models/           # 数据模型
│   │   │   └── schemas.py
│   │   └── config.py         # 配置管理
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── components/       # Vue组件
│   │   ├── services/        # API服务
│   │   ├── types/           # TypeScript类型
│   │   └── views/          # 页面视图
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

## 🚀 快速开始

### 前提条件

- Python 3.10+
- Node.js 16+
- pnpm (推荐) 或 npm
- MiniMax API密钥
- 高德地图API密钥 (Web服务API和Web端JS API)

### 后端安装

1. 进入后端目录
```bash
cd backend
```

2. 安装依赖
```bash
pip install -r requirements.txt
# 或使用 uv
uv pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入你的API密钥
```

必需的配置项：
- `MINIMAX_API_KEY` - MiniMax API密钥
- `MINIMAX_BASE_URL` - MiniMax API地址 (默认: https://api.minimaxi.com/v1)
- `MINIMAX_MODEL` - 模型名称 (默认: MiniMax-M2.7)
- `AMAP_API_KEY` - 高德地图Web服务API密钥

4. 启动后端服务
```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端安装

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
pnpm install
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入高德地图Web API Key和Web端JS API Key
```

必需的配置项：
- `VITE_AMAP_WEB_KEY` - 高德地图Web服务API Key
- `VITE_AMAP_WEB_JS_KEY` - 高德地图Web端JS API Key

4. 启动开发服务器
```bash
pnpm dev
```

5. 打开浏览器访问 `http://localhost:5173`

## 📝 使用指南

1. 在首页填写旅行信息:
   - 目的地城市
   - 旅行日期和天数
   - 交通方式偏好
   - 住宿偏好
   - 旅行风格标签

2. 点击"生成旅行计划"按钮

3. 系统将:
   - 并行调用4个专业Agent搜索景点、查询天气、搜索酒店
   - 整合所有信息生成完整的多日行程
   - 返回每日详细行程、景点地图标记、交通路线、天气预报、餐饮推荐

4. 查看结果:
   - 每日详细行程安排
   - 景点信息与地图标记
   - 交通路线规划
   - 天气预报
   - 餐饮推荐

## 🔧 核心实现

### LangChain Agent架构

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

# 初始化LLM
llm = ChatOpenAI(
    model="MiniMax-M2.7",
    base_url="https://api.minimaxi.com/v1",
    api_key="your_api_key"
)

# 创建Agent
agent = create_agent(
    model=llm,
    tools=mcp_tools,  # 从langchain-mcp-adapters加载
    system_prompt="你是一个专业的旅行规划助手..."
)
```

### 多Agent协作流程

1. **景点搜索Agent**: 搜索目的地热门景点
2. **天气查询Agent**: 查询未来几天的天气预报
3. **酒店推荐Agent**: 搜索合适的住宿酒店
4. **行程规划Agent**: 综合以上信息生成完整行程

### MCP工具调用

Agent通过MCP协议调用高德地图服务：
- `maps_text_search`: 搜索景点POI
- `maps_weather`: 查询天气
- `maps_direction_walking_by_address`: 步行路线规划
- `maps_direction_driving_by_address`: 驾车路线规划
- `maps_direction_transit_integrated_by_address`: 公共交通路线规划

## 📄 API文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看完整的API文档。

主要端点：
- `POST /api/trip/plan` - 生成旅行计划
- `GET /api/map/poi` - 搜索POI
- `GET /api/map/weather` - 查询天气
- `POST /api/map/route` - 规划路线
- `GET /api/poi/detail/{poi_id}` - 获取POI详情
- `GET /api/poi/photo` - 获取景点图片

## 🤝 贡献指南

欢迎提交Pull Request或Issue！

## 📜 开源协议

MIT License

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - AI应用框架
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) - MCP适配器
- [高德地图开放平台](https://lbs.amap.com/) - 地图服务
- [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server) - 高德地图MCP服务器
- [MiniMax](https://www.minimaxi.com/) - 大模型服务

---

**LangChain智能旅行助手** - 让旅行计划变得简单而智能 🌈
