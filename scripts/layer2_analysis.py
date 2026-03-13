"""scripts/layer2_analysis.py — 第二層：LLM 深度分析推薦"""
import json, os, sys, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

from llm_client     import analyze_stock
from discord_notify import send_recommendations, send_text

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

def run():
    print("=== 第二層：LLM 深度分析 ===")

    # 讀候選股與策略
    with open(os.path.join(DATA, "candidates.json"), encoding="utf-8") as f:
        candidates = json.load(f).get("candidates", [])
    with open(os.path.join(DATA, "today_strategy.json"), encoding="utf-8") as f:
        strategy = json.load(f)

    if not candidates:
        send_text("⚠️ 今日無候選股，建議觀望。")
        return

    print(f"分析 {len(candidates)} 檔候選股...")
    results, t0 = [], time.time()

    for i, stock in enumerate(candidates):
        print(f"[{i+1}/{len(candidates)}] {stock['name']}({stock['code']})")
        result = analyze_stock(stock, strategy)
        if not result:
            continue

        score = result.get("信心分數", 0)
        print(f"  推薦:{result.get('推薦')} 分:{score} {result.get('理由','')[:30]}")

        if result.get("推薦") and score >= 6:
            results.append({
                "code":        stock["code"],
                "name":        stock["name"],
                "sector":      stock.get("sector", ""),
                "change_pct":  stock.get("change_pct", 0),
                "entry_low":   result.get("進場區間低", round(stock["price"] * 0.98, 1)),
                "entry_high":  result.get("進場區間高", round(stock["price"] * 1.01, 1)),
                "take_profit": result.get("停利目標",   round(stock["price"] * 1.08, 1)),
                "stop_loss":   result.get("停損點",      round(stock["price"] * 0.94, 1)),
                "risk_reward": result.get("風報比", "N/A"),
                "trade_type":  result.get("操作屬性", "短線"),
                "reason":      result.get("理由", ""),
                "score":       score,
            })

        # 找到 5 檔就可以停了
        if len(results) >= 5 and i >= len(candidates) // 2:
            break

        # Groq 速率限制保護：每次呼叫後稍作等待
        time.sleep(1)

    results.sort(key=lambda x: -x["score"])
    top5    = results[:5]
    elapsed = round((time.time() - t0) / 60, 1)
    print(f"分析完成，{elapsed} 分鐘，推薦 {len(top5)} 檔")

    out = {
        "date":            datetime.today().strftime("%Y-%m-%d"),
        "generated_at":    datetime.now().strftime("%H:%M:%S"),
        "strategy":        strategy,
        "recommendations": top5,
        "analyzed":        i + 1,
        "total_time_min":  elapsed,
    }
    with open(os.path.join(DATA, "recommendations.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    send_recommendations(top5)

if __name__ == "__main__":
    run()
