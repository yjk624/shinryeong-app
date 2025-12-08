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
# 0. SYSTEM CONFIGURATION & UI TEXTS
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

# [CRITICAL FIX] UI_TEXT Definition Restored
UI_TEXT = {
    "ko": {
        "title": "🔮 신령 사주리포트",
        "caption": "정통 명리학 기반 데이터 분석 시스템 v13.2 (최종 수정)",
        "sidebar_title": "설정",
        "lang_btn": "English Mode",
        "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일",
        "input_time": "태어난 시간",
        "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별",
        "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작",
        "loading": "천문 데이터 계산 및 형이상학적 패턴 정밀 분석 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report",
        "caption": "Authentic Saju Analysis System v13.2 (Final Fixed)",
        "sidebar_title": "Settings",
        "lang_btn": "한국어 모드",
        "reset_btn": "Reset Session",
        "input_dob": "Date of Birth",
        "input_time": "Birth Time",
        "input_city": "Birth City (e.g., Seoul)",
        "input_gender": "Gender",
        "concern_label": "Describe your specific concern.",
        "submit_btn": "📜 Start Analysis",
        "loading": "Calculating Astral Data...",
        "warn_title": "Legal Disclaimer",
        "warn_text": "This analysis is for reference only. It does not replace professional advice.",
        "placeholder": "Ask follow-up questions..."
    }
}

# Initialize Session State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v13_2_final", timeout=10)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

# ==========================================
# 1. HELPER FUNCTIONS (Geo & Lunar)
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
# 2. LOGIC ENGINE (Fact Injection)
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

def analyze_logic_v13(saju_res):
    """
    Analyzes the Saju result from engine and prepares facts for AI.
    """
    dm = saju_res['Day_Stem']
    full_str = saju_res['Full_String']
    
    # 1. Metaphor
    metaphor_db = {
        '갑': "거목(Pioneer)", '을': "화초(Survivor)", '병': "태양(Visionary)", '정': "촛불(Mentor)",
        '무': "태산(Guardian)", '기': "대지(Cultivator)", '경': "바위(Warrior)", '신': "보석(Specialist)",
        '임': "바다(Strategist)", '계': "봄비(Intuitive)"
    }
    
    # 2. Shinsal Extraction from Engine
    shinsal_summary = ", ".join(saju_res['Shinsal']) if saju_res['Shinsal'] else "평온함"
    
    # 3. Strength Logic (Simplified for Demo)
    # In real deployment, calculate based on Element Counts
    strength = "신약(Sensitive)" if dm in ['계', '신', '을'] else "신강(Strong)"

    return {
        "identity": dm,
        "metaphor": metaphor_db.get(dm, "기운"),
        "strength": strength,
        "shinsal": shinsal_summary,
        "pillars": full_str,
        "ten_gods": saju_res['Ten_Gods']
    }

def generate_ai_response(messages, lang_mode):
    sys_instruction = """
[CRITICAL RULE] You are 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
Language: KOREAN ONLY. No German/English words in output.
Format: Use the provided JSON data. 
Visuals: Insert 

[Image of Five Elements Cycle]
 when explaining balance.
Task: Write a detailed report. Explain terms like '신강', '재다신약', '도화살' simply.
"""
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
    return "⚠️ 신령이 응답하지 못했습니다."

# ==========================================
# 3. MAIN UI FLOW
# ==========================================
with st.sidebar:
    st.title("⚙️ 설정")
    if st.button("🔄 리셋"):
        st.session_state.clear()
        st.rerun()

# [FIX] UI_TEXT is now defined, so this will work.
t = UI_TEXT[st.session_state.lang] 
st.title(t["title"])
st.caption(t["caption"])
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
                    facts = analyze_logic_v13(saju_res)
                    st.session_state.saju_data_dict = facts
                    st.session_state.raw_input_data = {"date": str(final_date), "concern": concern}
                    
                    sys_p = f"""
[DATA]
Identity: {facts['metaphor']} (DM: {facts['identity']})
Strength: {facts['strength']}
Shinsal: {facts['shinsal']}
Pillars: {facts['pillars']}
Concern: "{concern}"
[TASK] Write detailed report in Korean (Hage-che).
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
[CONTEXT] User: {facts['metaphor']}. Pillars: {facts['pillars']}.
Question: "{q}"
Answer specifically using the data.
"""
        msgs = [{"role": "system", "content": context_msg}, 
                {"role": "user", "content": q}]
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                full_resp = generate_ai_response(msgs, st.session_state.lang)
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
