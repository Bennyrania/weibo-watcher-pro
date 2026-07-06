"""微博监控器 - 监控引擎（后台线程）"""

import json
import logging
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

from .config import load_config, POSTS_DIR, DATA_DIR
from .state import (
    load_state, save_state, is_seen, mark_seen,
    get_week_filename, add_to_index, load_index, save_index
)

logger = logging.getLogger("weibo-watcher")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://m.weibo.cn/",
}


class WatcherThread(threading.Thread):
    """微博监控后台线程"""

    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self._paused = False
        self._paused_event = threading.Event()
        self._paused_event.set()
        self.status = {
            "running": False,
            "paused": False,
            "last_check": None,
            "last_error": None,
            "check_count": 0,
        }

    def stop(self):
        self._stop_event.set()

    def pause(self):
        self._paused = True
        self._paused_event.clear()
        self.status["paused"] = True
        logger.info("Paused")

    def resume(self):
        self._paused = False
        self._paused_event.set()
        self.status["paused"] = False
        logger.info("Resumed")

    @property
    def is_paused(self):
        return self._paused

    def run(self):
        self.status["running"] = True
        logger.info("Watcher started")

        while not self._stop_event.is_set():
            self._paused_event.wait()
            if self._stop_event.is_set():
                break

            try:
                cfg = load_config()
                if not cfg.get("uid", "").strip() or not cfg.get("cookie", "").strip():
                    logger.warning("Not configured, skipping")
                    self.status["last_error"] = "Not configured"
                    self._wait(15)
                    continue

                self._check_once(cfg)
                self.status["last_error"] = None
                self._wait(cfg.get("poll_interval", 180))

            except Exception as e:
                logger.error(f"Error: {e}")
                self.status["last_error"] = str(e)
                self._wait(60)

        self.status["running"] = False
        logger.info("Watcher stopped")

    def _wait(self, seconds):
        for _ in range(seconds):
            if self._stop_event.is_set():
                break
            time.sleep(1)

    def _check_once(self, cfg):
        """单次检查"""
        uid = cfg["uid"]
        state = load_state()

        session = requests.Session()
        session.headers.update(HEADERS)
        for item in cfg["cookie"].split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                session.cookies[k.strip()] = v.strip()

        all_posts = []

        for page in range(1, cfg.get("max_pages", 2) + 1):
            containerid = f"107603{uid}"
            url = "https://m.weibo.cn/api/container/getIndex"
            params = {"type": "uid", "value": uid, "containerid": containerid, "page": page}

            try:
                resp = session.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                if data.get("ok") != 1:
                    msg = data.get("msg", "")
                    if "login" in msg.lower() or "未登录" in msg:
                        self.status["last_error"] = "COOKIE_EXPIRED"
                        logger.error("Cookie expired!")
                        return
                    logger.warning(f"API error: ok={data.get('ok')}, msg={msg}")
                    continue

                cards = data.get("data", {}).get("cards", [])
                for card in cards:
                    post = self._parse_card(card)
                    if post:
                        all_posts.append(post)

                if len(cards) < 20:
                    break
                time.sleep(1)

            except requests.exceptions.Timeout:
                logger.warning("API timeout")
                continue
            except requests.exceptions.ConnectionError:
                logger.warning("Network error")
                continue
            except Exception as e:
                logger.warning(f"Request error: {e}")
                continue

        # 处理新微博
        new_posts = []
        for post in all_posts:
            if not is_seen(state, post["weibo_id"]):
                mark_seen(state, post["weibo_id"], {
                    "seen_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "text": post["text"][:200],
                    "created_at": post["created_at"],
                })
                new_posts.append(post)

        if new_posts:
            logger.info(f"  +{len(new_posts)} new, total {len(state.get('seen_ids', {}))}")

        state["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_state(state)

        # 先保存 state 再写文件：即使写文件时崩溃，重启后已标记为 seen，不会重复
        for post in new_posts:
            self._save_post(post, cfg)
            add_to_index(post, get_week_filename(post["created_at"]))
            logger.info(f"  New: {post['weibo_id']} - {post['text'][:60]}...")

        self.status["last_check"] = state["last_check"]
        self.status["check_count"] += 1

    def _parse_card(self, card):
        """解析微博卡片"""
        if card.get("card_type") != 9:
            return None
        mblog = card.get("mblog")
        if not mblog or not mblog.get("id"):
            return None

        weibo_id = str(mblog["id"])
        text = mblog.get("text", "")
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</?\w+[^>]*>", "", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        text = text.strip()

        created_at = mblog.get("created_at", "")
        source = mblog.get("source", "")
        pics = []
        if "pics" in mblog:
            pics = [
                pic.get("large", {}).get("url", "") or pic.get("url", "")
                for pic in mblog["pics"]
                if pic.get("large", {}).get("url") or pic.get("url")
            ]

        dt = created_at
        try:
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y").astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            pass

        return {
            "weibo_id": weibo_id,
            "text": text,
            "created_at": dt,
            "source": source,
            "pics": pics,
            "reposts": mblog.get("reposts_count", 0),
            "comments": mblog.get("comments_count", 0),
            "likes": mblog.get("attitudes_count", 0),
        }

    def _save_post(self, post, cfg):
        """
        保存微博到每周汇总文件。
        每篇微博作为文件中的一个条目，以 --- 分隔。
        """
        week_file = get_week_filename(post["created_at"])
        filepath = POSTS_DIR / week_file

        # 构建单条微博内容
        lines = ["---"]
        lines.append(f"weibo_id: {post['weibo_id']}")
        lines.append(f"created_at: {post['created_at']}")
        lines.append(f"url: https://weibo.com/{cfg['uid']}/{post['weibo_id']}")
        lines.append(f"archived_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"source: {post['source']}" if post.get("source") else "source: ''")
        lines.append(f"reposts: {post['reposts']}")
        lines.append(f"comments: {post['comments']}")
        lines.append(f"likes: {post['likes']}")
        lines.append(f"pics_count: {len(post['pics'])}")
        lines.append("")
        lines.append(post["text"] if post["text"] else "（纯图片/转发）")
        lines.append("")

        if post["pics"]:
            lines.append("图片:")
            for i, url in enumerate(post["pics"], 1):
                lines.append(f"  [{i}] {url}")
            lines.append("")

        # 写入文件（追加模式，新条目放末尾）
        POSTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"  Saved to {week_file}")
