import streamlit as st
import json
import os
import requests
import pandas as pd

# 1. 페이지 설정
st.set_page_config(
    page_title="네이버 부동산 자동 수집 대시보드",
    page_icon="🏠",
    layout="wide"
)

# 2. 광역단위 및 매물유형 매핑 사전
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
    """Streamlit Secrets 전용 GAS URL 로드"""
    try:
        return st.secrets["GAS_URL"]
    except Exception:
        return ""

def load_config():
    """config.json 읽기"""
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
    """config.json 저장"""
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

def fetch_sheet_data(gas_url):
    """개선된 doGet 응답 구조를 파싱하여 DataFrame 반환"""
    if not gas_url:
        return None, "GAS_URL이 설정되지 않았습니다."
    
    try:
        response = requests.get(gas_url, timeout=12)
        if response.status_code == 200:
            res_json = response.json()
            # 1) 신규 doGet 구조: {"status": "success", "data": [...]}
            if isinstance(res_json, dict):
                if res_json.get("status") == "success":
                    data_list = res_json.get("data", [])
                    return pd.DataFrame(data_list), None
                else:
                    return None, f"GAS 오류: {res_json.get('message')}"
            # 2) 구형 doGet 구조: 바로 리스트가 들어오는 경우 백업 파싱
            elif isinstance(res_json, list):
                return pd.DataFrame(res_json), None
        else:
            return None, f"HTTP 요청 실패 (코드: {response.status_code})"
    except Exception as e:
        return None, f"연동 예외 발생: {str(e)}"
        
    return None, "알 수 없는 응답 구조입니다."

# --- UI 메인 화면 ---
st.title("🏠 네이버 부동산 자동 수집 & 실시간 대시보드")

gas_url = get_gas_url()
config = load_config()

# 사이드바 조건 설정
st.sidebar.header("⚙️ 수집 조건 필터")

sido_options = list(SIDO_MAP.keys())
current_sido = config.get("selected_sido", "서울특별시")
sido_idx = sido_options.index(current_sido) if current_sido in sido_options else 0
selected_sido = st.sidebar.selectbox("📍 수집 광역단위 (시/도)", sido_options, index=sido_idx)

all_prop_names = list(PROPERTY_TYPE_MAP.keys())
saved_prop_names = config.get("rlet_names", ["단독/다가구", "토지"])
default_selected_props = [name for name in saved_prop_names if name in all_prop_names]

selected_prop_names = st.sidebar.multiselect(
    "🏢 매물유형 선택",
    options=all_prop_names,
    default=default_selected_props
)

max_price = st.sidebar.number_input("최대 매매가 (만원)", value=config.get("max_price", 10000), step=1000)
min_space = st.sidebar.number_input("최소 면적 (㎡)", value=config.get("min_space", 66.1), step=5.0)

if st.sidebar.button("💾 조건 저장"):
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
    st.sidebar.success("✅ 조건이 성공적으로 저장되었습니다!")
    st.rerun()

st.sidebar.markdown("---")
if gas_url:
    st.sidebar.success("🔒 Secrets: `GAS_URL` 연동 완료")
else:
    st.sidebar.error("⚠️ Streamlit Secrets에 `GAS_URL`이 없습니다.")

# 메인 대시보드 탭
tab1, tab2 = st.tabs(["📊 구글 시트 실시간 매물 조회", "⚙️ 수집 설정 정보"])

with tab1:
    st.subheader("📋 구글 시트 누적 매물 데이터")
    
    if st.button("🔄 시트 데이터 새로고침"):
        st.rerun()
        
    if not gas_url:
        st.warning("Streamlit Cloud의 App Settings > Secrets에 `GAS_URL`을 설정해 주세요.")
    else:
        with st.spinner("구글 시트 데이터를 로드하는 중..."):
            df, error_msg = fetch_sheet_data(gas_url)
            
        if error_msg:
            st.error(f"⚠️ 데이터 가져오기 실패: {error_msg}")
        elif df is not None:
            if df.empty:
                st.info("💡 구글 시트에 아직 누적된 매물 데이터가 없습니다. (크롤러를 수동 실행하거나 야간 스케줄링을 기다려 주세요.)")
            else:
                st.metric("총 수집된 매물 수", f"{len(df)} 건")
                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        "상세URL": st.column_config.LinkColumn("네이버 링크")
                    }
                )

with tab2:
    st.subheader("⚙️ 현재 저장된 설정 (`config.json`)")
    st.json(load_config())
