"""scripts/layer1_filter.py — 第一層：規則引擎掃全台股"""
import json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher   import get_all_stocks, get_moving_averages
from discord_notify import send_text

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

SECTOR_MAP = {
    "天然氣": ["9918","9931","9930","9957"],
    "能源":   ["1304","1305","6505","1312"],
    "半導體": ["2330","2303","2344","3711","6770","2379"],
    "電子":   ["2317","2382","3008","2357","2308"],
    "金融":   ["2882","2881","2886","2884","2891","2892"],
    "航運":   ["2603","2609","2615","5871","2618"],
    "散熱":   ["8044","3624","6121","3017"],
    "AI伺服器":["3515","6669","3231","5274"],
    "電信":   ["4904","3045","2412"],
    "生技":   ["4739","6547","4763","1786"],
}

def get_sector(code: str) -> str:
    for sector, codes in SECTOR_MAP.items():
        if code in codes:
            return sector
    return "其他"

def run():
    print("=== 第一層：規則引擎篩選 ===")

    # 讀今日策略
    strategy_path = os.path.join(DATA, "today_strategy.json")
    strategy = {}
    if os.path.exists(strategy_path):
        with open(strategy_path, encoding="utf-8") as f:
            strategy = json.load(f)

    cond    = strategy.get("篩選條件", {})
    prefer  = strategy.get("偏重產業", [])
    exclude = strategy.get("排除產業", [])
    min_chg = float(cond.get("最低漲幅", 2.0))
    min_turn = 30_000_000  # 最低成交金額 3000 萬元

    # 抓全市場報價
    all_stocks = get_all_stocks()
    print(f"取得 {len(all_stocks)} 筆股票")

    # 第一輪快速篩選
    passed = []
    for s in all_stocks:
        if s["price"] <= 0 or s["volume"] == 0:
            continue
        if s["turnover"] < min_turn:
            continue
        if s["change_pct"] < min_chg:
            continue
        sector = get_sector(s["code"])
        if exclude and sector in exclude:
            continue
        s["sector"] = sector
        passed.append(s)

    # 排序：偏重產業加權 + 漲幅
    passed.sort(key=lambda s: -(
        s["change_pct"] + (5 if s["sector"] in prefer else 0)
    ))

    # 取前 40 檔補均線
    candidates = []
    for s in passed[:40]:
        ma = get_moving_averages(s["code"])
        s.update(ma)

        ma_cond = cond.get("均線條件", "站上MA5")
        if ma_cond == "站上MA5" and s.get("ma5") and s["price"] < s["ma5"]:
            continue
        candidates.append(s)

    print(f"最終候選股：{len(candidates)} 檔")
    for c in candidates[:5]:
        print(f"  {c['name']}({c['code']}) {c['change_pct']:+.1f}% [{c['sector']}]")

    out = {
        "date":       datetime.today().strftime("%Y-%m-%d"),
        "count":      len(candidates),
        "candidates": candidates,
    }
    with open(os.path.join(DATA, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    send_text(f"📋 第一層完成：{len(all_stocks)} 檔 → **{len(candidates)} 檔**候選股，開始 LLM 分析...")

if __name__ == "__main__":
    run()
