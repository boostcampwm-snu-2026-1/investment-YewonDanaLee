import os
import re
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import requests

URL = "https://dramexchange.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
FILE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "memory_price.xlsx")


def clean_percentage(text: str) -> float:
    match = re.search(r"(-?\d+\.?\d*)", text)
    return float(match.group(1)) if match else 0.0


def to_float(text: str) -> float | None:
    """숫자로 변환 가능한 텍스트만 float 반환, 아니면 None"""
    try:
        return float(text.replace(",", "").strip())
    except ValueError:
        return None


def find_price_td(tds: list, start: int = 3) -> tuple[float, float] | None:
    """
    tds 리스트에서 start 인덱스부터 순서대로 탐색해
    숫자인 td(Avg)와 그 다음 td(Chg)를 찾아 반환.
    테이블 구조가 바뀌어도 대응 가능.
    """
    for i in range(start, len(tds) - 1):
        avg = to_float(tds[i].text)
        if avg is not None and avg > 0:
            chg = clean_percentage(tds[i + 1].text)
            return avg, chg
    return None


def crawl_and_save():
    today_str = datetime.today().strftime("%Y-%m-%d")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"조회 실패: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    new_data = {"Date": today_str}

    targets = {
        "DDR5 16Gb (2Gx8) 4800/5600":  ("DDR5_16Gb_Avg",       "DDR5_16Gb_Chg"),
        "DDR5 RDIMM 32GB 4800/5600":    ("DDR5_RDIMM_32GB_Avg", "DDR5_RDIMM_32GB_Chg"),
        "512Gb TLC":                    ("NAND_512Gb_TLC_Avg",  "NAND_512Gb_TLC_Chg"),
        "DDR4 UDIMM 16GB 3200":        ("DDR4_UDIMM_16GB_Avg", "DDR4_UDIMM_16GB_Chg"),
    }

    for row in soup.find_all("tr"):
        text = row.get_text(separator=" ", strip=True)
        for keyword, (avg_key, chg_key) in targets.items():
            if keyword in text and avg_key not in new_data:
                tds = row.find_all("td")
                result = find_price_td(tds, start=3)
                if result:
                    new_data[avg_key] = result[0]
                    new_data[chg_key] = result[1]
                else:
                    print(f"  [경고] '{keyword}' 행에서 숫자 컬럼을 찾지 못했습니다.")
                    print(f"         td 내용: {[td.text.strip() for td in tds]}")
                break

    required_keys = [
        "DDR5_16Gb_Avg", "DDR5_RDIMM_32GB_Avg",
        "NAND_512Gb_TLC_Avg", "DDR4_UDIMM_16GB_Avg",
    ]
    if not all(k in new_data for k in required_keys):
        missing = [k for k in required_keys if k not in new_data]
        print(f"경고: 다음 항목을 찾지 못했습니다: {missing}")
        return

    df_new = pd.DataFrame([new_data])

    if os.path.exists(FILE_NAME):
        df_old = pd.read_excel(FILE_NAME)
        if today_str in df_old["Date"].astype(str).values:
            print(f"{today_str} 데이터가 이미 존재합니다. 업데이트합니다.")
            df_old = df_old[df_old["Date"].astype(str) != today_str]
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new

    columns_order = [
        "Date",
        "DDR5_16Gb_Avg",       "DDR5_16Gb_Chg",
        "DDR5_RDIMM_32GB_Avg", "DDR5_RDIMM_32GB_Chg",
        "NAND_512Gb_TLC_Avg",  "NAND_512Gb_TLC_Chg",
        "DDR4_UDIMM_16GB_Avg", "DDR4_UDIMM_16GB_Chg",
    ]
    df_final = df_final[columns_order]
    df_final.to_excel(FILE_NAME, index=False)
    print(f"성공: {today_str} 데이터가 {FILE_NAME}에 기록되었습니다.")


if __name__ == "__main__":
    crawl_and_save()