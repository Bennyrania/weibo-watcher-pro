================================================================
  微博监控器 (Weibo Watcher) —— 归档副本
  Archived: 2026-10-20
================================================================

【这是什么】
  实时监控指定微博账号的发帖，发出即抓取，本地存档（防删帖）。
  单机版 Flask 应用，浏览器界面在 http://127.0.0.1:5000

  项目状态：🅿️ 已归档 / 暂停使用（2026-10-20）
  归档原因：Cap 老师暂不使用，保留代码与历史数据，日后可随时恢复。
  归档时状态：服务未运行、无开机自启、无计划任务、端口 5000 空闲。


【目录位置】
  代码（本目录）：D:\Projects\weibo-watcher-pro
  远程仓库     ：git@github.com:Bennyrania/weibo-watcher-pro.git
  项目记录     ：Obsidian → 06 - 个人项目 / 项目三 - 微博监控器（已归档）
  WSL 旧副本   ：~/projects/weibo-watcher-pro（如已保留，仅作备份）


【以后想恢复使用：三步】
  第一步 安装环境（只需一次，约 1-3 分钟）
        双击 install.bat
        自动创建 .venv 并安装 flask / requests / pyyaml
        （若 Python 未安装，会提示去 python.org 下载，记得勾选 Add to PATH）

  第二步 填 Cookie（微博登录凭证，会过期，过期就重填）
        打开 data\config.yaml，把 cookie: "" 的双引号内填入新的 Cookie
        获取方法见同目录 COOKIE_GUIDE.html（图文步骤）
        同时确认 uid: 是要监控的微博用户 ID

  第三步 启动
        双击 start.bat
        → 服务后台启动，脚本自检端口，成功才自动打开浏览器
        → 看到仪表盘即成功
        停止：双击 stop.bat


【文件清单】
  install.bat          一键安装（建 venv + 装依赖 + 建桌面快捷方式）
  start.bat            启动（已加健康检查：20 秒内端口没起来会打印日志尾部与排查建议）
  stop.bat             停止（兼容新版 Windows：wmic 已移除，改用 PowerShell CIM 查进程）
  data\config.yaml     配置：uid + cookie + 轮询间隔
  data\posts\          微博存档正文，按 ISO 周分文件（如 2026-W28.md）
  data\posts_index.json 检索索引
  data\state.json      运行状态（最后抓取时间等）
  logs\                运行日志（server.log 最有用）
  README.txt           完整使用手册（含 Cookie 获取图文步骤）
  COOKIE_GUIDE.html    Cookie 获取图文指引（浏览器打开更清楚）
  app\                 源码：main.py（Flask 路由）/ watcher.py（轮询线程）/ state.py（存档与索引）


【注意事项】
  1. data\config.yaml 里有你的微博 Cookie —— 这是账号凭证，不要提交到 git、
     不要发给任何人。.gitignore 已经把它排除。
  2. 归档期间不会自动运行、不会占用 CPU/内存/网络。
  3. 数据不会因归档丢失：data\ 已随代码一起复制到本目录。
  4. 端口固定 5000；若与其他程序冲突，先跑 stop.bat 或改 app\main.py 里的 port。


【技术备注（给未来的自己/给 AI 助手）】
  - Windows + WSL 混合开发：代码在 WSL 里写，启动脚本必须在 Windows 侧跑。
    两边的 Python 环境不通用，.venv 必须在 Windows 侧重建（故本归档未带 .venv）。
  - 所有 .bat 必须 CRLF 换行；时间戳一律用 PowerShell 生成，不能用 %DATE% 截取
    （中文 Windows 的 %DATE% 是 "2026/10/20 周一" 格式，substring 会算错）。
  - pythonw.exe 用于后台无窗口运行；若用 python.exe 会阻塞脚本窗口。
  - 微博正文接口默认返回截断文本，完整正文需再调 statuses/extend 接口
    （见 watcher.py 的 _fetch_full_text）。
================================================================
