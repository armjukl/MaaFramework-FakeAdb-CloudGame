"""MaaFFACG 本地环境变量文件的轻量加载器，无额外依赖。"""

from __future__ import annotations

from pathlib import Path


def load_env(path: str | Path) -> dict[str, str]:
    """读取 ``KEY=VALUE`` 格式；文件不存在时返回空配置。"""
    env_path = Path(path)
    if not env_path.is_file():
        return {}
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"invalid environment line {line_number} in {env_path}")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
