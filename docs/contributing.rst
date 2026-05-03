Contributing
============

感谢关注 GTAP！目前项目由 maintenance mode，请提交 Issue 而非 PR。

报告 Bug
--------

请在 GitHub Issues 提交：
- 复现步骤
- 期望行为 vs 实际行为
- 环境信息（OS、Python 版本、gtap 版本）

建议特性
--------

在 Discussions 中提出新特性请求，说明：
- 使用场景
- 预期 API
- 与其他功能的关联

开发流程
--------

本地开发：
1. `git clone` + `cd gtap`
2. `source venv/bin/activate`
3. `pip install -e ".[dev]"`
4. `pytest` + `mypy` + `ruff check`

提交前运行：
- 所有测试通过（141+）
- 类型检查通过（mypy）
- 代码风格符合（ruff）
