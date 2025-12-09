import json
import pandas as pd
import ephem
import os  # <--- [중요] 경로 계산을 위해 추가
from datetime import datetime
from korean_lunar_calendar import KoreanLunarCalendar

# ==========================================
# 1. 데이터베이스 로더 (DB Loader)
# ==========================================
class SajuDB:
    def __init__(self):
        # [중요] 데이터 파일들이 들어있는 폴더 이름 지정
        self.db_folder = "saju_db" 
        
        # 파일 로딩 시 경로가 자동으로 합쳐짐
        self.glossary = self.load_csv('saju_glossary_v2.csv')
        self.five_elements = self.load_json('five_elements_matrix.json')
        self.timeline = self.load_json('timeline_db.json')
        self.shinsal = self.load_json('shinsal_db.json')
        self.love = self.load_json('love_db.json')
        self.health = self.load_json('health_db.json')
        self.career = self.load_json('career_db.json')
        self.symptom = self.load_json('symptom_mapping.json')

    def load_json(self, filename):
        # 폴더명 + 파일명 합치기 (예: saju_db/timeline_db.json)
        full_path = os.path.join(self.db_folder, filename)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 에러 로그 대신 빈 딕셔너리 반환 (서버 안 죽게)
            print(f"⚠️ 경고: '{full_path}' 파일을 찾을 수 없네. 경로를 확인하게.")
            return {}

    def load_csv(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            return pd.read_csv(full_path)
        except FileNotFoundError:
            print(f"⚠️ 경고: '{full_path}' 파일을 찾을 수 없네.")
            return pd.DataFrame()

# 전역 DB 인스턴스 생성
db = SajuDB()

# ==========================================
# 2. 사주 만세력 계산 (Calculator)
# ==========================================
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

# ... (아래 get_ganji 및 analyze_saju 함수는 기존과 동일하게 유지) ...
# ... (기존 코드 그대로 두면 됨) ...

def get_ganji(year, month, day, hour, minute):
    # (내용 생략 - 기존 코드 유지)
    return {
        'year': '을사', 'month': '병술', 'day': '갑인', 'time': '무진',
        'year_stem': '을', 'year_branch': '사',
        'day_stem': '갑', 'day_branch': '인',
        'five_elem_counts': {'목': 3, '화': 2, '토': 1, '금': 1, '수': 1}
    }

def analyze_saju(user_input):
    # (내용 생략 - 기존 코드 유지)
    # 위에서 db 객체가 이미 경로를 잘 찾으므로 여기는 수정할 필요 없음
    saju = get_ganji(user_input['year'], user_input['month'], user_input['day'], user_input['hour'], 0)
    
    report = {
        "saju": saju,
        "analytics": [],
        "chat_context": [] 
    }
    
    # ... (분석 로직 기존 유지) ...
    
    # 2. 오행 분석 (Health & Personality)
    counts = saju['five_elem_counts']
    for elem, count in counts.items():
        if count >= 3:
            key = f"{elem}({_get_eng(elem)})"
            # db 객체가 데이터를 잘 가지고 있는지 확인
            if db.five_elements and 'imbalance_analysis' in db.five_elements:
                data = db.five_elements['imbalance_analysis'].get(key, {}).get('excess', {})
                if data:
                    report['analytics'].append({
                        "type": "⚠️ 과다 경고",
                        "title": data.get('title'),
                        "content": data.get('shamanic_voice')
                    })
                    report['chat_context'].append(f"{elem} 과다: {data.get('psychology')}")

    # 3. 2026년 운세
    if db.timeline and 'future_flow_db' in db.timeline:
        year_2026 = db.timeline['future_flow_db'].get('2026_Byeong_O', {})
        report['analytics'].append({
            "type": "🔮 2026년 예언",
            "title": year_2026.get('year_title'),
            "content": f"{year_2026.get('summary')}\n\n[여름 경고] {year_2026.get('Q2_Summer', {}).get('shamanic_warning')}"
        })
    
    # 4. 직업 등 추가 로직 유지...
    
    return report

def _get_eng(kor):
    mapping = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}
    return mapping.get(kor, '')
