"""
自定义异常类 - GTAP 网格交易回测平台

用于在数据获取、回测、费用计算等环节提供明确的异常类型，
便于上层调用者进行精确的错误处理。
"""

__all__ = [
    "DataFetchError",
    "GridTradingError",
    "ConfigError",
    "MetricsError",
    "PlotError",
]


from typing import Optional


class DataFetchError(Exception):
    """数据获取失败异常"""
    def __init__(self, message: str, code: str = "", original_error: Optional[Exception] = None):
        super().__init__(message)
        self.code = code
        self.original_error = original_error


class GridTradingError(Exception):
    """网格交易回测异常"""
    pass


class ConfigError(Exception):
    """配置错误异常"""
    pass


class MetricsError(Exception):
    """绩效指标计算异常"""
    pass


class PlotError(Exception):
    """图表绘制异常"""
    pass
