GTAP: Grid Trading Analysis Platform
====================================

**版本**: 1.0.0  
**状态**: 生产就绪

GTAP 是一个专业的股票网格交易回测与分析平台，基于香农信息理论设计，支持多资产组合、ATR 动态止损、再平衡策略。

.. image:: https://img.shields.io/pypi/v/gtap.svg
   :target: https://pypi.org/project/gtap/
   :alt: PyPI Version

.. image:: https://img.shields.io/badge/License-MIT-green.svg
   :target: LICENSE
   :alt: License

.. image:: https://img.shields.io/badge/Python-3.9%2B-blue
   :target: https://pypi.org/project/gtap/
   :alt: Python Version

快速开始
--------

安装
^^^^

.. code-block:: bash

   # 基础安装
   pip install gtap

   # 包含文档和开发依赖
   pip install "gtap[docs,dev]"

   # Docker 一键运行
   docker run -p 8501:8501 ghcr.io/yourname/gtap:1.0.0

运行 Streamlit 界面
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   streamlit run gtap/app.py

浏览器访问 http://localhost:8501 即可使用。

模块化 API
^^^^^^^^^^

.. code-block:: python

   from gtap import GridTradingConfig, grid_trading, calculate_metrics

   config = GridTradingConfig(
       symbol="sh.600519",  # 贵州茅台
       start_date="2023-01-01",
       end_date="2024-01-01",
       grid_count=10,
       grid_type="arithmetic"
   )
   result = grid_trading(config)
   print(calculate_metrics(result))

核心特性
--------

✅ **网格交易引擎**：算术/等比网格，支持 ATR 动态止损止盈  
✅ **策略抽象**：网格策略 + 再平衡策略 + Parrondo 悖论混合  
✅ **多资产组合**：跨资产相关性分析 + 组合再平衡  
✅ **香农理论对齐**：波动拖累实时计算 + 凯利仓位推荐  
✅ **Streamlit UI**：可视化配置 + 实时图表 + 指标面板  
✅ **完整测试**：141+ 测试，覆盖率 ≥ 90%

文档导航
--------

.. toctree::
   :maxdepth: 2
   :caption: 用户指南

   guide/installation
   guide/configuration
   guide/usage
   guide/parameters
   guide/troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: 教程

   tutorial/basic_grid
   tutorial/atr_stop
   tutorial/portfolio

.. toctree::
   :maxdepth: 2
   :caption: API 参考

   api/config
   api/grid
   api/metrics
   api/data
   api/plot
   api/fees
   api/atr
   api/theory
   api/providers
   api/exceptions

.. toctree::
   :maxdepth: 1
   :caption: 项目

   changelog
   contributing

项目信息
--------

- **许可证**: MIT
- **Python**: 3.9+
- **维护**: reven-tang + OpenClaw AI
- **问题追踪**: GitHub Issues
- **讨论**: GitHub Discussions

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
