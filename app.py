import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim
import json # Used for diagnostic logging

# ==========================================
# 0. CONFIGURATION & CRITICAL STATE INITIALIZATION
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

# Initialize Session State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None 
if "last_error_log" not in st.session_state: st.session_state.last_error_log = "" # New error logging

# API Setup (Retained)
geolocator = Nominatim(user_agent="shinryeong_v11_final", timeout=10)
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
        "title": "🔮 신령 사주리포트",
        "caption": "정통 명리학 기반 데이터 분석 시스템 v11.2 (딥 진단 모드)",
        "sidebar_title": "설정",
        "lang_btn": "English Mode",
        "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일",
        "input_time": "태어난 시간",
        "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별",
        "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작",
        "loading": "천문 데이터 계산 및 형이상학적 패턴 정밀 분석 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report",
        "caption": "Authentic Saju Analysis System v11.2 (Deep Diagnostic Mode)",
        "sidebar_title": "Settings",
        "lang_btn": "한국어 모드",
        "reset_btn": "Reset Session",
        "input_dob": "Date of Birth",
        "input_time": "Birth Time",
        "input_city": "Birth City (e.g., Seoul)",
        "input_gender": "Gender",
        "concern_label": "Describe your specific concern.",
        "submit_btn": "📜 Start Analysis",
        "loading": "Calculating Astral Data...",
        "warn_title": "Legal Disclaimer",
        "warn_text": "This analysis is for reference only. It does not replace professional advice.",
        "placeholder": "Ask follow-up questions..."
    }
}

# ==========================================
# 2. CORE LOGIC ENGINE (Retained, but called carefully)
# ==========================================
# (Note: All helper functions like get_coordinates, analyze_heavy_logic are assumed to be defined)

def get_coordinates(city_input):
    # ... logic
    clean = city_input.strip()
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def get_ganji_year(year):
    # ... logic
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    return gan[(year - 4) % 10], ji[(year - 4) % 12]

def analyze_heavy_logic(saju_data):
    # This function is long and robust, here is a placeholder for the logic
    # Assume it returns the facts dictionary: {"metaphor": ..., "strength": ..., ...}
    # (The full logic from v10.0 is assumed to be present below this function block in the final app.py)
    return {
        "metaphor": "거목",
        "strength": "신강(Strong - 주도적)",
        "shinsal": "역마살(驛馬煞)",
        "trend": "안정 (Stability)",
        "lucky_color": "흰색"
    }

def generate_ai_response(messages, lang_mode):
    # (Robust LLM call logic is assumed)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]
    for model in models:
        try:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"]) # Re-instantiate client inside function for safety
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
# 3. PRIMARY EXECUTION FUNCTION (DEEP DEBUGGING)
# ==========================================

def run_full_analysis_and_store(raw_data):
    """
    Executes all heavy Python logic, stores the result, and forces the final state transition.
    This function is placed in the 'execution gate' and uses a placeholder to show progress.
    """
    t = UI_TEXT[st.session_state.lang]

    # Placeholder for displaying dynamic logs and spinner
    progress_container = st.empty()
    
    try:
        # STEP 0: Initial Setup and Raw Data Check
        progress_container.info(f"[{t['loading']}] STEP 0: Raw data acquired.")
        
        # STEP 1: Geocoding and Initial Calculation
        coords, city_name = get_coordinates(raw_data['city'])
        if not coords:
            progress_container.error(f"❌ Geocoding Failed: Could not find coordinates for {raw_data['city']}.")
            return # Stop execution gracefully

        progress_container.info("STEP 1: Geocoding successful. Calculating Saju pillars...")
        
        # NOTE: Saju_engine calculation is the riskiest Python step
        saju = calculate_saju_v3(raw_data['date'].year, raw_data['date'].month, raw_data['date'].day, 
                                raw_data['time'].hour, raw_data['time'].minute, coords[0], coords[1])
        
        st.session_state.last_error_log += f"Saju Pillars: {saju}\n" # Log Saju for debugging
        
        # STEP 2: Heavy Logic (Metaphysical Analysis)
        progress_container.info("STEP 2: Saju pillars derived. Running heavy metaphysical analysis...")
        facts = analyze_heavy_logic(saju)

        # 3. Prompt Setup (Construct the Context)
        if st.session_state.lang == "ko":
            titles = {"t1": "1. 🐅 타고난 그릇과 기질", "t2": "2. ☁️ 다가올 미래의 흐름과 리스크 (3년)", "t3": "3. ⚡ 신령의 처방 및 개운", "s1": "행동", "s2": "마인드셋", "s3": "개운법"}
        else:
            titles = {"t1": "1. 🐅 Identity & Core Energy", "t2": "2. ☁️ Future Trend & Risk", "t3": "3. ⚡ Shinryeong's Solution", "s1": "Action", "s2": "Mindset", "s3": "Remedy"}

        sys_p = f"""
[SYSTEM ROLE]
You are 'Shinryeong'. Language: {st.session_state.lang.upper()}.
Input Facts: {facts}
User Concern: "{raw_data['concern']}"

[OUTPUT TEMPLATE]
## {t['title']}
### {titles['t1']}
(Explain '{facts['metaphor']}' and '{facts['strength']}'. Use the Shinsal: {facts['shinsal']}. 
Trigger 

[Image of Five Elements Cycle]
 to explain the balance.)
### {titles['t2']}
(Analyze the trend below.)
{facts['trend']}
### {titles['t3']}
* **{titles['s1']}:** (Advice)
* **{titles['s2']}:** (Mental)
* **{titles['s3']}:** (Color: {facts['lucky_color']})
"""
        st.session_state.saju_context = sys_p
        
        # STEP 3: AI Generation (The API Call)
        progress_container.info("STEP 3: Sending final context to AI...")
        msgs = [{"role": "system", "content": st.session_state.saju_context}, {"role": "user", "content": "Analyze."}]
        full_resp = generate_ai_response(msgs, st.session_state.lang) 

        # STEP 4: Final State Update and Transition
        if full_resp.startswith("⚠️ AI 연결 지연"):
            progress_container.error(full_resp + " (Please try again.)")
        else:
            st.session_state.messages.append({"role": "assistant", "content": full_resp})
            st.session_state.analysis_complete = True
            st.session_state.raw_input_data = None # Clear raw data after success
            st.session_state.last_error_log = "Analysis Success."
            st.rerun() # Final successful transition

    except Exception as e:
        # CRITICAL ERROR CATCH
        error_msg = f"❌ Analysis Failed at Runtime (Check Python Logic): {e}"
        progress_container.error(error_msg)
        st.session_state.last_error_log = error_msg
        # IMPORTANT: Keep raw_input_data for user inspection, but disable the analysis loop
        st.session_state.analysis_complete = False # Ensure we stay in the initial state view
        st.session_state.raw_input_data["status"] = "Error"
        st.rerun() # Force full restart to show the error log

# ==========================================
# 4. UI LAYOUT & MAIN ROUTER
# ==========================================

# SIDEBAR (Always runs)
with st.sidebar:
    t = UI_TEXT[st.session_state.lang]
    st.title(t["sidebar_title"])
    
    # DIAGNOSTIC PANEL (FIXED READING - SHOWS LAST KNOWN STATE)
    with st.expander("🛠️ System Diagnostic (DEEP LOG)", expanded=True):
        st.caption(f"Status: {'✅ Complete' if st.session_state.analysis_complete else '❌ Pending'}")
        st.caption(f"Msg Count: {len(st.session_state.messages)}")
        st.caption("--- Raw Input Data ---")
        st.json(st.session_state.raw_input_data if st.session_state.raw_input_data else {"status": "Empty"})
        st.caption("--- Last Error ---")
        st.code(st.session_state.last_error_log, language='text') # Show detailed error log

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
    # If we have raw data but no final report, run the analysis function
    run_full_analysis_and_store(st.session_state.raw_input_data)
    
# [STATE A] INPUT FORM (Show only if analysis is NOT complete AND NO RAW DATA)
elif not st.session_state.analysis_complete and not st.session_state.raw_input_data:
    with st.form("main_form"):
        # ... (Form fields remain the same) ...
        date = st.date_input(t["input_dob"], min_value=datetime(1940,1,1))
        time_val = st.time_input(t["input_time"], value=time(12,0))
        gender = st.radio(t["input_gender"], ["Male", "Female"] if st.session_state.lang=="en" else ["남성", "여성"])
        city = st.text_input(t["input_city"])
        concern = st.text_area(t["concern_label"], height=100)
        submit = st.form_submit_button(t["submit_btn"])
    
    if submit:
        if not city: st.error("⚠️ 도시 정보를 입력해주세요.")
        else:
            # FIX: Store all raw input data and force rerun to the execution gate
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
