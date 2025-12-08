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

# Robust Geocoding
geolocator = Nominatim(user_agent="shinryeong_app_v12_smart_compress", timeout=10)

# Initialize Groq
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

# ==========================================
# 2. FILE LOADERS
# ==========================================
@st.cache_data
def load_text_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

PROMPT_TEXT = load_text_file("prompt.txt")
KNOWLEDGE_TEXT = load_text_file("knowledgebase.txt")

# ==========================================
# 3. HELPER FUNCTIONS & SMART AI ENGINE
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "Seoul": (37.56, 126.97),
    "부산": (35.17, 129.07), "Busan": (35.17, 129.07),
    "대구": (35.87, 128.60), "Daegu": (35.87, 128.60),
    "인천": (37.45, 126.70), "Incheon": (37.45, 126.70),
    "광주": (35.15, 126.85), "Gwangju": (35.15, 126.85),
    "대전": (36.35, 127.38), "Daejeon": (36.35, 127.38),
    "울산": (35.53, 129.31), "Ulsan": (35.53, 129.31),
    "제주": (33.49, 126.53), "Jeju": (33.49, 126.53),
    "New York": (40.71, -74.00), "London": (51.50, -0.12),
    "Paris": (48.85, 2.35), "Tokyo": (35.67, 139.65)
}

def get_coordinates(city_input):
    clean = city_input.strip()
    if clean in CITY_DB: return CITY_DB[clean], clean
    for city_key, coords in CITY_DB.items():
        if city_key in clean or city_key.lower() in clean.lower():
            return coords, city_key 
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def save_to_database(user_data, birth_date_obj, birth_time_obj, concern, is_lunar):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gs_client = gspread.authorize(creds)
        sheet = gs_client.open("Shinryeong_User_Data").sheet1
        cal_type = "Lunar" if is_lunar else "Solar"
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{birth_date_obj.strftime('%Y-%m-%d')} ({cal_type})",
            birth_time_obj.strftime("%H:%M"),
            str(user_data.get('Birth_Place', 'Unknown')),
            user_data.get('Gender', 'Unknown'),
            user_data.get('Year', ''),
            user_data.get('Month', ''),
            user_data.get('Day', ''),
            user_data.get('Time', ''),
            concern
        ]
        sheet.append_row(row)
    except: pass

# [SMART ENGINE SWITCHER WITH COMPRESSION]
def generate_ai_response(messages_full, messages_lite=None):
    """
    Tries heavy model with full context first.
    If fails, tries backup model with full context.
    If fails (size error), tries small model with LITE context.
    """
    
    # Priority 1: Smartest (Hit limit?)
    # Priority 2: Large Context Backup (Mixtral)
    # Priority 3: Fast/Small (Requires Lite Context)
    
    plan = [
        ("llama-3.3-70b-versatile", messages_full),
        ("mixtral-8x7b-32768", messages_full),
        ("llama-3.1-8b-instant", messages_lite if messages_lite else messages_full) 
    ]
    
    for model_name, msgs_to_use in plan:
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=msgs_to_use,
                temperature=0.6,
                max_tokens=2500,
                top_p=1,
                stream=True,
                stop=None,
            )
            
            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            return # Success!
            
        except Exception as e:
            error_msg = str(e)
            # Log error but keep trying next model
            print(f"⚠️ Model {model_name} failed: {error_msg}")
            
            # If we are at the last model and it failed, yield error
            if model_name == plan[-1][0]:
                yield f"System Overload. Please try again in 1 minute. (Error: {error_msg})"
                return

# ==========================================
# 4. UI LAYOUT
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가",
        "warning": """
        ⚖️ **법적 면책 조항 (Disclaimer):**
        1. 본 서비스는 명리학 및 자미두수 데이터를 기반으로 한 **학술적 분석**이며, 절대적인 예언이 아닙니다.
        2. 신령은 **의학적 진단(Medical Diagnosis)이나 법률적 조언(Legal Advice)**을 제공하지 않습니다.
        3. 본 분석 결과에 따른 사용자의 결정과 그 결과에 대한 책임은 전적으로 **사용자 본인**에게 있습니다.
        """,
        "submit_btn": "🔮 신령에게 분석 요청하기",
        "loading": "⏳ 천문 데이터를 계산하고 신령을 소환하는 중...",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. 주요 도시명으로 다시 시도해주세요.",
        "chat_placeholder": "추가로 궁금한 점이 있으신가요? (예: 내년의 재물운은?)",
        "reset_btn": "🔄 새로운 분석 시작",
        "dob_label": "생년월일", "time_label": "태어난 시간", "gender_label": "성별",
        "male": "남성", "female": "여성", "loc_label": "태어난 지역 (도시명)",
        "concern_label": "현재 가장 큰 고민은 무엇인가요?",
        "cal_label": "양력/음력 구분",
        "theory_header": "📚 분석 근거 (Technical Basis)"
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        "warning": """
        ⚖️ **Legal Disclaimer:**
        1. This service provides **academic analysis** based on Saju and Jami Dou Shu data; it is not absolute prophecy.
        2. Shinryeong does **NOT provide Medical Diagnoses or Legal Advice**.
        3. The user bears full responsibility for any decisions made based on this analysis.
        """,
        "submit_btn": "🔮 Request Analysis",
        "loading": "⏳ Calculating celestial data...",
        "geo_error": "⚠️ Location not found. Please try a major city.",
        "chat_placeholder": "Follow-up questions?",
        "reset_btn": "🔄 Start New Analysis",
        "dob_label": "Date of Birth", "time_label": "Time of Birth", "gender_label": "Gender",
        "male": "Male", "female": "Female", "loc_label": "Birth Place (City)",
        "concern_label": "What is your main concern?",
        "cal_label": "Calendar Type",
        "theory_header": "📚 Technical Basis"
    }
}

with st.sidebar:
    lang_code = "ko" if st.radio("Language / 언어", ["한국어", "English"]) == "한국어" else "en"
    txt = TRANS[lang_code]
    if st.button(txt["reset_btn"]):
        st.session_state.messages = []
        st.session_state.saju_context = ""
        st.session_state.user_info_logged = False
        st.rerun()
    st.caption("Engine: Groq Auto-Switch")

st.title(txt["title"])
st.caption(txt["subtitle"])
st.info(txt["warning"])

# ==========================================
# 5. MAIN LOGIC
# ==========================================
if not st.session_state.saju_context:
    with st.form("input"):
        col1, col2 = st.columns(2)
        with col1:
            b_date = st.date_input(txt["dob_label"], min_value=datetime(1940,1,1))
            b_time = st.time_input(txt["time_label"], value=time(12,00), step=60)
            cal_type = st.radio(txt["cal_label"], ["양력 (Solar)", "음력 (Lunar)"])
        with col2:
            gender = st.radio(txt["gender_label"], [txt["male"], txt["female"]])
            loc_in = st.text_input(txt["loc_label"], placeholder="Seoul, Busan...")
        q = st.text_area(txt["concern_label"], height=100)
        submitted = st.form_submit_button(txt["submit_btn"])

    if submitted:
        if not loc_in:
            st.error(txt["geo_error"])
        else:
            with st.spinner(txt["loading"]):
                coords, matched_city = get_coordinates(loc_in)
                
                if coords:
                    lat, lon = coords
                    is_lunar = True if "음력" in cal_type else False
                    city_name = matched_city if matched_city else loc_in
                    
                    saju = calculate_saju_v3(b_date.year, b_date.month, b_date.day, 
                                           b_time.hour, b_time.minute, lat, lon, is_lunar)
                    saju['Birth_Place'] = city_name
                    saju['Gender'] = gender
                    
                    # CSV Format
                    csv_display = f"""
                    | Parameter | Value |
                    | :--- | :--- |
                    | **Date** | {b_date} ({cal_type}) |
                    | **Time** | {b_time} |
                    | **Location** | {city_name} |
                    | **Gender** | {gender} |
                    | **Saju** | {saju['Year']} / {saju['Month']} / {saju['Day']} / {saju['Time']} |
                    """
                    
                    # 1. FULL PROMPT (Heavy)
                    system_prompt_full = f"""
                    [SYSTEM ROLE]
                    You are 'Shinryeong' (신령). Speak in 'Hage-che'.
                    Language: {lang_code.upper()} Only.
                    
                    [KNOWLEDGE BASE]
                    {KNOWLEDGE_TEXT}
                    
                    [USER DATA]
                    - Saju: {saju}
                    - Gender: {gender}
                    - Concern: "{q}"
                    
                    [OUTPUT TEMPLATE]
                    ### 📜 신령의 분석 보고서
                    {csv_display}
                    ---
                    ### [Icon] 1. 타고난 기질과 에너지
                    ### [Icon] 2. 🔍 신령의 공명 (Accuracy Check)
                    ### [Icon] 3. ⚡ 현재의 흐름과 리스크
                    ### [Icon] 4. 🛡️ 신령의 처방
                    [[TECHNICAL_SECTION]]
                    """
                    
                    # 2. LITE PROMPT (Lightweight - For 8B fallback)
                    # We remove the huge KNOWLEDGE_TEXT to fit the 6k token limit
                    system_prompt_lite = f"""
                    [SYSTEM ROLE]
                    You are 'Shinryeong' (신령). Speak in 'Hage-che'.
                    Language: {lang_code.upper()} Only.
                    
                    [USER DATA]
                    - Saju: {saju}
                    - Gender: {gender}
                    - Concern: "{q}"
                    
                    [OUTPUT TEMPLATE]
                    ### 📜 신령의 분석 보고서 (Lite Version)
                    {csv_display}
                    ---
                    ### [Icon] 1. 타고난 기질과 에너지
                    ### [Icon] 2. 🔍 신령의 공명 (Accuracy Check)
                    ### [Icon] 3. ⚡ 현재의 흐름과 리스크
                    ### [Icon] 4. 🛡️ 신령의 처방
                    [[TECHNICAL_SECTION]]
                    """
                    
                    st.session_state.saju_context = system_prompt_full
                    st.session_state.saju_context_lite = system_prompt_lite
                    
                    msgs_full = [{"role": "system", "content": system_prompt_full}, {"role": "user", "content": f"Analyze my Saju. Concern: {q}"}]
                    msgs_lite = [{"role": "system", "content": system_prompt_lite}, {"role": "user", "content": f"Analyze my Saju. Concern: {q}"}]
                    
                    response_container = st.empty()
                    full_text = ""
                    
                    for chunk in generate_ai_response(msgs_full, msgs_lite):
                        full_text += chunk
                        response_container.markdown(full_text + "▌")
                    
                    response_container.empty()
                    if "[[TECHNICAL_SECTION]]" in full_text:
                        parts = full_text.split("[[TECHNICAL_SECTION]]")
                        main_r, theory_r = parts[0], parts[1]
                    else:
                        main_r, theory_r = full_text, "Technical analysis provided in main text."

                    st.markdown(main_r)
                    with st.expander(txt["theory_header"]):
                        st.markdown(theory_r)

                    st.session_state.messages.append({"role": "user", "content": q})
                    st.session_state.messages.append({"role": "assistant", "content": main_r, "theory": theory_r})
                    
                    if not st.session_state.user_info_logged:
                        save_to_database(saju, b_date, b_time, q, is_lunar)
                        st.session_state.user_info_logged = True
                else:
                    st.error(txt["geo_error"])
else:
    st.markdown("---")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "theory" in m:
                with st.expander(txt["theory_header"]):
                    st.markdown(m["theory"])
            
    if p := st.chat_input(txt["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        # Prepare context
        msgs_full = [{"role": "system", "content": st.session_state.saju_context}]
        msgs_lite = [{"role": "system", "content": st.session_state.get("saju_context_lite", st.session_state.saju_context)}]
        
        for m in st.session_state.messages[-4:]:
            msgs_full.append({"role": m["role"], "content": m["content"]})
            msgs_lite.append({"role": m["role"], "content": m["content"]})
            
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_text = ""
            for chunk in generate_ai_response(msgs_full, msgs_lite):
                full_text += chunk
                response_container.markdown(full_text + "▌")
            
            response_container.empty()
            if "[[TECHNICAL_SECTION]]" in full_text:
                parts = full_text.split("[[TECHNICAL_SECTION]]")
                main_r, theory_r = parts[0], parts[1]
            else:
                main_r, theory_r = full_text, ""
                
            st.markdown(main_r)
            if theory_r:
                with st.expander(txt["theory_header"]):
                    st.markdown(theory_r)
                    
            st.session_state.messages.append({"role": "assistant", "content": main_r, "theory": theory_r})
