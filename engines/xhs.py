#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xhs.py — 小红书一行命令爬取（走 TikHub，已验证可用的接口，免去试错）
key 自动从 ~/.claude.json 的 reading-bot mcpServers.tikhub-* 读取，不硬编码。

用法：
  python3 xhs.py search "旅游搭子平台" [page]      # 搜笔记，按评论数排序
  python3 xhs.py comments "<分享链接或note_id>" [页数]  # 扒评论区（含楼中楼）
  python3 xhs.py note "<分享链接或note_id>"          # 笔记正文

为什么这个脚本存在：raw curl 要猜接口路径/参数会反复 404/400；
本脚本锁定「实测可用」的接口：
  - 搜索: app/search_notes
  - 评论: app_v2/get_note_comments（传 share_text 即可，自动处理 token）★关键
  - 短链解析: 跟随重定向取 note_id + xsec_token
"""
import sys, json, re, os, urllib.parse, urllib.request, urllib.error

API = "https://api.tikhub.io/api/v1/xiaohongshu"

def load_key():
    p = os.path.expanduser("~/.claude.json")
    try:
        d = json.load(open(p))
    except Exception:
        return os.environ.get("TIKHUB_KEY", "")
    found = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, dict) and "args" in v and isinstance(v["args"], list):
                    for a in v["args"]:
                        m = re.search(r"Bearer\s+([A-Za-z0-9+/=]+)", str(a))
                        if m and "tikhub" in json.dumps(v).lower():
                            found.append(m.group(1))
                walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(d)
    return found[0] if found else os.environ.get("TIKHUB_KEY", "")

KEY = load_key()
if not KEY:
    print("找不到 TikHub key（~/.claude.json 的 tikhub-* 或环境变量 TIKHUB_KEY）", file=sys.stderr)
    sys.exit(2)

def get(path, params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {KEY}",
        "User-Agent": "curl/8.4 xhs-cli",   # urllib 默认 UA 会被 403，必须带
    })
    try:
        return json.load(urllib.request.urlopen(req, timeout=40))
    except urllib.error.HTTPError as e:
        try: return {"_err": e.code, "_body": e.read().decode()[:300]}
        except Exception: return {"_err": e.code}
    except Exception as e:
        return {"_err": str(e)}

def resolve(link_or_id):
    """短链/链接 -> (note_id, xsec_token, share_text)。纯 note_id 直接返回。"""
    s = link_or_id.strip()
    if re.fullmatch(r"[0-9a-fA-F]{20,32}", s):
        return s, None, ""
    m = re.search(r"(xhslink\.com\S+|xiaohongshu\.com\S+)", s)
    share = m.group(1) if m else s
    if not share.startswith("http"): share = "http://" + share
    try:
        req = urllib.request.Request(share, headers={"User-Agent": "Mozilla/5.0 (iPhone)"})
        final = urllib.request.urlopen(req, timeout=30).geturl()
    except Exception:
        final = share
    nid = (re.search(r"/item/([0-9a-f]+)", final) or re.search(r"/explore/([0-9a-f]+)", final))
    tok = re.search(r"xsec_token=([^&]+)", final)
    return (nid.group(1) if nid else None,
            urllib.parse.unquote(tok.group(1)) if tok else None,
            link_or_id.strip())

def deepfind(o, key):
    if isinstance(o, dict):
        if key in o: return o[key]
        for v in o.values():
            r = deepfind(v, key)
            if r is not None: return r
    elif isinstance(o, list):
        for v in o:
            r = deepfind(v, key)
            if r is not None: return r
    return None

def cmd_search(kw, page="1"):
    d = get("app/search_notes", {"keyword": kw, "page": page})
    if d.get("_err"): print("接口错误:", d); return
    items = (((d.get("data") or {}).get("data") or {}).get("items")) or []
    rows = []
    for it in items:
        n = it.get("note") if isinstance(it, dict) else None
        if not isinstance(n, dict): continue
        rows.append({
            "title": n.get("title", "") or (n.get("desc", "") or "")[:30],
            "likes": n.get("liked_count"), "collected": n.get("collected_count"),
            "comments": n.get("comments_count"), "author": (n.get("user") or {}).get("nickname"),
            "id": n.get("id"), "desc": (n.get("desc", "") or "")[:120],
        })
    rows.sort(key=lambda r: int(r["comments"] or 0), reverse=True)
    print(f"# 搜「{kw}」第{page}页，{len(rows)}条（按评论数排序）\n")
    for r in rows:
        print(f"评论{r['comments']} 赞{r['likes']} 收藏{r['collected']} | {r['title']}  @{r['author']}  [id={r['id']}]")
        if r["desc"]: print(f"   {r['desc']}")

def cmd_comments(link, pages="1"):
    nid, tok, share = resolve(link)
    cursor = ""
    total = 0
    for p in range(int(pages)):
        d = get("app_v2/get_note_comments", {
            "note_id": nid or "", "share_text": share, "cursor": cursor, "sort_strategy": "default"})
        if d.get("_err"): print("接口错误:", d); return
        data = ((d.get("data") or {}).get("data") or {})
        if p == 0:
            print(f"# 评论区  note_id={nid}  一级评论{data.get('comment_count_l1')}  总{data.get('comment_count')}\n")
        comments = data.get("comments") or []
        for c in comments:
            total += 1
            au = (c.get("user") or {}).get("nickname", "?")
            print(f"[{c.get('like_count',0)}赞] {au}: {c.get('content','')}")
            for sc in (c.get("sub_comments") or []):
                sau = (sc.get("user") or {}).get("nickname", "?")
                print(f"    ↳[{sc.get('like_count',0)}赞] {sau}: {sc.get('content','')}")
        cursor = data.get("cursor") or ""
        if not data.get("has_more") or not cursor: break
    print(f"\n（本次输出 {total} 条一级评论）")

def cmd_note(link):
    nid, tok, share = resolve(link)
    d = get("app/get_note_info_v2", {"note_id": nid or "", "share_text": share})
    if d.get("_err"): print("接口错误:", d); return
    print("标题:", deepfind(d, "title"))
    print("正文:", deepfind(d, "desc"))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    cmd, arg = sys.argv[1], sys.argv[2]
    extra = sys.argv[3] if len(sys.argv) > 3 else None
    if cmd == "search": cmd_search(arg, extra or "1")
    elif cmd == "comments": cmd_comments(arg, extra or "1")
    elif cmd == "note": cmd_note(arg)
    else: print("未知命令，支持 search / comments / note"); sys.exit(1)
