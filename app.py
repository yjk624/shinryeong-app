import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim
from geopy.distance import great_circle
import json

# ==========================================
# 0. SYSTEM CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

# Initialize State (Safety Checks)
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v12_3_final", timeout=10)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

# ==========================================
# 1. HELPER FUNCTIONS & MAPPING
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "창원": (35.22, 128.68), "광주": (35.15, 126.85),
    "대전": (36.35, 127.38), "울산": (35.53, 129.31), "제주": (33.49, 126.53),
    "seoul": (37.56, 126.97), "busan": (35.17, 129.07), "changwon": (35.22, 128.68)
}

def get_coordinates(city_input):
    clean = city_input.strip().lower()
    if clean in CITY_DB: return CITY_DB[clean], city_input
    
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude), city_input
    except: pass
    
    # Nearest Neighbor Fallback
    if city_input and any(c.isalpha() for c in city_input):
        try:
            approx_loc = geolocator.geocode(city_input + ", South Korea", timeout=3)
            if approx_loc:
                min_dist = float('inf')
                nearest_coords = None
                input_pt = (approx_loc.latitude, approx_loc.longitude)
                for coords in CITY_DB.values():
                    dist = great_circle(input_pt, coords).km
                    if dist < min_dist:
                        min_dist = dist
                        nearest_coords = coords
                if min_dist < 50: return nearest_coords, f"{city_input} (Nearest)"
        except: pass
    return None, None

def get_ganji_year(year):
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    return gan[(year - 4) % 10], ji[(year - 4) % 12]

# ==========================================
# 2. LOGIC ENGINE
# ==========================================
def parse_saju_to_korean(saju_res):
    """
    Converts English output from saju_engine to Korean.
    """
    E2K = {
        'Gap': '갑', 'Eul': '을', 'Byeong': '병', 'Jeong': '정', 'Mu': '무',
        'Gi': '기', 'Gyeong': '경', 'Sin': '신', 'Im': '임', 'Gye': '계',
        'Ja': '자', 'Chuk': '축', 'In': '인', 'Myo': '묘', 'Jin': '진',
        'Sa': '사', 'O': '오', 'Mi': '미', 'Yu': '유', 'Sul': '술', 'Hae': '해'
    }
    
    def translate_pillar(p_str):
        stem, branch = p_str.split('-')
        return E2K.get(stem, stem), E2K.get(branch, branch)

    y_s, y_b = translate_pillar(saju_res['Year'])
    m_s, m_b = translate_pillar(saju_res['Month'])
    d_s, d_b = translate_pillar(saju_res['Day']) 
    t_s, t_b = translate_pillar(saju_res['Time'])
    
    return {
        "year": f"{y_s}{y_b}", "month": f"{m_s}{m_b}", 
        "day": f"{d_s}{d_b}", "time": f"{t_s}{t_b}",
        "day_master": d_s, # 일간 (나)
        "month_branch": m_b # 월지 (환경/계절)
    }

def analyze_logic_v12(saju_korean):
    """
    Detailed Logic for Persona Injection.
    """
    dm = saju_korean['day_master'] 
    season = saju_korean['month_branch']
    full_str = saju_korean['year'] + saju_korean['month'] + saju_korean['day'] + saju_korean['time']
    
    # 1. Elements Definition
    elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    season_map = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}
    
    my_elem = elem_map[dm]
    season_elem = season_map[season]
    
    # 2. Strength (Deuk-ryeong)
    supporters = {
        '목': ['수', '목'], '화': ['목', '화'], '토': ['화', '토'], 
        '금': ['토', '금'], '수': ['금', '수']
    }
    
    is_supported = season_elem in supporters[my_elem]
    
    score = 0
    if is_supported: score += 50 
    
    support_cnt = 0
    for char in full_str:
        c_elem = '토' 
        if char in "갑을인묘": c_elem = '목'
        elif char in "병정사오": c_elem = '화'
        elif char in "경신신유": c_elem = '금'
        elif char in "임계해자": c_elem = '수'
        
        if c_elem in supporters[my_elem]:
            support_count += 1
            
    score += (support_count * 10)
    strength = "신강(身强 - 주도적인 힘)" if score >= 50 else "신약(身弱 - 섬세하고 환경에 민감함)"
    
    # 3. Special Pattern (Jae-da-sin-yak Check)
    wealth_elem = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'}[my_elem]
    wealth_count = 0
    for char in full_str:
        c_elem = '토'
        if char in "갑을인묘": c_elem = '목'
        elif char in "병정사오": c_elem = '화'
        elif char in "경신신유": c_elem = '금'
        elif char in "임계해자": c_elem = '수'
        if c_elem == wealth_elem: wealth_count += 1
        
    pattern = "일반격"
    if "신약" in strength and wealth_count >= 3:
        pattern = "재다신약(財多身弱 - 재물 욕심은 많으나 감당할 힘이 부족함)"
    elif wealth_count >= 3:
        pattern = "재성과다(Wealth Overload - 사업가적 기질)"

    # 4. Metaphor
    metaphor_db = {
        '갑': "곧게 뻗은 거목(Pioneer)", '을': "끈질긴 생명력의 화초(Survivor)", 
        '병': "만물을 비추는 태양(Visionary)", '정': "어둠을 밝히는 촛불(Mentor)",
        '무': "묵직한 태산(Guardian)", '기': "비옥한 대지(Cultivator)", 
        '경': "단단한 바위(Warrior)", '신': "예리한 보석(Specialist)",
        '임': "깊고 넓은 바다(Strategist)", '계': "스며드는 봄비(Intuitive)"
    }
    
    # 5. Shinsal
    shinsal = []
    if any(c in full_str for c in "자오묘유"): shinsal.append("도화살(Popularity - 사람을 끄는 매력)")
    if any(c in full_str for c in "인신사해"): shinsal.append("역마살(Mobility - 이동과 변화)")
    if any(c in full_str for c in "진술축미"): shinsal.append("화개살(Artistry - 명예와 고독)")
    
    return {
        "identity": dm,
        "element": my_elem,
        "metaphor": metaphor_db.get(dm, "신비한 기운"),
        "strength": strength,
        "pattern": pattern,
        "shinsal": ", ".join(shinsal) if shinsal else "평온하고 맑은 기운",
        "pillars": full_str
    }

def generate_ai_response(messages, lang_mode):
    # FIXED: Syntax error resolved (Triple Quotes)
    sys_instruction = """
[CRITICAL RULE] You are 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
Language: KOREAN ONLY. Absolutely NO German or English words in the final output text.
Format: Use the provided JSON data to answer. Do not hallucinate generic advice.
Visuals: When explaining energy balance, insert 

[Image of Five Elements Cycle]
.
For 'Jae-da-sin-yak' (재다신약), warn about health/stress and advise building strength (Study/License).
Structure:
1. 🐅 타고난 그릇 (Identity): Explain the metaphor and strength clearly.
2. ☁️ 운명의 흐름 (Analysis): Explain the Pattern and Shinsal.
3. ⚡ 신령의 처방 (Solution): Give specific, actionable advice based on the Pattern.
"""
    
    # Insert system instruction if missing
    if messages[0]['role'] == 'system':
        messages[0]['content'] += f"\n{sys_instruction}"
        
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.5, max_tokens=3500
            )
            return stream.choices[0].message.content
        except: time_module.sleep(0.5); continue
    return "⚠️ 신령이 깊은 명상에 잠겨 응답하지 못했습니다. 다시 시도해주게."

# ==========================================
# 3. MAIN EXECUTION FLOW
# ==========================================

# A. Sidebar & Diagnostic
with st.sidebar:
    st.title("⚙️ 설정")
    if st.button("🔄 새로운 상담"):
        st.session_state.clear()
        st.rerun()
    
    # Debug Panel
    with st.expander("🛠️ 데이터 진단", expanded=False):
        st.json(st.session_state.saju_data_dict)

t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption(t["caption"])
st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

# B. Input Form
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input(t["input_dob"], min_value=datetime(1940,1,1))
            time_val = st.time_input(t["input_time"], value=time(12,0))
        with c2:
            gender = st.radio(t["input_gender"], ["남성", "여성"])
            city = st.text_input(t["input_city"])
        
        concern = st.text_area(t["concern_label"], height=80)
        submit = st.form_submit_button(t["submit_btn"])
    
    if submit:
        if not city: 
            st.error("⚠️ 도시 정보를 입력해주세요.")
        else:
            # 1. Process Data Immediately (No Rerun Loop)
            with st.spinner(t["loading"]):
                coords, city_name = get_coordinates(city)
                if not coords:
                    st.error(f"❌ '{city}'의 위치를 찾을 수 없습니다.")
                else:
                    # Saju Calculation
                    saju_raw = calculate_saju_v3(date.year, date.month, date.day, 
                                               time_val.hour, time_val.minute, coords[0], coords[1])
                    
                    # Logic Processing
                    saju_korean = parse_saju_to_korean(saju_raw)
                    facts = analyze_logic_v12(saju_korean)
                    
                    # Save State
                    st.session_state.saju_data_dict = facts
                    st.session_state.raw_input_data = {"date": str(date), "concern": concern}
                    
                    # AI Generation
                    sys_p = f"""
[DATA]
Identity: {facts['metaphor']} (Day Master: {facts['identity']})
Strength: {facts['strength']}
Pattern: {facts['pattern']}
Shinsal: {facts['shinsal']}
Concern: "{concern}"

[TASK]
Write a detailed report in Korean (Hage-che).
"""
                    st.session_state.saju_context = sys_p
                    msgs = [{"role": "system", "content": sys_p}, 
                            {"role": "user", "content": "심층 분석 보고서를 작성하라."}]
                    
                    full_resp = generate_ai_response(msgs, st.session_state.lang)
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    st.session_state.analysis_complete = True
                    st.rerun()

# C. Chat Interface
else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Inject precise data context for follow-up
        facts = st.session_state.saju_data_dict
        context_msg = f"""
[CONTEXT REMINDER]
User is {facts['metaphor']} ({facts['identity']}).
Pattern: {facts['pattern']}.
Question: "{q}"
Answer specifically based on this pattern. 
Use 

[Image of Five Elements Cycle]
 if explaining balance.
"""
        msgs = [{"role": "system", "content": context_msg}, 
                {"role": "user", "content": q}]
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                full_resp = generate_ai_response(msgs, st.session_state.lang)
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
