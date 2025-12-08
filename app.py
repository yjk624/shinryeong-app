import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# ==========================================
# 1. CONFIGURATION (GROQ ENGINE)
# ==========================================
geolocator = Nominatim(user_agent="shinryeong_app_groq_v4")

# Initialize Groq Client
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
# 2. KNOWLEDGE BASE LOADER (THE BRAIN)
# ==========================================
@st.cache_data
def load_knowledge_base():
    """Reads the text file that contains all Saju logic."""
    try:
        # Tries to read the file from the same folder as app.py
        with open("knowledgebase.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        st.error("⚠️ critical Error: 'knowledgebase.txt' not found in repository.")
        return ""

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
        temperature=0.7,
        max_tokens=2048,
        top_p=1,
        stream=True,
        stop=None,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

# ==========================================
# 5. UI LAYOUT
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가",
        "warning": "💡 **알림:** 결과는 참고용입니다.",
        "submit_btn": "🔮 분석 시작하기",
        "loading": "⏳ 신령 소환 중...",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다.",
        "chat_placeholder": "궁금한 점을 물어보세요...",
        "reset_btn": "🔄 초기화"
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        "warning": "💡 **Notice:** For reference only.",
        "submit_btn": "🔮 Start Analysis",
        "loading": "⏳ Summoning Shinryeong...",
        "geo_error": "⚠️ Location not found.",
        "chat_placeholder": "Ask a follow-up...",
        "reset_btn": "🔄 Reset"
    }
}

st.set_page_config(page_title="신령", page_icon="🔮", layout="centered")

with st.sidebar:
    lang_code = "ko" if st.radio("Language", ["한국어", "English"]) == "한국어" else "en"
    txt = TRANS[lang_code]
    if st.button(txt["reset_btn"]):
        st.session_state.clear()
        st.rerun()
    st.caption("Engine: Groq Llama-3.3")

st.title(txt["title"])
st.caption(txt["subtitle"])
st.info(txt["warning"])

# ==========================================
# 6. APP LOGIC
# ==========================================
# Load the Knowledge Base ONCE
KNOWLEDGE_BASE_TEXT = load_knowledge_base()

if not st.session_state.saju_context:
    with st.form("input"):
        col1, col2 = st.columns(2)
        with col1:
            b_date = st.date_input("Date", min_value=datetime(1940,1,1))
            b_time = st.time_input("Time", value=time(12,00), step=60)
        with col2:
            gender = st.radio("Gender", ["Male", "Female"])
            loc_in = st.text_input("Location (City)", placeholder="Seoul, Busan...")
        q = st.text_area("Question", height=100)
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
                    
                    # [CRITICAL UPDATE] Inject the Knowledge Base into the System Prompt
                    ctx = f"""
                    [ROLE DEFINITION]
                    You are 'Shinryeong', a Metaphysical Analyst.
                    - Tone: Hage-che (하게체) - Old sage style.
                    - Language: ALWAYS respond in KOREAN (Hangul).
                    
                    [KNOWLEDGE BASE]
                    Use the following rules to analyze the user's destiny. Do not summarize this; APPLY it.
                    {KNOWLEDGE_BASE_TEXT}
                    
                    [USER DATA]
                    - Saju Pillars: {saju}
                    - Gender: {gender}
                    - Location: {loc_in}
                    
                    [INSTRUCTION]
                    Analyze the user's Saju structure based on the Knowledge Base. 
                    Address their concern: "{q}"
                    Do NOT mention 'Volume 4' or 'Knowledge Base' explicitly. Just give the advice.
                    """
                    
                    st.session_state.saju_context = ctx
                    
                    # Initial Prompt
                    msgs = [
                        {"role": "system", "content": ctx},
                        {"role": "user", "content": q}
                    ]
                    
                    try:
                        # Stream the response
                        stream = generate_ai_response(msgs)
                        response_text = st.write_stream(stream)
                        
                        # Save to history
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
        
        # Prepare context + history for Groq
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
