"""scripts/layer0_strategy.py — 第零層：LLM 決定今日篩選策略"""
import json, os, sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher    import get_taiex, get_news
from llm_client      import ask_strategy
from discord_notify  import send_strategy

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
TW   = timezone(timedelta(hours=8))

DEFAULT_STRATEGY = {
    "市場判斷": "LLM 分析失敗，使用預設條件",
    "偏重產業": [], "排除產業": [],
    "操作偏好": "短線", "風險等級": "中性",
    "篩選條件": {
        "最低漲幅": 2.0, "最低量比": 1.5,
        "均線條件": "站上MA5", "法人條件": "不限",
    },
}

def run():
    print("=== 第零層：策略分析 ===")
    taiex    = get_taiex()
    news_str = get_news()
    print(f"大盤：{taiex}")
    print(f"新聞筆數：{len(news_str.splitlines())}")

    strategy = ask_strategy(news_str, taiex) or DEFAULT_STRATEGY

    # 補齊欄位
    for k, v in DEFAULT_STRATEGY["篩選條件"].items():
        strategy.setdefault("篩選條件", {}).setdefault(k, v)

    # 把新聞清單和生成時間一起存進去，讓前端可以顯示
    news_list = [
        line[3:].strip()                          # 去掉 "1. " 前綴
        for line in news_str.splitlines()
        if line.strip() and line[0].isdigit()
    ]
    strategy['新聞']         = news_list
    strategy['generated_at'] = datetime.now(TW).strftime("%H:%M")
    strategy['taiex']        = taiex

    path = os.path.join(DATA, "today_strategy.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)

    print(f"策略：{strategy.get('市場判斷')}")
    send_strategy(strategy)

if __name__ == "__main__":
    run()
