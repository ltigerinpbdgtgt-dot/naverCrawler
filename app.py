import streamlit as st
import json
import os

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="네이버 부동산 매물유형 설정",
    page_icon="🏠",
    layout="wide"
)

# 2. 네이버 부동산 매물유형 이름 및 네이버 API 코드 매핑 사전
PROPERTY_TYPE_MAP = {
    "아파트": "APT",
    "오피스텔": "OPST",
    "빌라/연립": "VL",
    "단독/다가구": "DDD",
    "전원주택": "JW",
    "상가주택": "SGJT",
    "재개발": "JGB",
    "상가": "SG",
    "사무실": "SMS",
    "공장/창고": "GJ",
    "토지": "TJ",
    "지식산업센터": "JSS"
}

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

def load_config():
    """config.json 설정 파일 읽기"""
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
    """config.json 설정 파일 저장"""
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

# --- UI 화면 배치 ---
st.title("🏠 네이버 부동산 조건 설정 대시보드")
st.markdown("네이버 부동산 실제 서비스와 동일한 매물유형 드롭다운 필터를 설정합니다.")

config = load_config()

# 사이드바 설정 영역
st.sidebar.header("⚙️ 수집 조건 필터")

# 1) 광역단위 선택 드롭다운
sido_options = list(SIDO_MAP.keys())
current_sido = config.get("selected_sido", "서울특별시")
sido_idx = sido_options.index(current_sido) if current_sido in sido_options else 0
selected_sido = st.sidebar.selectbox("📍 수집 광역단위 (시/도)", sido_options, index=sido_idx)

# 2) 네이버 부동산 매물유형 멀티 선택 드롭다운 (Dropdown)
all_prop_names = list(PROPERTY_TYPE_MAP.keys())
saved_prop_names = config.get("rlet_names", ["단독/다가구", "토지"])

# 기존 저장값 중 존재하는 항목만 기본값으로 설정
default_selected_props = [name for name in saved_prop_names if name in all_prop_names]

selected_prop_names = st.sidebar.multiselect(
    "🏢 매물유형 선택 (중복 선택 가능)",
    options=all_prop_names,
    default=default_selected_props,
    help="네이버 부동산과 동일한 매물 유형 카테고리입니다."
)

# 3) 거래 조건 및 수치 필터
max_price = st.sidebar.number_input("최대 매매가 (만원)", value=config.get("max_price", 10000), step=1000, help="10000 = 1억 원")
min_space = st.sidebar.number_input("최소 면적 (㎡)", value=config.get("min_space", 66.1), step=5.0, help="66.1㎡ ≈ 20평")

# 설정 저장 버튼
if st.sidebar.button("💾 조건 저장 및 적용"):
    # 선택된 한글 매물유형 명칭을 네이버 API 코드(APT, VL, DDD 등)로 변환
    selected_codes = [PROPERTY_TYPE_MAP[name] for name in selected_prop_names]
    
    updated_config = {
        "selected_sido": selected_sido,
        "selected_sido_code": SIDO_MAP[selected_sido],
        "trade_type": "A1",
        "rlet_types": selected_codes,       # 네이버 API용 코드 배열 (예: ["DDD", "TJ"])
        "rlet_names": selected_prop_names,  # UI 표시용 한글 매물명 배열
        "max_price": max_price,
        "min_space": min_space
    }
    save_config(updated_config)
    st.sidebar.success("✅ 매물유형 및 조건이 성공적으로 저장되었습니다!")
    st.rerun()

# --- 메인 화면 결과 모니터링 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 현재 설정된 조건 (`config.json`)")
    st.json(load_config())

with col2:
    st.subheader("🔍 변환된 네이버 API 파라미터")
    current_cfg = load_config()
    codes = current_cfg.get("rlet_types", [])
    st.write(f"**선택된 한글 매물유형:** {', '.join(current_cfg.get('rlet_names', []))}")
    st.write(f"**네이버 API 전송 코드 (`rletTpCd`):** `{':'.join(codes)}`")
