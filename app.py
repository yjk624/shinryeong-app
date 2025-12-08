import streamlit as st
import google.generativeai as genai
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. CONFIGURATION & SESSION STATE
# ==========================================

# Initialize Geocoder
geolocator = Nominatim(user_agent="shinryeong_app_v2")

# Configure Gemini API
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Using 'gemini-1.5-flash' (or 'gemini-flash-latest') which supports multi-turn chat better
    model = genai.GenerativeModel('models/gemini-flash-latest')
except Exception as e:
    st.error(f"Secret Error: {e}")

# Initialize Session State (The App's Memory)
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None  # Stores the Gemini Chat Object
if "messages" not in st.session_state:
    st.session_state.messages = []        # Stores the visible chat history
if "saju_context" not in st.session_state:
    st.session_state.saju_context = ""    # Stores the calculated birth chart text
if "user_info_logged" not in st.session_state:
    st.session_state.user_info_logged = False # Prevents duplicate DB saving

# ==========================================
# 2. DATABASE FUNCTION
# ==========================================
def save_to_database(user_data, birth_date_obj, birth_time_obj, concern):
    """Saves initial user data to Google Sheets."""
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
        "subtitle": "AI 형이상학 분석가 (특정 주제 분석/상담)",
        "warning": "💡 **알림:** 본 분석 결과는 명리학적 데이터에 기반한 참고용 자료입니다.",
        "dob_label": "생년월일",
        "time_label": "태어난 시간",
        "gender_label": "성별",
        "male": "남성",
        "female": "여성",
        "loc_label": "태어난 장소 (도시, 국가)",
        "loc_placeholder": "예: 서울 강남구, 뉴욕, 파리...",
        "concern_label": "당신의 고민을 털어놓으시오",
        "concern_placeholder": "예: 재물운이 언제쯤 트일까요?",
        "submit_btn": "🔮 분석 시작하기",
        "loading": "⏳ 운명을 계산하고 신령을 소환하는 중...",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다.",
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
        "loc_label": "Place of Birth",
        "loc_placeholder": "Ex: Seoul, New York, Paris...",
        "concern_label": "What is your concern?",
        "concern_placeholder": "Ex: When will my financial luck improve?",
        "submit_btn": "🔮 Start Analysis",
        "loading": "⏳ Calculating destiny...",
        "geo_error": "⚠️ Location not found.",
        "chat_placeholder": "Ask a follow-up question... (Ex: What about my love life?)",
        "reset_btn": "🔄 Analyze New Person"
    }
}

# ==========================================
# 4. UI LAYOUT
# ==========================================
st.set_page_config(page_title="신령 (Shinryeong)", page_icon="🔮", layout="centered")

with st.sidebar:
    st.header("Settings")
    lang_choice = st.radio("Language / 언어", ["한국어", "English"])
    lang_code = "ko" if lang_choice == "한국어" else "en"
    txt = TRANS[lang_code]
    
    # Reset Button (Clears Memory)
    if st.button(txt["reset_btn"]):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.session_state.saju_context = ""
        st.session_state.user_info_logged = False
        st.rerun()

st.title(txt["title"])
st.caption(txt["subtitle"])
st.info(txt["warning"])

# ==========================================
# 5. INPUT FORM (SHOWN ONLY IF NO CHAT STARTED)
# ==========================================
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
                try:
                    # 1. Geocoding
                    location = geolocator.geocode(location_input, timeout=10)
                    if location:
                        lat, lon = location.latitude, location.longitude
                        
                        # 2. Calculate Saju
                        saju_data = calculate_saju_v3(
                            birth_date.year, birth_date.month, birth_date.day,
                            birth_time.hour, birth_time.minute, lat, lon
                        )
                        saju_data['Birth_Place'] = location_input
                        saju_data['Gender'] = gender
                        
                        # 3. Store Context in Session State (The "Hidden Memory")
                        target_output_lang = "Korean" if lang_code == "ko" else "English"
                        
                        # This string tells the AI who the user is for the ENTIRE chat
                        context_str = f"""
                        [SYSTEM CONTEXT: USER BIRTH DATA]
                        - Saju Pillars: {saju_data}
                        - Gender: {gender}
                        - Location: {location_input} ({lat}, {lon})
                        - Output Language: {target_output_lang}
                        - Persona: Shinryeong (Use Hage-che tone, Easy Modern Terms)
                        - Reference: Use Knowledge Base Vol 1-6 but do not cite them explicitly.
                        """
                        st.session_state.saju_context = context_str
                        
                        # 4. Start Chat Session with History
                        # We initiate the chat with the User's first concern
                        st.session_state.chat_session = model.start_chat(history=[])
                        
                        # 5. Send Initial Prompt
                        initial_prompt = f"{context_str}\n\nUser's First Concern: {user_question}\nAnalyze this."
                        response = st.session_state.chat_session.send_message(initial_prompt)
                        
                        # 6. Save Initial Response to visible history
                        st.session_state.messages.append({"role": "user", "content": user_question})
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        
                        # 7. Log to DB (Once per session)
                        if not st.session_state.user_info_logged:
                            save_to_database(saju_data, birth_date, birth_time, user_question)
                            st.session_state.user_info_logged = True
                        
                        st.rerun() # Refresh to show chat interface

                    else:
                        st.error(txt["geo_error"])
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# 6. CHAT INTERFACE (SHOWN AFTER ANALYSIS)
# ==========================================
else:
    # A. Display Saju Summary (Top of Chat)
    st.markdown("---")
    
    # B. Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # C. Handle New User Input
    if prompt := st.chat_input(txt["chat_placeholder"]):
        # 1. Add user message to UI
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Generate AI Response
        with st.chat_message("assistant"):
            with st.spinner("..."):
                try:
                    # We implicitly rely on the 'chat_session' object to remember history
                    # But we remind it of the context slightly just in case
                    full_msg = f"[Context Reminder: {st.session_state.saju_context}]\nUser Question: {prompt}"
                    response = st.session_state.chat_session.send_message(full_msg)
                    st.markdown(response.text)
                    
                    # 3. Add AI response to history
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("Connection Error. Please try again.")
