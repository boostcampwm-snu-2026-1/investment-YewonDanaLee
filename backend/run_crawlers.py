"""
전체 DB 크롤링 일괄 실행 스크립트
실행 순서:
  1. stock_DB_collector  — 삼성/SK 전일 주가 히스토리 → data/삼성_history.xlsx, data/SK_history.xlsx
  2. ETF_DB_crawling    — SOX/DRAM_ETF/EWY/KORU 전일 데이터 → data/ETF.xlsx
  3. memory_DB_crawling — 당일 DRAM 현물가 → data/memory_price.xlsx

실행: python backend/run_crawlers.py
      (또는 crontab에 등록하여 자동화)
"""
import sys
import os
import time
import importlib

# backend/ 폴더를 모듈 탐색 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CRAWLERS = [
    ("price_DB",  "stock_DB_collector",  "main"),
    ("ETF_DB",    "ETF_DB_collector",    "main"),
    ("memory_DB", "memory_DB_crawling", "crawl_and_save"),
]


def run_all():
    total_start = time.time()
    results = {}

    for label, module_name, func_name in CRAWLERS:
        print(f"\n{'─' * 50}")
        print(f"[{label}] 시작")
        start = time.time()
        try:
            mod = importlib.import_module(module_name)
            # 모듈을 재실행해야 할 경우(cron 등 장기 프로세스) 리로드
            importlib.reload(mod)
            getattr(mod, func_name)()
            elapsed = round(time.time() - start, 1)
            results[label] = f"완료 ({elapsed}s)"
            print(f"[{label}] 완료 ({elapsed}s)")
        except ModuleNotFoundError as e:
            elapsed = round(time.time() - start, 1)
            missing = str(e).replace("No module named ", "").strip("'")
            if missing == module_name:
                results[label] = f"실패: {module_name}.py 파일을 찾을 수 없음"
                print(f"[{label}] 실패: '{module_name}.py' 가 backend/ 폴더에 없습니다.")
            else:
                results[label] = f"실패: 의존성 없음 — {e}"
                print(f"[{label}] 실패: 패키지가 설치되지 않았습니다 — {e}")
        except AttributeError:
            elapsed = round(time.time() - start, 1)
            results[label] = f"실패: {module_name}.{func_name}() 함수 없음"
            print(f"[{label}] 실패: '{module_name}' 에 '{func_name}()' 함수가 없습니다.")
        except Exception as e:
            elapsed = round(time.time() - start, 1)
            results[label] = f"실패: {e}"
            print(f"[{label}] 실패 ({elapsed}s): {e}")

    total = round(time.time() - total_start, 1)
    print(f"\n{'=' * 50}")
    print(f"전체 소요: {total}s")
    for label, status in results.items():
        print(f"  {label:12s} → {status}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run_all()