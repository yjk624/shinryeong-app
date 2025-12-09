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
# 0. STYLE & CONFIG (UI 설정)
# ==========================================
st.set_page_config(page_title="신령: 귀신같은 운명 분석", page_icon="🔮", layout="centered")

# Custom CSS for Mystical UI (가독성 및 디자인 강화)
st.markdown("""
<style>
    .main-title { font-size: 2.5rem !important; font-weight: 800; color: #4A148C; text-align: center; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem !important; color: #555; text-align: center; margin-bottom: 25px; }
    .section-header { 
        font-size: 1.4rem !important; 
        font-weight: 600; 
        color: #311B92; 
        border-left: 5px solid #673AB7;
        padding-left: 10px;
        margin-top: 30px; 
        margin-bottom: 15px; 
        background-color: #F3E5F5;
        padding-top: 5px;
        padding-bottom: 5px;
        border-radius: 0 5px 5px 0;
    }
    .metric-box { border: 1px solid #ddd; padding: 10px; border-radius: 5px; text-align: center; }
    .stAlert { margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# State Initialization (안전한 세션 관리)
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "family_members" not in st.session_state: st.session_state.family_members = []
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

# ==========================================
# 1. DATABASE LOADING (The Knowledge Base)
# ==========================================
@st.cache_data
def load_databases():
    """
    Loads all JSON databases including the new Lifecycle Pillar DB.
    """
    db = {}
    # Load List: 이제 9개의 핵심 DB를 로드합니다.
    files = [
        'identity', 'career', 'love', 'health', 'timeline', 
        'shinsal', 'compatibility', 'five_elements_matrix',
        'lifecycle_pillar' # [NEW] 근묘화실 생애주기 DB 추가
    ]
    
    for name in files:
        try:
            # 파일명 매핑 (matrix, lifecycle 등 이름 불일치 방지)
            fname = name
            if name == "matrix": fname = "five_elements_matrix"
            elif name == "lifecycle_pillar": fname = "lifecycle_pillar_db"
            elif 'db' not in name: fname = f"{name}_db"
            
            path = f"saju_db/{fname}.json"
            
            with open(path, "r", encoding='utf-8') as f: 
                db[name] = json.load(f)
                
        except FileNotFoundError:
            # 파일이 없을 경우 빈 딕셔너리로 처리하여 앱 다운 방지
            db[name] = {}
        except json.JSONDecodeError:
            st.error(f"🚨 JSON 오류: {name} 파일의 형식이 잘못되었습니다.")
            db[name] = {}
            
    return db

DB = load_databases()

# API Setup (API 키 확인)
try:
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    else: client = None
except: client = None

# ==========================================
# 2. GEOCODING & HELPERS
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "창원": (35.22, 128.68), "광주": (35.15, 126.85),
    "대전": (36.35, 127.38), "울산": (35.53, 129.31), "제주": (33.49, 126.53),
    "seoul": (37.56, 126.97), "busan": (35.17, 129.07)
}

def get_coordinates(city_input):
    """지오코딩: DB 조회 후 실패 시 Nominatim 사용"""
    clean = city_input.strip().lower()
    if clean in CITY_DB: return CITY_DB[clean]
    
    geolocator = Nominatim(user_agent="shinryeong_v23_part1", timeout=3)
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude)
    except: pass
    return CITY_DB["서울"] # Fallback

def calculate_korean_age(birth_year):
    """한국식 나이 계산 (만 나이가 아닌 연 나이 기준)"""
    return datetime.now().year - birth_year + 1
# ==========================================
# 2. LOGIC ENGINE (Analysis & Narrative)
# ==========================================
def get_saju_data(dob, tm, is_lunar, is_intercalary, city="서울"):
    """
    사주 계산 및 신강/신약, 격국, 십성 분석 통합 함수
    """
    coords = get_coordinates(city)
    final_date = dob
    
    # 1. Lunar to Solar Conversion
    if is_lunar:
        try:
            cal = KoreanLunarCalendar()
            cal.setLunarDate(dob.year, dob.month, dob.day, is_intercalary)
            final_date = datetime(cal.solarYear, cal.solarMonth, cal.solarDay).date()
        except: pass

    # 2. Engine Call (Calculate Pillars)
    raw = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                          tm.hour, tm.minute, coords[0], coords[1])
    
    # 3. Strength Calculation (Logic: Season Weight)
    dm = raw['Day_Stem']
    e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    my_elem = e_map.get(dm, '수')
    
    supporters = {'목':['수','목'], '화':['목','화'], '토':['화','토'], '금':['토','금'], '수':['금','수']}[my_elem]
    season = raw['Month_Branch']
    # Season Element Mapping
    s_map = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}
    season_elem = s_map.get(season, '토')
    
    score = 0
    # 월지 득령 여부 (가장 중요: +/- 50점)
    if season_elem in supporters: score += 50
    else: score -= 50
    
    # 득세 여부 (글자 수 체크)
    for char in raw['Full_String']:
        if char == ' ': continue
        ce = '토' # default
        if char in "갑을인묘": ce='목'
        elif char in "병정사오": ce='화'
        elif char in "경신신유": ce='금'
        elif char in "임계해자": ce='수'
        
        if ce in supporters: score += 10
        else: score -= 5
            
    strength = "신강" if score >= 10 else "신약"
    
    # 4. Pattern Detection (Jae-da-sin-yak Check)
    wealth_map = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'}
    my_wealth = wealth_map[my_elem]
    wealth_cnt = 0
    for char in raw['Full_String']:
         ce = '토'
         if char in "갑을인묘": ce='목'
         elif char in "병정사오": ce='화'
         elif char in "경신신유": ce='금'
         elif char in "임계해자": ce='수'
         if ce == my_wealth: wealth_cnt += 1
         
    pattern = "일반격"
    if strength == "신약" and wealth_cnt >= 3: pattern = "재다신약"
    elif wealth_cnt >= 3: pattern = "재성과다"
    
    # DB Keys
    id_key = f"{dm}_{season}"
    
    return {
        "raw": raw, "day_stem": dm, "full_str": raw['Full_String'],
        "id_key": id_key, "strength": strength, "pattern": pattern,
        "my_elem": my_elem, "birth_year": final_date.year,
        "shinsal": raw['Shinsal'], "season": season,
        "ten_gods": raw['Ten_Gods'], "weakest": my_elem # Simplified for demo
    }

def get_lifecycle_narrative(ten_gods):
    """
    [근묘화실 로직] 사주의 기둥별 십성을 분석하여 생애주기 스토리텔링 생성
    """
    narrative = []
    
    # 1. 초년운 (Year Pillar)
    y_god = ten_gods.get('Year', '비견') # Default fallback
    y_text = DB['lifecycle_pillar'].get('year_pillar', {}).get(y_god, "평범한 유년기를 보냈네.")
    narrative.append(f"🌱 **초년기 (0~19세):** {y_text}")
    
    # 2. 청년운 (Month Pillar) - 사회성/직업
    m_god = ten_gods.get('Month', '비견')
    m_text = DB['lifecycle_pillar'].get('month_pillar', {}).get(m_god, "사회에 적응하며 기반을 닦는 시기네.")
    narrative.append(f"🌿 **청년기 (20~39세):** {m_text}")
    
    # 3. 중년운 (Day Pillar - Self/Spouse) -> 일지는 엔진에서 십성을 안 주므로 약식 계산
    # (여기서는 데모를 위해 청년운의 흐름이 이어진다고 가정하거나 별도 로직 필요. 
    #  안전하게 DB의 day_pillar 기본 텍스트 활용)
    d_text = DB['lifecycle_pillar'].get('day_pillar', {}).get(m_god, "인생의 전성기를 맞이하여 결실을 맺네.") 
    narrative.append(f"🌺 **중년기 (40~59세):** {d_text}")
    
    # 4. 말년운 (Time Pillar)
    t_god = ten_gods.get('Time', '비견')
    t_text = DB['lifecycle_pillar'].get('time_pillar', {}).get(t_god, "자식 덕을 보거나 평온한 노후를 보내네.")
    narrative.append(f"🍎 **말년운 (60세~):** {t_text}")
    
    return "\n\n".join(narrative)

def generate_report(data):
    """
    AI 보고서 생성기: DB 데이터를 프롬프트에 주입하여 할루시네이션 방지
    """
    if not client: return "⚠️ AI 연결 불가. 데이터만 확인하세요."
    
    # 1. Fetch Data from DB
    id_data = DB['identity'].get(data['id_key'], {"ko": "데이터 없음"})
    
    # Career
    career_ten_god = data['ten_gods'].get('Month', '편재') # 월지 십성을 직업궁으로 봄
    career_info = DB['career'].get('ten_gods', {}).get(career_ten_god, {})
    work_style = DB['career'].get('work_style', {}).get(data['strength'], {})
    
    # Love
    love_key = f"{data['my_elem']}_{data['strength']}"
    love_info = DB['love'].get('sexual_style', {}).get(love_key, {})
    
    # Timeline Narrative (근묘화실)
    lifecycle_story = get_lifecycle_narrative(data['ten_gods'])
    
    # Forecast (2025/2026)
    y25 = DB['timeline'].get('yearly_2025_2026', {}).get(data['day_stem'], {}).get('2025', '')
    y26 = DB['timeline'].get('yearly_2025_2026', {}).get(data['day_stem'], {}).get('2026', '')

    # Special Advice
    special_advice = "균형을 맞추며 정진하게."
    if data['pattern'] == "재다신약":
        special_advice = DB['career'].get('special_advice', {}).get('재다신약', {}).get('solution', special_advice)

    # Shinsal Warning
    shinsal_warnings = []
    for s in data['shinsal']:
        key = s.split("(")[0]
        if key in DB['shinsal'].get('basic_shinsal', {}):
            shinsal_warnings.append(f"- {s}: {DB['shinsal']['basic_shinsal'][key]['risk']}")

    # 2. Build Prompt
    sys_msg = """
    [ROLE] 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체).
    [RULE] KOREAN ONLY. Use the [FACTS] to write a flowing report.
    [STRUCTURE]
    1. 🐅 그대의 그릇 (Identity & Strength)
    2. 📜 인생의 파노라마 (Life Cycle Narrative)
    3. 💰 직업과 재물 (Career Strategy)
    4. ☁️ 다가올 미래와 경고 (2025-26 & Risks)
    """
    
    user_msg = f"""
    [FACTS]
    - Identity: {id_data.get('ko', '')}
    - Strength: {data['strength']} ({work_style.get('title', '')})
    - Pattern: {data['pattern']}
    - Life Story: {lifecycle_story}
    - Career Style: {career_info.get('desc', '')}
    - Love Style: {love_info.get('desc', '')}
    - 2025 Luck: {y25}
    - 2026 Luck: {y26}
    - Special Advice: {special_advice}
    - Risk Factors: {', '.join(shinsal_warnings)}
    
    [TASK] Write a detailed destiny report.
    """
    
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system", "content":sys_msg}, {"role":"user", "content":user_msg}],
            temperature=0.7
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"신령이 깊은 명상 중이라네. (오류: {str(e)})"
# ==========================================
# 3. MAIN UI LAYOUT
# ==========================================
st.markdown('<p class="main-title">🔮 신령(神靈)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">데이터로 보는 나의 운명 (v23.0 Final)</p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["👤 종합 정밀 진단", "💞 궁합 분석", "👨‍👩‍👧‍👦 가족/그룹 분석"])

# --- TAB 1: INDIVIDUAL (개인 정밀 진단) ---
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
            
            # [Logic] 생애주기 내러티브 생성
            lifecycle_story = get_lifecycle_narrative(res['ten_gods'])
            res['timeline_txt'] = lifecycle_story
            
            st.session_state.saju_data_dict = res
            
            with st.spinner("신령이 천기를 읽고 있습니다..."):
                st.session_state.final_report = generate_report(res)

    if "final_report" in st.session_state:
        st.divider()
        res = st.session_state.saju_data_dict
        
        # Dashboard Metrics
        k1, k2, k3 = st.columns(3)
        k1.metric("일주 (Identity)", f"{res['day_stem']} (Day)")
        k2.metric("에너지 (Energy)", res['strength'])
        k3.metric("격국 (Pattern)", res['pattern'])
        
        # Main AI Report
        st.markdown(st.session_state.final_report)
        
        # Shinsal Detail Expander (DB Lookup)
        if res['shinsal']:
            st.markdown("---")
            st.subheader("⚡ 발견된 특수 기운 (신살)")
            for sal in res['shinsal']:
                s_key = sal.split("(")[0]
                # Safe DB Lookup (basic_shinsal or root)
                info = DB['shinsal'].get('basic_shinsal', {}).get(s_key, {})
                if not info: info = DB['shinsal'].get(s_key, {})
                
                if info:
                    with st.expander(f"🔹 {sal} 상세 풀이"):
                        st.write(f"💬 **의미:** {info.get('desc','')}")
                        st.warning(f"⚠️ **위험:** {info.get('risk','')}")
                        st.info(f"🛡️ **개운법:** {info.get('remedy','')}")

# --- TAB 2: COMPATIBILITY (궁합 진단) ---
with tab2:
    st.markdown('<p class="section-header">💞 궁합 진단</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.info("🅰️ 본인")
        a_date = st.date_input("생일", value=datetime(1990,1,1), key="a_d", min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        a_time = st.time_input("시간", value=time(12,0), key="a_t")
    with c2:
        st.info("🅱️ 상대방")
        b_date = st.date_input("생일", value=datetime(1992,1,1), key="b_d", min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        b_time = st.time_input("시간", value=time(12,0), key="b_t")

    if st.button("궁합 분석 시작"):
        # Safe DB Check
        if not DB.get('compatibility'):
            st.error("궁합 데이터베이스가 로드되지 않았습니다.")
        else:
            r_a = get_saju_data(a_date, a_time, False, False)
            r_b = get_saju_data(b_date, b_time, False, False)
            
            # Key Generation (Bidirectional Check)
            key = f"{r_a['day_stem']}_{r_b['day_stem']}"
            info = DB['compatibility'].get(key)
            
            # Fallback for reverse key if needed
            if not info:
                 reverse_key = f"{r_b['day_stem']}_{r_a['day_stem']}"
                 # Note: Reverse lookup logic would require DB restructuring or symmetric keys. 
                 # Currently assuming DB has keys or using fallback.

            st.divider()
            st.subheader(f"{r_a['day_stem']} ❤️ {r_b['day_stem']}")
            
            if info:
                score = info.get('score', 60)
                st.progress(score)
                st.markdown(f"<h3 style='text-align: center; color: #E91E63;'>궁합 점수: {score}점</h3>", unsafe_allow_html=True)
                st.success(f"**관계의 본질:** {info.get('ko_relation', '정보 없음')}")
            else:
                # Basic Element Match Fallback
                st.warning("상세 데이터가 없습니다. (오행 기본 궁합 적용)")
                st.write("서로 다른 매력에 끌리거나 보완하는 관계입니다.")

# --- TAB 3: FAMILY (가족 역학 관계) ---
with tab3:
    st.markdown('<p class="section-header">👨‍👩‍👧‍👦 가족/그룹 역학 관계</p>', unsafe_allow_html=True)
    
    with st.form("fam_form"):
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        fn = c1.text_input("이름/호칭")
        fd = c2.date_input("생년월일", min_value=datetime(1900,1,1), max_value=datetime(2100,12,31))
        ft = c3.time_input("시간", value=time(12,0))
        add = st.form_submit_button("구성원 추가")
        
        if add and fn:
            st.session_state.family_members.append({"name":fn, "date":fd, "time":ft})
            st.rerun()

    if st.session_state.family_members:
        st.write("---")
        # List Display
        for idx, m in enumerate(st.session_state.family_members):
            st.text(f"{idx+1}. {m['name']} ({m['date']})")
        
        if st.button("가족 관계 분석"):
            fam_res = []
            # Calculate all members first
            for m in st.session_state.family_members:
                res = get_saju_data(m['date'], m['time'], False, False)
                e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
                elem = e_map.get(res['day_stem'], '토')
                fam_res.append({'name':m['name'], 'elem':elem, 'stem':res['day_stem'], 'full':res['full_str']})
            
            st.markdown("### 🧬 관계 매트릭스 (Interaction Matrix)")
            
            order = ['목','화','토','금','수']
            # Loop through pairs
            for i in range(len(fam_res)):
                for j in range(i+1, len(fam_res)):
                    p1 = fam_res[i]
                    p2 = fam_res[j]
                    
                    try:
                        i1 = order.index(p1['elem'])
                        i2 = order.index(p2['elem'])
                    except: continue 
                    
                    rel_type = "비견 (친구/동등)"
                    desc = "서로 대등한 관계"
                    key = None

                    # Matrix Logic (Saeng/Geuk)
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
                    
                    # DB Lookup
                    if key and key in DB['matrix']:
                         desc = DB['matrix'][key].get('role_parent_child', desc)

                    with st.container():
                        st.info(f"**{p1['name']}** ({p1['elem']}) ↔ **{p2['name']}** ({p2['elem']}) : {rel_type}")
                        st.caption(f"💡 {desc}")

            st.markdown("### ⚠️ 2026년(병오년) 키맨 경고")
            risk_found = False
            for m in fam_res:
                # Rat(자) in chart clashes with Horse(오) year
                if '자' in m['full']:
                    st.error(f"🚨 **{m['name']}**: 자오충(沖) 발생! (이동, 변동, 건강 주의)")
                    risk_found = True
            if not risk_found:
                st.success("2026년에는 가족 중 큰 충돌이 예상되지 않습니다.")

    if st.button("목록 초기화"):
        st.session_state.family_members = []
        st.rerun()
