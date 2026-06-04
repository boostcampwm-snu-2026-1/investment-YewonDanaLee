import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

# 1. 데이터 로드 및 날짜 전처리 함수
def load_and_preprocess():
    # 삼성 데이터 로드 (첫 번째 열이 날짜라고 가정)
    df_sam = pd.read_excel("삼성_history.xlsx")
    df_sam.columns = ["Date", "Close", "Open", "High", "Low", "Volume", "Change_Pct"]
    
    # 엑셀 깨짐(###) 예방을 위해 datetime으로 안전하게 파싱 유도 
    # (실제 엑셀 내부에는 타임스탬프 값이 살아있으므로 pd.to_datetime이 해결해줍니다)
    df_sam["Date"] = pd.to_datetime(df_sam["Date"], errors="coerce")
    
    # ETF 데이터 로드
    df_etf = pd.read_excel("ETF.xlsx")
    df_etf.columns = ["Date", "SOX", "DRAM_ETF", "EWY", "KORU"]
    
    # '2026년 6월 3일' 형식 전처리
    if df_etf["Date"].dtype == "object":
        df_etf["Date"] = df_etf["Date"].str.replace("년 ", "-").str.replace("월 ", "-").str.replace("일", "")
    df_etf["Date"] = pd.to_datetime(df_etf["Date"], errors="coerce")
    
    # 날짜 기준 병합 및 오름차순(과거 -> 최신) 정렬
    df = pd.merge(df_sam, df_etf, on="Date", how="inner")
    df = df.dropna().sort_values("Date").reset_index(drop=True)
    
    # 수치형 정규화 (Volume의 'M' 제거 등)
    if df["Volume"].dtype == "object":
        df["Volume"] = df["Volume"].str.replace("M", "").astype(float) * 1000000
    if df["Change_Pct"].dtype == "object":
        df["Change_Pct"] = df["Change_Pct"].str.replace("%", "").astype(float)
        
    return df

# 2. 시계열 피처 엔지니어링
def create_features(df):
    # 내일 종가가 오늘 종가보다 올랐으면 1, 내렸거나 같으면 0 (Target)
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    
    # 오늘 자 데이터들이 피처(X)가 됨
    feature_cols = ["Close", "Open", "High", "Low", "Volume", "Change_Pct", "SOX", "DRAM_ETF", "EWY", "KORU"]
    
    # 예측을 위해 마지막 행(가장 최신 날짜)은 따로 보관 (내일 주가를 예측할 피처 소스)
    latest_predict_features = df[feature_cols].iloc[[-1]]
    
    # 학습 세트에서는 마지막 행 제외 (내일 타겟이 없으므로)
    df_model = df.dropna().copy()
    
    X = df_model[feature_cols]
    y = df_model["Target"]
    
    return X, y, latest_predict_features

# 3. 최적의 시계열 모델 탐색 함수
def evaluate_models(X, y):
    models = {
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=100, random_state=42, eval_metric="logloss"),
        "LightGBM": LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
    }
    
    # 시계열 교차 검증 객체 (과거 데이터로 미래 순차 검증)
    tscv = TimeSeriesSplit(n_splits=3)
    best_model_name = None
    best_score = -1
    best_model = None
    
    for name, model in models.items():
        scores = []
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # 스케일링 기본 적용
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            model.fit(X_train_scaled, y_train)
            preds = model.predict(X_test_scaled)
            scores.append(accuracy_score(y_test, preds))
            
        avg_accuracy = np.mean(scores)
        print(f"[{name}] 시계열 교차 검증 평균 정확도: {avg_accuracy:.4f}")
        
        if avg_accuracy > best_score:
            best_score = avg_accuracy
            best_model_name = name
            best_model = model
            
    print(f"\n🏆 최종 선택된 최고 모델: {best_model_name} (정확도: {best_score:.4f})")
    return best_model, X # 전체 데이터 기반 재학습용

# 4. 메인 실행 및 결과 출력
def main():
    # 1) 데이터 전처리
    df = load_and_preprocess()
    
    # 2) 피처 생성
    X, y, latest_x = create_features(df)
    
    if len(X) < 10:
        print("데이터 행 수가 너무 적어 시계열 학습 모델을 구동할 수 없습니다. 데이터를 늘려주세요.")
        return
        
    # 3) 모델 비교 및 최적 모델 선정
    best_model, all_X = evaluate_models(X, y)
    
    # 4) 전체 데이터로 최종 학습 진행 후 내일 방향성 예측
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(all_X)
    best_model.fit(X_scaled, y)
    
    latest_x_scaled = scaler.transform(latest_x)
    prediction = best_model.predict(latest_x_scaled)[0]
    
    # 5) 시각적인 빨강/파랑 결과 출력
    print("\n" + "="*40)
    print(f"🔮 가장 최신 데이터 날짜 기준: {df['Date'].iloc[-1].strftime('%Y-%m-%d')}")
    if prediction == 1:
        # 터미널 전용 Red 텍스트 에스케이프 시퀀스 (\033[91m)
        print("▶ 다음 거래일 삼성전자 종가 예측 결과: \033[91m▲ [빨강] 상승\033[0m")
    else:
        # 터미널 전용 Blue 텍스트 에스케이프 시퀀스 (\033[94m)
        print("▶ 다음 거래일 삼성전자 종가 예측 결과: \033[94m▼ [파랑] 하락\033[0m")
    print("="*40)

if __name__ == "__main__":
    main()