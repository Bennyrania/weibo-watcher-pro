"""
微博监控器 - Web 服务 (Flask)
一键启动，浏览器操作，适合非技术用户。
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import load_config, save_config, is_configured, ensure_dirs, LOGS_DIR, POSTS_DIR, DATA_DIR
from .state import get_stats, get_index_page, search_index_by_id
from .watcher import WatcherThread

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("weibo-watcher")

# ── Flask ──
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ── 全局监控线程 ──
watcher: WatcherThread = None


# ═══════════════════════════════════════════════
# Web 页面路由
# ═══════════════════════════════════════════════

@app.route("/")
def dashboard():
    """首页 - 仪表盘"""
    global watcher
    stats = get_stats()
    if watcher:
        stats["is_running"] = watcher.status["running"]
        stats["is_paused"] = watcher.status["paused"]
        stats["last_check"] = watcher.status["last_check"] or stats["last_check"]
        stats["error"] = watcher.status["last_error"]
        stats["check_count"] = watcher.status["check_count"]
    return render_template("dashboard.html", stats=stats, configured=is_configured())


@app.route("/config", methods=["GET", "POST"])
def config_page():
    """配置页面"""
    global watcher

    if request.method == "POST":
        cfg = {
            "uid": request.form.get("uid", "").strip(),
            "cookie": request.form.get("cookie", "").strip(),
            "poll_interval": int(request.form.get("poll_interval", 180)),
            "max_pages": int(request.form.get("max_pages", 2)),
            "track_deletions": request.form.get("track_deletions") == "on",
        }
        save_config(cfg)
        logger.info("⚙️ 配置已更新")

        # 更新后重启监控
        if watcher and watcher.status["running"]:
            watcher.stop()
            watcher.join(timeout=5)
            if watcher.is_alive():
                logger.warning("Watcher thread did not exit within timeout")
        watcher = WatcherThread()
        watcher.start()

        return jsonify({"success": True, "message": "配置已保存，监控已重启"})

    cfg = load_config()
    return render_template("config.html", config=cfg)


@app.route("/feed")
def feed_page():
    """微博列表页面 - 直接显示内容预览"""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    posts, total = get_index_page(page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return render_template("feed.html", posts=posts, page=page, total_pages=total_pages, total=total)


@app.route("/post/<post_id>")
def view_post(post_id):
    """查看单篇微博 - 从周文件中提取"""
    entry = search_index_by_id(post_id)
    if not entry:
        return f"<h3>未找到微博: {post_id}</h3>", 404

    week_file = entry["week_file"]
    filepath = POSTS_DIR / week_file
    if not filepath.exists():
        # 也检查 deleted
        filepath = POSTS_DIR / "deleted" / week_file

    # 从周文件中提取该条微博的内容
    content = ""
    if filepath.exists():
        full = filepath.read_text(encoding="utf-8", errors="replace")
        # 按 --- 分隔，找包含 weibo_id: post_id 的块
        sections = full.split("\n---\n")
        for sec in sections:
            if f"weibo_id: {post_id}" in sec:
                content = sec.strip()
                break

    if not content:
        content = f"weibo_id: {post_id}\ncreated_at: {entry['created_at']}\n(内容存储在 {week_file} 中，但未找到具体条目)"

    return render_template("post.html", post=entry, content=content)


@app.route("/logs")
def logs_page():
    """日志页面"""
    log_files = sorted(LOGS_DIR.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)

    # 读取当前日志内容
    log_content = ""
    current_log = request.args.get("file", "")
    if current_log:
        log_path = LOGS_DIR / current_log
        if log_path.exists():
            log_content = log_path.read_text(encoding="utf-8", errors="replace")[-50000:]

    files = [
        {
            "name": f.name,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }
        for f in log_files[:20]
    ]
    return render_template("logs.html", log_files=files, log_content=log_content, current_log=current_log)


# ═══════════════════════════════════════════════
# API 路由（供页面 AJAX 调用）
# ═══════════════════════════════════════════════

@app.route("/api/status")
def api_status():
    """API: 获取监控状态"""
    global watcher
    stats = get_stats()
    if watcher:
        stats["is_running"] = watcher.status["running"]
        stats["is_paused"] = watcher.status["paused"]
        stats["last_check"] = watcher.status["last_check"] or stats["last_check"]
        stats["error"] = watcher.status["last_error"]
        stats["check_count"] = watcher.status["check_count"]
    return jsonify(stats)


@app.route("/api/control/<action>")
def api_control(action):
    """API: 控制监控启停"""
    global watcher
    if action == "start":
        if watcher and watcher.status["running"]:
            return jsonify({"success": True, "message": "监控已在运行"})
        if not is_configured():
            return jsonify({"success": False, "message": "请先配置 UID 和 Cookie"}), 400
        watcher = WatcherThread()
        watcher.start()
        return jsonify({"success": True, "message": "监控已启动"})

    elif action == "stop":
        if watcher and watcher.status["running"]:
            watcher.stop()
            watcher.join(timeout=10)
            watcher = None
            return jsonify({"success": True, "message": "监控已停止"})
        return jsonify({"success": True, "message": "监控未在运行"})

    elif action == "pause":
        if watcher and watcher.status["running"]:
            watcher.pause()
            return jsonify({"success": True, "message": "监控已暂停"})
        return jsonify({"success": False, "message": "监控未运行"}), 400

    elif action == "resume":
        if watcher and watcher.status["running"]:
            watcher.resume()
            return jsonify({"success": True, "message": "监控已恢复"})
        return jsonify({"success": False, "message": "监控未运行"}), 400

    return jsonify({"success": False, "message": f"未知操作: {action}"}), 400


@app.route("/api/check-now")
def api_check_now():
    """API: 手动触发一次检查"""
    global watcher
    cfg = load_config()
    if not cfg.get("uid", "").strip() or not cfg.get("cookie", "").strip():
        return jsonify({"success": False, "message": "请先配置 UID 和 Cookie"}), 400
    if not watcher or not watcher.status["running"]:
        # 没有后台线程时，临时检查一次
        from .watcher import WatcherThread as WT
        temp = WT()
        temp._check_once(cfg)
        return jsonify({"success": True, "message": "单次检查完成"})
    return jsonify({"success": True, "message": "后台监控正在运行，无需手动触发"})


@app.route("/api/posts")
def api_posts():
    """API: 获取微博列表（JSON）"""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    posts, total = get_index_page(page=page, per_page=per_page)
    return jsonify({"posts": posts, "total": total, "page": page})


# ═══════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════

def create_app():
    """工厂函数，供外部调用"""
    global watcher
    ensure_dirs()

    # 如果已配置，自动启动监控
    if is_configured():
        watcher = WatcherThread()
        watcher.start()
        logger.info("📡 监控已自动启动")
    else:
        logger.info("⏳ 尚未配置，请访问 Web 界面完成设置")

    return app


def main():
    """命令行启动"""
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")

    app = create_app()
    print(f"""
+{"=" * 45}+
|        WeiBo Watcher - v1.1              |
|                                          |
|  Open browser to:                        |
|  -> http://127.0.0.1:{port}                |
|                                          |
|  Press Ctrl+C to stop                    |
+{"=" * 45}+
    """)

    # 记录日志
    file_handler = logging.FileHandler(LOGS_DIR / "server.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger("weibo-watcher").addHandler(file_handler)

    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
