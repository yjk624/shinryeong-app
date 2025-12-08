import ephem
import math
from datetime import datetime, timedelta

# ==========================================
# 1. CONSTANTS & MAPPINGS (KOREAN NATIVE)
# ==========================================
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
ZODIAC = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]

# 오행 매핑 (목, 화, 토, 금, 수)
ELEMENTS = {
    "갑": "목", "을": "목", "인": "목", "묘": "목",
    "병": "화", "정": "화", "사": "화", "오": "화",
    "무": "토", "기": "토", "진": "토", "술": "토", "축": "토", "미": "토",
    "경": "금", "신": "금", "신": "금", "유": "금", # 신(申)은 금, 신(辛)도 금
    "임": "수", "계": "수", "해": "수", "자": "수"
}

# 십성 계산을 위한 오행 생극 관계 (아생식, 아극재, 관극아, 인생아, 비겁)
TEN_GODS_MAP = {
    # (일간오행, 대상오행, 음양같음여부) -> 십성
    # 목(0), 화(1), 토(2), 금(3), 수(4)
    # 음양: 양(0), 음(1)
}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_ganji_korean(index):
    return f"{CHEONGAN[index % 10]}{JIJI[index % 12]}"

def get_ganji_tuple(index):
    return (CHEONGAN[index % 10], JIJI[index % 12])

def get_element(char):
    # 신(申)과 신(辛) 구분 처리 필요 시 로직 추가
    if char in ["신"] and char not in CHEONGAN: return "금" # 지지 신
    return ELEMENTS.get(char, "")

def calculate_ten_gods(day_stem, target_stem):
    """
    일간(Day Stem)과 대상(Target) 간의 십성(Ten Gods) 관계를 계산합니다.
    """
    # 오행 인덱스: 목0, 화1, 토2, 금3, 수4
    elem_order = ['목', '화', '토', '금', '수']
    
    # 천간 음양오행 데이터
    stems_info = {
        '갑': (0, 0), '을': (0, 1), # (오행인덱스, 음양:0양/1음)
        '병': (1, 0), '정': (1, 1),
        '무': (2, 0), '기': (2, 1),
        '경': (3, 0), '신': (3, 1),
        '임': (4, 0), '계': (4, 1)
    }
    # 지지 음양오행 데이터 (지장간 정기 기준)
    branches_info = {
        '인': (0, 0), '묘': (0, 1),
        '사': (1, 0), '오': (1, 1),
        '진': (2, 0), '술': (2, 0), '축': (2, 1), '미': (2, 1),
        '신': (3, 0), '유': (3, 1),
        '해': (4, 0), '자': (4, 1) # 자수는 체는 양이나 용은 음 (명리에선 음으로 봄) -> 여기선 음(1)으로 처리
    }
    # 자수는 음수(1), 해수는 양수(0) / 사화는 양화(0), 오화는 음화(1) (체용론 적용)
    
    my_e, my_yin = stems_info.get(day_stem, (0, 0))
    
    if target_stem in stems_info:
        tgt_e, tgt_yin = stems_info[target_stem]
    elif target_stem in branches_info:
        tgt_e, tgt_yin = branches_info[target_stem]
    else:
        return "Unknown"

    # 관계 계산 (Target - Me)
    diff = (tgt_e - my_e) % 5
    is_same_yin = (my_yin == tgt_yin)
    
    if diff == 0: return "비견" if is_same_yin else "겁재"
    if diff == 1: return "식신" if is_same_yin else "상관"
    if diff == 2: return "편재" if is_same_yin else "정재"
    if diff == 3: return "편관" if is_same_yin else "정관"
    if diff == 4: return "편인" if is_same_yin else "정인"
    
    return "X"

def calculate_shinsal(full_str):
    """
    사주 원국 문자열을 분석하여 주요 신살을 추출합니다.
    """
    shinsal = []
    # 1. 역마살 (인신사해)
    if any(c in full_str for c in "인신사해"):
        shinsal.append("역마살(이동/변화)")
    # 2. 도화살 (자오묘유)
    if any(c in full_str for c in "자오묘유"):
        shinsal.append("도화살(인기/매력)")
    # 3. 화개살 (진술축미)
    if any(c in full_str for c in "진술축미"):
        shinsal.append("화개살(예술/종교)")
    # 4. 현침살 (갑신묘오)
    if any(c in full_str for c in "갑신묘오"):
        shinsal.append("현침살(예민/기술)")
    # 5. 백호대살 (갑진, 을미, 병술, 정축, 무진, 임술, 계축) - 일주 기준 등이 정확하나 약식으로 포함
    baekho_list = ["갑진", "을미", "병술", "정축", "무진", "임술", "계축"]
    if any(b in full_str for b in baekho_list):
        shinsal.append("백호살(강한 기운/혈광)")
    
    return shinsal

# ==========================================
# 3. MAIN ENGINE: CALCULATE SAJU V4
# ==========================================
def calculate_saju_v3(year, month, day, hour, minute, lat, lon, is_lunar=False):
    """
    [Updated Engine v4.0]
    Returns a RICH DICTIONARY with Korean Ganji, Ten Gods, and Shinsal.
    Compatible with existing app calls but provides better data.
    """
    # 1. Setup Observer
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    
    # Timezone conversion (Korea UTC+9)
    birth_date_kst = datetime(year, month, day, hour, minute)
    birth_date_utc = birth_date_kst - timedelta(hours=9)
    observer.date = birth_date_utc

    # 2. Solar Longitude (24 Solar Terms)
    sun = ephem.Sun(observer)
    sun.compute(observer)
    sun_lon_rad = sun.hlon # Heliocentric longitude is better for terms? No, Geocentric ecliptic.
    # Re-using established ephem logic for safety:
    ecliptic = ephem.Ecliptic(sun)
    sun_lon_deg = math.degrees(ecliptic.lon)
    if sun_lon_deg < 0: sun_lon_deg += 360

    # 3. YEAR PILLAR (Ipchun ~ 315 deg)
    # 입춘(315도) 기준 연주 변경
    if month <= 2 and 270 <= sun_lon_deg < 315:
        saju_year = year - 1
    else:
        saju_year = year
        
    # 1984년 = 갑자년 (Index 0). 1924 = 갑자.
    # 1900년 = 경자 (Index 36).
    year_offset = saju_year - 1924 
    year_idx = year_offset % 60
    year_stem, year_branch = get_ganji_tuple(year_idx)

    # 4. MONTH PILLAR (Solar Terms)
    # 입춘(315)부터 시작. 
    # (SunLon - 315) / 30 -> Month Index (0=인월, 1=묘월...)
    if sun_lon_deg >= 315:
        term_deg = sun_lon_deg - 315
    else:
        term_deg = sun_lon_deg + 45 # (360-315 = 45 offset)
        
    month_idx = int(term_deg // 30) % 12
    # 월간 계산: 년간(Year Stem)에 의해 결정 (진법)
    # 갑기년 -> 병인월 시작 (Index 2)
    # 을경년 -> 무인월 시작 (Index 4)
    # 병신년 -> 경인월 시작 (Index 6)
    # 정임년 -> 임인월 시작 (Index 8)
    # 무계년 -> 갑인월 시작 (Index 0)
    y_stem_idx = CHEONGAN.index(year_stem)
    start_month_stem_idx = (y_stem_idx % 5) * 2 + 2 
    month_stem_idx = (start_month_stem_idx + month_idx) % 10
    month_branch_idx = (2 + month_idx) % 12 # 인(2)부터 시작
    
    month_stem = CHEONGAN[month_stem_idx]
    month_branch = JIJI[month_branch_idx]

    # 5. DAY PILLAR (Julian Day Calculation)
    # Base: 1900-01-01 was Gap-Sul (Index 10). Julian Date approx 2415021.
    # Using python's ordinal for simplicity relative to a known Ganji date.
    # 1901-01-01 was Gregorian. Let's use a closer anchor.
    # 2000-01-01 was Wu-Wu (Muo, Index 54).
    base_date = datetime(2000, 1, 1)
    base_ganji = 54 # Mu-O
    
    delta = birth_date_kst.date() - base_date.date()
    day_idx = (base_ganji + delta.days) % 60
    day_stem, day_branch = get_ganji_tuple(day_idx)

    # 6. TIME PILLAR
    # 시간: 자시(23~01), 축시(01~03)... 
    # 야자시/조자시 구분은 복잡하므로 표준 자시 적용 (23:30 기준 보정은 app.py 좌표로 함)
    # 여기서는 단순 Hour 기준 (진태양시 보정된 시간이 들어온다고 가정)
    # 시간 인덱스: (Hour + 1) // 2
    time_branch_idx = ((hour + 1) // 2) % 12
    
    # 시간 계산: 일간(Day Stem)에 의해 결정
    # 갑기일 -> 갑자시
    # 을경일 -> 병자시
    # 병신일 -> 무자시
    # 정임일 -> 경자시
    # 무계일 -> 임자시
    d_stem_idx = CHEONGAN.index(day_stem)
    start_time_stem_idx = (d_stem_idx % 5) * 2
    time_stem_idx = (start_time_stem_idx + time_branch_idx) % 10
    
    time_stem = CHEONGAN[time_stem_idx]
    time_branch = JIJI[time_branch_idx]

    # ==========================================
    # 7. STRUCTURED DATA GENERATION
    # ==========================================
    
    # Full Strings
    year_pillar = f"{year_stem}{year_branch}"
    month_pillar = f"{month_stem}{month_branch}"
    day_pillar = f"{day_stem}{day_branch}"
    time_pillar = f"{time_stem}{time_branch}"
    full_str_korean = f"{year_pillar} {month_pillar} {day_pillar} {time_pillar}"
    
    # Ten Gods (십성) for each pillar relative to Day Stem
    ten_gods = {
        "Year": calculate_ten_gods(day_stem, year_stem),
        "Month": calculate_ten_gods(day_stem, month_stem),
        "Time": calculate_ten_gods(day_stem, time_stem)
    }
    
    # Shinsal
    shinsal_list = calculate_shinsal(full_str_korean)
    
    # Return Rich Dictionary
    return {
        "Year": year_pillar,
        "Month": month_pillar,
        "Day": day_pillar,
        "Time": time_pillar,
        "Day_Stem": day_stem,
        "Month_Branch": month_branch,
        "Ten_Gods": ten_gods,
        "Shinsal": shinsal_list,
        "Full_String": full_str_korean,
        "Debug_Info": f"SolarLon: {sun_lon_deg:.2f}, MonthIdx: {month_idx}"
    }
