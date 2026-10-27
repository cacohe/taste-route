"""配置管理模块 - 集中管理应用所有配置项"""

import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 加载 .env 环境变量文件
load_dotenv()


class Settings(BaseSettings):
    """应用配置类

    使用Pydantic的BaseSettings实现：
    - 自动从环境变量读取配置
    - 支持 .env 文件
    - 配置文件路径: backend/app/.env

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

    # ========== MiniMax LLM 配置 ==========
    # MiniMax API密钥，用于调用MiniMax M2.7模型
    minimax_api_key: str = ""
    # MiniMax API地址（OpenAI兼容格式）
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    # 使用的模型名称
    minimax_model: str = "MiniMax-M2.7"

    # ========== 兼容旧版配置的字段 ==========
    # 为保持向后兼容，保留这些字段（实际使用 MiniMax 配置）
    openai_api_key: str = ""
    openai_base_url: str = "https://api.minimaxi.com/v1"
    openai_model: str = "MiniMax-M2.7"

    # ========== Qloo Taste AI 配置 ==========
    qloo_api_key: str = ""
    qloo_api_base_url: str = "https://hackathon.api.qloo.com"
    qloo_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    qloo_max_results: int = Field(default=20, ge=1, le=50)

    # ========== Unsplash图片服务配置 ==========
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""

    # ========== 日志配置 ==========
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    def get_cors_origins_list(self) -> List[str]:
        """获取CORS origins列表

        将逗号分隔的字符串转换为列表，
        用于FastAPI CORS中间件配置。

        Returns:
            前端域名列表
        """
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_llm_config(self) -> dict:
        """获取LLM配置字典

        优先使用MiniMax配置，兼容旧版openai字段。
        用于初始化LangChain ChatOpenAI实例。

        Returns:
            包含 api_key、base_url、model 的字典
        """
        api_key = self.minimax_api_key or self.openai_api_key
        base_url = self.minimax_base_url or self.openai_base_url
        model = self.minimax_model or self.openai_model
        return {"api_key": api_key, "base_url": base_url, "model": model}

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

    检查必要的配置项是否已设置：
    - AMAP_API_KEY: 必须配置
    - LLM API Key: 警告但不阻止启动

    Raises:
        ValueError: 当必填配置项缺失时

    Returns:
        True: 验证通过
    """
    errors = []
    warnings = []

    active_settings = candidate or settings

    if not active_settings.qloo_api_key:
        errors.append("QLOO_API_KEY未配置")

    llm_config = active_settings.get_llm_config()
    if not llm_config["api_key"]:
        warnings.append("MiniMax API Key未配置，LLM功能可能无法使用")

    # 严重错误：阻止启动
    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    # 警告：允许启动但功能受限
    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")

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
    print(f"Qloo Base URL: {active_settings.qloo_api_base_url}")

    llm_config = active_settings.get_llm_config()
    print(f"LLM API Key: {'已配置' if llm_config['api_key'] else '未配置'}")
    print(f"LLM Base URL: {llm_config['base_url']}")
    print(f"LLM Model: {llm_config['model']}")
    print(f"日志级别: {active_settings.log_level}")
