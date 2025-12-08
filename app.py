import streamlit as st
import google.generativeai as genai
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. CONFIGURATION & FALLBACK DATA
# ==========================================

# A. Internal City Database (Safety Shield)
# This prevents the app from crashing for common locations if the API is blocked.
CITY_DB = {
    "서울": (37.56, 126.97), "Seoul": (37.56, 126.97),
    "부산": (35.17, 129.07), "Busan": (35.17, 129.07),
    "인천": (37.45, 126.70), "Incheon": (37.45, 126.70),
    "대구": (35.87, 128.60), "Daegu": (35.87, 128.60),
    "대전": (36.35, 127.38), "Daejeon": (36.35, 127.38),
    "광주": (35.15, 126.85), "Gwangju": (35.15, 126.85),
    "울산": (35.53, 129.31), "Ulsan": (35.53, 129.31),
    "세종": (36.48, 127.28), "Sejong": (36.48, 127.28),
    "수원": (37.26, 127.02), "Suwon": (37.26, 127.02),
    "성남": (37.42, 127.12), "Seongnam": (37.42, 127.12),
    "전주": (35.82, 127.14), "Jeonju": (35.82, 127.14),
    "제주": (33.49, 126.53), "Jeju": (33.49, 126.53),
    "창원": (35.22, 128.68), "Changwon": (35.22, 128.68),
    "고양": (37.65, 126.83), "Goyang": (37.65, 126.83),
    "용인": (37.24, 127.17), "Yongin": (37.24, 127.17),
    "청주": (36.64, 127.48), "Cheongju": (36.64, 127.48),
    "강릉": (37.75, 128.87), "Gangneung": (37.75, 128.87),
    "춘천": (37.88, 127.72), "Chuncheon": (37.88, 127.72),
    "New York": (40.71, -74.00), "뉴욕": (40.71, -74.00),
    "London": (51.50, -0.12), "런던": (51.50, -0.12),
    "Paris": (48.85, 2.35), "파리": (48.85, 2.35),
    "Tokyo": (35.67, 139.65), "도쿄": (35.67, 139.65),
    "Beijing": (39.90, 116.40), "베이징": (39.90, 116.40),
    "Los Angeles": (34.05, -118.24), "LA": (34.05, -118.24)
}

# B. Initialize External Geocoder (For other cities)
# We use a unique user-agent to try to avoid blocks
geolocator = Nominatim(user_agent="shinryeong_app_v2_custom_unique_id")

# C. Configure Gemini API with Fail-Safe Logic
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # Try preferred stable models first
    model = None
    options = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
    for m in options:
        try:
            test_model = genai.GenerativeModel(m)
            model = test_model
            break 
        except:
            continue
    if not model:
        model = genai.GenerativeModel('gemini-pro') # Last resort

except Exception as e:
    st.error(f"Configuration Error: {e}")

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
# 2. HELPER FUNCTIONS
# ==========================================
def get_coordinates(city_name):
    """
    Hybrid Geocoding: 
    1. Checks internal DB first (Fast, No Errors).
    2. Tries API second (For obscure places).
    3. Returns None if both fail.
    """
    # 1. Clean input
    clean_name = city_name.strip()
    
    # 2. Check Internal DB
    if clean_name in CITY_DB:
        return CITY_DB[clean_name]
    
    # 3. Try API (with error handling)
    try:
        location = geolocator.geocode(clean_name, timeout=5)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        print(f"API Geocoding Failed: {e}")
        # If API is blocked, we can't do anything for obscure cities.
        return None
        
    return None

def save_to_database(user_data, birth_date_obj, birth_time_obj, concern):
    """Saves data to Google Sheets."""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("Shinryeong_User_Data").sheet1
        
        input_date_str = birth_date_obj.strftime("%Y-%m-%d")
        input_time_str = birth_time_obj.strftime("%H:%M")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            timestamp,
            input_date_str,
            input_time_str,
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
# 3. LANGUAGE DICTIONARY
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가 (대화형 모드)",
        "warning": "💡 **알림:** 본 분석 결과는 명리학적 데이터에 기반한 참고용 자료입니다.",
        "dob_label": "생년월일",
        "time_label": "태어난 시간",
        "gender_label": "성별",
        "male": "남성",
        "female": "여성",
        "loc_label": "태어난 장소 (도시명 입력)",
        "loc_placeholder": "예: 서울, 부산, 창원, 뉴욕 (주요 도시는 즉시 인식됩니다)",
        "concern_label": "당신의 고민을 털어놓으시오",
        "concern_placeholder": "예: 재물운이 언제쯤 트일까요?",
        "submit_btn": "🔮 분석 시작하기",
        "loading": "⏳ 운명을 계산하고 신령을 소환하는 중...",
        "geo_error": "⚠️ 위치를 찾을 수 없거나 통신 오류가 발생했습니다. '서울', '부산' 등 주요 도시명으로 다시 시도해주세요.",
        "chat_placeholder": "신령에게 더 물어보고 싶은 것이 있나? (예: 내년 연애운은? 건강은?)",
        "reset_btn": "🔄 새로운 사주 분석하기"
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst (Chat Mode)",
        "warning": "💡 **Notice:** This analysis is based on metaphysical data.",
        "dob_label": "Date of Birth",
        "time_label": "Time of Birth",
        "gender_label": "Gender",
        "male": "Male",
        "female": "Female",
        "loc_label": "Place of Birth (City Name)",
        "loc_placeholder": "Ex: Seoul, New York, London...",
        "concern_label": "What is your concern?",
        "concern_placeholder": "Ex: When will my financial luck improve?",
        "submit_btn": "🔮 Start Analysis",
        "loading": "⏳ Calculating destiny...",
        "geo_error": "⚠️ Location not found or connection error. Please try a major city name.",
        "chat_placeholder": "Ask a follow-up question...",
        "reset_btn": "🔄 Analyze New Person"
    }
}

# ==========================================
# 4. UI LAYOUT & MAIN LOGIC
# ==========================================
st.set_page_config(page_title="신령 (Shinryeong)", page_icon="🔮", layout="centered")

with st.sidebar:
    st.header("Settings")
    lang_choice = st.radio("Language / 언어", ["한국어", "English"])
    lang_code = "ko" if lang_choice == "한국어" else "en"
    txt = TRANS[lang_code]
    
    if st.button(txt["reset_btn"]):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.session_state.saju_context = ""
        st.session_state.user_info_logged = False
        st.rerun()

st.title(txt["title"])
st.caption(txt["subtitle"])
st.info(txt["warning"])

# --- INPUT FORM ---
if not st.session_state.saju_context:
    with st.form("user_input"):
        col1, col2 = st.columns(2)
        with col1:
            birth_date = st.date_input(txt["dob_label"], min_value=datetime(1940, 1, 1))
            birth_time = st.time_input(txt["time_label"], value=time(12, 00), step=60)
        with col2:
            gender = st.radio(txt["gender_label"], [txt["male"], txt["female"]])
            location_input = st.text_input(txt["loc_label"], placeholder=txt["loc_placeholder"])

        user_question = st.text_area(txt["concern_label"], height=100, placeholder=txt["concern_placeholder"])
        submitted = st.form_submit_button(txt["submit_btn"])

    if submitted:
        if not location_input:
            st.error(txt["geo_error"])
        else:
            with st.spinner(txt["loading"]):
                # [NEW] Hybrid Geocoding Call
                coords = get_coordinates(location_input)
                
                if coords:
                    lat, lon = coords
                    
                    # Calculate Saju
                    saju_data = calculate_saju_v3(
                        birth_date.year, birth_date.month, birth_date.day,
                        birth_time.hour, birth_time.minute, lat, lon
                    )
                    saju_data['Birth_Place'] = location_input
                    saju_data['Gender'] = gender
                    
                    target_output_lang = "Korean" if lang_code == "ko" else "English"
                    
                    context_str = f"""
                    [SYSTEM CONTEXT: USER BIRTH DATA]
                    - Saju Pillars: {saju_data}
                    - Gender: {gender}
                    - Location: {location_input} ({lat}, {lon})
                    - Output Language: {target_output_lang}
                    - Persona: Shinryeong (Use Hage-che tone, Easy Modern Terms)
                    - Rule: Do not cite "Volume 4" explicitly.
                    """
                    st.session_state.saju_context = context_str
                    
                    # Start Chat
                    st.session_state.chat_session = model.start_chat(history=[])
                    
                    initial_prompt = f"{context_str}\n\nUser's First Concern: {user_question}\nAnalyze this."
                    
                    try:
                        response = st.session_state.chat_session.send_message(initial_prompt)
                        st.session_state.messages.append({"role": "user", "content": user_question})
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        
                        if not st.session_state.user_info_logged:
                            save_to_database(saju_data, birth_date, birth_time, user_question)
                            st.session_state.user_info_logged = True
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI Connection Error: {e}")

                else:
                    st.error(txt["geo_error"])

# --- CHAT INTERFACE ---
else:
    st.markdown("---")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(txt["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("..."):
                try:
                    full_msg = f"[Context Reminder: {st.session_state.saju_context}]\nUser Question: {prompt}"
                    response = st.session_state.chat_session.send_message(full_msg)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("Connection Error. Please try again.")
