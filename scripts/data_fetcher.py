"""
scripts/data_fetcher.py
台股資料抓取：TWSE 即時報價、大盤、財經新聞
"""

import requests
from datetime import datetime, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (TaiwanStockAI/2.0)"}


def get_all_stocks() -> list:
    """
    抓取全市場上市股票行情：
    - 盤中（09:00～13:30）：用 TWSE 即時全市場 API，取得今日漲跌
    - 盤後 / 開盤前：用 STOCK_DAY_ALL（前一交易日收盤）
    """
    from datetime import datetime, timezone, timedelta
    TW   = timezone(timedelta(hours=8))
    now  = datetime.now(TW)
    hour = now.hour
    minute = now.minute
    t = hour * 60 + minute
    is_market_hours = (9 * 60 <= t < 13 * 60 + 35)

    if is_market_hours:
        result = _get_stocks_intraday()
        if result:
            return result
        print("[TWSE] 盤中 API 無資料，改用 STOCK_DAY_ALL")

    return _get_stocks_day_all()


def _get_stocks_intraday() -> list:
    """
    盤中：用 Yahoo Finance 批次查詢全市場即時漲跌
    先從 TWSE 取得股票代號清單，再批次查 Yahoo Finance
    """
    # 先取代號清單（用前一日資料，只要代號和名稱）
    codes = _get_stock_list()
    if not codes:
        return []

    result = []
    # 每批最多 50 個代號，避免 URL 過長
    batch_size = 50
    symbols    = [f"{c['code']}.TW" for c in codes]
    name_map   = {c['code']: c['name'] for c in codes}

    for i in range(0, min(len(symbols), 1000), batch_size):
        batch = symbols[i:i+batch_size]
        url   = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(batch)}"
        headers = {"User-Agent": "Mozilla/5.0 (TaiwanStockAI/2.0)", "Accept": "application/json"}
        try:
            r     = requests.get(url, headers=headers, timeout=15)
            items = r.json().get("quoteResponse", {}).get("result", [])
            for item in items:
                sym    = item.get("symbol", "").replace(".TW", "")
                price  = item.get("regularMarketPrice")
                prev   = item.get("regularMarketPreviousClose")
                vol    = item.get("regularMarketVolume", 0)
                if not price or not sym:
                    continue
                change     = round(price - prev, 2) if prev else 0
                change_pct = round(change / prev * 100, 2) if prev else 0
                result.append({
                    "code": sym,
                    "name": name_map.get(sym, sym),
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": vol,
                    "turnover": int(price * vol),
                })
        except Exception as e:
            print(f"[Yahoo] 批次查詢失敗: {e}")
            continue

    print(f"[Yahoo] 盤中全市場：取得 {len(result)} 筆")
    return result


def _get_stock_list() -> list:
    """取得上市股票代號清單（從 STOCK_DAY_ALL，只要代號和名稱）"""
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        r   = requests.get(url, headers=HEADERS, timeout=15)
        return [
            {"code": d.get("證券代號","").strip(), "name": d.get("證券名稱","").strip()}
            for d in r.json()
            if d.get("證券代號") and d.get("證券名稱")
        ]
    except Exception as e:
        print(f"[TWSE] 代號清單失敗: {e}")
        return []


def _get_stocks_day_all() -> list:
    """盤後/開盤前：STOCK_DAY_ALL（前一交易日收盤資料）"""
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
        print(f"[TWSE] STOCK_DAY_ALL：取得 {len(result)} 筆")
        return result
    except Exception as e:
        print(f"[TWSE] STOCK_DAY_ALL 失敗: {e}")
        return []


def get_stock_info(code: str) -> dict | None:
    """
    取得單一股票/ETF 的即時資訊（price, prev_close）
    使用 Yahoo Finance API：不需要 cookie、支援股票和 ETF、盤中盤後都有資料
    台股代號格式：2330 → 2330.TW，00631L → 00631L.TW
    """
    symbol = f"{code}.TW"
    url    = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
    headers = {
        "User-Agent": "Mozilla/5.0 (TaiwanStockAI/2.0)",
        "Accept": "application/json",
    }
    try:
        r    = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]

        price      = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")

        if price:
            return {"price": price, "prev_close": prev_close}
    except Exception as e:
        print(f"[Yahoo] {code} 查詢失敗: {e}")

    return None


def get_stock_price(code: str) -> float | None:
    """取得單一股票即時成交價（向後相容介面）"""
    info = get_stock_info(code)
    return info.get("price") if info else None


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
