import streamlit as st
import json
import os
import requests
import pandas as pd

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="네이버 부동산 수집 대시보드",
    page_icon="🏠",
    layout="wide"
)

# 광역단위 코드 매핑
SIDO_MAP = {
    "서울특별시": "1100000000",
    "경기도": "4100000000",
    "인천광역시": "2800000000",
    "부산광역시": "2600000000",
    "대구광역시": "2700000000",
    "광주광역시": "2900000000",
    "대전광역시": "3000000000",
    "울산광역시": "3100000000",
    "강원특별자치도": "5100000000",
    "충청북도": "4300000000",
    "충청남도": "4400000000",
    "전라북도": "4500000000",
    "전라남도": "4600000000",
    "경상북도": "4700000000",
    "경상남도": "4800000000",
    "제주특별자치도": "5000000000"
}

PROPERTY_TYPE_MAP = {
    "단독/다가구": "DDD",
    "토지": "TJ",
    "아파트": "APT",
    "오피스텔": "OPST",
    "빌라/연립": "VL",
    "상가": "SG"
}

def get_gas_url():
    """
    GAS URL을 Streamlit Secrets에서만 로드합니다.
    (st.secrets["GAS_URL"] 방식 단일 적용)
    """
    try:
        return st.secrets["GAS_URL"]
    except Exception:
        return ""

def load_config():
    """config.json 설정 로드"""
    default_config = {
        "selected_sido": "서울특별시",
        "selected_sido_code": "1100000000",
        "trade_type": "A1",
        "rlet_types": ["DDD", "TJ"],
        "rlet_names": ["단독/다가구", "토지"],
        "max_price": 10000,
        "min_space": 66.1
    }
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_config
    return default_config

def save_config(config_data):
    """config.json 설정 저장"""
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

def fetch_sheet_data(gas_url):
    """
    GAS 웹앱(GET)을 통해 구글 시트에 누적된 최신 데이터를 가져옵니다.
    """
    if not gas_url:
        return None
    try:
        # GET 요청으로 시트 데이터 수신
        response = requests.get(gas_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return pd.DataFrame(data)
    except Exception as e:
        st.error(f"데이터 조회 중 오류 발생: {e}")
    return None

# --- UI 메인 화면 ---
st.title("🏠 네이버 부동산 자동 수집 & 실시간 조회 대시보드")
st.markdown("수집 조건을 설정하고 구글 시트에 업데이트된 매물을 실시간으로 모니터링합니다.")

gas_url = get_gas_url()
config = load_config()

# 사이드바 설정 영역
st.sidebar.header("⚙️ 야간 수집 조건 필터")

# 1. 광역단위 선택
sido_options = list(SIDO_MAP.keys())
current_sido = config.get("selected_sido", "서울특별시")
sido_idx = sido_options.index(current_sido) if current_sido in sido_options else 0
selected_sido = st.sidebar.selectbox("📍 수집 광역단위 (시/도)", sido_options, index=sido_idx)

# 2. 매물유형 멀티 선택
all_prop_names = list(PROPERTY_TYPE_MAP.keys())
saved_prop_names = config.get("rlet_names", ["단독/다가구", "토지"])
default_selected_props = [name for name in saved_prop_names if name in all_prop_names]

selected_prop_names = st.sidebar.multiselect(
    "🏢 매물유형 선택",
    options=all_prop_names,
    default=default_selected_props
)

# 3. 가격 및 면적 조건
max_price = st.sidebar.number_input("최대 매매가 (만원)", value=config.get("max_price", 10000), step=1000)
min_space = st.sidebar.number_input("최소 면적 (㎡)", value=config.get("min_space", 66.1), step=5.0)

# 설정 저장 버튼
if st.sidebar.button("💾 수집 조건 저장"):
    selected_codes = [PROPERTY_TYPE_MAP[name] for name in selected_prop_names]
    updated_config = {
        "selected_sido": selected_sido,
        "selected_sido_code": SIDO_MAP[selected_sido],
        "trade_type": "A1",
        "rlet_types": selected_codes,
        "rlet_names": selected_prop_names,
        "max_price": max_price,
        "min_space": min_space
    }
    save_config(updated_config)
    st.sidebar.success("✅ 조건이 저장되었습니다!")
    st.rerun()

# 보안 Secrets 연동 상태 확인
st.sidebar.markdown("---")
if gas_url:
    st.sidebar.success("🔒 Secrets: `GAS_URL` 연동 완료")
else:
    st.sidebar.error("⚠️ Secrets: `GAS_URL` 미설정")

# --- 탭 구성 (수집 설정 / 시트 데이터 실시간 조회) ---
tab1, tab2 = st.tabs(["📊 구글 시트 실시간 매물 조회", "⚙️ 수집 설정 정보"])

with tab1:
    st.subheader("📋 구글 시트 누적 매물 데이터")
    
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        refresh_button = st.button("🔄 시트 데이터 새로고침")
        
    if not gas_url:
        st.warning("Streamlit Secrets에 `GAS_URL`이 등록되어 있지 않습니다. App Settings > Secrets를 확인해 주세요.")
    else:
        with st.spinner("구글 시트에서 최신 데이터를 불러오는 중..."):
            df = fetch_sheet_data(gas_url)
            
        if df is not None and not df.empty:
            st.metric("총 수집된 매물 수", f"{len(df)} 건")
            
            # DataFrame 컬럼 순서 정리 및 테이블 출력
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "상세URL": st.column_config.LinkColumn("네이버 링크")
                }
            )
        else:
            st.info("시트에 저장된 매물이 없거나 데이터를 가져올 수 없습니다. Apps Script의 `doGet` 함수가 배포되었는지 확인해 주세요.")

with tab2:
    st.subheader("⚙️ 현재 저장된 수집 조건 (`config.json`)")
    st.json(load_config())
