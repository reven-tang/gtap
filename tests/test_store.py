"""
数据仓库模块测试 - DuckDB 本地存储
"""
import pytest
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import tempfile

from src.gtap.store import DataStore, get_store


def create_test_data(start: str, end: str) -> pd.DataFrame:
    """创建测试 K 线数据"""
    dates = pd.date_range(start=start, end=end, freq="B")
    n = len(dates)
    return pd.DataFrame({
        "open":  [10.0 + i * 0.1 for i in range(n)],
        "high":  [10.5 + i * 0.1 for i in range(n)],
        "low":   [9.5 + i * 0.1 for i in range(n)],
        "close": [10.2 + i * 0.1 for i in range(n)],
        "volume": [10000 + i * 100 for i in range(n)],
        "amount": [102000 + i * 1000 for i in range(n)],
    }, index=dates)


class TestDataStore:
    """测试 DataStore 核心功能"""

    def setup_method(self):
        """每个测试使用独立的临时数据库"""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "test_store.db"
        self.store = DataStore(self.db_path)

    def teardown_method(self):
        self.store.close()

    # ===== 写入测试 =====

    def test_store_and_get_basic(self):
        """基本写入和读取"""
        df = create_test_data("2024-01-01", "2024-01-31")
        count = self.store.store_kline("sh.601398", df)
        assert count > 0

        result = self.store.get_kline("sh.601398", "2024-01-01", "2024-01-31")
        assert len(result) == len(df)
        assert result.iloc[0]["close"] == df.iloc[0]["close"]

    def test_store_empty_df(self):
        """空 DataFrame 写入返回 0"""
        count = self.store.store_kline("sh.601398", pd.DataFrame())
        assert count == 0

    def test_store_no_overwrite(self):
        """重复写入不覆盖（INSERT OR IGNORE）"""
        df1 = create_test_data("2024-01-01", "2024-01-15")
        self.store.store_kline("sh.601398", df1)

        # 用不同数据写入同日期范围
        df2 = df1.copy()
        df2["close"] = df2["close"] * 2
        count2 = self.store.store_kline("sh.601398", df2)

        # 已经存在的日期被忽略
        result = self.store.get_kline("sh.601398", "2024-01-01", "2024-01-15")
        assert result.iloc[0]["close"] == df1.iloc[0]["close"]  # 原始值

    def test_store_updates_meta(self):
        """写入后元数据更新"""
        df = create_test_data("2024-01-01", "2024-01-31")
        self.store.store_kline("sh.601398", df)

        first, last = self.store.get_coverage("sh.601398")
        assert first == date(2024, 1, 1)
        assert last == date(2024, 1, 31)

    def test_store_expands_range(self):
        """追加数据扩展日期范围"""
        df1 = create_test_data("2024-01-01", "2024-01-15")
        self.store.store_kline("sh.601398", df1)

        df2 = create_test_data("2024-01-16", "2024-01-31")
        self.store.store_kline("sh.601398", df2)

        first, last = self.store.get_coverage("sh.601398")
        assert first == date(2024, 1, 1)
        assert last == date(2024, 1, 31)

    # ===== 查询测试 =====

    def test_get_empty_result(self):
        """查询不存在的代码返回空 DataFrame"""
        result = self.store.get_kline("unknown", "2024-01-01", "2024-01-31")
        assert result.empty

    def test_get_date_range(self):
        """日期范围筛选正确"""
        df = create_test_data("2024-01-01", "2024-03-31")
        self.store.store_kline("sh.601398", df)

        result = self.store.get_kline("sh.601398", "2024-02-01", "2024-02-29")
        assert len(result) > 0
        assert result.index.min() >= pd.Timestamp("2024-02-01")
        assert result.index.max() <= pd.Timestamp("2024-02-29")

    def test_get_coverage_empty(self):
        """未存储代码返回 None"""
        first, last = self.store.get_coverage("no_code")
        assert first is None
        assert last is None

    # ===== 缺口检测 =====

    def test_find_gaps_full_missing(self):
        """完全缺失 → 返回整个区间"""
        gaps = self.store.find_gaps("sh.601398", "2024-01-01", "2024-01-31")
        assert len(gaps) == 1
        assert gaps[0] == ("2024-01-01", "2024-01-31")

    def test_find_gaps_no_gaps(self):
        """全覆盖 → 返回空"""
        df = create_test_data("2024-01-01", "2024-01-31")
        self.store.store_kline("sh.601398", df)
        gaps = self.store.find_gaps("sh.601398", "2024-01-01", "2024-01-31")
        assert len(gaps) == 0

    def test_find_gaps_partial(self):
        """部分覆盖 → 返回缺口"""
        df1 = create_test_data("2024-01-01", "2024-01-15")
        self.store.store_kline("sh.601398", df1)

        gaps = self.store.find_gaps("sh.601398", "2024-01-01", "2024-01-31")
        # 应该有一个缺口: 01-16 ~ 01-31
        assert len(gaps) >= 1
        assert gaps[-1] == ("2024-01-16", "2024-01-31")

    # ===== 智能获取 =====

    def test_smart_fetch_all_local(self):
        """全部在本地 → 0 API调用"""
        df = create_test_data("2024-01-01", "2024-01-31")
        self.store.store_kline("sh.601398", df)

        api_calls = []

        def mock_fetch(code, start, end):
            api_calls.append((start, end))
            return create_test_data(start, end)

        result = self.store.get_data_smart(
            "sh.601398", "2024-01-01", "2024-01-31",
            fetch_fn=mock_fetch,
        )
        assert len(result) > 0
        assert len(api_calls) == 0  # 没有 API 调用

    def test_smart_fetch_all_remote(self):
        """全部缺失 → API 全量拉取 + 写入本地"""
        api_calls = []

        def mock_fetch(code, start, end):
            api_calls.append((start, end))
            return create_test_data(start, end)

        result = self.store.get_data_smart(
            "sh.601398", "2024-01-01", "2024-01-07",
            fetch_fn=mock_fetch,
        )
        assert len(result) > 0
        assert len(api_calls) == 1  # 一次 API 调用
        # 验证已写入本地
        local = self.store.get_kline("sh.601398", "2024-01-01", "2024-01-07")
        assert len(local) > 0

    def test_smart_fetch_partial_gap(self):
        """部分覆盖 → 只补缺口"""
        df = create_test_data("2024-01-01", "2024-01-15")
        self.store.store_kline("sh.601398", df)

        api_calls = []

        def mock_fetch(code, start, end):
            api_calls.append((start, end))
            return create_test_data(start, end)

        result = self.store.get_data_smart(
            "sh.601398", "2024-01-01", "2024-01-31",
            fetch_fn=mock_fetch,
        )
        assert len(result) > 0
        assert len(api_calls) == 1  # 只补一个缺口
        # 第二次调用：全部在本地
        api_calls.clear()
        result2 = self.store.get_data_smart(
            "sh.601398", "2024-01-01", "2024-01-31",
            fetch_fn=mock_fetch,
        )
        assert len(api_calls) == 0

    def test_smart_fetch_progress_called(self):
        """进度回调被正确调用"""
        progress = []

        def mock_fetch(code, start, end):
            return create_test_data(start, end)

        self.store.get_data_smart(
            "sh.601398", "2024-01-01", "2024-01-10",
            fetch_fn=mock_fetch,
            progress_callback=lambda msg, pct: progress.append((msg, pct)),
        )
        assert len(progress) >= 2  # 至少开始和结束
        assert progress[-1][1] == 100  # 最后进度 100%

    def test_smart_fetch_result_no_duplicates(self):
        """结果没有重复日期"""
        df = create_test_data("2024-01-01", "2024-01-15")
        self.store.store_kline("sh.601398", df)

        def mock_fetch(code, start, end):
            return create_test_data(start, end)

        result = self.store.get_data_smart(
            "sh.601398", "2024-01-01", "2024-01-31",
            fetch_fn=mock_fetch,
        )
        assert not result.index.duplicated().any()


class TestAutoFrequency:
    """测试自动降采样"""

    def test_short_range(self):
        from src.gtap.data import auto_frequency
        assert auto_frequency("2024-01-01", "2024-01-15") == "5"

    def test_medium_range(self):
        from src.gtap.data import auto_frequency
        assert auto_frequency("2022-01-01", "2024-12-31") == "d"

    def test_long_range(self):
        from src.gtap.data import auto_frequency
        assert auto_frequency("2010-01-01", "2024-12-31") == "w"

    def test_fallback(self):
        from src.gtap.data import auto_frequency
        assert auto_frequency("bad", "date") == "d"
