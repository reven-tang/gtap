"""
数据源提供商测试 - GTAP v0.4.0

测试数据源工厂、代码转换、频率映射等功能。
不依赖网络请求，仅测试本地逻辑。
"""

import pytest
from src.gtap.providers.factory import get_provider, available_providers
from src.gtap.providers.baostock_provider import BaoStockProvider
from src.gtap.providers.base import DataProvider
from src.gtap.exceptions import DataFetchError


class TestGetProvider:
    """数据源工厂测试"""

    def test_baostock_always_available(self):
        """baostock 应始终可用"""
        provider = get_provider("baostock")
        assert isinstance(provider, BaoStockProvider)
        assert isinstance(provider, DataProvider)

    def test_baostock_returns_provider_instance(self):
        """每次调用应返回新实例"""
        p1 = get_provider("baostock")
        p2 = get_provider("baostock")
        assert p1 is not p2  # 不同实例

    def test_unsupported_source_raises(self):
        """不支持的数据源应抛出异常"""
        with pytest.raises(DataFetchError) as exc_info:
            get_provider("invalid_source")
        assert "不支持的数据源" in str(exc_info.value)

    def test_available_providers_returns_list(self):
        """可用数据源列表应包含 baostock"""
        providers = available_providers()
        assert "baostock" in providers

    def test_yfinance_not_installed_raises(self):
        """yfinance 未安装时应抛出明确异常"""
        try:
            provider = get_provider("yfinance")
            # 如果 yfinance 已安装，应成功
            assert isinstance(provider, DataProvider)
        except DataFetchError as e:
            # 如果未安装，应有安装提示
            assert "pip install yfinance" in str(e)

    def test_akshare_not_installed_raises(self):
        """akshare 未安装时应抛出明确异常"""
        try:
            provider = get_provider("akshare")
            assert isinstance(provider, DataProvider)
        except DataFetchError as e:
            assert "pip install akshare" in str(e)


class TestBaoStockCodeNormalization:
    """BaoStock 代码标准化测试"""

    provider = BaoStockProvider()

    def test_sh_prefix_preserved(self):
        """sh. 前缀代码应保持不变"""
        assert self.provider.normalize_code("sh.601398") == "sh.601398"

    def test_sz_prefix_preserved(self):
        """sz. 前缀代码应保持不变"""
        assert self.provider.normalize_code("sz.000001") == "sz.000001"

    def test_pure_number_shanghai(self):
        """6 开头纯数字应添加 sh. 前缀"""
        assert self.provider.normalize_code("601398") == "sh.601398"

    def test_pure_number_shenzhen(self):
        """0 开头纯数字应添加 sz. 前缀"""
        assert self.provider.normalize_code("000001") == "sz.000001"

    def test_pure_number_3_start(self):
        """3 开头纯数字应添加 sz. 前缀"""
        assert self.provider.normalize_code("300001") == "sz.300001"

    def test_yfinance_ss_suffix(self):
        """yfinance .SS 后缀应转为 sh. 前缀"""
        assert self.provider.normalize_code("601398.SS") == "sh.601398"

    def test_yfinance_sz_suffix(self):
        """yfinance .SZ 后缀应转为 sz. 前缀"""
        assert self.provider.normalize_code("000001.SZ") == "sz.000001"

    def test_supported_markets(self):
        """BaoStock 应支持 A 股市场"""
        markets = self.provider.supported_markets()
        assert "A股-沪市" in markets
        assert "A股-深市" in markets

    def test_supported_frequencies(self):
        """BaoStock 应支持所有标准频率"""
        freqs = self.provider._supported_frequencies()
        assert "5" in freqs
        assert "d" in freqs
        assert "w" in freqs


class TestDataProviderInterface:
    """DataProvider 抽象接口测试"""

    def test_cannot_instantiate_base(self):
        """不能直接实例化 DataProvider 基类"""
        with pytest.raises(TypeError):
            DataProvider()

    def test_baostock_is_provider(self):
        """BaoStockProvider 应继承 DataProvider"""
        assert issubclass(BaoStockProvider, DataProvider)

    def test_baostock_has_required_methods(self):
        """BaoStockProvider 应实现所有必要方法"""
        provider = BaoStockProvider()
        assert hasattr(provider, "fetch_kline")
        assert hasattr(provider, "fetch_dividend")
        assert hasattr(provider, "fetch_basic")
        assert hasattr(provider, "supported_markets")
        assert hasattr(provider, "normalize_code")
        assert hasattr(provider, "supports_frequency")

    def test_supports_frequency_valid(self):
        """支持的有效频率应返回 True"""
        provider = BaoStockProvider()
        assert provider.supports_frequency("d") is True
        assert provider.supports_frequency("5") is True

    def test_supports_frequency_invalid(self):
        """无效频率应返回 False"""
        provider = BaoStockProvider()
        assert provider.supports_frequency("1") is False
        assert provider.supports_frequency("2h") is False