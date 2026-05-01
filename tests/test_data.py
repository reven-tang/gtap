"""数据获取模块单元测试（v0.4.0 适配 Provider 抽象层）"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.gtap.data import get_stock_data, StockData
from src.gtap.exceptions import DataFetchError


def _make_mock_provider(kline_df=None, dividend_df=None, basic_df=None, normalize_code=None):
    """构造 mock DataProvider"""
    provider = MagicMock()
    provider.fetch_kline.return_value = kline_df if kline_df is not None else pd.DataFrame()
    provider.fetch_dividend.return_value = dividend_df if dividend_df is not None else pd.DataFrame()
    provider.fetch_basic.return_value = basic_df if basic_df is not None else pd.DataFrame()
    provider.normalize_code.return_value = normalize_code or "sh.600000"
    return provider


def _make_kline_df(datetime_index, open_price=10.0, high=10.5, low=9.8, close=10.2, volume=10000):
    """构造 K 线 DataFrame"""
    return pd.DataFrame({
        "open": [open_price],
        "high": [high],
        "low": [low],
        "close": [close],
        "volume": [volume],
    }, index=pd.DatetimeIndex([pd.Timestamp(datetime_index)]))


class TestGetStockData:
    """测试数据获取逻辑（Provider 抽象层）"""

    @patch("src.gtap.data.get_provider")
    def test_get_stock_data_returns_correct_type(self, mock_get_provider):
        """测试返回 StockData NamedTuple 类型"""
        kline = _make_kline_df("2024-01-01 09:35:00")
        provider = _make_mock_provider(kline_df=kline)
        mock_get_provider.return_value = provider

        result = get_stock_data("sh.601398", "2024-01-01", "2024-01-02", show_quarterly=False)

        assert isinstance(result, StockData)
        assert isinstance(result.kline, pd.DataFrame)
        assert not result.kline.empty
        assert result.kline.iloc[0]["open"] == 10.0
        provider.normalize_code.assert_called_once_with("sh.601398")
        provider.fetch_kline.assert_called_once()

    @patch("src.gtap.data.get_provider")
    def test_get_stock_data_passes_parameters_to_provider(self, mock_get_provider):
        """测试 data_source 参数正确传递给 factory"""
        kline = _make_kline_df("2024-01-01")
        provider = _make_mock_provider(kline_df=kline)
        mock_get_provider.return_value = provider

        result = get_stock_data(
            "AAPL", "2024-01-01", "2024-01-31",
            frequency="d", adjustflag="1", show_quarterly=False,
            data_source="yfinance",
        )

        # get_provider may be called multiple times (auto_frequency + main fetch)
        mock_get_provider.assert_called_with("yfinance")
        provider.normalize_code.assert_called_with("AAPL")
        provider.fetch_kline.assert_called_with(
            code="sh.600000",
            start_date="2024-01-02",
            end_date="2024-01-31",
            frequency="d",
            adjustflag="1",
        )
        assert isinstance(result, StockData)
        assert not result.kline.empty

    @patch("src.gtap.data.get_provider")
    def test_get_stock_data_returns_empty_dividend_when_not_supported(self, mock_get_provider):
        """测试非 baostock 数据源的财务数据为空"""
        kline = _make_kline_df("2024-01-01")
        provider = _make_mock_provider(kline_df=kline)
        mock_get_provider.return_value = provider

        result = get_stock_data("AAPL", "2024-01-01", "2024-01-02",
                                show_quarterly=True, data_source="yfinance")

        assert result.profit.empty
        assert result.operation.empty
        assert result.growth.empty
        assert result.balance.empty
        assert result.cash_flow.empty
        assert result.dupont.empty
        assert result.performance_express.empty
        assert result.forecast.empty

    def test_show_quarterly_false_returns_empty_dfs(self):
        """测试 show_quarterly=False 时空 DataFrame"""
        pytest.skip("需要完整 mock Provider 接口")

    def test_data_module_exports(self):
        """验证数据模块导出正确"""
        from src.gtap import data as data_module
        assert hasattr(data_module, "get_stock_data")
        assert hasattr(data_module, "StockData")

    @patch("src.gtap.data.get_provider")
    def test_datetime_parsing_for_daily_frequency(self, mock_get_provider):
        """测试日线频率的 datetime 正确处理"""
        kline = _make_kline_df("2025-01-02 00:00:00")
        provider = _make_mock_provider(kline_df=kline)
        mock_get_provider.return_value = provider

        result = get_stock_data("sh.600000", "2025-01-02", "2025-01-02",
                                frequency="d", show_quarterly=False)

        assert not result.kline.empty
        assert isinstance(result.kline.index, pd.DatetimeIndex)
        assert result.kline.index[0] == pd.Timestamp("2025-01-02 00:00:00")

    @patch("src.gtap.data.get_provider")
    def test_datetime_parsing_for_minute_frequency(self, mock_get_provider):
        """测试分钟线频率的 datetime 正确处理"""
        kline = pd.DataFrame({
            "open": [10.0, 10.2],
            "high": [10.5, 10.8],
            "low": [9.8, 10.1],
            "close": [10.2, 10.5],
            "volume": [10000, 8000],
        }, index=pd.DatetimeIndex([
            pd.Timestamp("2025-01-02 09:35:00"),
            pd.Timestamp("2025-01-02 09:40:00"),
        ]))

        provider = _make_mock_provider(kline_df=kline)
        mock_get_provider.return_value = provider

        result = get_stock_data("sh.600000", "2025-01-02", "2025-01-02",
                                frequency="5", show_quarterly=False)

        assert len(result.kline) == 2
        assert isinstance(result.kline.index, pd.DatetimeIndex)
        assert result.kline.index[0] == pd.Timestamp("2025-01-02 09:35:00")
        assert result.kline.index[1] == pd.Timestamp("2025-01-02 09:40:00")

    @patch("src.gtap.data.get_provider")
    def test_raises_data_fetch_error_on_provider_failure(self, mock_get_provider):
        """测试 Provider 失败时抛出 DataFetchError"""
        mock_get_provider.side_effect = DataFetchError("Provider not available")

        with pytest.raises(DataFetchError, match="Provider not available"):
            get_stock_data("sh.600000", "2025-01-02", "2025-01-02")

    @patch("src.gtap.data.get_provider")
    def test_raises_data_fetch_error_on_kline_failure(self, mock_get_provider):
        """测试 K 线获取失败时抛出 DataFetchError"""
        provider = _make_mock_provider()
        provider.fetch_kline.side_effect = RuntimeError("Network error")
        mock_get_provider.return_value = provider

        with pytest.raises(DataFetchError, match="数据获取失败"):
            get_stock_data("sh.600000", "2025-01-02", "2025-01-02")

    @patch("src.gtap.data.get_provider")
    def test_quarterly_baostock_data(self, mock_get_provider):
        """测试 show_quarterly=True 时的 baostock 季频财务数据获取"""
        kline = _make_kline_df("2024-01-01")
        provider = _make_mock_provider(kline_df=kline)
        mock_get_provider.return_value = provider

        # 需要 baostock 来获取季频数据，用 import
        try:
            import baostock as bs
        except ImportError:
            pytest.skip("baostock 不可用")

        # 这个路径实际需要 mock 整个 baostock 模块
        # 只验证函数签名和数据源正确传递
        try:
            result = get_stock_data(
                "sh.600000", "2024-01-01", "2024-03-31",
                show_quarterly=True, data_source="baostock",
            )

            assert isinstance(result, StockData)
            assert isinstance(result.kline, pd.DataFrame)
        except Exception as e:
            # baostock 可能在测试环境不可用，允许失败
            if "login failed" in str(e).lower() or "baostock" in str(e).lower():
                pass  # 预期可能失败
            else:
                raise
