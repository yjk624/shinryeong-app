import streamlit as st
import google.generativeai as genai
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. AUTO-DISCOVERY MODEL LOADER
# ==========================================
def configure_and_find_model(api_key):
    """
    Asks Google: 'What models do I have?' and picks the best 1.5-Flash version.
    """
    genai.configure(api_key=api_key)
    
    found_model_name = None
    
    try:
        # 1. Get list of all available models for this Key
        all_models = list(genai.list_models())
        
        # 2. Strategy: Find '1.5-flash' but NOT 'latest' (to avoid 2.5 quota trap)
        # We prefer '001' or '002' specific versions.
        priority_keywords = ['1.5-flash-002', '1.5-flash-001', '1.5-flash']
        
        for keyword in priority_keywords:
            for m in all_models:
                if keyword in m.name and 'latest' not in m.name:
                    if 'generateContent' in m.supported_generation_methods:
                        found_model_name = m.name
                        break
            if found_model_name: break
            
        # 3. Fallback: If no Flash, look for Pro
        if not found_model_name:
            for m in all_models:
                if 'gemini-pro' in m.name and 'latest' not in m.name:
                     if 'generateContent' in m.supported_generation_methods:
                        found_model_name = m.name
                        break
                        
        # 4. Final Fallback (Blind Guess)
        if not found_model_name:
            found_model_name = 'models/gemini-1.5-flash-001'
            
        return genai.GenerativeModel(found_model_name), found_model_name

    except Exception as e:
        st.error(f"Model List Error: {e}")
        return None, None

# ==========================================
# 2. CONFIGURATION & SETUP
# ==========================================

# Initialize Geocoder
geolocator = Nominatim(user_agent="shinryeong_app_auto_v1")

# Load Model
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    model, model_name = configure_and_find_model(API_KEY)
    
    if model is None:
        st.error("CRITICAL: Could not find any working models.")
        st.stop()
        
except Exception as e:
    st.error(f"Setup Error: {e}")

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
        return True
    except Exception as e:
        print(f"Database Save Failed: {e}")
        return False

# ==========================================
# 4. CITY DATABASE (Fallback)
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "Seoul": (37.56, 126.97),
    "부산": (35.17, 129.07), "Busan": (35.17, 129.07),
    "대구": (35.87, 128.60), "Daegu": (35.87, 128.60),
    "대전": (36.35, 127.38), "Daejeon": (36.35, 127.38),
    "광주": (35.15, 126.85), "Gwangju": (35.15, 126.85),
    "인천": (37.45, 126.70), "Incheon": (37.45, 126.70),
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

# ==========================================
# 5. UI LAYOUT
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가",
        "warning": "💡 **알림:** 본 분석 결과는 명리학적 데이터에 기반한 참고용 자료입니다.",
        "submit_btn": "🔮 분석 시작하기",
        "loading": "⏳ 신령을 소환하고 있습니다...",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. 주요 도시명으로 입력해주세요.",
        "chat_placeholder": "궁금한 점을 물어보세요...",
        "reset_btn": "🔄 초기화",
        "model_info": "연결된 AI 모델: "
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        "warning": "💡 **Notice:** For reference only.",
        "submit_btn": "🔮 Start Analysis",
        "loading": "⏳ Summoning Shinryeong...",
        "geo_error": "⚠️ Location not found.",
        "chat_placeholder": "Ask a follow-up...",
        "reset_btn": "🔄 Reset",
        "model_info": "Connected AI Model: "
    }
}

st.set_page_config(page_title="신령", page_icon="🔮", layout="centered")

with st.sidebar:
    lang_code = "ko" if st.radio("Language", ["한국어", "English"]) == "한국어" else "en"
    txt = TRANS[lang_code]
    if st.button(txt["reset_btn"]):
        st.session_state.clear()
        st.rerun()
    # Debug info: Show user which model we actually found
    st.caption(f"{txt['model_info']} `{model_name}`")

st.title(txt["title"])
st.caption(txt["subtitle"])
st.info(txt["warning"])

# ==========================================
# 6. APP LOGIC
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
                    
                    ctx = f"""[SYSTEM: USER DATA]
                    {saju}
                    Gender: {gender}
                    Loc: {loc_in}
                    Lang: {lang_code}
                    Role: Shinryeong (Hage-che tone, Easy Korean)
                    Rule: Do NOT cite 'Volume 4'."""
                    
                    st.session_state.saju_context = ctx
                    
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
                try:
                    resp = st.session_state.chat_session.send_message(p)
                    st.markdown(resp.text)
                    st.session_state.messages.append({"role": "assistant", "content": resp.text})
                except:
                    st.error("Connection failed. Try Reset.")
