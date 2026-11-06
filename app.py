import streamlit as st
import json
import pandas as pd
import requests

st.set_page_config(page_title="네이버 부동산 수집기", layout="wide")

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
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_config(config):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

st.title("🏠 네이버 부동산 야간 수집 설정 및 조회")

config = load_config()

st.sidebar.header("⚙️ 수집 조건 설정")

sido_names = list(SIDO_MAP.keys())
current_sido = config.get("selected_sido", "서울특별시")
selected_sido = st.sidebar.selectbox("수집 대상 광역(시/도)", sido_names, index=sido_names.index(current_sido) if current_sido in sido_names else 0)

max_price = st.sidebar.number_input("최대 매매가 (만원)", value=config.get("max_price", 10000), step=1000)
min_space = st.sidebar.number_input("최소 면적 (㎡)", value=config.get("min_space", 66.1), step=5.0)

gas_url = st.sidebar.text_input("Google Apps Script 웹앱 URL", value=config.get("gas_url", ""))

if st.sidebar.button("💾 설정 저장하기"):
    new_config = {
        "selected_sido": selected_sido,
        "selected_sido_code": SIDO_MAP[selected_sido],
        "trade_type": "A1",
        "rlet_types": ["DDD", "TJ"],
        "max_price": max_price,
        "min_space": min_space,
        "gas_url": gas_url
    }
    save_config(new_config)
    st.sidebar.success("설정이 저장되었습니다! 오늘 밤 23시 야간 수집부터 새로 저장된 조건이 적용됩니다.")

st.subheader("📌 현재 야간 수집 설정 정보")
st.json(load_config())
