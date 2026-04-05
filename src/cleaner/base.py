"""清洗器抽象基类"""

from abc import ABC, abstractmethod


class BaseCleaner(ABC):
    """数据清洗器基类"""

    @abstractmethod
    def clean(self, data: dict) -> dict:
        """清洗单条 JD 数据，返回清洗后的 dict"""
