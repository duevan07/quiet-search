#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""camoufox 无头兜底：读取一个已知 URL 的正文（公众号优先，通用页兜底）。
用法：python3 cam_fetch.py <url>   或   from cam_fetch import fetch_url_text
返回 (title, author, body_text)。仅做"渲染+抠正文"，不做搜索/提炼——那是元宝的活。
"""
import sys


def fetch_url_text(url, timeout_ms=45000, max_chars=0):
    """打开 url，返回 (title, author, body)。抗 Akamai/公众号墙用 camoufox。"""
    from camoufox.sync_api import Camoufox
    title = author = body = ""
    with Camoufox(headless=True, locale="zh-CN", os="macos") as b:
        pg = b.new_page(viewport={"width": 1440, "height": 2400})
        pg.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        pg.wait_for_timeout(2500)

        # 标题：公众号 #activity-name → og:title → h1 → <title>
        for sel in ["#activity-name", "meta[property='og:title']", "h1", "title"]:
            try:
                if sel.startswith("meta"):
                    title = (pg.get_attribute(sel, "content") or "").strip()
                else:
                    el = pg.query_selector(sel)
                    title = el.inner_text().strip() if el else ""
                if title:
                    break
            except Exception:
                pass

        # 作者/来源：公众号 #js_name → meta author
        for sel in ["#js_name", ".rich_media_meta_text", "meta[name='author']"]:
            try:
                if sel.startswith("meta"):
                    author = (pg.get_attribute(sel, "content") or "").strip()
                else:
                    el = pg.query_selector(sel)
                    author = el.inner_text().strip() if el else ""
                if author:
                    break
            except Exception:
                pass

        # 正文：公众号 #js_content → article → main → body
        for sel in ["#js_content", "article", "main"]:
            try:
                el = pg.query_selector(sel)
                if el:
                    body = el.inner_text().strip()
                if body:
                    break
            except Exception:
                pass
        if not body:
            try:
                body = pg.inner_text("body").strip()
            except Exception:
                body = ""

    if max_chars and len(body) > max_chars:
        body = body[:max_chars]
    return title, author, body


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 cam_fetch.py <url>", file=sys.stderr)
        sys.exit(1)
    t, a, txt = fetch_url_text(sys.argv[1])
    print("TITLE:", t)
    print("AUTHOR:", a)
    print("LEN:", len(txt))
    print("==== BODY ====")
    print(txt)
