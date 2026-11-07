import streamlit as st
import json
import os
import requests
import pandas as pd
import re

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="네이버 부동산 자동 수집 & 실시간 대시보드",
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

def get_secret(key_name):
    """st.secrets에서 보안 변수를 안전하게 로드합니다."""
    try:
        return st.secrets[key_name]
    except Exception:
        return ""

def clean_github_repo(raw_repo):
    """
    GITHUB_REPO에 URL 전체(예: https://github.com/user/repo)가 들어와도
    순수 'owner/repo' 형태만 자동으로 정규화하여 추출합니다.
    """
    if not raw_repo:
        return ""
    # URL 형태인 경우 owner/repo 부분만 정규식으로 추출
    clean_str = raw_repo.strip().rstrip("/")
    match = re.search(r"github\.com/([^/]+/[^/]+)", clean_str)
    if match:
        return match.group(1)
    return clean_str

def load_config():
    """config.json 로드"""
    default_config = {
        "selected_sido": "서울특별시",
        "selected_sido_code": "1100000000",
        "trade_type": "A1",
        "rlet_types": ["DDD", "TJ"],
        "rlet_names": ["단독/다가구", "토지"],
        "max_price": 10000,
        "min_space": 66.1,
        "schedule_time": "23:00"
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
    """GAS doGet 응답 파싱하여 DataFrame 반환"""
    if not gas_url:
        return None, "GAS_URL이 설정되지 않았습니다."
    try:
        response = requests.get(gas_url, timeout=12)
        if response.status_code == 200:
            res_json = response.json()
            if isinstance(res_json, dict):
                if res_json.get("status") == "success":
                    return pd.DataFrame(res_json.get("data", [])), None
                else:
                    return None, f"GAS 오류: {res_json.get('message')}"
            elif isinstance(res_json, list):
                return pd.DataFrame(res_json), None
        else:
            return None, f"HTTP 요청 실패 (코드: {response.status_code})"
    except Exception as e:
        return None, f"연동 예외 발생: {str(e)}"
    return None, "알 수 없는 응답 구조입니다."

def trigger_github_workflow():
    """
    GitHub REST API를 호출하여 workflow_dispatch 수동 실행을 트리거합니다.
    404 에러 발생 시 원인을 정밀 진단합니다.
    """
    github_token = get_secret("GITHUB_TOKEN").strip()
    raw_repo = get_secret("GITHUB_REPO")
    github_repo = clean_github_repo(raw_repo)
    workflow_filename = "crawler.yml"  # .github/workflows/ 폴더 내 파일명

    if not github_token or not github_repo:
        return False, "Streamlit Secrets에 `GITHUB_TOKEN` 또는 `GITHUB_REPO`가 설정되지 않았습니다."

    url = f"https://api.github.com/repos/{github_repo}/actions/workflows/{workflow_filename}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {"ref": "main"}

    try:
        res = requests.post(url, headers=headers, json=data, timeout=10)
        
        # 204 No Content: 호출 성공
        if res.status_code == 204:
            return True, f"🚀 [{github_repo}] 크롤러 수동 실행 요청이 성공적으로 발송되었습니다!"
        
        # 404 Not Found 정밀 진단
        elif res.status_code == 404:
            err_msg = (
                f"❌ GitHub API 404 오류 발생! 다음 3가지를 점검해 주세요:\n"
                f"1. GITHUB_REPO 이름 확인: 현재 감지된 이름 → `{github_repo}` (대소문자 오타 확인)\n"
                f"2. 워크플로우 파일 확인: 저장소의 `.github/workflows/{workflow_filename}` 파일 존재 여부\n"
                f"3. 토큰 권한(Scope) 확인: 발급받은 GITHUB_TOKEN에 `repo` 및 `workflow` 권한이 포함되었는지 확인"
            )
            return False, err_msg
        else:
            return False, f"GitHub API 호출 실패 (상태 코드: {res.status_code}, 메시지: {res.text})"
            
    except Exception as e:
        return False, f"요청 처리 중 예외 발생: {str(e)}"

# --- UI 메인 화면 ---
st.title("🏠 네이버 부동산 자동 수집 & 실시간 대시보드")

gas_url = get_secret("GAS_URL")
raw_repo = get_secret("GITHUB_REPO")
clean_repo = clean_github_repo(raw_repo)
config = load_config()

# 사이드바: 수집 조건 및 스케줄 설정
st.sidebar.header("⚙️ 수집 조건 & 스케줄 설정")

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

schedule_times = ["06:00", "09:00", "12:00", "18:00", "21:00", "23:00"]
current_sched = config.get("schedule_time", "23:00")
sched_idx = schedule_times.index(current_sched) if current_sched in schedule_times else 5
selected_schedule = st.sidebar.selectbox("⏰ 야간 자동 수집 희망 시간", schedule_times, index=sched_idx)

if st.sidebar.button("💾 수집 설정 저장"):
    selected_codes = [PROPERTY_TYPE_MAP[name] for name in selected_prop_names]
    updated_config = {
        "selected_sido": selected_sido,
        "selected_sido_code": SIDO_MAP[selected_sido],
        "trade_type": "A1",
        "rlet_types": selected_codes,
        "rlet_names": selected_prop_names,
        "max_price": max_price,
        "min_space": min_space,
        "schedule_time": selected_schedule
    }
    save_config(updated_config)
    st.sidebar.success("✅ 설정이 성공적으로 저장되었습니다!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔒 Secrets 연동 상태")
st.sidebar.text(f"GAS_URL: {'✅' if gas_url else '❌'}")
st.sidebar.text(f"GITHUB_TOKEN: {'✅' if get_secret('GITHUB_TOKEN') else '❌'}")
st.sidebar.text(f"GITHUB_REPO: {'✅' if clean_repo else '❌'} ({clean_repo if clean_repo else '미설정'})")

# 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 구글 시트 실시간 조회", "🚀 수동 수집 트리거", "⚙️ 설정 및 안내"])

with tab1:
    st.subheader("📋 구글 시트 누적 매물 데이터")
    if st.button("🔄 시트 데이터 새로고침"):
        st.rerun()

    if not gas_url:
        st.warning("Streamlit Secrets에 `GAS_URL`이 설정되어 있지 않습니다.")
    else:
        with st.spinner("구글 시트 데이터를 로드하는 중..."):
            df, error_msg = fetch_sheet_data(gas_url)

        if error_msg:
            st.error(f"⚠️ 데이터 가져오기 실패: {error_msg}")
        elif df is not None:
            if df.empty:
                st.info("💡 시트에 저장된 매물이 없습니다. [🚀 수동 수집 트리거] 탭에서 수동 실행을 눌러보세요.")
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
    st.subheader("🚀 즉시 크롤링 수동 실행")
    st.markdown("""
    정기 자동 수집 시간까지 기다리지 않고, **지금 즉시 GitHub Actions 가상 머신을 가동하여 수집**합니다.
    """)
    
    col_trigger, col_blank = st.columns([1, 2])
    with col_trigger:
        if st.button("⚡ 지금 즉시 크롤러 실행하기", type="primary", use_container_width=True):
            with st.spinner("GitHub Actions에 워크플로우 실행 요청을 보내는 중..."):
                success, msg = trigger_github_workflow()
                if success:
                    st.success(msg)
                    st.info("ℹ️ GitHub Actions VM 구동 및 데이터 시트 저장까지 약 1~2분이 소요됩니다.")
                else:
                    st.error(msg)

with tab3:
    st.subheader("⚙️ 저장된 설정 정보 (`config.json`)")
    st.json(load_config())
