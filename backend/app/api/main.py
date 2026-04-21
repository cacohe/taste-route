"""FastAPI主应用 - 应用入口点

初始化FastAPI应用、配置中间件、注册路由、定义启动/关闭事件。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings, validate_config, print_config
from .routes import trip, poi, map as map_routes

# 获取配置单例
settings = get_settings()

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于LangChain框架的智能旅行规划助手API",
    docs_url="/docs",  # Swagger文档地址
    redoc_url="/redoc",  # ReDoc文档地址
)

# 配置CORS跨域中间件，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),  # 允许的前端域名
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(trip.router, prefix="/api")  # /api/trip/*
app.include_router(poi.router, prefix="/api")  # /api/poi/*
app.include_router(map_routes.router, prefix="/api")  # /api/map/*


@app.on_event("startup")
async def startup_event():
    """应用启动事件

    应用启动时执行：
    - 打印欢迎信息和配置状态
    - 验证配置完整性
    - 验证失败会阻止应用启动
    """
    print("\n" + "=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 60)

    # 打印当前配置（不含敏感信息）
    print_config()

    # 验证配置完整性
    try:
        validate_config()
        print("\n✅ 配置验证通过")
    except ValueError as e:
        print(f"\n❌ 配置验证失败:\n{e}")
        print("\n请检查.env文件并确保所有必要的配置项都已设置")
        raise

    print("\n" + "=" * 60)
    print("📚 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件

    应用关闭时执行清理操作。
    """
    print("\n" + "=" * 60)
    print("👋 应用正在关闭...")
    print("=" * 60 + "\n")


@app.get("/")
async def root():
    """根路径 - 返回应用信息

    Returns:
        包含应用名称、版本、状态的字典
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health():
    """健康检查端点

    用于Kubernetes/负载均衡器探测应用状态。

    Returns:
        包含健康状态、应用名称、版本的字典
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


# 直接运行入口（用于开发调试）
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.main:app", host=settings.host, port=settings.port, reload=True)
