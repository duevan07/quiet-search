#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可复用元宝查询：python3 yb.py "问题" [model]  → 输出干净答案文本"""
import sys, os, json, re, urllib.request

PROMPT = sys.argv[1] if len(sys.argv) > 1 else "你好"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "deepseek-v3-search"

body = json.dumps({"model": MODEL, "stream": True,
    "messages": [{"role": "user", "content": PROMPT}]}).encode()
req = urllib.request.Request("http://localhost:8000/v1/chat/completions",
    data=body, headers={"Authorization": "Bearer " + os.environ.get("YUANBAO_LOCAL_KEY", "sk-yuanbao-local"),
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

full = "".join(ans)
# 清洗元宝引用标记
full = re.sub(r"\[\]\(@mark_underline=\d+\)", "", full)
full = re.sub(r"\[citation:\d+\]", "", full)
print(full.strip())
