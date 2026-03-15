import streamlit as st
import pandas as pd
import os
import plotly.express as px

# --- [1. 데이터베이스 설정] ---
DB_FILE = "ledger_data.csv"

def load_ledger():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['날짜', '가맹점', '금액', '분류'])

def save_ledger(df):
    df.to_csv(DB_FILE, index=False)

def categorize_merchant(name):
    if any(keyword in name for keyword in ['마트', '편의점', '식당', '배달', '쿠팡', '컬리', '홈플러스']): return '식비/생활'
    elif any(keyword in name for keyword in ['소아과', '병원', '약국', '내과', '의원']): return '의료/건강'
    elif any(keyword in name for keyword in ['학원', '교육', '학습지', '독서실']): return '교육/육아'
    elif any(keyword in name for keyword in ['택시', '주유', '버스', '지하철']): return '교통/차량'
    elif any(keyword in name for keyword in ['카페', '커피', '베이커리']): return '카페/간식'
    return '기타/쇼핑'

# --- [2. 초기 세팅] ---
st.set_page_config(page_title="etsongji 연말정산 가계부", layout="wide")
if 'ledger' not in st.session_state:
    st.session_state['ledger'] = load_ledger()

# --- [3. 사이드바: 내 연봉 및 설정] ---
st.sidebar.header("👤 내 정보 설정")
salary = st.sidebar.number_input("나의 총급여(연봉)", value=50000000, step=1000000)
is_single_parent = st.sidebar.checkbox("한부모 공제 적용", value=True)

# 계산 로직
threshold = salary * 0.25
total_spent = st.session_state['ledger']['금액'].sum()

# --- [4. 상단 대시보드: 연말정산 핵심 요약] ---
st.title("👩‍👧‍👦 etsongji님의 연말정산 & 분야별 가계부")
st.markdown("---")

col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.metric("현재 총 사용액", f"{total_spent:,.0f}원")
with col_info2:
    st.metric("소득공제 문턱", f"{threshold:,.0f}원")
with col_info3:
    diff = threshold - total_spent
    if diff > 0:
        st.metric("문턱까지 남은 금액", f"{diff:,.0f}원", delta_color="inverse")
    else:
        st.metric("공제 대상 금액", f"{abs(diff):,.0f}원", delta="문턱 돌파!")

# 문턱 그래프
st.subheader("🏁 소득공제 문턱 도달률")
progress = min(1.0, total_spent / threshold) if threshold > 0 else 0
st.progress(progress)
if total_spent >= threshold:
    st.success("🎉 축하합니다! 지금부터 쓰는 돈은 모두 세금 환급으로 돌아옵니다. (체크카드/전통시장 유리)")
else:
    st.info(f"💡 연봉의 25%({threshold:,.0f}원)를 채워야 공제가 시작됩니다. 조금만 더 힘내세요!")

# --- [5. 분야별 지출 분석 (가계부 기능)] ---
st.divider()
st.subheader("📊 어디에 가장 많이 썼을까요?")

if not st.session_state['ledger'].empty:
    c1, c2 = st.columns([1, 1])
    category_sum = st.session_state['ledger'].groupby('분류')['금액'].sum().reset_index()
    
    with c1:
        fig_pie = px.pie(category_sum, values='금액', names='분류', hole=0.4, title="지출 항목 비중")
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        fig_bar = px.bar(category_sum.sort_values('금액'), x='금액', y='분류', orientation='h', 
                         title="항목별 지출 금액", color='분류', text_auto=',.0f')
        st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.warning("아직 데이터가 없습니다. 아래에서 현대카드 명세서를 업로드해 주세요!")

# --- [6. 파일 업로드 섹션] ---
st.divider()
st.subheader("📂 신규 명세서 내역 추가")
uploaded_file = st.file_uploader("현대카드 xls 파일을 올려주세요", type=["xls", "xlsx", "csv"])

if uploaded_file:
    # (파일 분석 로직은 이전과 동일)
    try:
        try: data = pd.read_excel(uploaded_file)
        except:
            uploaded_file.seek(0)
            data = pd.read_html(uploaded_file)[0]
        
        data.columns = [str(c).strip() for c in data.columns]
        date_col = next((c for c in data.columns if '이용일' in c), None)
        merchant_col = next((c for c in data.columns if '이용가맹점' in c), None)
        amount_col = next((c for c in data.columns if '이용금액' in c or '결제원금' in c), None)

        if amount_col:
            new_records = data.dropna(subset=[date_col, amount_col])
            new_records = new_records[~new_records[merchant_col].astype(str).str.contains('소계|합계|할부', na=False)]
            
            refined = pd.DataFrame({
                '날짜': pd.to_datetime(new_records[date_col]).dt.strftime('%Y-%m-%d'),
                '가맹점': new_records[merchant_col],
                '금액': pd.to_numeric(new_records[amount_col], errors='coerce'),
            }).dropna()
            refined['분류'] = refined['가맹점'].apply(categorize_merchant)

            st.dataframe(refined.head())
            if st.button("💾 이 내역을 가계부에 누적 저장"):
                st.session_state['ledger'] = pd.concat([st.session_state['ledger'], refined]).drop_duplicates()
                save_ledger(st.session_state['ledger'])
                st.rerun()
    except Exception as e:
        st.error(f"오류: {e}")

# --- [7. 최근 내역 리스트] ---
st.subheader("📝 전체 지출 내역")
st.dataframe(st.session_state['ledger'].sort_values('날짜', ascending=False), use_container_width=True)
