"""scripts/layer0_strategy.py — 第零層：LLM 決定今日篩選策略"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher    import get_taiex, get_news
from llm_client      import ask_strategy
from discord_notify  import send_strategy, send_text

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

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
    taiex = get_taiex()
    news  = get_news()
    print(f"大盤：{taiex}")
    print(f"新聞筆數：{len(news.splitlines())}")

    strategy = ask_strategy(news, taiex) or DEFAULT_STRATEGY

    # 補齊欄位
    for k, v in DEFAULT_STRATEGY["篩選條件"].items():
        strategy.setdefault("篩選條件", {}).setdefault(k, v)

    path = os.path.join(DATA, "today_strategy.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)

    print(f"策略：{strategy.get('市場判斷')}")
    send_strategy(strategy)

if __name__ == "__main__":
    run()
