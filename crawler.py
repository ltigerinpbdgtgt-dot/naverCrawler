import requests
import json
import time
import random
from datetime import datetime
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://m.land.naver.com/"
}

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_sub_regions(cortar_no):
    """상위 법정동 코드로 하위 구/군 또는 동/읍/면 목록을 조회합니다."""
    url = f"https://m.land.naver.com/cluster/ajax/cortarList?cortarNo={cortar_no}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            return res.json().get("regionList", [])
    except Exception as e:
        print(f"지역 코드 조회 중 오류 ({cortar_no}): {e}")
    return []

def fetch_articles_by_dong(dong_code, dong_name, config):
    """특정 동 단위의 매물을 조건별로 수집합니다."""
    rlet_code_str = ":".join(config["rlet_types"])
    articles = []
    page = 1
    
    while True:
        url = (
            f"https://m.land.naver.com/cluster/ajax/articleList?"
            f"cortarNo={dong_code}&rletTpCd={rlet_code_str}&tradTpCd={config['trade_type']}"
            f"&prcMax={config['max_price']}&spcMin={config['min_space']}&page={page}"
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
                articles.append({
                    "수집일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "매물ID": item.get("atclNo"),
                    "지역명": dong_name,
                    "매물명": item.get("atclNm"),
                    "매물유형": item.get("rletTpNm"),
                    "거래유형": item.get("tradTpNm"),
                    "매매가": item.get("prc"),
                    "면적": f"{item.get('spc1')}/{item.get('spc2')}",
                    "층수": item.get("flrInfo"),
                    "상세URL": f"https://m.land.naver.com/article/info/{item.get('atclNo')}"
                })
            page += 1
            time.sleep(random.uniform(1.2, 2.0)) # 차단 방지 랜덤 지연
        except Exception as e:
            print(f"매물 수집 에러 ({dong_name}): {e}")
            break
            
    return articles

def send_to_gas(gas_url, data):
    """수집 데이터를 Google Apps Script URL로 전송합니다."""
    if not gas_url or not data:
        return
    try:
        res = requests.post(gas_url, json=data, timeout=30)
        print(f"GAS 전송 결과: {res.text}")
    except Exception as e:
        print(f"GAS 전송 오류: {e}")

def run_crawler():
    config = load_config()
    sido_code = config["selected_sido_code"]
    sido_name = config["selected_sido"]
    gas_url = os.environ.get("GAS_URL", config.get("gas_url", ""))
    
    print(f"[{datetime.now()}] '{sido_name}' 야간 자동 순회를 시작합니다...")
    
    # 1단계: 시/도 ➔ 하위 구/군 목록 추출
    sigungu_list = get_sub_regions(sido_code)
    total_collected = 0
    
    for sigungu in sigungu_list:
        sigungu_code = sigungu["cortarNo"]
        sigungu_name = sigungu["cortarNm"]
        
        # 2단계: 구/군 ➔ 하위 동/읍/면 목록 추출
        dong_list = get_sub_regions(sigungu_code)
        for dong in dong_list:
            dong_code = dong["cortarNo"]
            dong_name = f"{sido_name} {sigungu_name} {dong['cortarNm']}"
            
            # 3단계: 동 단위 매물 수집
            items = fetch_articles_by_dong(dong_code, dong_name, config)
            if items:
                send_to_gas(gas_url, items)
                total_collected += len(items)
                print(f"  - {dong_name}: {len(items)}건 수집 완료 및 구글 시트 전송")
                
            time.sleep(random.uniform(0.5, 1.2))
            
    print(f"[{datetime.now()}] 전체 순회 완료! 총 수집 매물: {total_collected}건")

if __name__ == "__main__":
    run_crawler()
