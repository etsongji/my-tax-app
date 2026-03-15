import streamlit as st
import pandas as pd
import os

# --- [파일 저장 관련 함수] ---
DB_FILE = "user_data.csv"

def load_data():
    """저장된 데이터를 불러옵니다."""
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE).iloc[0].to_dict()
    return {"salary": 50000000, "credit_card": 12000000, "debit_cash": 5000000, "market": 500000}

def save_data(data_dict):
    """데이터를 파일에 저장합니다."""
    pd.DataFrame([data_dict]).to_csv(DB_FILE, index=False)

# --- [초기 설정] ---
st.set_page_config(page_title="우리집 연말정산 가계부", layout="wide")
saved_val = load_data()

st.title("👩‍👧‍👦 나만의 연말정산 & 가계부")

# --- [사이드바: 입력 및 저장] ---
st.sidebar.header("📋 내 정보 설정")
salary = st.sidebar.number_input("나의 연봉", value=int(saved_val['salary']))
credit_card = st.sidebar.number_input("신용카드 총액", value=int(saved_val['credit_card']))
debit_cash = st.sidebar.number_input("체크카드/현금", value=int(saved_val['debit_cash']))
market_spent = st.sidebar.number_input("전통시장", value=int(saved_val['market']))

if st.sidebar.button("💾 현재 설정값 저장하기"):
    current_data = {
        "salary": salary,
        "credit_card": credit_card,
        "debit_cash": debit_cash,
        "market": market_spent
    }
    save_data(current_data)
    st.sidebar.success("데이터가 안전하게 저장되었습니다!")

# --- [계산 및 시각화 로직] ---
threshold = salary * 0.25
total_spent = credit_card + debit_cash + market_spent

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("🏁 소득공제 문턱 도달률")
    st.progress(min(1.0, total_spent / threshold))
    st.write(f"현재 총 사용액: **{total_spent:,.0f}원** / 문턱: **{threshold:,.0f}원**")

# --- [현대카드 분석 섹션] ---
st.divider()
st.subheader("📂 현대카드 명세서 추가")
uploaded_file = st.file_uploader("명세서 업로드", type=["xls", "csv", "xlsx"])

if uploaded_file:
    # (기존의 현대카드 분석 로직이 들어가는 자리)
    # 분석 후 버튼을 누르면 위의 credit_card 변수에 합산되도록 구현
    st.info("파일을 분석하여 '신용카드 총액'에 더한 후 [저장하기]를 눌러주세요.")

# --- [가계부 확장 아이디어] ---
st.divider()
st.subheader("📅 월별 가계부 기록 (확장 예정)")
st.caption("여기에 월별 지출 내역을 누적해서 기록하는 기능을 추가할 수 있습니다.")