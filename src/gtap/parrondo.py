"""
Parrondo's Paradox 模拟模块 - GTAP 网格交易回测平台

Parrondo悖论：两个"输钱游戏"交替玩反而能赢钱。
本模块验证这一悖论，并探索其与网格交易/跨资产再平衡的关联。

核心发现：网格交易中的"低波动赚小钱+高波动亏大钱"结构
是否类似 Parrondo 的 Game A+B 组合效应。
"""

import numpy as np
from dataclasses import dataclass, field
from typing import NamedTuple


@dataclass
class ParrondoConfig:
    """Parrondo 模拟配置"""
    # Game A: 简单硬币（偏向输）
    game_a_win_prob: float = 0.49  # Game A 赢的概率（<0.5 = 输钱倾向）
    game_a_reward: float = 1.0     # Game A 赢的收益

    # Game B: 状态依赖硬币（资本依赖）
    game_b_win_prob_mod: float = 0.16  # 资本 % M == 0 时赢的概率
    game_b_win_prob_pos: float = 0.75   # 资本 % M != 0 时赢的概率
    game_b_modulus: int = 3             # M（状态划分周期）
    game_b_reward: float = 1.0

    # 模拟参数
    initial_capital: float = 100.0
    total_rounds: int = 1000
    mix_pattern: str = "alternating"  # alternating / random / a_only / b_only
    random_mix_prob: float = 0.5       # random 模式下选 A 的概率


class ParrondoRound(NamedTuple):
    """单轮模拟记录"""
    round_num: int
    game_type: str  # "A" / "B"
    won: bool       # 是否赢了
    reward: float   # 收益/亏损
    capital_after: float  # 该轮后资本


class ParrondoResult(NamedTuple):
    """Parrondo 模拟结果"""
    config: ParrondoConfig
    rounds: list[ParrondoRound]
    final_capital: float
    total_return_pct: float  # 总收益率（%）
    win_rate_a: float  # Game A 胜率
    win_rate_b: float  # Game B 胜率
    win_rate_combined: float  # 组合胜率
    game_a_only_result: float  # 只玩 A 的最终资本
    game_b_only_result: float  # 只玩 B 的最终资本
    combined_result: float  # 交替玩的最终资本
    parrondo_effect: bool  # 是否观察到 Parrondo 效应


def parrondo_simulate(config: ParrondoConfig) -> ParrondoResult:
    """执行 Parrondo 模拟

    验证：
    1. 只玩 Game A → 输钱（win_prob < 0.5）
    2. 只玩 Game B → 输钱（状态依赖导致整体负期望）
    3. 交替/混合玩 → 可能赢钱（Parrondo 效应）

    Returns:
        ParrondoResult 模拟结果
    """
    rng = np.random.default_rng()

    # === 只玩 Game A ===
    capital_a = config.initial_capital
    for _ in range(config.total_rounds):
        if rng.random() < config.game_a_win_prob:
            capital_a += config.game_a_reward
        else:
            capital_a -= config.game_a_reward

    # === 只玩 Game B ===
    capital_b = config.initial_capital
    for _ in range(config.total_rounds):
        if int(capital_b) % config.game_b_modulus == 0:
            win_prob = config.game_b_win_prob_mod
        else:
            win_prob = config.game_b_win_prob_pos
        if rng.random() < win_prob:
            capital_b += config.game_b_reward
        else:
            capital_b -= config.game_b_reward

    # === 组合玩法 ===
    capital = config.initial_capital
    rounds = []
    a_wins = 0
    a_total = 0
    b_wins = 0
    b_total = 0

    for i in range(config.total_rounds):
        # 选择游戏
        if config.mix_pattern == "alternating":
            game = "A" if i % 2 == 0 else "B"
        elif config.mix_pattern == "random":
            game = "A" if rng.random() < config.random_mix_prob else "B"
        elif config.mix_pattern == "a_only":
            game = "A"
        elif config.mix_pattern == "b_only":
            game = "B"
        else:
            game = "A" if i % 2 == 0 else "B"

        # 按游戏规则玩
        if game == "A":
            won = rng.random() < config.game_a_win_prob
            reward = config.game_a_reward if won else -config.game_a_reward
            a_total += 1
            if won:
                a_wins += 1
        else:  # Game B
            if int(capital) % config.game_b_modulus == 0:
                win_prob = config.game_b_win_prob_mod
            else:
                win_prob = config.game_b_win_prob_pos
            won = rng.random() < win_prob
            reward = config.game_b_reward if won else -config.game_b_reward
            b_total += 1
            if won:
                b_wins += 1

        capital += reward
        rounds.append(ParrondoRound(
            round_num=i,
            game_type=game,
            won=won,
            reward=reward,
            capital_after=capital,
        ))

    # 汇总结果
    final_capital = capital
    total_return_pct = ((final_capital - config.initial_capital) / config.initial_capital) * 100
    win_rate_a = a_wins / a_total if a_total > 0 else 0.0
    win_rate_b = b_wins / b_total if b_total > 0 else 0.0
    total_wins = a_wins + b_wins
    win_rate_combined = total_wins / (a_total + b_total) if (a_total + b_total) > 0 else 0.0

    # Parrondo 效果判定：A输 + B输 + 组合赢
    parrondo_effect = (
        capital_a < config.initial_capital
        and capital_b < config.initial_capital
        and final_capital > config.initial_capital
    )

    return ParrondoResult(
        config=config,
        rounds=rounds,
        final_capital=round(final_capital, 2),
        total_return_pct=round(total_return_pct, 2),
        win_rate_a=round(win_rate_a, 4),
        win_rate_b=round(win_rate_b, 4),
        win_rate_combined=round(win_rate_combined, 4),
        game_a_only_result=round(capital_a, 2),
        game_b_only_result=round(capital_b, 2),
        combined_result=round(final_capital, 2),
        parrondo_effect=parrondo_effect,
    )


def parrondo_grid_analysis():
    """探索 Parrondo 效应与网格交易的关联

    分析要点：
    1. 网格交易中的"低波动网格盈利" ≈ Game A（小额频繁盈利）
    2. 高波动止损/清仓 ≈ Game B（大额偶发亏损）
    3. 跨资产再平衡 ≈ A+B 组合（低波动资产稳定盈利 + 高波动资产间歇亏损 → 组合盈利）

    返回分析结论字典
    """
    return {
        "game_a_mapping": "低波动网格盈利（高频小额赢）",
        "game_b_mapping": "高波动止损亏损（低频大额输）",
        "combined_mapping": "跨资产再平衡（A资产稳定+B资产亏损 → 组合反而盈利）",
        "parrondo_condition": "相关性低的资产组合，波动差异大时，再平衡产生的效果类似Parrondo",
        "implication": "多资产网格策略的核心价值不在单一资产盈利，而在跨资产再平衡的Parrondo效应",
    }


__all__ = [
    "ParrondoConfig",
    "ParrondoRound",
    "ParrondoResult",
    "parrondo_simulate",
    "parrondo_grid_analysis",
]