import streamlit as st
import google.generativeai as genai
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================

# Initialize Geocoder
geolocator = Nominatim(user_agent="shinryeong_app_v2")

# Configure Gemini API (from Secrets)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('models/gemini-flash-latest')
except Exception as e:
    st.error(f"Secret Error: {e}")

# ==========================================
# 2. DATABASE FUNCTION (Google Sheets)
# ==========================================
def save_to_database(user_data, concern, analysis_summary):
    """Saves user session data to Google Sheets securely."""
    try:
        # Define Scope
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Load Credentials from Secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Fix formatting for private key
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Open Sheet (Make sure your sheet is named EXACTLY this)
        sheet = client.open("Shinryeong_User_Data").sheet1
        
        # Prepare Row
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            user_data.get('Year', ''),
            user_data.get('Month', ''),
            user_data.get('Day', ''),
            user_data.get('Time', ''),
            str(user_data.get('Birth_Place', 'Unknown')),
            user_data.get('Gender', 'Unknown'),
            concern
        ]
        
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"Database Save Failed: {e}")
        return False

# ==========================================
# 3. LANGUAGE DICTIONARY (UI TEXT)
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가",
        "warning": "💡 **알림:** 본 분석 결과는 명리학적 데이터에 기반한 참고용 자료입니다. 연구 목적으로 익명화된 생년월일 데이터가 수집될 수 있습니다.",
        "dob_label": "생년월일",
        "time_label": "태어난 시간",
        "gender_label": "성별",
        "male": "남성",
        "female": "여성",
        "loc_label": "태어난 장소 (도시, 국가)",
        "loc_placeholder": "예: 서울 강남구, 뉴욕, 파리...",
        "concern_label": "당신의 고민을 털어놓으시오",
        "concern_placeholder": "예: 재물운이 언제쯤 트일까요?",
        "submit_btn": "🔮 신령에게 분석 요청하기",
        "loading": "⏳ 위성 좌표를 수신하고 운명을 계산하는 중...",
        "result_header": "### 📜 신령의 분석 보고서",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. 도시 이름을 정확히 입력해주세요.",
        "ref_expander": "📚 분석 근거 및 기술적 이론",
        "ref_intro": "신령의 분석은 다음의 명리학적 이론에 근거하여 도출되었습니다:",
        "error_connect": "오류 발생: "
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        "warning": "💡 **Notice:** This analysis is based on metaphysical data. Anonymous birth data may be collected for research accuracy.",
        "dob_label": "Date of Birth",
        "time_label": "Time of Birth",
        "gender_label": "Gender",
        "male": "Male",
        "female": "Female",
        "loc_label": "Place of Birth",
        "loc_placeholder": "Ex: Seoul, New York, Paris...",
        "concern_label": "What is your concern?",
        "concern_placeholder": "Ex: When will my financial luck improve?",
        "submit_btn": "🔮 Ask Shinryeong",
        "loading": "⏳ Geocoding coordinates and calculating destiny...",
        "result_header": "### 📜 Analyst Report",
        "geo_error": "⚠️ Could not find location. Please try 'City, Country' format.",
        "ref_expander": "📚 Technical Theory & Basis",
        "ref_intro": "This report was derived using the following metaphysical theories:",
        "error_connect": "Error: "
    }
}

# ==========================================
# 4. UI LAYOUT & INPUT FORM
# ==========================================
st.set_page_config(page_title="신령 (Shinryeong)", page_icon="🔮", layout="centered")

# Sidebar Language
with st.sidebar:
    st.header("Settings")
    lang_choice = st.radio("Language / 언어", ["한국어", "English"])
    lang_code = "ko" if lang_choice == "한국어" else "en"
    txt = TRANS[lang_code]

# Main Title
st.title(txt["title"])
st.subheader(txt["subtitle"])
st.markdown("---")
st.info(txt["warning"])

# Input Form
with st.form("user_input"):
    col1, col2 = st.columns(2)
    
    with col1:
        birth_date = st.date_input(txt["dob_label"], min_value=datetime(1940, 1, 1))
        birth_time = st.time_input(txt["time_label"], value=time(12, 00), step=60)
    
    with col2:
        gender = st.radio(txt["gender_label"], [txt["male"], txt["female"]])
        location_input = st.text_input(txt["loc_label"], placeholder=txt["loc_placeholder"])

    user_question = st.text_area(txt["concern_label"], height=100, placeholder=txt["concern_placeholder"])
    
    # This defines the variable 'submitted'
    submitted = st.form_submit_button(txt["submit_btn"])

# ==========================================
# 5. LOGIC CORE
# ==========================================
if submitted:
    if not location_input:
        st.error(txt["geo_error"])
    else:
        with st.spinner(txt["loading"]):
            try:
                # A. Geocoding
                location = geolocator.geocode(location_input, timeout=10)
                
                if location:
                    lat = location.latitude
                    lon = location.longitude
                    
                    # B. Calculate Saju
                    saju_data = calculate_saju_v3(
                        birth_date.year, birth_date.month, birth_date.day,
                        birth_time.hour, birth_time.minute, lat, lon
                    )
                    
                    # C. Construct Prompt
                    target_output_lang = "Korean" if lang_code == "ko" else "English"
                    
                    full_prompt = f"""
                    [System Command: You are 'Shinryeong'.]
                    [CRITICAL RULE: SEPARATE OUTPUT]
                    1. First, write the main counseling report in {target_output_lang}. Use Hage-che tone (if Korean). Use Easy Modern Terms.
                    2. Then, type exactly "[[TECHNICAL_SECTION]]".
                    3. After that marker, explain the **Technical Saju Theories** used.
                       - Do NOT mention "Volume 4". 
                       - Write this technical part in {target_output_lang} too.

                    USER DATA:
                    {saju_data}
                    - Birth Place: {location_input} ({lat}, {lon})
                    - Gender: {gender}
                    
                    USER CONCERN:
                    "{user_question}"
                    """
                    
                    # D. Call AI
                    response = model.generate_content(full_prompt)
                    
                    # E. Save to Database (Silent Background Process)
                    saju_data['Birth_Place'] = location_input
                    saju_data['Gender'] = gender
                    save_to_database(saju_data, user_question, "Analysis Generated")
                    
                    # F. Display Results
                    if "[[TECHNICAL_SECTION]]" in response.text:
                        parts = response.text.split("[[TECHNICAL_SECTION]]")
                        main_report = parts[0]
                        theory_report = parts[1]
                    else:
                        main_report = response.text
                        theory_report = "Technical details integrated."

                    st.markdown(txt["result_header"])
                    st.markdown(main_report)
                    
                    with st.expander(txt["ref_expander"]):
                        st.write(txt["ref_intro"])
                        st.markdown(theory_report)
                        st.caption(f"📍 Calculated based on: {location.address}")

                else:
                    st.error(txt["geo_error"])
                    
            except Exception as e:
                st.error(f"{txt['error_connect']}{e}")
