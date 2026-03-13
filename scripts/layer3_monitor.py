"""
scripts/layer3_monitor.py — 第三層：持倉監控
每次由 GitHub Actions 每 5 分鐘觸發，執行一輪檢查
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher   import get_stock_price
from discord_notify import send_alert, send_text
from gist_sync      import push

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

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
    updated = False

    for pos in portfolio:
        code  = pos["code"]
        name  = pos["name"]
        cost  = float(pos["cost"])
        tp    = float(pos["take_profit"])
        sl    = float(pos["stop_loss"])

        price = get_stock_price(code)
        if price is None:
            print(f"  {name}({code}) 取價失敗")
            continue

        pnl = (price - cost) / cost * 100
        pos["current_price"] = price
        pos["pnl_pct"]       = round(pnl, 2)
        print(f"  {name}({code}) 現價:{price} 損益:{pnl:+.2f}%")

        # 停利
        if price >= tp and not pos.get("alerted_tp"):
            send_alert(code, name, "take_profit", price, tp, pnl)
            pos["alerted_tp"] = True
            updated = True

        # 停損
        if price <= sl and not pos.get("alerted_sl"):
            send_alert(code, name, "stop_loss", price, sl, pnl)
            pos["alerted_sl"] = True
            updated = True

    if updated:
        with open(port_path, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        push()  # 立即同步回 Gist
        print("持倉狀態已更新並同步")

if __name__ == "__main__":
    run()
