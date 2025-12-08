import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim

# ==========================================
# 1. UI TEXT DICTIONARY (Language Pack)
# ==========================================
UI_TEXT = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "caption": "AI 정통 명리학 분석 시스템 v4.0",
        "sidebar_title": "설정 (Settings)",
        "reset_btn": "🔄 새로운 상담 (Reset)",
        "lang_btn": "🇺🇸 Switch to English",
        "dob_label": "생년월일",
        "time_label": "태어난 시간",
        "city_label": "태어난 도시 (예: Seoul, Busan)",
        "gender_label": "성별",
        "gender_options": ["남성", "여성"],
        "concern_label": "현재 고민 (비워두면 종합 운세를 분석합니다)",
        "concern_placeholder": "예: 이직 시기, 결혼 운, 재물 운...",
        "submit_btn": "📜 종합 분석 시작 (Analyze)",
        "loading_msg": "⏳ 천문 데이터 계산 및 3년 운세 흐름 분석 중...",
        "result_title": "📜 신령의 정밀 분석 보고서",
        "error_city": "⚠️ 도시 이름을 찾을 수 없습니다.",
        "disclaimer_title": "법적 면책 조항",
        "disclaimer_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 개척하는 것입니다.",
        "chat_placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong (Divine Spirit)",
        "caption": "AI Authentic Saju Analysis System v4.0",
        "sidebar_title": "Settings",
        "reset_btn": "🔄 Reset Session",
        "lang_btn": "🇰🇷 한국어로 전환",
        "dob_label": "Date of Birth",
        "time_label": "Birth Time",
        "city_label": "Birth City (e.g., Seoul, NYC)",
        "gender_label": "Gender",
        "gender_options": ["Male", "Female"],
        "concern_label": "Your Concern (Leave empty for General Reading)",
        "concern_placeholder": "e.g., Career change, Love life, Wealth...",
        "submit_btn": "📜 Analyze Destiny",
        "loading_msg": "⏳ Calculating Astral Data & 3-Year Timeline...",
        "result_title": "📜 Shinryeong's Analysis Report",
        "error_city": "⚠️ City not found.",
        "disclaimer_title": "Legal Disclaimer",
        "disclaimer_text": "This analysis is for reference only. It does not replace professional medical or legal advice.",
        "chat_placeholder": "Ask follow-up questions..."
    }
}

# ==========================================
# 2. SYSTEM CONFIGURATION
# ==========================================
st.set_page_config(page_title="Shinryeong Saju", page_icon="🔮", layout="centered")

if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

geolocator = Nominatim(user_agent="shinryeong_global_v4", timeout=10)

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"🚨 API Key Error: {e}")
    st.stop()

# ==========================================
# 3. LOGIC ENGINE (Timeline & Metaphysics)
# ==========================================
def get_coordinates(city_input):
    clean = city_input.strip()
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def analyze_timeline_logic(saju_data):
    """
    [LOGIC INJECTION]
    Calculates 3-Year Timeline (2024, 2025, 2026) based on Day Branch interactions.
    """
    day_stem = saju_data['Day'][0]
    day_branch = saju_data['Day'][3]
    full_str = saju_data['Year'] + saju_data['Month'] + saju_data['Day'] + saju_data['Time']
    
    # 1. Identity & Metaphor
    identity_map = {
        '갑': "Giant Tree (Pioneer)", '을': "Wild Flower (Survivor)",
        '병': "The Sun (Visionary)", '정': "Candle Light (Mentor)",
        '무': "Mountain (Guardian)", '기': "Fertile Earth (Nurturer)",
        '경': "Iron/Rock (Warrior)", '신': "Gemstone/Needle (Specialist)",
        '임': "Ocean (Strategist)", '계': "Rain/Mist (Advisor)"
    }
    metaphor = identity_map.get(day_stem, "Mystical Energy")

    # 2. Strength & Pattern
    # Simple Element Counting
    wood = full_str.count('갑') + full_str.count('을') + full_str.count('인') + full_str.count('묘')
    fire = full_str.count('병') + full_str.count('정') + full_str.count('사') + full_str.count('오')
    earth = full_str.count('무') + full_str.count('기') + full_str.count('진') + full_str.count('술') + full_str.count('축') + full_str.count('미')
    metal = full_str.count('경') + full_str.count('신') + full_str.count('신') + full_str.count('유')
    water = full_str.count('임') + full_str.count('계') + full_str.count('해') + full_str.count('자')
    
    counts = {'Wood': wood, 'Fire': fire, 'Earth': earth, 'Metal': metal, 'Water': water}
    weakest = min(counts, key=counts.get)
    
    # 3. Three-Year Timeline Logic (2024-2026)
    # 2024: Jin (Dragon), 2025: Sa (Snake), 2026: O (Horse)
    timeline = {}
    
    # 2024 (Gap-Jin) Analysis
    if day_branch == "술": timeline['2024'] = "Clash (Jin-Sul). Conflict in residence/spouse."
    elif day_branch == "유": timeline['2024'] = "Harmony (Jin-Yu). Good for contracts."
    else: timeline['2024'] = "Moderate energy. Focus on foundation."
    
    # 2025 (Eul-Sa) Analysis
    if day_branch == "해": timeline['2025'] = "Big Clash (Sa-Hae). Major movement/Travel/Job Change."
    elif day_branch in ["인", "신"]: timeline['2025'] = "Punishment (In-Sa-Shin). Adjustment of power/Health check."
    elif day_branch in ["유", "축"]: timeline['2025'] = "Harmony (Metal Alliance). Group success/Authority."
    else: timeline['2025'] = "Stable growth. Inner development."
    
    # 2026 (Byung-O) Analysis
    if day_branch == "자": timeline['2026'] = "Clash (Ja-O). Emotional stress/Change of environment."
    elif day_branch in ["인", "술"]: timeline['2026'] = "Harmony (Fire Alliance). Passion/Fame/Promotion."
    else: timeline['2026'] = "High energy (Fire). Active social life."

    return {
        "metaphor": metaphor,
        "counts": str(counts),
        "weakest": weakest,
        "timeline": timeline
    }

def generate_ai_response(messages, lang_mode):
    """Generates response enforcing the selected language."""
    # Ensure the system prompt has the language instruction
    messages[0]['content'] += f"\n[CRITICAL: OUTPUT MUST BE IN {lang_mode.upper()} LANGUAGE ONLY]"
    
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.6, max_tokens=3500, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except: continue
    yield "Error: AI System Busy."

# ==========================================
# 4. UI LAYOUT & INTERACTION
# ==========================================
# Sidebar Settings
with st.sidebar:
    st.title(UI_TEXT[st.session_state.lang]["sidebar_title"])
    
    # Language Toggle
    if st.button(UI_TEXT[st.session_state.lang]["lang_btn"]):
        st.session_state.lang = "en" if st.session_state.lang == "ko" else "ko"
        st.rerun()
        
    st.markdown("---")
    if st.button(UI_TEXT[st.session_state.lang]["reset_btn"]):
        st.session_state.clear()
        st.rerun()

# Main Title
t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption(t["caption"])

# Input Form
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        with c1:
            b_date = st.date_input(t["dob_label"], min_value=datetime(1940,1,1))
            b_time = st.time_input(t["time_label"], value=time(12,0))
        with c2:
            gender = st.radio(t["gender_label"], t["gender_options"])
            city = st.text_input(t["city_label"])
            
        concern = st.text_area(t["concern_label"], placeholder=t["concern_placeholder"], height=100)
        submit = st.form_submit_button(t["submit_btn"])
    
    if submit:
        if not city:
            st.error(t["error_city"])
        else:
            with st.spinner(t["loading_msg"]):
                coords, city_name = get_coordinates(city)
                if coords:
                    # 1. Logic Calculation
                    saju = calculate_saju_v3(b_date.year, b_date.month, b_date.day, 
                                           b_time.hour, b_time.minute, coords[0], coords[1])
                    facts = analyze_timeline_logic(saju)
                    
                    # 2. Determine Analysis Mode (Specific Concern vs Generic)
                    concern_mode = "Specific" if concern.strip() else "Generic"
                    final_concern = concern if concern.strip() else "General analysis of Wealth, Career, and Love."
                    
                    # 3. Construct System Prompt (The Cheatsheet)
                    sys_p = f"""
[SYSTEM ROLE]
You are 'Shinryeong', a Saju Master.
Language Mode: **{st.session_state.lang.upper()}** (Strictly follow this).
Tone: Mystical but Logical.

[INSTRUCTION]
Render the [Calculated Facts] into a structured report.
If 'Concern Mode' is 'Generic', cover Wealth, Career, and Love in Section 4.
If 'Concern Mode' is 'Specific', focus Section 4 entirely on the user's input.

[CALCULATED FACTS]
1. Identity: {facts['metaphor']}
2. Element Balance: {facts['counts']} (Weakest: {facts['weakest']})
3. Timeline Forecast:
   - 2024 (Dragon): {facts['timeline']['2024']}
   - 2025 (Snake): {facts['timeline']['2025']}
   - 2026 (Horse): {facts['timeline']['2026']}
4. User Concern: "{final_concern}" (Mode: {concern_mode})

[OUTPUT TEMPLATE ({st.session_state.lang})]
## {t['result_title']}

### 1. Identity & Core Energy
(Explain Identity metaphor. Mention Element Balance.)

### 2. The 3-Year Timeline (2024-2026)
* **2024 (Gap-Jin):** (Expand on timeline['2024'])
* **2025 (Eul-Sa):** (Expand on timeline['2025'])
* **2026 (Byung-O):** (Expand on timeline['2026'])

### 3. Deep Analysis: {final_concern}
(If mode is Generic: Analyze Wealth, Career, Love broadly.)
(If mode is Specific: Answer the user's specific question deeply.)

### 4. Shinryeong's Solution
* **Action:** (Practical advice based on timeline)
* **Remedy:** (Lucky element/color based on Weakest Element: {facts['weakest']})

"""
                    st.session_state.saju_context = sys_p
                    st.session_state.analysis_complete = True
                    
                    # 4. Generate & Stream Response
                    msgs = [{"role": "system", "content": sys_p}, 
                            {"role": "user", "content": "Analyze."}]
                    
                    with st.chat_message("assistant"):
                        full_resp = ""
                        res_box = st.empty()
                        for chunk in generate_ai_response(msgs, st.session_state.lang):
                            full_resp += chunk
                            res_box.markdown(full_resp + "▌")
                        res_box.markdown(full_resp)
                        st.session_state.messages.append({"role": "assistant", "content": full_resp})
                        
                        # 5. Show Disclaimer Warning (Like a sign)
                        st.warning(f"**[{t['disclaimer_title']}]**\n\n{t['disclaimer_text']}")
                    
                    st.rerun()

# Chat Interface
else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    # Show Disclaimer at the bottom of history if analysis is done
    st.warning(f"**[{t['disclaimer_title']}]**\n\n{t['disclaimer_text']}")

    if q := st.chat_input(t["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Context + History
        ctxt = [{"role": "system", "content": st.session_state.saju_context}]
        ctxt.extend(st.session_state.messages[-4:])
        
        with st.chat_message("assistant"):
            full_resp = ""
            res_box = st.empty()
            for chunk in generate_ai_response(ctxt, st.session_state.lang):
                full_resp += chunk
                res_box.markdown(full_resp + "▌")
            res_box.markdown(full_resp)
            st.session_state.messages.append({"role": "assistant", "content": full_resp})
