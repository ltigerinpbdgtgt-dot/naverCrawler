import streamlit as st
import json
import os
import requests

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="네이버 부동산 자동 수집 제어판",
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
    GAS URL 자동 탐색 우선순위:
    1. Streamlit Secrets (secrets.toml)
    2. OS 환경 변수 (GAS_URL)
    3. config.json 설정 파일
    """
    if "GAS_URL" in st.secrets:
        return st.secrets["GAS_URL"]
    return os.environ.get("GAS_URL", "")

def load_config():
    """config.json 설정 로드"""
    default_config = {
        "selected_sido": "서울특별시",
        "selected_sido_code": "1100000000",
        "trade_type": "A1",
        "rlet_types": ["DDD", "TJ"],
        "rlet_names": ["단독/다가구", "토지"],
        "max_price": 10000,
        "min_space": 66.1,
        "gas_url": ""
    }
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            return default_config
    return default_config

def save_config(config_data):
    """config.json 설정 저장"""
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

# --- UI 메인 화면 ---
st.title("🏠 네이버 부동산 자동 수집 제어판")
st.markdown("매번 URL을 입력할 필요 없이 자동으로 연동되는 수집 시스템입니다.")

config = load_config()
current_gas_url = get_gas_url() or config.get("gas_url", "")

# 사이드바 설정 영역
st.sidebar.header("⚙️ 수집 조건 필터")

# 1. 광역단위 선택
sido_options = list(SIDO_MAP.keys())
current_sido = config.get("selected_sido", "서울특별시")
sido_idx = sido_options.index(current_sido) if current_sido in sido_options else 0
selected_sido = st.sidebar.selectbox("📍 수집 광역단위 (시/도)", sido_options, index=sido_idx)

# 2. 매물유형 선택
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

# 4. GAS 웹앱 URL (자동 로드 및 수동 백업)
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 구글 시트 연동 설정")
input_gas_url = st.sidebar.text_input(
    "GAS Web App URL",
    value=current_gas_url,
    type="password",
    help="Streamlit Secrets에 저장되어 있으면 자동 로드됩니다."
)

if st.sidebar.button("💾 수집 조건 저장"):
    selected_codes = [PROPERTY_TYPE_MAP[name] for name in selected_prop_names]
    updated_config = {
        "selected_sido": selected_sido,
        "selected_sido_code": SIDO_MAP[selected_sido],
        "trade_type": "A1",
        "rlet_types": selected_codes,
        "rlet_names": selected_prop_names,
        "max_price": max_price,
        "min_space": min_space,
        "gas_url": input_gas_url
    }
    save_config(updated_config)
    st.sidebar.success("✅ 조건이 성공적으로 저장되었습니다!")
    st.rerun()

# 메인 화면 연동 상태 점검
col1, col2 = st.columns(2)

with col1:
    st.subheader("📡 연결 상태 체크")
    if input_gas_url:
        st.success("✅ GAS URL 연결 정보가 존재합니다.")
    else:
        st.error("⚠️ GAS URL이 설정되지 않았습니다! Secrets 등록 또는 URL을 입력해 주세요.")
        
    st.subheader("📋 현재 설정 정보")
    st.json(load_config())

with col2:
    st.subheader("🧪 연동 테스트 버튼")
    if st.button("🔔 구글 시트 연결 테스트 전송"):
        if not input_gas_url:
            st.error("GAS URL이 없습니다.")
        else:
            test_payload = [{
                "수집일시": "테스트 실행",
                "매물ID": "TEST_001",
                "지역명": "테스트 지역",
                "매물명": "연동 테스트 매물",
                "매물유형": "테스트",
                "거래유형": "매매",
                "매매가": "0",
                "면적": "0/0",
                "층수": "1/1",
                "상세URL": "https://land.naver.com"
            }]
            try:
                res = requests.post(input_gas_url, json=test_payload, timeout=10)
                st.write(f"응답 코드: {res.status_code}")
                st.write(f"응답 내용: {res.text}")
                if res.status_code == 200:
                    st.success("🎉 구글 시트 데이터 전송 성공!")
            except Exception as e:
                st.error(f"전송 실패: {e}")
