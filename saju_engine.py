import json
import pandas as pd
import os
import ephem
import math
from datetime import datetime, timedelta
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

# ==========================================
# 1. 정밀 사주 계산기 (Astronomical Calculator)
# ==========================================
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
OHENG_MAP = {
    '갑': '목', '을': '목', '병': '화', '정': '화', '무': '토', '기': '토', 
    '경': '금', '신': '금', '임': '수', '계': '수',
    '인': '목', '묘': '목', '사': '화', '오': '화', '진': '토', '술': '토', '축': '토', '미': '토',
    '신': '금', '유': '금', '해': '수', '자': '수'
}

def get_location_info(city_name):
    """도시 이름으로 위도, 경도, 타임존 찾기"""
    try:
        geolocator = Nominatim(user_agent="shinryeong_app")
        location = geolocator.geocode(city_name)
        
        if not location:
            return None
            
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        
        return {
            'lat': location.latitude,
            'lon': location.longitude,
            'timezone': timezone_str,
            'address': location.address
        }
    except:
        return None

def calculate_true_solar_time(birth_dt, lat, lon, timezone_str):
    local_tz = pytz.timezone(timezone_str)
    try:
        dt_aware = local_tz.localize(birth_dt)
    except ValueError:
        dt_aware = birth_dt.astimezone(local_tz)
    dt_utc = dt_aware.astimezone(pytz.UTC)
    
    offset = dt_aware.utcoffset().total_seconds() / 3600
    standard_meridian = offset * 15 
    diff_deg = lon - standard_meridian
    correction_minutes = diff_deg * 4 
    true_solar_dt = birth_dt + timedelta(minutes=correction_minutes)
    return true_solar_dt

def calculate_saju_pillars(dt):
    y = dt.year
    # 입춘 기준 간략 보정 (양력 2월 4일 기준)
    if dt.month < 2 or (dt.month == 2 and dt.day < 4):
        year_ganji_idx = (y - 1 - 4) % 60
    else:
        year_ganji_idx = (y - 4) % 60
        
    year_stem = CHEONGAN[year_ganji_idx % 10]
    year_branch = JIJI[year_ganji_idx % 12]
    
    month_base_idx = (year_ganji_idx % 10 % 5) * 2 + 2
    month_branch_idx = (dt.month + 10) % 12
    # 절기 보정 (간략히 5일 기준)
    if dt.day < 5:
        month_branch_idx = (month_branch_idx - 1) % 12
    month_stem_idx = (month_base_idx + (month_branch_idx - 2)) % 10 
    month_stem = CHEONGAN[month_stem_idx]
    month_branch = JIJI[month_branch_idx]

    base_date = datetime(1900, 1, 1)
    diff_days = (dt - base_date).days
    day_ganji_idx = (10 + diff_days) % 60
    day_stem = CHEONGAN[day_ganji_idx % 10]
    day_branch = JIJI[day_ganji_idx % 12]

    hour_base_idx = (day_ganji_idx % 10 % 5) * 2
    h = dt.hour
    if h >= 23: hour_branch_idx = 0 
    else: hour_branch_idx = (h + 1) // 2
    
    hour_stem_idx = (hour_base_idx + hour_branch_idx) % 10
    hour_stem = CHEONGAN[hour_stem_idx]
    hour_branch = JIJI[hour_branch_idx % 12]

    pillars = {
        'year': f"{year_stem}{year_branch}", 
        'month': f"{month_stem}{month_branch}", 
        'day': f"{day_stem}{day_branch}", 
        'time': f"{hour_stem}{hour_branch}"
    }
    
    counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
    for char in [year_stem, year_branch, month_stem, month_branch, day_stem, day_branch, hour_stem, hour_branch]:
        if char in OHENG_MAP:
            counts[OHENG_MAP[char]] += 1
            
    return {
        'ganji_text': f"{year_stem}{year_branch}년 {month_stem}{month_branch}월 {day_stem}{day_branch}일 {hour_stem}{hour_branch}시",
        'pillars': pillars,
        'day_stem': day_stem,
        'day_elem': OHENG_MAP[day_stem],
        'five_elem_counts': counts,
        'true_solar_time': dt.strftime("%Y-%m-%d %H:%M")
    }

# ==========================================
# 2. 데이터베이스 로더 & 분석 엔진 (수정됨)
# ==========================================
class SajuDB:
    def __init__(self):
        # [수정] 이 파일(saju_engine.py)이 있는 폴더를 기준으로 saju_db 위치를 찾음
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_folder = os.path.join(current_dir, "saju_db")
        
        # 로드 상태 확인용 변수
        self.load_status = {}

        self.glossary = self.load_csv('saju_glossary_v2.csv')
        self.five_elements = self.load_json('five_elements_matrix.json')
        self.timeline = self.load_json('timeline_db.json')
        self.shinsal = self.load_json('shinsal_db.json')
        self.love = self.load_json('love_db.json')
        self.health = self.load_json('health_db.json')
        self.career = self.load_json('career_db.json')
        self.symptom = self.load_json('symptom_mapping.json')
        self.compatibility = self.load_json('compatibility_db.json')

    def load_json(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.load_status[filename] = "✅ Loaded"
                return data
        except Exception as e:
            self.load_status[filename] = f"❌ Error: {str(e)}"
            return {}

    def load_csv(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            df = pd.read_csv(full_path)
            self.load_status[filename] = "✅ Loaded"
            return df
        except Exception as e:
            self.load_status[filename] = f"❌ Error: {str(e)}"
            return pd.DataFrame()

db = SajuDB()

def analyze_saju_precision(user_data):
    loc_info = get_location_info(user_data['city'])
    if not loc_info:
        lat, lon, tz = 37.5665, 126.9780, 'Asia/Seoul'
    else:
        lat, lon, tz = loc_info['lat'], loc_info['lon'], loc_info['timezone']
        
    birth_dt = datetime(user_data['year'], user_data['month'], user_data['day'], user_data['hour'], user_data['minute'])
    true_dt = calculate_true_solar_time(birth_dt, lat, lon, tz)
    
    saju = calculate_saju_pillars(true_dt)
    # 디버그용: DB 로드 상태를 리포트에 포함시킬 수도 있음
    saju['location_info'] = f"{user_data['city']} (보정시각: {true_dt.strftime('%H:%M')})"
    
    report = {"saju": saju, "analytics": [], "chat_context": []}
    counts = saju['five_elem_counts']
    
    # [분석 1] 오행 과다/고립
    has_imbalance = False
    
    # DB가 비어있으면 경고 메시지 추가
    if not db.five_elements:
         report['analytics'].append({"type": "⚠️ 시스템 경고", "title": "데이터 로드 실패", "content": "데이터베이스 파일을 찾을 수 없습니다. saju_db 폴더 위치를 확인하세요."})
         return report

    for elem, count in counts.items():
        key_korean = f"{elem}({_get_eng(elem)})" # 예: 목(Wood)
        
        # 3개 이상(과다)
        if count >= 3:
            data = db.five_elements.get('imbalance_analysis', {}).get(key_korean, {}).get('excess')
            if data:
                report['analytics'].append({"type": "⚠️ 기질 분석 (과다)", "title": data['title'], "content": data['shamanic_voice']})
                report['chat_context'].append(f"{elem} 과다")
                has_imbalance = True
        # 0개(고립)
        elif count == 0:
            data = db.five_elements.get('imbalance_analysis', {}).get(key_korean, {}).get('isolation')
            if data:
                report['analytics'].append({"type": "⚠️ 기질 분석 (부족)", "title": data['title'], "content": data['shamanic_voice']})
                report['chat_context'].append(f"{elem} 부족")
                has_imbalance = True
                
    if not has_imbalance:
        report['analytics'].append({"type": "⚖️ 오행의 조화", "title": "오행이 골고루 갖춰진 귀격", "content": "치우침 없이 원만한 성품일세."})

    # [분석 2] 직업 적성
    strongest = max(counts, key=counts.get)
    job_key_prefix = _get_job_key_prefix(strongest)
    
    if db.career and 'modern_jobs' in db.career:
        for k, v in db.career['modern_jobs'].items():
            if job_key_prefix in k:
                report['analytics'].append({"type": "💼 신령의 천직 추천", "title": f"'{strongest}' 기운을 쓰는 직업", "content": f"**[성향]** {v['trait']}\n\n**[추천]** {v['jobs']}\n\n📢 {v['shamanic_voice']}"})
                break
                
    # [분석 3] 2026년 운세
    if db.timeline and 'future_flow_db' in db.timeline:
        flow = db.timeline['future_flow_db'].get('2026_Byeong_O', {})
        if flow:
            report['analytics'].append({"type": "🔮 2026년 병오년 예언", "title": flow['year_title'], "content": f"{flow['summary']}\n\n**[여름 조심]** {flow['Q2_Summer']['shamanic_warning']}"})

    return report

def analyze_compatibility_precision(user_a, user_b):
    # 궁합 로직 구현
    # 1. 두 사람의 사주 각각 분석
    res_a = analyze_saju_precision(user_a)
    res_b = analyze_saju_precision(user_b)
    
    saju_a = res_a['saju']
    saju_b = res_b['saju']
    
    report = {
        "saju_a": saju_a,
        "saju_b": saju_b,
        "analytics": [],
        "chat_context": res_a['chat_context'] + res_b['chat_context']
    }
    
    # 2. 일간 궁합 (Day Stem Harmony)
    stem_a = saju_a['day_elem'] # 목/화/토/금/수
    stem_b = saju_b['day_elem']
    
    # 궁합 DB 조회
    comp_text = "특별한 기록이 없네."
    if db.love and 'basic_compatibility' in db.love:
        # 키 생성: wood_fire (알파벳순 정렬 권장하거나 양쪽 다 체크)
        eng_a = _get_eng(stem_a).lower()
        eng_b = _get_eng(stem_b).lower()
        key1 = f"{eng_a}_{eng_b}"
        key2 = f"{eng_b}_{eng_a}"
        
        harmony_db = db.love['basic_compatibility'].get('element_harmony', {})
        comp_text = harmony_db.get(key1, harmony_db.get(key2, "서로 무난한 관계일세."))

    report['analytics'].append({
        "type": "💞 속궁합 분석",
        "title": f"{user_a['name']}({stem_a}) ❤️ {user_b['name']}({stem_b})",
        "content": comp_text
    })
    
    # 3. 갈등 예고
    if db.love and 'conflict_triggers' in db.love:
        triggers = list(db.love['conflict_triggers'].values())
        if triggers:
            warn = random.choice(triggers) # 데모용 랜덤
            report['analytics'].append({
                "type": "⚡ 이별 주의보",
                "title": "싸움의 원인",
                "content": f"**[이유]** {warn['fight_reason']}\n\n📢 {warn['shamanic_voice']}"
            })

    return report

def _get_eng(k): return {'목':'Wood','화':'Fire','토':'Earth','금':'Metal','수':'Water'}.get(k,'')
def _get_job_key_prefix(k): return {'목':'식상','화':'재성','토':'비겁','금':'관성','수':'인성'}.get(k,'식상')
