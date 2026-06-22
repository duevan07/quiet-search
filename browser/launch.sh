#!/bin/bash
# 专用自动化浏览器 = Playwright 自带的 Chrome for Testing（独立内核，绝不碰系统 Google Chrome）
# 加载 OpenCLI 扩展 + 独立资料目录，给 AutoCLI / OpenCLI / Agent-Reach 复用登录态用。
# 用法：bash ~/.autocli-chrome/launch.sh          # 有头（登录/扫码用，会弹窗）
#       bash ~/.autocli-chrome/launch.sh headless # 无头（已登录后台抓取用）

CFT="$HOME/Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
PROFILE="$HOME/.autocli-chrome/profile"
EXT="$HOME/.autocli-chrome/opencli-ext"
PORT=9333
mkdir -p "$PROFILE"

if curl -s "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "✅ 专用浏览器已在运行（端口 $PORT），无需重启"
  exit 0
fi

MODE="${1:-headful}"
EXTRA=""
[ "$MODE" = "headless" ] && EXTRA="--headless=new"

"$CFT" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE" \
  --load-extension="$EXT" \
  --disable-extensions-except="$EXT" \
  --no-first-run --no-default-browser-check \
  --remote-allow-origins=http://127.0.0.1:$PORT \
  $EXTRA \
  about:blank \
  >/dev/null 2>&1 &

echo "启动中（$MODE）… PID=$!"
sleep 3
curl -s "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1 && echo "✅ 端口 $PORT 就绪" || echo "⚠️ 端口未就绪，稍等"
