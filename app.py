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

UI_TEXT = {
    "ko": {
        "title": "🔮 신령 사주리포트",
        "caption": "정통 명리학 기반 데이터 분석 시스템 v13.3 (로직 완전 수정)",
        "sidebar_title": "설정", "lang_btn": "English Mode", "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일", "input_time": "태어난 시간", "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별", "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작", "loading": "천문 데이터 계산 및 신강/신약 정밀 판별 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report",
        "caption": "Authentic Saju Analysis System v13.3 (Logic Fixed)",
        "sidebar_title": "Settings", "lang_btn": "한국어 모드", "reset_btn": "Reset Session",
        "input_dob": "Date of Birth", "input_time": "Birth Time", "input_city": "Birth City (e.g., Seoul)",
        "input_gender": "Gender", "concern_label": "Describe your specific concern.",
        "submit_btn": "📜 Start Analysis", "loading": "Calculating Astral Data...",
        "warn_title": "Legal Disclaimer",
        "warn_text": "This analysis is for reference only. It does not replace professional advice.",
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
geolocator = Nominatim(user_agent="shinryeong_v13_3_final", timeout=10)
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
# 2. LOGIC ENGINE (Corrected for Kim Yong-jun Case)
# ==========================================
def analyze_logic_v13_3(saju_res):
    """
    Correctly identifies Identity, Strength (Sin-gang/Sin-yak), and Patterns.
    """
    # 1. Identity Extraction (CRITICAL FIX)
    # saju_engine v4.0 returns 'Day_Stem' explicitly. Use it.
    dm = saju_res['Day_Stem'] # e.g., '계' (Gye/Water)
    season = saju_res['Month_Branch'] # e.g., '오' (O/Fire)
    full_str = saju_res['Full_String']
    
    # 2. Element Mapping
    elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    branch_elem_map = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}
    
    my_elem = elem_map[dm] # e.g., '수' (Water)
    season_elem = branch_elem_map.get(season, '토') # e.g., '화' (Fire)
    
    # 3. Supporters Definition (My Element + Resource)
    # 수(Water) -> Supporters: 수(Water), 금(Metal)
    supporters = []
    if my_elem == '목': supporters = ['목', '수']
    elif my_elem == '화': supporters = ['화', '목']
    elif my_elem == '토': supporters = ['토', '화']
    elif my_elem == '금': supporters = ['금', '토']
    elif my_elem == '수': supporters = ['수', '금']
    
    # 4. Strength Calculation (Scoring System)
    score = 0
    
    # A. Season Check (Deuk-ryeong) - Most Important
    # 계수(Water) born in 오월(Fire/Summer) -> Not supported -> Score remains 0 or negative
    if season_elem in supporters: 
        score += 50 
    else:
        score -= 30 # Penalty for being born in hostile season (Sil-ryeong)
        
    # B. Quantity Check (Deuk-se)
    # Count how many characters in Full String support Me
    total_supporters = 0
    for char in full_str:
        if char == ' ': continue
        # Map char to element
        ce = '토' # Default
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "무기진술축미": ce = '토'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        
        if ce in supporters:
            total_supporters += 1
            
    score += (total_supporters * 10)
    
    # Final Diagnosis
    if score >= 40:
        strength = "신강(身强 - 주도적인 힘)"
        strength_desc = "주관이 뚜렷하고 환경을 리드하는 힘"
    else:
        strength = "신약(身弱 - 섬세하고 현실적)"
        strength_desc = "환경에 민감하게 반응하며 실리를 추구하는 지혜"

    # 5. Metaphor Generation (Identity)
    metaphor_db = {
        '갑': "곧게 뻗은 거목(Pioneer)", '을': "끈질긴 생명력의 화초(Survivor)", 
        '병': "만물을 비추는 태양(Visionary)", '정': "어둠을 밝히는 촛불(Mentor)",
        '무': "묵직한 태산(Guardian)", '기': "비옥한 대지(Cultivator)", 
        '경': "단단한 바위(Warrior)", '신': "예리한 보석(Specialist)",
        '임': "깊고 넓은 바다(Strategist)", '계': "스며드는 봄비(Intuitive)"
    }
    my_metaphor = metaphor_db.get(dm, "신비한 기운")

    # 6. Special Pattern (Wealth Check for Jae-da-sin-yak)
    # Wealth Element: What I control (e.g., Water controls Fire)
    wealth_map = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'}
    my_wealth_elem = wealth_map[my_elem]
    
    wealth_count = 0
    for char in full_str:
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "무기진술축미": ce = '토'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        if ce == my_wealth_elem: wealth_count += 1
        
    pattern = "일반격"
    pattern_desc = "오행의 흐름이 원만한 구조"
    
    if "신약" in strength and wealth_count >= 3:
        pattern = "재다신약(財多身弱)"
        pattern_desc = "재물 욕심과 기회는 많으나, 이를 혼자 감당하기엔 벅찬 구조. (부자 사주이나 관리가 필수)"
    elif "신강" in strength and wealth_count >= 3:
        pattern = "신왕재왕(身旺財旺)"
        pattern_desc = "능력과 재물이 모두 왕성하여 큰 부를 이루는 거부(巨富)의 명"

    return {
        "identity": dm,
        "element": my_elem,
        "metaphor": my_metaphor,
        "strength": strength,
        "strength_desc": strength_desc,
        "pattern": pattern,
        "pattern_desc": pattern_desc,
        "shinsal": ", ".join(saju_res['Shinsal']) if saju_res['Shinsal'] else "평온함",
        "pillars": full_str,
        "ten_gods": saju_res['Ten_Gods']
    }

def generate_ai_response(messages, lang_mode):
    # FIXED: Persona Injection - Force "Interpretation" not "Definition"
    sys_instruction = """
[CRITICAL INSTRUCTION]
Role: You are 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
Language: KOREAN ONLY.
Goal: Interpret the data deeply for the user's life, DO NOT just define terms.

[RULES FOR REPORT]
1. Identity: Start with the Metaphor (e.g., '그대는 한여름에 내리는 봄비와 같네'). Explain what this means for their personality (e.g., '뜨거운 열기를 식혀주는 소중한 존재이지').
2. Strength/Pattern: If 'Sin-yak', do NOT say "You are weak". Say "Sensitive and realistic (섬세하고 실리적)". If 'Jae-da-sin-yak', explain: "Money flows around you, but you need stamina to hold it."
3. Shinsal: Explain how 'Yeokma' or 'Dohwa' manifests in real life (e.g., "People are naturally drawn to you").
4. Visuals: Insert 

[Image of Five Elements Cycle]
 when explaining the balance of elements.
"""
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
    return "⚠️ 신령이 깊은 명상에 잠겨 응답하지 못했습니다. 다시 시도해주게."

# ==========================================
# 3. MAIN UI FLOW
# ==========================================
with st.sidebar:
    st.title("⚙️ 설정")
    if st.button("🔄 리셋"):
        st.session_state.clear()
        st.rerun()

t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption("음력/윤달 지원 & 정밀 분석 엔진 v13.3")
st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

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
            st.error("⚠️ 도시를 입력해주세요.")
        else:
            with st.spinner("⏳ 신령이 천문 데이터를 계산 중입니다..."):
                coords, city_name = get_coordinates(city)
                if not coords:
                    st.error(f"❌ '{city}' 위치 확인 불가.")
                else:
                    # 1. Lunar Convert
                    final_date = input_date
                    if is_lunar:
                        final_date = convert_lunar_to_solar(input_date.year, input_date.month, input_date.day, is_intercalary)
                        if not final_date:
                            st.error("❌ 날짜 변환 오류.")
                            st.stop()
                        st.info(f"ℹ️ 음력 {input_date} -> 양력 {final_date}")

                    # 2. Engine Call
                    saju_res = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                                               time_val.hour, time_val.minute, coords[0], coords[1])
                    
                    # 3. Logic & AI
                    facts = analyze_logic_v13_3(saju_res)
                    st.session_state.saju_data_dict = facts
                    st.session_state.raw_input_data = {"date": str(final_date), "concern": concern}
                    
                    sys_p = f"""
[CALCULATED DATA]
- Identity: {facts['metaphor']} (Day Master: {facts['identity']})
- Strength: {facts['strength']} ({facts['strength_desc']})
- Pattern: {facts['pattern']} ({facts['pattern_desc']})
- Shinsal: {facts['shinsal']}
- Pillars: {facts['pillars']}
- Concern: "{concern}"

[TASK]
Based on the data above, write a warm, insightful report in Korean (Hage-che).
Focus on interpreting the 'Pattern' ({facts['pattern']}) for the user's career/wealth.
"""
                    st.session_state.saju_context = sys_p
                    msgs = [{"role": "system", "content": sys_p}, 
                            {"role": "user", "content": "분석 보고서 작성."}]
                    
                    full_resp = generate_ai_response(msgs, st.session_state.lang)
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    st.session_state.analysis_complete = True
                    st.rerun()

else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        facts = st.session_state.saju_data_dict
        context_msg = f"""
[CONTEXT] User: {facts['metaphor']}. Pattern: {facts['pattern']}.
Question: "{q}"
Answer specifically using the data. Focus on practical advice.
"""
        msgs = [{"role": "system", "content": context_msg}, 
                {"role": "user", "content": q}]
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                full_resp = generate_ai_response(msgs, st.session_state.lang)
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
