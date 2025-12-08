import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim
from geopy.distance import great_circle
from korean_lunar_calendar import KoreanLunarCalendar
import json

# ==========================================
# 0. SYSTEM CONFIGURATION
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

# Initialize State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v14_final", timeout=10)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

# ==========================================
# 1. HELPER FUNCTIONS
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

def convert_lunar_to_solar(year, month, day, is_intercalary):
    try:
        calendar = KoreanLunarCalendar()
        calendar.setLunarDate(year, month, day, is_intercalary)
        return datetime(calendar.solarYear, calendar.solarMonth, calendar.solarDay).date()
    except: return None

# ==========================================
# 2. TRUTH ENGINE (Python Logic v14.0)
# ==========================================
def parse_saju_to_korean(saju_res):
    E2K = {
        'Gap': '갑', 'Eul': '을', 'Byeong': '병', 'Jeong': '정', 'Mu': '무',
        'Gi': '기', 'Gyeong': '경', 'Sin': '신', 'Im': '임', 'Gye': '계',
        'Ja': '자', 'Chuk': '축', 'In': '인', 'Myo': '묘', 'Jin': '진',
        'Sa': '사', 'O': '오', 'Mi': '미', 'Yu': '유', 'Sul': '술', 'Hae': '해'
    }
    def tr(p):
        s, b = p.split('-')
        return E2K.get(s, s), E2K.get(b, b)

    y_s, y_b = tr(saju_res['Year'])
    m_s, m_b = tr(saju_res['Month'])
    d_s, d_b = tr(saju_res['Day']) 
    t_s, t_b = tr(saju_res['Time'])
    
    return {
        "year": f"{y_s}{y_b}", "month": f"{m_s}{m_b}", 
        "day": f"{d_s}{d_b}", "time": f"{t_s}{t_b}",
        "day_master": d_s, "month_branch": m_b
    }

def analyze_logic_v14(saju_korean):
    """
    [CRITICAL UPDATE] Season-Weighted Strength Calculation
    """
    dm = saju_korean['day_master'] # Me
    season = saju_korean['month_branch'] # Environment
    full_str = saju_korean['year'] + saju_korean['month'] + saju_korean['day'] + saju_korean['time']
    
    # 1. Elements Definition
    elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    season_map = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}
    
    my_elem = elem_map[dm]
    season_elem = season_map[season]
    
    # 2. Supporters (My Resource & Friends)
    supporters = []
    if my_elem == '목': supporters = ['수', '목']
    elif my_elem == '화': supporters = ['목', '화']
    elif my_elem == '토': supporters = ['화', '토']
    elif my_elem == '금': supporters = ['토', '금']
    elif my_elem == '수': supporters = ['금', '수'] # Water needs Metal & Water
    
    # 3. Strength Calculation (Weighted)
    score = 0
    # Season Check (Crucial)
    # Ex: Water(Gye) born in Fire(O) -> Not supported -> -50 points
    if season_elem in supporters: 
        score += 50
    else: 
        score -= 50 
        
    # Pillar Check
    for char in full_str:
        if char == ' ': continue
        # Map char to element (Simplified)
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        
        if ce in supporters: score += 10
        else: score -= 5
            
    # Final Diagnosis
    if score >= 20: 
        strength = "신강(Strong - 주도적)" 
        advice = "자신의 넘치는 에너지를 사회적으로 발산해야 함"
    else: 
        strength = "신약(Sensitive - 섬세함)"
        advice = "환경의 영향을 많이 받으므로, 주변 인맥과 멘토가 중요함"

    # 4. Pattern Detection (Jae-da-sin-yak)
    # Wealth Element: What I control
    wealth_map = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'} # Water controls Fire
    my_wealth = wealth_map[my_elem]
    
    wealth_count = 0
    for char in full_str:
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화' # Fire
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        if ce == my_wealth: wealth_count += 1
        
    pattern = "일반격"
    if "신약" in strength and wealth_count >= 3:
        pattern = "재다신약(財多身弱)"
        strength = "극신약(Very Weak)" # Force update
        advice = "재물 욕심은 많으나 가질 힘이 부족함. 반드시 공부(인성)와 사람(비겁)으로 힘을 길러야 돈이 붙음."

    # 5. Metaphor
    metaphor_db = {
        '갑': "곧게 뻗은 거목(Pioneer)", '을': "끈질긴 생명력의 화초(Survivor)", 
        '병': "만물을 비추는 태양(Visionary)", '정': "어둠을 밝히는 촛불(Mentor)",
        '무': "묵직한 태산(Guardian)", '기': "비옥한 대지(Cultivator)", 
        '경': "단단한 바위(Warrior)", '신': "예리한 보석(Specialist)",
        '임': "깊고 넓은 바다(Strategist)", '계': "스며드는 봄비(Intuitive)"
    }
    
    # 6. Shinsal
    shinsal = []
    if any(c in full_str for c in "자오묘유"): shinsal.append("도화살(Popularity)")
    if any(c in full_str for c in "인신사해"): shinsal.append("역마살(Global Mobility)")
    if any(c in full_str for c in "진술축미"): shinsal.append("화개살(Artistry)")
    if "오" in full_str and "오" in full_str and "병" in full_str: # Kim Yong-jun specific
        shinsal.append("자형살(Self-Punishment - 완벽주의)")

    return {
        "identity": dm, "metaphor": metaphor_db.get(dm, "기운"),
        "strength": strength, "pattern": pattern, "advice": advice,
        "shinsal": ", ".join(shinsal), "pillars": full_str,
        "wealth_count": wealth_count
    }

def generate_ai_response(messages, mode="report"):
    # STRICT INSTRUCTION to prevent hallucination
    sys_instruction = """
[ROLE] You are 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
[LANGUAGE] KOREAN ONLY. Never use Vietnamese, Chinese, or English words in the text.
[INSTRUCTION]
1. Do not calculate. Use the provided [DATA] as absolute truth.
2. If Pattern is '재다신약', interpret it as: "Money flows around you, but you are too weak to hold it. You need to study or work with friends to keep it."
3. Do not be generic. Be mystical yet painfully accurate.
"""
    if mode == "chat":
        sys_instruction += "\n[CHAT MODE] Answer ONLY the user's specific question using the data. Do NOT repeat the birth chart or introduction."

    if messages[0]['role'] == 'system':
        messages[0]['content'] += f"\n{sys_instruction}"
        
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.6, max_tokens=4000
            )
            return stream.choices[0].message.content
        except: time_module.sleep(0.5); continue
    return "⚠️ 신령이 침묵하고 있네. 다시 시도하게."

# ==========================================
# 3. MAIN UI FLOW
# ==========================================
with st.sidebar:
    st.title("⚙️ 신령의 제단")
    if st.button("🔄 새로운 점사 보기"):
        st.session_state.clear()
        st.rerun()
    
    with st.expander("🔍 데이터 분석값", expanded=False):
        st.json(st.session_state.saju_data_dict)

t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption("AI 정통 명리학 분석 시스템 v14.0")
st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

# A. Input Form
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        with c1:
            input_date = st.date_input(t["input_dob"], min_value=datetime(1940,1,1))
            time_val = st.time_input(t["input_time"], value=time(12,0))
            is_lunar = st.checkbox("음력 (Lunar)", value=False)
            is_intercalary = st.checkbox("윤달", value=False, disabled=not is_lunar)
        with c2:
            gender = st.radio(t["input_gender"], ["남성", "여성"])
            city = st.text_input(t["input_city"])
        
        concern = st.text_area(t["concern_label"], height=80)
        submit = st.form_submit_button(t["submit_btn"])
    
    if submit:
        if not city: st.error("⚠️ 도시를 입력하게.")
        else:
            with st.spinner("⏳ 신령이 천문 데이터를 읽고 있네..."):
                coords, city_name = get_coordinates(city)
                if not coords:
                    st.error(f"❌ '{city}'의 기운을 찾을 수 없네.")
                else:
                    # 1. Calc
                    final_date = input_date
                    if is_lunar:
                        final_date = convert_lunar_to_solar(input_date.year, input_date.month, input_date.day, is_intercalary)
                        if not final_date: st.error("❌ 날짜가 잘못되었네."); st.stop()
                    
                    saju_res = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                                               time_val.hour, time_val.minute, coords[0], coords[1])
                    
                    # 2. Logic (Python Truth Engine)
                    saju_korean = parse_saju_to_korean(saju_res)
                    facts = analyze_logic_v14(saju_korean)
                    
                    st.session_state.saju_data_dict = facts
                    st.session_state.raw_input_data = {"date": str(final_date), "concern": concern}
                    
                    # 3. Report Generation
                    sys_p = f"""
[ABSOLUTE FACTS]
- Identity: {facts['metaphor']} (Day Master: {facts['identity']})
- Strength: {facts['strength']} (Score was calculated rigorously)
- Special Pattern: {facts['pattern']}
- Advice Logic: {facts['advice']}
- Shinsal: {facts['shinsal']}
- User Concern: "{concern}"

[TASK]
Write a report in Korean 'Hage-che'.
1. 🐅 타고난 그릇 (Identity): Describe the Metaphor.
2. 🗡️ 운명의 명암 (Analysis): Explain Strength and Pattern. If 'Jae-da-sin-yak', warn about health and money management.
3. ⚡ 신령의 처방 (Solution): Give the 'Advice Logic'.
"""
                    st.session_state.saju_context = sys_p
                    msgs = [{"role": "system", "content": sys_p}, 
                            {"role": "user", "content": "상세 분석 리포트를 작성하라."}]
                    
                    full_resp = generate_ai_response(msgs, mode="report")
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    st.session_state.analysis_complete = True
                    st.rerun()

# B. Chat Mode
else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Inject Specific Data for Chat
        facts = st.session_state.saju_data_dict
        context_msg = f"""
[CHAT CONTEXT]
User Identity: {facts['metaphor']} ({facts['identity']})
Pattern: {facts['pattern']}
Question: "{q}"

[INSTRUCTION]
Answer the question "{q}" specifically using the pattern '{facts['pattern']}'.
Do not repeat the introduction. Go straight to the answer.
If asking about money, mention 'Wealth Element Count: {facts['wealth_count']}'.
"""
        msgs = [{"role": "system", "content": context_msg}, 
                {"role": "user", "content": q}]
        
        with st.chat_message("assistant"):
            with st.spinner("신령이 점을 치는 중..."):
                full_resp = generate_ai_response(msgs, mode="chat")
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
