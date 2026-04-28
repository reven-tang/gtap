"""费用计算模块单元测试"""

import pytest
from src.gtap.fees import calculate_fees
from src.gtap.exceptions import ConfigError


class TestCalculateFees:
    """测试 calculate_fees 函数"""

    def test_buy_a_stock(self):
        """测试沪市买入费用"""
        commission, transfer, stamp, total = calculate_fees(
            amount=10000,
            is_buy=True,
            stock_code="sh.601398",
            commission_rate=0.0003,
            transfer_fee_rate=0.00001,
            stamp_duty_rate=0.001,
        )
        assert commission == 5.0  # 最低 5 元
        assert transfer == 0.1  # 10000 * 0.00001
        assert stamp == 0.0  # 买入无印花税
        assert total == pytest.approx(5.1)

    def test_sell_a_stock(self):
        """测试沪市卖出费用"""
        commission, transfer, stamp, total = calculate_fees(
            amount=10000,
            is_buy=False,
            stock_code="sh.601398",
            commission_rate=0.0003,
            transfer_fee_rate=0.00001,
            stamp_duty_rate=0.001,
        )
        assert commission == 5.0
        assert transfer == 0.1
        assert stamp == 10.0  # 10000 * 0.001
        assert total == pytest.approx(15.1)

    def test_sell_shenzhen_stock(self):
        """测试深市卖出（无过户费）"""
        commission, transfer, stamp, total = calculate_fees(
            amount=10000,
            is_buy=False,
            stock_code="sz.000001",
            commission_rate=0.0003,
            transfer_fee_rate=0.00001,
            stamp_duty_rate=0.001,
        )
        assert commission == 5.0
        assert transfer == 0.0  # 深市无过户费
        assert stamp == 10.0
        assert total == pytest.approx(15.0)

    def test_small_amount_commission_min(self):
        """测试小额交易佣金最低 5 元"""
        commission, _, _, _ = calculate_fees(
            amount=1000,
            is_buy=True,
            stock_code="sh.601398",
            commission_rate=0.0003,
            transfer_fee_rate=0.00001,
            stamp_duty_rate=0.001,
        )
        assert commission == 5.0  # 1000 * 0.0003 = 0.3 < 5

    def test_large_amount_commission(self):
        """测试大额交易佣金正常计算"""
        commission, _, _, _ = calculate_fees(
            amount=100000,
            is_buy=True,
            stock_code="sh.601398",
            commission_rate=0.0003,
            transfer_fee_rate=0.00001,
            stamp_duty_rate=0.001,
        )
        assert commission == pytest.approx(30.0)  # 100000 * 0.0003

    def test_negative_amount(self):
        """测试负金额应抛出异常"""
        with pytest.raises(ConfigError, match="交易金额不能为负"):
            calculate_fees(
                amount=-1000,
                is_buy=True,
                stock_code="sh.601398",
                commission_rate=0.0003,
                transfer_fee_rate=0.00001,
                stamp_duty_rate=0.001,
            )

    def test_none_stock_code(self):
        """测试股票代码为空应抛出异常"""
        with pytest.raises(ConfigError, match="股票代码不能为空"):
            calculate_fees(
                amount=1000,
                is_buy=True,
                stock_code=None,
                commission_rate=0.0003,
                transfer_fee_rate=0.00001,
                stamp_duty_rate=0.001,
            )
