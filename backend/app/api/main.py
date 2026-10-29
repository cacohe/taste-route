"""FastAPI主应用 - 应用入口点

初始化FastAPI应用、配置中间件、注册路由、定义启动/关闭事件。
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings, validate_config, print_config
from .routes import health, taste, trip
from .static_site import mount_spa

# 获取配置单例
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("\n" + "=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 60)

    print_config()

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

    yield

    print("\n" + "=" * 60)
    print("👋 应用正在关闭...")
    print("=" * 60 + "\n")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Bounded taste-grounded itinerary planning with Qloo, LangChain, and optional OSRM driving evidence",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trip.router, prefix="/api")
app.include_router(taste.router, prefix="/api")
app.include_router(health.router)

frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
mount_spa(app, frontend_dist)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.main:app", host=settings.host, port=settings.port, reload=True)
