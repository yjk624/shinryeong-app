import ephem
import math
from datetime import datetime, timedelta

# ==========================================
# 1. CONSTANTS & MAPPINGS
# ==========================================
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

def get_ganji_tuple(index):
    return (CHEONGAN[index % 10], JIJI[index % 12])

def calculate_ten_gods(day_stem, target_stem):
    """일간(Day)과 타 천간(Target)의 십성 관계 계산"""
    stems_info = {
        '갑': (0, 0), '을': (0, 1), '병': (1, 0), '정': (1, 1),
        '무': (2, 0), '기': (2, 1), '경': (3, 0), '신': (3, 1),
        '임': (4, 0), '계': (4, 1)
    }
    if day_stem not in stems_info or target_stem not in stems_info: return ""
    
    me, me_yin = stems_info[day_stem]
    tgt, tgt_yin = stems_info[target_stem]
    
    diff = (tgt - me) % 5
    same_yin = (me_yin == tgt_yin)
    
    patterns = {
        0: ("비견", "겁재"), 1: ("식신", "상관"), 2: ("편재", "정재"),
        3: ("편관", "정관"), 4: ("편인", "정인")
    }
    return patterns[diff][0] if same_yin else patterns[diff][1]

def calculate_shinsal(full_str):
    shinsal = []
    if any(c in full_str for c in "인신사해"): shinsal.append("역마살(이동/변화)")
    if any(c in full_str for c in "자오묘유"): shinsal.append("도화살(인기/매력)")
    if any(c in full_str for c in "진술축미"): shinsal.append("화개살(예술/고독)")
    if any(c in full_str for c in "갑신묘오"): shinsal.append("현침살(예민/기술)")
    if ("진" in full_str and "해" in full_str) or ("사" in full_str and "술" in full_str):
        shinsal.append("원진살(애증/갈등)")
    return shinsal

def gregorian_to_jd(year, month, day):
    """Astronomical Julian Day Calculation"""
    if month <= 2:
        year -= 1
        month += 12
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    JD = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5
    return JD

def calculate_saju_v3(year, month, day, hour, minute, lat, lon):
    # 1. Observer
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    birth_date_kst = datetime(year, month, day, hour, minute)
    observer.date = birth_date_kst - timedelta(hours=9)

    # 2. Solar Longitude
    sun = ephem.Sun(observer)
    sun.compute(observer)
    sun_lon_deg = math.degrees(ephem.Ecliptic(sun).lon)
    if sun_lon_deg < 0: sun_lon_deg += 360
