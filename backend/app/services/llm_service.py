"""LLM服务模块 - 使用LangChain连接MiniMax大模型"""

from typing import Optional
from langchain_openai import ChatOpenAI  # LangChain OpenAI兼容接口
from langchain_core.language_models import BaseChatModel  # LangChain聊天模型基类
from ..config import get_settings  # 获取应用配置

# 全局LLM单例实例
_global_llm: Optional[BaseChatModel] = None


def get_llm() -> BaseChatModel:
    """获取LLM实例（单例模式，延迟初始化）

    首次调用时根据配置创建ChatOpenAI实例，
    后续调用直接返回缓存的实例。

    Returns:
        LangChain ChatOpenAI实例（配置为MiniMax）

    Raises:
        ValueError: 当API Key未配置时抛出
    """
    global _global_llm

    if _global_llm is None:
        settings = get_settings()
        llm_config = settings.get_llm_config()

        # 验证API Key
        if not llm_config["api_key"]:
            raise ValueError("MiniMax API Key未配置，请在.env文件中设置MINIMAX_API_KEY")

        # 创建LangChain ChatOpenAI实例
        # 由于MiniMax API兼容OpenAI格式，可直接使用ChatOpenAI
        _global_llm = ChatOpenAI(
            model=llm_config["model"],
            base_url=llm_config["base_url"],
            api_key=llm_config["api_key"],
            temperature=1.0,  # 创造性参数，越高越随机
            max_tokens=None,  # 不限制输出长度
            timeout=600,  # 10分钟超时（Planner Agent可能很慢）
            max_retries=3,  # 最多重试3次
        )

        print(f"✅ LLM服务初始化成功")
        print(f"   Base URL: {llm_config['base_url']}")
        print(f"   Model: {llm_config['model']}")

    return _global_llm


def reset_llm():
    """重置LLM实例（用于测试或重新配置）

    将全局LLM实例置为None，下次调用get_llm()时会重新初始化。
    """
    global _global_llm
    _global_llm = None
