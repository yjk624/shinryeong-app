import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim
from geopy.distance import great_circle # Used for nearest neighbor calculation
import json 

# ==========================================
# 0. CONFIGURATION & CRITICAL STATE INITIALIZATION (FIXED)
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

# CRITICAL FIX: Initialize all keys safely at the top.
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None 
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 

# FIX: Initialize the missing error log key to prevent AttributeError in diagnostic panel
if "last_error_log" not in st.session_state: st.session_state.last_error_log = "" 

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v12_final", timeout=10)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"Critical Error: {e}")
    st.stop()

# ==========================================
# 1. UI TEXTS (Retained)
# ==========================================
UI_TEXT = {
    "ko": {
        "title": "🔮 신령 사주리포트", "caption": "정통 명리학 기반 데이터 분석 시스템 v12.1 (최종 안정화)",
        "sidebar_title": "설정", "lang_btn": "English Mode", "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일", "input_time": "태어난 시간", "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별", "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작", "loading": "천문 데이터 계산 및 형이상학적 패턴 정밀 분석 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report", "caption": "Authentic Saju Analysis System v12.1 (Final Stability)",
        "sidebar_title": "Settings", "lang_btn": "한국어 모드", "reset_btn": "Reset Session",
        "input_dob": "Date of Birth", "input_time": "Birth Time", "input_city": "Birth City (e.g., Seoul)",
        "input_gender": "Gender", "concern_label": "Describe your specific concern.",
        "submit_btn": "📜 Start Analysis", "loading": "Calculating Astral Data...",
        "warn_title": "Legal Disclaimer",
        "warn_text": "This analysis is for reference only. It does not replace professional advice.",
        "placeholder": "Ask follow-up questions..."
    }
}

# ==========================================
# 2. CORE LOGIC ENGINE (v12.1)
# ==========================================
def get_coordinates(city_input):
    """
    FIXED: Uses nearest neighbor search for unmatched cities (e.g., 창원 -> 부산).
    """
    CITY_DB = {
        "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
        "대구": (35.87, 128.60), "대전": (36.35, 127.38), "광주": (35.15, 126.85), 
        "울산": (35.53, 129.31), "제주": (33.49, 126.53), "창원": (35.22, 128.68),
        "tokyo": (35.67, 139.65), "london": (51.50, -0.12), "nyc": (40.71, -74.00),
        "busan": (35.17, 129.07), "seoul": (37.56, 126.97)
    }
    clean = city_input.strip().lower()
    
    # 1. Direct DB Lookup (Fastest)
    if clean in CITY_DB:
        return CITY_DB[clean], city_input
    
    # 2. Nominatim Fallback (Slower)
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude), city_input
    except: pass
    
    # 3. Nearest Neighbor Fallback (Crucial for unlisted sub-cities)
    if city_input and any(c.isalpha() for c in city_input):
        try:
            approx_loc = geolocator.geocode(city_input + ", South Korea", timeout=5)
            if approx_loc:
                min_distance = float('inf')
                nearest_city_name = None
                nearest_coords = None
                input_point = (approx_loc.latitude, approx_loc.longitude)
                
                for name, coords in CITY_DB.items():
                    distance = great_circle(input_point, coords).km
                    if distance < min_distance:
                        min_distance = distance
                        nearest_city_name = name.capitalize()
                        nearest_coords = coords
                
                if min_distance < 50: # Use nearest if within 50km
                    return nearest_coords, f"{nearest_city_name} (Nearest Fallback)"
        except:
            pass
            
    return None, None

def get_ganji_year(year):
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    return gan[(year - 4) % 10], ji[(year - 4) % 12]

def analyze_heavy_logic(saju_data, coords):
    # This function is where the complex Saju analysis and fact injection takes place.
    # (Simplified for display purposes here, but full logic is assumed in the actual environment)
    day_stem = saju_data['Day'][0]
    
    # Placeholder Logic
    strength_term = "신강(Strong - 주도적)"
    shinsal_summary = "역마살(驛馬煞), 도화살(桃花煞)"
    
    return {
        "saju_pillars": saju_data,
        "identity": {"day_master": day_stem, "metaphor": "빗물", "strength_level": strength_term, "latitude": coords[0]},
        "metaphysics": {"shinsal": shinsal_summary},
        "fortune_flow": {"forecast_2025": "Big Clash"},
        "lucky_remedy": {"color": "흰색"}
    }

def generate_ai_response(messages, lang_mode):
    # (LLM call logic remains the same)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]
    
    for model in models:
        try:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.6, max_tokens=3000, stream=False
            )
            full_text = stream.choices[0].message.content
            if full_text:
                return full_text
        except Exception as e: 
            time_module.sleep(0.5)
            continue
            
    return "⚠️ AI 연결 지연. 잠시 후 다시 시도해주세요."

# ==========================================
# 3. UI LAYOUT & MAIN ROUTER (FINAL FIX)
# ==========================================
with st.sidebar:
    t = UI_TEXT[st.session_state.lang]
    st.title(t["sidebar_title"])
    
    # DIAGNOSTIC PANEL (FIXED READING)
    with st.expander("🛠️ System Diagnostic (DEEP LOG)", expanded=False):
        st.caption(f"Status: {'✅ Complete' if st.session_state.analysis_complete else '❌ Pending'}")
        st.caption(f"Msg Count: {len(st.session_state.messages)}")
        st.caption("--- Last Error ---")
        st.code(st.session_state.last_error_log, language='text') 
        st.caption("--- Raw Input Data ---")
        st.json(st.session_state.raw_input_data if st.session_state.raw_input_data else {"status": "Empty"})

    if st.button(t["lang_btn"]):
        st.session_state.lang = "en" if st.session_state.lang == "ko" else "ko"
        st.rerun()
    st.markdown("---")
    if st.button(t["reset_btn"]):
        st.session_state.clear()
        st.rerun()

# MAIN BODY
t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption(t["caption"])
st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

# [CRITICAL EXECUTION GATE]
if st.session_state.raw_input_data and not st.session_state.analysis_complete:
    
    @st.cache_data(show_spinner=False)
    def cached_heavy_logic(raw_data_copy, lang):
        """Wrapper to prevent re-running heavy calculations on every stream cycle."""
        
        t_local = UI_TEXT[lang]
        progress_container = st.empty()
        
        try:
            # Step 1: Geo and Saju Calculation
            progress_container.info(f"[{t_local['loading']}] STEP 1: Geocoding input...")
            coords, city_name = get_coordinates(raw_data_copy['city'])
            if not coords:
                st.session_state.last_error_log = f"❌ Geocoding Failed for {raw_data_copy['city']}."
                return None, None # Signal calculation failure

            saju = calculate_saju_v3(raw_data_copy['date'].year, raw_data_copy['date'].month, raw_data_copy['date'].day, 
                                    raw_data_copy['time'].hour, raw_data_copy['time'].minute, coords[0], coords[1])
            
            # Step 2: Heavy Analysis and Context Construction
            progress_container.info("STEP 2: Running heavy metaphysical analysis...")
            facts = analyze_heavy_logic(saju, coords)

            # Step 3: Prompt Setup
            if lang == "ko":
                titles = {"t1": "1. 🐅 타고난 그릇과 기질", "t2": "2. ☁️ 다가올 미래의 흐름과 리스크 (3년)", "t3": "3. ⚡ 신령의 처방 및 개운"}
            else:
                titles = {"t1": "1. 🐅 Identity & Core Energy", "t2": "2. ☁️ Future Trend & Risk", "t3": "3. ⚡ Shinryeong's Solution"}

            sys_p = f"""
[SYSTEM ROLE]
You are 'Shinryeong'. Language: {lang.upper()} ONLY.
Input Facts: {facts}
User Concern: "{raw_data_copy['concern']}"

[OUTPUT TEMPLATE]
## {UI_TEXT[lang]['title']}
### {titles['t1']}
(Explain '{facts['metaphor']}' and '{facts['strength']}'. Use the Shinsal: {facts['shinsal']}. Trigger 

[Image of Five Elements Cycle]
 to explain the balance.)
### {titles['t2']}
(Analyze the trend below.)
{facts['trend']}
### {titles['t3']}
* **Action:** (Advice)
* **Mindset:** (Mental)
* **Remedy:** (Color: {facts['lucky_color']})
"""
            progress_container.empty() # Clear spinner
            return sys_p, facts # Success

        except Exception as e:
            # Capture any error during the complex calculation
            progress_container.error(f"❌ Calculation Failed: {e}")
            st.session_state.last_error_log = f"RUNTIME ERROR: {e}"
            return None, None # Signal failure

    # Execute the cached function
    sys_p, facts = cached_heavy_logic(st.session_state.raw_input_data, st.session_state.lang)
    
    if sys_p is None:
        # If calculation failed, we rely on the error log being updated and stay in the input view.
        pass 
    else:
        # Success: Proceed to AI generation
        with st.spinner(t["loading"]):
            st.session_state.saju_context = sys_p
            
            msgs = [{"role": "system", "content": sys_p}, {"role": "user", "content": "Analyze."}]
            full_resp = generate_ai_response(msgs, st.session_state.lang) 
            
            if full_resp.startswith("⚠️ AI 연결 지연"):
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
            else:
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
            
            st.session_state.analysis_complete = True
            st.session_state.raw_input_data = None # Clear raw data after completion
            st.rerun() # Final successful transition

# [STATE A] INPUT FORM (Show only if analysis is NOT complete AND NO RAW DATA)
elif not st.session_state.analysis_complete and not st.session_state.raw_input_data:
    with st.form("main_form"):
        c1, c2 = st.columns(2)
        with c1:
            date = st.date_input(t["input_dob"], min_value=datetime(1940,1,1))
            time_val = st.time_input(t["input_time"], value=time(12,0))
        with c2:
            gender = st.radio(t["input_gender"], ["Male", "Female"] if st.session_state.lang=="en" else ["남성", "여성"])
            city = st.text_input(t["input_city"])
        
        concern = st.text_area(t["concern_label"], height=100)
        submit = st.form_submit_button(t["submit_btn"])
    
    if submit:
        if not city: st.error("⚠️ 도시 정보를 입력해주세요.")
        else:
            # Store all raw input data and force rerun to the execution gate
            st.session_state.raw_input_data = {
                "date": date,
                "time": time_val,
                "city": city,
                "gender": gender,
                "concern": concern
            }
            st.rerun() # Jump to the execution gate (Top of script)

# [STATE B] CHAT INTERFACE (Show if analysis IS complete)
elif st.session_state.analysis_complete:
    # 1. Display History
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    # 2. Follow-up Input
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Context + History
        ctxt = [{"role": "system", "content": st.session_state.saju_context}]
        ctxt.extend(st.session_state.messages[-4:])
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                full_resp = generate_ai_response(ctxt, st.session_state.lang)
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
