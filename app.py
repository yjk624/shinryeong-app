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
# 0. CONFIG & TEXTS (Must be first)
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

UI_TEXT = {
    "ko": {
        "title": "🔮 신령 사주리포트", "caption": "정통 명리학 기반 데이터 분석 시스템 v15.0 (최종 완성)",
        "sidebar_title": "설정", "lang_btn": "English Mode", "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일", "input_time": "태어난 시간", "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별", "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작", "loading": "천문 데이터 계산 및 신강/신약 정밀 판별 중...",
        "warn_title": "법적 면책 조항", "warn_text": "본 분석은 통계적 참고자료입니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report", "caption": "Authentic Saju Analysis System v15.0",
        "sidebar_title": "Settings", "lang_btn": "한국어 모드", "reset_btn": "Reset Session",
        "input_dob": "Date of Birth", "input_time": "Birth Time", "input_city": "Birth City (e.g., Seoul)",
        "input_gender": "Gender", "concern_label": "Describe your specific concern.",
        "submit_btn": "📜 Start Analysis", "loading": "Calculating Astral Data...",
        "warn_title": "Legal Disclaimer", "warn_text": "Reference only.",
        "placeholder": "Ask follow-up questions..."
    }
}

# Initialize State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v15_final", timeout=10)
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
# 2. LOGIC ENGINE (v15.0 - Logic Fix)
# ==========================================
def analyze_logic_v15(saju_res):
    """
    Robust logic for Strength and Pattern.
    """
    dm = saju_res['Day_Stem'] # 일간 (나)
    season = saju_res['Month_Branch'] # 월지 (계절)
    full_str = saju_res['Full_String']
    
    # 1. Elements Definition
    elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    season_map = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}
    
    my_elem = elem_map[dm]
    season_elem = season_map[season]
    
    # 2. Supporters (Indicates 'My Side')
    supporters = []
    if my_elem == '목': supporters = ['수', '목']
    elif my_elem == '화': supporters = ['목', '화']
    elif my_elem == '토': supporters = ['화', '토']
    elif my_elem == '금': supporters = ['토', '금']
    elif my_elem == '수': supporters = ['금', '수'] # Water needs Metal & Water
    
    # 3. Strength Calculation (Scoring)
    score = 0
    # Season (Month) Check - The most important factor
    # If Season supports Me -> +50. If not -> -50.
    if season_elem in supporters: 
        score += 50
    else: 
        score -= 50 # Penalize heavily for Sil-ryeong (Born in hostile season)
        
    # Pillar Check
    for char in full_str:
        if char == ' ': continue
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        
        if ce in supporters: score += 10
        else: score -= 5
    
    # Diagnosis
    if score >= 10: 
        strength = "신강(Strong - 주도적)" 
    else: 
        strength = "신약(Sensitive - 섬세함)"

    # 4. Pattern Detection
    # Wealth Element: What I control
    wealth_map = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'}
    my_wealth = wealth_map[my_elem]
    
    wealth_count = 0
    for char in full_str:
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        if ce == my_wealth: wealth_count += 1
        
    pattern = "일반격"
    advice_core = "오행의 균형을 맞추는 것이 중요하네."
    
    # Jae-da-sin-yak Check: Weak AND Many Wealth
    if "신약" in strength and wealth_count >= 3:
        pattern = "재다신약(財多身弱 - 재물은 많으나 가질 힘이 약함)"
        strength = "극신약(Very Weak)" # Force logic update
        advice_core = "돈을 쫓으면 건강을 해치거나 돈이 나가는 구조일세. 본인의 실력(자격증, 공부)을 키우거나, 주변 동료(비견/겁재)와 협업해야 돈이 모이네."
    elif wealth_count >= 3:
        pattern = "재성과다(Wealth Overload - 사업가적 기질)"
        advice_core = "타고난 사업가 기질이 있으나, 재물 관리에 신중해야 하네."

    # 5. Metaphor
    metaphor_db = {
        '갑': "거목(Pioneer)", '을': "화초(Survivor)", '병': "태양(Visionary)", '정': "촛불(Mentor)",
        '무': "태산(Guardian)", '기': "대지(Cultivator)", '경': "바위(Warrior)", '신': "보석(Specialist)",
        '임': "바다(Strategist)", '계': "봄비(Intuitive)"
    }
    
    # 6. Shinsal
    shinsal = ", ".join(saju_res['Shinsal']) if saju_res['Shinsal'] else "평온함"

    return {
        "identity": dm, "metaphor": metaphor_db.get(dm, "기운"),
        "strength": strength, "pattern": pattern, "advice": advice_core,
        "shinsal": shinsal, "pillars": full_str,
        "wealth_count": wealth_count
    }

def generate_ai_response(messages, lang_mode):
    # STRICT SYSTEM PROMPT
    sys_instruction = """
[CRITICAL INSTRUCTION]
Role: You are 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
Language: KOREAN ONLY. No German/Chinese/English in body text.
Input Data is Absolute Truth: Use the provided Strength and Pattern strictly.
Task:
1. If Pattern is '재다신약', explain: "You have many opportunities for money, but you are too weak to hold them alone. Strengthen yourself with study or friends."
2. Explain 'Shinsal' (e.g. Yeokma) in terms of real life (moving, travel).
3. Insert 

[Image of Five Elements Cycle]
 when explaining balance.
"""
    if messages[0]['role'] == 'system':
        messages[0]['content'] += f"\n{sys_instruction}"
        
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.5, max_tokens=4000
            )
            return stream.choices[0].message.content
        except: time_module.sleep(0.5); continue
    return "⚠️ 신령이 침묵하고 있네. 잠시 후 다시 시도하게."

# ==========================================
# 3. MAIN UI FLOW
# ==========================================
with st.sidebar:
    st.title("⚙️ 설정")
    if st.button("🔄 리셋"):
        st.session_state.clear()
        st.rerun()
    
    with st.expander("🛠️ 데이터 진단", expanded=False):
        st.json(st.session_state.saju_data_dict)

t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption("음력/윤달 지원 & 정밀 분석 엔진 v15.0")
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
        if not city: 
            st.error("⚠️ 도시를 입력하게.")
        else:
            with st.spinner("⏳ 천기누설을 준비 중이네..."):
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
                    facts = analyze_logic_v15(parse_saju_to_korean(saju_res))
                    
                    st.session_state.saju_data_dict = facts
                    st.session_state.raw_input_data = {"date": str(final_date), "concern": concern}
                    
                    # 3. Report Generation
                    sys_p = f"""
[ABSOLUTE FACTS]
- Identity: {facts['metaphor']} (Day Master: {facts['identity']})
- Strength: {facts['strength']}
- Pattern: {facts['pattern']}
- Advice Logic: {facts['advice']}
- Shinsal: {facts['shinsal']}
- User Concern: "{concern}"

[TASK]
Write a report in Korean 'Hage-che'.
1. 🐅 타고난 그릇 (Identity): Describe the Metaphor.
2. 🗡️ 운명의 명암 (Analysis): Explain Strength and Pattern.
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
User: {facts['metaphor']} ({facts['identity']}). Pattern: {facts['pattern']}.
Question: "{q}"
Answer specifically using the data. Do NOT repeat the intro.
"""
        msgs = [{"role": "system", "content": context_msg}, 
                {"role": "user", "content": q}]
        
        with st.chat_message("assistant"):
            with st.spinner("신령이 점을 치는 중..."):
                full_resp = generate_ai_response(msgs, mode="chat")
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
