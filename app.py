import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="신령 (Shinryeong)", page_icon="🔮", layout="centered")
geolocator = Nominatim(user_agent="shinryeong_app_v6_final")

# Initialize Groq
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "saju_context" not in st.session_state:
    st.session_state.saju_context = ""
if "user_info_logged" not in st.session_state:
    st.session_state.user_info_logged = False

# ==========================================
# 2. FILE LOADERS (BRAIN & SOUL)
# ==========================================
@st.cache_data
def load_text_file(filename):
    """Reads external text files (Prompt & Knowledge)."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "" # Fail silently if file missing (but quality will drop)

# LOAD THE SOUL (Persona) AND BRAIN (Knowledge)
PROMPT_TEXT = load_text_file("prompt.txt") # Rename '신령 prompt .txt' to 'prompt.txt' on GitHub
KNOWLEDGE_TEXT = load_text_file("knowledgebase.txt") 

# ==========================================
# 3. DATABASE FUNCTION
# ==========================================
def save_to_database(user_data, birth_date_obj, birth_time_obj, concern):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gs_client = gspread.authorize(creds)
        sheet = gs_client.open("Shinryeong_User_Data").sheet1
        
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            birth_date_obj.strftime("%Y-%m-%d"),
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

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "Seoul": (37.56, 126.97),
    "부산": (35.17, 129.07), "Busan": (35.17, 129.07),
    "대구": (35.87, 128.60), "Daegu": (35.87, 128.60),
    "인천": (37.45, 126.70), "Incheon": (37.45, 126.70),
    "광주": (35.15, 126.85), "Gwangju": (35.15, 126.85),
    "대전": (36.35, 127.38), "Daejeon": (36.35, 127.38),
    "제주": (33.49, 126.53), "Jeju": (33.49, 126.53),
    "New York": (40.71, -74.00), "London": (51.50, -0.12)
}

def get_coordinates(city_name):
    clean = city_name.strip()
    if clean in CITY_DB: return CITY_DB[clean]
    try:
        loc = geolocator.geocode(clean, timeout=5)
        if loc: return (loc.latitude, loc.longitude)
    except: return None
    return None

def generate_ai_response(messages):
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.6, # Slightly lowered for more consistent formatting
        max_tokens=2048,
        top_p=1,
        stream=True,
        stop=None,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

# ==========================================
# 5. UI LAYOUT & TRANSLATION
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가",
        # [FIXED] Matches strict legal disclaimer from Volume 6/Prompt
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
        "dob_label": "생년월일",
        "time_label": "태어난 시간",
        "gender_label": "성별",
        "male": "남성", 
        "female": "여성",
        "loc_label": "태어난 지역 (도시명)",
        "loc_placeholder": "예: 서울, 부산, 뉴욕...",
        "concern_label": "현재 가장 큰 고민은 무엇인가요?",
        "concern_placeholder": "예: 직장 상사와의 갈등, 이직 문제, 연애운 등"
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        # [FIXED] English equivalent of the legal disclaimer
        "warning": """
        ⚖️ **Legal Disclaimer:**
        1. This service provides **academic analysis** based on Saju and Jami Dou Shu data; it is not absolute prophecy.
        2. Shinryeong does **NOT provide Medical Diagnoses or Legal Advice**.
        3. The user bears full responsibility for any decisions made based on this analysis.
        """,
        "submit_btn": "🔮 Request Analysis",
        "loading": "⏳ Calculating celestial data and summoning Shinryeong...",
        "geo_error": "⚠️ Location not found. Please try a major city name.",
        "chat_placeholder": "Do you have follow-up questions? (Ex: Wealth luck next year?)",
        "reset_btn": "🔄 Start New Analysis",
        "dob_label": "Date of Birth",
        "time_label": "Time of Birth",
        "gender_label": "Gender",
        "male": "Male", 
        "female": "Female",
        "loc_label": "Birth Place (City)",
        "loc_placeholder": "Ex: Seoul, New York, London...",
        "concern_label": "What is your main concern?",
        "concern_placeholder": "Ex: Career conflict, relationship advice, etc."
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
    st.caption("Engine: Groq Llama-3.3")

st.title(txt["title"])
st.caption(txt["subtitle"])
# Display the Warning Block
st.info(txt["warning"])

# ==========================================
# 6. APP LOGIC
# ==========================================
if not st.session_state.saju_context:
    with st.form("input"):
        col1, col2 = st.columns(2)
        with col1:
            b_date = st.date_input(txt["dob_label"], min_value=datetime(1940,1,1))
            b_time = st.time_input(txt["time_label"], value=time(12,00), step=60)
        with col2:
            gender = st.radio(txt["gender_label"], [txt["male"], txt["female"]])
            loc_in = st.text_input(txt["loc_label"], placeholder=txt["loc_placeholder"])
        q = st.text_area(txt["concern_label"], height=100, placeholder=txt["concern_placeholder"])
        submitted = st.form_submit_button(txt["submit_btn"])

    if submitted:
        if not loc_in:
            st.error(txt["geo_error"])
        else:
            with st.spinner(txt["loading"]):
                coords = get_coordinates(loc_in)
                if coords:
                    lat, lon = coords
                    saju = calculate_saju_v3(b_date.year, b_date.month, b_date.day, b_time.hour, b_time.minute, lat, lon)
                    saju['Birth_Place'] = loc_in
                    saju['Gender'] = gender
                    
                    # [CRITICAL] Inject PROMPT + KNOWLEDGE + USER DATA
                    # This structure forces the AI to "Become" Shinryeong again.
                    ctx = f"""
                    [SYSTEM INSTRUCTION: PERSONA ADOPTION]
                    {PROMPT_TEXT}
                    
                    [KNOWLEDGE BASE]
                    {KNOWLEDGE_TEXT}
                    
                    [USER DATA FOR ANALYSIS]
                    - Saju Pillars: {saju}
                    - Gender: {gender}
                    - Birth Location: {loc_in}
                    - Output Language: {lang_code} (Respond in this language ONLY)
                    """
                    
                    st.session_state.saju_context = ctx
                    
                    # Initial Prompt
                    msgs = [
                        {"role": "system", "content": ctx},
                        {"role": "user", "content": f"My concern is: {q}. Please analyze my Saju and provide the solution based on the knowledge base."}
                    ]
                    
                    try:
                        stream = generate_ai_response(msgs)
                        response_text = st.write_stream(stream)
                        
                        st.session_state.messages.append({"role": "user", "content": q})
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                        
                        if not st.session_state.user_info_logged:
                            save_to_database(saju, b_date, b_time, q)
                            st.session_state.user_info_logged = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI Error: {e}")
                else:
                    st.error(txt["geo_error"])
else:
    st.markdown("---")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            
    if p := st.chat_input(txt["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        groq_messages = [{"role": "system", "content": st.session_state.saju_context}]
        for m in st.session_state.messages:
            groq_messages.append({"role": m["role"], "content": m["content"]})
            
        with st.chat_message("assistant"):
            try:
                stream = generate_ai_response(groq_messages)
                response_text = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except:
                st.error("Connection failed.")
