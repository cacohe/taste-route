"""Unsplash图片服务 - 提供景点图片搜索功能

使用Unsplash API根据关键词搜索相关图片。
Unsplash是一个免费的高质量图片平台。
"""

import requests  # 同步HTTP客户端
from typing import List, Optional
from ..config import get_settings  # 获取应用配置


class UnsplashService:
    """Unsplash图片服务类

    提供图片搜索和URL获取功能。
    注意：使用的是同步requests库，不适合高并发场景。
    """

    def __init__(self):
        """初始化服务，从配置读取API密钥"""
        settings = get_settings()
        self.access_key = settings.unsplash_access_key
        self.base_url = "https://api.unsplash.com"

    def search_photos(self, query: str, per_page: int = 5) -> List[dict]:
        """搜索图片

        Args:
            query: 搜索关键词，如 "Great Wall China"
            per_page: 返回结果数量，默认为5

        Returns:
            图片信息列表，每项包含 id, url, thumb, description, photographer
        """
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": self.access_key,
            }

            # 发送GET请求，10秒超时
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # HTTP错误时抛出异常

            data = response.json()
            results = data.get("results", [])

            # 提取图片URL和其他信息
            photos = []
            for photo in results:
                photos.append(
                    {
                        "id": photo.get("id"),
                        "url": photo.get("urls", {}).get("regular"),  # 中等尺寸图片
                        "thumb": photo.get("urls", {}).get("thumb"),  # 缩略图
                        "description": photo.get("description")
                        or photo.get("alt_description"),
                        "photographer": photo.get("user", {}).get("name"),
                    }
                )

            return photos

        except Exception as e:
            print(f"❌ Unsplash搜索失败: {str(e)}")
            return []

    def get_photo_url(self, query: str) -> Optional[str]:
        """获取单张图片URL

        便捷方法：搜索并返回第一张图片的URL。

        Args:
            query: 搜索关键词

        Returns:
            图片URL，未找到返回None
        """
        photos = self.search_photos(query, per_page=1)
        if photos:
            return photos[0].get("url")
        return None


# 全局服务实例（单例模式）
_unsplash_service = None


def get_unsplash_service() -> UnsplashService:
    """获取Unsplash服务实例（单例模式）

    Returns:
        UnsplashService实例
    """
    global _unsplash_service

    if _unsplash_service is None:
        _unsplash_service = UnsplashService()

    return _unsplash_service
