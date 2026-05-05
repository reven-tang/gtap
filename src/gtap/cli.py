"""GTAP CLI entry point."""
import argparse
import sys
from pathlib import Path

from .config import GridTradingConfig
from .data import get_stock_data
from .grid import grid_trading
from .metrics import calculate_metrics
from .plot import plot_kline, plot_asset_curve, plot_grid_lines


def main():
    """CLI entry point for gtap."""
    parser = argparse.ArgumentParser(
        prog="gtap",
        description="Grid Trading Analysis Platform - 股票网格交易回测平台",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # backtest subcommand
    bt = subparsers.add_parser("backtest", help="Run grid trading backtest")
    bt.add_argument("--stock", required=True, help="Stock code (e.g. 000001)")
    bt.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    bt.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    bt.add_argument("--grid-lower", type=float, default=None, help="Grid lower price")
    bt.add_argument("--grid-upper", type=float, default=None, help="Grid upper price")
    bt.add_argument("--grid-count", type=int, default=10, help="Number of grid levels")
    bt.add_argument("--amount", type=float, default=10000, help="Amount per grid (元)")
    bt.add_argument("--output", default=None, help="Output directory for results")

    # info subcommand
    info = subparsers.add_parser("info", help="Show stock info")
    info.add_argument("--stock", required=True, help="Stock code (e.g. 000001)")

    # version
    parser.add_argument("--version", action="version", version="gtap 1.0.0")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "backtest":
        return _run_backtest(args)
    elif args.command == "info":
        return _run_info(args)

    return 0


def _run_backtest(args):
    """Run backtest with CLI args."""
    try:
        # Build config
        config = GridTradingConfig(
            stock_code=args.stock,
            start_date=args.start,
            end_date=args.end,
            grid_count=args.grid_count,
            amount_per_grid=args.amount,
            grid_lower=args.grid_lower,
            grid_upper=args.grid_upper,
        )

        # Get data
        data = get_stock_data(config.stock_code, config.start_date, config.end_date)
        if data is None:
            print(f"❌ 无法获取股票 {config.stock_code} 的数据")
            return 1

        # Run backtest
        result = grid_trading(config, data)

        # Calculate metrics
        metrics = calculate_metrics(result, data, config)

        # Print summary
        print(f"\n📊 回测结果: {config.stock_code} ({config.start_date} ~ {config.end_date})")
        print(f"   总收益率: {metrics.get('total_return_pct', 0):.2f}%")
        print(f"   年化收益率: {metrics.get('annual_return_pct', 0):.2f}%")
        print(f"   最大回撤: {metrics.get('max_drawdown_pct', 0):.2f}%")
        print(f"   夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"   交易次数: {metrics.get('trade_count', 0)}")

        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            # Save detailed results
            import json
            report = {
                "config": config.__dict__,
                "metrics": metrics,
                "trades": len(result.trades),
            }
            (output_dir / "report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False, default=str)
            )
            print(f"\n📁 结果已保存到: {output_dir}")

        return 0

    except Exception as e:
        print(f"❌ 回测失败: {e}")
        return 1


def _run_info(args):
    """Show stock info."""
    try:
        data = get_stock_data(args.stock, "2024-01-01", "2024-12-31")
        if data is None:
            print(f"❌ 无法获取股票 {args.stock} 的数据")
            return 1

        print(f"\n📈 股票信息: {args.stock}")
        print(f"   数据量: {len(data)} 条")
        print(f"   时间范围: {data.index[0]} ~ {data.index[-1]}")
        if hasattr(data, 'close'):
            print(f"   最新收盘价: {data.close.iloc[-1]:.2f}")
            print(f"   最高价: {data.high.max():.2f}")
            print(f"   最低价: {data.low.min():.2f}")

        return 0

    except Exception as e:
        print(f"❌ 获取信息失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())