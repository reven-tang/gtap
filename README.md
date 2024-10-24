# 股票分析网站

这是一个使用Streamlit构建的简单股票分析网站。

## 功能

- 输入股票代码获取历史交易数据
- 显示指定日期范围内的股票交易信息
- 绘制K线图展示股票价格走势
- 计算并显示基本统计信息（平均收盘价、最高价、最低价、总成交量）
- 计算并显示技术指标（MA5、MA10、MA20）
- 提供股票相关新闻链接
- 显示股票基本信息和除权除息数据
- 可选显示季频财务数据（盈利能力、营运能力、成长能力等）
- 执行网格交易回测，并显示回测结果和绩效指标

## 安装

1. 克隆此仓库:
   ```bash
   git clone https://github.com/reven-tang/gtap.git
   ```

2. 进入项目目录:
   ```bash
   cd stock-analysis-website
   ```

3. 安装所需的Python包:
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. 运行Streamlit应用:
   ```bash
   streamlit run gtap.py
   ```

2. 在浏览器中打开显示的URL（通常是 http://localhost:8501）

3. 在左侧边栏输入股票代码（例如：sh.601398）

4. 选择开始日期和结束日期

5. 设置网格交易参数（网格上限、下限、数量等）

6. 设置交易费用参数（佣金费率、过户费费率、印花税费率）

7. 选择是否显示季频财务数据

8. 点击"运行网格交易回测"按钮查看结果

## 主要依赖

- Python 3.7+
- Streamlit==1.39.0
- Pandas==2.2.3
- Plotly==5.24.1
- baostock==0.8.9
- mplfinance==0.12.10b0
- numpy==1.26.4

## 注意事项

- 确保您有稳定的网络连接以获取股票数据
- 股票代码格式应为"交易所代码.股票代码"，例如：sh.601398（上海）或sz.000001（深圳）
- 网格交易回测结果仅供参考，不构成投资建议
- 使用季频财务数据功能可能会增加数据加载时间

## 贡献

欢迎提交问题和拉取请求。对于重大更改，请先开issue讨论您想要更改的内容。

## 参考链接

- http://defiplot.com/blog/grid-trading-with-python/
- http://baostock.com/baostock/index.php/Python_API%E6%96%87%E6%A1%A3

## 许可

[MIT](https://choosealicense.com/licenses/mit/)
