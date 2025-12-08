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
geolocator = Nominatim(user_agent="shinryeong_master_v22", timeout=10)

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "user_info_logged" not in st.session_state: st.session_state.user_info_logged = False
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

# ==========================================
# 2. LOADERS
# ==========================================
@st.cache_data
def load_text_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f: return f.read()
    except: return ""

PROMPT_TEXT = load_text_file("prompt.txt")
KNOWLEDGE_TEXT = load_text_file("knowledgebase.txt")

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "대전": (36.35, 127.38), "광주": (35.15, 126.85), 
    "울산": (35.53, 129.31), "세종": (36.48, 127.28), "창원": (35.22, 128.68),
    "제주": (33.49, 126.53), "New York": (40.71, -74.00), "London": (51.50, -0.12),
    "Paris": (48.85, 2.35), "Tokyo": (35.67, 139.65),
    "Los Angeles": (34.05, -118.24), "Sydney": (-33.86, 151.20)
}

def get_coordinates(city_input):
    clean = city_input.strip()
    if clean in CITY_DB: return CITY_DB[clean], clean
    for k, v in CITY_DB.items():
        if k in clean or k.lower() in clean.lower(): return v, k
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def save_to_database(user_data, birth_date_obj, birth_time_obj, concern, is_lunar):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        sheet = client.open("Shinryeong_User_Data").sheet1
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{birth_date_obj} ({'Lunar' if is_lunar else 'Solar'})",
            str(birth_time_obj),
            str(user_data.get('Birth_Place', 'Unknown')),
            user_data.get('Gender', 'Unknown'),
            user_data.get('Year', ''), user_data.get('Month', ''), 
            user_data.get('Day', ''), user_data.get('Time', ''),
            concern
        ])
    except: pass

# --- ADVANCED SAJU LOGIC (PYTHON SIDE) ---
def analyze_saju_logic(saju_data):
    """
    Pre-calculates 'Shinsal', 'Clashes', and 'Metaphors' to force specific AI output.
    """
    day = saju_data['Day']   # e.g., "갑(甲)자(子)"
    month = saju_data['Month']
    year = saju_data['Year']
    
    # 1. Metaphor Construction (Day Stem + Month Branch)
    day_stem = day[0:2] # 갑(甲)
    month_branch = month[3:5] # 자(子)
    metaphor = f"'{month_branch}월(Season)'에 태어난 '{day_stem}(Self)'"
    
    # 2. Shinsal (Special Stars) Detection
    shinsal_list = []
    # Hyun-Chim (Needle) - Sharp, Medical, Precision
    if any(x in (day + month) for x in ["갑", "신", "묘", "오"]):
        shinsal_list.append("현침살(懸針殺-예리한 통찰력과 전문기술)")
    # Yeokma (Travel) - Movement, Global
    if any(x in (day + month) for x in ["인", "신", "사", "해"]):
        shinsal_list.append("역마살(驛馬殺-이동과 변화)")
    # Dohwa (Peach Blossom) - Popularity
    if any(x in (day + month) for x in ["자", "오", "묘", "유"]):
        shinsal_list.append("도화살(桃花殺-인기와 매력)")
    
    special_star_text = ", ".join(shinsal_list) if shinsal_list else "특이 신살 없음(평온함)"

    # 3. Future Prediction (Clash with 2025 Eul-Sa)
    # 2025 is Snake (Sa). Snake clashes with Pig (Hae).
    future_prediction = ""
    if "해(亥)" in day or "해(亥)" in month:
        future_prediction = "2025년(을사년)은 사해충(巳亥沖)이 들어오는 해라, 이동수나 직업적 변동이 매우 강하게 들어온다."
    elif "신(申)" in day: # Snake + Monkey = Hap (Water) or Hyeong
        future_prediction = "2025년은 사신형(巳申刑)이 작용하니, 인간관계의 조정이나 문서상의 조정이 필요하다."
    else:
        future_prediction = "2025년은 큰 충돌보다는 세력을 키우는 흐름으로 간다."

    return metaphor, special_star_text, future_prediction

def generate_ai_response(messages):
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.5, max_tokens=5000, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except: continue
    yield "⚠️ System Busy."

# ==========================================
# 4. UI LAYOUT
# ==========================================
TRANS = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)", "subtitle": "AI 정통 명리학 분석가",
        "warning": "⚖️ 본 분석은 명리학적 통계에 기반한 학술적 자료입니다.",
        "submit_btn": "🔮 정밀 분석 시작", "loading": "⏳ 신령을 소환하여 운명을 읽는 중...",
        "geo_error": "⚠️ 위치를 찾을 수 없습니다. (예: 서울, 부산)",
        "chat_placeholder": "추가 질문을 입력하세요...",
        "reset_btn": "🔄 새로하기", "dob": "생년월일", "time": "태어난 시간",
        "gender": "성별", "loc": "태어난 지역", "concern": "고민 내용 (비워두면 종합 운세 분석)",
        "cal": "양력/음력",
        "table_key": "구분", "table_val": "내용"
    },
    "en": {
        "title": "🔮 Shinryeong", "subtitle": "AI Metaphysical Analyst",
        "warning": "⚖️ Academic analysis based on Saju.",
        "submit_btn": "🔮 Analyze", "loading": "⏳ Analyzing...",
        "geo_error": "⚠️ Location not found.", "chat_placeholder": "Follow-up question...",
        "reset_btn": "🔄 Reset", "dob": "Date of Birth", "time": "Time",
        "gender": "Gender", "loc": "Birth Place", "concern": "Concern",
        "cal": "Calendar",
        "table_key": "Parameter", "table_val": "Value"
    }
}

with st.sidebar:
    lang = "ko" if st.radio("Language", ["한국어", "English"]) == "한국어" else "en"
    t = TRANS[lang]
    if st.button(t["reset_btn"]):
        st.session_state.clear()
        st.rerun()

st.title(t["title"])
st.caption(t["subtitle"])
st.info(t["warning"])

# --- MAIN LOGIC ---
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        with c1:
            b_date = st.date_input(t["dob"], min_value=datetime(1940,1,1))
            b_time = st.time_input(t["time"], value=time(12,0), step=60)
            cal = st.radio(t["cal"], ["양력 (Solar)", "음력 (Lunar)"])
        with c2:
            gender = st.radio(t["gender"], ["남성 (Male)", "여성 (Female)"])
            loc = st.text_input(t["loc"], placeholder="Seoul, Busan...")
        q_input = st.text_area(t["concern"], height=100)
        submitted = st.form_submit_button(t["submit_btn"])

    if submitted:
        if not loc:
            st.error(t["geo_error"])
        else:
            with st.spinner(t["loading"]):
                coords, matched_city = get_coordinates(loc)
                if coords:
                    is_lunar = "음력" in cal
                    saju = calculate_saju_v3(b_date.year, b_date.month, b_date.day, 
                                           b_time.hour, b_time.minute, coords[0], coords[1], is_lunar)
                    saju['Birth_Place'] = matched_city if matched_city else loc
                    saju['Gender'] = gender
                    
                    final_q = q_input if q_input.strip() else "나의 타고난 기질과 향후 운세"
                    
                    # 1. Run Python Logic (The "Truth Engine")
                    metaphor, shinsal, future_fact = analyze_saju_logic(saju)
                    
                    # 2. Table Render
                    table_md = f"""
| {t['table_key']} | {t['table_val']} |
| :--- | :--- |
| **{t['dob']}** | {b_date} ({cal}) |
| **{t['time']}** | {b_time} |
| **{t['loc']}** | {saju['Birth_Place']} |
| **{t['gender']}** | {gender} |
| **사주(간지)** | Y:{saju['Year']} / M:{saju['Month']} / D:{saju['Day']} / T:{saju['Time']} |
| **분석 주제** | {final_q} |
"""
                    
                    # 3. System Prompt (Injected with Python Facts)
                    current_year = datetime.now().year
                    sys_p = f"""
                    [SYSTEM ROLE]
                    You are 'Shinryeong' (신령). Master Saju Analyst.
                    Tone: "Hage-che" (하게체: ~하네, ~이라네). Authoritative, Mystical.
                    Language: {lang.upper()} ONLY.
                    
                    [USER DATA]
                    - Identity (Day Master): {saju['Day']}
                    - Environment: {saju['Month']}
                    - Concern: "{final_q}"
                    
                    [CALCULATED FACTS - YOU MUST USE THESE]
                    1. **Metaphor:** {metaphor} (Use this in Section 1)
                    2. **Special Stars:** {shinsal} (Use this in Section 2 for Talent/Job)
                    3. **Future Prediction:** {future_fact} (Use this in Section 4)
                    
                    [REQUIRED OUTPUT FORMAT]
                    **Do NOT output the table again.** Start with Section 1.
                    
                    ### 🔮 1. 타고난 명(命)과 기질
                    (Describe the metaphor: "{metaphor}". Explain the tension or harmony between Day and Month. Use bold text for elements.)
                    
                    ### 🗡️ 2. 특별한 능력과 직업 (재능 매핑)
                    (Analyze the '{shinsal}' mentioned above. Suggest specific jobs like 'Surgeon', 'Judge', 'Influencer' based on these stars.)
                    
                    ### 👁️ 3. 신령의 공명 (Accuracy Check)
                    (Ask a question related to their 'Special Stars' or a past clash year. e.g. "Did you feel isolated in 2023?")
                    
                    ### ☁️ 4. 가까운 미래의 흐름 (2025/2026)
                    (Explain the prediction: "{future_fact}". Explain *why* it happens.)
                    
                    ### ⚡ 5. 당신의 고민에 대한 해답
                    (Direct answer to: "{final_q}")
                    
                    ### 🛡️ 6. 신령의 처방 (Action Plan)
                    * **행동:** (Specific habit)
                    * **마음가짐:** (Mental advice)
                    * **개운 아이템:** (Color/Object/Direction)
                    
                    [[TECHNICAL_SECTION]]
                    (Explain the technical derivation.)
                    """
                    
                    st.session_state.saju_context = sys_p
                    st.session_state.analysis_complete = True
                    
                    msgs = [{"role": "system", "content": sys_p}, {"role": "user", "content": "Analyze."}]
                    
                    # 4. Display
                    with st.chat_message("assistant"):
                        st.markdown("### 📜 신령의 분석 보고서")
                        st.markdown(table_md)
                        st.markdown("---")
                        
                        full_resp = ""
                        resp_container = st.empty()
                        for chunk in generate_ai_response(msgs):
                            full_resp += chunk
                            resp_container.markdown(full_resp + "▌")
                        
                        if "[[TECHNICAL_SECTION]]" in full_resp:
                            main_r, tech_r = full_resp.split("[[TECHNICAL_SECTION]]")
                        else:
                            main_r, tech_r = full_resp, "분석 로직 포함."
                            
                        resp_container.markdown(main_r)
                        with st.expander("📚 분석 근거 (Technical Basis)"):
                            st.markdown(tech_r)
                            
                        final_content = f"### 📜 신령의 분석 보고서\n\n{table_md}\n\n---\n\n{main_r}"
                        st.session_state.messages.append({"role": "assistant", "content": final_content, "theory": tech_r})
                    
                    if not st.session_state.user_info_logged:
                        save_to_database(saju, b_date, b_time, final_q, is_lunar)
                        st.session_state.user_info_logged = True
                    st.rerun()
                else:
                    st.error(t["geo_error"])

# --- CHAT MODE ---
else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if "theory" in m:
                with st.expander("📚 분석 근거"):
                    st.markdown(m["theory"])
    
    if p := st.chat_input(t["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        msgs = [{"role": "system", "content": st.session_state.saju_context}]
        for m in st.session_state.messages[-4:]:
            msgs.append({"role": m["role"], "content": m["content"]})
            
        with st.chat_message("assistant"):
            full_resp = ""
            resp_container = st.empty()
            for chunk in generate_ai_response(msgs):
                full_resp += chunk
                resp_container.markdown(full_resp + "▌")
            
            if "[[TECHNICAL_SECTION]]" in full_resp:
                main_r, tech_r = full_resp.split("[[TECHNICAL_SECTION]]")
            else:
                main_r, tech_r = full_resp, ""
            
            resp_container.markdown(main_r)
            if tech_r:
                with st.expander("📚 분석 근거"):
                    st.markdown(tech_r)
            
            st.session_state.messages.append({"role": "assistant", "content": main_r, "theory": tech_r})
