"""
scripts/layer3_monitor.py — 第三層：持倉監控
每次由 GitHub Actions 每 5 分鐘觸發，執行一輪檢查
"""
import json, os, sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher   import get_stock_info
from discord_notify import send_alert
from gist_sync      import push

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
TW   = timezone(timedelta(hours=8))

def run():
    port_path = os.path.join(DATA, "portfolio.json")
    if not os.path.exists(port_path):
        print("portfolio.json 不存在，跳過監控")
        return

    with open(port_path, encoding="utf-8") as f:
        portfolio = json.load(f)

    if not portfolio:
        print("持倉清單為空，跳過")
        return

    print(f"監控 {len(portfolio)} 筆持倉...")
    any_updated   = False
    alert_updated = False
    now_str       = datetime.now(TW).strftime("%H:%M")

    for pos in portfolio:
        code = pos["code"]
        name = pos["name"]
        cost = float(pos["cost"])
        tp   = float(pos["take_profit"])
        sl   = float(pos["stop_loss"])

        info = get_stock_info(code)
        if not info:
            print(f"  {name}({code}) 取價失敗")
            continue

        price      = info.get("price")
        prev_close = info.get("prev_close")

        if not price:
            print(f"  {name}({code}) 無即時成交價")
            continue

        # 成本損益（相對買入成本）
        cost_pnl_pct = (price - cost) / cost * 100

        # 今日損益（相對昨收價，即今日平盤）
        today_pnl_pct = None
        if prev_close:
            today_pnl_pct = (price - prev_close) / prev_close * 100

        pos["current_price"]  = price
        pos["prev_close"]     = prev_close
        pos["pnl_pct"]        = round(cost_pnl_pct, 2)
        pos["today_pnl_pct"]  = round(today_pnl_pct, 2) if today_pnl_pct is not None else None
        pos["last_updated"]   = now_str
        any_updated = True

        print(
            f"  {name}({code}) "
            f"現價:{price} "
            f"成本損益:{cost_pnl_pct:+.2f}% "
            f"今日:{today_pnl_pct:+.2f}%" if today_pnl_pct else f"今日:N/A"
        )

        # 停利警報
        if price >= tp and not pos.get("alerted_tp"):
            send_alert(code, name, "take_profit", price, tp, cost_pnl_pct)
            pos["alerted_tp"] = True
            alert_updated = True

        # 停損警報
        if price <= sl and not pos.get("alerted_sl"):
            send_alert(code, name, "stop_loss", price, sl, cost_pnl_pct)
            pos["alerted_sl"] = True
            alert_updated = True

    if any_updated:
        with open(port_path, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        push()
        print(f"持倉現價已更新並同步 Gist（有警報:{alert_updated}）")

if __name__ == "__main__":
    run()
