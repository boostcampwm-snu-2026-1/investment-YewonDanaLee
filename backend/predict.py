"""
다음날 삼성/SK 종가 방향성 이진분류 예측
- 모델: RandomForest / XGBoost / LightGBM 중 Walk-Forward 검증 기준 최고 모델 선택
- 피처: 기술적 지표 + ETF 전일 수익률 + 종목 간 상관
- 타겟: 내일 종가 > 오늘 종가 → 1(상승), 아니면 → 0(하락/보합)
"""

import os
import warnings
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SAMSUNG  = os.path.join(BASE_DIR, "삼성_history.xlsx")
SK       = os.path.join(BASE_DIR, "SK_history.xlsx")
ETF      = os.path.join(BASE_DIR, "ETF.xlsx")

MODELS = {
    "RandomForest": RandomForestClassifier(
        n_estimators=200, max_depth=4, min_samples_leaf=5,
        class_weight="balanced", random_state=42
    ),
    "XGBoost": XGBClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=1, eval_metric="logloss",
        random_state=42, verbosity=0
    ),
    "LightGBM": LGBMClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        num_leaves=15, min_child_samples=10,
        subsample=0.8, colsample_bytree=0.8,
        class_weight="balanced", random_state=42, verbose=-1
    ),
}


# ─────────────────────────────────────────
# 1. 데이터 로드
# ─────────────────────────────────────────
import re as _re

_EXCEL_EPOCH = pd.Timestamp("1899-12-30")

def _parse_dates(series: pd.Series) -> pd.Series:
    """
    Excel 파일에서 날짜가 두 가지 형식으로 혼재:
      - 문자열: "2026년 06월 05일"
      - 정수:   46175 (Excel 날짜 시리얼)
    둘 다 올바른 Timestamp로 변환한다.
    """
    def _convert(val):
        if isinstance(val, (int, float)) and not pd.isna(val):
            return _EXCEL_EPOCH + pd.Timedelta(days=int(val))
        if isinstance(val, str):
            m = _re.match(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", val.strip())
            if m:
                return pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return pd.to_datetime(val, errors="coerce")
    return series.map(_convert)


def load_stock(path: str, prefix: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = ["날짜", "종가", "시가", "고가", "저가", "거래량", "변동"]
    df["날짜"] = _parse_dates(df["날짜"])
    df = df.dropna(subset=["날짜"]).sort_values("날짜").reset_index(drop=True)
    for col in ["종가", "시가", "고가", "저가"]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)
    df["거래량"] = pd.to_numeric(
        df["거래량"].astype(str).str.replace(r"[,MK]", "", regex=True), errors="coerce"
    )
    return df.rename(columns={
        "날짜": "date", "종가": f"{prefix}_close", "시가": f"{prefix}_open",
        "고가": f"{prefix}_high", "저가": f"{prefix}_low",
        "거래량": f"{prefix}_volume",
    }).drop(columns=["변동"])


def load_etf(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = ["date", "SOX", "DRAM_ETF", "EWY", "KORU"]
    df["date"] = _parse_dates(df["date"])
    return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


# ─────────────────────────────────────────
# 2. 피처 엔지니어링
# ─────────────────────────────────────────
def add_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    c, h, l, v = f"{prefix}_close", f"{prefix}_high", f"{prefix}_low", f"{prefix}_volume"
    df[f"{prefix}_ret1"] = df[c].pct_change(1)
    df[f"{prefix}_ret3"] = df[c].pct_change(3)
    df[f"{prefix}_ret5"] = df[c].pct_change(5)
    for w in [5, 10, 20]:
        df[f"{prefix}_ma{w}_ratio"] = df[c] / df[c].rolling(w).mean() - 1
    df[f"{prefix}_vol5"]     = df[f"{prefix}_ret1"].rolling(5).std()
    df[f"{prefix}_hl_range"] = (df[h] - df[l]) / df[c]
    df[f"{prefix}_vol_ratio"]= df[v] / df[v].rolling(5).mean()
    delta = df[c].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df[f"{prefix}_rsi14"]    = 100 - 100 / (1 + gain / (loss + 1e-9))
    ema12 = df[c].ewm(span=12).mean()
    ema26 = df[c].ewm(span=26).mean()
    df[f"{prefix}_macd_ratio"] = (ema12 - ema26) / df[c]
    return df


def build_dataframe() -> tuple[pd.DataFrame, list]:
    sam = load_stock(SAMSUNG, "삼성")
    sk  = load_stock(SK, "SK")
    etf = load_etf(ETF)

    df = sam.merge(sk, on="date", how="inner").merge(etf, on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)

    df = add_features(df, "삼성")
    df = add_features(df, "SK")

    # ETF 전일 수익률 (1일 lag — 미국 전날 → 한국 당일 반영)
    for col in ["SOX", "DRAM_ETF", "EWY", "KORU"]:
        df[f"{col}_ret"] = df[col].pct_change(1).shift(1)

    # 교차 피처
    df["cross_ret_diff"]  = df["삼성_ret1"] - df["SK_ret1"]
    df["cross_ret_corr5"] = df["삼성_ret1"].rolling(5).corr(df["SK_ret1"])
    df["weekday"]         = df["date"].dt.weekday

    features = [
        "삼성_ret1", "삼성_ret3", "삼성_ret5",
        "삼성_ma5_ratio", "삼성_ma10_ratio", "삼성_ma20_ratio",
        "삼성_vol5", "삼성_hl_range", "삼성_vol_ratio",
        "삼성_rsi14", "삼성_macd_ratio",
        "SK_ret1", "SK_ret3", "SK_ret5",
        "SK_ma5_ratio", "SK_ma10_ratio", "SK_ma20_ratio",
        "SK_vol5", "SK_hl_range", "SK_vol_ratio",
        "SK_rsi14", "SK_macd_ratio",
        "SOX_ret", "DRAM_ETF_ret", "EWY_ret", "KORU_ret",
        "cross_ret_diff", "cross_ret_corr5", "weekday",
    ]
    features = [f for f in features if f in df.columns]
    # NaN 비율 50% 초과 피처 제거 (데이터 공백이 많은 ETF 컬럼 대응)
    nan_rate = df[features].isna().mean()
    features = [f for f in features if nan_rate[f] <= 0.5]
    return df, features


# ─────────────────────────────────────────
# 3. Walk-Forward Validation
# ─────────────────────────────────────────
def walk_forward(df: pd.DataFrame, features: list, target_col: str,
                 train_size: int = None, step: int = None) -> dict:
    n = len(df)
    # 데이터가 적을 때 자동 조정: train 60%, step 10%
    if train_size is None:
        train_size = max(30, int(n * 0.6))
    if step is None:
        step = max(5, int(n * 0.1))
    X = df[features].values
    y = df[target_col].values
    n = len(df)
    results = {}

    for model_name, model in MODELS.items():
        all_preds, all_true = [], []
        scaler = StandardScaler()

        for start in range(train_size, n - step, step):
            X_tr, y_tr   = X[:start], y[:start]
            X_val, y_val = X[start:start + step], y[start:start + step]

            mask_tr  = ~np.isnan(X_tr).any(axis=1)
            mask_val = ~np.isnan(X_val).any(axis=1)
            X_tr, y_tr     = X_tr[mask_tr], y_tr[mask_tr]
            X_val, y_val   = X_val[mask_val], y_val[mask_val]

            if len(X_tr) < 50 or len(X_val) == 0:
                continue

            X_tr_s  = scaler.fit_transform(X_tr)
            X_val_s = scaler.transform(X_val)
            model.fit(X_tr_s, y_tr)
            all_preds.extend(model.predict(X_val_s))
            all_true.extend(y_val)

        acc = accuracy_score(all_true, all_preds)
        results[model_name] = {
            "accuracy": acc,
            "report": classification_report(
                all_true, all_preds,
                target_names=["하락/보합", "상승"], output_dict=True
            ),
        }

    return results


# ─────────────────────────────────────────
# 4. 최종 학습 & 내일 예측
# ─────────────────────────────────────────
def train_and_predict(df: pd.DataFrame, features: list,
                      target_col: str, prefix: str,
                      best_model_name: str):
    model  = MODELS[best_model_name]
    X      = df[features]
    y      = df[target_col]

    X_train = X.iloc[:-1]
    y_train = y.iloc[:-1]
    X_today = X.iloc[[-1]]

    mask    = ~X_train.isna().any(axis=1)
    X_train, y_train = X_train[mask], y_train[mask]

    scaler    = StandardScaler()
    X_tr_s    = scaler.fit_transform(X_train)
    X_today_s = scaler.transform(X_today)

    model.fit(X_tr_s, y_train)
    pred      = model.predict(X_today_s)[0]
    prob      = model.predict_proba(X_today_s)[0]
    direction = "▲ 상승" if pred == 1 else "▼ 하락/보합"
    color     = "\033[91m" if pred == 1 else "\033[94m"

    print(f"\n{'─'*45}")
    print(f"[{prefix}] 내일 예측: {color}{direction}\033[0m  (확률 {prob[pred]:.1%})")
    print(f"{'─'*45}")

    if hasattr(model, "feature_importances_"):
        top10 = pd.Series(model.feature_importances_, index=features) \
                  .sort_values(ascending=False).head(10)
        print("피처 중요도 Top 10:")
        for feat, imp in top10.items():
            print(f"  {feat:<35s} {imp:>6.0f}")


# ─────────────────────────────────────────
# 5. API용 단일 종목 예측 (dict 반환)
# ─────────────────────────────────────────
def predict_ticker(prefix: str) -> dict:
    """'삼성' 또는 'SK'를 받아 내일 방향성 예측 결과를 dict로 반환"""
    df, features = build_dataframe()
    target_col = f"{prefix}_target"
    df[target_col] = (df[f"{prefix}_close"].shift(-1) > df[f"{prefix}_close"]).astype(int)

    # target NaN(마지막 행 shift(-1) 결과)도 제거하고 walk-forward 수행
    df_clean = df.dropna(subset=features + [target_col])
    results = walk_forward(df_clean, features, target_col)

    best_name, best_acc = None, -1.0
    for name, res in results.items():
        if res["accuracy"] > best_acc:
            best_acc, best_name = res["accuracy"], name

    model = MODELS[best_name]
    # 오늘 피처: target NaN인 마지막 행 (예측 대상)
    today_row = df[df[target_col].isna()].iloc[[-1]] if df[target_col].isna().any() else df.iloc[[-1]]
    X = df_clean[features]
    y = df_clean[target_col]

    X_train = X
    y_train = y
    X_today = today_row[features]

    mask = ~X_train.isna().any(axis=1)
    X_train, y_train = X_train[mask], y_train[mask]

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_train)
    X_today_s = scaler.transform(X_today)

    model.fit(X_tr_s, y_train)
    pred = int(model.predict(X_today_s)[0])
    prob = model.predict_proba(X_today_s)[0]

    return {
        "direction":     "up" if pred == 1 else "down",
        "probability":   round(float(prob[pred]), 4),
        "bestModel":     best_name,
        "modelAccuracy": round(float(best_acc), 4),
    }


# ─────────────────────────────────────────
# 6. Main
# ─────────────────────────────────────────
def main():
    df, features = build_dataframe()

    for prefix in ["삼성", "SK"]:
        target_col = f"{prefix}_target"
        df[target_col] = (df[f"{prefix}_close"].shift(-1) > df[f"{prefix}_close"]).astype(int)

        print(f"\n{'='*45}")
        print(f"[{prefix}] Walk-Forward 검증")
        print(f"{'='*45}")

        results = walk_forward(df.dropna(subset=features), features, target_col)

        best_name, best_acc = None, -1
        for name, res in results.items():
            acc = res["accuracy"]
            r   = res["report"]
            print(f"  {name:<14s} 정확도 {acc:.1%}  "
                  f"| 상승 F1 {r['상승']['f1-score']:.2f}  "
                  f"| 하락 F1 {r['하락/보합']['f1-score']:.2f}")
            if acc > best_acc:
                best_acc, best_name = acc, name

        print(f"\n  🏆 선택: {best_name} (정확도 {best_acc:.1%})")
        train_and_predict(df, features, target_col, prefix, best_name)

    print(f"\n{'='*45}\n")


if __name__ == "__main__":
    main()