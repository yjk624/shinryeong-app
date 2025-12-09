import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import json
import pandas as pd
from korean_lunar_calendar import KoreanLunarCalendar
from geopy.geocoders import Nominatim
from geopy.distance import great_circle

# ==========================================
# 0. SYSTEM SETUP (Mobile-Friendly)
# ==========================================
# [FIX] Layout centered for better mobile view
st.set_page_config(page_title="신령: 운명 분석", page_icon="🔮", layout="centered") 

# State Initialization
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "family_members" not in st.session_state: st.session_state.family_members = []
if "saju_cache" not in st.session_state: st.session_state.saju_cache = {} # Cache expensive calc

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v18_mobile", timeout=5)
try:
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    else:
        client = None
except: client = None

# ==========================================
# 1. DATABASE & LOGIC
# ==========================================
@st.cache_data
def load_databases():
    """Loads JSON DBs safely. Returns empty dicts if missing."""
    db = {'identity': {}, 'compatibility': {}, 'matrix': {}, 'shinsal': {}}
    try:
        # Try loading each file individually to prevent total failure
        try: 
            with open("saju_db/identity_db.json", "r", encoding='utf-8') as f: db['identity'] = json.load(f)
        except: pass
        try: 
            with open("saju_db/compatibility_db.json", "r", encoding='utf-8') as f: db['compatibility'] = json.load(f)
        except: pass
        try: 
            with open("saju_db/five_elements_matrix.json", "r", encoding='utf-8') as f: db['matrix'] = json.load(f)
        except: pass
        try: 
            with open("saju_db/shinsal_db.json", "r", encoding='utf-8') as f: db['shinsal'] = json.load(f)
        except: pass
    except Exception as e:
        st.error(f"DB Loading Error: {e}")
    return db

DB = load_databases()

CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "창원": (35.22, 128.68), "광주": (35.15, 126.85),
    "대전": (36.35, 127.38), "울산": (35.53, 129.31), "제주": (33.49, 126.53),
    "seoul": (37.56, 126.97), "busan": (35.17, 129.07)
}

def get_coordinates(city_input):
    clean = city_input.strip().lower()
    if clean in CITY_DB: return CITY_DB[clean]
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude)
    except: pass
    return CITY_DB["서울"] # Fallback

def get_saju_data(dob, tm, is_lunar, is_intercalary, city="서울"):
    """
    Robust Saju Calculator with Caching.
    """
    cache_key = f"{dob}_{tm}_{is_lunar}_{city}"
    if cache_key in st.session_state.saju_cache:
        return st.session_state.saju_cache[cache_key]

    coords = get_coordinates(city)
    final_date = dob
    
    if is_lunar:
        try:
            cal = KoreanLunarCalendar()
            cal.setLunarDate(dob.year, dob.month, dob.day, is_intercalary)
            final_date = datetime(cal.solarYear, cal.solarMonth, cal.solarDay).date()
        except: pass # Fallback to input date if conversion fails

    # Engine Call
    raw = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                          tm.hour, tm.minute, coords[0], coords[1])
    
    # Store essential data
    result = {
        "raw": raw,
        "day_stem": raw['Day_Stem'],
        "month_branch": raw['Month_Branch'],
        "day_pillar": raw['Day'],
        "full_str": raw['Full_String'],
        "shinsal": raw['Shinsal'],
        "id_key": f"{raw['Day_Stem']}_{raw['Month_Branch']}"
    }
    
    st.session_state.saju_cache[cache_key] = result
    return result

def get_fallback_relation(stem1, stem2):
    """
    Generates a relation string mathematically if DB lookup fails.
    """
    elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    e1 = elem_map.get(stem1, '토')
    e2 = elem_map.get(stem2, '토')
    
    relations = ['목','화','토','금','수']
    idx1 = relations.index(e1)
    idx2 = relations.index(e2)
    
    if (idx1 + 1) % 5 == idx2: return f"{stem1}({e1})이 {stem2}({e2})을 생해주는(돕는) 관계입니다.", 80
    if (idx2 + 1) % 5 == idx1: return f"{stem2}({e2})이 {stem1}({e1})을 생해주는(돕는) 관계입니다.", 85
    if (idx1 + 2) % 5 == idx2: return f"{stem1}({e1})이 {stem2}({e2})을 극하는(이기는) 관계입니다.", 50
    if (idx2 + 2) % 5 == idx1: return f"{stem2}({e2})이 {stem1}({e1})을 극하는(이기는) 관계입니다.", 50
    if e1 == e2: return "같은 오행으로 친구 같은 관계입니다.", 70
    return "서로 무난한 관계입니다.", 60

# ==========================================
# 2. UI HEADER & SIDEBAR
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정 (Settings)")
    
    # Language Toggle
    lang_mode = st.radio("언어 (Language)", ["한국어", "English"], index=0 if st.session_state.lang=="ko" else 1)
    st.session_state.lang = "ko" if lang_mode == "한국어" else "en"
    
    if st.button("🗑️ 상담 기록 초기화 (Reset)"):
        st.session_state.clear()
        st.rerun()

st.title("🔮 신령(神靈)")
st.caption("AI Based Destiny Analysis v18.0")

# ==========================================
# 3. TABS (MAIN FEATURES)
# ==========================================
tab1, tab2, tab3 = st.tabs(["👤 개인", "💞 궁합", "👨‍👩‍👧‍👦 가족"])

# --- TAB 1: PERSONAL ---
with tab1:
    with st.expander("📝 사주 정보 입력", expanded=True):
        c1, c2 = st.columns(2)
        # [FIX] Date range extended 1900-2100
        p_date = c1.date_input("생년월일", value=datetime(1990,1,1), 
                             min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        p_time = c1.time_input("태어난 시간", value=time(12,0))
        p_city = c2.text_input("태어난 도시 (예: 서울)", "서울")
        p_lunar = c2.checkbox("음력", key="p_lunar")
        p_yoon = c2.checkbox("윤달", disabled=not p_lunar, key="p_yoon")
        
        if st.button("분석 시작", type="primary"):
            res = get_saju_data(p_date, p_time, p_lunar, p_yoon, p_city)
            st.session_state.p_result = res

    if "p_result" in st.session_state:
        res = st.session_state.p_result
        
        st.divider()
        st.markdown(f"### 📜 **{res['day_stem']}**일간의 운명")
        st.caption(f"사주 구성: {res['full_str']}")
        
        # 1. Identity (DB Lookup)
        id_data = DB['identity'].get(res['id_key'])
        if id_data:
            desc = id_data['ko'] if st.session_state.lang == 'ko' else id_data['en']
            st.success(f"🐅 **타고난 기질:** {desc}")
        else:
            st.info(f"🐅 **타고난 기질:** {res['day_stem']}의 기운을 타고났으며, {res['month_branch']}월의 환경 속에 있습니다.")

        # 2. Shinsal (DB Lookup)
        if res['shinsal']:
            st.markdown("#### ⚡ 신령의 처방 (Special Stars)")
            for sal in res['shinsal']:
                # Extract clean name (e.g. "역마살(이동)" -> "역마살")
                sal_key = sal.split("(")[0] 
                
                # Check mapping
                db_info = DB['shinsal'].get(sal_key)
                
                # Fallback check for keys in DB
                if not db_info:
                    for k in DB['shinsal'].keys():
                        if k in sal:
                            db_info = DB['shinsal'][k]
                            break
                            
                if db_info:
                    with st.container():
                        st.write(f"**🔹 {sal}**")
                        st.caption(f"💡 {db_info['desc']}")
                        st.info(f"🛡️ **개운법:** {db_info['remedy']}")
        else:
            st.info("평온한 사주입니다. 특별한 흉살이 없습니다.")

# --- TAB 2: COMPATIBILITY ---
with tab2:
    st.info("두 사람의 생년월일을 입력하세요.")
    c1, c2 = st.columns(2)
    with c1:
        st.write("🅰️ 본인")
        a_date = st.date_input("생일", value=datetime(1990,1,1), key="a_d", min_value=datetime(1900,1,1))
        a_time = st.time_input("시간", value=time(12,0), key="a_t")
    with c2:
        st.write("🅱️ 상대방")
        b_date = st.date_input("생일", value=datetime(1992,1,1), key="b_d", min_value=datetime(1900,1,1))
        b_time = st.time_input("시간", value=time(12,0), key="b_t")
        
    if st.button("궁합 보기"):
        r_a = get_saju_data(a_date, a_time, False, False)
        r_b = get_saju_data(b_date, b_time, False, False)
        
        key = f"{r_a['day_stem']}_{r_b['day_stem']}"
        
        # [FIX] Safe DB Lookup with Fallback
        comp_data = DB['compatibility'].get(key)
        
        st.divider()
        st.subheader(f"{r_a['day_stem']} ❤️ {r_b['day_stem']}")
        
        if comp_data:
            txt = comp_data['ko_relation'] if st.session_state.lang == 'ko' else comp_data['en_relation']
            score = comp_data.get('score', 50)
            st.progress(score)
            st.write(f"**궁합 점수: {score}점**")
            st.success(txt)
        else:
            # Fallback Logic (Error Prevention)
            txt, score = get_fallback_relation(r_a['day_stem'], r_b['day_stem'])
            st.progress(score)
            st.warning(f"{txt} (DB 데이터 없음 - 자동 분석)")

# --- TAB 3: FAMILY ---
with tab3:
    st.markdown("### 👨‍👩‍👧‍👦 가족 구성원 입력")
    
    # [FIX] Added Time and City for precision
    with st.expander("구성원 추가", expanded=True):
        c1, c2 = st.columns(2)
        f_name = c1.text_input("이름 (예: 아빠)")
        f_date = c2.date_input("생년월일", key="f_d", min_value=datetime(1900,1,1))
        c3, c4 = st.columns(2)
        f_time = c3.time_input("시간", key="f_t")
        f_city = c4.text_input("출생지", "서울", key="f_c")
        
        if st.button("가족 추가"):
            if f_name:
                st.session_state.family_members.append({
                    "name": f_name, "date": f_date, "time": f_time, "city": f_city
                })
                st.success(f"{f_name} 추가됨")
                st.rerun()

    if st.session_state.family_members:
        st.write("---")
        st.write("📋 분석 대상:")
        # Simple dataframe display
        df = pd.DataFrame(st.session_state.family_members)
        st.dataframe(df[['name', 'date', 'city']], use_container_width=True)
        
        if st.button("가족 관계 분석"):
            fam_data = []
            for m in st.session_state.family_members:
                res = get_saju_data(m['date'], m['time'], False, False, m['city'])
                # Get element from mapping (Simple)
                e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
                elem = e_map.get(res['day_stem'], '토')
                fam_data.append({'name': m['name'], 'stem': res['day_stem'], 'elem': elem, 'full': res['full_str']})
            
            st.subheader("1. 가족 오행 관계도")
            
            # Matrix Logic
            order = ['목', '화', '토', '금', '수']
            for i in range(len(fam_data)):
                for j in range(i+1, len(fam_data)):
                    p1, p2 = fam_data[i], fam_data[j]
                    idx1, idx2 = order.index(p1['elem']), order.index(p2['elem'])
                    
                    rel_key = None
                    # Generate keys like "목_생_화"
                    if (idx1 + 1) % 5 == idx2: rel_key = f"{p1['elem']}_생_{p2['elem']}"
                    elif (idx2 + 1) % 5 == idx1: rel_key = f"{p2['elem']}_생_{p1['elem']}"
                    elif (idx1 + 2) % 5 == idx2: rel_key = f"{p1['elem']}_극_{p2['elem']}"
                    elif (idx2 + 2) % 5 == idx1: rel_key = f"{p2['elem']}_극_{p1['elem']}"
                    
                    if rel_key and rel_key in DB['matrix']:
                        desc = DB['matrix'][rel_key]['role_parent_child']
                        st.info(f"**{p1['name']}({p1['elem']}) ↔ {p2['name']}({p2['elem']})**")
                        st.caption(desc)
                    else:
                        st.write(f"🔹 **{p1['name']} & {p2['name']}**: {p1['elem']}와 {p2['elem']}의 관계")

            st.subheader("2. 2026년(병오년) 위험 신호")
            found_risk = False
            for m in fam_data:
                # Rat(자) in chart clashes with Horse(오) year
                if '자' in m['full']:
                    st.error(f"⚠️ **{m['name']}**: 자오충(沖) 발생! (이동, 변동, 건강 주의)")
                    found_risk = True
            if not found_risk:
                st.success("2026년 큰 충돌 없음.")

    if st.button("목록 초기화"):
        st.session_state.family_members = []
        st.rerun()
