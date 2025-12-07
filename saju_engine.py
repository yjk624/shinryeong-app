import ephem
import math
from datetime import datetime, timedelta

# === CONSTANTS ===
GAN = ["Gap", "Eul", "Byeong", "Jeong", "Mu", "Gi", "Gyeong", "Sin", "Im", "Gye"]
JI = ["Ja", "Chuk", "In", "Myo", "Jin", "Sa", "O", "Mi", "Sin", "Yu", "Sul", "Hae"]

def get_ganji(index):
    return f"{GAN[index % 10]}-{JI[index % 12]}"

def calculate_saju_v3(year, month, day, hour, minute, lat, lon):
    # 1. Setup Observer
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    
    # Timezone conversion (Korea UTC+9)
    birth_date_kst = datetime(year, month, day, hour, minute)
    birth_date_utc = birth_date_kst - timedelta(hours=9)
    observer.date = birth_date_utc

    # 2. Get Sun's GEOCENTRIC Longitude
    sun = ephem.Sun(observer)
    ecliptic_sun = ephem.Ecliptic(sun)
    sun_lon_rad = ecliptic_sun.lon
    sun_lon_deg = math.degrees(sun_lon_rad)
    
    # Normalize to 0-360
    if sun_lon_deg < 0: sun_lon_deg += 360

    # 3. YEAR PILLAR LOGIC
    if month <= 2 and 270 <= sun_lon_deg < 315:
        saju_year = year - 1
    else:
        saju_year = year
        
    year_offset = saju_year - 1924 
    year_ganji_idx = year_offset % 60
    year_pillar = get_ganji(year_ganji_idx)

    # 4. MONTH PILLAR LOGIC
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

    # 5. DAY PILLAR
    base_date = datetime(1900, 1, 1) 
    days_passed = (birth_date_kst - base_date).days
    day_ganji_idx = (10 + days_passed) % 60
    day_pillar = get_ganji(day_ganji_idx)

    # 6. TIME PILLAR
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
        "Solar_Longitude": f"{sun_lon_deg:.2f}°",
        "Date_Debug": birth_date_kst.strftime("%Y-%m-%d")
    }
