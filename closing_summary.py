"""scripts/closing_summary.py — 收盤後推播盤後總結"""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from discord_notify import send_text

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

def run():
    today = datetime.today().strftime("%Y-%m-%d")
    lines = [f"## 📋 盤後總結 `{today}`\n"]

    # 持倉損益
    port_path = os.path.join(DATA, "portfolio.json")
    if os.path.exists(port_path):
        with open(port_path, encoding="utf-8") as f:
            portfolio = json.load(f)
        if portfolio:
            lines.append("**今日持倉損益：**")
            for p in portfolio:
                chg = p.get("pnl_pct", 0)
                arrow = "🔺" if chg > 0 else ("🔻" if chg < 0 else "➖")
                lines.append(f"> {arrow} {p['name']}（{p['code']}）`{chg:+.2f}%`")
            lines.append("")

    # 今日推薦回顧
    rec_path = os.path.join(DATA, "recommendations.json")
    if os.path.exists(rec_path):
        with open(rec_path, encoding="utf-8") as f:
            rec_data = json.load(f)
        recs = rec_data.get("recommendations", [])
        if recs:
            lines.append("**今日推薦回顧：**")
            for r in recs:
                lines.append(f"> {r['name']}（{r['code']}）進場區間 {r['entry_low']}～{r['entry_high']}")
            lines.append("")

    lines.append("⚠️ AI 分析結果，非投資建議，請自行審慎判斷。")
    lines.append("🔕 今日監控結束，明日 08:00 自動重啟。")
    send_text("\n".join(lines))

if __name__ == "__main__":
    run()
