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

# --- [2. 카테고리 자동 분류 함수] ---
def categorize_merchant(name):
    if any(keyword in name for keyword in ['마트', '편의점', '식당', '배달', '쿠팡', '컬리']):
        return '식비/생활'
    elif any(keyword in name for keyword in ['소아과', '병원', '약국', '내과', '치과']):
        return '의료/건강'
    elif any(keyword in name for keyword in ['학원', '교육', '서점', '독서실']):
        return '교육/육아'
    elif any(keyword in name for keyword in ['택시', '주유', '버스', '지하철', '철도']):
        return '교통/차량'
    elif any(keyword in name for keyword in ['카페', '스타벅스', '커피']):
        return '카페/간식'
    return '기타/쇼핑'

# --- [3. 초기 세팅] ---
st.set_page_config(page_title="etsongji 스마트 가계부", layout="wide")
if 'ledger' not in st.session_state:
    st.session_state['ledger'] = load_ledger()

st.title("👩‍👧‍👦 etsongji님의 분야별 지출 분석 가계부")

# --- [4. 파일 업로드 및 자동 분류 저장] ---
st.subheader("📂 카드 명세서 내역 추가")
uploaded_file = st.file_uploader("현대카드 명세서를 올려주세요", type=["xls", "xlsx", "csv"])

if uploaded_file:
    try:
        # 파일 읽기 및 컬럼 자동 탐색
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

            # 가맹점 이름을 보고 자동으로 분류를 채웁니다.
            refined['분류'] = refined['가맹점'].apply(categorize_merchant)

            st.write("📊 분석된 내역 미리보기 (카테고리 자동 분류)")
            st.dataframe(refined.head())

            if st.button("💾 이 내역을 가계부에 누적 저장"):
                updated_df = pd.concat([st.session_state['ledger'], refined]).drop_duplicates()
                st.session_state['ledger'] = updated_df
                save_ledger(updated_df)
                st.success("카테고리별로 저장되었습니다!")
                st.rerun()
    except Exception as e:
        st.error(f"분석 오류: {e}")

# --- [5. 분야별 분석 시각화] ---
st.divider()
if not st.session_state['ledger'].empty:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🥧 분야별 지출 비중")
        # 분류별 합계 계산
        category_sum = st.session_state['ledger'].groupby('분류')['금액'].sum().reset_index()
        fig_pie = px.pie(category_sum, values='금액', names='분류', hole=0.3, 
                         title="어디에 가장 많이 썼을까요?")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("💰 분야별 지출 금액")
        fig_bar = px.bar(category_sum.sort_values(by='금액', ascending=False), 
                         x='분류', y='금액', text_auto=',.0f', color='분류')
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📝 전체 내역 상세보기")
    st.dataframe(st.session_state['ledger'].sort_values(by='날짜', ascending=False), use_container_width=True)
else:
    st.info("명세서를 업로드하면 분야별 분석 차트가 나타납니다.")
