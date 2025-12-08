import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim

# ==========================================
# 1. UI TEXT & CONFIGURATION
# ==========================================
st.set_page_config(page_title="신령 (Shinryeong)", page_icon="🔮", layout="centered")

UI_TEXT = {
    "ko": {
        "title": "🔮 신령 (Shinryeong)",
        "caption": "정통 명리학 기반 운명 분석 시스템 v5.0",
        "sidebar_title": "설정",
        "lang_btn": "English",
        "reset_btn": "상담 종료 및 초기화",
        "dob": "생년월일",
        "time": "태어난 시간",
        "city": "태어난 도시 (예: Seoul, Busan)",
        "gender": "성별",
        "concern": "당신의 고민을 구체적으로 적어주세요.",
        "submit": "📜 정밀 분석 시작",
        "loading": "천문 데이터 계산 및 형이상학적 패턴 분석 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong",
        "caption": "Authentic Saju Analysis System v5.0",
        "sidebar_title": "Settings",
        "lang_btn": "한국어",
        "reset_btn": "Reset Session",
        "dob": "Date of Birth",
        "time": "Birth Time",
        "city": "Birth City",
        "gender": "Gender",
        "concern": "Describe your specific concern.",
        "submit": "📜 Start Analysis",
        "loading": "Calculating Astral Data & Metaphysical Patterns...",
        "warn_title": "Legal Disclaimer",
        "warn_text": "This analysis is for reference only. It does not replace professional advice.",
        "placeholder": "Ask follow-up questions..."
    }
}

# Initialize State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

# API & Geocoder
geolocator = Nominatim(user_agent="shinryeong_v5_master", timeout=10)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"CRITICAL ERROR: API Key Missing. {e}")
    st.stop()

# ==========================================
# 2. HEAVY LOGIC ENGINE (The Brain)
# ==========================================
def get_coordinates(city_input):
    clean = city_input.strip()
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def get_ganji_year(year):
    """Calculates Heavenly Stem & Earthly Branch for ANY year."""
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    
    stem_idx = (year - 4) % 10
    branch_idx = (year - 4) % 12
    return gan[stem_idx], ji[branch_idx]

def analyze_universal_timeline(saju_data):
    """
    [DYNAMIC TIMELINE ENGINE]
    Calculates interactions (Clash/Harmony) for the current year + next 2 years.
    Also calculates deep metaphysical traits (Ten Gods, Strength).
    """
    day_stem = saju_data['Day'][0]
    day_branch = saju_data['Day'][3]
    full_str = saju_data['Year'] + saju_data['Month'] + saju_data['Day'] + saju_data['Time']
    
    # 1. Identity Metaphor (Vocabulary Injection)
    identity_db = {
        '갑': "Giant Tree (Pioneer) - Straightforward, Leadership, Stubborn.",
        '을': "Ivy/Flower (Survivor) - Flexible, Adaptive, Resilient.",
        '병': "The Sun (Visionary) - Passionate, Expressive, Public Figure.",
        '정': "Candle Light (Mentor) - Focused, Warm, Detail-oriented.",
        '무': "Mountain (Guardian) - Trustworthy, Slow-mover, Heavy.",
        '기': "Fertile Earth (Nurturer) - Practical, Motherly, Resourceful.",
        '경': "Iron/Axe (Warrior) - Decisive, Loyal, Sharp.",
        '신': "Gemstone/Needle (Specialist) - Sensitive, Precise, Sharp-tongued.",
        '임': "Ocean (Strategist) - Deep wisdom, Adaptive, Flowing.",
        '계': "Rain/Mist (Advisor) - Intuitive, Gentle,渗透 (Permeating)."
    }
    metaphor = identity_db.get(day_stem, "Mystical Energy")

    # 2. Element Analysis & Strength (Sin-gang/Sin-yak)
    wood = full_str.count('갑') + full_str.count('을') + full_str.count('인') + full_str.count('묘')
    fire = full_str.count('병') + full_str.count('정') + full_str.count('사') + full_str.count('오')
    earth = full_str.count('무') + full_str.count('기') + full_str.count('진') + full_str.count('술') + full_str.count('축') + full_str.count('미')
    metal = full_str.count('경') + full_str.count('신') + full_str.count('신') + full_str.count('유')
    water = full_str.count('임') + full_str.count('계') + full_str.count('해') + full_str.count('자')
    
    counts = {'Wood': wood, 'Fire': fire, 'Earth': earth, 'Metal': metal, 'Water': water}
    
    # Simple Strength Calc: My Element + Mother Element vs Others
    # (This is a simplified logic for demo; real engine is more complex)
    elem_list = ['Wood', 'Fire', 'Earth', 'Metal', 'Water']
    my_elem_idx = -1
    if day_stem in ['갑', '을']: my_elem_idx = 0
    elif day_stem in ['병', '정']: my_elem_idx = 1
    elif day_stem in ['무', '기']: my_elem_idx = 2
    elif day_stem in ['경', '신']: my_elem_idx = 3
    elif day_stem in ['임', '계']: my_elem_idx = 4
    
    my_force = counts[elem_list[my_elem_idx]] + counts[elem_list[(my_elem_idx-1)%5]] # Me + Resource
    strength = "Sin-gang (Strong Self)" if my_force >= 4 else "Sin-yak (Weak Self)"
    
    # 3. Dynamic Timeline Calculation (Current Year + 2)
    current_year = datetime.now().year
    timeline_data = {}
    
    for y in range(current_year, current_year + 3):
        y_stem, y_branch = get_ganji_year(y)
        
        # Interaction Logic
        prediction = f"General flow of {y_stem} (Stem) and {y_branch} (Branch)."
        
        # Clash (Chung) Logic - Day Branch vs Year Branch
        clashes = {
            "자": "오", "축": "미", "인": "신", "묘": "유", "진": "술", "사": "해",
            "오": "자", "미": "축", "신": "인", "유": "묘", "술": "진", "해": "사"
        }
        if clashes.get(day_branch) == y_branch:
            prediction = "**⚠️ CLASH (Chung):** Conflict, Movement, Job Change, Stress."
        
        # Harmony (Hap) Logic
        harmonies = {
            "자": "축", "축": "자", "인": "해", "해": "인", "묘": "술", "술": "묘",
            "진": "유", "유": "진", "사": "신", "신": "사", "오": "미", "미": "오"
        }
        if harmonies.get(day_branch) == y_branch:
            prediction = "**✨ HARMONY (Hap):** Contracts, Marriage, New Team, Stability."
            
        # Special Stars (Yeokma - Travel)
        if y_branch in ["인", "신", "사", "해"]:
            prediction += " (High Mobility / Travel Energy)"
            
        timeline_data[y] = f"{y} ({y_stem}{y_branch}): {prediction}"

    return {
        "metaphor": metaphor,
        "strength": strength,
        "counts": counts,
        "weakest": min(counts, key=counts.get),
        "dominant": max(counts, key=counts.get),
        "timeline": timeline_data
    }

def generate_ai_response(messages, lang_mode):
    """
    Robust Generation with Retries.
    Ensures response even if API is slightly busy.
    """
    # Enforce System Instruction
    messages[0]['content'] += f"\n[CRITICAL: OUTPUT MUST BE IN {lang_mode.upper()} LANGUAGE. Use 'Shinryeong' Persona.]"
    
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
    
    for attempt in range(3): # Retry logic
        for model in models:
            try:
                stream = client.chat.completions.create(
                    model=model, messages=messages, temperature=0.6, max_tokens=4000, stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return # Success
            except: 
                time_module.sleep(1) # Wait 1 sec before retry
                continue
                
    yield "⚠️ (Connection unstable. Please press enter again.) 신령이 깊은 명상 중입니다..."

# ==========================================
# 3. UI LAYOUT & INTERACTION
# ==========================================
with st.sidebar:
    st.title(UI_TEXT[st.session_state.lang]["sidebar_title"])
    
    # Simple Text Button
    if st.button(UI_TEXT[st.session_state.lang]["lang_btn"]):
        st.session_state.lang = "en" if st.session_state.lang == "ko" else "ko"
        st.rerun()
        
    st.markdown("---")
    if st.button(UI_TEXT[st.session_state.lang]["reset_btn"]):
        st.session_state.clear()
        st.rerun()

# Main Header
t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption(t["caption"])

# INITIAL WARNING SIGN (Before Analysis)
st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

# Input Form
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        with c1:
            b_date = st.date_input(t["dob"], min_value=datetime(1940,1,1))
            b_time = st.time_input(t["time"], value=time(12,0))
        with c2:
            gender = st.radio(t["gender"], ["Male", "Female"] if st.session_state.lang == "en" else ["남성", "여성"])
            city = st.text_input(t["city"])
            
        concern = st.text_area(t["concern"], height=100)
        submit = st.form_submit_button(t["submit"])
    
    if submit:
        if not city:
            st.error("⚠️ City is required.")
        else:
            with st.spinner(t["loading"]):
                coords, city_name = get_coordinates(city)
                if coords:
                    # 1. Logic Calculation
                    saju = calculate_saju_v3(b_date.year, b_date.month, b_date.day, 
                                           b_time.hour, b_time.minute, coords[0], coords[1])
                    
                    # 2. RUN HEAVY ENGINE
                    facts = analyze_universal_timeline(saju)
                    
                    # 3. Construct Context (The Cheatsheet)
                    sys_p = f"""
[SYSTEM ROLE]
You are 'Shinryeong', a legendary Saju Master.
Language: {st.session_state.lang.upper()} ONLY.
Tone: Mystical, Authoritative, Detailed, Metaphorical.

[INSTRUCTION]
Expand the [Calculated Facts] into a full report.
- Do not summarize. Write at least 4-5 sentences per section.
- Use the metaphors provided.
- If suggesting a remedy, provide a specific action or item.

[CALCULATED FACTS]
1. Identity: {facts['metaphor']}
2. Energy Balance: {facts['strength']} (Dominant: {facts['dominant']}, Weakest: {facts['weakest']})
3. 3-Year Forecast:
   {facts['timeline']}
4. User Concern: "{concern if concern else 'General Life Analysis'}"

[OUTPUT TEMPLATE]
## {t['title']} Analysis Report

### 1. 🐅 Identity & Core Energy
(Use Fact 1 & 2. Explain the nature metaphor vividly. Explain 'Sin-gang/Sin-yak'.)
(Trigger:
 to explain balance.)

### 2. ☁️ The Universal Timeline ({datetime.now().year}-{datetime.now().year+2})
(Use Fact 3. Go through each year. Explain the 'Why' - Clash or Harmony?)
* **{datetime.now().year}:** ...
* **{datetime.now().year+1}:** ...
* **{datetime.now().year+2}:** ...

### 3. 🔍 Deep Dive: {concern if concern else 'Wealth & Career'}
(Analyze the concern deeply based on Fact 2 'Dominant Element'. Provide Phenomenon -> Risk -> Advice.)

### 4. ⚡ Shinryeong's Solution
* **Action:** (Practical advice)
* **Remedy:** (Lucky color based on Weakest Element: {facts['weakest']})

"""
                    st.session_state.saju_context = sys_p
                    st.session_state.analysis_complete = True
                    
                    # 4. Generate Response
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
                    st.rerun()

# Chat Interface
else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    # Warning at bottom as well
    st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Context + History (Limit history to save tokens)
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
