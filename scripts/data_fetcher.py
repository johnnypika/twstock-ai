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
    """盤中：用 MI_INDEX API 取得當日全市場即時行情"""
    import time
    ts  = int(time.time() * 1000)
    url = (
        f"https://www.twse.com.tw/exchangeReport/MI_INDEX"
        f"?response=json&type=ALL&_={ts}"
    )
    try:
        r    = requests.get(url, headers=HEADERS, timeout=20)
        data = r.json()

        # fields9 是個股欄位名稱，data9 是個股資料
        fields = data.get("fields9", [])
        rows   = data.get("data9", [])

        if not fields or not rows:
            print(f"[TWSE] MI_INDEX 無 data9，status={data.get('stat')}")
            return []

        # 找欄位索引
        def idx(name):
            try: return fields.index(name)
            except ValueError: return None

        i_code   = idx("證券代號")
        i_name   = idx("證券名稱")
        i_close  = idx("收盤價")
        i_change = idx("漲跌價差")
        i_vol    = idx("成交股數")
        i_turn   = idx("成交金額")
        i_sign   = idx("漲跌(+/-)")

        if i_code is None or i_name is None or i_close is None:
            print(f"[TWSE] MI_INDEX 欄位不符，fields={fields[:5]}")
            return []

        result = []
        for row in rows:
            try:
                code  = row[i_code].strip()
                name  = row[i_name].strip()
                close_str = row[i_close].replace(",", "").strip()
                if not close_str or close_str in ("-", "--", ""):
                    continue
                close  = float(close_str)
                change_str = row[i_change].replace(",", "").strip() if i_change else "0"
                change = float(change_str) if change_str and change_str not in ("-","--","") else 0.0

                # 漲跌符號：html tag 包含 color:red → 漲，color:green → 跌
                if i_sign is not None:
                    sign_html = row[i_sign]
                    if "green" in sign_html:
                        change = -abs(change)
                    elif "red" in sign_html:
                        change = abs(change)

                prev = close - change
                chg_pct = round(change / prev * 100, 2) if prev > 0 else 0.0

                vol  = int(row[i_vol].replace(",","")) if i_vol is not None else 0
                turn = int(row[i_turn].replace(",","")) if i_turn is not None else 0

                result.append({
                    "code": code, "name": name,
                    "price": close, "change": change,
                    "change_pct": chg_pct,
                    "volume": vol, "turnover": turn,
                })
            except Exception:
                continue

        print(f"[TWSE] MI_INDEX 盤中全市場：取得 {len(result)} 筆")
        return result

    except Exception as e:
        print(f"[TWSE] MI_INDEX 失敗: {e}")
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
    取得單一股票的即時資訊（price, prev_close）
    使用 MI_INDEX 盤中資料，不需要 session cookie
    """
    # 先嘗試從盤中快取取得
    data = _get_mi_index_cache()
    if code in data:
        return data[code]

    # 若快取沒有（可能盤後），改用 STOCK_DAY 歷史資料
    return _get_stock_day_price(code)


_mi_cache: dict = {}
_mi_cache_time: float = 0.0

def _get_mi_index_cache() -> dict:
    """取得 MI_INDEX 全市場資料，每次呼叫至多 60 秒重新抓一次"""
    import time as _time
    global _mi_cache, _mi_cache_time
    now = _time.time()
    if now - _mi_cache_time < 60 and _mi_cache:
        return _mi_cache

    ts  = int(now * 1000)
    url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&type=ALL&_={ts}"
    try:
        r      = requests.get(url, headers=HEADERS, timeout=15)
        data   = r.json()
        fields = data.get("fields9", [])
        rows   = data.get("data9", [])
        if not fields or not rows:
            return _mi_cache  # 回傳舊快取

        def idx(n):
            try: return fields.index(n)
            except ValueError: return None

        i_code  = idx("證券代號")
        i_name  = idx("證券名稱")
        i_close = idx("收盤價")
        i_prev  = None  # MI_INDEX 沒有直接提供昨收，用開盤前資料補
        i_sign  = idx("漲跌(+/-)")
        i_chg   = idx("漲跌價差")

        if i_code is None or i_close is None:
            return _mi_cache

        result = {}
        for row in rows:
            try:
                code  = row[i_code].strip()
                cs    = row[i_close].replace(",","").strip()
                if not cs or cs in ("-","--"): continue
                close = float(cs)
                chg   = 0.0
                if i_chg is not None:
                    ds = row[i_chg].replace(",","").strip()
                    if ds and ds not in ("-","--"):
                        chg = float(ds)
                        if i_sign is not None and "green" in row[i_sign]:
                            chg = -abs(chg)
                prev_close = round(close - chg, 2) if chg else None
                result[code] = {"price": close, "prev_close": prev_close}
            except Exception:
                continue

        _mi_cache      = result
        _mi_cache_time = now
        print(f"[TWSE] MI_INDEX 快取更新：{len(result)} 筆")
        return result
    except Exception as e:
        print(f"[TWSE] MI_INDEX 快取失敗: {e}")
        return _mi_cache


def _get_stock_day_price(code: str) -> dict | None:
    """盤後備援：從 STOCK_DAY 取最新收盤價"""
    from datetime import datetime
    today  = datetime.today().strftime("%Y%m%d")
    url    = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={today}&stockNo={code}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        rows = data.get("data", [])
        if rows:
            last  = rows[-1]
            price = float(last[6].replace(",",""))  # 收盤價欄位
            return {"price": price, "prev_close": None}
    except Exception:
        pass
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
