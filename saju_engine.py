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

def calculate_true_solar_time(birth_dt, lat, lon, timezone_str):
    """
    진태양시(True Solar Time) 계산
    :param birth_dt: 입력받은 생년월일시 (datetime)
    :param lat: 위도
    :param lon: 경도
    :param timezone_str: 타임존 (예: 'Asia/Seoul')
    :return: 진태양시 적용된 datetime
    """
    # 1. 입력 시간을 UTC로 변환
    local_tz = pytz.timezone(timezone_str)
    try:
        dt_aware = local_tz.localize(birth_dt)
    except ValueError: # 이미 tzinfo가 있는 경우
        dt_aware = birth_dt.astimezone(local_tz)
        
    dt_utc = dt_aware.astimezone(pytz.UTC)
    
    # 2. 균시차(Equation of Time) 및 경도 보정
    # ephem은 UTC 기준 계산
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = dt_utc
    
    sun = ephem.Sun(observer)
    
    # 태양의 남중 시각(Transit time) 계산은 복잡하므로, 
    # 간이식: (해당 지역 경도 - 표준 자오선) * 4분 보정 + 균시차
    # 여기서는 좀 더 정밀한 사주식 '경도 보정'만 적용 (가장 큰 요인)
    
    # 해당 타임존의 표준 자오선 계산 (대략적)
    # tz offset in hours
    offset = dt_aware.utcoffset().total_seconds() / 3600
    standard_meridian = offset * 15 # 1시간 = 15도
    
    diff_deg = lon - standard_meridian
    correction_minutes = diff_deg * 4 # 1도당 4분
    
    # 진태양시 = 시계시간 + 경도보정 (균시차는 사주학파마다 이견이 있어 일단 경도보정만 적용)
    true_solar_dt = birth_dt + timedelta(minutes=correction_minutes)
    
    return true_solar_dt

def get_solar_terms(year):
    """해당 연도의 24절기 날짜 계산 (ephem 사용)"""
    terms = {}
    observer = ephem.Observer()
    
    # 입춘(315도)부터 대한(300도)까지 15도 간격
    # 0도=춘분, 15=청명 ... 315=입춘
    # 사주 새해 기준은 '입춘(315도)'
    
    start_date = ephem.Date(f"{year}-01-01")
    sun = ephem.Sun()
    
    # 24절기 각도 (입춘 시작)
    # 입춘은 전년도 태양황경 315도 지점 or 금년도 315도
    # 편의상 월별 절기 진입일 계산 로직
    # (여기서는 약식 구현 대신, 월주 계산을 위한 핵심 로직만 구현)
    pass 
    # *정밀 구현이 너무 길어져, 월주 결정 핵심 로직(절입일)만 동적으로 처리*

def calculate_saju_pillars(dt):
    """
    진태양시 기준 사주 팔자(4기둥) 도출
    """
    # 1. 연주 (Year Pillar) - 입춘 기준
    # ephem으로 입춘 시각 계산
    sun = ephem.Sun()
    y = dt.year
    
    # 입춘 찾기 (태양 황경 315도)
    def find_term(angle, year):
        # 대략 2월 4일 근처
        start = ephem.Date(f"{year}-02-01")
        # 뉴턴법 등으로 정확한 시각 찾기 (약식: 2월3일~5일 사이 검색)
        for i in range(5000): # 분 단위 검색 (느림, 최적화 필요)
            d = ephem.Date(start + i * ephem.minute)
            sun.compute(d)
            # ephem uses radians. 315 deg = 5.497 rad
            if sun.hlon >= 5.49778: # 315도 라디안 근사값
                return d.datetime()
        return datetime(year, 2, 4) # fallback

    # *성능을 위해 간이 절기표 알고리즘 사용 (ephem loop는 너무 느림)*
    # 띠 계산 (입춘 기준)
    if dt.month < 2 or (dt.month == 2 and dt.day < 4):
        year_ganji_idx = (y - 1 - 4) % 60
    elif dt.month == 2 and dt.day >= 4:
        # 2월 4일~5일 경계는 시간까지 봐야 하나 여기선 4일 이후면 새해로 간주
        year_ganji_idx = (y - 4) % 60
    else:
        year_ganji_idx = (y - 4) % 60
        
    year_stem = CHEONGAN[year_ganji_idx % 10]
    year_branch = JIJI[year_ganji_idx % 12]
    
    # 2. 월주 (Month Pillar) - 절기 기준
    # 연간에 따른 월두법 (진술축미 월 등 복잡, 여기선 약식 월두법 적용)
    month_base_idx = (year_ganji_idx % 10 % 5) * 2 + 2 # 갑기년은 병인월두...
    # 양력 2월(인월)부터 시작. 입춘 지났으면 인월.
    # 절기 보정 로직 생략(복잡), 양력 월 기반 근사치 적용
    month_branch_idx = (dt.month + 10) % 12 # 2월->2(인), 3월->3(묘)...
    if dt.day < 5: # 절기 전이면 전달 기운
        month_branch_idx = (month_branch_idx - 1) % 12
        
    month_stem_idx = (month_base_idx + (month_branch_idx - 2)) % 10 
    month_stem = CHEONGAN[month_stem_idx]
    month_branch = JIJI[month_branch_idx]

    # 3. 일주 (Day Pillar)
    # 1900년 1월 1일 갑술일 기준 계산
    base_date = datetime(1900, 1, 1)
    diff_days = (dt - base_date).days
    day_ganji_idx = (10 + diff_days) % 60 # 10은 갑술(11번째) 보정
    day_stem = CHEONGAN[day_ganji_idx % 10]
    day_branch = JIJI[day_ganji_idx % 12]

    # 4. 시주 (Hour Pillar)
    # 일간에 따른 시두법
    hour_base_idx = (day_ganji_idx % 10 % 5) * 2
    # 자시(23~01)부터 시작, 2시간 간격
    h = dt.hour
    if h >= 23:
        hour_branch_idx = 0 # 야자시
    else:
        hour_branch_idx = (h + 1) // 2
    
    hour_stem_idx = (hour_base_idx + hour_branch_idx) % 10
    hour_stem = CHEONGAN[hour_stem_idx]
    hour_branch = JIJI[hour_branch_idx % 12]

    # 오행 통계
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
# 2. 데이터베이스 로더 & 분석 엔진
# ==========================================
class SajuDB:
    def __init__(self):
        self.db_folder = "saju_db"
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
                return json.load(f)
        except: return {}

    def load_csv(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            return pd.read_csv(full_path)
        except: return pd.DataFrame()

db = SajuDB()

def analyze_saju_precision(user_data):
    # 1. 위치 기반 진태양시 계산
    loc_info = get_location_info(user_data['city'])
    if not loc_info:
        # 위치 못 찾으면 기본값(서울 표준) 처리
        lat, lon, tz = 37.5665, 126.9780, 'Asia/Seoul'
    else:
        lat, lon, tz = loc_info['lat'], loc_info['lon'], loc_info['timezone']
        
    birth_dt = datetime(user_data['year'], user_data['month'], user_data['day'], user_data['hour'], user_data['minute'])
    true_dt = calculate_true_solar_time(birth_dt, lat, lon, tz)
    
    # 2. 사주 명식 추출
    saju = calculate_saju_pillars(true_dt)
    saju['location_info'] = f"{user_data['city']} (보정시각: {true_dt.strftime('%H:%M')})"
    
    report = {"saju": saju, "analytics": [], "chat_context": []}
    counts = saju['five_elem_counts']
    
    # [분석 1] 오행 과다/고립 (Always check)
    has_imbalance = False
    for elem, count in counts.items():
        # 키 매칭 로직 강화 (JSON 키: "목(Wood)" 형식 대응)
        key_korean = f"{elem}({_get_eng(elem)})"
        
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
        report['analytics'].append({"type": "⚖️ 오행의 조화", "title": "오행이 골고루 갖춰진 귀격", "content": "치우침 없이 원만한 성품일세. 어디 가서든 둥글게 잘 어울릴 팔자야."})

    # [분석 2] 직업 적성 (가장 강한 기운 기준)
    strongest = max(counts, key=counts.get)
    job_key_prefix = _get_job_key_prefix(strongest) # 예: '식상_발달'
    
    found_job = False
    if db.career and 'modern_jobs' in db.career:
        for k, v in db.career['modern_jobs'].items():
            if job_key_prefix in k:
                report['analytics'].append({"type": "💼 신령의 천직 추천", "title": f"'{strongest}' 기운을 쓰는 직업", "content": f"**[성향]** {v['trait']}\n\n**[추천]** {v['jobs']}\n\n📢 {v['shamanic_voice']}"})
                found_job = True
                break
                
    # [분석 3] 2026년 운세
    if db.timeline and 'future_flow_db' in db.timeline:
        flow = db.timeline['future_flow_db'].get('2026_Byeong_O', {})
        report['analytics'].append({"type": "🔮 2026년 병오년 예언", "title": flow['year_title'], "content": f"{flow['summary']}\n\n**[여름 조심]** {flow['Q2_Summer']['shamanic_warning']}"})

    return report

def analyze_compatibility_precision(user_a, user_b):
    # (위의 analyze_saju_precision 로직 활용하여 사주 2개 뽑고 비교)
    # 지면상 핵심 로직은 기존 analyze_compatibility와 동일하되
    # 입력값을 precision 버전으로 처리하는 부분만 연결하면 됨
    pass # app.py에서 호출 시 각각 analyze_saju_precision을 불러 데이터를 합치면 됨

# --- Helpers ---
def _get_eng(k): return {'목':'Wood','화':'Fire','토':'Earth','금':'Metal','수':'Water'}.get(k,'')
def _get_job_key_prefix(k): return {'목':'식상','화':'재성','토':'비겁','금':'관성','수':'인성'}.get(k,'식상')
