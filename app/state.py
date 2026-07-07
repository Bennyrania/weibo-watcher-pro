"""微博监控器 - 状态管理 + 帖子索引"""

import json
from datetime import datetime, date
from pathlib import Path

from .config import DATA_DIR, STATE_FILE, POSTS_DIR

INDEX_FILE = DATA_DIR / "posts_index.json"


# ============================================================
# 周文件计算
# ============================================================

def get_week_filename(dt_str: str) -> str:
    """根据日期字符串计算 ISO 周文件名，如 '2026-W27.md'"""
    try:
        d = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").date()
    except (ValueError, TypeError):
        d = date.today()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}.md"


# ============================================================
# 帖子索引管理
# ============================================================

def load_index() -> list:
    """加载帖子索引"""
    if not INDEX_FILE.exists():
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_index(index: list):
    """保存帖子索引"""
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def add_to_index(post: dict, week_file: str):
    """添加一条帖子到索引（按时间倒序插入）"""
    index = load_index()
    entry = {
        "id": post["weibo_id"],
        "created_at": post["created_at"],
        "archived_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text_preview": post["text"] if post.get("text") else "(纯图片/转发)",
        "week_file": week_file,
        "pics": len(post.get("pics", [])),
        "reposts": post.get("reposts", 0),
        "comments": post.get("comments", 0),
        "likes": post.get("likes", 0),
    }
    # 去重
    index = [e for e in index if e["id"] != post["weibo_id"]]
    # 按 created_at 倒序插入
    index.insert(0, entry)
    save_index(index)
    return entry


def get_index_page(page: int = 1, per_page: int = 20) -> tuple:
    """分页获取索引，返回 (posts, total)"""
    index = load_index()
    total = len(index)
    start = (page - 1) * per_page
    end = start + per_page
    return index[start:end], total


def search_index_by_id(weibo_id: str) -> dict | None:
    """根据微博 ID 查找索引条目"""
    index = load_index()
    for entry in index:
        if entry["id"] == weibo_id:
            return entry
    return None


# ============================================================
# 状态管理（已有微博 ID 去重）
# ============================================================

def load_state() -> dict:
    """加载状态文件"""
    if not STATE_FILE.exists():
        return {"seen_ids": {}, "last_check": None, "total_posts": 0, "total_deleted": 0}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"seen_ids": {}, "last_check": None, "total_posts": 0, "total_deleted": 0}


def save_state(state: dict):
    """保存状态"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_seen(state: dict, weibo_id: str) -> bool:
    return weibo_id in state.get("seen_ids", {})


def mark_seen(state: dict, weibo_id: str, metadata: dict = None):
    if "seen_ids" not in state:
        state["seen_ids"] = {}
    state["seen_ids"][weibo_id] = metadata or {
        "seen_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    state["total_posts"] = len(state["seen_ids"])


def get_deleted_count() -> int:
    """获取已删除微博数量"""
    deleted_dir = POSTS_DIR / "deleted"
    if not deleted_dir.exists():
        return 0
    return len(list(deleted_dir.glob("*.md")))


def get_stats() -> dict:
    """获取统计数据"""
    state = load_state()
    index = load_index()
    total_posts = len(index)
    deleted = get_deleted_count()
    last_check = state.get("last_check", "从未")

    recent = []
    for entry in index[:3]:
        recent.append((entry["id"], entry["created_at"], entry["text_preview"][:40]))

    return {
        "total_seen": total_posts,
        "total_deleted": deleted,
        "last_check": last_check,
        "recent_posts": recent,
        "is_running": False,
        "is_paused": False,
        "error": None,
        "check_count": 0,
    }
