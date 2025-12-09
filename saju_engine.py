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
    try:
        geolocator = Nominatim(user_agent="shinryeong_app_v3")
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
    if dt.month < 2 or (dt.month == 2 and dt.day < 4): year_ganji_idx = (y - 1 - 4) % 60
    else: year_ganji_idx = (y - 4) % 60
    year_stem = CHEONGAN[year_ganji_idx % 10]
    year_branch = JIJI[year_ganji_idx % 12]
    
    month_base_idx = (year_ganji_idx % 10 % 5) * 2 + 2
    month_branch_idx = (dt.month + 10) % 12
    if dt.day < 5: month_branch_idx = (month_branch_idx - 1) % 12
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

    pillars = {'year': f"{year_stem}{year_branch}", 'month': f"{month_stem}{month_branch}", 'day': f"{day_stem}{day_branch}", 'time': f"{hour_stem}{hour_branch}"}
    counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
    for char in [year_stem, year_branch, month_stem, month_branch, day_stem, day_branch, hour_stem, hour_branch]:
        if char in OHENG_MAP: counts[OHENG_MAP[char]] += 1
            
    return {
        'ganji_text': f"{year_stem}{year_branch}년 {month_stem}{month_branch}월 {day_stem}{day_branch}일 {hour_stem}{hour_branch}시",
        'pillars': pillars, 'day_stem': day_stem, 'day_elem': OHENG_MAP[day_stem],
        'five_elem_counts': counts, 'true_solar_time': dt.strftime("%Y-%m-%d %H:%M")
    }

# ==========================================
# 2. 데이터베이스 로더 (경로 자동 인식)
# ==========================================
class SajuDB:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_folder = os.path.join(current_dir, "saju_db")
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
                self.load_status[filename] = "✅ Loaded"
                return json.load(f)
        except Exception as e:
            self.load_status[filename] = f"❌ Error: {e}"
            return {}

    def load_csv(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            df = pd.read_csv(full_path)
            self.load_status[filename] = "✅ Loaded"
            return df
        except Exception as e:
            self.load_status[filename] = f"❌ Error: {e}"
            return pd.DataFrame()

db = SajuDB()

# ==========================================
# 3. 유연한 검색 엔진 (Smart Match Engine)
# ==========================================
def find_in_db(data_dict, keyword):
    """키워드가 포함된 키의 값을 반환 (Fuzzy Match)"""
    if not isinstance(data_dict, dict): return None
    if keyword in data_dict: return data_dict[keyword]
    for k, v in data_dict.items():
        if keyword in k: return v
    return None

def _get_data_safe(db_source, primary_key, fallback_keys=[]):
    """
    DB에서 데이터를 꺼낼 때, 키가 없으면 대체 키를 찾거나
    아예 루트(Root)에서 찾아보는 안전 함수
    """
    # 1. Primary Key 시도 (예: imbalance_analysis)
    if primary_key in db_source:
        return db_source[primary_key]
    
    # 2. Fallback Keys 시도 (예: imbalance_matrix)
    for k in fallback_keys:
        if k in db_source:
            return db_source[k]
            
    # 3. 못 찾았으면 혹시 Root 자체가 데이터인가? (예: 목(Wood) 키가 바로 있는지 확인)
    # 샘플 키워드('목' or '갑' 등)가 있는지 확인해보고 맞으면 통째로 반환
    sample_keys = ['목', '화', '토', '금', '수', 'Wood', 'Fire', '비겁', '식상', '2026', '2025']
    for k in db_source.keys():
        for sample in sample_keys:
            if sample in k:
                return db_source # 상자 없이 내용물이 바로 있는 경우
                
    return {} # 정말 없음

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
    
    # [분석 1] 오행 과다/고립 (Data Loading 보정 적용)
    # 상자 이름이 imbalance_analysis인지, imbalance_matrix인지, 아니면 없는지 확인
    imbalance_db = _get_data_safe(db.five_elements, 'imbalance_analysis', ['imbalance_matrix', 'patterns'])
    
    has_imbalance = False
    for elem, count in counts.items():
        found_data = find_in_db(imbalance_db, elem) # "금"으로 "금(Metal)" 찾기
        
        if found_data:
            data = None
            tag = ""
            if count >= 3:
                data = found_data.get('excess')
                tag = "과다"
            elif count == 0:
                data = found_data.get('isolation')
                tag = "부족"
            
            if data:
                report['analytics'].append({
                    "type": f"⚠️ 기질 분석 ({tag})",
                    "title": data.get('title', f'{elem} 기운 {tag}'),
                    "content": data.get('shamanic_voice', '기운이 치우쳐 있어.')
                })
                report['chat_context'].append(f"{elem} {tag}")
                has_imbalance = True

    if not has_imbalance:
        report['analytics'].append({"type": "⚖️ 오행의 조화", "title": "오행이 골고루 갖춰진 귀격", "content": "치우침 없이 원만한 성품일세."})

    # [분석 2] 직업 (Career) - Data Loading 보정
    strongest = max(counts, key=counts.get)
    trait_map = {'목':'식상', '화':'재성', '토':'비겁', '금':'관성', '수':'인성'}
    keyword = trait_map.get(strongest, '식상')
    
    # career_db에서 modern_jobs 키가 없어도 찾도록 보정
    career_data_source = _get_data_safe(db.career, 'modern_jobs', ['jobs', 'career_list'])
    job_data = find_in_db(career_data_source, keyword)
    
    if job_data:
        report['analytics'].append({
            "type": "💼 신령의 천직 추천",
            "title": f"'{strongest}' 기운을 쓰는 일",
            "content": f"**[성향]** {job_data.get('trait', '')}\n\n**[추천]** {job_data.get('jobs', '')}\n\n📢 {job_data.get('shamanic_voice', '')}"
        })
    else:
        # Fallback
        report['analytics'].append({
             "type": "💼 신령의 천직 추천",
             "title": f"'{strongest}' 기운 활용",
             "content": "데이터베이스 연결이 원활하지 않으나, 자네의 강점을 살리는 전문직이나 사업이 어울리네."
        })

    # [분석 3] 2026년 예언 (Timeline)
    future_source = _get_data_safe(db.timeline, 'future_flow_db', ['timeline', 'yearly_flow'])
    year_data = find_in_db(future_source, "2026")
    
    if year_data:
        report['analytics'].append({
            "type": "🔮 2026년 병오년 예언",
            "title": year_data.get('year_title', '내년 운세'),
            "content": f"{year_data.get('summary', '')}\n\n**[여름 경고]** {year_data.get('Q2_Summer', {}).get('shamanic_warning', '매사 조심하게.')}"
        })

    return report

def analyze_compatibility_precision(user_a, user_b):
    res_a = analyze_saju_precision(user_a)
    res_b = analyze_saju_precision(user_b)
    
    report = {
        "saju_a": res_a['saju'], "saju_b": res_b['saju'],
        "analytics": [],
        "chat_context": res_a['chat_context'] + res_b['chat_context']
    }
    
    # 속궁합
    stem_a = res_a['saju']['day_elem']
    stem_b = res_b['saju']['day_elem']
    
    # love_db 로딩 보정
    comp_db = _get_data_safe(db.love, 'basic_compatibility', ['compatibility'])
    if 'element_harmony' in comp_db: comp_db = comp_db['element_harmony']
    
    eng_map = {'목':'wood', '화':'fire', '토':'earth', '금':'metal', '수':'water'}
    key1 = f"{eng_map[stem_a]}_{eng_map[stem_b]}"
    key2 = f"{eng_map[stem_b]}_{eng_map[stem_a]}"
    
    comp_text = comp_db.get(key1, comp_db.get(key2, ""))
    if not comp_text: comp_text = "서로 맞춰가는 평범한 인연일세."

    report['analytics'].append({
        "type": "💞 속궁합 분석",
        "title": f"{user_a['name']}({stem_a}) ❤️ {user_b['name']}({stem_b})",
        "content": comp_text
    })
    
    # 갈등 원인
    conflict_db = _get_data_safe(db.love, 'conflict_triggers', ['triggers'])
    if conflict_db:
        # dict values list로 변환
        triggers = list(conflict_db.values())
        if triggers:
            warn = triggers[0] # 랜덤 대신 첫번째 or 랜덤
            import random
            warn = random.choice(triggers)
            report['analytics'].append({
                "type": "⚡ 이별 주의보",
                "title": "싸움의 원인",
                "content": f"**[이유]** {warn.get('fight_reason')}\n\n📢 {warn.get('shamanic_voice')}"
            })

    return report

def _get_eng(k): return {'목':'Wood','화':'Fire','토':'Earth','금':'Metal','수':'Water'}.get(k,'')
