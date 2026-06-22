#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Kimi 一行命令（camoufox 无头 + 持久登录 ~/.kimi_profile）。同 yb.py 风格。
#   python3 ~/video-factory/kimi.py "你的问题"
# 未登录请先跑：python3 ~/video-factory/kimi_login.py（微信扫码，小号）
import os, sys, time
from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/.kimi_profile")

def ask(q, timeout=150):
    with Camoufox(headless=True, persistent_context=True, user_data_dir=PROFILE,
                  os="macos", locale="zh-CN", window=(1440, 1000)) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.kimi.com", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(".chat-input-editor", timeout=30000)
        page.wait_for_timeout(2500)
        if page.evaluate("()=>document.body.innerText.includes('登录以同步历史会话')"):
            raise SystemExit("未登录，请先运行 kimi_login.py（微信扫码）")

        # 发送：关遮罩 + 焦点输入框 + execCommand 触发 Vue 输入事件 + 键盘 Enter（遮罩拦不住键盘）
        page.keyboard.press("Escape")
        page.evaluate("""(t)=>{
            document.querySelectorAll('.mask,.login-modal-mask').forEach(m=>m.style.display='none');
            const e=document.querySelector('.chat-input-editor')||document.querySelector('[contenteditable=true]');
            e.focus(); document.execCommand('insertText', false, t);
            e.dispatchEvent(new InputEvent('input',{bubbles:true,data:t,inputType:'insertText'}));
        }""", q)
        page.wait_for_timeout(700)
        page.keyboard.press("Enter")

        # 答案在最后一个 .markdown；轮询到稳定（~4.5s 不变）
        def answer():
            return page.evaluate("""()=>{const n=document.querySelectorAll('.markdown');
                return n.length?(n[n.length-1].innerText||'').trim():'';}""")
        t0 = time.time(); last = ""; stable = 0
        while time.time() - t0 < timeout:
            page.wait_for_timeout(1500)
            cur = answer()
            if cur and cur == last:
                stable += 1
                if stable >= 3:
                    break
            else:
                stable = 0
            last = cur
        return last or "(未取到答案，可能网页结构变化或被风控；可重跑或检查登录)"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 kimi.py \"问题\""); sys.exit(1)
    print(ask(" ".join(sys.argv[1:])))
