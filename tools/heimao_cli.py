#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
heimao_cli.py — 黑猫投诉 只读查询 CLI（公开数据，不登录/不投诉/不绕验证码/不批量爬）

只用 Python 3 标准库。单文件直接运行。
    python3 heimao_cli.py company 京东 -n 3
    python3 heimao_cli.py services 1003608
    python3 heimao_cli.py complaints --sid 31944 -n 5
    python3 heimao_cli.py complaints --couid 5650743478 -n 5
    python3 heimao_cli.py feed -n 5
    python3 heimao_cli.py fields
    python3 heimao_cli.py rank --type black --span week --field 6
    python3 heimao_cli.py rise --field 0
任意命令加 --json 输出原始 JSON。
"""

import sys, time, json, random, string, hashlib, argparse
import urllib.request, urllib.parse, urllib.error

BASE = "https://tousu.sina.com.cn"
SALT = "$d6eb7ff91ee257475%"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 投诉状态码映射
STATUS = {1: "通过审核", 3: "待分配", 4: "处理中", 6: "已回复", 7: "已完成", 8: "已关闭"}


class HeimaoError(Exception):
    pass


def _fmt_date(v):
    """feed 的 timestamp 是 unix 秒，转成 YYYY-MM-DD；已是日期串则原样返回。"""
    s = str(v) if v is not None else ""
    if s.isdigit() and len(s) == 10:
        try:
            return time.strftime("%Y-%m-%d", time.localtime(int(s)))
        except Exception:
            return s
    return s


def _fix_url(u):
    if not u:
        return u
    if u.startswith("//"):
        return "https:" + u
    return u


def _get(path, params=None):
    """GET 一个接口，返回 result.data；接口报错抛 HeimaoError。"""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://tousu.sina.com.cn/",
        "Accept": "application/json, text/plain, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HeimaoError("HTTP %s：%s" % (e.code, path))
    except Exception as e:
        raise HeimaoError("请求失败：%s（%s）" % (e, path))
    try:
        obj = json.loads(raw)
    except Exception:
        raise HeimaoError("返回非 JSON（可能被风控/需验证码）：%s" % raw[:120])
    res = obj.get("result", {})
    st = res.get("status", {})
    if st.get("code") != 0:
        raise HeimaoError("接口返回错误 code=%s msg=%s（%s）"
                          % (st.get("code"), st.get("msg"), path))
    return res.get("data")


def _sign(parts):
    """signature = sha256("".join(sorted([...]))) 全部为字符串。"""
    parts = [str(p) for p in parts]
    return hashlib.sha256("".join(sorted(parts)).encode("utf-8")).hexdigest()


def _signed_params(type_, page_size, page, id_val=None):
    """构造带 ts/rs/signature 的签名参数。id_val=None 时（feed）不含 id。"""
    ts = str(int(time.time() * 1000))
    rs = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    type_, page_size, page = str(type_), str(page_size), str(page)
    if id_val is None:
        parts = [ts, rs, SALT, type_, page_size, page]
        p = {"type": type_, "page_size": page_size, "page": page}
    else:
        id_val = str(id_val)
        parts = [ts, rs, SALT, id_val, type_, page_size, page]
        p = {"type": type_, "page_size": page_size, "page": page}
    p["ts"] = ts
    p["rs"] = rs
    p["signature"] = _sign(parts)
    return p


# ---------------- 各命令实现 ----------------

def cmd_company(args):
    data = _get("/api/company/main_search",
                {"keyword": args.keyword, "page": 1, "page_size": args.n})
    lists = (data or {}).get("lists", []) if isinstance(data, dict) else (data or [])
    if args.json:
        return lists
    rows = []
    for c in lists:
        rows.append({
            "商家": c.get("title"),
            "couid/uid": c.get("uid"),
            "sid": c.get("sid"),
            "总投诉": c.get("valid_amt"),
            "30天": c.get("valid30d"),
            "已回复": c.get("replied_amt"),
            "已完成": c.get("completed_amt"),
            "链接": _fix_url(c.get("url")),
        })
    return rows


def cmd_services(args):
    data = _get("/api/company/rel_service", {"couid": args.couid})
    svcs = data or []
    if args.json:
        return svcs
    rows = []
    for s in svcs:
        rows.append({
            "服务": s.get("name"),
            "couid": args.couid,
            "sid": s.get("sid"),
            "总投诉": s.get("valid_amt"),
            "30天": s.get("valid30d"),
            "已回复": s.get("replied_amt"),
            "已完成": s.get("completed_amt"),
        })
    return rows


def cmd_complaints(args):
    if not args.sid and not args.couid:
        raise HeimaoError("complaints 需要 --sid 或 --couid 之一")
    if args.sid and args.couid:
        raise HeimaoError("--sid 与 --couid 只能给一个")
    if args.sid:
        path = "/api/company/service_complaints"
        idp = {"sid": str(args.sid)}
        idv = args.sid
    else:
        path = "/api/company/received_complaints"
        idp = {"couid": str(args.couid)}
        idv = args.couid
    p = _signed_params(args.type, args.n, 1, id_val=idv)
    p.update(idp)
    data = _get(path, p)
    comps = (data or {}).get("complaints", []) if isinstance(data, dict) else (data or [])
    if args.json:
        return comps
    rows = []
    for c in comps:
        m = c.get("main", c)
        rows.append({
            "日期": _fmt_date(m.get("timestamp")),
            "编号": m.get("sn"),
            "状态": STATUS.get(m.get("status"), m.get("status")),
            "投诉对象": m.get("cotitle"),
            "诉求": m.get("appeal"),
            "问题": m.get("issue"),
            "标题": m.get("title"),
            "链接": _fix_url(m.get("url")),
        })
    return rows


def cmd_feed(args):
    p = _signed_params(args.type, args.n, 1, id_val=None)
    data = _get("/api/index/feed", p)
    if isinstance(data, dict):
        items = data.get("lists") or data.get("complaints") or []
    else:
        items = data or []
    if args.json:
        return items
    rows = []
    for c in items:
        m = c.get("main", c)
        rows.append({
            "日期": _fmt_date(m.get("timestamp")),
            "编号": m.get("sn"),
            "状态": STATUS.get(m.get("status"), m.get("status")),
            "投诉对象": m.get("cotitle"),
            "标题": m.get("title"),
            "链接": _fix_url(m.get("url")),
        })
    return rows


def cmd_search(args):
    """近期公开流过滤（非站内全文搜索，不登录）：分页读 index/feed，本地按标题/摘要/投诉对象匹配关键词。"""
    sys.stderr.write(
        "ℹ 这是「近期公开投诉流」的本地关键词过滤，不是黑猫站内全文搜索"
        "（站内全文搜索需登录，已按只读原则跳过）。只能命中最近出现在公开流里的投诉。\n")
    kw = args.keyword
    found, seen = [], set()
    for page in range(1, args.pages + 1):
        p = _signed_params(args.type, 20, page, id_val=None)
        try:
            data = _get("/api/index/feed", p)
        except HeimaoError as e:
            sys.stderr.write("✗ 第%d页失败：%s\n" % (page, e))
            break
        items = (data.get("lists") or data.get("complaints") or []) if isinstance(data, dict) else (data or [])
        if not items:
            break
        for c in items:
            m = c.get("main", c)
            blob = " ".join(str(m.get(k, "")) for k in ("title", "summary", "cotitle", "appeal", "issue"))
            if kw in blob:
                sn = m.get("sn")
                if sn in seen:
                    continue
                seen.add(sn)
                found.append({
                    "日期": _fmt_date(m.get("timestamp")),
                    "编号": m.get("sn"),
                    "状态": STATUS.get(m.get("status"), m.get("status")),
                    "投诉对象": m.get("cotitle"),
                    "标题": m.get("title"),
                    "链接": _fix_url(m.get("url")),
                })
                if len(found) >= args.n:
                    return found
        time.sleep(0.4)  # 温和限速
    return found


def cmd_fields(args):
    data = _get("/api/top_rank/rank_fields")
    if args.json:
        return data
    return [{"field": f.get("id"), "领域": f.get("title")} for f in (data or [])]


def cmd_rank(args):
    data = _get("/api/top_rank/rank",
                {"span": args.span, "field": args.field,
                 "type": args.type, "date": int(time.time())})
    if args.json:
        return data
    rows = []
    for i, c in enumerate(data or [], 1):
        rows.append({"名次": c.get("rank", i), "商家": c.get("title"),
                     "sid": c.get("sid"), "uid": c.get("uid")})
    return rows


def cmd_rise(args):
    data = _get("/api/top_rank/riserank_list", {"field": args.field})
    if args.json:
        return data
    rows = []
    for c in (data or []):
        rows.append({"名次": c.get("rank"), "商家": c.get("title"),
                     "sid": c.get("sid"), "新增投诉": c.get("valid_diff")})
    return rows


# ---------------- 输出 ----------------

def render(rows):
    if isinstance(rows, (dict, list)) and not (isinstance(rows, list) and rows and isinstance(rows[0], dict)):
        # 非"字典列表"，直接 JSON 兜底
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("（无数据）")
        return
    for i, r in enumerate(rows, 1):
        print("─" * 60)
        print("[%d]" % i)
        for k, v in r.items():
            if v is None or v == "":
                continue
            print("  %-9s %s" % (k + "：", v))
    print("─" * 60)
    print("共 %d 条" % len(rows))


def build_parser():
    p = argparse.ArgumentParser(
        prog="heimao_cli.py",
        description="黑猫投诉 只读查询 CLI（公开数据）")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_json(sp):
        sp.add_argument("--json", action="store_true", help="输出原始 JSON")

    sp = sub.add_parser("company", help="搜商家")
    sp.add_argument("keyword")
    sp.add_argument("-n", type=int, default=10, help="条数（默认10）")
    add_json(sp); sp.set_defaults(func=cmd_company)

    sp = sub.add_parser("services", help="查商家服务/子商家")
    sp.add_argument("couid")
    add_json(sp); sp.set_defaults(func=cmd_services)

    sp = sub.add_parser("complaints", help="查某商家/服务下的投诉")
    sp.add_argument("--sid")
    sp.add_argument("--couid")
    sp.add_argument("-n", type=int, default=10, help="条数（默认10）")
    sp.add_argument("--type", default="1", help="类型过滤（默认1=全部）")
    add_json(sp); sp.set_defaults(func=cmd_complaints)

    sp = sub.add_parser("feed", help="查首页公开投诉流")
    sp.add_argument("-n", type=int, default=10)
    sp.add_argument("--type", default="1")
    add_json(sp); sp.set_defaults(func=cmd_feed)

    sp = sub.add_parser("search", help="近期公开流本地过滤（非站内全文搜索，不登录）")
    sp.add_argument("keyword")
    sp.add_argument("-n", type=int, default=20, help="最多返回命中数（默认20）")
    sp.add_argument("--pages", type=int, default=5, help="扫描公开流页数（默认5，温和限速）")
    sp.add_argument("--type", default="1")
    add_json(sp); sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("fields", help="查榜单领域")
    add_json(sp); sp.set_defaults(func=cmd_fields)

    sp = sub.add_parser("rank", help="查榜单")
    sp.add_argument("--type", default="black", choices=["red", "black", "reply"])
    sp.add_argument("--span", default="week", choices=["week", "month", "season"])
    sp.add_argument("--field", default="6")
    add_json(sp); sp.set_defaults(func=cmd_rank)

    sp = sub.add_parser("rise", help="查一周投诉飙升榜")
    sp.add_argument("--field", default="0")
    add_json(sp); sp.set_defaults(func=cmd_rise)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        out = args.func(args)
    except HeimaoError as e:
        print("✗ %s" % e, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        render(out)


if __name__ == "__main__":
    main()
