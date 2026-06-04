import os
import re
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import requests

# 1. 크롤링 타겟 URL 및 헤더 설정
URL = "https://dramexchange.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
FILE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "memory_price.xlsx")


def clean_percentage(text):
    """%-문자열에서 숫자만 추출하는 헬퍼 함수"""
    match = re.search(r"(-?\d+\.?\d*)", text)
    return float(match.group(1)) if match else 0.0


def crawl_and_save():
    # 오늘 날짜 (주가 데이터와 조인하기 편하게 YYYY-MM-DD 포맷)
    today_str = datetime.today().strftime("%Y-%m-%d")

    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"조회 실패: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # 오늘 저장할 데이터 딕셔너리 초기화
    new_data = {"Date": today_str}

    # 전체 테이블 행(tr)을 돌며 필요한 데이터 추출
    rows = soup.find_all("tr")

    for row in rows:
        text = row.get_text(separator=" ", strip=True)

        # 1. DDR5 16Gb (2Gx8) 4800/5600 [DRAM 현물 선행]
        if "DDR5 16Gb (2Gx8) 4800/5600" in text:
            tds = row.find_all("td")
            if len(tds) >= 7:
                new_data["DDR5_16Gb_Avg"] = float(tds[5].text.strip())
                new_data["DDR5_16Gb_Chg"] = clean_percentage(tds[6].text)

        # 2. DDR5 RDIMM 32GB 4800/5600 [서버 수요]
        elif "DDR5 RDIMM 32GB 4800/5600" in text:
            tds = row.find_all("td")
            if len(tds) >= 7:
                new_data["DDR5_RDIMM_32GB_Avg"] = float(tds[5].text.strip())
                new_data["DDR5_RDIMM_32GB_Chg"] = clean_percentage(tds[6].text)

        # 3. 512Gb TLC [NAND 웨이퍼]
        elif "512Gb TLC" in text:
            tds = row.find_all("td")
            if len(tds) >= 7:
                new_data["NAND_512Gb_TLC_Avg"] = float(tds[5].text.strip())
                new_data["NAND_512Gb_TLC_Chg"] = clean_percentage(tds[6].text)

        # 4. DDR4 16GB SO-DIMM [전통 고정거래가]
        elif "DDR4 16GB SO-DIMM" in text:
            tds = row.find_all("td")
            if len(tds) >= 6:
                # 고정가 테이블은 구조가 소폭 다름 (Avg가 3번째 index)
                new_data["DDR4_16GB_SO_DIMM_Avg"] = float(tds[3].text.strip())
                new_data["DDR4_16GB_SO_DIMM_Chg"] = clean_percentage(
                    tds[4].text
                )

    # 데이터 유실 방지 검증 (필수 항목이 다 차있는지 확인)
    required_keys = [
        "DDR5_16Gb_Avg",
        "DDR5_RDIMM_32GB_Avg",
        "NAND_512Gb_TLC_Avg",
        "DDR4_16GB_SO_DIMM_Avg",
    ]
    if not all(key in new_data for key in required_keys):
        print("경고: 일부 타겟 데이터를 웹페이지에서 찾지 못했습니다.")
        return

    # 3. 엑셀 파일 누적 저장 로직
    df_new = pd.DataFrame([new_data])

    if os.path.exists(FILE_NAME):
        # 기존 파일이 있으면 읽어와서 합치기
        df_old = pd.read_excel(FILE_NAME)

        # 중복 수집 방지 (오늘 날짜 데이터가 이미 있으면 업데이트 혹은 패스)
        if today_str in df_old["Date"].astype(str).values:
            print(f"{today_str} 데이터가 이미 존재합니다. 업데이트합니다.")
            df_old = df_old[df_old["Date"].astype(str) != today_str]

        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        # 파일이 없으면 새로 만들기
        df_final = df_new

    # 순서 고정을 위한 컬럼 정의
    columns_order = [
        "Date",
        "DDR5_16Gb_Avg",
        "DDR5_16Gb_Chg",
        "DDR5_RDIMM_32GB_Avg",
        "DDR5_RDIMM_32GB_Chg",
        "NAND_512Gb_TLC_Avg",
        "NAND_512Gb_TLC_Chg",
        "DDR4_16GB_SO_DIMM_Avg",
        "DDR4_16GB_SO_DIMM_Chg",
    ]
    df_final = df_final[columns_order]

    # 엑셀 저장
    df_final.to_excel(FILE_NAME, index=False)
    print(f"성공: {today_str} 데이터가 {FILE_NAME}에 기록되었습니다.")


if __name__ == "__main__":
    crawl_and_save()