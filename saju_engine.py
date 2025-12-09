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
        geolocator = Nominatim(user_agent="shinryeong_app_v2")
        location = geolocator.geocode(city_name)
        if not location: return None
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        return {'lat': location.latitude, 'lon': location.longitude, 'timezone': timezone_str}
    except: return None

def calculate_true_solar_time(birth_dt, lat, lon, timezone_str):
    local_tz = pytz.timezone(timezone_str)
    try: dt_aware = local_tz.localize(birth_dt)
    except ValueError: dt_aware = birth_dt.astimezone(local_tz)
    
    offset = dt_aware.utcoffset().total_seconds() / 3600
    standard_meridian = offset * 15 
    diff_deg = lon - standard_meridian
    correction_minutes = diff_deg * 4 
    return birth_dt + timedelta(minutes=correction_minutes)

def calculate_saju_pillars(dt):
    y = dt.year
    # 입춘 기준 간략 보정
    if dt.month < 2 or (dt.month == 2 and dt.day < 4): year_ganji_idx = (y - 1 - 4) % 60
    else: year_ganji_idx = (y - 4) % 60
        
    year_stem = CHEONGAN[year_ganji_idx % 10]
    year_branch = JIJI[year_ganji_idx % 12]
    
    month_base_idx = (year_ganji_idx % 10 % 5) * 2 + 2
    month_branch_idx = (dt.month + 10) % 12
    if dt.day < 5: month_branch_idx = (month_branch_idx - 1) % 12 # 절기 약식 보정
    month_stem = CHEONGAN[(month_base_idx + (month_branch_idx - 2)) % 10]
    month_branch = JIJI[month_branch_idx]

    base_date = datetime(1900, 1, 1)
    diff_days = (dt - base_date).days
    day_ganji_idx = (10 + diff_days) % 60
    day_stem = CHEONGAN[day_ganji_idx % 10]
    day_branch = JIJI[day_ganji_idx % 12]

    hour_base_idx = (day_ganji_idx % 10 % 5) * 2
    h = dt.hour
    hour_branch_idx = 0 if h >= 23 else (h + 1) // 2
    hour_stem = CHEONGAN[(hour_base_idx + hour_branch_idx) % 10]
    hour_branch = JIJI[hour_branch_idx % 12]

    pillars = {
        'year': f"{year_stem}{year_branch}", 
        'month': f"{month_stem}{month_branch}", 
        'day': f"{day_stem}{day_branch}", 
        'time': f"{hour_stem}{hour_branch}"
    }
    
    counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
    for char in [year_stem, year_branch, month_stem, month_branch, day_stem, day_branch, hour_stem, hour_branch]:
        if char in OHENG_MAP: counts[OHENG_MAP[char]] += 1
            
    return {
        'ganji_text': f"{year_stem}{year_branch}년 {month_stem}{month_branch}월 {day_stem}{day_branch}일 {hour_stem}{hour_branch}시",
        'pillars': pillars,
        'day_stem': day_stem,
        'day_elem': OHENG_MAP[day_stem],
        'five_elem_counts': counts,
        'true_solar_time': dt.strftime("%Y-%m-%d %H:%M")
    }

# ==========================================
# 2. 데이터베이스 로더 (경로 자동 인식)
# ==========================================
class SajuDB:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_folder = os.path.join(current_dir, "saju_db")
        self.load_status = {}
        
        # 각 파일 로드
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
                self.load_status[filename] = "✅ Loaded"
                return json.load(f)
        except Exception as e:
            self.load_status[filename] = f"❌ {e}"
            return {}

    def load_csv(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            df = pd.read_csv(full_path)
            self.load_status[filename] = "✅ Loaded"
            return df
        except Exception as e:
            self.load_status[filename] = f"❌ {e}"
            return pd.DataFrame()

db = SajuDB()

# ==========================================
# 3. 유연한 검색 엔진 (Fuzzy Match Engine) [핵심 수정]
# ==========================================
def find_in_db(data_dict, keyword):
    """
    JSON 키가 정확히 일치하지 않아도(예: '금' vs '금(Metal)') 
    키워드가 포함되어 있으면 데이터를 반환하는 함수
    """
    if not isinstance(data_dict, dict): return None
    
    # 1. 정확 일치 시도
    if keyword in data_dict: return data_dict[keyword]
    
    # 2. 부분 일치 시도 (Loop)
    for key, value in data_dict.items():
        if keyword in key: # 예: "금" in "금(Metal)" -> True
            return value
            
    return None

def analyze_saju_precision(user_data):
    # 1. 시각 계산
    loc_info = get_location_info(user_data['city'])
    if not loc_info: lat, lon, tz = 37.5665, 126.9780, 'Asia/Seoul'
    else: lat, lon, tz = loc_info['lat'], loc_info['lon'], loc_info['timezone']
    
    birth_dt = datetime(user_data['year'], user_data['month'], user_data['day'], user_data['hour'], user_data['minute'])
    true_dt = calculate_true_solar_time(birth_dt, lat, lon, tz)
    saju = calculate_saju_pillars(true_dt)
    saju['location_info'] = f"{user_data['city']} (보정시각: {true_dt.strftime('%H:%M')})"
    
    report = {"saju": saju, "analytics": [], "chat_context": []}
    counts = saju['five_elem_counts']
    
    # [분석 1] 오행 과다/고립
    has_imbalance = False
    imbalance_db = db.five_elements.get('imbalance_analysis', {})
    
    for elem, count in counts.items(): # 목, 화, 토, 금, 수
        found_data = find_in_db(imbalance_db, elem) # "금"으로 "금(Metal)" 찾기 시도
        
        if found_data:
            data = None
            if count >= 3:
                data = found_data.get('excess')
                tag = "과다"
            elif count == 0:
                data = found_data.get('isolation')
                tag = "부족"
            
            if data:
                report['analytics'].append({
                    "type": f"⚠️ 기질 분석 ({tag})",
                    "title": data.get('title', f'{elem} 기운 불균형'),
                    "content": data.get('shamanic_voice', '기운이 치우쳐 있어 조심해야 하네.')
                })
                report['chat_context'].append(f"{elem} {tag}")
                has_imbalance = True

    if not has_imbalance:
        report['analytics'].append({"type": "⚖️ 오행의 조화", "title": "오행이 골고루 갖춰진 귀격", "content": "치우침 없이 원만한 성품일세."})

    # [분석 2] 직업 (Career) - career_db.json
    strongest = max(counts, key=counts.get) # 가장 강한 오행
    
    # 오행 -> 십성 매핑 (약식)
    trait_map = {'목':'식상', '화':'재성', '토':'비겁', '금':'관성', '수':'인성'}
    keyword = trait_map.get(strongest, '식상') # 예: '관성'
    
    career_db = db.career.get('modern_jobs', {})
    job_data = find_in_db(career_db, keyword) # "관성"으로 "관성_발달(Official...)" 찾기
    
    if job_data:
        report['analytics'].append({
            "type": "💼 신령의 천직 추천",
            "title": f"'{strongest}' 기운을 쓰는 일",
            "content": f"**[성향]** {job_data.get('trait')}\n\n**[추천]** {job_data.get('jobs')}\n\n📢 {job_data.get('shamanic_voice')}"
        })
    else:
        # DB 매칭 실패 시 기본 멘트
        report['analytics'].append({
            "type": "💼 직업 조언",
            "title": "자신만의 길을 찾게",
            "content": f"{strongest} 기운이 강하니 이를 활용하는 쪽으로 나가면 대성할 것일세."
        })

    # [분석 3] 2026년 예언 (Timeline)
    future_db = db.timeline.get('future_flow_db', {})
    year_data = find_in_db(future_db, "2026") # "2026" 키워드로 찾기
    
    if year_data:
        report['analytics'].append({
            "type": "🔮 2026년 병오년 예언",
            "title": year_data.get('year_title', '2026년 운세'),
            "content": f"{year_data.get('summary')}\n\n**[여름 경고]** {year_data.get('Q2_Summer', {}).get('shamanic_warning')}"
        })

    return report

def analyze_compatibility_precision(user_a, user_b):
    res_a = analyze_saju_precision(user_a)
    res_b = analyze_saju_precision(user_b)
    
    saju_a = res_a['saju']
    saju_b = res_b['saju']
    
    report = {
        "saju_a": saju_a, "saju_b": saju_b,
        "analytics": [],
        "chat_context": res_a['chat_context'] + res_b['chat_context']
    }
    
    # 일간 궁합
    stem_a = saju_a['day_elem']
    stem_b = saju_b['day_elem']
    
    comp_db = db.love.get('basic_compatibility', {}).get('element_harmony', {})
    
    # 1. 정확 매칭 시도
    eng_map = {'목':'wood', '화':'fire', '토':'earth', '금':'metal', '수':'water'}
    ea, eb = eng_map[stem_a], eng_map[stem_b]
    
    key1 = f"{ea}_{eb}" # wood_fire
    key2 = f"{eb}_{ea}"
    
    comp_text = comp_db.get(key1, comp_db.get(key2, ""))
    
    if not comp_text:
        comp_text = f"서로 {stem_a}와 {stem_b}의 기운을 가졌네. 서로 다르지만 맞춰가면 좋은 인연일세."

    report['analytics'].append({
        "type": "💞 속궁합 분석",
        "title": f"{user_a['name']}({stem_a}) ❤️ {user_b['name']}({stem_b})",
        "content": comp_text
    })
    
    # 갈등 트리거 (랜덤)
    triggers = list(db.love.get('conflict_triggers', {}).values())
    if triggers:
        warn = random.choice(triggers)
        report['analytics'].append({
            "type": "⚡ 이별 주의보",
            "title": "싸움의 원인?",
            "content": f"**[이유]** {warn.get('fight_reason')}\n\n📢 {warn.get('shamanic_voice')}"
        })

    return report

def _get_eng(k): return {'목':'Wood','화':'Fire','토':'Earth','금':'Metal','수':'Water'}.get(k,'')
