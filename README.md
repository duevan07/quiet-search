# quiet-search 🤫🔍

> **一句话，全网检索；全程无头后台，绝不打扰你。**
> 把 AI Agent（如 Claude Code）变成"全网搜查官"——小红书 / B站 / 推特 / Reddit / 知乎 / YouTube / 公众号 + **Kimi / 元宝 / DeepSeek / 秘塔** 四个中文强模型，一句口令搞定，且**绝不碰你的日常浏览器**。

> ⚠️ 这是一套 **编排 + 说明书 + 辅助脚本**，依赖 agent-reach / OpenCLI / camoufox / Playwright / TikHub / yuanbao-free-api 等第三方项目（请从各自官方来源安装）。使用前请先读 [DISCLAIMER.md](DISCLAIMER.md)。

## 📦 仓库结构
- `README.md` — 完整搭建说明书（下方全文，给 AI 读）
- `engines/` — AI/平台引擎封装：`yb.py`(元宝) · `kimi.py`/`kimi_login.py`(Kimi) · `xhs.py`(小红书/TikHub)
- `browser/launch.sh` — 专用无头浏览器(Chrome for Testing)启动模板
- `tools/heimao_cli.py` — 自建公开 API CLI 示范（黑猫投诉）
- `commands/search-commands.md` — `ss/ssc/ssf` 口令（粘进你 AI 的常驻记忆）
- `.env.example` — 凭证模板（复制成 `.env`，已被 `.gitignore` 忽略）

## 🚀 最快上手
1. `cp .env.example .env`，填入你自己的 `TIKHUB_KEY` 等；
2. 按下方 Playbook 装 agent-reach / OpenCLI / camoufox；
3. 把 `commands/search-commands.md` 粘进你 AI 的记忆；
4. 对你的 AI 说 `ssc 旅游搭子` —— 坐等带来源的报告，全程不打扰。

---

# 无打扰全网检索 · AI 搭建 Playbook

> **目标读者：AI Agent（如 Claude Code）。** 读完本文，你应能在一台新机器上复刻一套"打一句口令 → 多平台静默检索 → 不打扰用户、不碰用户日常浏览器"的检索系统。
>
> ⚠️ 凡标 `<...>` 的都是占位符（密钥/账号/路径），需按本机实际替换。**绝不要把真实密钥写进可分享文档。**

---

## 0. 一句话心智模型

大模型自己**碰不到网站**，要靠"手脚"。按平台**开放程度**，连接方式分四档；**越开放越轻越稳，越封闭越重越脆**。核心设计原则只有一条：

> **所有自动化绝不碰用户的日常浏览器。独立内核 + 无头后台 + 静默交付。**

---

## 1. 四种连接方式（按优先级，能用上面的就别用下面的）

| 档 | 方式 | 适用平台 | 要登录 | 稳定性 |
|---|---|---|---|---|
| A | **真 MCP**（标准接口直连） | 知乎、TikHub(小红书) | 否 | 🟢 最稳 |
| B | **免登录公开 API / 自建 CLI** | GitHub、YouTube字幕、V2EX、RSS、维基、Arxiv、HackerNews、语义搜索、网页转MD、黑猫投诉等 | 否 | 🟢 |
| C | **本地代理 / camoufox 网页直驱**（把封闭 AI 网页变成可调用） | 元宝(公众号生态)、Kimi / DeepSeek / 秘塔(中文 AI 引擎) | 是(cookie) | 🟡 会过期 |
| D | **专用无头浏览器 + 扩展**（驱动真浏览器） | 推特/X、Reddit、B站、小红书(看具体内容) | 是(小号) | 🔴 最重 |

**路由判断**：能 A 就 A；否则能 B 就 B；中文公众号生态走 C；只有"必须登录才能看"的封闭平台才用 D。

---

## 2. 组件与安装

### 2.1 agent-reach（B 档主力，免登录）
```bash
pipx install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto        # 自动装依赖、配免费语义搜索(Exa)
agent-reach doctor                     # 看各渠道状态
```
开箱即用（无需登录）：GitHub、YouTube 字幕、V2EX、RSS、HackerNews、Arxiv、维基、**全网语义搜索**、**任意网页转 Markdown**。

### 2.2 OpenCLI（D 档的浏览器遥控器，需 ≥ v1.8.4）
```bash
npm install -g @jackwener/opencli@latest
opencli doctor                         # 看 daemon + 扩展连接
```
- 旧版(<1.8.4) bridge 有 bug，必须升级。
- 它靠一个 **Chrome 扩展** + 本地 daemon 驱动浏览器。**关键：让扩展只装在"专用浏览器"里，不要用用户日常 Chrome。**

### 2.3 专用无头浏览器（D 档的核心，绝不碰日常 Chrome）
用 **Playwright 自带的 Chrome for Testing**（独立 .app，不与日常 Chrome 抢 macOS 单实例）：
- 二进制：`~/Library/Caches/ms-playwright/chromium-<ver>/chrome-mac-arm64/Google Chrome for Testing.app/.../Google Chrome for Testing`
- 把 OpenCLI 扩展从用户 Chrome 资料里复制出来（`.../Extensions/<extId>/<ver>/`，去掉 `_metadata` 目录），用 `--load-extension` 加载。
- 启动脚本 `~/.autocli-chrome/launch.sh`：

```bash
#!/bin/bash
CFT="<Chrome for Testing 二进制路径>"
PROFILE="$HOME/.autocli-chrome/profile"
EXT="$HOME/.autocli-chrome/opencli-ext"
PORT=9333
mkdir -p "$PROFILE"
curl -s "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1 && { echo "已在运行"; exit 0; }
MODE="${1:-headful}"; EXTRA=""; [ "$MODE" = "headless" ] && EXTRA="--headless=new"
"$CFT" --remote-debugging-port=$PORT --user-data-dir="$PROFILE" \
  --load-extension="$EXT" --disable-extensions-except="$EXT" \
  --no-first-run --no-default-browser-check \
  --remote-allow-origins=http://127.0.0.1:$PORT $EXTRA about:blank >/dev/null 2>&1 &
```
- **首次登录**：`launch.sh`（有头）→ 用**小号**登推特/小红书/B站/Reddit（扫码或账号密码，用户自己操作，AI 不碰密码）→ 登录态存进 `profile`。
- **日常使用**：`launch.sh headless`（无头后台，绝不弹窗抢焦点）。
- 锁定默认 profile 到专用浏览器：`opencli profile use dedicated`（或 `OPENCLI_PROFILE=<id>` 前缀）。**绝不路由到用户日常 Chrome。**

### 2.4 元宝本地代理（C 档，中文/公众号生态）
- 部署 `yuanbao-free-api`（社区项目），作为 launchd/常驻服务，暴露 OpenAI 兼容接口于本地端口（如 8000），本地 key `<本地key>`。
- 底层用**无头 Playwright Chromium** 驱动元宝网页，登录态持久化在 `~/.yuanbao_profile`。
- 封装一个一行命令 `yb.py`：`python3 yb.py "问题"` → 返回干净答案。
- cookie 过期 → 设 `headful` 重登一次。

### 2.5 MCP 服务（A 档）
在 AI 客户端的 MCP 配置里加：
- **知乎**：zhihu 热榜 / 搜索 / 全网搜（社区 MCP）。
- **TikHub 小红书**：HTTP MCP，需 `x-api-key: <你的TikHub key>`。走量、不赌账号的小红书数据走这里。
```json
{ "mcpServers": {
  "tikhub-xiaohongshu": { "type":"http", "url":"<TikHub MCP url>", "headers":{"x-api-key":"<key>"} }
}}
```

### 2.6 自建公开 API CLI（B 档进阶，示范：黑猫投诉）
很多站有**公开 JSON 接口 + 客户端可算的签名**，可不登录做成 CLI。方法论：
1. 打开目标页，看前端 JS / network 抓真实接口与参数。
2. 复现签名（常见：`sha256("".join(sorted([ts, rs, salt, id, type, page_size, page])))`）。
3. 用标准库写单文件 CLI，全部 `--json` 可选。
4. **遇到登录墙/验证码就降级或跳过，绝不引导用户登录。**

### 2.7 中文 AI 引擎（camoufox 网页直驱）— 以 Kimi 为例
有些封闭 AI 网页没有现成 free-api，可用 **camoufox（隐身 Firefox）无头直驱网页 + 抓答案**，登录态持久化到独立 profile。Kimi 实战要点（踩坑后定稿；DeepSeek / 秘塔 / Grok 同理，各用各自 profile）：
- **登录**（`kimi_login.py`，有头 camoufox 开 kimi.com，小号微信扫码）：检测"登录以同步历史会话"字样**消失 = 登录成功**，停几秒确保 `localStorage` 落盘后让 `with` 块**优雅退出**——**严禁 pkill，否则登录态不落盘、白扫一次**。登录态存 `~/.kimi_profile`。
- **发送**：输入框多是 Vue 控制的 contenteditable，**直接键盘打字不触发输入事件、发送键灰着**；必须 `execCommand('insertText', ...)` + 派发 `InputEvent` 才点亮。
- **提交**：用键盘 **Enter** 发送，**别点发送按钮**（常被侧栏遮罩 `.mask` 拦住鼠标点击；键盘事件能穿透遮罩）。
- **取答案**：等最后一个答案容器（Kimi 是 `.markdown`）文本**稳定（约几秒不变）**后取 `innerText`。
- 调用：`python3 kimi.py "问题"` —— 无头静默、不打扰；与元宝/DeepSeek/秘塔一起做关键结论多源交叉。

---

## 3. 口令系统（写进 AI 的持久记忆，让用户零负担驱动）

把以下规则写进 AI 的常驻记忆（如 `CLAUDE.md`），任何会话开场即生效：

- `ss <内容>` = 全平台（中国组 + 外国组），合并成带来源的报告
- `ssc <内容>` = 全中国（元宝 + 小红书 + B站 + 知乎 + V2EX；走量加 TikHub）
- `ssf <内容>` = 全外国（推特 + Reddit + WebSearch + YouTube；技术加 HN/Arxiv）

执行细则：登录类走专用无头浏览器；**多平台并行**；**人速限流**；输出=**按平台分块 + 综合结论 + 来源链接**的小报告；中文实时带元宝；**关键结论可用 元宝 / Kimi / DeepSeek / 秘塔 多源交叉核实**。

---

## 4. 🚨 铁律（全是踩坑换来的，违反就翻车）

1. **绝不碰用户日常 Google Chrome**。自动化只用 Chrome for Testing / headless-shell（独立内核）。
2. **专用浏览器永远无头后台**。有头模式只用于"首次登录扫码"，用完切回无头。无窗口 = 不可能抢用户键盘焦点。
3. **禁止 `osascript activate` / `--focus`** 把自动化窗口提到前台。
4. **禁止 `autocli read` 及 autocli 任何登录/浏览器命令**——它的扩展在用户日常 Chrome 里，一调就占用日常 Chrome。autocli 只可用于免登录公共站。
5. **渲染 PNG/PDF 用 `chrome-headless-shell`**（`~/Library/Caches/ms-playwright/chromium_headless_shell-*/.../chrome-headless-shell`），**不要用系统 `/Applications/Google Chrome`**——只要有任何 `Google Chrome.app` 进程在跑，用户双击日常 Chrome 就打不开窗口。
6. **登录类一律用小号**，主号绝不碰；**人速限流**（小红书尤其：间隔几秒、单次几十条内，见验证码当天停手）；走量数据用 TikHub/官方 API，不赌小号。
7. **不要重复启动**专用浏览器（先 `pgrep -f "Chrome for Testing"`，已在跑就别再起，否则多窗口互抢焦点）。
8. **camoufox 网页引擎登录后绝不 pkill**：登录态在 localStorage，必须让 `with` 块优雅退出才落盘；强杀 = 白登一次。

---

## 5. 排障

| 症状 | 处理 |
|---|---|
| `Multiple Browser Bridge profiles` | `opencli profile use dedicated`，或命令前加 `OPENCLI_PROFILE=<专用id>` |
| `Extension: not connected` / unstable | MV3 后台休眠，打开 `chrome-extension://<extId>/popup.html` 唤醒后重连 |
| 命令超时/挂起 | 多半是连错浏览器或扩展没连；重启 daemon `opencli daemon stop` 后重连专用浏览器扩展 |
| **用户日常 Chrome 打不开窗口** | 有无头系统 Chrome 残留占了 .app 单实例：`pkill -9 -f "Google Chrome.app/Contents/MacOS/Google Chrome --headless"` |
| 元宝返回空/401 | cookie 过期，有头重登一次 |

---

## 6. 验收（搭完逐项确认）

```bash
agent-reach doctor                                  # B 档渠道
opencli doctor                                      # daemon + 扩展
pgrep -f "Chrome for Testing"                       # 专用浏览器在跑(无头)
opencli twitter search "test" --limit 2 -f yaml     # D 档(需先登录小号)
opencli xiaohongshu note "<分享链接或URL>" -f yaml   # 小红书(需签名URL，或用 TikHub)
python3 yb.py "测试"                                 # C 档元宝
python3 kimi.py "测试"                               # C 档 Kimi(camoufox 网页直驱)
```
全绿即搭成。然后用 `ss / ssc / ssf` 跑一条真实检索，确认**全程无窗口、无焦点抢占、用户日常 Chrome 不受影响**。

---

## 7. 最小可用版（懒人路径）

只想要"免打扰 + 大部分能力"，最省事：
1. 装 **agent-reach**（B 档，覆盖 GitHub/油管/知乎/V2EX/语义搜索/网页转MD，零登录）。
2. 配 **知乎 MCP + TikHub 小红书 MCP**（A 档）。
3. 中文公众号生态加 **元宝本地代理**（C 档）；想要中文 AI 引擎再加 **Kimi（camoufox 网页直驱）**。
4. 只有确实要推特/Reddit/B站登录内容时，才搭 **专用无头浏览器 + OpenCLI**（D 档）。

A+B+C 就能覆盖绝大多数检索且全程零登录、零打扰；D 档按需再上。

---

## 8. 明确不纳入：ChatGPT-web（Cloudflare 反自动化，已踩坑）

实测确认**做不成"不打扰"版**，写出来避免你重复踩：
- chatgpt.com 用 **Cloudflare 人机验证（Turnstile）**，会识别"挂了调试端口 / 被自动化控制"的浏览器，弹"请验证您是真人"并清空页面 → camoufox、Chrome for Testing(无头+CDP) **全部被挡**。
- 登录还会因自动化环境被判可疑而**反复掉线**。
- 它**唯一**能用的方式是 **Computer Use 接管真屏幕 / 真 Chrome 扩展**——这恰恰违背"不打扰"原则（要占用真实鼠标键盘）。
- **结论**：放弃 ChatGPT-web。要"最强模型做深研"，用 **Kimi / DeepSeek / 秘塔 + 全平台检索**组合替代，质量够用且全程零打扰。

> 经验：**平台是否上 Cloudflare 这类人机验证，是能不能"无头不打扰"的分水岭**。Kimi/元宝/小红书/B站没有 → 能无头；ChatGPT 有 → 不行。接新平台前先用无头打开首页看看是否被"验证您是真人"挡，再决定值不值得做。

---

*本 Playbook 描述方法与架构，不含任何私密凭证；落地时各密钥/账号请在本机自行配置。*
