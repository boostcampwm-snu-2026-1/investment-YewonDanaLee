"""
YENLAB 백엔드
- /stock/{ticker}  : 네이버 금융 → KRX / NXT 시세 (requests + BeautifulSoup)
- /sox             : Yahoo Finance → SOX 지수 (yfinance, 60s 캐시)
- /etf             : investing.com → DRAM / EWY / KORU ETF (Selenium, 60s 캐시)
실행: venv/bin/python3 backend/main.py
"""
import time
import threading
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://finance.naver.com",
}

# ─── 파싱 유틸 ─────────────────────────────────────────────────────────

def _parse_num(element) -> int:
    if not element:
        return 0
    blind = element.find("span", class_="blind")
    if blind:
        raw = blind.text.strip()
    else:
        em = element.find("em")
        raw = "".join(s.text for s in em.find_all("span")).strip() if em else ""
    try:
        return int(float(raw.replace(",", "").replace("+", "").strip() or "0"))
    except ValueError:
        return 0

def _parse_exday(exday_element) -> tuple[int, float]:
    if not exday_element:
        return 0, 0.0
    ems = exday_element.find_all("em")

    def _signed(em, is_float=False):
        if not em:
            return 0.0 if is_float else 0
        blind = em.find("span", class_="blind")
        raw = blind.text.strip() if blind else ""
        try:
            val = float(raw.replace(",", "").replace("+", "").strip() or "0")
        except ValueError:
            val = 0.0
        if "no_down" in em.get("class", []):
            val = -abs(val)
        return round(val, 2) if is_float else int(val)

    return (
        _signed(ems[0] if ems else None, is_float=False),
        _signed(ems[1] if len(ems) > 1 else (ems[0] if ems else None), is_float=True),
    )

def _to_float(s: str) -> float:
    try:
        return float(s.replace(",", "").replace("+", "").strip())
    except Exception:
        return 0.0

# ─── 주식 데이터 (네이버 금융) ──────────────────────────────────────────

def get_stock_data(ticker: str) -> dict | None:
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    try:
        res = requests.get(url, headers=NAVER_HEADERS, timeout=10)
        if res.status_code != 200:
            return None
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        def section(container) -> dict | None:
            if not container:
                return None
            price = _parse_num(container.find("p", class_="no_today"))
            if price <= 0:
                return None
            diff_amt, diff_rate = _parse_exday(container.find("p", class_="no_exday"))
            v_span = container.find("span", class_="sp_txt9")
            volume = _parse_num(v_span.find_parent("td")) if v_span else 0
            a_span = container.find("span", class_="sp_txt10")
            trading_value = _parse_num(a_span.find_parent("td")) if a_span else 0
            return {
                "price": price,
                "diffAmount": diff_amt,
                "diffRate": round(diff_rate, 2),
                "prevClosePrice": price - diff_amt,
                "volume": volume,
                "tradingValue": trading_value,
            }

        krx_data = section(soup.find("div", id="rate_info_krx"))
        nxt_data = section(soup.find("div", id="rate_info_nxt"))
        if not krx_data and not nxt_data:
            return None

        h2 = soup.select_one("div.wrap_company h2 a")
        return {
            "ticker": ticker,
            "name": h2.get_text(strip=True) if h2 else ticker,
            "krx": krx_data,
            "nxt": nxt_data,
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        }
    except Exception as e:
        print(f"[stock] {ticker} error: {e}")
        return None

# ─── SOX (yfinance) ─────────────────────────────────────────────────────

_sox_cache: dict | None = None
_sox_ts: float = 0.0

def _fetch_sox() -> dict | None:
    try:
        import yfinance as yf
        info = yf.Ticker("^SOX").fast_info
        price = round(float(info.last_price), 2)
        prev  = round(float(info.previous_close), 2)
        diff  = round(price - prev, 2)
        rate  = round((diff / prev) * 100, 2) if prev else 0.0
        return {
            "index": price, "diffAmount": diff, "diffRate": rate,
            "direction": "up" if diff > 0 else ("down" if diff < 0 else "neutral"),
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        }
    except Exception as e:
        print(f"[SOX] error: {e}")
        return None

def _sox_poller():
    global _sox_cache, _sox_ts
    while True:
        d = _fetch_sox()
        if d:
            _sox_cache, _sox_ts = d, time.time()
            print(f"[SOX] {d['index']:,.2f}  {d['diffRate']:+.2f}%")
        time.sleep(60)

threading.Thread(target=_sox_poller, daemon=True).start()

# ─── ETF (investing.com, Selenium) ──────────────────────────────────────

ETF_PAGES = [
    {"key": "DRAM", "name": "DRAM",
     "url": "https://kr.investing.com/etfs/dram"},
    {"key": "EWY",  "name": "EWY",
     "url": "https://kr.investing.com/etfs/ishares-south-korea-index"},
    {"key": "KORU", "name": "KORU",
     "url": "https://kr.investing.com/etfs/direxion-daily-sk-bull-3x-shrs"},
]

_etf_cache: dict = {}   # key → item dict
_etf_lock = threading.Lock()

def _create_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver

def _scrape_investing(driver, url: str) -> dict | None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        driver.get(url)
        price_el = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@data-test="instrument-price-last"]')
            )
        )
        price = _to_float(price_el.text)
        change_els = driver.find_elements(By.XPATH, '//*[@data-test="instrument-price-change"]')
        pct_els    = driver.find_elements(By.XPATH, '//*[@data-test="instrument-price-change-percent"]')
        change = _to_float(change_els[0].text) if change_els else 0.0
        pct    = _to_float(pct_els[0].text.strip().strip("()%+")) if pct_els else 0.0
        if change < 0:
            pct = -abs(pct)
        return {
            "index": price, "diffAmount": change, "diffRate": round(pct, 2),
            "direction": "up" if change > 0 else ("down" if change < 0 else "neutral"),
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        }
    except Exception as e:
        print(f"[ETF] scrape error {url}: {e}")
        return None

def _etf_poller():
    """단일 Chrome 세션으로 ETF 3개를 순회하며 60초마다 캐시 갱신"""
    while True:
        driver = _create_driver()
        try:
            for etf in ETF_PAGES:
                data = _scrape_investing(driver, etf["url"])
                if data:
                    with _etf_lock:
                        _etf_cache[etf["key"]] = {**data, "name": etf["name"]}
                    print(f"[ETF] {etf['key']:4s}  {data['index']:>10.2f}  {data['diffRate']:+.2f}%")
        except Exception as e:
            print(f"[ETF] poller error: {e}")
        finally:
            driver.quit()
        time.sleep(60)

threading.Thread(target=_etf_poller, daemon=True).start()

# ─── API 엔드포인트 ──────────────────────────────────────────────────────

@app.get("/stock/{ticker}")
def api_stock(ticker: str):
    data = get_stock_data(ticker)
    if not data:
        raise HTTPException(status_code=502, detail="parse failed")
    return data

@app.get("/sox")
def api_sox():
    global _sox_cache, _sox_ts
    now = time.time()
    if _sox_cache and (now - _sox_ts) < 60:
        return _sox_cache
    d = _fetch_sox()
    if d:
        _sox_cache, _sox_ts = d, now
        return d
    if _sox_cache:
        return _sox_cache
    return JSONResponse({"error": "SOX unavailable"}, status_code=502)

def _etf_item(key: str):
    with _etf_lock:
        data = _etf_cache.get(key)
    if not data:
        return JSONResponse({"error": "loading"}, status_code=503)
    return data

@app.get("/etf")
def api_etf():
    with _etf_lock:
        items = list(_etf_cache.values())
    return {
        "items": items,
        "loading": len(items) == 0,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
    }

@app.get("/drametf")
def api_drametf():
    return _etf_item("DRAM")

@app.get("/ewy")
def api_ewy():
    return _etf_item("EWY")

@app.get("/koru")
def api_koru():
    return _etf_item("KORU")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
