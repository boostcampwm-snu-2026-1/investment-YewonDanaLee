"""
YENLAB 백엔드
- /stock/{ticker}  : 네이버 금융 → KRX / NXT 시세 (requests + BeautifulSoup)
- /sox             : investing.com → SOX 지수 (Selenium, 60s 캐시)
- /etf             : investing.com → DRAM / EWY / KORU ETF (Selenium, 60s 캐시)
- /dram/spot       : DRAMExchange → 주가 예측용 4대 핵심 지표 (60분 캐시 & 엑셀 누적)
백그라운드 DB 누적 (1일 1회, 날짜 중복 시 자동 스킵):
  - price_DB_crawling  → data/삼성_history.xlsx, data/SK_history.xlsx  (전일 데이터)
  - ETF_DB_crawling    → data/ETF.xlsx                                  (전일 데이터)
  - _dram_poller       → data/memory_price.xlsx                         (당일 데이터)
실행: venv/bin/python3 backend/main.py
"""
import os
import re
import sys
import threading
import time
from datetime import datetime

# 같은 디렉토리의 크롤링 스크립트를 임포트 가능하게 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
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

# ─── ETF + SOX + USD/KRW (investing.com, Selenium) ─────────────────────

ETF_PAGES = [
    {"key": "SOX",  "name": "SOX",
     "url": "https://kr.investing.com/indices/phlx-semiconductor"},
    {"key": "DRAM", "name": "DRAM",
     "url": "https://kr.investing.com/etfs/dram"},
    {"key": "EWY",  "name": "EWY",
     "url": "https://kr.investing.com/etfs/ishares-south-korea-index"},
    {"key": "KORU", "name": "KORU",
     "url": "https://kr.investing.com/etfs/direxion-daily-sk-bull-3x-shrs"},
    {"key": "USDKRW", "name": "USD/KRW",
     "url": "https://kr.investing.com/currencies/usd-krw"},
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
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
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

def _fetch_one_etf(etf: dict):
    driver = _create_driver()
    try:
        data = _scrape_investing(driver, etf["url"])
        if data:
            with _etf_lock:
                _etf_cache[etf["key"]] = {**data, "name": etf["name"]}
            print(f"[ETF] {etf['key']:4s}  {data['index']:>10.2f}  {data['diffRate']:+.2f}%")
    except Exception as e:
        print(f"[ETF] {etf['key']} error: {e}")
    finally:
        driver.quit()

def _etf_poller():
    from concurrent.futures import ThreadPoolExecutor
    while True:
        with ThreadPoolExecutor(max_workers=len(ETF_PAGES)) as pool:
            pool.map(_fetch_one_etf, ETF_PAGES)
        time.sleep(60)

threading.Thread(target=_etf_poller, daemon=True).start()



# ─── DRAMExchange Spot/Contract (신규 통합) ──────────────────────────────────

_dram_cache: dict | None = None
_dram_lock = threading.Lock()
DRAM_FILE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "memory_price.xlsx")

def _clean_dram_percentage(text: str) -> float:
    match = re.search(r"(-?\d+\.?\d*)", text)
    return float(match.group(1)) if match else 0.0

def _fetch_dram_exchange() -> dict | None:
    url = "https://dramexchange.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        
        extracted = {}
        rows = soup.find_all("tr")
        
        for row in rows:
            text = row.get_text(separator=" ", strip=True)
            
            # 1. DDR5 16Gb 단품 (현물 선행)
            if "DDR5 16Gb (2Gx8) 4800/5600" in text:
                tds = row.find_all("td")
                if len(tds) >= 7:
                    extracted["DDR5_16Gb_Avg"] = float(tds[5].text.strip())
                    extracted["DDR5_16Gb_Chg"] = _clean_dram_percentage(tds[6].text)
            
            # 2. DDR5 RDIMM 32GB (서버용 모듈 수요)
            elif "DDR5 RDIMM 32GB 4800/5600" in text:
                tds = row.find_all("td")
                if len(tds) >= 7:
                    extracted["DDR5_RDIMM_32GB_Avg"] = float(tds[5].text.strip())
                    extracted["DDR5_RDIMM_32GB_Chg"] = _clean_dram_percentage(tds[6].text)
            
            # 3. 512Gb TLC Wafer (NAND 업황)
            elif "512Gb TLC" in text:
                tds = row.find_all("td")
                if len(tds) >= 7:
                    extracted["NAND_512Gb_TLC_Avg"] = float(tds[5].text.strip())
                    extracted["NAND_512Gb_TLC_Chg"] = _clean_dram_percentage(tds[6].text)
            
            # 4. DDR4 16GB SO-DIMM (고정 계약가 대표)
            elif "DDR4 16GB SO-DIMM" in text:
                tds = row.find_all("td")
                if len(tds) >= 6:
                    extracted["DDR4_16GB_SO_DIMM_Avg"] = float(tds[3].text.strip())
                    extracted["DDR4_16GB_SO_DIMM_Chg"] = _clean_dram_percentage(tds[4].text)

        required_keys = ["DDR5_16Gb_Avg", "DDR5_RDIMM_32GB_Avg", "NAND_512Gb_TLC_Avg", "DDR4_16GB_SO_DIMM_Avg"]
        if not all(k in extracted for k in required_keys):
            print("[DRAM] Error: Some key metrics missing from HTML.")
            return None
            
        extracted["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        return extracted
    except Exception as e:
        print(f"[DRAM] fetch error: {e}")
        return None

def _save_dram_to_excel(data: dict):
    """매일 최초 1회 실행 혹은 데이터 갱신 시 엑셀 파일 누적 저장"""
    try:
        today_str = datetime.today().strftime("%Y-%m-%d")
        new_row = {"Date": today_str}
        for k, v in data.items():
            if k != "updatedAt":
                new_row[k] = v
                
        df_new = pd.DataFrame([new_row])
        columns_order = [
            "Date", "DDR5_16Gb_Avg", "DDR5_16Gb_Chg", 
            "DDR5_RDIMM_32GB_Avg", "DDR5_RDIMM_32GB_Chg", 
            "NAND_512Gb_TLC_Avg", "NAND_512Gb_TLC_Chg", 
            "DDR4_16GB_SO_DIMM_Avg", "DDR4_16GB_SO_DIMM_Chg"
        ]
        
        os.makedirs(os.path.dirname(DRAM_FILE_NAME), exist_ok=True)
        
        if os.path.exists(DRAM_FILE_NAME):
            df_old = pd.read_excel(DRAM_FILE_NAME)
            # 오늘 날짜 중복 행 필터링 제거 후 병합
            if today_str in df_old["Date"].astype(str).values:
                df_old = df_old[df_old["Date"].astype(str) != today_str]
            df_final = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_final = df_new
            
        df_final = df_final[columns_order]
        df_final.to_excel(DRAM_FILE_NAME, index=False)
        print(f"[DRAM] Excel accumulated successfully for {today_str}.")
    except Exception as e:
        print(f"[DRAM] Excel save error: {e}")

def _dram_poller():
    global _dram_cache
    while True:
        d = _fetch_dram_exchange()
        if d:
            with _dram_lock:
                _dram_cache = d
            print(f"[DRAM] Spot/Contract market data updated inside cache.")
            _save_dram_to_excel(d)
        time.sleep(86400)

threading.Thread(target=_dram_poller, daemon=True).start()


# ─── 주가 히스토리 (price_DB_crawling.py, 1일 주기) ─────────────────────

def _price_history_poller():
    import price_DB_crawling as _mod
    while True:
        try:
            _mod.main()
        except Exception as e:
            print(f"[PriceHistory] error: {e}")
        time.sleep(86400)

threading.Thread(target=_price_history_poller, daemon=True).start()

# ─── ETF 히스토리 (ETF_DB_crawling.py, 1일 주기) ────────────────────────

def _etf_history_poller():
    import ETF_DB_crawling as _mod
    while True:
        try:
            _mod.main()
        except Exception as e:
            print(f"[ETFHistory] error: {e}")
        time.sleep(86400)

threading.Thread(target=_etf_history_poller, daemon=True).start()


# ─── API 엔드포인트 ──────────────────────────────────────────────────────

@app.get("/usdkrw")
def api_usdkrw():
    with _etf_lock:
        raw = _etf_cache.get("USDKRW")
    if not raw:
        return JSONResponse({"error": "loading"}, status_code=503)
    return {
        "usdKrw":     raw["index"],
        "diffAmount": raw["diffAmount"],
        "diffRate":   raw["diffRate"],
        "direction":  raw["direction"],
        "updatedAt":  raw["updatedAt"],
    }

@app.get("/stock/{ticker}")
def api_stock(ticker: str):
    data = get_stock_data(ticker)
    if not data:
        raise HTTPException(status_code=502, detail="parse failed")
    return data

@app.get("/sox")
def api_sox():
    return _etf_item("SOX")

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


# ─── 신규 라우터 추가 (프론트엔드 연동용) ───────────────────────────────────

@app.get("/dram/spot")
def api_dram_spot():
    """주가 예측을 위한 메모리 현물/고정 핵심 스펙 반환"""
    with _dram_lock:
        data = _dram_cache
    if not data:
        return JSONResponse({"error": "DRAM data loading"}, status_code=503)
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")