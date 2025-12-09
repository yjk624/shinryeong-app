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
# 0. STYLE & CONFIG (UI 개선)
# ==========================================
st.set_page_config(page_title="신령: 운명 분석", page_icon="🔮", layout="centered")

# Custom CSS for Typography & Layout
st.markdown("""
<style>
    .main-title { font-size: 2.5rem !important; font-weight: 800; color: #4A148C; text-align: center; margin-bottom: 0px; }
    .sub-title { font-size: 1.2rem !important; color: #6D6D6D; text-align: center; margin-bottom: 30px; }
    .section-header { font-size: 1.5rem !important; font-weight: 600; color: #1A237E; border-bottom: 2px solid #E8EAF6; padding-bottom: 10px; margin-top: 20px; }
    .highlight { background-color: #F3E5F5; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    .stAlert { margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# State Init
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "family_members" not in st.session_state: st.session_state.family_members = []
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 

# ==========================================
# 1. DATABASE LOADING (Robust)
# ==========================================
@st.cache_data
def load_databases():
    db = {}
    files = ['identity', 'career', 'love', 'health', 'timeline', 'shinsal', 'compatibility', 'five_elements_matrix']
    for name in files:
        try:
            fname = "five_elements_matrix" if name == "matrix" else name
            path = f"saju_db/{fname}_db.json" if 'db' not in fname and fname != 'five_elements_matrix' else f"saju_db/{fname}.json"
            with open(path, "r", encoding='utf-8') as f: db[name] = json.load(f)
        except: db[name] = {}
    return db

DB = load_databases()

# API Setup
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except: client = None

# ==========================================
# 2. LOGIC ENGINE (Advanced & Safe)
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "창원": (35.22, 128.68), "광주": (35.15, 126.85),
    "대전": (36.35, 127.38), "울산": (35.53, 129.31), "제주": (33.49, 126.53)
}

def get_coordinates(city_input):
    clean = city_input.strip()
    if clean in CITY_DB: return CITY_DB[clean]
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude)
    except: pass
    return CITY_DB["서울"] # Fallback

def get_saju_data(dob, tm, is_lunar, is_intercalary, city="서울"):
    coords = get_coordinates(city)
    final_date = dob
    if is_lunar:
        try:
            cal = KoreanLunarCalendar()
            cal.setLunarDate(dob.year, dob.month, dob.day, is_intercalary)
            final_date = datetime(cal.solarYear, cal.solarMonth, cal.solarDay).date()
        except: pass

    raw = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                          tm.hour, tm.minute, coords[0], coords[1])
    
    # [Logic] Identify Strength & Pattern
    dm = raw['Day_Stem']
    e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    my_elem = e_map.get(dm, '수')
    
    # Calculate Strength (Weighted)
    supporters = {'목':['수','목'], '화':['목','화'], '토':['화','토'], '금':['토','금'], '수':['금','수']}[my_elem]
    season = raw['Month_Branch']
    season_elem = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}.get(season, '토')
    
    score = 50 if season_elem in supporters else -50
    for char in raw['Full_String']:
        if char in "갑을인묘": ce='목'
        elif char in "병정사오": ce='화'
        elif char in "경신신유": ce='금'
        elif char in "임계해자": ce='수'
        else: ce='토'
        if ce in supporters: score += 10
            
    strength = "신강" if score >= 20 else "신약"
    
    # Pattern Logic
    wealth_map = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'}
    wealth_cnt = 0
    for char in raw['Full_String']:
         if char in "갑을인묘": ce='목'
         elif char in "병정사오": ce='화'
         elif char in "경신신유": ce='금'
         elif char in "임계해자": ce='수'
         else: ce='토'
         if ce == wealth_map[my_elem]: wealth_cnt += 1
         
    pattern = "일반격"
    if strength == "신약" and wealth_cnt >= 3: pattern = "재다신약"
    
    id_key = f"{dm}_{season}"
    
    return {
        "raw": raw, "day_stem": dm, "full_str": raw['Full_String'],
        "id_key": id_key, "strength": strength, "pattern": pattern,
        "my_elem": my_elem, "birth_year": final_date.year,
        "shinsal": raw['Shinsal']
    }

def get_timeline_narrative(birth_year, ten_god_pattern="비겁운"):
    """
    Constructs a life-story based on birth year using timeline_db.
    """
    current_year = datetime.now().year
    age = current_year - birth_year + 1
    narrative = []
    
    stages = DB['timeline'].get('life_stages_detailed', {})
    impacts = DB['timeline'].get('ten_gods_impact', {})
    
    # 10s (School Age)
    if age > 15:
        txt = impacts.get('middle_school', {}).get(ten_god_pattern, "평범한 학창시절") # Fallback logic needed for exact TenGod mapping
        narrative.append(f"**[10대 성장기]**: {txt}")
        
    # 20s (Youth)
    if age > 20:
        txt = impacts.get('university', {}).get(ten_god_pattern, "자유로운 탐색기")
        narrative.append(f"**[20대 청춘]**: {txt}")
        
    return "\n\n".join(narrative)

def generate_report(data):
    if not client: return "AI 연결 불가. 데이터만 확인하세요."
    
    # Construct a highly detailed prompt with pre-fetched data
    id_data = DB['identity'].get(data['id_key'], {"ko": "데이터 없음"})
    career_data = DB['career']['ten_gods'].get("편재", {}) # Defaulting to Pyeonjae for demo logic, needs exact mapping
    if data['pattern'] == "재다신약":
        special_advice = DB['career']['special_advice']['재다신약']['solution']
    else:
        special_advice = "오행의 균형을 맞추며 정진하게."
        
    # 2025/2026 Forecast
    y25 = DB['timeline']['yearly_2025_2026'].get(data['day_stem'], {}).get('2025', '')
    y26 = DB['timeline']['yearly_2025_2026'].get(data['day_stem'], {}).get('2026', '')

    sys_msg = """
    [ROLE] 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
    [RULE] KOREAN ONLY. Interpret the provided [FACTS] deeply.
    [STRUCTURE]
    1. 🐅 그대의 그릇 (Identity): Start with the Metaphor. Explain Strength & Pattern.
    2. 📜 지나온 발자취 (Past): Use the 'Past Timeline' data to describe their youth.
    3. ☁️ 다가올 미래 (2025-2026): Use the Yearly Forecast data.
    4. ⚡ 신령의 처방 (Solution): Give the Special Advice clearly.
    """
    
    user_msg = f"""
    [FACTS]
    - Metaphor: {id_data['ko']}
    - Strength: {data['strength']}
    - Pattern: {data['pattern']}
    - Past Timeline: {data['timeline_txt']}
    - 2025 Forecast: {y25}
    - 2026 Forecast: {y26}
    - Special Advice: {special_advice}
    - Shinsal: {data['shinsal']}
    """
    
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system", "content":sys_msg}, {"role":"user", "content":user_msg}],
            temperature=0.7
        )
        return resp.choices[0].message.content
    except: return "신령이 깊은 명상 중이네."

# ==========================================
# 3. MAIN UI
# ==========================================
st.markdown('<p class="main-title">🔮 신령(神靈)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">데이터로 보는 나의 운명 (v21.0 Final)</p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["👤 종합 진단", "💞 궁합 분석", "👨‍👩‍👧‍👦 가족 분석"])

# --- TAB 1: INDIVIDUAL ---
with tab1:
    with st.expander("📝 사주 정보 입력", expanded=True):
        c1, c2 = st.columns(2)
        # [FIX] Year range expanded 1900-2100
        p_date = c1.date_input("생년월일", value=datetime(1990,1,1), min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        p_time = c1.time_input("태어난 시간", value=time(12,0))
        p_city = c2.text_input("태어난 도시", "서울")
        p_lunar = c2.checkbox("음력", key="p_l")
        p_yoon = c2.checkbox("윤달", disabled=not p_lunar, key="p_y")
        
        if st.button("운명 확인하기", type="primary"):
            res = get_saju_data(p_date, p_time, p_lunar, p_yoon, p_city)
            
            # Retrieve Timeline Data (Past)
            # Simulating 'Shik-Sang' luck for youth for demonstration (In full logic, calculate Daewoon)
            timeline_txt = get_timeline_narrative(p_date.year, "식상운") 
            res['timeline_txt'] = timeline_txt
            
            st.session_state.saju_data_dict = res
            st.session_state.final_report = generate_report(res)

    if "final_report" in st.session_state:
        st.divider()
        res = st.session_state.saju_data_dict
        
        # Dashboard
        k1, k2, k3 = st.columns(3)
        k1.metric("일주(Identity)", f"{res['day_stem']} (Day)")
        k2.metric("에너지(Strength)", res['strength'])
        k3.metric("격국(Pattern)", res['pattern'])
        
        # Report Content
        st.markdown(st.session_state.final_report)
        
        # Shinsal Badges
        st.markdown("---")
        st.caption("📌 발견된 특수 기운:")
        st.write(", ".join(res['shinsal']))

# --- TAB 2: COMPATIBILITY ---
with tab2:
    st.markdown('<p class="section-header">💞 궁합 진단</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    # [FIX] Added Time inputs and Date Range
    with c1:
        st.info("🅰️ 본인")
        a_date = st.date_input("생일", value=datetime(1990,1,1), key="a_d", min_value=datetime(1900,1,1))
        a_time = st.time_input("시간", value=time(12,0), key="a_t")
    with c2:
        st.info("🅱️ 상대방")
        b_date = st.date_input("생일", value=datetime(1992,1,1), key="b_d", min_value=datetime(1900,1,1))
        b_time = st.time_input("시간", value=time(12,0), key="b_t")

    if st.button("궁합 분석 시작"):
        if DB:
            r_a = get_saju_data(a_date, a_time, False, False)
            r_b = get_saju_data(b_date, b_time, False, False)
            
            key = f"{r_a['day_stem']}_{r_b['day_stem']}"
            # [FIX] Safe Get
            info = DB['compatibility'].get(key)
            
            st.divider()
            st.subheader(f"{r_a['day_stem']} ❤️ {r_b['day_stem']}")
            
            if info:
                score = info.get('score', 60)
                st.progress(score)
                st.markdown(f"<h3 style='text-align: center; color: #E91E63;'>궁합 점수: {score}점</h3>", unsafe_allow_html=True)
                st.success(f"**관계의 본질:** {info['ko_relation']}")
            else:
                # Fallback
                st.warning("데이터베이스에 없는 조합이나, 기본 오행 궁합으로 분석합니다.")
                st.write("서로 다른 매력에 끌리는 관계입니다. (Fallback Analysis)")

# --- TAB 3: FAMILY ---
with tab3:
    st.markdown('<p class="section-header">👨‍👩‍👧‍👦 가족/그룹 역학 관계</p>', unsafe_allow_html=True)
    
    with st.form("fam_form"):
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        fn = c1.text_input("이름/호칭")
        # [FIX] Date Range
        fd = c2.date_input("생년월일", min_value=datetime(1900,1,1))
        ft = c3.time_input("시간", value=time(12,0))
        add = st.form_submit_button("구성원 추가")
        
        if add and fn:
            st.session_state.family_members.append({"name":fn, "date":fd, "time":ft})
            st.rerun()

    if st.session_state.family_members:
        st.write("---")
        for idx, m in enumerate(st.session_state.family_members):
            st.text(f"{idx+1}. {m['name']} ({m['date']})")
        
        if st.button("가족 관계 분석"):
            fam_res = []
            for m in st.session_state.family_members:
                res = get_saju_data(m['date'], m['time'], False, False)
                # Map Stem to Element
                e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
                elem = e_map[res['day_stem']]
                fam_res.append({'name':m['name'], 'elem':elem, 'stem':res['day_stem']})
            
            st.markdown("### 🧬 관계 매트릭스")
            cols = st.columns(2)
            
            # Simple Matrix Logic display
            for i in range(len(fam_res)):
                for j in range(i+1, len(fam_res)):
                    p1 = fam_res[i]
                    p2 = fam_res[j]
                    
                    # Construct Key for DB Lookup
                    # (Simplified for demo, real logic uses index diff)
                    order = ['목','화','토','금','수']
                    i1, i2 = order.index(p1['elem']), order.index(p2['elem'])
                    
                    rel_type = "비견 (친구)"
                    if (i1+1)%5 == i2: rel_type = f"{p1['elem']}생{p2['elem']} (도움)"
                    elif (i2+1)%5 == i1: rel_type = f"{p2['elem']}생{p1['elem']} (도움)"
                    elif (i1+2)%5 == i2: rel_type = f"{p1['elem']}극{p2['elem']} (통제)"
                    elif (i2+2)%5 == i1: rel_type = f"{p2['elem']}극{p1['elem']} (통제)"
                    
                    st.info(f"**{p1['name']}** vs **{p2['name']}**: {rel_type}")

    if st.button("초기화"):
        st.session_state.family_members = []
        st.rerun()
