import ephem
import math
from datetime import datetime, timedelta, date

# ==========================================
# 1. CONSTANTS
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
    # 김용준 사주(오-오 자형)
    if full_str.count("오") >= 2: shinsal.append("자형살(스스로 볶는 스트레스)")
    return shinsal

def calculate_saju_v3(year, month, day, hour, minute, lat, lon):
    """
    [v6.0 Engine] Uses Python's reliable date ordinal for Day Pillar.
    """
    # 1. Observer Setup (For Solar Terms/Month)
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

    # 3. YEAR PILLAR
    saju_year = year - 1 if (month <= 2 and 270 <= sun_lon_deg < 315) else year
    year_ganji_idx = (saju_year - 1924) % 60
    year_stem, year_branch = get_ganji_tuple(year_ganji_idx)

    # 4. MONTH PILLAR
    term_deg = (sun_lon_deg - 315) if sun_lon_deg >= 315 else (sun_lon_deg + 45)
    month_idx = int(term_deg // 30) % 12
    y_stem_idx = CHEONGAN.index(year_stem)
    m_stem_idx = ((y_stem_idx % 5) * 2 + 2 + month_idx) % 10
    month_stem, month_branch = CHEONGAN[m_stem_idx], JIJI[(2 + month_idx) % 12]

    # 5. DAY PILLAR (The Anchor Method)
    # 1924-01-01 was Gap-Ja (Index 0)
    base_date = date(1924, 1, 1)
    target_date = date(year, month, day)
    delta_days = (target_date - base_date).days
    day_ganji_idx = delta_days % 60
    day_stem, day_branch = get_ganji_tuple(day_ganji_idx)

    # 6. TIME PILLAR
    time_idx = ((hour + 1) // 2) % 12
    d_stem_idx = CHEONGAN.index(day_stem)
    t_stem_idx = ((d_stem_idx % 5) * 2 + time_idx) % 10
    time_stem, time_branch = CHEONGAN[t_stem_idx], JIJI[time_idx]

    full_str = f"{year_stem}{year_branch} {month_stem}{month_branch} {day_stem}{day_branch} {time_stem}{time_branch}"
    
    return {
        "Year": f"{year_stem}{year_branch}", "Month": f"{month_stem}{month_branch}",
        "Day": f"{day_stem}{day_branch}", "Time": f"{time_stem}{time_branch}",
        "Day_Stem": day_stem, "Month_Branch": month_branch,
        "Full_String": full_str,
        "Ten_Gods": {
            "Year": calculate_ten_gods(day_stem, year_stem),
            "Month": calculate_ten_gods(day_stem, month_stem),
            "Time": calculate_ten_gods(day_stem, time_stem)
        },
        "Shinsal": calculate_shinsal(full_str)
    }
