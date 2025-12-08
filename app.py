import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import time as time_module
from geopy.geocoders import Nominatim
from geopy.distance import great_circle
from korean_lunar_calendar import KoreanLunarCalendar
import json

# ==========================================
# 0. CONFIG & TEXTS
# ==========================================
st.set_page_config(page_title="신령 사주리포트", page_icon="🔮", layout="centered")

UI_TEXT = {
    "ko": {
        "title": "🔮 신령 사주리포트",
        "caption": "정통 명리학 기반 데이터 분석 시스템 v16.3 (문법 완전수정)",
        "sidebar_title": "설정", "lang_btn": "English Mode", "reset_btn": "새로운 상담 시작",
        "input_dob": "생년월일", "input_time": "태어난 시간", "input_city": "태어난 도시",
        "input_gender": "성별", "concern_label": "당신의 고민을 구체적으로 적어주세요.",
        "submit_btn": "📜 정밀 분석 시작", "loading": "천문 데이터 계산 및 신강/신약 정밀 판별 중...",
        "warn_title": "법적 면책 조항", "warn_text": "본 분석은 통계적 참고자료입니다.",
        "placeholder": "추가 질문을 입력하세요..."
    }
}

# Initialize State
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "saju_data_dict" not in st.session_state: st.session_state.saju_data_dict = {} 
if "raw_input_data" not in st.session_state: st.session_state.raw_input_data = None

# API Setup
geolocator = Nominatim(user_agent="shinryeong_v16_3_final", timeout=10)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "창원": (35.22, 128.68), "광주": (35.15, 126.85),
    "대전": (36.35, 127.38), "울산": (35.53, 129.31), "제주": (33.49, 126.53),
    "seoul": (37.56, 126.97), "busan": (35.17, 129.07), "changwon": (35.22, 128.68)
}

def get_coordinates(city_input):
    clean = city_input.strip().lower()
    if clean in CITY_DB: return CITY_DB[clean], city_input
    try:
        loc = geolocator.geocode(city_input)
        if loc: return (loc.latitude, loc.longitude), city_input
    except: pass
    return None, None

def convert_lunar_to_solar(year, month, day, is_intercalary):
    try:
        calendar = KoreanLunarCalendar()
        calendar.setLunarDate(year, month, day, is_intercalary)
        return datetime(calendar.solarYear, calendar.solarMonth, calendar.solarDay).date()
    except: return None

# ==========================================
# 2. LOGIC ENGINE (v16.3 - Syntax Safe)
# ==========================================
def analyze_logic_v16(saju_res):
    """
    Constructs the NARRATIVE directly in Python to prevent AI hallucination.
    """
    dm = saju_res['Day_Stem']
    season = saju_res['Month_Branch']
    full_str = saju_res['Full_String']
    
    # 1. Elements
    elem_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
    season_map = {'인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수','자':'수','축':'토'}
    
    my_elem = elem_map.get(dm, '수')
    season_elem = season_map.get(season, '화')
    
    # 2. Supporters
    supporters = []
    if my_elem == '목': supporters = ['수', '목']
    elif my_elem == '화': supporters = ['목', '화']
    elif my_elem == '토': supporters = ['화', '토']
    elif my_elem == '금': supporters = ['토', '금']
    elif my_elem == '수': supporters = ['금', '수']
    
    # 3. Strength Scoring
    score = 0
    if season_elem in supporters: score += 50
    else: score -= 50 # Penalize for Sil-ryeong
    
    for char in full_str:
        if char == ' ': continue
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        if ce in supporters: score += 10
        else: score -= 5
            
    # Diagnosis Narrative
    strength_desc = ""
    if score >= 20: 
        strength = "신강(Strong)" 
        strength_desc = "그대는 뚝심 있고 주관이 뚜렷하여, 남의 말에 휘둘리기보다 자신이 상황을 리드하는 힘을 타고났네."
    else: 
        strength = "신약(Sensitive)"
        strength_desc = "그대는 환경에 민감하고 섬세하여, 주변의 기운을 잘 읽어내나 그만큼 에너지 소모가 빠른 편이네."

    # 4. Pattern Detection (Jae-da-sin-yak)
    wealth_map = {'목':'토', '화':'금', '토':'수', '금':'목', '수':'화'}
    my_wealth = wealth_map.get(my_elem, '화')
    
    wealth_count = 0
    for char in full_str:
        ce = '토'
        if char in "갑을인묘": ce = '목'
        elif char in "병정사오": ce = '화'
        elif char in "경신신유": ce = '금'
        elif char in "임계해자": ce = '수'
        if ce == my_wealth: wealth_count += 1
        
    pattern = "일반격"
    # [FIXED: TRIPLE QUOTES USED]
    advice_core = """오행의 균형을 맞추는 것이 중요하네. 

[Image of Five Elements Cycle]
"""
    
    if "신약" in strength and wealth_count >= 3:
        pattern = "재다신약(財多身弱 - 재물은 많으나 가질 힘이 약함)"
        strength = "극신약(Very Weak)"
        strength_desc = "그대는 재물과 기회(돈/여자/일) 속에 둘러싸여 있으나, 정작 그것을 쥘 힘이 부족해 건강을 잃거나 스트레스를 받는 형국이네."
        advice_core = "돈을 쫓지 말고, **'자신을 채우는 공부(인성)'**나 **'믿을만한 동료(비겁)'**와 함께해야 재물이 내 것이 되네."
    elif wealth_count >= 3:
        pattern = "재성과다(Wealth Overload)"
        advice_core = "타고난 사업가 기질이 있으나, 재물 관리에 신중해야 하네."

    # 5. Metaphor
    metaphor_db = {
        '갑': "곧게 뻗은 거목", '을': "끈질긴 생명력의 화초", '병': "만물을 비추는 태양", '정': "어둠을 밝히는 촛불",
        '무': "묵직한 태산", '기': "비옥한 대지", '경': "단단한 바위", '신': "예리한 보석",
        '임': "깊고 넓은 바다", '계': "스며드는 봄비"
    }
    metaphor_text = f"그대는 자연으로 치면 **'{metaphor_db.get(dm, '알 수 없는 기운')}'**와 같네."
    
    # 6. Shinsal
    shinsal_list = saju_res['Shinsal']
    shinsal_text = "특별한 살은 보이지 않으나, 평온함이 장점이라네."
    if shinsal_list:
        shinsal_text = f"그대에게는 **{', '.join(shinsal_list)}**의 기운이 흐르고 있네."

    return {
        "identity": dm,
        "metaphor_narrative": metaphor_text,
        "strength_narrative": f"분석 결과, 그대의 기운은 **'{strength}'**이라네. {strength_desc}",
        "pattern_narrative": f"격국은 **'{pattern}'**에 해당하네.",
        "advice_narrative": advice_core,
        "shinsal_narrative": shinsal_text,
        "raw_pattern": pattern,
        "pillars": full_str
    }

def generate_ai_response(messages, mode="report"):
    # STRICT Persona & Language Lock
    sys_instruction = """
[CRITICAL RULE]
1. Role: 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체: ~하네, ~이라네).
2. Language: KOREAN ONLY. Absolutely NO Chinese characters (except in brackets) or English words in the final output text.
3. Source: Use the provided [NARRATIVE DATA]. Do NOT calculate or invent new facts.
4. If the data says 'Jae-da-sin-yak', DO NOT say 'You are strong'. Say "You are surrounded by wealth but need strength to hold it."
5. Visuals: Insert 

[Image of Five Elements Cycle]
 exactly once.
"""
    if mode == "chat":
        sys_instruction += "\n[CHAT MODE] Answer ONLY the user's specific question using the data. Do NOT repeat the birth chart or introduction."

    if messages[0]['role'] == 'system':
        messages[0]['content'] += f"\n{sys_instruction}"
        
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.5, max_tokens=4000
            )
            return stream.choices[0].message.content
        except: time_module.sleep(0.5); continue
    return "⚠️ 신령이 깊은 명상에 잠겨 응답하지 못했습니다. 다시 시도해주게."

# ==========================================
# 3. MAIN UI FLOW
# ==========================================
with st.sidebar:
    st.title("⚙️ 설정")
    if st.button("🔄 리셋"):
        st.session_state.clear()
        st.rerun()
    
    with st.expander("🔍 데이터 진단", expanded=False):
        st.json(st.session_state.saju_data_dict)

t = UI_TEXT["ko"] # Force Korean context
st.title(t["title"])
st.caption("음력/윤달 지원 & 정밀 분석 엔진 v16.3")
st.warning(f"**[{t['warn_title']}]**\n\n{t['warn_text']}")

# A. Input Form
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        with c1:
            input_date = st.date_input(t["input_dob"], min_value=datetime(1940,1,1))
            time_val = st.time_input(t["input_time"], value=time(12,0))
            is_lunar = st.checkbox("음력 (Lunar)", value=False)
            is_intercalary = st.checkbox("윤달", value=False, disabled=not is_lunar)
        with c2:
            gender = st.radio(t["input_gender"], ["남성", "여성"])
            city = st.text_input(t["input_city"])
        
        concern = st.text_area(t["concern_label"], height=80)
        submit = st.form_submit_button(t["submit_btn"])
    
    if submit:
        if not city: 
            st.error("⚠️ 도시를 입력하게.")
        else:
            with st.spinner("⏳ 천기누설을 준비 중이네..."):
                coords, city_name = get_coordinates(city)
                if not coords:
                    st.error(f"❌ '{city}'의 기운을 찾을 수 없네.")
                else:
                    # 1. Calc
                    final_date = input_date
                    if is_lunar:
                        final_date = convert_lunar_to_solar(input_date.year, input_date.month, input_date.day, is_intercalary)
                        if not final_date: st.error("❌ 날짜가 잘못되었네."); st.stop()
                    
                    saju_res = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                                               time_val.hour, time_val.minute, coords[0], coords[1])
                    
                    # 2. Logic (v16.2 Correct Call)
                    facts = analyze_logic_v16(saju_res)
                    
                    st.session_state.saju_data_dict = facts
                    st.session_state.raw_input_data = {"date": str(final_date), "concern": concern}
                    
                    # 3. Report Generation
                    sys_p = f"""
[NARRATIVE DATA]
1. Identity: {facts['metaphor_narrative']} (Self: {facts['identity']})
2. Strength: {facts['strength_narrative']}
3. Pattern: {facts['pattern_narrative']}
4. Shinsal: {facts['shinsal_narrative']}
5. Solution: {facts['advice_narrative']}
6. User Concern: "{concern}"

[TASK]
Convert the [NARRATIVE DATA] into a complete, flowing report in Korean 'Hage-che'.
Do NOT add extra meanings. Use the provided narratives directly.
"""
                    st.session_state.saju_context = sys_p
                    msgs = [{"role": "system", "content": sys_p}, 
                            {"role": "user", "content": "상세 분석 리포트를 작성하라."}]
                    
                    full_resp = generate_ai_response(msgs, mode="report")
                    st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    st.session_state.analysis_complete = True
                    st.rerun()

# B. Chat Mode
else:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    if q := st.chat_input(t["placeholder"]):
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        # Inject Specific Data for Chat
        facts = st.session_state.saju_data_dict
        context_msg = f"""
[CHAT CONTEXT]
User Identity: {facts['identity']} ({facts['raw_pattern']}).
User Solution: {facts['advice_narrative']}
Question: "{q}"

[INSTRUCTION]
Answer the question "{q}" specifically using the User Solution context.
If asking about money/career, emphasize the 'Solution'. Do NOT repeat intro.
"""
        msgs = [{"role": "system", "content": context_msg}, 
                {"role": "user", "content": q}]
        
        with st.chat_message("assistant"):
            with st.spinner("신령이 점을 치는 중..."):
                full_resp = generate_ai_response(msgs, mode="chat")
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
