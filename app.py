import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import json
import os
import pandas as pd
from korean_lunar_calendar import KoreanLunarCalendar
from geopy.geocoders import Nominatim
from geopy.distance import great_circle

# ==========================================
# 0. CONFIG & STYLE (UI 설정)
# ==========================================
st.set_page_config(page_title="신령: 운명 분석", page_icon="🔮", layout="centered")

st.markdown("""
<style>
    .main-title { font-size: 2.2rem !important; font-weight: 800; color: #4A148C; text-align: center; margin-bottom: 5px; }
    .sub-title { font-size: 1.0rem !important; color: #6D6D6D; text-align: center; margin-bottom: 20px; }
    h3 { font-size: 1.3rem !important; font-weight: 700; color: #311B92; border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 20px; }
    .stAlert { padding: 10px !important; }
</style>
""", unsafe_allow_html=True)

# Initialize State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "family_members" not in st.session_state: st.session_state.family_members = []
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 

# ==========================================
# 1. DATABASE LOADING (ROBUST)
# ==========================================
@st.cache_data
def load_databases():
    """Loads JSON DBs with explicit error handling."""
    db = {
        'identity': {}, 'career': {}, 'love': {}, 'health': {}, 
        'timeline': {}, 'shinsal': {}, 'compatibility': {}, 'matrix': {}
    }
    
    # File mapping (Correct filename vs DB Key)
    file_map = {
        'identity': 'identity_db.json',
        'career': 'career_db.json',
        'love': 'love_db.json',
        'health': 'health_db.json',
        'timeline': 'timeline_db.json',
        'shinsal': 'shinsal_db.json',
        'compatibility': 'compatibility_db.json',
        'matrix': 'five_elements_matrix.json'
    }
    
    for key, filename in file_map.items():
        try:
            with open(f"saju_db/{filename}", "r", encoding='utf-8') as f:
                db[key] = json.load(f)
        except FileNotFoundError:
            # Fallback for missing files to prevent KeyError
            pass 
            
    return db

DB = load_databases()

# API Setup
try:
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    else: client = None
except: client = None
# ==========================================
# 2. LOGIC ENGINE (Advanced)
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "창원": (35.22, 128.68), "광주": (35.15, 126.85),
    "대전": (36.35, 127.38), "울산": (35.53, 129.31), "제주": (33.49, 126.53),
    "seoul": (37.56, 126.97), "busan": (35.17, 129.07)
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
    
    # Identify Strength & Pattern
    dm = raw['Day_Stem']
    e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    my_elem = e_map.get(dm, '수')
    
    # Calculate Element Counts (For Health)
    counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
    for char in raw['Full_String']:
        if char in "갑을인묘": counts['목']+=1
        elif char in "병정사오": counts['화']+=1
        elif char in "무기진술축미": counts['토']+=1
        elif char in "경신신유": counts['금']+=1
        elif char in "임계해자": counts['수']+=1
        
    weakest_elem = min(counts, key=counts.get)
    
    # Strength Calculation
    supporters = {'목':['수','목'], '화':['목','화'], '토':['화','토'], '금':['토','금'], '수':['금','수']}[my_elem]
    season = raw['Month_Branch']
    season_elem = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}.get(season, '토')
    
    score = 50 if season_elem in supporters else -50
    for char in raw['Full_String']:
        ce = '토'
        if char in "갑을인묘": ce='목'
        elif char in "병정사오": ce='화'
        elif char in "경신신유": ce='금'
        elif char in "임계해자": ce='수'
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
        "shinsal": raw['Shinsal'], "season": season,
        "weakest": weakest_elem
    }

def get_timeline_narrative(birth_year, ten_god_pattern="비겁운"):
    current_year = datetime.now().year
    age = current_year - birth_year + 1
    narrative = []
    
    stages = DB['timeline'].get('life_stages_detailed', {})
    impacts = DB['timeline'].get('ten_gods_impact', {})
    
    if age > 15:
        txt = impacts.get('middle_school', {}).get(ten_god_pattern, "평범한 학창시절") 
        narrative.append(f"**[10대 성장기]**: {txt}")
    if age > 20:
        txt = impacts.get('university', {}).get(ten_god_pattern, "자유로운 탐색기")
        narrative.append(f"**[20대 청춘]**: {txt}")
    if age > 30:
        txt = impacts.get('settlement', {}).get(ten_god_pattern, "기반 구축기")
        narrative.append(f"**[30대 정착기]**: {txt}")
        
    return "\n\n".join(narrative)

def generate_report(data):
    if not client: return "AI 연결 불가. 데이터만 확인하세요."
    
    # 1. Identity
    id_data = DB['identity'].get(data['id_key'], {"ko": f"{data['day_stem']} 일간 데이터 없음"})
    
    # 2. Career
    ten_god_key = "편재" 
    career_info = DB['career'].get('ten_gods', {}).get(ten_god_key, {})
    work_style = DB['career'].get('work_style', {}).get(data['strength'], {})
    
    # 3. Love
    love_key = f"{data['my_elem']}_{data['strength']}"
    love_info = DB['love'].get('sexual_style', {}).get(love_key, {})
    
    # 4. Health (CRITICAL FIX: Explicit Mapping)
    weak_e = data['weakest'] 
    health_basic = DB['health'].get('element_diagnosis', {}).get(weak_e, {})
    health_remedy = DB['health'].get('remedy', {}).get(weak_e, {})
    
    health_text = f"약한 오행: {weak_e}, 증상: {health_basic.get('weak_symptom','')}, 추천 음식: {health_remedy.get('food','')}"
    
    # 5. Forecast
    y25 = DB['timeline'].get('yearly_2025_2026', {}).get(data['day_stem'], {}).get('2025', '2025년 운세 데이터 없음')
    y26 = DB['timeline'].get('yearly_2025_2026', {}).get(data['day_stem'], {}).get('2026', '2026년 운세 데이터 없음')
    
    # 6. Advice
    special_advice = "균형을 맞추며 정진하게."
    if data['pattern'] == "재다신약":
        special_advice = DB['career'].get('special_advice', {}).get('재다신약', {}).get('solution', special_advice)

    # Prompt Engineering
    sys_msg = """
    [ROLE] You are 'Shinryeong' (Divine Guru). Tone: Mystical & Authoritative Korean (하게체).
    [RULE] 
    1. KOREAN ONLY. No English output.
    2. DATA-DRIVEN: Use the provided [FACTS] to write the report. Do NOT invent general advice.
    3. FORMAT: Use clear headers with emojis.
    """
    
    user_msg = f"""
    [FACTS TO INTERPRET]
    1. 🐅 본질(Identity): {id_data.get('ko', '')} (Metaphor)
    2. 💪 에너지(Energy): {data['strength']} - {work_style.get('desc', '')}
    3. 💰 직업/재물(Career): {career_info.get('wealth_strategy', '')}
    4. 💖 연애/성향(Love): {love_info.get('desc', '')} - {love_info.get('detail', '')}
    5. 💊 건강(Health): {health_text}
    6. ☁️ 미래(Future): 
       - 2025(을사): {y25}
       - 2026(병오): {y26}
    7. ⚡ 처방(Solution): {special_advice}
    
    [TASK] 위 팩트들을 자연스럽게 연결하여 '신령의 운명 보고서'를 작성하게. 건강 부분은 구체적인 음식과 운동을 꼭 언급하게.
    """
    
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system", "content":sys_msg}, {"role":"user", "content":user_msg}],
            temperature=0.7
        )
        return resp.choices[0].message.content
    except: return "신령이 깊은 명상 중이네. 잠시 후 다시 시도하게."
    # ==========================================
# 3. MAIN UI LAYOUT
# ==========================================
st.markdown('<p class="main-title">🔮 신령(神靈)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">데이터로 보는 나의 운명 (v22.0 Final)</p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["👤 종합 정밀 진단", "💞 궁합 분석", "👨‍👩‍👧‍👦 가족/그룹 분석"])

# --- TAB 1: INDIVIDUAL ---
with tab1:
    with st.expander("📝 사주 정보 입력", expanded=True):
        c1, c2 = st.columns(2)
        # [FIX] Date range explicit 1900-2100
        p_date = c1.date_input("생년월일", value=datetime(1990,1,1), min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        p_time = c1.time_input("태어난 시간", value=time(12,0))
        p_city = c2.text_input("태어난 도시", "서울")
        p_lunar = c2.checkbox("음력", key="p_l")
        p_yoon = c2.checkbox("윤달", disabled=not p_lunar, key="p_y")
        
        if st.button("운명 확인하기", type="primary"):
            res = get_saju_data(p_date, p_time, p_lunar, p_yoon, p_city)
            
            # Retrieve Timeline Data
            timeline_txt = get_timeline_narrative(p_date.year, "식상운") 
            res['timeline_txt'] = timeline_txt
            
            st.session_state.saju_data_dict = res
            st.session_state.final_report = generate_report(res)

    if "final_report" in st.session_state:
        st.divider()
        res = st.session_state.saju_data_dict
        
        k1, k2, k3 = st.columns(3)
        k1.metric("일주 (Identity)", f"{res['day_stem']} (Day)")
        k2.metric("에너지 (Strength)", res['strength'])
        k3.metric("부족한 기운 (Weak)", res['weakest'])
        
        st.markdown(st.session_state.final_report)
        
        # Shinsal Detail Expander
        if res['shinsal']:
            with st.expander("⚡ 발견된 특수 기운 (신살) 상세 보기"):
                for sal in res['shinsal']:
                    s_key = sal.split("(")[0]
                    # [FIX] Safe DB Lookup
                    info = DB['shinsal'].get(s_key, {})
                    if not info and 'basic_shinsal' in DB['shinsal']: 
                         info = DB['shinsal']['basic_shinsal'].get(s_key, {})
                    
                    if info:
                        st.markdown(f"**🔹 {sal}**")
                        st.write(f"- {info.get('desc','')}")
                        st.caption(f"💡 개운법: {info.get('remedy','')}")

# --- TAB 2: COMPATIBILITY ---
with tab2:
    st.markdown('<p class="section-header">💞 궁합 진단</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    # [FIX] Date range applied
    with c1:
        st.info("🅰️ 본인")
        a_date = st.date_input("생일", value=datetime(1990,1,1), key="a_d", min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        a_time = st.time_input("시간", value=time(12,0), key="a_t")
    with c2:
        st.info("🅱️ 상대방")
        b_date = st.date_input("생일", value=datetime(1992,1,1), key="b_d", min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        b_time = st.time_input("시간", value=time(12,0), key="b_t")

    if st.button("궁합 분석 시작"):
        if DB:
            r_a = get_saju_data(a_date, a_time, False, False)
            r_b = get_saju_data(b_date, b_time, False, False)
            
            key = f"{r_a['day_stem']}_{r_b['day_stem']}"
            info = DB['compatibility'].get(key)
            
            st.divider()
            st.subheader(f"{r_a['day_stem']} ❤️ {r_b['day_stem']}")
            
            if info:
                score = info.get('score', 60)
                st.progress(score)
                st.markdown(f"<h3 style='text-align: center; color: #E91E63;'>궁합 점수: {score}점</h3>", unsafe_allow_html=True)
                st.success(f"**관계의 본질:** {info.get('ko_relation', '정보 없음')}")
            else:
                st.warning("데이터베이스에 없는 조합입니다. 기본 오행 궁합으로 분석합니다.")

# --- TAB 3: FAMILY ---
with tab3:
    st.markdown('<p class="section-header">👨‍👩‍👧‍👦 가족/그룹 역학 관계</p>', unsafe_allow_html=True)
    
    with st.form("fam_form"):
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        fn = c1.text_input("이름/호칭")
        # [FIX] Date Range
        fd = c2.date_input("생년월일", min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
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
                e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
                elem = e_map.get(res['day_stem'], '토')
                fam_res.append({'name':m['name'], 'elem':elem, 'stem':res['day_stem'], 'full':res['full_str']})
            
            st.markdown("### 🧬 관계 매트릭스")
            
            order = ['목','화','토','금','수']
            for i in range(len(fam_res)):
                for j in range(i+1, len(fam_res)):
                    p1 = fam_res[i]
                    p2 = fam_res[j]
                    
                    try:
                        i1, i2 = order.index(p1['elem']), order.index(p2['elem'])
                    except: continue 
                    
                    rel_type = "비견 (친구)"
                    desc = "서로 대등한 관계"
                    key = None

                    # Matrix Logic
                    if (i1+1)%5 == i2: 
                        rel_type = f"{p1['elem']}생{p2['elem']} (도움)"
                        key = f"{p1['elem']}_생_{p2['elem']}"
                    elif (i2+1)%5 == i1: 
                        rel_type = f"{p2['elem']}생{p1['elem']} (도움)"
                        key = f"{p2['elem']}_생_{p1['elem']}"
                    elif (i1+2)%5 == i2: 
                        rel_type = f"{p1['elem']}극{p2['elem']} (통제)"
                        key = f"{p1['elem']}_극_{p2['elem']}"
                    elif (i2+2)%5 == i1: 
                        rel_type = f"{p2['elem']}극{p1['elem']} (통제)"
                        key = f"{p2['elem']}_극_{p1['elem']}"
                    
                    if key and key in DB['matrix']:
                         desc = DB['matrix'][key].get('role_parent_child', desc)

                    with st.container():
                        st.info(f"**{p1['name']}** vs **{p2['name']}**: {rel_type}")
                        st.caption(f"💡 {desc}")

            st.markdown("### ⚠️ 2026년(병오년) 키맨 경고")
            risk_found = False
            for m in fam_res:
                if '자' in m['full']:
                    st.error(f"🚨 **{m['name']}**: 자오충(沖) 발생! (이동, 변동, 건강 주의)")
                    risk_found = True
            if not risk_found:
                st.success("2026년에는 가족 중 큰 충돌이 예상되지 않습니다.")

    if st.button("초기화"):
        st.session_state.family_members = []
        st.rerun()
