#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可复用元宝查询：python3 yb.py "问题" [model]  → 输出干净答案文本。
元宝 = 会搜索会提炼的主力；若 prompt 含 URL 且元宝彻底失败（5xx/崩），自动用
camoufox 无头读取该 URL 正文兜底（仅"读已知链接"这一档；搜索/提炼无法兜底）。
密钥走环境变量 YUANBAO_LOCAL_KEY（默认占位符，绝不硬编码真实密钥）。"""
import sys, os, json, re, time, urllib.request, urllib.error

PROMPT = sys.argv[1] if len(sys.argv) > 1 else "你好"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "deepseek-v3-search"

MAX_RETRIES = 3
RETRY_DELAY = 8  # 服务重新捕获 headers 需要几秒，稍等一下

URL_RE = re.compile(r'https?://[^\s"\'<>）)】]+')


def do_query():
    body = json.dumps({"model": MODEL, "stream": True,
        "messages": [{"role": "user", "content": PROMPT}]}).encode()
    req = urllib.request.Request("http://localhost:8000/v1/chat/completions",
        data=body, headers={
            "Authorization": "Bearer " + os.environ.get("YUANBAO_LOCAL_KEY", "sk-yuanbao-local"),
            "Content-Type": "application/json"})
    ans = []
    with urllib.request.urlopen(req, timeout=240) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            p = line[5:].strip()
            if p in ("[DONE]", ""):
                continue
            try:
                c = json.loads(p)["choices"][0]["delta"].get("content", "")
            except Exception:
                continue
            if not c:
                continue
            try:
                obj = json.loads(c)
                if isinstance(obj, dict) and obj.get("type") == "text" and obj.get("msg"):
                    ans.append(obj["msg"])
            except Exception:
                ans.append(c)
    return "".join(ans)


def camoufox_fallback(urls):
    """元宝挂了且 prompt 里有 URL → 抠正文兜底。返回拼好的文本或 None。"""
    try:
        from cam_fetch import fetch_url_text
    except Exception as e:
        print(f"[yb] camoufox 兜底不可用：{e}", file=sys.stderr)
        return None
    parts = []
    for u in urls:
        try:
            t, a, txt = fetch_url_text(u)
            if txt:
                head = f"【标题】{t}".rstrip()
                if a:
                    head += f"\n【来源】{a}"
                parts.append(f"{head}\n\n{txt}")
        except Exception as e:
            print(f"[yb] camoufox 读取失败 {u}：{e}", file=sys.stderr)
    return "\n\n---\n\n".join(parts) if parts else None


full = None
yuanbao_err = None
for attempt in range(1, MAX_RETRIES + 1):
    try:
        full = do_query()
        break
    except urllib.error.HTTPError as e:
        yuanbao_err = e
        if e.code == 500 and attempt < MAX_RETRIES:
            print(f"[yb] 500 session失效，{RETRY_DELAY}s后重试({attempt}/{MAX_RETRIES})…", file=sys.stderr)
            time.sleep(RETRY_DELAY)
        elif attempt < MAX_RETRIES:
            print(f"[yb] HTTP {e.code}，{RETRY_DELAY}s后重试({attempt}/{MAX_RETRIES})…", file=sys.stderr)
            time.sleep(RETRY_DELAY)
    except Exception as e:
        yuanbao_err = e
        if attempt < MAX_RETRIES:
            print(f"[yb] 请求失败({e})，{RETRY_DELAY}s后重试({attempt}/{MAX_RETRIES})…", file=sys.stderr)
            time.sleep(RETRY_DELAY)

# 元宝彻底失败 → 若 prompt 含 URL，camoufox 兜底读正文
if full is None:
    urls = URL_RE.findall(PROMPT)
    if urls:
        print(f"[yb] 元宝不可用({yuanbao_err})，改用 camoufox 兜底读取 {len(urls)} 个 URL 正文…", file=sys.stderr)
        fb = camoufox_fallback(urls)
        if fb:
            print("[yb] ⚠️ 以下为 camoufox 抠取的原始正文（非元宝综合/搜索结果）。", file=sys.stderr)
            print(fb.strip())
            sys.exit(0)
    print(f"[yb] 失败且无可兜底：{yuanbao_err}", file=sys.stderr)
    sys.exit(1)

# 清洗元宝引用标记
full = re.sub(r"\[\]\(@mark_underline=\d+\)", "", full)
full = re.sub(r"\[citation:\d+\]", "", full)
print(full.strip())
