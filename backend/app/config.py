"""配置管理模块 - 集中管理应用所有配置项"""

from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类

    使用Pydantic的BaseSettings实现：
    - 自动从环境变量读取配置
    - 支持 .env 文件
    - 配置文件路径: 后端工作目录下的 .env

    配置优先级: 环境变量 > .env文件 > 默认值
    """

    # ========== 应用基本信息 ==========
    app_name: str = "TasteRoute"
    app_version: str = "2.0.0"
    debug: bool = False

    # ========== 服务器配置 ==========
    host: str = "0.0.0.0"
    port: int = 8000

    # ========== CORS跨域配置 ==========
    # 允许的前端域名列表，逗号分隔
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # ========== OpenAI-compatible LLM 配置 ==========
    # 厂商由服务地址、凭据和模型名决定；应用不内置厂商默认值。
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=180.0, gt=0, le=600)
    llm_max_retries: int = Field(default=1, ge=0, le=3)

    # ========== Qloo Taste AI 配置 ==========
    qloo_api_key: str = ""
    qloo_api_base_url: str = "https://hackathon.api.qloo.com"
    qloo_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    qloo_max_results: int = Field(default=20, ge=1, le=50)

    # ========== Bounded planning agent ===========
    agent_max_decisions: int = Field(default=8, ge=4, le=20)
    qloo_nearby_radius_meters: int = Field(default=10_000, ge=1_000, le=50_000)

    # ========== Optional driving route evidence ===========
    routing_base_url: str = "https://router.project-osrm.org"
    routing_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    # ========== Public demo safeguards (process-local) ==========
    search_rate_limit_per_minute: int = Field(default=30, ge=1, le=300)
    plan_rate_limit_per_minute: int = Field(default=5, ge=1, le=60)
    plan_max_concurrency: int = Field(default=3, ge=1, le=20)
    search_cache_ttl_seconds: float = Field(default=600, ge=0, le=3600)
    plan_cache_ttl_seconds: float = Field(default=900, ge=0, le=3600)

    # ========== 日志配置 ==========
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    def get_cors_origins_list(self) -> list[str]:
        """获取CORS origins列表

        将逗号分隔的字符串转换为列表，
        用于FastAPI CORS中间件配置。

        Returns:
            前端域名列表
        """
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_llm_config(self) -> dict:
        """Return the provider-neutral OpenAI-compatible LLM configuration."""
        return {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "model": self.llm_model,
        }

    def get_qloo_config(self) -> dict:
        """Return bounded server-only configuration for the Qloo client."""
        return {
            "api_key": self.qloo_api_key,
            "base_url": self.qloo_api_base_url.rstrip("/"),
            "timeout_seconds": self.qloo_timeout_seconds,
            "max_results": self.qloo_max_results,
        }


# 全局配置单例
settings = Settings()


def get_settings() -> Settings:
    """获取配置单例

    Returns:
        Settings实例
    """
    return settings


def validate_config(candidate: Settings | None = None):
    """验证配置完整性

    检查 Qloo 与行程生成模型所需的服务端密钥。

    Raises:
        ValueError: 当必填配置项缺失时

    Returns:
        True: 验证通过
    """
    errors = []
    active_settings = candidate or settings

    if not active_settings.qloo_api_key:
        errors.append("QLOO_API_KEY未配置")
    if not _is_http_endpoint(active_settings.qloo_api_base_url):
        errors.append("Qloo Base URL必须是有效的HTTP(S)地址")
    if not _is_http_endpoint(active_settings.routing_base_url):
        errors.append("Routing Base URL必须是有效的HTTP(S)地址")

    llm_config = active_settings.get_llm_config()
    if not llm_config["api_key"]:
        errors.append("LLM API Key未配置")
    if not _is_http_endpoint(llm_config["base_url"]):
        errors.append("LLM Base URL必须是有效的HTTP(S)地址")
    if not llm_config["model"].strip():
        errors.append("LLM Model未配置")

    # 严重错误：阻止启动
    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    return True


def print_config(candidate: Settings | None = None):
    """打印当前配置概要

    用于启动时显示配置状态，便于调试。
    不会显示敏感信息（如API Key）。
    """
    active_settings = candidate or settings
    print(f"应用名称: {active_settings.app_name}")
    print(f"版本: {active_settings.app_version}")
    print(f"服务器: {active_settings.host}:{active_settings.port}")
    print(f"Qloo API Key: {'已配置' if active_settings.qloo_api_key else '未配置'}")
    print(f"Qloo Base URL: {_safe_endpoint(active_settings.qloo_api_base_url)}")

    llm_config = active_settings.get_llm_config()
    print(f"LLM API Key: {'已配置' if llm_config['api_key'] else '未配置'}")
    print(f"LLM Base URL: {_safe_endpoint(llm_config['base_url'])}")
    print(f"LLM Model: {llm_config['model']}")
    print(f"日志级别: {active_settings.log_level}")


def _safe_endpoint(value: str) -> str:
    """Return only scheme and host so URL-embedded credentials cannot reach logs."""
    try:
        parsed = urlsplit(value)
        if not parsed.scheme or not parsed.hostname:
            return "[configured]" if value else "[not configured]"
        host = parsed.hostname
        if ":" in host:
            host = f"[{host}]"
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.scheme}://{host}{port}"
    except ValueError:
        return "[configured]" if value else "[not configured]"


def _is_http_endpoint(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and parsed.hostname is not None
    except ValueError:
        return False
