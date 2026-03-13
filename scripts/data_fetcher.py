"""
scripts/data_fetcher.py
台股資料抓取：TWSE 即時報價、大盤、財經新聞
"""

import requests
from datetime import datetime, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (TaiwanStockAI/2.0)"}


def get_all_stocks() -> list:
    """抓取全市場上市股票今日行情"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        result = []
        for item in r.json():
            try:
                close  = float(item.get("收盤價") or 0)
                change = float(item.get("漲跌價差") or 0)
                vol    = int(item.get("成交股數") or 0)
                turn   = int(item.get("成交金額") or 0)
                prev   = close - change
                chg_pct = round(change / prev * 100, 2) if prev > 0 else 0
                code    = item.get("證券代號", "").strip()
                name    = item.get("證券名稱", "").strip()
                if not code or not name:
                    continue
                result.append({
                    "code": code, "name": name,
                    "price": close, "change": change,
                    "change_pct": chg_pct,
                    "volume": vol, "turnover": turn,
                })
            except Exception:
                continue
        return result
    except Exception as e:
        print(f"[TWSE] 全市場報價失敗: {e}")
        return []


def get_stock_price(code: str) -> float | None:
    """取得單一股票即時成交價"""
    url = (
        f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
        f"?ex_ch=tse_{code}.tw&json=1&delay=0"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        items = r.json().get("msgArray", [])
        if items:
            price = items[0].get("z") or items[0].get("y")
            if price and price != "-":
                return float(price)
    except Exception:
        pass
    return None


def get_taiex() -> dict:
    """大盤加權指數最新收盤資料"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/TAIEX"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        if data:
            last = data[-1]
            return {
                "date":       last.get("Date", ""),
                "close":      float(last.get("CloseIndex", 0)),
                "change":     float(last.get("Change", 0)),
                "change_pct": float(last.get("ChangePercent", 0)),
            }
    except Exception as e:
        print(f"[TWSE] 大盤資料失敗: {e}")
    return {}


def get_moving_averages(code: str) -> dict:
    """從 FinMind 免費 API 取得 MA5/MA20（每日限額，輕量使用）"""
    url    = "https://api.finmindtrade.com/api/v4/data"
    start  = (datetime.today() - timedelta(days=40)).strftime("%Y-%m-%d")
    params = {"dataset": "TaiwanStockPrice", "data_id": code, "start_date": start}
    try:
        r      = requests.get(url, params=params, headers=HEADERS, timeout=15)
        data   = r.json().get("data", [])
        closes = [float(d["close"]) for d in data if d.get("close")]
        if len(closes) >= 5:
            ma5  = round(sum(closes[-5:]) / 5, 2)
            ma20 = round(sum(closes[-20:]) / 20, 2) if len(closes) >= 20 else None
            return {"ma5": ma5, "ma20": ma20}
    except Exception:
        pass
    return {}


def get_news() -> str:
    """抓取鉅亨網台股新聞標題（RSS）"""
    headlines = []
    try:
        import xml.etree.ElementTree as ET
        r    = requests.get("https://news.cnyes.com/rss/cat/tw_stock",
                            headers=HEADERS, timeout=10)
        root = ET.fromstring(r.content)
        for item in root.iter("item"):
            t = item.findtext("title", "").strip()
            if t:
                headlines.append(t)
            if len(headlines) >= 12:
                break
    except Exception:
        pass

    if not headlines:
        return "（新聞取得失敗，請依大盤走勢判斷）"

    return "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))
