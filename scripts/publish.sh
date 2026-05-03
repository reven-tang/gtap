#!/usr/bin/env bash
# GTAP v1.0.0 发布自动化脚本
# 用法: ./scripts/publish.sh [--dry-run] [--testpypi]

set -e  # 遇错即停

DRY_RUN=false
TEST_PYPI=false

# 解析参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --testpypi) TEST_PYPI=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo "🚀 GTAP v1.0.0 发布流程启动..."

# Step 1: 环境检查
echo "🔍 检查环境..."
python --version
pip --version

# Step 2: 运行测试
echo "🧪 运行测试..."
source venv/bin/activate
pytest --cov=gtap

# Step 3: 构建分发包
echo "📦 构建分发包..."
python -m build

# Step 4: 检查包
echo "🔎 检查包..."
twine check dist/*

if [[ "$DRY_RUN" == "true" ]]; then
  echo "✅ Dry-run 模式完成，不实际上传"
  exit 0
fi

# Step 5: 上传 PyPI
if [[ "$TEST_PYPI" == "true" ]]; then
  echo "📤 上传到 TestPyPI..."
  twine upload --repository testpypi dist/*
else
  echo "📤 上传到 PyPI..."
  twine upload dist/*
fi

# Step 6: 打标签
echo "🏷️  打标签..."
git add -A
git commit -m "chore: release v1.0.0"
git tag -a v1.0.0 -m "GTAP v1.0.0 - 正式发布"
git push origin main --tags

echo "🎉 发布完成！"
echo "   PyPI: https://pypi.org/project/gtap/"
echo "   Docs: https://gtap.readthedocs.io/"
