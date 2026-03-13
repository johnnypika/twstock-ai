"""
scripts/discord_notify.py
Discord Webhook 推播工具
"""

import os
import requests
from datetime import datetime, timezone, timedelta

WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
TW = timezone(timedelta(hours=8))   # 台灣 UTC+8

def _now_tw():
    return datetime.now(TW).strftime("%Y-%m-%d %H:%M")

def _post(content: str) -> bool:
    if not WEBHOOK:
        print(f"[Discord] Webhook 未設定，訊息：{content[:60]}")
        return False
    try:
        r = requests.post(WEBHOOK, json={"content": content}, timeout=10)
        return r.status_code in (200, 204)
    except Exception as e:
        print(f"[Discord] 推播失敗: {e}")
        return False


def send_strategy(s: dict):
    if not s:
        return
    ts      = _now_tw()
    prefer  = "、".join(s.get("偏重產業", [])) or "不限"
    exclude = "、".join(s.get("排除產業", [])) or "無"
    cond    = s.get("篩選條件", {})
    msg = (
        f"## 📊 今日台股策略 `{ts}`\n"
        f"**市場判斷：** {s.get('市場判斷', 'N/A')}\n"
        f"**偏重：** {prefer}　**排除：** {exclude}\n"
        f"**操作偏好：** {s.get('操作偏好', 'N/A')}　**風險：** {s.get('風險等級', 'N/A')}\n"
        f"**條件：** 漲幅≥{cond.get('最低漲幅', 2)}%｜量比≥{cond.get('最低量比', 1.5)}｜{cond.get('均線條件', 'MA5')}"
    )
    _post(msg)


def send_recommendations(recs: list):
    if not recs:
        _post("⚠️ 今日無符合條件的推薦標的，建議觀望。")
        return

    ts   = _now_tw()
    rank = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    lines = [f"## 🏆 今日推薦入場清單 `{ts}`\n"]

    for i, r in enumerate(recs[:5]):
        lines += [
            f"{rank[i]} **{r['name']}（{r['code']}）**",
            f"> 進場：`{r['entry_low']}～{r['entry_high']} 元`",
            f"> 停利：`{r['take_profit']} 元`　停損：`{r['stop_loss']} 元`　風報比：{r.get('risk_reward', 'N/A')}",
            f"> {r.get('reason', '')}",
            "",
        ]

    lines.append("⚠️ AI 分析結果，非投資建議，請自行審慎判斷。")
    _post("\n".join(lines))


def send_alert(code: str, name: str, alert_type: str,
               price: float, target: float, pnl: float):
    emoji = "🟢" if alert_type == "take_profit" else "🔴"
    label = "停利" if alert_type == "take_profit" else "停損"
    ts    = _now_tw()
    msg   = (
        f"{emoji} **{label}警報 [{ts}]**\n"
        f"**{name}（{code}）**\n"
        f"> 現價：`{price}` 元　目標：`{target}` 元　損益：`{pnl:+.2f}%`\n"
        f"@here"
    )
    _post(msg)


def send_text(msg: str):
    _post(msg)
