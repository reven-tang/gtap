"""Test Docker configuration."""
from pathlib import Path

def test_dockerfile_exists():
    """Dockerfile 必须存在。"""
    assert Path("Dockerfile").exists(), "Dockerfile missing"

def test_docker_compose_exists():
    """docker-compose.yml 必须存在。"""
    assert Path("docker-compose.yml").exists(), "docker-compose.yml missing"

def test_dockerfile_uses_slim():
    """Dockerfile 应使用 python:slim 基础镜像以控制大小。"""
    content = Path("Dockerfile").read_text()
    assert "slim" in content.lower(), "Dockerfile should use python:slim"

def test_docker_exposes_streamlit_port():
    """Dockerfile 必须暴露 Streamlit 默认端口 8501。"""
    content = Path("Dockerfile").read_text()
    assert "8501" in content, "Dockerfile must expose port 8501"

if __name__ == "__main__":
    test_dockerfile_exists()
    test_docker_compose_exists()
    test_dockerfile_uses_slim()
    test_docker_exposes_streamlit_port()
    print("✅ Docker config tests pass")
