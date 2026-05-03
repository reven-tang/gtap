# GTAP 用户指南

## 1. 安装

### pip 安装
```bash
pip install gtap
```

### 源码安装
```bash
git clone https://github.com/yourname/gtap.git
cd gtap
pip install -e ".[dev]"
```

### Docker 运行
```bash
docker run -p 8501:8501 ghcr.io/yourname/gtap:1.0.0
```

---

## 2. 配置

### 基本配置
```python
from gtap import GridTradingConfig

config = GridTradingConfig(
    symbol="sh.600519",      # 股票代码
    start_date="2023-01-01",
    end_date="2024-01-01",
    grid_count=10,           # 网格数量
    grid_type="arithmetic"   # 算术/等比
)
```

### 高级配置
参考 `pyproject.toml` 和 `docs/api/config.md`。

---

## 3. 使用

### Streamlit 界面
```bash
streamlit run gtap/app.py
```

### 模块化 API
```python
from gtap import grid_trading, calculate_metrics

result = grid_trading(config)
metrics = calculate_metrics(result)
```

---

## 4. 参数说明

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| symbol | str | - | 股票代码（baostock 格式） |
| start_date | str | - | 开始日期 |
| end_date | str | - | 结束日期 |
| grid_count | int | 10 | 网格层数 |
| grid_type | str | "arithmetic" | 网格类型 |

完整参数见 `src/gtap/config.py`。

---

## 5. 故障排除

### 数据源错误
```
DataFetchError: 请先安装 yfinance 或 akshare
```
**解决**: `pip install yfinance akshare`

### 回测时间过长
**解决**: 缩小日期范围，减少网格数，启用 `@st.cache_data`

### 图表不显示
**解决**: 检查 matplotlib 版本，升级到 3.10+

---

更多帮助请参考 `docs/tutorial/` 或提交 GitHub Issue。
