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
    info = get_stock_info(code)
    return info.get("price") if info else None


def get_stock_info(code: str) -> dict | None:
    """
    取得單一股票的即時資訊，包含：
      price      : 最新成交價
      prev_close : 昨日收盤價（今日平盤）
    """
    # 先嘗試上市（tse），失敗再試上櫃（otc）
    for market in ("tse", "otc"):
        url = (
            f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
            f"?ex_ch={market}_{code}.tw&json=1&delay=0"
        )
        try:
            r     = requests.get(url, headers=HEADERS, timeout=8)
            items = r.json().get("msgArray", [])
            if not items:
                continue
            item = items[0]
            z = item.get("z", "-")   # 即時成交價
            y = item.get("y", "-")   # 昨收價
            price      = float(z) if z and z != "-" else None
            prev_close = float(y) if y and y != "-" else None
            if price or prev_close:
                return {"price": price, "prev_close": prev_close}
        except Exception:
            continue
    return None


def get_taiex() -> dict:
    """
    大盤加權指數資料，依序嘗試多個來源：
    1. TWSE 即時大盤（盤中有效）
    2. TWSE 歷史收盤（盤前/收盤後有效）
    回傳最近一筆有效資料，週一盤前會回傳上週五收盤。
    """

    # ── 來源一：TWSE 即時大盤指數（盤中才有資料）──
    try:
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw&json=1&delay=0"
        r   = requests.get(url, headers=HEADERS, timeout=8)
        items = r.json().get("msgArray", [])
        if items:
            item = items[0]
            z = item.get("z", "-")
            y = item.get("y", "-")
            price = float(z) if z and z != "-" else None
            prev  = float(y) if y and y != "-" else None
            if price and price > 0:
                change     = round(price - prev, 2) if prev else 0
                change_pct = round(change / prev * 100, 2) if prev else 0
                print(f"[TWSE] 即時大盤：{price} 點 {change_pct:+.2f}%")
                return {
                    "date": "今日", "close": price,
                    "change": change, "change_pct": change_pct,
                    "prev_close": prev,
                }
    except Exception as e:
        print(f"[TWSE] 即時大盤失敗: {e}")

    # ── 來源二：TWSE 歷史收盤資料（盤前/休市時使用）──
    try:
        url  = "https://openapi.twse.com.tw/v1/exchangeReport/TAIEX"
        r    = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        # 找最後一筆有效資料
        for last in reversed(data):
            close = float(last.get("CloseIndex", 0) or 0)
            if close > 0:
                change     = float(last.get("Change", 0) or 0)
                change_pct = float(last.get("ChangePercent", 0) or 0)
                date_str   = last.get("Date", "")
                print(f"[TWSE] 歷史收盤大盤：{date_str} {close} 點 {change_pct:+.2f}%")
                return {
                    "date": date_str, "close": close,
                    "change": change, "change_pct": change_pct,
                }
    except Exception as e:
        print(f"[TWSE] 歷史收盤大盤失敗: {e}")

    print("[TWSE] 大盤資料所有來源均失敗，使用備援預設值")
    return {
        "date": "N/A", "close": 0, "change": 0, "change_pct": 0,
        "note": "資料暫時無法取得，請依近期走勢判斷",
    }


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
