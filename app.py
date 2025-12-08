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
geolocator = Nominatim(user_agent="shinryeong_app_v13_pro_master", timeout=10)

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
# 2. FILE LOADERS (Optimized)
# ==========================================
@st.cache_data
def load_text_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

# Load Prompts
PROMPT_TEXT = load_text_file("prompt.txt")
KNOWLEDGE_TEXT = load_text_file("knowledgebase.txt")

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
CITY_DB = {
    # Major Global Cities for Instant Fallback
    "서울": (37.56, 126.97), "Seoul": (37.56, 126.97),
    "부산": (35.17, 129.07), "Busan": (35.17, 129.07),
    "인천": (37.45, 126.70), "Incheon": (37.45, 126.70),
    "대구": (35.87, 128.60), "Daegu": (35.87, 128.60),
    "대전": (36.35, 127.38), "Daejeon": (36.35, 127.38),
    "광주": (35.15, 126.85), "Gwangju": (35.15, 126.85),
    "제주": (33.49, 126.53), "Jeju": (33.49, 126.53),
    "창원": (35.22, 128.68), "Changwon": (35.22, 128.68),
    "New York": (40.71, -74.00), "London": (51.50, -0.12),
    "Paris": (48.85, 2.35), "Tokyo": (35.67, 139.65),
    "Los Angeles": (34.05, -118.24), "Sydney": (-33.86, 151.20)
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

def generate_ai_response(messages):
    """
    Priority: Llama 3.3 (Genius) -> Mixtral (Large Memory) -> Llama 3.1 (Backup)
    """
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
    
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6,
                max_tokens=4500, # Allow for long, detailed reports
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
            return # Success
        except Exception as e:
            # If rate limit or size error, try next model
            print(f"⚠️ Model {model} failed: {e}")
            continue
            
    yield "⚠️ System Busy: All AI models are currently overloaded. Please try again in 1 minute."

# ==========================================
# 4. UI LAYOUT
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 정통 명리학 분석가",
        "warning": "⚖️ 본 분석은 명리학적 통계에 기반한 학술적 자료이며, 법률/의학적 조언이 아닙니다.",
        "submit_btn": "🔮 신령에게 정밀 분석 요청하기",
        "loading": "⏳ 천문 데이터를 분석하고 신령을 소환하는 중...",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. (예: 서울, 창원, 뉴욕)",
        "chat_placeholder": "추가로 궁금한 점이 있으신가요?",
        "reset_btn": "🔄 새로운 분석",
        "dob_label": "생년월일", "time_label": "태어난 시간", "gender_label": "성별",
        "male": "남성", "female": "여성", "loc_label": "태어난 지역 (구체적 지명 입력 가능)",
        "concern_label": "가장 큰 고민은 무엇인가요?",
        "cal_label": "양력/음력 구분",
        "theory_header": "📚 분석 근거 (Technical Basis)"
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        "warning": "⚖️ Academic analysis based on Saju data. Not legal/medical advice.",
        "submit_btn": "🔮 Request Deep Analysis",
        "loading": "⏳ Analyzing celestial data...",
        "geo_error": "⚠️ Location not found.",
        "chat_placeholder": "Follow-up questions?",
        "reset_btn": "🔄 New Analysis",
        "dob_label": "Date of Birth", "time_label": "Time of Birth", "gender_label": "Gender",
        "male": "Male", "female": "Female", "loc_label": "Birth Place",
        "concern_label": "Main Concern",
        "cal_label": "Calendar",
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
    st.caption("Engine: Llama-3.3 (Genius)")

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
            loc_in = st.text_input(txt["loc_label"], placeholder="Seoul, Busan, New York...")
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
                    
                    # ----------------------------------------------------
                    # ULTIMATE SYSTEM PROMPT (The Soul of the App)
                    # ----------------------------------------------------
                    # We inject the "Persona" and "Structure" forcefully.
                    
                    current_year = datetime.now().year
                    
                    system_prompt = f"""
                    [SYSTEM ROLE]
                    You are 'Shinryeong' (신령). You are a master of Saju Myeongli.
                    Tone: Authoritative, Mystical, yet Logical (Hage-che / 하게체).
                    Language: {lang_code.upper()} Only.
                    
                    [KNOWLEDGE BASE OVERVIEW]
                    {KNOWLEDGE_TEXT[:4000]} 
                    (Note: Knowledge condensed to save memory. Use general Saju logic for details.)
                    
                    [USER DATA]
                    - Saju: {saju}
                    - Gender: {gender}
                    - Location: {city_name}
                    - Calendar: {cal_type}
                    - Concern: "{q}"
                    - Current Year: {current_year}
                    
                    [CRITICAL INSTRUCTION: COLD READING]
                    You MUST prove your accuracy. Look at the User's Year/Day Pillars.
                    Find a recent year (e.g., 2022, 2023, 2024) where there was a 'Clash' (Chung) or 'Combination' (Hap) with their Day Master.
                    Then, in Section 2, ask a SPECIFIC question like:
                    "Did you experience a separation or job change in [Year] due to the [Clash Name] energy?"
                    
                    [OUTPUT FORMAT TEMPLATE]
                    Start exactly with this Markdown table:
                    | 구분 | 내용 |
                    | :--- | :--- |
                    | **생년월일** | {b_date} ({cal_type}) |
                    | **사주(간지)** | {saju['Year']} / {saju['Month']} / {saju['Day']} / {saju['Time']} |
                    | **분석 주제** | {q} |
                    
                    ---
                    
                    ### 🔮 1. 타고난 명(命)과 기질
                    (Analyze the 4 Pillars deeply. Use metaphors like "Lonely Pine Tree" or "Raging Ocean". Bold key terms.)
                    
                    ### 👁️ 2. 신령의 공명 (Accuracy Check)
                    (Perform the Cold Reading here. Ask the specific question about a past event to prove accuracy.)
                    
                    ### ⚡ 3. 흐름과 리스크 (Solution)
                    (Directly answer the user's concern "{q}". Be sharp and honest.)
                    
                    ### 🛡️ 4. 신령의 처방 (Action Plan)
                    * **행동:** ...
                    * **마음가짐:** ...
                    * **개운법:** ...
                    
                    [[TECHNICAL_SECTION]]
                    (Explain the technical derivation: "This analysis is based on the clash between Water and Fire in the Month Pillar...")
                    """
                    
                    st.session_state.saju_context = system_prompt
                    
                    msgs = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze my Saju deeply. My concern is: {q}"}
                    ]
                    
                    response_container = st.empty()
                    full_text = ""
                    
                    for chunk in generate_ai_response(msgs):
                        full_text += chunk
                        response_container.markdown(full_text + "▌")
                    
                    response_container.empty()
                    if "[[TECHNICAL_SECTION]]" in full_text:
                        parts = full_text.split("[[TECHNICAL_SECTION]]")
                        main_r, theory_r = parts[0], parts[1]
                    else:
                        main_r, theory_r = full_text, "Analysis based on standard Saju logic."

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
        
        # Optimize context for chat
        msgs = [{"role": "system", "content": st.session_state.saju_context}]
        for m in st.session_state.messages[-2:]: # Keep history short to avoid 429 Error
            msgs.append({"role": m["role"], "content": m["content"]})
            
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_text = ""
            for chunk in generate_ai_response(msgs):
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
