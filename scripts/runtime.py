"""Shared executable discovery. Explicit option > environment variable > PATH."""
import os
from pathlib import Path
import shutil


def find_binary(name, override=None):
    env_name = name.upper() + "_BINARY"
    value = override or os.environ.get(env_name) or name
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    found = shutil.which(str(candidate))
    if found:
        return found
    raise FileNotFoundError(
        f"找不到 {name}: {value}。请安装并加入 PATH，"
        f"或设置 {env_name} 为可执行文件完整路径（不要包含额外参数）。"
    )
