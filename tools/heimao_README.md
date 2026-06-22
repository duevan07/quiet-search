# 黑猫投诉 只读查询 CLI（heimao_cli.py）

本地命令行工具，查询 [黑猫投诉](https://tousu.sina.com.cn/) 的**公开数据**。

- ✅ 只读：搜商家、查服务、看投诉流、榜单
- ❌ 不登录、不提交投诉、不绕验证码、不做批量爬取
- 纯 Python 3 标准库，单文件，开箱即用

## 安装 / 运行

无需安装依赖（只用标准库）。直接：

```bash
python3 heimao_cli.py <命令> [参数] [--json]
```

建议每次查询条数 `-n` 不要太大、不要高频请求（仅供研究/风控参考）。

## 命令

| 命令 | 说明 | 示例 |
|---|---|---|
| `company <关键词>` | 搜商家 | `python3 heimao_cli.py company 京东 -n 3` |
| `services <couid>` | 查商家服务/子商家 | `python3 heimao_cli.py services 1003608` |
| `complaints --sid <sid>` | 查某服务下的投诉 | `python3 heimao_cli.py complaints --sid 31944 -n 5` |
| `complaints --couid <couid>` | 查某商家下的投诉 | `python3 heimao_cli.py complaints --couid 5650743478 -n 5` |
| `feed` | 首页公开投诉流 | `python3 heimao_cli.py feed -n 10` |
| `fields` | 榜单领域列表 | `python3 heimao_cli.py fields` |
| `rank` | 榜单（红/黑/回复榜） | `python3 heimao_cli.py rank --type black --span week --field 6` |
| `rise` | 一周投诉飙升榜 | `python3 heimao_cli.py rise --field 0` |
| `search <关键词>` | **近期公开流本地过滤**（非站内全文搜索，不登录） | `python3 heimao_cli.py search 退款 --pages 5` |

- `rank --type`：`red`（红榜）/ `black`（黑榜）/ `reply`（回复榜）
- `rank --span`：`week` / `month` / `season`
- `rank --field` / `rise --field`：领域 id，用 `fields` 命令查（如 6=购物平台、28=旅游出行住宿）
- `complaints --type`：默认 `1`（全部），可按需调整
- **任意命令加 `--json`** 输出原始 JSON，方便脚本二次分析

## 典型工作流

先用 `company` 找到商家拿 `sid`/`couid`，再用 `complaints` 拉它的投诉原文：

```bash
python3 heimao_cli.py company 飞猪 -n 5
python3 heimao_cli.py complaints --sid <上一步的sid> -n 20 --json > feizhu.json
```

或按领域看榜单找选题：

```bash
python3 heimao_cli.py fields
python3 heimao_cli.py rank --type black --span week --field 28   # 旅游出行住宿黑榜
```

## 关于登录与搜索（重要）

- 本工具**全程不登录、不扫码、不保存 cookie**。上面所有命令都走公开接口完成。
- 黑猫的**站内全文搜索页**（`tousu.sina.com.cn/index/search`）有登录墙——**本工具按只读原则不实现它**，也不会要求你扫码。
- `search` 命令是**降级方案**：分页读取公开投诉流（`feed`）后在本地按 标题/摘要/投诉对象/诉求/问题 过滤关键词。它**只能命中最近出现在公开流里的投诉**，不是站内历史全文检索——命中与否取决于关键词近期是否进入公开流。
- 若任何接口返回需要登录/验证码，工具会直接报错跳过，**不会引导登录**。

## 状态码

`1` 通过审核 · `3` 待分配 · `4` 处理中 · `6` 已回复 · `7` 已完成 · `8` 已关闭

## 输出字段

- **company**：商家名、couid/uid、sid、总投诉、30天投诉、已回复、已完成、链接
- **complaints / feed**：日期、投诉编号(sn)、状态、投诉对象、诉求(appeal)、问题(issue)、标题、链接
- `//tousu.sina.com.cn/...` 形式的链接会自动补全为 `https://`

## 实现说明

- 公开接口（`main_search` / `rel_service` / `rank_fields` / `rank` / `riserank_list`）无需签名。
- 投诉类接口（`service_complaints` / `received_complaints` / `index/feed`）需签名参数：
  - `ts` = 当前毫秒时间戳；`rs` = 16 位随机字母数字
  - `signature = sha256("".join(sorted([ts, rs, salt, <id>, type, page_size, page])))`
  - `index/feed` 无 `id`，签名用 `[ts, rs, salt, type, page_size, page]`
- 如接口/签名变更导致报错，需重新打开网页与前端 JS 核对最新 API 后调整。

## 免责

仅查询公开展示数据，用于研究与风险参考；请遵守网站条款，勿高频/批量抓取。
