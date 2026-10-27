# TasteRoute

- **状态：** Qloo Agentic Hackathon 参赛项目，正在开发
- **来源：** 基于作者的 [`trip-planner`](https://github.com/cacohe/trip-planner) 显著改造并保留历史
- **License：** [MIT](LICENSE.md)

TasteRoute 是一个以文化品味为核心的旅行 Agent。用户选择喜欢的电影、音乐、书籍、品牌或地点，Qloo Taste AI 将这些跨领域兴趣映射为目的地中的候选体验；后端只允许通过验证的 Qloo 候选进入行程，并保留每项推荐的来源和解释信息。

当前分支仍在迁移原有界面与接口。尚未完成的 Qloo 实时集成和公开 Demo 不在本 README 中宣称可用。

## 已实现功能

- 首页表单：城市、日期、交通、住宿、偏好标签、自由文本
- `POST /api/trip/plan`：景点、天气、酒店三个 Agent 串行调用同一条 MCP stdio 连接，再由无工具的行程规划 Agent 生成 JSON
- 解析模型输出（含 Markdown 代码块），缺字段时补齐；解析或执行失败时返回占位行程，HTTP 仍为 200
- `GET /api/poi/photo`：用 Unsplash 按景点名取一张图；未配置密钥时返回空 URL
- 结果页：概览、预算、每日行程、天气、高德 JS 地图（景点标记，相邻景点用直线连接）
- 结果页本地编辑，以及导出图片 / PDF
- 后端 pytest（解析与备用计划）、前端 vitest（表单天数与错误文案），GitHub Actions 同时做前端类型检查和构建

未实现：账号、行程落库、真实路网导航、酒店按住宿偏好筛选、独立的地图 API。

## 技术栈

| 技术 | 在本项目中的应用 |
| --- | --- |
| Python 3.12 | 后端语言；CI 使用此版本 |
| [uv](https://docs.astral.sh/uv/) | CI 与 Render 上安装 `backend/requirements.txt` |
| [LangChain](https://www.langchain.com/) | `create_agent` 组装模型、工具和系统提示 |
| [langchain-openai](https://python.langchain.com/docs/integrations/chat/openai/) | 以 OpenAI 兼容接口调用 MiniMax |
| [MCP](https://modelcontextprotocol.io/)（`langchain-mcp-adapters`） | stdio 启动 `amap-mcp-server`，加载高德工具 |
| [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server) `0.1.11` | 景点搜索 `maps_text_search`、天气 `maps_weather` |
| FastAPI / uvicorn | `/api/trip/plan`、`/api/poi/photo`、`/docs` |
| pydantic / pydantic-settings | 请求响应模型与 `.env` |
| Node.js 22 / pnpm 9 | 前端工具链；CI 使用此版本 |
| Vue 3 + TypeScript + Vite | 首页与结果页 |
| Ant Design Vue | 表单、卡片、菜单 |
| 高德 JS API | 结果页地图 |
| axios | 调用后端，超时 20 分钟 |
| vitest / pytest | 单元测试 |

## 项目结构

```
trip-planner/
├── docs/
│   └── NOTES.md                      # 学习笔记
├── .github/workflows/ci.yml          # 后端测试 + 前端测试与构建
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── trip_planner_agent.py # 四个 Agent 的串行编排
│   │   │   ├── prompts.py            # 提示词与行程 JSON Schema
│   │   │   ├── parsers.py            # 从模型文本提取并修复 JSON
│   │   │   └── fallback.py           # 失败时的占位行程
│   │   ├── api/                      # FastAPI 入口与路由
│   │   ├── services/
│   │   │   ├── amap_service.py       # MCP stdio 会话
│   │   │   ├── llm_service.py        # MiniMax ChatOpenAI
│   │   │   └── unsplash_service.py   # 景点图片
│   │   ├── models/schemas.py
│   │   └── config.py
│   ├── tests/
│   ├── requirements.txt
│   ├── run.py
│   └── .env.example
├── frontend/
│   ├── src/views/                    # Home.vue、Result.vue
│   ├── src/services/api.ts
│   ├── src/utils/                    # 表单与错误文案，含测试
│   ├── package.json
│   ├── pnpm-lock.yaml                # CI 使用这份锁
│   └── .env.example
├── LICENSE.md
└── README.md
```

## 快速开始

需要 **Python 3.12**、**Node.js 22**、[pnpm 9](https://pnpm.io/)、MiniMax API 密钥，以及高德 Web 服务 Key、Web 端 JS API Key。

### 1. 克隆并准备环境变量

```bash
git clone https://github.com/cacohe/trip-planner.git
cd trip-planner
```

后端：

```bash
cd backend
cp .env.example .env
```

Windows PowerShell 可用 `Copy-Item .env.example .env`。

| 环境变量 | 用途 |
| --- | --- |
| `MINIMAX_API_KEY` | MiniMax；缺失时进程仍能启动，第一次规划会失败并走备用计划 |
| `MINIMAX_BASE_URL` | 默认 `https://api.minimaxi.com/v1` |
| `MINIMAX_MODEL` | 默认 `MiniMax-M2.7` |
| `AMAP_API_KEY` | 高德 Web 服务 Key；缺失时启动直接失败 |
| `UNSPLASH_ACCESS_KEY` | 景点图片，可留空 |
| `CORS_ORIGINS` | 允许的前端源，逗号分隔 |

前端：

```bash
cd frontend
cp .env.example .env
```

| 环境变量 | 用途 |
| --- | --- |
| `VITE_API_BASE_URL` | 后端地址，本地默认 `http://localhost:8000` |
| `VITE_AMAP_WEB_JS_KEY` | 高德 Web 端 JS API Key，结果页地图使用 |
| `VITE_AMAP_WEB_KEY` | 示例文件中的 Web 服务 Key 字段；当前地图加载只用 JS Key |

### 2. 安装并启动

后端（在 `backend/`）：

```bash
uv pip install -r requirements.txt --system
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

也可以 `python run.py`，它读取 `HOST` / `PORT`。接口文档在 `http://localhost:8000/docs`。

前端（在 `frontend/`）：

```bash
pnpm install
pnpm dev
```

浏览器打开 `http://localhost:5173`。

## 常用命令

```bash
# backend/
uv pip install -r requirements.txt --system
python -m compileall app
python -m pytest tests/ -q

# frontend/
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

后端测试覆盖 JSON 提取、行程修补和备用计划，不调用 MiniMax，也不启动 MCP。前端测试覆盖天数计算和错误文案。

## CI

`.github/workflows/ci.yml` 在 `main` 的 push 和 pull request 上运行：

- 后端：Python 3.12，`uv pip install -r requirements.txt --system`，`compileall`，`pytest`
- 前端：Node.js 22、pnpm 9，`pnpm install --frozen-lockfile`，`pnpm test`，`pnpm build`（含 `vue-tsc`）

## Render 部署

现有线上环境是 **1 个 Web Service（后端）+ 1 个 Static Site（前端）**。首页记录在仓库 About 里。

### Static Site（前端）

| 配置项 | 值 |
| --- | --- |
| Root Directory | `frontend` |
| Build Command | `pnpm install && pnpm build` |
| Publish Directory | `dist` |

构建期环境变量：`VITE_API_BASE_URL`（后端 Web Service 的 URL）、`VITE_AMAP_WEB_JS_KEY`。

### Web Service（后端）

| 配置项 | 值 |
| --- | --- |
| Root Directory | `backend` |
| Build Command | `pip install uv && uv pip install -r requirements.txt --system` |
| Start Command | `python -m uvicorn app.api.main:app --host 0.0.0.0 --port $PORT` |

运行期环境变量：`MINIMAX_API_KEY`、`MINIMAX_BASE_URL`、`MINIMAX_MODEL`、`AMAP_API_KEY`、可选的 `UNSPLASH_ACCESS_KEY`、`CORS_ORIGINS`（前端 Static Site 域名）。

Render 注入 `PORT`，启动命令使用 `$PORT`。`amap-mcp-server` 已在 `requirements.txt` 中，后端用 `python -m amap_mcp_server` 拉起，不需要再装 `uvx`。免费实例约 15 分钟无请求会休眠；一次规划要串行四次模型调用，耗时和内存都高于普通 CRUD。

## 范围与限制

- 三个 MCP Agent 必须串行。它们共用一个 stdio 会话，并发会抢同一条连接。
- 行程规划 Agent 没有工具。景点、天气、酒店的文本原样塞进它的用户消息。
- 提示词点名的工具只有 `maps_text_search` 和 `maps_weather`。`amap-mcp-server` 还会暴露步行、驾车、公交路线工具，本仓库不调用；地图上的线是前端直线。
- 景点搜索只用 `preferences` 的第一项，没有偏好时关键词是「景点」。酒店搜索关键词固定为「酒店」，不读取住宿偏好。
- 备用行程的坐标从北京附近的常数递增，失败时接口仍返回 `success: true`。
- 结果页的编辑和导出只存在于浏览器，刷新即丢失。
- 无登录、无数据库。规划器和 MCP 会话都是进程内单例，关闭应用时没有显式结束 MCP 子进程。
- Python 依赖除 `amap-mcp-server==0.1.11` 外不锁定版本。前端 CI 以 `pnpm-lock.yaml` 为准，仓库里同时留着 `package-lock.json`。

## License

[MIT](LICENSE.md)
