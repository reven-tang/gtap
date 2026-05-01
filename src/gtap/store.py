"""
数据仓库模块 - DuckDB 本地存储

实现股票数据的本地持久化，解决：
1. 第三方数据源清理早期数据 → 本地永久保存
2. 大跨度回测重复拉取 → 本地秒级查询
3. 增量更新 → 只拉缺失区间

架构:
    get_data_smart() → 查本地 → 有 → 直接返回
                                → 缺 → API补缺口 → 写本地 → 返回
"""

from pathlib import Path
from typing import Optional, List, Tuple
from datetime import date, timedelta
import logging

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "gtap_store.db"


class DataStore:
    """
    本地数据仓库，基于 DuckDB 列式存储。

    自动管理表创建、增量写入、缺口查询。
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """获取连接（懒加载，用完需手动 close 或用 context manager）"""
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
            self._ensure_tables()
        return self._conn

    def _ensure_tables(self) -> None:
        """确保表结构存在"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                code      VARCHAR NOT NULL,
                date      DATE    NOT NULL,
                open      DOUBLE,
                high      DOUBLE,
                low       DOUBLE,
                close     DOUBLE,
                volume    DOUBLE,
                amount    DOUBLE,
                adjustflag VARCHAR,
                PRIMARY KEY (code, date)
            )
        """)
        # 索引加速按代码+日期范围查询
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_code_date
            ON stock_daily(code, date)
        """)
        # 元数据表：记录数据更新时间
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_meta (
                code         VARCHAR PRIMARY KEY,
                first_date   DATE,
                last_date    DATE,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # ===== 写入 =====

    def store_kline(
        self,
        code: str,
        df: pd.DataFrame,
        adjustflag: str = "3",
    ) -> int:
        """
        将 K 线数据写入本地仓库。

        Args:
            code: 股票代码（标准化后，如 "sh.601398"）
            df: K线 DataFrame，需包含 open/high/low/close 列
            adjustflag: 复权标记

        Returns:
            实际插入的行数
        """
        if df.empty:
            return 0

        # 准备写入数据
        write_df = df.copy()
        write_df["code"] = code
        write_df["adjustflag"] = adjustflag

        # 确保 date 列存在
        if "date" not in write_df.columns:
            if isinstance(write_df.index, pd.DatetimeIndex):
                write_df["date"] = write_df.index
            else:
                raise ValueError("DataFrame 必须有 'date' 列或 DatetimeIndex")

        # 需要的列
        needed = ["code", "date", "open", "high", "low", "close", "volume", "amount", "adjustflag"]
        for col in needed:
            if col not in write_df.columns:
                write_df[col] = None

        insert_df = write_df[needed].copy()
        insert_df["date"] = pd.to_datetime(insert_df["date"]).dt.date

        # 用 DuckDB INSERT OR IGNORE 处理重复
        self.conn.register("_insert_df", insert_df)
        result = self.conn.execute("""
            INSERT OR IGNORE INTO stock_daily
            SELECT code, date, open, high, low, close, volume, amount, adjustflag
            FROM _insert_df
        """)
        self.conn.unregister("_insert_df")

        # 更新元数据
        first_d = insert_df["date"].min()
        last_d = insert_df["date"].max()
        self.conn.execute("""
            INSERT INTO stock_meta (code, first_date, last_date)
            VALUES (?, ?, ?)
            ON CONFLICT (code) DO UPDATE SET
                first_date = LEAST(stock_meta.first_date, EXCLUDED.first_date),
                last_date  = GREATEST(stock_meta.last_date, EXCLUDED.last_date),
                updated_at = now()
        """, [code, first_d, last_d])

        return insert_df.shape[0]

    # ===== 查询 =====

    def get_kline(
        self,
        code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        从本地仓库读取 K 线数据。

        Returns:
            DataFrame，列为 date/open/high/low/close/volume/amount
            日期为索引。如果本地无数据则返回空 DataFrame。
        """
        df = self.conn.execute("""
            SELECT date, open, high, low, close, volume, amount
            FROM stock_daily
            WHERE code = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """, [code, start_date, end_date]).df()

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

        return df

    def get_coverage(self, code: str) -> Tuple[Optional[date], Optional[date]]:
        """
        查询某股票在本地仓库的日期范围。

        Returns:
            (first_date, last_date) 或 (None, None)
        """
        row = self.conn.execute(
            "SELECT first_date, last_date FROM stock_meta WHERE code = ?",
            [code]
        ).fetchone()
        if row and row[0]:
            return row[0], row[1]
        return None, None

    def find_gaps(
        self,
        code: str,
        start_date: str,
        end_date: str,
    ) -> List[Tuple[str, str]]:
        """找出本地仓库中缺失的日期区间。

        策略：
        1. 先基于 stock_meta 判断整体覆盖范围
        2. 然后检查实际数据的连续性（中间空洞检测）
        3. 如果 meta 不覆盖请求范围，或中间有空洞，返回缺口
        """
        # 查出本地实际数据
        local_df = self.get_kline(code, start_date, end_date)

        if local_df.empty:
            return [(start_date, end_date)]  # 完全缺失

        # 检查覆盖度：数据范围是否覆盖请求范围
        local_start = local_df.index[0].strftime("%Y-%m-%d")
        local_end = local_df.index[-1].strftime("%Y-%m-%d")

        gaps = []

        # 前端缺失
        if local_start > start_date:
            gaps.append((start_date, local_start))

        # 后端缺失
        if local_end < end_date:
            gaps.append((local_end, end_date))

        # 中间空洞检测：连续交易日间隔 > 5 天可能有缺失
        dates = local_df.index
        for i in range(1, len(dates)):
            gap_days = (dates[i] - dates[i-1]).days
            # 10天以上的间隔才是数据缺失
            # 中国最长假期春节约9天+周末=10-11天
            # 正常周末2-3天，清明/劳动节/端午4-5天
            if gap_days > 12:
                # 这是中间空洞
                gap_start = dates[i-1].strftime("%Y-%m-%d")
                gap_end = dates[i].strftime("%Y-%m-%d")
                # 检查是否已被前端/后端缺口覆盖
                already_covered = False
                for gs, ge in gaps:
                    if gap_start >= gs and gap_end <= ge:
                        already_covered = True
                        break
                if not already_covered:
                    gaps.append((gap_start, gap_end))

        return gaps

    # ===== 智能获取（核心 API）=====

    def get_data_smart(
        self,
        code: str,
        start_date: str,
        end_date: str,
        fetch_fn,  # callable: (code, start, end) -> pd.DataFrame
        progress_callback=None,  # callable: (msg, pct) -> None
    ) -> pd.DataFrame:
        """
        智能获取数据：先查本地，缺失部分从 API 补充。

        Args:
            code: 标准化股票代码
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            fetch_fn: 远程获取函数，签名 (code, start, end) -> pd.DataFrame
            progress_callback: 进度回调 (message, percentage)

        Returns:
            完整的 K 线 DataFrame（日期为索引）
        """
        # 1. 查出本地已有数据
        if progress_callback:
            progress_callback("查询本地数据仓库...", 5)

        local_df = self.get_kline(code, start_date, end_date)

        # 2. 找缺口
        gaps = self.find_gaps(code, start_date, end_date)

        if not gaps:
            # 本地全量覆盖
            if progress_callback:
                progress_callback("✓ 全部数据来自本地仓库 (0 API调用)", 100)
            return local_df

        # 3. 补缺口
        fetched_dfs = [local_df] if not local_df.empty else []
        total_gaps = len(gaps)

        for i, (gap_s, gap_e) in enumerate(gaps):
            pct = 10 + int(80 * (i + 1) / total_gaps)
            if progress_callback:
                progress_callback(
                    f"从API拉取 {gap_s} ~ {gap_e} ({i+1}/{total_gaps})",
                    pct
                )

            try:
                gap_df = fetch_fn(code, gap_s, gap_e)
                if not gap_df.empty:
                    self.store_kline(code, gap_df)
                    fetched_dfs.append(gap_df)
            except Exception as e:
                logger.warning(f"获取 {code} {gap_s}~{gap_e} 失败: {e}")
                # 继续拉其他缺口，不中断

        # 4. 合并结果
        if not fetched_dfs:
            return pd.DataFrame()

        result = pd.concat(fetched_dfs)
        result = result[~result.index.duplicated(keep="last")]
        result.sort_index(inplace=True)

        # 裁剪到请求范围
        mask = (result.index >= start_date) & (result.index <= end_date)
        result = result[mask]

        if progress_callback:
            progress_callback(f"✓ 本地{len(local_df)}行 + 远程{len([d for d in fetched_dfs if d is not local_df] )}行", 100)

        return result

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局单例
_store: Optional[DataStore] = None


def get_store(db_path: str | Path | None = None) -> DataStore:
    """获取 DataStore 实例（每次新建，避免连接泄漏）"""
    return DataStore(db_path)
