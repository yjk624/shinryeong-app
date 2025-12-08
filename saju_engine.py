import ephem
import math
from datetime import datetime, timedelta
from korean_lunar_calendar import KoreanLunarCalendar

# === CONSTANTS ===
GAN = ["Gap (甲)", "Eul (乙)", "Byeong (丙)", "Jeong (丁)", "Mu (戊)", "Gi (己)", "Gyeong (庚)", "Sin (辛)", "Im (壬)", "Gye (癸)"]
JI = ["Ja (子)", "Chuk (丑)", "In (寅)", "Myo (卯)", "Jin (辰)", "Sa (巳)", "O (午)", "Mi (未)", "Sin (申)", "Yu (酉)", "Sul (戌)", "Hae (亥)"]

def get_ganji(index):
    return f"{GAN[index % 10]}-{JI[index % 12]}"

def calculate_saju_v3(year, month, day, hour, minute, lat, lon, is_lunar=False):
    """
    Calculates the Four Pillars (Saju).
    Supports Lunar Date conversion.
    """
    
    # 1. Lunar -> Solar Conversion (if needed)
    if is_lunar:
        calendar = KoreanLunarCalendar()
        # setSolarDate(isLunar, year, month, day) -> returns False if invalid
        try:
            calendar.setLunarDate(year, month, day, False) # False = Not Leap Month for simplicity, or add toggle
            solar_date = calendar.getSolarIsoFormat()
            # Parse back to int
            s_year, s_month, s_day = map(int, solar_date.split('-'))
            process_year, process_month, process_day = s_year, s_month, s_day
        except:
            # Fallback if conversion fails
            process_year, process_month, process_day = year, month, day
    else:
        process_year, process_month, process_day = year, month, day

    # 2. Setup Observer (Astronomy)
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    
    # Korea Standard Time (UTC+9) adjustment
    birth_date_kst = datetime(process_year, process_month, process_day, hour, minute)
    birth_date_utc = birth_date_kst - timedelta(hours=9)
    observer.date = birth_date_utc

    # 3. Get Sun's Longitude (24 Solar Terms)
    sun = ephem.Sun(observer)
    ecliptic_sun = ephem.Ecliptic(sun)
    sun_lon_deg = math.degrees(ecliptic_sun.lon)
    if sun_lon_deg < 0: sun_lon_deg += 360

    # 4. YEAR PILLAR (Based on Ipchun - 315 degrees)
    # If the date is early in the year BUT before Ipchun (approx Feb 4), it belongs to previous year.
    if process_month <= 2 and 270 <= sun_lon_deg < 315:
        saju_year = process_year - 1
    else:
        saju_year = process_year
        
    year_offset = saju_year - 1924 
    year_ganji_idx = year_offset % 60
    year_pillar = get_ganji(year_ganji_idx)

    # 5. MONTH PILLAR (Based on Solar Terms)
    if sun_lon_deg < 315:
        normalized_deg = (sun_lon_deg + 360) - 315
    else:
        normalized_deg = sun_lon_deg - 315
        
    month_idx = int(normalized_deg // 30)
    year_gan_idx = year_ganji_idx % 10
    start_month_gan = (year_gan_idx * 2 + 2) % 10
    month_gan_idx = (start_month_gan + month_idx) % 10
    month_ji_idx = (2 + month_idx) % 12 
    month_pillar = f"{GAN[month_gan_idx]}-{JI[month_ji_idx]}"

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
    time_pillar = f"{GAN[time_gan_idx]}-{JI[time_ji_idx]}"

    return {
        "Year": year_pillar,
        "Month": month_pillar,
        "Day": day_pillar,
        "Time": time_pillar,
        "Is_Lunar_Input": is_lunar,
        "Solar_Date_Used": f"{process_year}-{process_month}-{process_day}"
    }
