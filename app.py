import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

# --- Streamlit 페이지 기본 설정 ---
st.set_page_config(
    page_title="네이버 부동산 매물 수집기",
    page_icon="🏠",
    layout="wide"
)

# --- 네이버 부동산 API 기본 헤더 설정 ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://m.land.naver.com/"
}

# --- 1. 야간 시간 탐색 제어 함수 ---
def is_working_hours(start_hour=23, end_hour=8):
    """현재 시간이 작업 시간(23:00 ~ 08:00)에 해당하는지 확인합니다."""
    now_hour = datetime.now().hour
    # 23시 이상이거나 8시 미만인 경우
    return now_hour >= start_hour or now_hour < end_hour

# --- 2. 구글 시트 API 연동 함수 ---
def connect_google_sheet(sheet_url):
    """Streamlit Secrets 인증 정보로 구글 시트에 연결합니다."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        # secrets.toml 의 gcp_service_account 정보 사용
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url).sheet1
        return sheet
    except Exception as e:
        st.error(f"구글 시트 연동 실패: {e}")
        return None

# --- 3. 네이버 부동산 매물 수집 함수 ---
def fetch_naver_articles(cortar_no, rlet_tp_cd, trad_tp_cd, prc_max, spc_min):
    """
    특정 법정동 코드(cortarNo) 및 조건에 따라 네이버 부동산 매물을 수집합니다.
    """
    articles = []
    page = 1
    
    while True:
        url = (
            f"https://m.land.naver.com/cluster/ajax/articleList?"
            f"cortarNo={cortar_no}&rletTpCd={rlet_tp_cd}&tradTpCd={trad_tp_cd}"
            f"&prcMax={prc_max}&spcMin={spc_min}&page={page}"
        )
        
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                break
                
            data = res.json()
            body = data.get("body", [])
            
            if not body:
                break
                
            for item in body:
                article = {
                    "수집일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "매물ID": item.get("atclNo"),
                    "매물명": item.get("atclNm"),
                    "매물유형": item.get("rletTpNm"),
                    "거래유형": item.get("tradTpNm"),
                    "매매가(만원)": item.get("prc"),
                    "공급/전용면적": f"{item.get('spc1')}/{item.get('spc2')}㎡",
                    "층수": f"{item.get('flrInfo')}",
                    "설명": item.get("atclFctrDesc", ""),
                    "상세URL": f"https://m.land.naver.com/article/info/{item.get('atclNo')}"
                }
                articles.append(article)
                
            page += 1
            time.sleep(1.5) # IP 차단 방지를 위한 요청 간격 지연
            
        except Exception as e:
            st.warning(f"데이터 수집 중 오류 발생: {e}")
            break
            
    return articles

# --- 4. Streamlit UI 메인 화면 ---
st.title("🏠 네이버 부동산 조건 매물 자동 수집기")

# 사이드바: 동적 매개변수 조절 메뉴
st.sidebar.header("⚙️ 수집 조건 설정")

# 거래 유형 설정
trad_tp_map = {"매매": "A1", "전세": "B1", "월세": "B2"}
selected_trad = st.sidebar.selectbox("거래 유형", list(trad_tp_map.keys()), index=0)

# 매물 종류 선택 (다중 선택 가능)
rlet_tp_map = {"단독/다가구": "DDD", "토지": "TJ", "아파트": "APT", "빌라/다세대": "VL"}
selected_rlet = st.sidebar.multiselect("매물 종류", list(rlet_tp_map.keys()), default=["단독/다가구", "토지"])

# 가격 및 면적 필터링 설정
max_price = st.sidebar.number_input("최대 매매가 (단위: 만원)", value=10000, step=1000, help="10000 = 1억 원")
min_space = st.sidebar.number_input("최소 면적 (단위: ㎡)", value=66.1, step=5.0, help="66.1㎡ ≈ 20평")

# 법정동 코드 입력 (테스트용 입력창 / 상위 코드 확장 가능)
cortar_input = st.sidebar.text_input("탐색할 법정동 코드 (CortarNo)", value="1168000000", help="예: 1168000000 (서울시 강남구)")

# 구글 시트 연동 설정
st.sidebar.header("📊 구글 시트 저장 설정")
google_sheet_url = st.sidebar.text_input("구글 시트 URL", value="")
enable_sheet_save = st.sidebar.checkbox("구글 시트에 실시간 저장하기")

# 야간 자동 실행 모드 설정
use_night_scheduler = st.sidebar.checkbox("야간 시간대(23시~08시) 스케줄러 활성화", value=False)

# 탐색 시작 버튼
if st.button("🔍 매물 탐색 시작"):
    # 스케줄러 시간 체크
    if use_night_scheduler and not is_working_hours():
        st.warning("⏰ 현재는 휴식 시간(08:00 ~ 23:00)입니다. 야간 시간대(23:00 ~ 08:00)에 다시 탐색이 시작됩니다.")
    else:
        st.info("매물 탐색을 시작합니다...")
        
        # 매물 종류 코드 조합 (예: DDD:TJ)
        rlet_code_str = ":".join([rlet_tp_map[item] for item in selected_rlet])
        trad_code_str = trad_tp_map[selected_trad]
        
        # 수집 진행
        results = fetch_naver_articles(
            cortar_no=cortar_input,
            rlet_tp_cd=rlet_code_str,
            trad_tp_cd=trad_code_str,
            prc_max=max_price,
            spc_min=min_space
        )
        
        if results:
            df = pd.DataFrame(results)
            st.success(f"총 {len(df)}건의 매물을 찾았습니다!")
            
            # HTML 표 출력 UI
            st.subheader("📋 수집 매물 리스트 (HTML 표)")
            st.write(
                df.to_html(escape=False, render_links=True, index=False),
                unsafe_allow_html=True
            )
            
            # 구글 시트 저장 로직
            if enable_sheet_save and google_sheet_url:
                sheet = connect_google_sheet(google_sheet_url)
                if sheet:
                    # 첫 행에 헤더가 없으면 추가 후 데이터 작성
                    if len(sheet.get_all_values()) == 0:
                        sheet.append_row(df.columns.tolist())
                    
                    for row in df.values.tolist():
                        sheet.append_row(row)
                    st.success("✅ 구글 시트에 실시간 저장이 완료되었습니다!")
        else:
            st.warning("조건에 맞는 매물이 존재하지 않거나 탐색에 실패했습니다.")
