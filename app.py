import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim

# ==========================================
# 0. DIAGNOSTIC & CONFIGURATION
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

# Initialize Session State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v8_final", timeout=10)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"Critical Error: {e}")
    st.stop()

# ==========================================
# 1. UI TEXTS
# ==========================================
UI_TEXT = {
    "ko": {
        "title": "🔮 신령 사주리포트",
        "caption": "정통 명리학 기반 데이터 분석 시스템 v8.1 (정밀도 개선)",
        "sidebar_title": "설정",
        "lang_btn": "English Mode",
        "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일",
        "input_time": "태어난 시간",
        "input_city": "태어난 도시 (예: 서울, 부산)",
        "input_gender": "성별",
        "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작",
        "loading": "천문 데이터 계산 및 신강/신약 패턴 정밀 분석 중...",
        "warn_title": "법적 면책 조항",
        "warn_text": "본 분석은 통계적 참고자료이며, 의학적/법률적 효력이 없습니다. 운명은 본인의 선택으로 완성됩니다.",
        "placeholder": "추가 질문을 입력하세요..."
    },
    "en": {
        "title": "🔮 Shinryeong Destiny Report",
        "caption": "Authentic Saju Analysis System v8.1 (Accuracy Improved)",
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
# 2. CORE LOGIC ENGINE (Sin-gang/Sin-yak FIX)
# ==========================================
def get_coordinates(city_input):
    clean = city_input.strip()
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def get_ganji_year(year):
    gan = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    ji = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    return gan[(year - 4) % 10], ji[(year - 4) % 12]

def analyze_heavy_logic(saju_data):
    """
    [CRITICAL FIX: Season Weighted Score]
    Guarantees Sin-yak for hostile season Saju like Gye-Su in O-Wol.
    """
    day_stem = saju_data['Day'][0]
    month_branch = saju_data['Month'][3]
    full_str = saju_data['Year'] + saju_data['Month'] + saju_data['Day'] + saju_data['Time']
    
    # Element Mappings
    season_elem_map = {'인': '목', '묘': '목', '진': '목', '사': '화', '오': '화', '미': '화', '신': '금', '유': '금', '술': '금', '해': '수', '자': '수', '축': '수'}
    day_elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    my_elem = day_elem_map.get(day_stem, '토')
    month_elem = season_elem_map.get(month_branch, '토')
    supporters = {'목': ['수', '목'], '화': ['목', '화'], '토': ['화', '토'], '금': ['토', '금'], '수': ['금', '수']}
    
    score = 0
    
    # 1. Season Check (Highest Weight: +100/-100)
    if month_elem in supporters[my_elem]: score += 100
    else: score -= 100 # Kim Yongjun case starts here (-100)
        
    # 2. Deuk-se Check (Pillar Support: +10 per char)
    support_count = 0
    for char in full_str:
        char_elem = ""
        if char in "갑을인묘": char_elem = '목'
        elif char in "병정사오": char_elem = '화'
        elif char in "무기진술축미": char_elem = '토'
        elif char in "경신신유": char_elem = '금'
        elif char in "임계해자": char_elem = '수'
        
        if char_elem in supporters[my_elem]:
            support_count += 1
            
    score += (support_count * 10)
    
    # Final Diagnosis: Must pass a high threshold to override Sil-ryeong
    strength_term = "신강(Strong - 주도적)" if score >= 40 else "신약(Weak - 환경 민감)"

    # 3. Future Trend (3 Years) - Retained Logic
    current_year = datetime.now().year
    trend_text = []
    day_branch = saju_data['Day'][3]
    clashes = {"자":"오", "축":"미", "인":"신", "묘":"유", "진":"술", "사":"해", "오":"자", "미":"축", "신":"인", "유":"묘", "술":"진", "해":"사"}
    harmonies = {"자":"축", "축":"자", "인":"해", "해":"인", "묘":"술", "술":"묘", "진":"유", "유":"진", "사":"신", "신":"사", "오":"미", "미":"오"}

    for y in range(current_year, current_year+3):
        stem, branch = get_ganji_year(y)
        rel_msg = "안정 (Stability)"
        if clashes.get(day_branch) == branch: rel_msg = f"⚠️ 충(Clash) - 변화와 이동수"
        elif harmonies.get(day_branch) == branch: rel_msg = f"✨ 합(Harmony) - 계약운, 협력"
        elif branch in ["인", "신", "사", "해"]: rel_msg = f"🐎 역마(Movement) - 활동성 증가"
        elif branch in ["자", "오", "묘", "유"]: rel_msg = f"🌸 도화(Attraction) - 인기 상승"
        trend_text.append(f"- **{y}년({stem}{branch}년):** {rel_msg}")
    
    # 4. Lucky Color
    weak_colors = {'목':'검은색(수)', '화':'초록색(목)', '토':'붉은색(화)', '금':'노란색(토)', '수':'흰색(금)'}
    strong_colors = {'목':'흰색(금)', '화':'검은색(수)', '토':'초록색(목)', '금':'붉은색(화)', '수':'노란색(토)'}
    lucky_color = weak_colors.get(my_elem) if score < 40 else strong_colors.get(my_elem)

    return {
        "metaphor": metaphor,
        "strength": strength_term,
        "trend": "\n".join(trend_text),
        "lucky_color": lucky_color
    }

def generate_ai_response(messages, lang_mode):
    # System Instruction Injection
    instruction = (
        "[CRITICAL INSTRUCTION]\n"
        f"Language: {lang_mode.upper()} ONLY.\n"
        "If Korean: Use Titles: '1. 타고난 그릇', '2. 미래 흐름', '3. 신령의 처방'.\n"
        "Explain Chinese characters (Hanja) easily. Ensure detailed, multi-sentence response per section.\n"
    )
    if messages[0]['role'] == 'system':
        messages[0]['content'] += "\n" + instruction
    
    # Robust Model List (Including high-performance models)
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]
    
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.6, max_tokens=3000, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return # Success
        except: 
            time_module.sleep(0.5)
            continue
            
    yield "⚠️ AI 연결 지연. 잠시 후 다시 시도해주세요."

# ==========================================
# 3. UI LAYOUT & MAIN ROUTER (FIXED)
# ==========================================
with st.sidebar:
    t = UI_TEXT[st.session_state.lang]
    st.title(t["sidebar_title"])
    if st.button(t["lang_btn"]):
        st.session_state.lang = "en" if st.session_state.lang == "ko" else "ko"
        st.rerun()
    st.markdown("---")
    if st.button(t["reset_btn"]):
        st.session_state.clear()
        st.rerun()

t = UI_TEXT[st.session_state.lang]
st.title(t["title"])
st.caption(t["caption"])
st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

# [STATE A] INPUT FORM (Generates and Stores Result, then Reruns)
if not st.session_state.analysis_complete:
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
            with st.spinner(t["loading"]):
                coords, city_name = get_coordinates(city)
                if coords:
                    saju = calculate_saju_v3(date.year, date.month, date.day, 
                                           time_val.hour, time_val.minute, coords[0], coords[1])
                    facts = analyze_heavy_logic(saju)
                    
                    # --- CRITICAL STEP: Store all facts before Rerun ---
                    if st.session_state.lang == "ko":
                        titles = {"t1": "1. 🐅 타고난 그릇과 기질", "t2": "2. ☁️ 다가올 미래의 흐름과 리스크 (3년)", "t3": "3. ⚡ 신령의 처방 및 개운", "s1": "행동", "s2": "마인드셋", "s3": "개운법"}
                    else:
                        titles = {"t1": "1. 🐅 Identity & Core Energy", "t2": "2. ☁️ Future Trend & Risk", "t3": "3. ⚡ Shinryeong's Solution", "s1": "Action", "s2": "Mindset", "s3": "Remedy"}

                    sys_p = f"""
[SYSTEM ROLE]
You are 'Shinryeong'. Language: {st.session_state.lang.upper()}.
Input Facts: {facts}
User Concern: "{concern}"

[OUTPUT TEMPLATE]
## {t['title']}
### {titles['t1']}
(Explain '{facts['metaphor']}' and '{facts['strength']}'. Trigger 

[Image of Five Elements Cycle]
.)
### {titles['t2']}
(Analyze the trend below.)
{facts['trend']}
### {titles['t3']}
* **{titles['s1']}:** (Advice)
* **{titles['s2']}:** (Mental)
* **{titles['s3']}:** (Color: {facts['lucky_color']})
"""
                    st.session_state.saju_context = sys_p
                    st.session_state.analysis_complete = True
                    st.session_state.submit_trigger = True # New flag to trigger generation after rerun
                    
                    # Save a placeholder message to ensure history transition works
                    st.session_state.messages.append({"role": "system_info", "content": f"분석 요청 완료: {city_name} 기준"})
                    
                    st.rerun()

# [STATE B] CHAT INTERFACE (FIXED: Generation happens AFTER the state is set)
else:
    # 1. Trigger Initial Generation (If coming from form submit)
    if st.session_state.get("submit_trigger", False):
        st.session_state.submit_trigger = False # Reset flag

        # Run the generation process outside the form, inside the main container
        with st.chat_message("assistant"):
            full_resp = ""
            res_box = st.empty()
            msgs = [{"role": "system", "content": st.session_state.saju_context}, 
                    {"role": "user", "content": "Analyze."}]
            
            for chunk in generate_ai_response(msgs, st.session_state.lang):
                full_resp += chunk
                res_box.markdown(full_resp + "▌")
            res_box.markdown(full_resp)
            st.session_state.messages.append({"role": "assistant", "content": full_resp})

    # 2. Display History (Including the newly generated one)
    for m in st.session_state.messages:
        # Skip the temporary system info message for cleaner display
        if m["role"] != "system_info": 
            with st.chat_message(m["role"]): st.markdown(m["content"])
        
    # 3. Follow-up Input
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
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
