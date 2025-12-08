import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="신령 (Shinryeong)", page_icon="🔮", layout="centered")
geolocator = Nominatim(user_agent="shinryeong_app_final_kr", timeout=10)

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

# Session State
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "user_info_logged" not in st.session_state: st.session_state.user_info_logged = False
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

# ==========================================
# 2. FILE LOADERS
# ==========================================
@st.cache_data
def load_text_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f: return f.read()
    except: return ""

PROMPT_TEXT = load_text_file("prompt.txt")
KNOWLEDGE_TEXT = load_text_file("knowledgebase.txt")

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "대전": (36.35, 127.38), "광주": (35.15, 126.85), 
    "울산": (35.53, 129.31), "세종": (36.48, 127.28), "창원": (35.22, 128.68),
    "제주": (33.49, 126.53), "New York": (40.71, -74.00), "Tokyo": (35.67, 139.65)
}

def get_coordinates(city_input):
    clean = city_input.strip()
    if clean in CITY_DB: return CITY_DB[clean], clean
    for k, v in CITY_DB.items():
        if k in clean or k.lower() in clean.lower(): return v, k
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def save_to_database(user_data, birth_date_obj, birth_time_obj, concern, is_lunar):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        sheet = client.open("Shinryeong_User_Data").sheet1
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{birth_date_obj} ({'Lunar' if is_lunar else 'Solar'})",
            str(birth_time_obj),
            str(user_data.get('Birth_Place', 'Unknown')),
            user_data.get('Gender', 'Unknown'),
            user_data.get('Year', ''), user_data.get('Month', ''), 
            user_data.get('Day', ''), user_data.get('Time', ''),
            concern
        ])
    except: pass

def generate_ai_response(messages):
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.4, max_tokens=5000, stream=True
            )
            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    c = chunk.choices[0].delta.content
                    full_response += c
                    yield c
            return
        except: continue
    yield "⚠️ System Busy. Please try again."

# ==========================================
# 4. UI LOGIC
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)", "subtitle": "AI 정통 명리학 분석가",
        "warning": "⚖️ 본 분석은 명리학적 통계에 기반한 학술적 자료입니다.",
        "submit_btn": "🔮 정밀 분석 시작", "loading": "⏳ 사주 명식을 분석 중입니다...",
        "geo_error": "⚠️ 위치를 확인할 수 없습니다.", "chat_placeholder": "추가 질문을 입력하세요...",
        "reset_btn": "🔄 새로하기", "dob": "생년월일", "time": "태어난 시간",
        "gender": "성별", "loc": "태어난 지역", "concern": "고민 내용 (비워두면 종합 운세 분석)",
        "cal": "양력/음력"
    },
    "en": {
        "title": "🔮 Shinryeong", "subtitle": "AI Metaphysical Analyst",
        "warning": "⚖️ Academic analysis based on Saju.",
        "submit_btn": "🔮 Analyze", "loading": "⏳ Analyzing...",
        "geo_error": "⚠️ Location not found.", "chat_placeholder": "Follow-up question...",
        "reset_btn": "🔄 Reset", "dob": "Date of Birth", "time": "Time",
        "gender": "Gender", "loc": "Birth Place", "concern": "Concern (Leave empty for general)",
        "cal": "Calendar"
    }
}

with st.sidebar:
    lang = "ko" if st.radio("Language", ["한국어", "English"]) == "한국어" else "en"
    t = TRANS[lang]
    if st.button(t["reset_btn"]):
        st.session_state.clear()
        st.rerun()

st.title(t["title"])
st.caption(t["subtitle"])
st.info(t["warning"])

# --- INPUT FORM ---
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        with c1:
            b_date = st.date_input(t["dob"], min_value=datetime(1940,1,1))
            b_time = st.time_input(t["time"], value=time(12,0), step=60)
            cal = st.radio(t["cal"], ["양력 (Solar)", "음력 (Lunar)"])
        with c2:
            gender = st.radio(t["gender"], ["남성 (Male)", "여성 (Female)"])
            loc = st.text_input(t["loc"], placeholder="Seoul, Busan...")
        q_input = st.text_area(t["concern"], height=100)
        submitted = st.form_submit_button(t["submit_btn"])

    if submitted:
        if not loc:
            st.error(t["geo_error"])
        else:
            with st.spinner(t["loading"]):
                coords, matched_city = get_coordinates(loc)
                if coords:
                    # 1. Logic Setup
                    is_lunar = "음력" in cal
                    saju = calculate_saju_v3(b_date.year, b_date.month, b_date.day, 
                                           b_time.hour, b_time.minute, coords[0], coords[1], is_lunar)
                    saju['Birth_Place'] = matched_city if matched_city else loc
                    saju['Gender'] = gender
                    
                    # Handle Empty Question
                    final_q = q_input if q_input.strip() else "나의 전반적인 사주 기질과 2025년 종합 운세 흐름"
                    
                    # 2. System Prompt
                    sys_p = f"""
                    [SYSTEM ROLE]
                    Act as 'Shinryeong'. Speak strictly in Korean (Hage-che style: ~하네, ~이라네).
                    NO ENGLISH in output.
                    
                    [KNOWLEDGE]
                    {KNOWLEDGE_TEXT[:3000]}
                    
                    [USER DATA]
                    - Day Master (User): {saju['Day']}
                    - Structure: Year({saju['Year']}), Month({saju['Month']}), Time({saju['Time']})
                    - Concern: "{final_q}"
                    
                    [FORMAT INSTRUCTIONS]
                    Do NOT output the data table. Start directly with Section 1.
                    Use these icons: 🔮, 🗡️, 👁️, ☁️, ⚡, 🛡️.
                    
                    ### 🔮 1. 타고난 명(命)과 기질
                    (Analyze the Day Master & Season. Use nature metaphors.)
                    
                    ### 🗡️ 2. 특별한 능력과 직업 (재능 매핑)
                    (Analyze Sipseong/Ten Gods. Explain what 'Shik-sin' or 'Pyun-gwan' means in Korean terms.)
                    
                    ### 👁️ 3. 신령의 공명 (Accuracy Check)
                    (Ask a question about a past event based on a recent clash year.)
                    
                    ### ☁️ 4. 가까운 미래의 흐름
                    (Predict 2025/2026 energy flow.)
                    
                    ### ⚡ 5. 당신의 고민에 대한 신령의 해답
                    (Answer: "{final_q}")
                    
                    ### 🛡️ 6. 신령의 처방
                    (Actionable advice.)
                    
                    [[TECHNICAL_SECTION]]
                    (Explain technical logic.)
                    """
                    
                    st.session_state.saju_context = sys_p
                    st.session_state.user_q = final_q
                    st.session_state.saju_data = saju
                    st.session_state.analysis_complete = True # Unlock Chat
                    
                    # 3. Generate Initial Report
                    msgs = [{"role": "system", "content": sys_p}, {"role": "user", "content": "Analyze now."}]
                    
                    # Store User's "Invisible" prompt to history
                    st.session_state.messages.append({"role": "user", "content": f"사주 분석 요청: {final_q}"})
                    
                    # Stream Response
                    full_text = ""
                    response_container = st.empty() # Placeholder for streaming
                    
                    # Render Table MANUALLY first (Python Side)
                    table_md = f"""
                    ### 📜 신령의 분석 보고서
                    | 구분 | 내용 |
                    | :--- | :--- |
                    | **생년월일** | {b_date} ({cal}) |
                    | **태어난 시간** | {b_time} |
                    | **태어난 곳** | {saju['Birth_Place']} |
                    | **성별** | {gender} |
                    | **사주(간지)** | {saju['Year']} (년) / {saju['Month']} (월) / {saju['Day']} (일) / {saju['Time']} (시) |
                    | **분석 주제** | {final_q} |
                    
                    ---
                    """
                    st.markdown(table_md)
                    
                    # Stream AI
                    for chunk in generate_ai_response(msgs):
                        full_text += chunk
                        # We don't stream to container here to avoid overwriting the table immediately
                    
                    # Split and Save
                    if "[[TECHNICAL_SECTION]]" in full_text:
                        main_r, tech_r = full_text.split("[[TECHNICAL_SECTION]]")
                    else:
                        main_r, tech_r = full_text, "분석 로직 포함."
                        
                    st.markdown(main_r)
                    with st.expander("📚 분석 근거 (Technical Basis)"):
                        st.markdown(tech_r)
                        
                    st.session_state.messages.append({"role": "assistant", "content": table_md + main_r, "theory": tech_r})
                    
                    if not st.session_state.user_info_logged:
                        save_to_database(saju, b_date, b_time, final_q, is_lunar)
                        st.session_state.user_info_logged = True
                        
                    st.rerun() # Force UI refresh to show chat input
                else:
                    st.error(t["geo_error"])

# --- CHAT MODE ---
else:
    # Render History
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "theory" in m:
                with st.expander("📚 분석 근거"):
                    st.markdown(m["theory"])
    
    # Input
    if p := st.chat_input(t["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        msgs = [{"role": "system", "content": st.session_state.saju_context}]
        for m in st.session_state.messages[-4:]:
            msgs.append({"role": m["role"], "content": m["content"]})
            
        with st.chat_message("assistant"):
            full_resp = ""
            resp_container = st.empty()
            for chunk in generate_ai_response(msgs):
                full_resp += chunk
                resp_container.markdown(full_resp + "▌")
            
            if "[[TECHNICAL_SECTION]]" in full_resp:
                main_r, tech_r = full_resp.split("[[TECHNICAL_SECTION]]")
            else:
                main_r, tech_r = full_resp, ""
                
            resp_container.markdown(main_r)
            if tech_r:
                with st.expander("📚 분석 근거"):
                    st.markdown(tech_r)
            
            st.session_state.messages.append({"role": "assistant", "content": main_r, "theory": tech_r})
