import streamlit as st
import google.generativeai as genai
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. ROBUST MODEL LOADER (Health Check)
# ==========================================
def get_working_model(api_key):
    """
    Tries multiple models. Returns the first one that successfully 
    connects to Google's servers.
    """
    genai.configure(api_key=api_key)
    
    # Priority List: Best/Fastest -> Old/Reliable
    candidates = [
        'models/gemini-1.5-flash',
        'models/gemini-flash-latest',
        'models/gemini-1.5-flash-001',
        'models/gemini-pro'
    ]
    
    for model_name in candidates:
        try:
            # 1. Create Model
            model = genai.GenerativeModel(model_name)
            
            # 2. HEALTH CHECK: Try to generate one token
            # This forces the API to validate the model name NOW.
            response = model.generate_content("test")
            
            # If we get here, it worked!
            print(f"✅ Selected Model: {model_name}")
            return model
        except Exception as e:
            print(f"❌ Failed model {model_name}: {e}")
            continue
            
    # If all fail, return None
    return None

# ==========================================
# 2. CONFIGURATION & SETUP
# ==========================================

# Initialize Geocoder
geolocator = Nominatim(user_agent="shinryeong_app_final")

# Load Model using the Health Check
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    model = get_working_model(API_KEY)
    
    if model is None:
        st.error("CRITICAL ERROR: Could not connect to ANY Google AI models. Please check your API Key or Google Cloud status.")
        st.stop() # Stop the app entirely if no brain is found
        
except Exception as e:
    st.error(f"Secret Error: {e}")

# Initialize Session State
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None  
if "messages" not in st.session_state:
    st.session_state.messages = []        
if "saju_context" not in st.session_state:
    st.session_state.saju_context = ""    
if "user_info_logged" not in st.session_state:
    st.session_state.user_info_logged = False 

# ==========================================
# 3. DATABASE FUNCTION
# ==========================================
def save_to_database(user_data, birth_date_obj, birth_time_obj, concern):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("Shinryeong_User_Data").sheet1
        
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
    except Exception as e:
        print(f"Database Save Failed: {e}")

# ==========================================
# 4. INTERNAL CITY DB (Fallback)
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "Seoul": (37.56, 126.97),
    "부산": (35.17, 129.07), "Busan": (35.17, 129.07),
    "인천": (37.45, 126.70), "Incheon": (37.45, 126.70),
    "대구": (35.87, 128.60), "Daegu": (35.87, 128.60),
    "대전": (36.35, 127.38), "Daejeon": (36.35, 127.38),
    "광주": (35.15, 126.85), "Gwangju": (35.15, 126.85),
    "제주": (33.49, 126.53), "Jeju": (33.49, 126.53),
    "New York": (40.71, -74.00), "London": (51.50, -0.12)
}

def get_coordinates(city_name):
    clean_name = city_name.strip()
    if clean_name in CITY_DB: return CITY_DB[clean_name]
    try:
        loc = geolocator.geocode(clean_name, timeout=5)
        if loc: return (loc.latitude, loc.longitude)
    except: return None
    return None

# ==========================================
# 5. UI LAYOUT & TEXT
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가 (대화형 모드)",
        "warning": "💡 **알림:** 본 분석 결과는 참고용입니다.",
        "submit_btn": "🔮 분석 시작하기",
        "loading": "⏳ 신령을 소환하고 있습니다... (AI 모델 연결 중)",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. 주요 도시명으로 입력해주세요.",
        "chat_placeholder": "궁금한 점을 물어보세요...",
        "reset_btn": "🔄 초기화"
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        "warning": "💡 **Notice:** For reference only.",
        "submit_btn": "🔮 Start Analysis",
        "loading": "⏳ Summoning Shinryeong... (Connecting to AI)",
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

st.title(txt["title"])
st.caption(txt["subtitle"])
st.info(txt["warning"])

# ==========================================
# 6. MAIN APP LOGIC
# ==========================================
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
                    
                    # Construct Prompt
                    ctx = f"""[SYSTEM: SAJU DATA]
                    {saju}
                    Gender: {gender}
                    Loc: {loc_in}
                    Lang: {lang_code}
                    Role: Shinryeong (Hage-che tone)
                    Rule: Do NOT cite 'Volume 4'."""
                    
                    st.session_state.saju_context = ctx
                    
                    # Start Chat
                    try:
                        st.session_state.chat_session = model.start_chat(history=[])
                        prompt = f"{ctx}\n\nUser Question: {q}\nAnalyze."
                        resp = st.session_state.chat_session.send_message(prompt)
                        
                        st.session_state.messages.append({"role": "user", "content": q})
                        st.session_state.messages.append({"role": "assistant", "content": resp.text})
                        
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
        with st.chat_message("assistant"):
            with st.spinner("..."):
                resp = st.session_state.chat_session.send_message(p)
                st.markdown(resp.text)
                st.session_state.messages.append({"role": "assistant", "content": resp.text})
