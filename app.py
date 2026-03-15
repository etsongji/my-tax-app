import streamlit as st
import pandas as pd
import os

# --- [1. 데이터 로드/저장 로직 개선] ---
DB_FILE = "user_data.csv"

def load_data():
    default_values = {"salary": 50000000, "credit_card": 0, "debit_cash": 0, "market": 0}
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                return df.iloc[0].to_dict()
        except Exception:
            pass # 에러 나면 그냥 기본값 반환
    return default_values

def save_data(data_dict):
    pd.DataFrame([data_dict]).to_csv(DB_FILE, index=False)

# --- [2. 앱 초기 설정 및 데이터 불러오기] ---
st.set_page_config(page_title="etsongji 연말정산 가계부", layout="wide")
saved_val = load_data()

# 세션 상태에 저장 (파일 업로드 시 즉시 반영을 위해)
if 'credit_card_val' not in st.session_state:
    st.session_state['credit_card_val'] = saved_val['credit_card']

st.title("👩‍👧‍👦 etsongji님의 스마트 연말정산 가계부")

# --- [3. 사이드바: 입력 및 저장] ---
st.sidebar.header("📋 기본 설정")
salary = st.sidebar.number_input("나의 연봉", value=int(saved_val['salary']))
# 신용카드 총액은 파일 업로드 결과와 연동됩니다.
credit_card = st.sidebar.number_input("신용카드 총액", value=int(st.session_state['credit_card_val']))
debit_cash = st.sidebar.number_input("체크카드/현금", value=int(saved_val['debit_cash']))
market_spent = st.sidebar.number_input("전통시장", value=int(saved_val['market']))

if st.sidebar.button("💾 이 설정값을 영구 저장하기"):
    save_data({
        "salary": salary,
        "credit_card": credit_card,
        "debit_cash": debit_cash,
        "market": market_spent
    })
    st.sidebar.success("데이터가 저장되었습니다!")

# --- [4. 대시보드 시각화] ---
threshold = salary * 0.25
total_spent = credit_card + debit_cash + market_spent

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("🏁 소득공제 문턱 도달률")
    progress = min(1.0, total_spent / threshold) if threshold > 0 else 0
    st.progress(progress)
    st.write(f"현재 총액: **{total_spent:,.0f}원** / 문턱: **{threshold:,.0f}원**")
    
    if total_spent < threshold:
        st.warning(f"문턱까지 **{threshold - total_spent:,.0f}원** 더 써야 합니다.")
    else:
        st.success("🎉 문턱 돌파! 이제부터 환급액이 쌓입니다.")

# --- [5. 현대카드 파일 분석 및 누적] ---
st.divider()
st.subheader("📂 현대카드 명세서 합산")
uploaded_file = st.file_uploader("명세서 업로드 (xls, csv)", type=["xls", "xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.xls'):
            try: data = pd.read_excel(uploaded_file, engine='xlrd')
            except: 
                uploaded_file.seek(0)
                data = pd.read_html(uploaded_file)[0]
        else:
            data = pd.read_excel(uploaded_file)

        # 복잡한 컬럼명에서 '이용금액' 추출 (이미지 분석 결과 반영)
        target_col = next((c for c in data.columns if '이용금액' in str(c)), None)
        
        if target_col:
            vals = pd.to_numeric(data[target_col], errors='coerce').dropna()
            file_total = int(vals[vals > 0].sum())
            st.metric("이 파일에서 찾은 금액", f"{file_total:,.0f} 원")
            
            if st.button("📊 이 금액을 현재 총액에 더하기"):
                st.session_state['credit_card_val'] += file_total
                st.rerun()
    except Exception as e:
        st.error(f"파일 분석 오류: {e}")
