"""
费用计算模块 - GTAP 网格交易回测平台

计算 A 股交易费用：佣金（最低 5 元）、过户费（仅沪市）、印花税（仅卖出）。
"""

from .exceptions import ConfigError


def calculate_fees(
    amount: float,
    is_buy: bool,
    stock_code: str,
    commission_rate: float,
    transfer_fee_rate: float,
    stamp_duty_rate: float,
) -> tuple[float, float, float, float]:
    """
    计算交易费用。

    Args:
        amount: 交易金额（股价 × 股数）
        is_buy: True 为买入，False 为卖出
        stock_code: 股票代码（用于判断沪市/深市）
        commission_rate: 佣金费率
        transfer_fee_rate: 过户费费率
        stamp_duty_rate: 印花税费率

    Returns:
        (commission, transfer_fee, stamp_duty, total_fee)
        commission: 佣金
        transfer_fee: 过户费（仅沪市收取）
        stamp_duty: 印花税（仅卖出收取）
        total_fee: 总费用
    """
    if amount < 0:
        raise ConfigError("交易金额不能为负")

    if stock_code is None:
        raise ConfigError("股票代码不能为空")

    # 佣金：最低 5 元
    commission = max(amount * commission_rate, 5.0)

    # 过户费：仅沪市（sh 开头）收取
    transfer_fee = amount * transfer_fee_rate if stock_code.startswith("sh") else 0.0

    # 印花税：仅卖出收取
    stamp_duty = amount * stamp_duty_rate if not is_buy else 0.0

    total_fee = commission + transfer_fee + stamp_duty
    return commission, transfer_fee, stamp_duty, total_fee
