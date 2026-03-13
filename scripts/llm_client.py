"""
scripts/llm_client.py
Groq API 統一介面（LLaMA 3.3 70B，每日 500K tokens 免費）
"""

import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
MODEL  = "llama-3.3-70b-versatile"


def _chat(messages: list, temperature: float = 0.3, max_tokens: int = 1024) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"[Groq] 呼叫失敗: {e}")
        return ""


def _parse_json(text: str) -> dict:
    """從回應中安全解析 JSON"""
    try:
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return {}


def ask_strategy(news: str, taiex: dict) -> dict:
    """第零層：根據新聞與大盤產生今日策略 JSON"""
    taiex_str = (
        f"昨日加權指數 {taiex.get('close', 'N/A')} 點，"
        f"漲跌 {taiex.get('change', 0):+.0f} 點（{taiex.get('change_pct', 0):+.2f}%）"
        if taiex else "大盤資料無法取得"
    )

    prompt = f"""你是台股量化投資策略師。請根據以下資訊，輸出今日選股策略的 JSON。
只輸出 JSON，不要任何解釋文字。

大盤：{taiex_str}

今日財經新聞：
{news}

輸出格式：
{{
  "市場判斷": "一句話",
  "偏重產業": ["產業1"],
  "排除產業": ["產業A"],
  "操作偏好": "短線",
  "風險等級": "中性",
  "篩選條件": {{
    "最低漲幅": 2.0,
    "最低量比": 1.5,
    "均線條件": "站上MA5",
    "法人條件": "不限"
  }}
}}"""

    resp = _chat([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=512)
    return _parse_json(resp)


def analyze_stock(stock: dict, strategy: dict) -> dict:
    """第二層：深度分析單一候選股"""
    ma_status = "無均線資料"
    if stock.get("ma5") and stock.get("ma20"):
        p = stock["price"]
        if p > stock["ma5"] > stock["ma20"]:
            ma_status = "均線多頭排列"
        elif p < stock["ma5"]:
            ma_status = "股價跌破 MA5"
        else:
            ma_status = "均線整理中"

    prompt = f"""你是台股投資顧問。以 JSON 格式分析以下個股，只輸出 JSON。

市場偏好：{strategy.get('操作偏好','短線')}，風險：{strategy.get('風險等級','中性')}

個股資料：
- {stock['name']}（{stock['code']}）現價 {stock['price']} 元
- 今日漲幅 {stock.get('change_pct', 0):+.2f}%
- 均線狀態：{ma_status}（MA5={stock.get('ma5','N/A')}，MA20={stock.get('ma20','N/A')}）
- 外資近3日：{stock.get('foreign_net', 0):+,} 張
- 投信近3日：{stock.get('investment_trust_net', 0):+,} 張

輸出格式：
{{
  "推薦": true,
  "信心分數": 8,
  "進場區間低": 0,
  "進場區間高": 0,
  "停利目標": 0,
  "停損點": 0,
  "操作屬性": "短線",
  "理由": "一句話"
}}"""

    resp = _chat([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=256)
    result = _parse_json(resp)

    # 計算風報比
    if result:
        mid    = (result.get("進場區間低", 0) + result.get("進場區間高", 0)) / 2
        profit = result.get("停利目標", 0) - mid
        loss   = mid - result.get("停損點", 0)
        if loss > 0:
            result["風報比"] = f"1:{profit/loss:.1f}"

    return result
