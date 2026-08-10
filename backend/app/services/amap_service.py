"""高德地图MCP服务 - 使用 langchain-mcp-adapters 连接 amap-mcp-server"""

import os
import sys
from contextlib import AsyncExitStack
from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.sessions import StdioConnection, create_session
from langchain_mcp_adapters.tools import load_mcp_tools

from ..config import get_settings

_mcp_tools: Optional[List[BaseTool]] = None
_stack: Optional[AsyncExitStack] = None


async def get_mcp_tools() -> List[BaseTool]:
    """获取高德地图 MCP 工具（单例，延迟初始化）"""
    global _mcp_tools, _stack

    if _mcp_tools is not None:
        return _mcp_tools

    settings = get_settings()
    if not settings.amap_api_key:
        raise ValueError("高德地图API Key未配置，无法启动MCP服务")

    env = os.environ.copy()
    env["AMAP_MAPS_API_KEY"] = settings.amap_api_key
    env["PYTHONUNBUFFERED"] = "1"

    connection = StdioConnection(
        transport="stdio",
        command=sys.executable,
        args=["-m", "amap_mcp_server"],
        env=env,
        cwd=None,
    )

    _stack = AsyncExitStack()
    session = await _stack.enter_async_context(create_session(connection))
    await session.initialize()
    _mcp_tools = await load_mcp_tools(session)

    print("✅ 高德地图MCP工具初始化成功")
    print(f"   工具数量: {len(_mcp_tools)}")

    return _mcp_tools


class AmapService:
    """高德地图服务封装类"""

    def __init__(self):
        self._tools: Optional[List[BaseTool]] = None

    async def get_tools(self) -> List[BaseTool]:
        """获取 MCP 工具列表"""
        if self._tools is None:
            self._tools = await get_mcp_tools()
        return self._tools


_amap_service: Optional[AmapService] = None


def get_amap_service() -> AmapService:
    """获取 AmapService 单例"""
    global _amap_service

    if _amap_service is None:
        _amap_service = AmapService()

    return _amap_service
