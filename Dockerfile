# GTAP Dockerfile
# 基于 python:3.11-slim，镜像目标 < 500MB

FROM python:3.11-slim AS builder

# 系统依赖（轻量）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖定义
COPY pyproject.toml requirements.txt ./

# 安装依赖（分两步以利用缓存）
RUN pip install --no-cache-dir --user -r requirements.txt

# 运行时镜像（更小）
FROM python:3.11-slim AS runtime

# 运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从 builder 复制 Python 依赖
COPY --from=builder /root/.local /root/.local

# 复制源码（src 布局）
COPY src/ ./src/
COPY app.py .
COPY pyproject.toml .

# 确保 Python 能找到用户安装的包
ENV PATH=/root/.local/bin:$PATH

# 安装 gtap 包（editable 模式）
RUN pip install --no-cache-dir -e .

# 暴露 Streamlit 端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
