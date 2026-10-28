"""Provider-neutral LLM service using an OpenAI-compatible endpoint."""

from typing import Optional
from langchain_openai import ChatOpenAI  # LangChain OpenAI兼容接口
from langchain_core.language_models import BaseChatModel  # LangChain聊天模型基类
from ..config import get_settings  # 获取应用配置

# 全局LLM单例实例
_global_llm: Optional[BaseChatModel] = None


def get_llm() -> BaseChatModel:
    """获取LLM实例（单例模式，延迟初始化）

    首次调用时根据通用 LLM 配置创建 ChatOpenAI 实例，
    后续调用直接返回缓存的实例。

    Returns:
        LangChain ChatOpenAI 实例

    Raises:
        ValueError: 当API Key未配置时抛出
    """
    global _global_llm

    if _global_llm is None:
        settings = get_settings()
        llm_config = settings.get_llm_config()

        # 验证API Key
        if not llm_config["api_key"]:
            raise ValueError("LLM API Key未配置，请在.env文件中设置LLM_API_KEY")

        # ChatOpenAI 在这里是协议适配器，不代表绑定 OpenAI 厂商。
        _global_llm = ChatOpenAI(
            model=llm_config["model"],
            base_url=llm_config["base_url"],
            api_key=llm_config["api_key"],
            temperature=1.0,  # 创造性参数，越高越随机
            max_tokens=None,  # 不限制输出长度
            timeout=600,  # 10分钟超时（Planner Agent可能很慢）
            max_retries=3,  # 最多重试3次
        )

        print("✅ LLM服务初始化成功")
        print("   Base URL: 已配置")
        print(f"   Model: {llm_config['model']}")

    return _global_llm


def reset_llm():
    """重置LLM实例（用于测试或重新配置）

    将全局LLM实例置为None，下次调用get_llm()时会重新初始化。
    """
    global _global_llm
    _global_llm = None
