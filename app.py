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
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None 
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "last_error_log" not in st.session_state: st.session_state.last_error_log = "" 

# API Setup
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
        "title": "🔮 신령 사주리포트", "caption": "정통 명리학 기반 데이터 분석 시스템 v11.4 (최종 안정화)",
        "sidebar_title": "설정", "lang_btn": "English Mode", "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일", "input_time": "태어난 시간", "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별", "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작", "loading": "천문 데이터 계산 및 형이상학적 패턴 정밀 분석 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report", "caption": "Authentic Saju Analysis System v11.4 (Final Stability)",
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
# 2. CORE LOGIC ENGINE (v11.4)
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "대전": (36.35, 127.38), "광주": (35.15, 126.85), 
    "울산": (35.53, 129.31), "제주": (33.49, 126.53), "창원": (35.22, 128.68),
    "tokyo": (35.67, 139.65), "london": (51.50, -0.12), "nyc": (40.71, -74.00),
    "busan": (35.17, 129.07), "seoul": (37.56, 126.97)
}

def get_coordinates(city_input):
    """ FINAL GEOCODING LOGIC: Uses Nearest Neighbor for robustness and speed. """
    clean = city_input.strip().lower()
    if clean in CITY_DB:
        return CITY_DB[clean], city_input
    
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude), city_input
    except: pass
            
    return None, None

def get_ganji_year(year):
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    return gan[(year - 4) % 10], ji[(year - 4) % 12]

def analyze_heavy_logic(saju_data, coords):
    """
    Final robust logic for fact injection.
    """
    day_stem = saju_data['Day'][0]
    month_branch = saju_data['Month'][3]
    full_str = saju_data['Year'] + saju_data['Month'] + saju_data['Day'] + saju_data['Time']
    
    # 1. Strength Calculation
    season_elem_map = {'인': '목', '묘': '목', '진': '목', '사': '화', '오': '화', '미': '화', '신': '금', '유': '금', '술': '금', '해': '수', '자': '수', '축': '수'}
    day_elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    my_elem = day_elem_map.get(day_stem, '토')
    month_elem = season_elem_map.get(month_branch, '토')
    supporters = {'목': ['수', '목'], '화': ['목', '화'], '토': ['화', '토'], '금': ['토', '금'], '수': ['금', '수']}
    
    score = 0
    if month_elem in supporters[my_elem]: score += 100
    else: score -= 100 
    
    for char in full_str:
        char_elem = ""
        if char in "갑을인묘": char_elem = '목'
        elif char in "병정사오": char_elem = '화'
        elif char in "무기진술축미": char_elem = '토'
        elif char in "경신신유": char_elem = '금'
        elif char in "임계해자": char_elem = '수'
        if char_elem in supporters[my_elem]: score += 10
            
    strength_term = "신강(Strong - 주도적)" if score >= 40 else "신약(Weak - 환경 민감)"
    
    # 2. Hanja/Metaphor Mapping
    identity_db = {'갑': "거목", '을': "화초", '병': "태양", '정': "촛불", '무': "태산", '기': "대지", '경': "바위", '신': "보석", '임': "바다", '계': "빗물"}
    
    # 3. Shinsal (살) Injection
    shinsal_list = []
    if any(x in full_str for x in ["인", "신", "사", "해"]): shinsal_list.append("역마살(驛馬煞): 활동성 강함, 이동과 변화")
    if any(x in full_str for x in ["자", "오", "묘", "유"]): shinsal_list.append("도화살(桃花煞): 인기를 끌고 주목받는 매력")
    shinsal_summary = " / ".join(shinsal_list) if shinsal_list else "평온한 기운"

    # 4. Future Trend (3 Years)
    current_year = datetime.now().year
    trend_data = []
    day_branch = saju_data['Day'][3]
    clashes = {"자":"오", "축":"미", "인":"신", "묘":"유", "진":"술", "사":"해", "오":"자", "미":"축", "신":"인", "유":"묘", "술":"진", "해":"사"}
    
    for y in range(current_year, current_year+3):
        stem, branch = get_ganji_year(y)
        rel_msg = "안정 (Stability)"
        if clashes.get(day_branch) == branch: rel_msg = f"⚠️ 충(Clash) - 변화와 이동수"
        trend_data.append(f"{y}년({stem}{branch}년): {rel_msg}")

    # 5. Lucky Color
    weak_colors = {'목':'검은색(수)', '화':'초록색(목)', '토':'붉은색(화)', '금':'노란색(토)', '수':'흰색(금)'}
    lucky_color = weak_colors.get(my_elem) if score < 40 else '흰색'
    
    return {
        "metaphor": identity_db.get(day_stem, "기운"),
        "strength": strength_term,
        "shinsal": shinsal_summary,
        "trend": trend_data,
        "lucky_color": lucky_color
    }

def generate_ai_response(messages, lang_mode):
    # System Instruction Injection (Tighter language control)
    instruction = (
        "[CRITICAL INSTRUCTION]\n"
        f"Language: {lang_mode.upper()} ONLY. DO NOT use English or any foreign language words (e.g., Master, Level, VS, or, жел정) in the output text body.\n"
        "Persona: Use the formal and mystical '하게체' (~하네, ~라네).\n"
        "RULE: Every time a complex Saju term (e.g., 신강, 신약, 역마살, 도화살) is used, define it immediately in simple Korean sentences (e.g., '신강이란 곧은 소나무와 같은 힘을 말하는 것일세.').\n"
        "RULE: When asked a follow-up question (e.g., '재물운'), analyze the stored SAJU DATA CONTEXT for relevant elements and provide a pinpoint, detailed answer, not a generic report summary.\n"
    )
    if messages[0]['role'] == 'system':
        messages[0]['content'] += "\n" + instruction
    
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
# 3. PRIMARY EXECUTION FUNCTION (DEEP DEBUGGING)
# ==========================================

def run_full_analysis_and_store(raw_data):
    """
    Executes all heavy Python logic, stores the result, and forces the final state transition.
    """
    t = UI_TEXT[st.session_state.lang]
    progress_container = st.empty()
    st.session_state.last_error_log = "" 

    try:
        # STEP 0: Geocoding and Initial Calculation
        progress_container.info(f"[{t['loading']}] STEP 0/5: Geocoding input...")
        
        coords, city_name = get_coordinates(raw_data['city'])
        
        if not coords:
            st.session_state.last_error_log = f"❌ GeoCoding Failed for {raw_data['city']}."
            raise Exception(f"GeoCoding Failed for {raw_data['city']}.")

        progress_container.info(f"STEP 1/5: Location matched to {city_name}. Calculating Saju pillars...")
        
        # STEP 1: Saju Calculation (saju_engine.py)
        saju = calculate_saju_v3(raw_data['date'].year, raw_data['date'].month, raw_data['date'].day, 
                                raw_data['time'].hour, raw_data['time'].minute, coords[0], coords[1])
        
        # STEP 2: Heavy Logic (Metaphysical Analysis)
        progress_container.info("STEP 2/5: Saju pillars derived. Running heavy metaphysical analysis...")
        facts = analyze_heavy_logic(saju, coords)

        # 3. Prompt Construction
        progress_container.info("STEP 3/5: Context generation successful. Preparing for AI call...")
        
        if st.session_state.lang == "ko":
            titles = {"t1": "1. 🐅 타고난 그릇과 기질", "t2": "2. ☁️ 다가올 미래의 흐름과 리스크 (3년)", "t3": "3. ⚡ 신령의 처방 및 개운", "s1": "행동", "s2": "마인드셋", "s3": "개운법"}
        else:
            titles = {"t1": "1. 🐅 Identity & Core Energy", "t2": "2. ☁️ Future Trend & Risk", "t3": "3. ⚡ Shinryeong's Solution", "s1": "Action", "s2": "Mindset", "s3": "Remedy"}

        sys_p = f"""
[SYSTEM ROLE]
You are 'Shinryeong'. Language: {st.session_state.lang.upper()}. Persona: Use the formal and mystical '하게체' (~하네, ~라네).
[IMPORTANT: EXPLAIN COMPLEX TERMS SIMPLY. NO FOREIGN LANGUAGE IN OUTPUT.]
Input Facts: {facts}
User Concern: "{raw_data['concern']}"

[OUTPUT TEMPLATE]
## {t['title']}
### {titles['t1']}
(Explain '{facts['metaphor']}' and '{facts['strength']}'. Define '{facts['strength']}' immediately after using it. Use the Shinsal: {facts['shinsal']}. 
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
        st.session_state.saju_data_dict = facts # Save structured data for chat
        
        # STEP 4: AI Generation
        progress_container.info("STEP 4/5: Sending final context to AI...")
        msgs = [{"role": "system", "content": sys_p}, {"role": "user", "content": "Analyze."}]
        full_resp = generate_ai_response(msgs, st.session_state.lang) 
        
        # STEP 5: Final State Update and Transition
        progress_container.info("STEP 5/5: AI response received. Finalizing state...")
        
        if full_resp.startswith("⚠️ AI 연결 지연"):
            progress_container.error(full_resp)
        else:
            st.session_state.messages.append({"role": "assistant", "content": full_resp})
            st.session_state.analysis_complete = True
            st.session_state.raw_input_data = None # Clear raw data after success
            progress_container.empty()
            st.rerun() # Final successful transition

    except Exception as e:
        # CRITICAL RUNTIME ERROR CATCH
        error_msg = f"❌ Runtime Logic Error: {e}"
        st.session_state.last_error_log = error_msg
        progress_container.error(f"❌ Analysis Failed. Check logs for details. Error: {e}")
        st.session_state.analysis_complete = False 
        st.rerun() # Force full restart to show the error log

# ==========================================
# 4. UI LAYOUT & MAIN ROUTER
# ==========================================

# SIDEBAR (Always runs)
with st.sidebar:
    t = UI_TEXT[st.session_state.lang]
    st.title(t["sidebar_title"])
    
    # DIAGNOSTIC PANEL (Always visible)
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
        
    # 2. Follow-up Input
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Inject structured data into the current prompt for specific analysis
        analysis_prompt = f"User Question: {q}\n\n[SAJU DATA CONTEXT]: {json.dumps(st.session_state.saju_data_dict)}"
        
        # Context + History
        ctxt = [{"role": "system", "content": st.session_state.saju_context}]
        ctxt.extend(st.session_state.messages[-4:])
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                # Send the detailed analysis prompt for specificity
                full_resp = generate_ai_response(ctxt, st.session_state.lang) 
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
