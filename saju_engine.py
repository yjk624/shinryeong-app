import json
import pandas as pd
import os
import ephem
import math
from datetime import datetime, timedelta
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from typing import Dict, Any, List, Optional

# ==========================================
# 1. 상수 및 기본 맵핑 (Constants & Maps)
# ==========================================
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
OHENG_MAP = {
    '갑': '목', '을': '목', '병': '화', '정': '화', '무': '토', '기': '토', 
    '경': '금', '신': '금', '임': '수', '계': '수',
    '인': '목', '묘': '목', '사': '화', '오': '화', '진': '토', '술': '토', '축': '토', '미': '토',
    '신': '금', '유': '금', '해': '수', '자': '수'
}
JIJANGGAN = {
    '자': ['임', '계'], '축': ['계', '신', '기'], '인': ['무', '병', '갑'], 
    '묘': ['갑', '을'], '진': ['을', '계', '무'], '사': ['무', '경', '병'],
    '오': ['병', '기', '정'], '미': ['정', '을', '기'], '신': ['경', '임', '무'], 
    '유': ['경', '신'], '술': ['신', '정', '무'], '해': ['무', '갑', '임']
}
SIBSEONG_MAP = {
    # 십성 맵핑 전체 (Day Gan : Target Gan)
    ('갑', '갑'): '비견', ('갑', '을'): '겁재', ('갑', '병'): '식신', ('갑', '정'): '상관', ('갑', '무'): '편재',
    ('갑', '기'): '정재', ('갑', '경'): '편관', ('갑', '신'): '정관', ('갑', '임'): '편인', ('갑', '계'): '정인',
    ('을', '갑'): '겁재', ('을', '을'): '비견', ('을', '병'): '상관', ('을', '정'): '식신', ('을', '무'): '정재',
    ('을', '기'): '편재', ('을', '경'): '정관', ('을', '신'): '편관', ('을', '임'): '정인', ('을', '계'): '편인',
    ('병', '갑'): '편인', ('병', '을'): '정인', ('병', '병'): '비견', ('병', '정'): '겁재', ('병', '무'): '식신',
    ('병', '기'): '상관', ('병', '경'): '편재', ('병', '신'): '정재', ('병', '임'): '편관', ('병', '계'): '정관',
    ('정', '갑'): '정인', ('정', '을'): '편인', ('정', '병'): '겁재', ('정', '정'): '비견', ('정', '무'): '상관',
    ('정', '기'): '식신', ('정', '경'): '정재', ('정', '신'): '편재', ('정', '임'): '정관', ('정', '계'): '편관',
    ('무', '갑'): '편관', ('무', '을'): '정관', ('무', '병'): '편인', ('무', '정'): '정인', ('무', '무'): '비견',
    ('무', '기'): '겁재', ('무', '경'): '식신', ('무', '신'): '상관', ('무', '임'): '편재', ('무', '계'): '정재',
    ('기', '갑'): '정관', ('기', '을'): '편관', ('기', '병'): '정인', ('기', '정'): '편인', ('기', '무'): '겁재',
    ('기', '기'): '비견', ('기', '경'): '상관', ('기', '신'): '식신', ('기', '임'): '정재', ('기', '계'): '편재',
    ('경', '갑'): '편재', ('경', '을'): '정재', ('경', '병'): '편관', ('경', '정'): '정관', ('경', '무'): '편인',
    ('경', '기'): '정인', ('경', '경'): '비견', ('경', '신'): '겁재', ('경', '임'): '식신', ('경', '계'): '상관',
    ('신', '갑'): '정재', ('신', '을'): '편재', ('신', '병'): '정관', ('신', '정'): '편관', ('신', '무'): '정인',
    ('신', '기'): '편인', ('신', '경'): '겁재', ('신', '신'): '비견', ('신', '임'): '상관', ('신', '계'): '식신',
    ('임', '갑'): '식신', ('임', '을'): '상관', ('임', '병'): '편재', ('임', '정'): '정재', ('임', '무'): '편관',
    ('임', '기'): '정관', ('임', '경'): '편인', ('임', '신'): '정인', ('임', '임'): '비견', ('임', '계'): '겁재',
    ('계', '갑'): '상관', ('계', '을'): '식신', ('계', '병'): '정재', ('계', '정'): '편재', ('계', '무'): '정관',
    ('계', '기'): '편관', ('계', '경'): '정인', ('계', '신'): '편인', ('계', '임'): '겁재', ('계', '계'): '비견',
}

# ==========================================
# 2. 유틸리티 및 계산 함수 (Utility & Calculation)
# ==========================================

def get_location_info(city_name: str) -> Optional[Dict[str, Any]]:
    """도시 이름으로 위도, 경도, 시간대 정보를 가져옵니다."""
    try:
        geolocator = Nominatim(user_agent="shinryeong_app_v4")
        location = geolocator.geocode(city_name)
        if not location: return None
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone_str": timezone_str
        }
    except Exception:
        return None

def get_true_solar_time(dt: datetime, longitude: float, timezone_str: str) -> datetime:
    """사용자 좌표를 기준으로 진태양시를 계산하여 시간을 보정합니다. (KST 135도 기준)"""
    try:
        local_tz = pytz.timezone(timezone_str)
        local_dt = local_tz.localize(dt)
        utc_dt = local_dt.astimezone(pytz.utc)
        
        sun = ephem.Sun()
        observer = ephem.Observer()
        observer.lon = str(longitude * ephem.degree)
        next_noon = observer.next_transit(ephem.Sun(), start=utc_dt, use_center=True)
        
        noon_kst = pytz.utc.localize(next_noon).astimezone(pytz.timezone('Asia/Seoul'))
        std_noon_kst = noon_kst.replace(hour=12, minute=0, second=0, microsecond=0)
        
        time_offset = noon_kst - std_noon_kst
        true_solar_dt = dt + time_offset
        
        return true_solar_dt.replace(tzinfo=None)
    except Exception:
        return dt

def get_ganji(dt: datetime, is_lunar: bool = False, is_leap_month: bool = False) -> Dict[str, str]:
    """
    정밀한 진태양시 기준으로 년월일시 간지를 계산합니다. (DB 부재로 더미 로직 사용)
    """
    # 🚨 실제 만세력 DB가 필요함. 여기서는 특정 날짜에 대한 더미 간지 사용.
    if dt.year == 2025 and dt.month == 12 and dt.day == 9:
         # 2025년 12월 9일 17:45 (가정)
         ganji = {'year_gan': '을', 'year_ji': '사', 'month_gan': '무', 'month_ji': '자',
             'day_gan': '경', 'day_ji': '진', 'time_gan': '을', 'time_ji': '유'}
    else:
        # 기본 더미: 2023년 3월 15일 14:30 (계묘년 을묘월 정축일 정미시)
        ganji = {'year_gan': '계', 'year_ji': '묘', 'month_gan': '을', 'month_ji': '묘',
                 'day_gan': '정', 'day_ji': '축', 'time_gan': '정', 'time_ji': '미'}
        
    return ganji

def _get_data_safe(db: Dict, key_path: str) -> Any:
    """JSON DB에서 안전하게 데이터를 추출합니다."""
    keys = key_path.split('.')
    data = db
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return {}
    return data

def calculate_sibseong(day_gan: str, ganji_map: Dict[str, str]) -> Dict[str, str]:
    """4柱 8글자에 대한 십성(十星)을 계산합니다. (천간 중심)"""
    result = {}
    for column in ['year', 'month', 'day', 'time']:
        gan = ganji_map[f'{column}_gan']
        ji = ganji_map[f'{column}_ji']
        
        # 1. 천간 십성
        result[f'{column}_gan'] = SIBSEONG_MAP.get((day_gan, gan), '일간')
        
        # 2. 지장간 십성 (주요 지장간만)
        main_jijanggan = JIJANGGAN.get(ji, [])
        if main_jijanggan:
            # 여기서는 지장간의 첫 번째 글자 십성만 대표로 저장
            jg_gan = main_jijanggan[0] 
            result[f'{column}_ji_sibseong'] = SIBSEONG_MAP.get((day_gan, jg_gan), '')
                
    return result

def calculate_five_elements_count(ganji_map: Dict[str, str]) -> Dict[str, float]:
    """사주 8글자 및 지장간까지 오행 카운트를 계산합니다. (지장간 가중치 0.5)"""
    counts = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    
    # 1. 8글자 오행 카운트 (가중치 1)
    for key in ['year_gan', 'year_ji', 'month_gan', 'month_ji', 
                'day_gan', 'day_ji', 'time_gan', 'time_ji']:
        char = ganji_map[key]
        element = OHENG_MAP.get(char)
        if element:
            counts[element] += 1
            
    # 2. 지장간 오행 카운트 (주요 2개, 가중치 0.5)
    for ji in [ganji_map['year_ji'], ganji_map['month_ji'], 
               ganji_map['day_ji'], ganji_map['time_ji']]:
        jijanggan_list = JIJANGGAN.get(ji, [])
        for i in range(min(2, len(jijanggan_list))): 
            jg_gan = jijanggan_list[i]
            element = OHENG_MAP.get(jg_gan)
            if element:
                counts[element] += 0.5 
                
    return counts

# ==========================================
# 3. DB 기반 심층 분석 함수 (Deep Dive Analysis)
# ==========================================

def get_day_pillar_identity(day_ganji: str, db: Dict) -> Dict[str, str]:
    """identity_db.json을 사용하여 일주(日柱)의 특징을 분석합니다."""
    identity_data = db.get('identity', {}).get(day_ganji, {})
    return {
        "title": f"일주({day_ganji})의 고유 기질",
        "shamanic_voice": identity_data.get('ko', "일주 데이터를 찾을 수 없네."),
        "keywords": ", ".join(identity_data.get('keywords', []))
    }

def analyze_ohang_imbalance(ohang_counts: Dict[str, float], day_gan_elem: str, db: Dict) -> List[Dict[str, Any]]:
    """five_elements_matrix.json과 health_db.json을 사용하여 오행 불균형을 분석합니다."""
    reports = []
    matrix_db = db.get('five_elements', {})
    health_db = db.get('health', {}).get('health_remedy', {})
    elements = ['목', '화', '토', '금', '수']
    eng_map = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}
    
    for elem in elements:
        count = ohang_counts.get(elem, 0)
        
        # 과다(Excess) 분석 (3.5 이상)
        if count >= 3.5:
            data = matrix_db.get(f"{elem}({eng_map.get(elem)})", {}).get("excess", {})
            if data:
                reports.append({
                    "type": f"🔥 오행 **{elem}** 과다 (태과)",
                    "title": data.get('title', f"{elem} 기운이 넘쳐흐르네."),
                    "content": f"**심리:** {data.get('psychology', '')}"
                                f"\n**신체:** {data.get('physical', '')}"
                                f"\n*신령의 충고:* {data.get('shamanic_voice', '기운을 좀 빼내게나.')}"
                })
        
        # 고립(Isolation) 분석 (0.5 이하)
        elif count <= 0.5:
            data = matrix_db.get(f"{elem}({eng_map.get(elem)})", {}).get("isolation", {})
            remedy = health_db.get(f"{elem}({eng_map.get(elem)})_문제", {})
            
            if data and remedy:
                reports.append({
                    "type": f"🧊 오행 **{elem}** 부족 (고립)",
                    "title": data.get('title', f"{elem} 기운이 너무 약하네."),
                    "content": f"**심리:** {data.get('psychology', '')}"
                                f"\n**신체:** {data.get('physical', '')}"
                                f"\n\n**개운법:**"
                                f"\n* **음식:** {remedy.get('food_remedy', '')}"
                                f"\n* **행동:** {remedy.get('action_remedy', '')}"
                                f"\n*신령의 일침:* {data.get('shamanic_voice', '기운을 채워야 할 때네.')}"
                })
                
    return reports

def perform_cold_reading(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    """symptom_mapping.json을 사용하여 콜드 리딩 분석을 수행합니다. (콜드리딩 DB 사용)"""
    reports = []
    symptom_db = db.get('symptom', {}).get('patterns', {})
    ohang_counts = calculate_five_elements_count(ganji_map)
    
    # 1. 습한 사주 체크
    if ohang_counts.get('수', 0) >= 3 or ganji_map['month_ji'] in ['해', '자', '축']:
        data = symptom_db.get('습한_사주(Wet_Chart)', {})
        if data:
            reports.append({
                "type": "☔ 습한 사주 (환경 진단)",
                "title": f"이 신령이 자네의 환경을 먼저 짚어보네.",
                "content": f"**환경/주거지:** {data.get('environment', '')}"
                           f"\n**신체 증상:** {data.get('body', '')}"
                           f"\n*신령의 일침:* {data.get('shamanic_voice', '눅눅한 기운을 걷어내게.')}"
            })
            
    # 2. 양인살 발동 체크
    day_gan = ganji_map['day_gan']
    yangin_ji = {'갑': '묘', '병': '오', '무': '오', '경': '유', '임': '자'}.get(day_gan)
    
    if yangin_ji and (ganji_map['day_ji'] == yangin_ji or ganji_map['month_ji'] == yangin_ji):
        data = symptom_db.get('양인살_발동(Sheep_Blade)', {})
        if data:
            reports.append({
                "type": "🔪 양인살 발동 (기질 진단)",
                "title": f"자네 몸에 **강력한 칼날**을 품고 있네.",
                "content": f"**기질/습관:** {data.get('habit', '')}"
                           f"\n**신령의 일침:** {data.get('shamanic_voice', '칼날을 잘 쓰면 명의가 되고 못 쓰면 살인자네.')}"
            })
            
    return reports

def analyze_shinsal(ganji_map: Dict[str, str], db: Dict) -> List[Dict[str, Any]]:
    """shinsal_db.json을 사용하여 신살 분석을 수행합니다. (신살 DB 사용)"""
    reports = []
    shinsal_db = db.get('shinsal', {}).get('basic_meanings', {})
    
    # 도화살 (자오묘유)
    dohwa_jis = ['자', '오', '묘', '유']
    if any(ji in dohwa_jis for ji in [ganji_map['year_ji'], ganji_map['month_ji'], ganji_map['time_ji']]):
        data = shinsal_db.get('도화살(Peach_Blossom)', {})
        if data: reports.append({"type": "🌷 도화살", "title": "타고난 매력의 별", "content": data.get('desc', '') + "\n" + f"**긍정:** {data.get('positive', '')}"})
            
    # 역마살 (인신사해)
    yeokma_jis = ['인', '신', '사', '해']
    if any(ji in yeokma_jis for ji in [ganji_map['year_ji'], ganji_map['day_ji']]):
        data = shinsal_db.get('역마살(Stationary_Horse)', {})
        if data: reports.append({"type": "🐎 역마살", "title": "넓은 세상으로 뻗어 나가는 이동수", "content": data.get('desc', '') + "\n" + f"**긍정:** {data.get('positive', '')}"})
            
    return reports

def analyze_timeline(birth_dt: datetime, day_gan: str, db: Dict) -> List[Dict[str, Any]]:
    """timeline_db.json과 lifecycle_pillar_db.json을 사용하여 현재 운의 흐름을 분석합니다."""
    reports = []
    
    current_year = datetime.now().year
    current_year_gan = '을' # 2025년 기준
    current_year_sibseong = SIBSEONG_MAP.get((day_gan, current_year_gan), '운')
    
    # 1. 세운 분석
    if current_year == 2025:
        timeline_data = db.get('timeline', {}).get("2025_Eul_Sa", {})
        if timeline_data:
            reports.append({
                "type": f"⚡️ **{current_year_sibseong}** 세운 분석",
                "title": timeline_data.get('year_title', f"{current_year}년의 기운이네."),
                "content": timeline_data.get('summary', '') 
                           + "\n\n**상반기 예측:** " + timeline_data.get('first_half', {}).get('prediction', '')
                           + "\n*신령의 경고:* " + timeline_data.get('first_half', {}).get('shamanic_warning', '')
            })
    
    # 2. 라이프 사이클 분석
    age = datetime.now().year - birth_dt.year
    life_stages_db = db.get('timeline', {}).get('life_stages_detailed', {})
    major_pillar_db = db.get('lifecycle', {}).get('prime_pillar', {}) 
    
    # 나이대별 key 찾기
    life_stage_key = ""
    if 30 <= age <= 39: life_stage_key = "settlement"
    # 다른 나이대 로직도 추가 가능...
    
    life_data = life_stages_db.get(life_stage_key, {})
    
    if life_stage_key == "settlement" and life_data: 
        # 대운 십성(임시)을 '정관'으로 가정하여 중년운 분석
        temp_sibseong = '정관' 
        sibseong_desc = major_pillar_db.get(temp_sibseong, '특별한 중년운 설명이 없네.')
        
        reports.append({
            "type": "⚖️ 중년 시기 운세 분석",
            "title": f"**'인생의 기반 다지기'** 시기의 흐름",
            "content": f"자네는 현재 **{life_data.get('desc', '')}**의 흐름에 있네.\n\n"
                       f"이 시기에 **{temp_sibseong}**의 기운이 들어왔으니, {sibseong_desc}"
        })
            
    return reports

# ==========================================
# 4. 메인 처리 함수 (Main Processing)
# ==========================================

def process_saju_input(user_data: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    """개인 사주 분석 및 보고서 생성 (모든 DB 활용)"""
    
    name = user_data['name']
    birth_dt = user_data['birth_dt']
    city_name = user_data.get('city', 'Seoul')
    
    location_info = get_location_info(city_name)
    if location_info:
        true_solar_dt = get_true_solar_time(birth_dt, location_info['longitude'], location_info['timezone_str'])
    else:
        true_solar_dt = birth_dt
        
    ganji_map = get_ganji(true_solar_dt)
    day_gan = ganji_map['day_gan']
    sibseong_map = calculate_sibseong(day_gan, ganji_map)
    five_elements_count = calculate_five_elements_count(ganji_map)
    
    # 최종 보고서 구조
    report: Dict[str, Any] = {
        "user": user_data,
        "saju": ganji_map,
        "analytics": []
    }
    
    # 6-1. 일주 기질 분석 (Identity DB)
    day_ganji = ganji_map['day_gan'] + ganji_map['day_ji']
    identity_analysis = get_day_pillar_identity(day_ganji, db)
    report['analytics'].append({
        "type": "👤 일주(日柱) 기질 분석",
        "title": identity_analysis['title'],
        "content": identity_analysis['shamanic_voice']
    })
    
    # 6-2. 콜드 리딩 (Symptom DB)
    cold_reading_reports = perform_cold_reading(ganji_map, db)
    report['analytics'].extend(cold_reading_reports)
    
    # 6-3. 오행 불균형 & 개운법 (Matrix & Health DB)
    ohang_imbalance_reports = analyze_ohang_imbalance(five_elements_count, day_gan, db)
    report['analytics'].extend(ohang_imbalance_reports)

    # 6-4. 직업/적성 분석 (Career DB)
    sibseong_counts = {} # 십성 카운트 로직은 여기에 유지
    for key, sibseong in sibseong_map.items():
        if key.endswith('_gan') and sibseong != '일간': sibseong_counts[sibseong] = sibseong_counts.get(sibseong, 0) + 1
    
    main_sibseong = max(sibseong_counts, key=sibseong_counts.get) if sibseong_counts else '비견' 
    career_db_data = db.get('career', {}).get('modern_jobs', {})
    sibseong_to_db_key = {'비견': '비겁_태과(Self_Strong)', '겁재': '비겁_태과(Self_Strong)', '식신': '식상_발달(Output_Strong)', '상관': '식상_발달(Output_Strong)', '편재': '재성_발달(Wealth_Strong)', '정재': '재성_발달(Wealth_Strong)', '편관': '관살_발달(Power_Strong)', '정관': '관살_발달(Power_Strong)', '편인': '인성_발달(Resource_Strong)', '정인': '인성_발달(Resource_Strong)',}
    db_key_for_career = sibseong_to_db_key.get(main_sibseong, '비겁_태과(Self_Strong)')
    career_data = career_db_data.get(db_key_for_career, {})
    
    career_analysis = {"type": "💼 직업 및 적성 분석", "title": f"가장 발달한 십성: **{main_sibseong}** (천직)", "content": f"그대는 {main_sibseong}의 기운이 가장 강하니, 이것이 곧 사회적 능력이네."}
    if career_data:
        career_analysis['content'] += f"\n* **타고난 기질:** {career_data.get('trait', '')}"
        career_analysis['content'] += f"\n* **현대 직업:** {career_data.get('jobs', '')}"
        career_analysis['content'] += f"\n* **신령의 충고:** {career_data.get('shamanic_voice', '자네가 하고 싶은 대로 하게나.')}"
    report['analytics'].append(career_analysis)
    
    # 6-5. 신살 분석 (Shinsal DB)
    shinsal_reports = analyze_shinsal(ganji_map, db)
    report['analytics'].extend(shinsal_reports)
    
    # 6-6. 운세 흐름 분석 (Timeline/Lifecycle DB)
    timeline_reports = analyze_timeline(true_solar_dt, day_gan, db)
    report['analytics'].extend(timeline_reports)
        
    return report


def process_love_compatibility(user_a: Dict[str, Any], user_b: Dict[str, Any], db: Dict) -> Dict[str, Any]:
    """두 사주를 비교하여 궁합을 분석합니다. (Compatibility DB 강화)"""
    
    res_a = process_saju_input(user_a, db)
    res_b = process_saju_input(user_b, db)
    
    ganji_a = res_a['saju']
    ganji_b = res_b['saju']
    
    report = {"user_a_saju": ganji_a, "user_b_saju": ganji_b, "analytics": []}
    
    # 1. 천간합 궁합 분석 (Compatibility DB 사용)
    gan_a = ganji_a['day_gan']
    gan_b = ganji_b['day_gan']
    comp_db = db.get('compatibility', {}) 
    
    key1 = f"{gan_a}_{gan_b}"
    key2 = f"{gan_b}_{gan_a}"
    comp_data = comp_db.get(key1, comp_db.get(key2, {}))
    
    comp_analysis = {"type": "💖 일간(日干) 기운 궁합 분석", "title": f"{user_a['name']}({gan_a}) ❤️ {user_b['name']}({gan_b})의 화학적 결합", "content": "두 분의 타고난 성향이 만나 만들어내는 운명적 관계라네."}
    
    if comp_data:
        comp_analysis['content'] = comp_data.get('ko_relation', '평범하지만 서로 맞춰가는 인연일세.')
        score = comp_data.get('score', '??')
        comp_analysis['content'] += f"\n\n**신령 궁합 점수:** {score}점 (100점 만점)"
    report['analytics'].append(comp_analysis)
    
    # 2. 갈등 원인 (Love DB 사용)
    conflict_db = db.get('love', {}).get('conflict_triggers', {})
    conflict_data = None
    
    # 재다신약 (남성) - 3개 이상 가정
    if ganji_a.get('gender') == '남' and five_elements_count.get('재성', 0) >= 3: 
        conflict_data = conflict_db.get('재다신약_남성')
    # 관살혼잡 (여성) - 3개 이상 가정
    elif ganji_a.get('gender') == '여' and five_elements_count.get('관성', 0) >= 3: 
        conflict_data = conflict_db.get('관살혼잡_여성')
    # 간여지동 커플 (일주 동일 오행)
    elif ganji_a['day_gan'] == ganji_b['day_gan'] and OHENG_MAP[ganji_a['day_gan']] == OHENG_MAP[ganji_a['day_ji']]:
         conflict_data = conflict_db.get('간여지동_커플')
    
    if conflict_data:
        report['analytics'].append({
            "type": "⚔️ 주요 갈등 원인",
            "title": f"이 커플의 다툼은 **{conflict_data.get('partner_context', '특정 패턴')}**에서 시작되네.",
            "content": f"**싸움 이유:** {conflict_data.get('fight_reason', '')}"
                       f"\n*신령의 일침:* {conflict_data.get('shamanic_voice', '서로 고집 좀 꺾으시게.')}"
        })
    else:
        report['analytics'].append({
            "type": "⚔️ 주요 갈등 원인",
            "title": "특별히 눈에 띄는 흉한 조합은 없네.",
            "content": "두 분 모두 평범한 연애를 지향하는구먼. 작은 다툼은 있겠으나, 큰 갈등 없이 무난히 지낼 수 있네."
        })
        
    return report
