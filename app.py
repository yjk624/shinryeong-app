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

# Robust Geocoding (Increased timeout to 10s to fix "not rendering" issue)
geolocator = Nominatim(user_agent="shinryeong_app_v7_final_fix", timeout=10)

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

PROMPT_TEXT = load_text_file("prompt.txt")        # The Persona
KNOWLEDGE_TEXT = load_text_file("knowledgebase.txt") # The Brain

# ==========================================
# 3. HELPER FUNCTIONS
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
    clean = city_name.strip()
    # 1. Internal DB Check
    if clean in CITY_DB: return CITY_DB[clean]
    
    # 2. API Check (with error handling)
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude)
    except (GeocoderTimedOut, GeocoderServiceError):
        return None # Return None implies failure, handled in UI
    except Exception as e:
        print(f"Geo Error: {e}")
        return None
    return None

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

def generate_ai_response(messages):
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6,
            max_tokens=3000, # Increased for full reports
            top_p=1,
            stream=True,
            stop=None,
        )
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                # yield content # Streaming disabled for Split Logic consistency
        return full_response
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 4. UI LAYOUT
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
        "loading": "⏳ 천문 데이터를 계산하고 신령을 소환하는 중...",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. (서버 과부하일 수 있으니 '서울'로 테스트해보세요).",
        "chat_placeholder": "추가로 궁금한 점이 있으신가요?",
        "reset_btn": "🔄 새로운 분석 시작",
        "dob_label": "생년월일", "time_label": "태어난 시간", "gender_label": "성별",
        "male": "남성", "female": "여성", "loc_label": "태어난 지역 (도시명)",
        "concern_label": "현재 가장 큰 고민은 무엇인가요?",
        "theory_header": "📚 분석 근거 및 기술적 이론 (Technical Basis)"
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
        "loading": "⏳ Calculating celestial data...",
        "geo_error": "⚠️ Location not found. Please try a major city.",
        "chat_placeholder": "Do you have follow-up questions?",
        "reset_btn": "🔄 Start New Analysis",
        "dob_label": "Date of Birth", "time_label": "Time of Birth", "gender_label": "Gender",
        "male": "Male", "female": "Female", "loc_label": "Birth Place (City)",
        "concern_label": "What is your main concern?",
        "theory_header": "📚 Technical Theory & Basis"
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
st.info(txt["warning"])

# ==========================================
# 5. APP LOGIC
# ==========================================
if not st.session_state.saju_context:
    with st.form("input"):
        col1, col2 = st.columns(2)
        with col1:
            b_date = st.date_input(txt["dob_label"], min_value=datetime(1940,1,1))
            b_time = st.time_input(txt["time_label"], value=time(12,00), step=60)
        with col2:
            gender = st.radio(txt["gender_label"], [txt["male"], txt["female"]])
            loc_in = st.text_input(txt["loc_label"], placeholder="Seoul, New York...")
        q = st.text_area(txt["concern_label"], height=100)
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
                    
                    # [CRITICAL] 1. Enforce Language 2. Enforce Structure 3. Inject Persona
                    system_prompt = f"""
                    [SYSTEM ROLE]
                    You are 'Shinryeong'. Act EXACTLY according to the Persona below.
                    {PROMPT_TEXT}
                    
                    [KNOWLEDGE BASE]
                    Use these rules for analysis:
                    {KNOWLEDGE_TEXT}
                    
                    [USER DATA]
                    - Saju: {saju}
                    - Gender: {gender}
                    - Location: {loc_in}
                    
                    [STRICT OUTPUT RULES]
                    1. LANGUAGE: Respond in {lang_code.upper()} ({'Korean' if lang_code == 'ko' else 'English'}). 
                       - Even if the user asks in English, if the setting is Korean, answer in Korean.
                    2. STRUCTURE: 
                       - First, provide the Counseling/Advice (Persona).
                       - Then, print EXACTLY: "[[TECHNICAL_SECTION]]"
                       - Finally, provide the Technical Theory/Basis (Explain the Ten Gods, Elements used).
                    """
                    
                    st.session_state.saju_context = system_prompt
                    
                    msgs = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"My concern is: {q}. Please analyze."}
                    ]
                    
                    # Call AI (No streaming to handle split)
                    full_text = generate_ai_response(msgs)
                    
                    # Split Response
                    if "[[TECHNICAL_SECTION]]" in full_text:
                        parts = full_text.split("[[TECHNICAL_SECTION]]")
                        main_report = parts[0]
                        theory_report = parts[1]
                    else:
                        main_report = full_text
                        theory_report = "Technical basis integrated into main text."

                    # Store & Display
                    st.session_state.messages.append({"role": "user", "content": q})
                    st.session_state.messages.append({"role": "assistant", "content": main_report, "theory": theory_report})
                    
                    if not st.session_state.user_info_logged:
                        save_to_database(saju, b_date, b_time, q)
                        st.session_state.user_info_logged = True
                    st.rerun()
                else:
                    st.error(txt["geo_error"])
else:
    st.markdown("---")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            # [FIXED] Show theory in expander if available for this message
            if "theory" in m:
                with st.expander(txt["theory_header"]):
                    st.markdown(m["theory"])
            
    if p := st.chat_input(txt["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        # Build context for next turn
        groq_msgs = [{"role": "system", "content": st.session_state.saju_context}]
        # Only feed the 'content' (main text) back to AI, not the theory, to keep context clean
        for m in st.session_state.messages:
            groq_msgs.append({"role": m["role"], "content": m["content"]})
            
        with st.chat_message("assistant"):
            with st.spinner("..."):
                response_text = generate_ai_response(groq_msgs)
                
                # Dynamic Split for Chat as well
                if "[[TECHNICAL_SECTION]]" in response_text:
                    parts = response_text.split("[[TECHNICAL_SECTION]]")
                    main_r = parts[0]
                    theory_r = parts[1]
                else:
                    main_r = response_text
                    theory_r = "Analysis based on established Saju logic."
                
                st.markdown(main_r)
                with st.expander(txt["theory_header"]):
                    st.markdown(theory_r)
                    
                st.session_state.messages.append({"role": "assistant", "content": main_r, "theory": theory_r})
