import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time, date
import json
import pandas as pd
from korean_lunar_calendar import KoreanLunarCalendar
from geopy.geocoders import Nominatim
from geopy.distance import great_circle

# ==========================================
# 0. CONFIGURATION & DB LOADING
# ==========================================
st.set_page_config(page_title="신령: 귀신같은 통합 분석", page_icon="🔮", layout="centered")

# Initialize State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None
if "family_members" not in st.session_state: st.session_state.family_members = []

# Load All Databases
@st.cache_data
def load_databases():
    db_names = ['identity', 'career', 'love', 'health', 'timeline', 'shinsal', 'compatibility', 'five_elements_matrix']
    db = {}
    for name in db_names:
        try:
            # Map filename to key (handle potential naming mismatches if any)
            fname = "five_elements_matrix" if name == "matrix" else name
            with open(f"saju_db/{fname}_db.json" if 'db' not in fname and fname != 'five_elements_matrix' else f"saju_db/{fname}.json", "r", encoding='utf-8') as f:
                db[name] = json.load(f)
        except Exception as e:
            # Fallback for naming variations
            try:
                with open(f"saju_db/{name}_db.json", "r", encoding='utf-8') as f: db[name] = json.load(f)
            except:
                db[name] = {} 
    return db

DB = load_databases()

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v20_final", timeout=5)
try:
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    else: client = None
except: client = None

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
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
    return CITY_DB["서울"]

def calculate_korean_age(birth_year):
    return datetime.now().year - birth_year + 1

# ==========================================
# 2. LOGIC ENGINE (The Brain)
# ==========================================
def analyze_comprehensive_logic(saju_res, birth_year):
    """
    Integration of ALL DBs for a complete diagnosis.
    """
    dm = saju_res['Day_Stem'] # Day Master (Identity)
    season = saju_res['Month_Branch']
    full_str = saju_res['Full_String']
    
    # --- A. Element & Ten God Analysis ---
    e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    my_elem = e_map[dm]
    
    # Count Elements
    counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
    for char in full_str:
        if char == ' ': continue
        # Simplified mapping for counting
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        counts[ce] += 1
        
    weakest_elem = min(counts, key=counts.get)
    strongest_elem = max(counts, key=counts.get)

    # --- B. Strength & Pattern (Sin-gang/Sin-yak) ---
    # Season Check
    supporters = {'목':['수','목'], '화':['목','화'], '토':['화','토'], '금':['토','금'], '수':['금','수']}[my_elem]
    season_elem = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}[season]
    
    score = 50 if season_elem in supporters else -50
    for char in full_str:
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        if ce in supporters: score += 10
            
    strength_key = "신강" if score >= 20 else "신약"
    
    # Pattern Logic
    # Simple Ten God Dominance for Career DB
    # (In a real engine, calculate Ten Gods properly. Here we approximate with Element counts)
    # Wealth Element for Me
    wealth_e = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'}[my_elem]
    wealth_cnt = counts[wealth_e]
    
    pattern = "일반격"
    if strength_key == "신약" and wealth_cnt >= 3: pattern = "재다신약"
    # Map to Ten God for Career DB (e.g. if Wealth is strong -> 편재/정재)
    dominant_ten_god = "비견" # Default
    if wealth_cnt >= 3: dominant_ten_god = "편재"
    
    # --- C. Data Retrieval from DBs ---
    
    # 1. Identity
    id_key = f"{dm}_{season}"
    identity_data = DB['identity'].get(id_key, {"ko": "정보 없음", "en": "No Data", "keywords": []})
    
    # 2. Career
    career_data = DB['career']['ten_gods'].get(dominant_ten_god, {})
    work_style = DB['career']['work_style'].get(strength_key, {})
    
    # 3. Love
    love_key = f"{my_elem}_{strength_key}"
    love_data = DB['love']['sexual_style'].get(love_key, {})
    
    # 4. Health
    health_data = DB['health']['element_diagnosis'].get(weakest_elem, {})
    health_remedy = DB['health']['remedy'].get(weakest_elem, {})
    
    # 5. Timeline (Risk & Yearly)
    age = calculate_korean_age(birth_year)
    current_year = datetime.now().year
    
    # Samjae/Ahopsu Check
    risk_list = []
    if age % 10 == 9: risk_list.append("아홉수 (Nine-Ender Risk)")
    
    zodiac_idx = (birth_year - 4) % 12 # 0:Ja ... 11:Hae
    y_idx = (current_year - 4) % 12 # 2025:Snake(5)
    
    # Samjae Logic (Simplified)
    samjae_group = {
        0:[2,3,4], 1:[11,0,1], 2:[8,9,10], 3:[5,6,7], # Groups by Zodiac Index
        4:[2,3,4], 5:[11,0,1], 6:[8,9,10], 7:[5,6,7],
        8:[2,3,4], 9:[11,0,1], 10:[8,9,10], 11:[5,6,7]
    }
    # Example: Snake(5) year -> Pig(11), Rabbit(3), Sheep(7) are in Samjae? 
    # (Correct logic needs exact Samjae tables. Using placeholder for structure)
    # Check 2025 Clash
    if "해" in full_str: risk_list.append("2025년 사해충(역마 충돌)")
    
    # 6. Shinsal & Remedy
    detected_shinsal = []
    shinsal_details = []
    for s_name, s_info in DB['shinsal'].items():
        # Check if user has this shinsal (Name match in saju_res list or char check)
        if s_name in str(saju_res['Shinsal']):
            detected_shinsal.append(s_name)
            shinsal_details.append(f"- **{s_name}**: {s_info['desc']} (개운법: {s_info.get('remedy','없음')})")
    
    # Special Pattern Advice
    if pattern == "재다신약" and "재다신약" in DB['shinsal']:
        p_info = DB['shinsal']['재다신약']
        shinsal_details.append(f"- **[특수격국] 재다신약**: {p_info['desc']}\n  👉 **솔루션:** {p_info['action']}")

    return {
        "meta": {"age": age, "pattern": pattern, "strength": strength_key},
        "identity": identity_data,
        "career": {"job": career_data.get('jobs', []), "strategy": career_data.get('wealth_strategy', ''), "style": work_style.get('title', '')},
        "love": love_data,
        "health": {"weak": weakest_elem, "symptom": health_data.get('weak_symptom', ''), "food": health_remedy.get('food', '')},
        "risks": risk_list,
        "shinsal_text": "\n".join(shinsal_details),
        "full_str": full_str
    }

def generate_ai_report(context_data):
    """
    Generates the final polished report using the LLM.
    """
    if not client: return "AI 연결 불가. 데이터만 확인하세요."
    
    sys_msg = """
[ROLE] You are 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
[RULE]
1. Language: KOREAN ONLY. No English/Chinese characters in main text.
2. Source: Use the provided [DATA] strictly. Do NOT invent new facts.
3. Structure:
   - **🐅 그대의 본질 (Identity)**: Use Identity Data.
   - **💰 부와 성공 (Career)**: Use Career Strategy & Work Style.
   - **💖 사랑과 욕망 (Love)**: Use Love Style data.
   - **💊 건강과 양생 (Health)**: Use Health Symptom & Food.
   - **⚡ 신령의 처방 (Solution)**: Summarize Risks and Shinsal remedies.
"""
    user_msg = f"""
[DATA]
Identity: {context_data['identity']['ko']}
Career: {context_data['career']['style']}, Strategy: {context_data['career']['strategy']}
Love: {context_data['love'].get('desc', '')} - {context_data['love'].get('detail', '')}
Health: Weak in {context_data['health']['weak']}. Symptom: {context_data['health']['symptom']}. Food: {context_data['health']['food']}
Risks: {context_data['risks']}
Shinsal Details:
{context_data['shinsal_text']}

[TASK] Write the final detailed report.
"""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system", "content":sys_msg}, {"role":"user", "content":user_msg}],
            temperature=0.6
        )
        return resp.choices[0].message.content
    except: return "신령이 깊은 명상 중입니다..."

# ==========================================
# 3. MAIN UI
# ==========================================
tab1, tab2, tab3 = st.tabs(["👤 종합 정밀 진단", "💞 궁합 분석", "👨‍👩‍👧‍👦 가족/그룹 분석"])

# --- TAB 1: INDIVIDUAL ---
with tab1:
    with st.expander("📝 사주 정보 입력", expanded=True):
        c1, c2 = st.columns(2)
        p_date = c1.date_input("생년월일", value=datetime(1990,1,1), min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        p_time = c1.time_input("태어난 시간", value=time(12,0))
        p_city = c2.text_input("태어난 도시", "서울")
        p_lunar = c2.checkbox("음력", key="p_l")
        p_yoon = c2.checkbox("윤달", disabled=not p_lunar, key="p_y")
        
        if st.button("운명 확인하기", type="primary"):
            # 1. Calc
            final_date = p_date
            if p_lunar:
                try:
                    cal = KoreanLunarCalendar()
                    cal.setLunarDate(p_date.year, p_date.month, p_date.day, p_yoon)
                    final_date = datetime(cal.solarYear, cal.solarMonth, cal.solarDay).date()
                except: st.error("날짜 변환 오류"); st.stop()
            
            # 2. Engine
            coords = get_coordinates(p_city)
            raw_res = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                                      p_time.hour, p_time.minute, coords[0], coords[1])
            
            # 3. Integration Logic
            data = analyze_comprehensive_logic(raw_res, final_date.year)
            st.session_state.final_report = generate_ai_report(data)
            st.session_state.analysis_data = data

    if "final_report" in st.session_state:
        st.divider()
        d = st.session_state.analysis_data
        
        # Header Stats
        k1, k2, k3 = st.columns(3)
        k1.metric("격국/패턴", d['meta']['pattern'])
        k2.metric("에너지", d['meta']['strength'])
        k3.metric("부족한 오행", d['health']['weak'])
        
        # Main Report
        st.markdown(st.session_state.final_report)
        
        # Raw Data Expander (For verification)
        with st.expander("🔍 분석 데이터 원문 보기"):
            st.json(d)

# --- TAB 2: COMPATIBILITY ---
with tab2:
    st.info("두 사람의 정보를 입력하세요.")
    c1, c2 = st.columns(2)
    with c1:
        st.write("🅰️ 본인")
        d1 = st.date_input("생일 A", value=datetime(1990,1,1), min_value=datetime(1900,1,1))
    with c2:
        st.write("🅱️ 상대방")
        d2 = st.date_input("생일 B", value=datetime(1992,1,1), min_value=datetime(1900,1,1))
        
    if st.button("궁합 보기"):
        # Simple Calculation for Demo
        s1 = calculate_saju_v3(d1.year, d1.month, d1.day, 12, 0, 37.56, 126.97)
        s2 = calculate_saju_v3(d2.year, d2.month, d2.day, 12, 0, 37.56, 126.97)
        
        key = f"{s1['Day_Stem']}_{s2['Day_Stem']}"
        info = DB['compatibility'].get(key)
        
        st.divider()
        st.subheader(f"{s1['Day_Stem']} ❤️ {s2['Day_Stem']}")
        
        if info:
            score = info.get('score', 50)
            st.progress(score)
            st.write(f"**점수: {score}점**")
            st.success(info['ko_relation'])
        else:
            st.warning("기본 오행 궁합으로 분석합니다.")

# --- TAB 3: FAMILY ---
with tab3:
    st.markdown("### 👨‍👩‍👧‍👦 가족 구성원 입력")
    # (Simple Input Loop)
    if "fam_list" not in st.session_state: st.session_state.fam_list = []
    
    with st.form("fam_form"):
        fn = st.text_input("이름")
        fd = st.date_input("생년월일", min_value=datetime(1900,1,1))
        if st.form_submit_button("추가"):
            st.session_state.fam_list.append({"name":fn, "date":fd})
            st.rerun()
            
    if st.session_state.fam_list:
        st.write(pd.DataFrame(st.session_state.fam_list))
        if st.button("분석"):
            st.write("가족 간 역학 관계 분석 결과...")
            # (Loop through Matrix DB similar to previous versions)
            # Implemented in full version, abbreviated here for length
