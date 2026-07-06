"""微博监控器 - 配置管理"""

import os
import sys
from pathlib import Path

import yaml

# 数据目录：优先取环境变量，默认 data/
DATA_DIR = Path(os.environ.get("WEIBO_DATA_DIR", "") or Path(__file__).resolve().parent.parent / "data")
DATA_DIR.mkdir(exist_ok=True)

CONFIG_FILE = DATA_DIR / "config.yaml"
STATE_FILE = DATA_DIR / "state.json"
POSTS_DIR = DATA_DIR / "posts"
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


DEFAULT_CONFIG = {
    "uid": "",
    "cookie": "",
    "poll_interval": 30,
    "max_pages": 2,
    "track_deletions": True,
    "notify_on_new": False,
}


def ensure_dirs():
    """确保数据目录结构存在"""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    (POSTS_DIR / "deleted").mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """加载配置，若文件不存在则返回默认值"""
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        # 合并默认值，确保新字段不缺
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    """保存配置到文件"""
    # 只保留有效字段
    cleaned = {k: cfg.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG}
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(cleaned, f, allow_unicode=True, default_flow_style=False)
    return cleaned


def is_configured() -> bool:
    """检查是否已配置 UID 和 Cookie"""
    cfg = load_config()
    return bool(cfg.get("uid", "").strip()) and bool(cfg.get("cookie", "").strip())
