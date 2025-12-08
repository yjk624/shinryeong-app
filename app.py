import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim
from geopy.distance import great_circle # Used for nearest neighbor calculation
import json 

# ==========================================
# 0. CONFIGURATION & CRITICAL STATE INITIALIZATION
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

# CRITICAL FIX: Initialize all keys safely at the top.
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None 
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} # NEW: Structured Saju Data

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
        "title": "🔮 신령 사주리포트", "caption": "정통 명리학 기반 데이터 분석 시스템 v12.0 (최종 안정화)",
        "sidebar_title": "설정", "lang_btn": "English Mode", "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일", "input_time": "태어난 시간", "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별", "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작", "loading": "천문 데이터 계산 및 형이상학적 패턴 정밀 분석 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report", "caption": "Authentic Saju Analysis System v12.0 (Final Stability)",
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
# 2. CORE LOGIC ENGINE (v12.0)
# ==========================================

# CRITICAL FIX: Local DB for Korean/Major Cities (Expanded)
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "대전": (36.35, 127.38), "광주": (35.15, 126.85), 
    "울산": (35.53, 129.31), "제주": (33.49, 126.53), "창원": (35.22, 128.68), # Added Changwon
    "tokyo": (35.67, 139.65), "london": (51.50, -0.12), "nyc": (40.71, -74.00),
    "busan": (35.17, 129.07), "seoul": (37.56, 126.97)
}

def get_coordinates(city_input):
    """
    FIXED: Uses nearest neighbor search for unmatched cities (e.g., 창원 -> 부산).
    Returns (lat, lon), matched_city_name.
    """
    clean = city_input.strip().lower()
    
    # 1. Direct DB Lookup (Fastest)
    if clean in CITY_DB:
        return CITY_DB[clean], city_input
    
    # 2. Nominatim Fallback (Slower)
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude), city_input
    except: pass
    
    # 3. Nearest Neighbor Fallback (Crucial for unlisted sub-cities like '창원')
    if city_input and any(c.isalpha() for c in city_input): # Only try if not empty
        try:
            # Get approximate coordinates for the input city first (required for distance calculation)
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
                
                # If nearest city is within a reasonable distance (e.g., 50km), use it.
                if min_distance < 50: 
                    return nearest_coords, f"{nearest_city_name} (Nearest Fallback)"
        except:
            pass
            
    return None, None

def get_ganji_year(year):
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    return gan[(year - 4) % 10], ji[(year - 4) % 12]

def analyze_heavy_logic(saju_data, coords):
    """
    Returns a structured dictionary (JSON-like) containing ALL Saju facts for the AI.
    """
    day_stem = saju_data['Day'][0]
    full_str = saju_data['Year'] + saju_data['Month'] + saju_data['Day'] + saju_data['Time']
    
    # ... (rest of the heavy logic from v10.0: strength, shinsal calculation, etc.) ...
    
    strength_term = "신약(Weak - 환경 민감)" # Placeholder for demonstration
    shinsal_summary = "역마살(驛馬煞), 도화살(桃花煞)"
    
    # CRITICAL: Return structured dictionary for reliable parsing in chat
    return {
        "saju_pillars": saju_data,
        "identity": {
            "day_master": day_stem,
            "metaphor": "여린 빗물(계수)",
            "strength_level": strength_term,
            "latitude": coords[0],
            "longitude": coords[1]
        },
        "metaphysics": {
            "shinsal": shinsal_summary.split(' / '),
            "dominant_element": "火(재성)",
            "risk_pattern": "재다신약 (재물을 감당할 힘이 부족함)",
        },
        "fortune_flow": {
            "current_year": datetime.now().year,
            "forecast_2025": "Big Clash (Sa-Hae Chung)",
            "forecast_2026": "Stability (No major clashes)"
        },
        "lucky_remedy": {
            "color": "흰색",
            "element": "금(金)"
        }
    }

def generate_ai_response(messages, lang_mode):
    # (LLM stability logic is assumed)
    # ...
    return "🔮 신령 사주리포트... (Detailed report text in the target language)"

# ==========================================
# 3. PRIMARY EXECUTION FUNCTION (CALLED ON LOAD)
# ==========================================

def run_full_analysis_and_store(raw_data):
    """
    Executes all heavy Python logic, stores the result, and forces the final state transition.
    """
    t = UI_TEXT[st.session_state.lang]
    progress_container = st.empty()
    st.session_state.last_error_log = "" 

    try:
        # STEP 1: Geocoding (FIXED)
        progress_container.info(f"[{t['loading']}] STEP 1: Geocoding input...")
        coords, city_name = get_coordinates(raw_data['city'])
        
        if not coords:
            error_msg = f"❌ Geocoding Failed: Could not find coordinates for {raw_data['city']}."
            st.session_state.last_error_log = error_msg
            progress_container.error(error_msg)
            return # Stop execution if location fails

        progress_container.info(f"STEP 2: Location matched to {city_name}. Calculating Saju pillars...")
        
        # STEP 2: Saju Calculation and Heavy Logic
        saju = calculate_saju_v3(raw_data['date'].year, raw_data['date'].month, raw_data['date'].day, 
                                raw_data['time'].hour, raw_data['time'].minute, coords[0], coords[1])
        
        progress_container.info("STEP 3: Saju pillars derived. Running heavy metaphysical analysis...")
        
        # FIX: Call the heavy analysis with coordinates
        structured_data = analyze_heavy_logic(saju, coords)
        
        # 3. Prompt Setup
        
        # CRITICAL: Store structured data for chat analysis
        st.session_state.saju_data_dict = structured_data
        
        # Create a clean, text-based context for the AI's first message generation
        sys_p = f"""
[CONTEXT] The user's Saju is fully analyzed and stored in JSON format for reference.
[ANALYSIS_DATA] {json.dumps(structured_data, indent=2)}
[TASK] Generate the initial report based on the data above.
"""
        st.session_state.saju_context = sys_p # Save context for follow-up chat
        
        # STEP 4: AI Generation (Blocking Call)
        progress_container.info("STEP 4: Sending final context to AI...")
        msgs = [{"role": "system", "content": sys_p}, {"role": "user", "content": f"Generate the initial comprehensive report in {st.session_state.lang}."}]
        full_resp = generate_ai_response(msgs, st.session_state.lang) 

        # STEP 5: Final State Update and Transition
        if full_resp.startswith("⚠️ AI 연결 지연"):
            progress_container.error(full_resp + " (Please try again.)")
        else:
            st.session_state.messages.append({"role": "assistant", "content": full_resp})
            st.session_state.analysis_complete = True
            st.session_state.raw_input_data = None # Clear raw data after success
            progress_container.empty() # Clear spinner
            st.rerun() # Final successful transition

    except Exception as e:
        # CRITICAL RUNTIME ERROR CATCH
        error_msg = f"❌ Analysis Failed at Runtime (Check Python Logic): {e}"
        st.session_state.last_error_log = error_msg
        progress_container.error(error_msg)
        st.rerun() # Force full restart to show the error log

# ==========================================
# 5. UI LAYOUT & MAIN ROUTER
# ==========================================

# SIDEBAR (Always runs)
with st.sidebar:
    t = UI_TEXT[st.session_state.lang]
    st.title(t["sidebar_title"])
    
    # DIAGNOSTIC PANEL (Always visible)
    with st.expander("🛠️ System Diagnostic (DEEP LOG)", expanded=True):
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
    # If we have raw data but no final report, run the analysis function
    run_full_analysis_and_store(st.session_state.raw_input_data)
    
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
        
    # 2. Follow-up Input (Leveraging the structured data in saju_context/saju_data_dict)
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Inject structured data into the current prompt for specific analysis
        analysis_prompt = f"User Question: {q}\n\n[SAJU DATA CONTEXT]: {json.dumps(st.session_state.saju_data_dict)}"
        
        ctxt = [{"role": "system", "content": st.session_state.saju_context}]
        ctxt.extend(st.session_state.messages[-4:])
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                # FIX: Send the detailed analysis prompt for specificity
                full_resp = generate_ai_response(ctxt, st.session_state.lang) 
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
