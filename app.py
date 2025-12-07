import streamlit as st
import google.generativeai as genai
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# === CONFIGURATION ===
API_KEY = "AIzaSyDkaqLK6OSLw8YS5udevA5mKJTAsbTfiz0" 

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-flash-latest')

# Initialize Geocoder (Free Service via OpenStreetMap)
geolocator = Nominatim(user_agent="shinryeong_app_v2")

# === LANGUAGE DICTIONARY ===
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "subtitle": "AI 형이상학 분석가",
        "warning": "💡 **알림:** 본 분석 결과는 명리학적 데이터에 기반한 참고용 자료입니다. 인생의 중요한 결정은 본인의 의지에 달려 있음을 기억해 주세요.",
        "dob_label": "생년월일",
        "time_label": "태어난 시간 (정확한 분 단위)",
        "gender_label": "성별",
        "male": "남성",
        "female": "여성",
        "loc_label": "태어난 장소 (전 세계 어디든 입력 가능)",
        "loc_placeholder": "예: 서울 강남구, 뉴욕, 파리, 도쿄...",
        "concern_label": "당신의 고민을 털어놓으시오",
        "concern_placeholder": "예: 재물운이 언제쯤 트일까요?",
        "submit_btn": "🔮 신령에게 분석 요청하기",
        "loading": "⏳ 위성 좌표를 수신하고 운명을 계산하는 중...",
        "result_header": "### 📜 신령의 분석 보고서",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. 도시 이름을 정확히 입력해주세요 (예: Seoul, Korea).",
        "ref_expander": "📚 분석 근거 및 기술적 이론 (Technical Basis)",
        "ref_intro": "신령의 분석은 다음의 명리학적/자미두수 이론에 근거하여 도출되었습니다:",
        "error_connect": "오류 발생: "
    },
    "en": {
        "title": "🔮 Shinryeong",
        "subtitle": "AI Metaphysical Analyst",
        "warning": "💡 **Notice:** This analysis is based on metaphysical data. Please use it for reference only; the final choice is always yours.",
        "dob_label": "Date of Birth",
        "time_label": "Time of Birth",
        "gender_label": "Gender",
        "male": "Male",
        "female": "Female",
        "loc_label": "Place of Birth (City, Country)",
        "loc_placeholder": "Ex: Seoul, New York, Paris, London...",
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

# === UI LAYOUT ===
st.set_page_config(page_title="신령 (Shinryeong)", page_icon="🔮", layout="centered")

# Sidebar Language Toggle
with st.sidebar:
    st.header("Settings")
    lang_choice = st.radio("Language / 언어", ["한국어", "English"])
    lang_code = "ko" if lang_choice == "한국어" else "en"
    txt = TRANS[lang_code]

# Main UI
st.title(txt["title"])
st.subheader(txt["subtitle"])
st.markdown("---")
st.info(txt["warning"])

# === INPUT FORM ===
with st.form("user_input"):
    col1, col2 = st.columns(2)
    
    with col1:
        birth_date = st.date_input(txt["dob_label"], min_value=datetime(1940, 1, 1))
        birth_time = st.time_input(txt["time_label"], value=time(12, 00), step=60)
    
    with col2:
        gender = st.radio(txt["gender_label"], [txt["male"], txt["female"]])
        # Free Text Input for Location
        location_input = st.text_input(txt["loc_label"], placeholder=txt["loc_placeholder"])

    user_question = st.text_area(txt["concern_label"], height=100, placeholder=txt["concern_placeholder"])
    
    submitted = st.form_submit_button(txt["submit_btn"])

# === LOGIC CORE ===
if submitted:
    if not location_input:
        st.error(txt["geo_error"])
    else:
        with st.spinner(txt["loading"]):
            try:
                # 1. Geocoding (Text -> Lat/Lon)
                location = geolocator.geocode(location_input, timeout=10)
                
                if location:
                    lat = location.latitude
                    lon = location.longitude
                    
                    # 2. Calculate Saju
                    saju_data = calculate_saju_v3(
                        birth_date.year, birth_date.month, birth_date.day,
                        birth_time.hour, birth_time.minute, lat, lon
                    )
                    
                    # 3. Construct Prompt with SEPARATOR Logic
                    target_output_lang = "Korean" if lang_code == "ko" else "English"
                    
                    full_prompt = f"""
                    [System Command: You are 'Shinryeong'.]
                    [CRITICAL RULE: SEPARATE OUTPUT]
                    1. First, write the main counseling report in {target_output_lang}. Use Hage-che tone (if Korean). Use Easy Modern Terms.
                    2. Then, type exactly "[[TECHNICAL_SECTION]]".
                    3. After that marker, explain the **Technical Saju Theories** used (e.g., "Used 'Clash of Rat and Horse' to predict stress", "Applied 'Ten Gods' logic"). 
                       - Do NOT mention "Volume 4". 
                       - Explain the logic so the user understands the 'Why'.
                       - Write this technical part in {target_output_lang} too.

                    USER DATA:
                    {saju_data}
                    - Birth Place: {location_input} ({lat}, {lon})
                    
                    USER CONCERN:
                    "{user_question}"
                    """
                    
                    # 4. Call AI
                    response = model.generate_content(full_prompt)
                    
                    # 5. Split Response (Main vs Theory)
                    if "[[TECHNICAL_SECTION]]" in response.text:
                        parts = response.text.split("[[TECHNICAL_SECTION]]")
                        main_report = parts[0]
                        theory_report = parts[1]
                    else:
                        main_report = response.text
                        theory_report = "Technical details were integrated into the main text."

                    # 6. Display Main Report
                    st.markdown(txt["result_header"])
                    st.markdown(main_report)
                    
                    # 7. Display Theory in Expander (Matching Language)
                    with st.expander(txt["ref_expander"]):
                        st.write(txt["ref_intro"])
                        st.markdown(theory_report)
                        st.caption(f"📍 Calculated based on coordinates: {lat:.2f}, {lon:.2f} ({location.address})")

                else:
                    st.error(txt["geo_error"])
                    
            except Exception as e:
                st.error(f"{txt['error_connect']}{e}")
            
