# -*- coding: utf-8 -*-
# Kimi 一次性登录：有头 camoufox 打开 kimi.com，你用小号登录，登录态持久化到 ~/.kimi_profile
# 检测到登录(localStorage 出现 token 类键)后自动优雅关闭、落盘 cookie。
import os, time, sys
from camoufox.sync_api import Camoufox

PROFILE = os.path.expanduser("~/.kimi_profile")
os.makedirs(PROFILE, exist_ok=True)

# 登出态信号：有登录遮罩/弹窗，或侧边栏出现"登录以同步历史会话"
LOGGEDOUT_JS = """()=>{
  const modal=document.querySelector('.login-modal-mask,.login-modal-wechat,[class*="login-modal"],.wechat-login');
  const txt=document.body.innerText||'';
  return !!modal || txt.includes('登录以同步历史会话') || /(^|\\n)登录(\\n|$)/.test(txt);
}"""

def main():
    print("启动有头浏览器，打开 kimi.com … 请用小号【微信扫码】登录")
    with Camoufox(headless=False, persistent_context=True, user_data_dir=PROFILE,
                  os="macos", locale="zh-CN",
                  window=(1280, 900)) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.kimi.com", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        deadline = time.time() + 420   # 7 分钟
        saw_out = False; inn = 0; logged = False
        while time.time() < deadline:
            try:
                if page.is_closed():
                    print("窗口被关闭。"); break
                out = page.evaluate(LOGGEDOUT_JS)
                if out:
                    saw_out = True; inn = 0
                elif saw_out:             # 先见过登出态、现在登出信号消失 = 登录成功
                    inn += 1
                    if inn >= 3:          # 持续 ~6s
                        logged = True
                        print("✅ 检测到登录成功，停留 8 秒确保 localStorage 落盘，然后优雅关闭。")
                        time.sleep(8); break
            except Exception:
                pass
            time.sleep(2)
        # 不强杀；with 块自然退出 → cookie + localStorage 落盘
    print("✅ 登录态已写入 ~/.kimi_profile" if logged else "未确认登录(超时/手动关闭)，请重跑。")

if __name__ == "__main__":
    main()
