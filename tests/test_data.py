"""数据获取模块单元测试（骨架 + 关键逻辑验证）"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.gtap.data import get_stock_data, StockData
from src.gtap.exceptions import DataFetchError


class TestGetStockData:
    """测试数据获取逻辑"""

    @patch("src.gtap.data.bs")
    def test_get_stock_data_returns_correct_type(self, mock_bs):
        """测试返回 StockData NamedTuple 类型"""
        # 构造 mock 返回值
        mock_lg = MagicMock()
        mock_lg.error_code = "0"
        mock_lg.error_msg = ""

        mock_rs = MagicMock()
        mock_rs.error_code = "0"
        mock_rs.fields = ["date", "time", "code", "open", "high", "low", "close", "volume"]
        mock_rs.next.return_value = True
        mock_rs.get_row_data.return_value = [
            "2024-01-01", "09:35:00", "sh.601398", "5.0", "5.1", "4.9", "5.0", "1000"
        ]

        mock_bs.login.return_value = mock_lg
        mock_bs.query_history_k_data_plus.return_value = mock_rs
        mock_bs.query_dividend_data.return_value = mock_rs
        mock_bs.query_stock_basic.return_value = mock_rs

        # 其他查询返回空 DataFrame
        for query_name in [
            "query_profit_data", "query_operation_data", "query_growth_data",
            "query_balance_data", "query_cash_flow_data", "query_dupont_data",
            "query_performance_express_report", "query_forecast_report"
        ]:
            setattr(mock_bs, query_name, MagicMock(return_value=MagicMock(
                error_code="0",
                fields=[],
                next=MagicMock(return_value=False),
                get_row_data=MagicMock(return_value=[])
            )))

        mock_bs.logout.return_value = None

        result = get_stock_data("sh.601398", "2024-01-01", "2024-01-02", show_quarterly=False)

        assert isinstance(result, StockData)
        assert isinstance(result.kline, pd.DataFrame)

    def test_show_quarterly_false_returns_empty_dfs(self):
        """测试 show_quarterly=False 时空 DataFrame"""
        # 这个测试依赖真实的 baostock 连接，仅用于手动验证
        # 自动化测试需要完整 mock
        pytest.skip("需要完整 mock baostock 接口")

    def test_data_module_exports(self):
        """验证数据模块导出正确"""
        from src.gtap import data as data_module
        assert hasattr(data_module, "get_stock_data")
        assert hasattr(data_module, "StockData")
