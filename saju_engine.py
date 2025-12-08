import ephem
import math
from datetime import datetime, timedelta
from korean_lunar_calendar import KoreanLunarCalendar

# === CONSTANTS (KOREAN VER.) ===
# Changed from "Gap (甲)" to "갑(甲)" for native readability
GAN = ["갑(甲)", "을(乙)", "병(丙)", "정(丁)", "무(戊)", "기(己)", "경(庚)", "신(辛)", "임(壬)", "계(癸)"]
JI = ["자(子)", "축(丑)", "인(寅)", "묘(卯)", "진(辰)", "사(巳)", "오(午)", "미(未)", "신(申)", "유(酉)", "술(戌)", "해(亥)"]

def get_ganji(index):
    return f"{GAN[index % 10]}{JI[index % 12]}"

def calculate_saju_v3(year, month, day, hour, minute, lat, lon, is_lunar=False):
    """
    Calculates the Four Pillars (Saju) with Lunar conversion support.
    """
    
    # 1. Lunar -> Solar Conversion
    if is_lunar:
        calendar = KoreanLunarCalendar()
        try:
            calendar.setLunarDate(year, month, day, False) 
            solar_date = calendar.getSolarIsoFormat()
            s_year, s_month, s_day = map(int, solar_date.split('-'))
            process_year, process_month, process_day = s_year, s_month, s_day
        except:
            process_year, process_month, process_day = year, month, day
    else:
        process_year, process_month, process_day = year, month, day

    # 2. Setup Observer
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    
    # KST Adjustment
    birth_date_kst = datetime(process_year, process_month, process_day, hour, minute)
    birth_date_utc = birth_date_kst - timedelta(hours=9)
    observer.date = birth_date_utc

    # 3. Sun Longitude
    sun = ephem.Sun(observer)
    ecliptic_sun = ephem.Ecliptic(sun)
    sun_lon_deg = math.degrees(ecliptic_sun.lon)
    if sun_lon_deg < 0: sun_lon_deg += 360

    # 4. YEAR PILLAR
    if process_month <= 2 and 270 <= sun_lon_deg < 315:
        saju_year = process_year - 1
    else:
        saju_year = process_year
        
    year_offset = saju_year - 1924 
    year_ganji_idx = year_offset % 60
    year_pillar = get_ganji(year_ganji_idx)

    # 5. MONTH PILLAR
    if sun_lon_deg < 315:
        normalized_deg = (sun_lon_deg + 360) - 315
    else:
        normalized_deg = sun_lon_deg - 315
        
    month_idx = int(normalized_deg // 30)
    year_gan_idx = year_ganji_idx % 10
    start_month_gan = (year_gan_idx * 2 + 2) % 10
    month_gan_idx = (start_month_gan + month_idx) % 10
    month_ji_idx = (2 + month_idx) % 12 
    month_pillar = f"{GAN[month_gan_idx]}{JI[month_ji_idx]}"

    # 6. DAY PILLAR
    base_date = datetime(1900, 1, 1) 
    days_passed = (birth_date_kst - base_date).days
    day_ganji_idx = (10 + days_passed) % 60
    day_pillar = get_ganji(day_ganji_idx)

    # 7. TIME PILLAR
    time_idx = ((hour + 1) % 24) // 2
    day_gan_idx = day_ganji_idx % 10
    start_time_gan = (day_gan_idx * 2) % 10
    time_gan_idx = (start_time_gan + time_idx) % 10
    time_ji_idx = time_idx 
    time_pillar = f"{GAN[time_gan_idx]}{JI[time_ji_idx]}"

    return {
        "Year": year_pillar,
        "Month": month_pillar,
        "Day": day_pillar,
        "Time": time_pillar,
    }
