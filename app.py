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

# Robust Geocoding with Unique User Agent
geolocator = Nominatim(user_agent="shinryeong_app_v8_final_pro", timeout=10)

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
# 3. SMART LOCATION ENGINE
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "Seoul": (37.56, 126.97),
    "부산": (35.17, 129.07), "Busan": (35.17, 129.07),
    "인천": (37.45, 126.70), "Incheon": (37.45, 126.70),
    "대구": (35.87, 128.60), "Daegu": (35.87, 128.60),
    "대전": (36.35, 127.38), "Daejeon": (36.35, 127.38),
    "광주": (35.15, 126.85), "Gwangju": (35.15, 126.85),
    "울산": (35.53, 129.31), "Ulsan": (35.53, 129.31),
    "세종": (36.48, 127.28), "Sejong": (36.48, 127.28),
    "창원": (35.22, 128.68), "Changwon": (35.22, 128.68),
    "수원": (37.26, 127.02), "Suwon": (37.26, 127.02),
    "제주": (33.49, 126.53), "Jeju": (33.49, 126.53),
    "강릉": (37.75, 128.87), "Gangneung": (37.75, 128.87),
    "New York": (40.71, -74.00), "London": (51.50, -0.12),
    "Paris": (48.85, 2.35), "Tokyo": (35.67, 139.65)
}

def get_coordinates(city_input):
    """
    Smart Logic:
    1. Try Exact Geocoding (Best accuracy).
    2. If fails, check if input *contains* a major city name (e.g. "Changwon Hospital" -> Match "Changwon").
    3. Return fallback if nothing found.
    """
    clean_input = city_input.strip()
    
    # 1. Try Exact API Call
    try:
        loc = geolocator.geocode(clean_input)
        if loc: 
            return (loc.latitude, loc.longitude), clean_input
    except:
        pass # If API blocks/fails, fall through to smart match
    
    # 2. Smart Substring Match (The Fix for "Changwon Fatima Hospital")
    # We check if any key in our DB exists inside the user's input string.
    for city_key, coords in CITY_DB.items():
        if city_key in clean_input or city_key.lower() in clean_input.lower():
            return coords, city_key # Return the matched major city coords
            
    return None, None

# ==========================================
# 4. DATABASE & AI ENGINE
# ==========================================
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
    except:
        pass

def generate_ai_response(messages):
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.5,
            max_tokens=3500,
            top_p=1,
            stream=True,
            stop=None,
        )
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
        return full_response
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 5. UI LAYOUT
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
        "loading": "⏳ 위성 좌표를 수신하고 신령을 소환하는 중...",
        "geo_error": "⚠️ 위치를 확인할 수 없습니다. 도시 이름을 정확히 입력해주세요.",
        "chat_placeholder": "추가로 궁금한 점이 있으신가요? (예: 내년의 재물운은?)",
        "reset_btn": "🔄 새로운 분석 시작",
        "dob_label": "생년월일", "time_label": "태어난 시간", "gender_label": "성별",
        "male": "남성", "female": "여성", "loc_label": "태어난 장소 (예: 창원 파티마병원, 서울 강남구)",
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
        "loading": "⏳ Geocoding location and calculating destiny...",
        "geo_error": "⚠️ Location not found.",
        "chat_placeholder": "Follow-up questions?",
        "reset_btn": "🔄 New Analysis",
        "dob_label": "Date of Birth", "time_label": "Time of Birth", "gender_label": "Gender",
        "male": "Male", "female": "Female", "loc_label": "Birth Place (e.g., New York, Seoul)",
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
        st.session_state.saju_context = {}
        st.session_state.user_info_logged = False
        st.rerun()
    st.caption("Engine: Groq Llama-3.3")

st.title(txt["title"])
st.caption(txt["subtitle"])
st.info(txt["warning"])

# ==========================================
# 6. MAIN LOGIC
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
                # 1. SMART GEOCODING
                coords, matched_city_name = get_coordinates(loc_in)
                
                if coords:
                    lat, lon = coords
                    is_lunar = True if "음력" in cal_type else False
                    
                    # 2. CALCULATE MATH
                    saju = calculate_saju_v3(b_date.year, b_date.month, b_date.day, 
                                           b_time.hour, b_time.minute, lat, lon, is_lunar)
                    saju['Birth_Place'] = matched_city_name # Store the clean name (e.g. "Changwon")
                    saju['Gender'] = gender
                    
                    # 3. HIGH-FIDELITY PROMPT CONSTRUCTION
                    # We paste the "Ideal Response Structure" directly into the instruction.
                    system_prompt = f"""
                    [SYSTEM ROLE]
                    You are 'Shinryeong'. You MUST speak in 'Hage-che' (하게체).
                    Language: {lang_code.upper()} Only.
                    
                    [KNOWLEDGE BASE]
                    {KNOWLEDGE_TEXT}
                    
                    [USER DATA - DO NOT ASK FOR THIS AGAIN]
                    - Saju: {saju['Year']} (Year), {saju['Month']} (Month), {saju['Day']} (Day), {saju['Time']} (Time)
                    - Gender: {gender}
                    - Location: {matched_city_name} (Lat: {lat}, Lon: {lon})
                    - Concern: "{q}"
                    
                    [REQUIRED OUTPUT FORMAT]
                    You must follow this EXACT structure. Use emojis.
                    
                    1. 🔮 타고난 에너지 (기질 분석)
                       - Explain the 4 Pillars (Year/Month/Day/Time) using nature metaphors.
                       - Use the specific Ganji chars (e.g., 甲, 寅) provided in User Data.
                    
                    2. ⚡ 현재의 흐름과 리스크 (운세 분석)
                       - Analyze the current situation based on the user's concern.
                    
                    3. 🛡️ 신령의 처방 (Action Plan)
                       - 행동 지침 (Action Guide)
                       - 마음가짐 (Mindset)
                       - 개운 아이템 (Lucky Item/Color/Direction)
                    
                    [[TECHNICAL_SECTION]]
                    (Here, explain the technical 'Ten Gods' or 'Shensha' logic used above.)
                    """
                    
                    st.session_state.saju_context = system_prompt
                    
                    msgs = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze my Saju. My concern is: {q}"}
                    ]
                    
                    full_text = generate_ai_response(msgs)
                    
                    if "[[TECHNICAL_SECTION]]" in full_text:
                        parts = full_text.split("[[TECHNICAL_SECTION]]")
                        main_report = parts[0]
                        theory_report = parts[1]
                    else:
                        main_report = full_text
                        theory_report = "Technical basis integrated."

                    st.session_state.messages.append({"role": "user", "content": q})
                    st.session_state.messages.append({"role": "assistant", "content": main_report, "theory": theory_report})
                    
                    if not st.session_state.user_info_logged:
                        save_to_database(saju, b_date, b_time, q, is_lunar)
                        st.session_state.user_info_logged = True
                    st.rerun()
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
        
        # Keep the "Persona" alive in follow-up chat
        msgs = [{"role": "system", "content": st.session_state.saju_context}]
        for m in st.session_state.messages:
            msgs.append({"role": m["role"], "content": m["content"]})
            
        with st.chat_message("assistant"):
            with st.spinner("..."):
                response_text = generate_ai_response(msgs)
                
                if "[[TECHNICAL_SECTION]]" in response_text:
                    parts = response_text.split("[[TECHNICAL_SECTION]]")
                    main_r, theory_r = parts[0], parts[1]
                else:
                    main_r, theory_r = response_text, ""
                
                st.markdown(main_r)
                if theory_r:
                    with st.expander(txt["theory_header"]):
                        st.markdown(theory_r)
                        
                st.session_state.messages.append({"role": "assistant", "content": main_r, "theory": theory_r})
