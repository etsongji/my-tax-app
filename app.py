import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import numpy as np

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="연말정산 카드공제 최적화",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CSS 스타일
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

    * { font-family: 'Noto Sans KR', sans-serif; }

    .main { background: #0f1117; }

    /* 메트릭 카드 */
    .metric-card {
        background: linear-gradient(135deg, #1e2130 0%, #252840 100%);
        border: 1px solid #2e3250;
        border-radius: 16px;
        padding: 20px 24px;
        margin: 8px 0;
    }
    .metric-label {
        font-size: 12px;
        color: #8b93b5;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #e8ecf7;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-value.green { color: #4ade80; }
    .metric-value.yellow { color: #fbbf24; }
    .metric-value.red { color: #f87171; }
    .metric-value.blue { color: #60a5fa; }

    /* 추천 박스 */
    .recommend-box {
        background: linear-gradient(135deg, #1a2744 0%, #1e3a5f 100%);
        border: 1px solid #2563eb44;
        border-left: 4px solid #3b82f6;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 10px 0;
    }
    .recommend-box.success {
        background: linear-gradient(135deg, #0f2a1e 0%, #14352a 100%);
        border-color: #16a34a44;
        border-left-color: #22c55e;
    }
    .recommend-box.warning {
        background: linear-gradient(135deg, #2a1f0f 0%, #352a14 100%);
        border-color: #d97706;
        border-left-color: #f59e0b;
    }
    .recommend-box h4 {
        margin: 0 0 8px 0;
        font-size: 14px;
        font-weight: 700;
        color: #93c5fd;
    }
    .recommend-box.success h4 { color: #86efac; }
    .recommend-box.warning h4 { color: #fde68a; }
    .recommend-box p {
        margin: 0;
        font-size: 13px;
        color: #cbd5e1;
        line-height: 1.6;
    }

    /* 섹션 헤더 */
    .section-header {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #4b5563;
        padding: 12px 0 8px 0;
        border-bottom: 1px solid #1e2130;
        margin-bottom: 16px;
    }

    /* 프로그레스 바 커스텀 */
    .progress-container {
        background: #1e2130;
        border-radius: 100px;
        height: 12px;
        overflow: hidden;
        margin: 8px 0;
    }
    .progress-bar {
        height: 100%;
        border-radius: 100px;
        transition: width 0.5s ease;
    }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        background: #1e2130;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #6b7280;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #2e3250 !important;
        color: #e8ecf7 !important;
    }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: #0d0f1a;
        border-right: 1px solid #1e2130;
    }

    /* 데이터프레임 */
    .dataframe { font-size: 12px; }

    /* 알림 박스 */
    .info-tag {
        display: inline-block;
        background: #1e3a5f;
        color: #93c5fd;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 100px;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 세법 계산 함수들
# ─────────────────────────────────────────────

def get_deduction_limit(annual_salary: float) -> float:
    """총급여에 따른 카드공제 기본 한도"""
    if annual_salary <= 7000:
        return 300
    elif annual_salary <= 12000:
        return 250
    else:
        return 200

def get_tax_rate(annual_salary: float) -> float:
    """소득세율 (지방소득세 포함 10% 가산)"""
    # 근로소득공제 후 대략적인 과세표준 추정
    if annual_salary <= 1400:
        return 0.06 * 1.1
    elif annual_salary <= 5000:
        return 0.15 * 1.1
    elif annual_salary <= 8800:
        return 0.24 * 1.1
    elif annual_salary <= 15000:
        return 0.35 * 1.1
    else:
        return 0.38 * 1.1

def calc_deduction(
    credit: float,      # 신용카드
    check: float,       # 체크카드
    cash: float,        # 현금영수증
    market: float,      # 전통시장
    transit: float,     # 대중교통
    culture: float,     # 도서/공연/미술관
    annual_salary: float,
) -> dict:
    """
    카드공제 계산 (법정 공제 순서 적용)
    신용카드 → 체크/현금 → 전통시장/교통/문화 순서
    """
    threshold = annual_salary * 0.25  # 총급여 25%
    base_limit = get_deduction_limit(annual_salary)

    total_used = credit + check + cash + market + transit + culture

    if total_used <= threshold:
        return {
            "threshold": threshold,
            "total_used": total_used,
            "over_threshold": 0,
            "credit_deduction": 0,
            "check_deduction": 0,
            "cash_deduction": 0,
            "market_deduction": 0,
            "transit_deduction": 0,
            "culture_deduction": 0,
            "total_deduction": 0,
            "base_limit": base_limit,
            "tax_saving": 0,
            "is_over": False,
        }

    remaining = threshold  # 문턱값 소진 추적
    
    # 공제율
    CREDIT_RATE = 0.15
    CHECK_RATE = 0.30
    CASH_RATE = 0.30
    MARKET_RATE = 0.40
    TRANSIT_RATE = 0.40
    CULTURE_RATE = 0.30

    # 법정 순서: 신용카드 먼저 문턱값 소진
    credit_over = max(0, credit - remaining)
    remaining = max(0, remaining - credit)

    check_over = max(0, check - remaining)
    remaining = max(0, remaining - check)

    cash_over = max(0, cash - remaining)
    remaining = max(0, remaining - cash)

    market_over = max(0, market - remaining)
    remaining = max(0, remaining - market)

    transit_over = max(0, transit - remaining)
    remaining = max(0, remaining - transit)

    culture_over = max(0, culture - remaining)

    # 공제금액 계산
    credit_ded = credit_over * CREDIT_RATE
    check_ded = check_over * CHECK_RATE
    cash_ded = cash_over * CASH_RATE
    market_ded = market_over * MARKET_RATE
    transit_ded = transit_over * TRANSIT_RATE
    culture_ded = culture_over * CULTURE_RATE

    # 기본 한도 적용 (신용+체크+현금)
    base_sum = credit_ded + check_ded + cash_ded
    base_sum_capped = min(base_sum, base_limit)

    # 전통시장 추가 한도 100만원
    market_ded_capped = min(market_ded, 100)
    # 대중교통 추가 한도 100만원
    transit_ded_capped = min(transit_ded, 100)
    # 문화비 추가 한도 100만원 (총급여 7천 이하만)
    if annual_salary <= 7000:
        culture_ded_capped = min(culture_ded, 100)
    else:
        culture_ded_capped = 0

    total_deduction = base_sum_capped + market_ded_capped + transit_ded_capped + culture_ded_capped
    tax_rate = get_tax_rate(annual_salary)
    tax_saving = total_deduction * tax_rate

    return {
        "threshold": threshold,
        "total_used": total_used,
        "over_threshold": max(0, total_used - threshold),
        "credit_deduction": credit_ded,
        "check_deduction": check_ded,
        "cash_deduction": cash_ded,
        "market_deduction": market_ded,
        "transit_deduction": transit_ded,
        "culture_deduction": culture_ded,
        "base_sum": base_sum,
        "base_sum_capped": base_sum_capped,
        "market_ded_capped": market_ded_capped,
        "transit_ded_capped": transit_ded_capped,
        "culture_ded_capped": culture_ded_capped,
        "total_deduction": total_deduction,
        "base_limit": base_limit,
        "tax_rate": tax_rate,
        "tax_saving": tax_saving,
        "is_over": True,
    }


def recommend_strategy(
    result: dict,
    annual_salary: float,
    credit: float, check: float, cash: float,
    market: float, transit: float, culture: float,
    current_month: int,
) -> list:
    """남은 기간 최적 전략 추천"""
    recs = []
    remaining_months = max(1, 12 - current_month)
    threshold = result["threshold"]
    total_used = result["total_used"]
    base_limit = result["base_limit"]

    # 문턱값 미달
    if not result["is_over"]:
        gap = threshold - total_used
        monthly = gap / remaining_months
        recs.append({
            "type": "warning",
            "title": "⚠️ 아직 공제 구간 미진입",
            "body": f"총급여 25% 기준 {threshold:.0f}만원까지 추가로 <b>{gap:.0f}만원</b> 사용해야 공제 시작됩니다. "
                    f"남은 {remaining_months}개월 동안 월 <b>{monthly:.0f}만원</b>씩 더 쓰시면 문턱값 도달 가능해요. "
                    f"(신용카드로 먼저 채우는 게 유리)"
        })
        return recs

    # 문턱값 초과 → 고공제율 카드 권장
    credit_ded = result["credit_deduction"]
    check_ded = result["check_deduction"]
    base_sum = credit_ded + check_ded + result["cash_deduction"]
    base_limit = result["base_limit"]
    remaining_base = base_limit - min(base_sum, base_limit)

    if remaining_base > 10:
        monthly_needed = remaining_base / remaining_months / 0.30
        recs.append({
            "type": "info",
            "title": "💳 체크카드 / 현금영수증 우선 사용 권장",
            "body": f"기본 한도까지 <b>{remaining_base:.0f}만원</b> 공제 여유가 있습니다. "
                    f"체크카드(30%)로 月 <b>{monthly_needed:.0f}만원</b>씩 사용하면 한도를 꽉 채울 수 있어요."
        })

    # 전통시장 추가 한도
    market_remaining = 100 - result["market_ded_capped"]
    if market_remaining > 5:
        monthly_market = market_remaining / remaining_months / 0.40
        recs.append({
            "type": "info",
            "title": "🏪 전통시장 추가 한도 활용",
            "body": f"전통시장 공제 추가한도 100만원 중 <b>{market_remaining:.0f}만원</b> 여유가 있습니다. "
                    f"月 <b>{monthly_market:.0f}만원</b> 이상 전통시장 이용 시 추가 절세 가능해요."
        })

    # 대중교통 추가 한도
    transit_remaining = 100 - result["transit_ded_capped"]
    if transit_remaining > 5:
        monthly_transit = transit_remaining / remaining_months / 0.40
        recs.append({
            "type": "info",
            "title": "🚌 대중교통 추가 한도 활용",
            "body": f"대중교통 공제 추가한도 100만원 중 <b>{transit_remaining:.0f}만원</b> 여유가 있습니다. "
                    f"月 <b>{monthly_transit:.0f}만원</b> 이상 교통카드 이용 권장이에요."
        })

    # 한도 초과 경고
    if base_sum > base_limit:
        over = base_sum - base_limit
        recs.append({
            "type": "success",
            "title": "✅ 기본 카드 공제 한도 달성!",
            "body": f"신용/체크/현금 기본 공제 한도 {base_limit:.0f}만원을 <b>{over:.0f}만원 초과</b>했습니다. "
                    f"이제 전통시장·대중교통·문화비 추가 한도 집중 공략하세요!"
        })

    if result["tax_saving"] > 0:
        recs.append({
            "type": "success",
            "title": f"💸 예상 절세액 {result['tax_saving']:.0f}만원",
            "body": f"현재 카드공제 {result['total_deduction']:.0f}만원 × 소득세율 {result['tax_rate']*100:.1f}% 기준입니다."
        })

    return recs


# ─────────────────────────────────────────────
# CSV 샘플 생성 함수
# ─────────────────────────────────────────────
def make_sample_csv():
    months = list(range(1, 13))
    data = {
        "월": months,
        "신용카드(만원)": [80, 75, 90, 85, 95, 100, 88, 92, 78, 82, 110, 120],
        "체크카드(만원)": [30, 25, 35, 40, 30, 45, 38, 42, 35, 28, 50, 60],
        "현금영수증(만원)": [10, 8, 12, 15, 10, 18, 12, 14, 10, 8, 20, 25],
        "전통시장(만원)": [5, 5, 8, 10, 6, 12, 8, 10, 7, 5, 15, 20],
        "대중교통(만원)": [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8],
        "도서_공연_문화(만원)": [0, 5, 0, 8, 0, 10, 0, 5, 0, 8, 0, 10],
    }
    return pd.DataFrame(data)


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 16px 0 24px 0;'>
        <div style='font-size:22px; font-weight:900; color:#e8ecf7; letter-spacing:-0.02em;'>💰 연말정산</div>
        <div style='font-size:11px; color:#4b5563; letter-spacing:0.1em; margin-top:4px;'>CARD DEDUCTION OPTIMIZER</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">기본 정보</div>', unsafe_allow_html=True)
    annual_salary = st.number_input(
        "추정 연봉 (만원)",
        min_value=1000, max_value=100000,
        value=5000, step=100,
        help="세전 총급여액을 입력하세요"
    )
    current_month = st.slider(
        "현재 월",
        min_value=1, max_value=12, value=3,
        help="현재 기준월 (남은 기간 계산에 사용)"
    )

    st.markdown('<div class="section-header" style="margin-top:16px;">기준 정보</div>', unsafe_allow_html=True)
    threshold_val = annual_salary * 0.25
    limit_val = get_deduction_limit(annual_salary)
    tax_rate_val = get_tax_rate(annual_salary) * 100

    st.markdown(f"""
    <div class="metric-card" style="padding:12px 16px; margin:4px 0;">
        <div class="metric-label">공제 시작 기준금액</div>
        <div class="metric-value yellow" style="font-size:20px;">{threshold_val:.0f}만원</div>
    </div>
    <div class="metric-card" style="padding:12px 16px; margin:4px 0;">
        <div class="metric-label">기본 공제 한도</div>
        <div class="metric-value blue" style="font-size:20px;">{limit_val}만원</div>
    </div>
    <div class="metric-card" style="padding:12px 16px; margin:4px 0;">
        <div class="metric-label">적용 세율 (지방세 포함)</div>
        <div class="metric-value green" style="font-size:20px;">{tax_rate_val:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header" style="margin-top:16px;">공제율 참고</div>', unsafe_allow_html=True)
    rates_data = {
        "구분": ["신용카드", "체크카드", "현금영수증", "전통시장", "대중교통", "도서/공연"],
        "공제율": ["15%", "30%", "30%", "40%", "40%", "30%"],
        "추가한도": ["-", "-", "-", "+100만", "+100만", "+100만"]
    }
    st.dataframe(pd.DataFrame(rates_data), hide_index=True, use_container_width=True)


# ─────────────────────────────────────────────
# 메인 영역
# ─────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:28px; font-weight:900; color:#e8ecf7; margin-bottom:4px; letter-spacing:-0.02em;'>
    카드공제 최적화 계산기
</h1>
<p style='color:#6b7280; font-size:13px; margin-bottom:24px;'>
    월별 카드 사용액을 입력하거나 CSV로 업로드하면 최적 전략을 제안해드립니다
</p>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📥 데이터 입력", "📊 현황 분석", "💡 최적화 전략", "📤 결과 내보내기"])


# ─────────────────────────────────────────────
# TAB 1: 데이터 입력
# ─────────────────────────────────────────────
with tab1:
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown("#### 📄 CSV 업로드")
        st.markdown("""
        <div style='background:#1e2130; border-radius:10px; padding:12px 16px; margin-bottom:12px;'>
        <div style='font-size:12px; color:#8b93b5;'>
        📌 CSV 형식: <span class="info-tag">월</span> <span class="info-tag">신용카드(만원)</span> 
        <span class="info-tag">체크카드(만원)</span> <span class="info-tag">현금영수증(만원)</span>
        <span class="info-tag">전통시장(만원)</span> <span class="info-tag">대중교통(만원)</span>
        <span class="info-tag">도서_공연_문화(만원)</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

        sample_df = make_sample_csv()
        csv_bytes = sample_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "📥 샘플 CSV 다운로드",
            data=csv_bytes,
            file_name="카드사용내역_샘플.csv",
            mime="text/csv",
        )

        uploaded = st.file_uploader("CSV 파일 업로드", type=["csv"])
        if uploaded:
            try:
                df_upload = pd.read_csv(uploaded, encoding="utf-8-sig")
                st.success(f"✅ {len(df_upload)}개월 데이터 로드 완료!")
                st.dataframe(df_upload, hide_index=True, use_container_width=True)
                st.session_state["df_card"] = df_upload
            except Exception as e:
                try:
                    df_upload = pd.read_csv(uploaded, encoding="cp949")
                    st.success(f"✅ {len(df_upload)}개월 데이터 로드 완료!")
                    st.dataframe(df_upload, hide_index=True, use_container_width=True)
                    st.session_state["df_card"] = df_upload
                except:
                    st.error(f"파일 읽기 오류: {e}")

    with col_b:
        st.markdown("#### ✏️ 직접 입력")
        st.caption("현재 월까지만 입력하시면 됩니다")

        input_months = list(range(1, current_month + 1))
        month_labels = [f"{m}월" for m in input_months]

        default_credit = [80] * len(input_months)
        default_check  = [30] * len(input_months)
        default_cash   = [10] * len(input_months)
        default_market = [5]  * len(input_months)
        default_transit= [8]  * len(input_months)
        default_culture= [0]  * len(input_months)

        manual_df = pd.DataFrame({
            "월": month_labels,
            "신용카드": default_credit,
            "체크카드": default_check,
            "현금영수증": default_cash,
            "전통시장": default_market,
            "대중교통": default_transit,
            "도서공연문화": default_culture,
        })

        edited_df = st.data_editor(
            manual_df,
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "월": st.column_config.TextColumn("월", disabled=True),
                "신용카드": st.column_config.NumberColumn("신용카드(만원)", min_value=0, format="%d"),
                "체크카드": st.column_config.NumberColumn("체크카드(만원)", min_value=0, format="%d"),
                "현금영수증": st.column_config.NumberColumn("현금영수증(만원)", min_value=0, format="%d"),
                "전통시장": st.column_config.NumberColumn("전통시장(만원)", min_value=0, format="%d"),
                "대중교통": st.column_config.NumberColumn("대중교통(만원)", min_value=0, format="%d"),
                "도서공연문화": st.column_config.NumberColumn("도서공연(만원)", min_value=0, format="%d"),
            }
        )
        st.session_state["edited_df"] = edited_df

    st.markdown("---")
    st.markdown("#### 🗂️ 사용할 데이터 선택")
    data_source = st.radio(
        "계산에 사용할 데이터",
        ["직접 입력 데이터", "CSV 업로드 데이터"],
        horizontal=True
    )

    # 최종 데이터 결정
    if data_source == "CSV 업로드 데이터" and "df_card" in st.session_state:
        final_df = st.session_state["df_card"].copy()
        # 컬럼명 표준화
        col_map = {
            "신용카드(만원)": "신용카드",
            "체크카드(만원)": "체크카드",
            "현금영수증(만원)": "현금영수증",
            "전통시장(만원)": "전통시장",
            "대중교통(만원)": "대중교통",
            "도서_공연_문화(만원)": "도서공연문화",
        }
        final_df = final_df.rename(columns=col_map)
    else:
        final_df = edited_df.copy()

    st.session_state["final_df"] = final_df

    # 누적 합산
    cols_needed = ["신용카드", "체크카드", "현금영수증", "전통시장", "대중교통", "도서공연문화"]
    for c in cols_needed:
        if c not in final_df.columns:
            final_df[c] = 0

    total_credit  = final_df["신용카드"].sum()
    total_check   = final_df["체크카드"].sum()
    total_cash    = final_df["현금영수증"].sum()
    total_market  = final_df["전통시장"].sum()
    total_transit = final_df["대중교통"].sum()
    total_culture = final_df["도서공연문화"].sum()

    st.session_state["totals"] = {
        "credit": total_credit, "check": total_check, "cash": total_cash,
        "market": total_market, "transit": total_transit, "culture": total_culture
    }

    st.markdown(f"""
    <div style='background:#1e2130; border-radius:12px; padding:16px 20px; margin-top:8px;'>
    <div style='font-size:12px; color:#8b93b5; margin-bottom:10px; font-weight:600;'>📊 현재까지 누적 사용액 합계</div>
    <div style='display:flex; gap:12px; flex-wrap:wrap;'>
        <div><span style='color:#f87171; font-weight:700; font-size:16px;'>{total_credit:.0f}만</span> <span style='color:#6b7280; font-size:11px;'>신용카드</span></div>
        <div><span style='color:#60a5fa; font-weight:700; font-size:16px;'>{total_check:.0f}만</span> <span style='color:#6b7280; font-size:11px;'>체크카드</span></div>
        <div><span style='color:#a78bfa; font-weight:700; font-size:16px;'>{total_cash:.0f}만</span> <span style='color:#6b7280; font-size:11px;'>현금영수증</span></div>
        <div><span style='color:#34d399; font-weight:700; font-size:16px;'>{total_market:.0f}만</span> <span style='color:#6b7280; font-size:11px;'>전통시장</span></div>
        <div><span style='color:#fbbf24; font-weight:700; font-size:16px;'>{total_transit:.0f}만</span> <span style='color:#6b7280; font-size:11px;'>대중교통</span></div>
        <div><span style='color:#f472b6; font-weight:700; font-size:16px;'>{total_culture:.0f}만</span> <span style='color:#6b7280; font-size:11px;'>도서공연</span></div>
        <div style='border-left:1px solid #2e3250; padding-left:12px;'>
        <span style='color:#e8ecf7; font-weight:900; font-size:16px;'>{total_credit+total_check+total_cash+total_market+total_transit+total_culture:.0f}만</span> 
        <span style='color:#6b7280; font-size:11px;'>합계</span></div>
    </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 계산 실행 (공통)
# ─────────────────────────────────────────────
if "totals" in st.session_state:
    t = st.session_state["totals"]
    result = calc_deduction(
        t["credit"], t["check"], t["cash"],
        t["market"], t["transit"], t["culture"],
        annual_salary
    )
    st.session_state["result"] = result
else:
    result = calc_deduction(0,0,0,0,0,0,annual_salary)
    st.session_state["result"] = result


# ─────────────────────────────────────────────
# TAB 2: 현황 분석
# ─────────────────────────────────────────────
with tab2:
    result = st.session_state.get("result", {})
    t = st.session_state.get("totals", {"credit":0,"check":0,"cash":0,"market":0,"transit":0,"culture":0})

    total_all = sum(t.values())
    threshold = result.get("threshold", annual_salary * 0.25)
    threshold_pct = min(100, total_all / threshold * 100) if threshold > 0 else 0
    base_limit = result.get("base_limit", 300)

    # 상단 메트릭 4개
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">총 카드 사용액</div>
            <div class="metric-value">{total_all:.0f}<span style='font-size:14px;color:#6b7280;'>만원</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        color = "green" if result.get("is_over") else "yellow"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">문턱값 초과액</div>
            <div class="metric-value {color}">{result.get('over_threshold',0):.0f}<span style='font-size:14px;color:#6b7280;'>만원</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">예상 카드공제액</div>
            <div class="metric-value blue">{result.get('total_deduction',0):.1f}<span style='font-size:14px;color:#6b7280;'>만원</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">예상 절세액</div>
            <div class="metric-value green">{result.get('tax_saving',0):.1f}<span style='font-size:14px;color:#6b7280;'>만원</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### 📈 문턱값 달성 현황")

        bar_color = "#22c55e" if threshold_pct >= 100 else ("#f59e0b" if threshold_pct >= 70 else "#ef4444")
        st.markdown(f"""
        <div style='margin: 8px 0 4px;'>
            <div style='display:flex; justify-content:space-between; font-size:12px; color:#8b93b5; margin-bottom:6px;'>
                <span>총 사용액 {total_all:.0f}만원</span>
                <span>{threshold_pct:.1f}%</span>
            </div>
            <div class="progress-container">
                <div class="progress-bar" style="width:{min(threshold_pct,100):.1f}%; background:{bar_color};"></div>
            </div>
            <div style='display:flex; justify-content:space-between; font-size:11px; color:#4b5563; margin-top:4px;'>
                <span>0</span>
                <span>목표 {threshold:.0f}만원</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🏦 기본공제 한도 달성 현황")
        base_sum = result.get("base_sum", 0)
        base_pct = min(100, base_sum / base_limit * 100) if base_limit > 0 else 0
        bar_color2 = "#22c55e" if base_pct >= 100 else ("#f59e0b" if base_pct >= 70 else "#60a5fa")
        st.markdown(f"""
        <div style='margin: 8px 0 4px;'>
            <div style='display:flex; justify-content:space-between; font-size:12px; color:#8b93b5; margin-bottom:6px;'>
                <span>공제금액 {base_sum:.1f}만원</span>
                <span>{base_pct:.1f}%</span>
            </div>
            <div class="progress-container">
                <div class="progress-bar" style="width:{min(base_pct,100):.1f}%; background:{bar_color2};"></div>
            </div>
            <div style='display:flex; justify-content:space-between; font-size:11px; color:#4b5563; margin-top:4px;'>
                <span>0</span>
                <span>한도 {base_limit}만원</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 추가 한도
        for label, used, limit in [
            ("전통시장 추가한도", result.get("market_ded_capped", 0), 100),
            ("대중교통 추가한도", result.get("transit_ded_capped", 0), 100),
        ]:
            pct = min(100, used / limit * 100)
            st.markdown(f"""
            <div style='margin: 6px 0;'>
                <div style='display:flex; justify-content:space-between; font-size:11px; color:#8b93b5; margin-bottom:4px;'>
                    <span>{label}</span><span>{used:.1f}/{limit}만원</span>
                </div>
                <div class="progress-container" style="height:8px;">
                    <div class="progress-bar" style="width:{pct:.1f}%; background:#34d399;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.markdown("#### 🥧 카드 유형별 사용 비율")
        labels = ["신용카드", "체크카드", "현금영수증", "전통시장", "대중교통", "도서공연문화"]
        values = [t["credit"], t["check"], t["cash"], t["market"], t["transit"], t["culture"]]
        colors = ["#f87171", "#60a5fa", "#a78bfa", "#34d399", "#fbbf24", "#f472b6"]

        fig_pie = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.5,
            marker=dict(colors=colors, line=dict(color="#0f1117", width=2)),
            textinfo="label+percent",
            textfont=dict(size=11, color="#e8ecf7"),
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8ecf7"),
            margin=dict(l=10, r=10, t=20, b=10),
            height=280,
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # 공제금액 분포
        st.markdown("#### 💰 항목별 공제금액")
        ded_labels = ["신용카드\n(15%)", "체크카드\n(30%)", "현금영수증\n(30%)", "전통시장\n(40%)", "대중교통\n(40%)", "도서공연\n(30%)"]
        ded_values = [
            result.get("credit_deduction", 0),
            result.get("check_deduction", 0),
            result.get("cash_deduction", 0),
            result.get("market_deduction", 0),
            result.get("transit_deduction", 0),
            result.get("culture_deduction", 0),
        ]

        fig_bar = go.Figure(go.Bar(
            x=ded_labels, y=ded_values,
            marker=dict(color=colors, line=dict(color="#0f1117", width=1)),
            text=[f"{v:.1f}" for v in ded_values],
            textposition="outside",
            textfont=dict(size=11, color="#e8ecf7"),
        ))
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8b93b5"),
            margin=dict(l=10, r=10, t=10, b=10),
            height=220,
            yaxis=dict(gridcolor="#1e2130", color="#4b5563"),
            xaxis=dict(color="#6b7280"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 월별 추이 (CSV/직접입력 데이터 기반)
    if "final_df" in st.session_state:
        fdf = st.session_state["final_df"]
        if len(fdf) > 0:
            st.markdown("---")
            st.markdown("#### 📅 월별 카드 사용 추이")
            col_list = ["신용카드", "체크카드", "현금영수증", "전통시장", "대중교통", "도서공연문화"]
            month_col = "월" if "월" in fdf.columns else fdf.columns[0]
            x_vals = fdf[month_col].astype(str).tolist()

            fig_line = go.Figure()
            for col, color in zip(col_list, colors):
                if col in fdf.columns:
                    fig_line.add_trace(go.Scatter(
                        x=x_vals, y=fdf[col],
                        name=col, line=dict(color=color, width=2),
                        mode="lines+markers",
                        marker=dict(size=6),
                    ))
            fig_line.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8b93b5"),
                margin=dict(l=10, r=10, t=10, b=10),
                height=260,
                yaxis=dict(gridcolor="#1e2130", color="#4b5563"),
                xaxis=dict(color="#6b7280", gridcolor="#1e2130"),
                legend=dict(
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11),
                    orientation="h", y=-0.15,
                ),
            )
            st.plotly_chart(fig_line, use_container_width=True)


# ─────────────────────────────────────────────
# TAB 3: 최적화 전략
# ─────────────────────────────────────────────
with tab3:
    result = st.session_state.get("result", {})
    t = st.session_state.get("totals", {"credit":0,"check":0,"cash":0,"market":0,"transit":0,"culture":0})

    recs = recommend_strategy(
        result, annual_salary,
        t["credit"], t["check"], t["cash"],
        t["market"], t["transit"], t["culture"],
        current_month
    )

    st.markdown("#### 💡 맞춤 절세 전략 추천")

    if not recs:
        st.info("데이터를 입력하면 맞춤 전략이 표시됩니다.")
    else:
        for rec in recs:
            box_class = f"recommend-box {rec['type']}" if rec['type'] in ['success','warning'] else "recommend-box"
            st.markdown(f"""
            <div class="{box_class}">
                <h4>{rec['title']}</h4>
                <p>{rec['body']}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📐 시뮬레이션: 남은 기간 추가 사용 예측")

    remaining_months = max(1, 12 - current_month)
    add_check = st.slider(
        f"남은 {remaining_months}개월간 추가 체크카드 사용액 (만원/월)",
        0, 200, 50, 10
    )
    add_market = st.slider(
        f"남은 {remaining_months}개월간 추가 전통시장 사용액 (만원/월)",
        0, 100, 10, 5
    )

    sim_check  = t["check"] + add_check * remaining_months
    sim_market = t["market"] + add_market * remaining_months
    sim_result = calc_deduction(
        t["credit"], sim_check, t["cash"],
        sim_market, t["transit"], t["culture"],
        annual_salary
    )

    col_s1, col_s2, col_s3 = st.columns(3)
    delta_ded  = sim_result["total_deduction"] - result.get("total_deduction", 0)
    delta_save = sim_result["tax_saving"] - result.get("tax_saving", 0)

    with col_s1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">시뮬레이션 공제금액</div>
            <div class="metric-value blue">{sim_result['total_deduction']:.1f}<span style='font-size:13px;color:#6b7280;'>만원</span></div>
            <div style='font-size:11px; color:#4ade80; margin-top:4px;'>▲ +{delta_ded:.1f}만원 증가</div>
        </div>
        """, unsafe_allow_html=True)
    with col_s2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">시뮬레이션 절세액</div>
            <div class="metric-value green">{sim_result['tax_saving']:.1f}<span style='font-size:13px;color:#6b7280;'>만원</span></div>
            <div style='font-size:11px; color:#4ade80; margin-top:4px;'>▲ +{delta_save:.1f}만원 절세 증가</div>
        </div>
        """, unsafe_allow_html=True)
    with col_s3:
        add_spend = (add_check + add_market) * remaining_months
        roi = (delta_save / add_spend * 100) if add_spend > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">추가 지출 대비 절세 ROI</div>
            <div class="metric-value yellow">{roi:.1f}<span style='font-size:13px;color:#6b7280;'>%</span></div>
            <div style='font-size:11px; color:#8b93b5; margin-top:4px;'>추가지출 {add_spend:.0f}만원</div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 4: 결과 내보내기
# ─────────────────────────────────────────────
with tab4:
    result = st.session_state.get("result", {})
    t = st.session_state.get("totals", {"credit":0,"check":0,"cash":0,"market":0,"transit":0,"culture":0})

    st.markdown("#### 📊 최종 계산 요약표")

    summary = {
        "항목": [
            "추정 연봉",
            "공제 시작 기준금액 (총급여 × 25%)",
            "현재까지 총 카드 사용액",
            "── 신용카드",
            "── 체크카드",
            "── 현금영수증",
            "── 전통시장",
            "── 대중교통",
            "── 도서/공연/문화",
            "",
            "문턱값 초과액",
            "카드공제 금액 (기본)",
            "카드공제 금액 (전통시장 추가)",
            "카드공제 금액 (대중교통 추가)",
            "카드공제 금액 합계",
            "기본 공제 한도",
            "",
            "적용 세율 (지방세 포함)",
            "예상 절세액",
        ],
        "금액": [
            f"{annual_salary:,}만원",
            f"{result.get('threshold',0):,.0f}만원",
            f"{sum(t.values()):,.0f}만원",
            f"{t['credit']:,.0f}만원",
            f"{t['check']:,.0f}만원",
            f"{t['cash']:,.0f}만원",
            f"{t['market']:,.0f}만원",
            f"{t['transit']:,.0f}만원",
            f"{t['culture']:,.0f}만원",
            "",
            f"{result.get('over_threshold',0):,.0f}만원",
            f"{result.get('base_sum_capped',0):,.1f}만원",
            f"{result.get('market_ded_capped',0):,.1f}만원",
            f"{result.get('transit_ded_capped',0):,.1f}만원",
            f"{result.get('total_deduction',0):,.1f}만원",
            f"{result.get('base_limit',300)}만원",
            "",
            f"{result.get('tax_rate',0)*100:.1f}%",
            f"{result.get('tax_saving',0):,.1f}만원 💸",
        ]
    }
    summary_df = pd.DataFrame(summary)
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

    # 엑셀 다운로드
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="연말정산요약", index=False)
        if "final_df" in st.session_state:
            st.session_state["final_df"].to_excel(writer, sheet_name="월별카드사용내역", index=False)

    output.seek(0)
    st.download_button(
        label="📥 엑셀로 결과 다운로드",
        data=output,
        file_name=f"연말정산_카드공제_{annual_salary}만원.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    st.caption("⚠️ 본 계산기는 참고용이며 실제 연말정산 결과와 다를 수 있습니다. 정확한 계산은 국세청 홈택스를 이용하세요.")
