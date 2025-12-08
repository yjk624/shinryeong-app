import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 1. SYSTEM CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="신령 (Shinryeong) - AI Destiny Analyst", 
    page_icon="🔮", 
    layout="centered"
)

# Initialize Geocoder
geolocator = Nominatim(user_agent="shinryeong_final_v1", timeout=10)

# Configure GROQ API (DeepSeek/Llama/Mixtral)
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_KEY)
except Exception as e:
    st.error(f"🚨 API Key Missing: {e}")
    st.stop()

# Initialize Session State
if "messages" not in st.session_state: st.session_state.messages = []
if "saju_context" not in st.session_state: st.session_state.saju_context = ""
if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

# ==========================================
# 2. CORE LOGIC ENGINE (THE BRAIN)
# ==========================================
def get_coordinates(city_input):
    """Finds latitude/longitude for precise solar time calculation."""
    CITY_DB = {
        "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
        "대구": (35.87, 128.60), "대전": (36.35, 127.38), "광주": (35.15, 126.85), 
        "울산": (35.53, 129.31), "세종": (36.48, 127.28), "제주": (33.49, 126.53),
        "New York": (40.71, -74.00), "London": (51.50, -0.12), "Tokyo": (35.67, 139.65)
    }
    clean = city_input.strip()
    if clean in CITY_DB: return CITY_DB[clean], clean
    try:
        loc = geolocator.geocode(clean)
        if loc: return (loc.latitude, loc.longitude), clean
    except: pass
    return None, None

def analyze_saju_logic(saju_data):
    """
    [LOGIC INJECTION LAYER]
    Calculates destiny facts in Python to prevent AI hallucination.
    Returns a dictionary of pre-written 'Truths' for the AI to render.
    """
    day_stem = saju_data['Day'][0]   # 일간 (Identity)
    month_branch = saju_data['Month'][3] # 월지 (Season/Environment)
    day_branch = saju_data['Day'][3] # 일지 (Spouse/Reality)
    full_str = saju_data['Year'] + saju_data['Month'] + saju_data['Day'] + saju_data['Time']
    
    # -----------------------------------------------------
    # A. IDENTITY METAPHOR (NATURE IMAGERY)
    # -----------------------------------------------------
    identity_map = {
        '갑': "곧게 뻗은 거목(Giant Tree) - 굽히지 않는 자존심과 선구자적 기질",
        '을': "끈질긴 화초(Ivy) - 어떤 환경에서도 살아남는 유연함과 생활력",
        '병': "태양(Sun) - 누구에게나 공평하고 화려하게 빛나는 예능감",
        '정': "촛불(Candle) - 한 사람, 한 분야만 파고드는 집중력과 은근한 열정",
        '무': "태산(Mountain) - 말없이 묵직하여 믿음을 주는 리더",
        '기': "대지(Field) - 만물을 길러내는 어머니 같은 포용력과 실속",
        '경': "바위(Iron) - 한번 결정하면 뒤를 보지 않는 결단력과 의리",
        '신': "보석(Diamond) - 예민하고 섬세하며, 남다른 기술을 가진 전문가",
        '임': "바다(Ocean) - 속을 알 수 없으나 거대한 지혜와 포부를 가진 전략가",
        '계': "빗물(Rain) - 어디든 스며드는 친화력과 뛰어난 참모 기질"
    }
    season_map = {
        '인': '초봄', '묘': '봄', '진': '늦봄',
        '사': '초여름', '오': '한여름', '미': '늦여름',
        '신': '초가을', '유': '가을', '술': '늦가을',
        '해': '초겨울', '자': '한겨울', '축': '늦겨울'
    }
    
    my_nature = identity_map.get(day_stem, "신비로운 기운")
    my_season = season_map.get(month_branch, "어느 계절")
    metaphor_sentence = f"그대는 **{my_season}**에 태어난 **{my_nature}**의 형상입니다."

    # -----------------------------------------------------
    # B. TALENT & SHINSAL (SPECIAL WEAPONS)
    # -----------------------------------------------------
    traits = []
    # 1. Hyunchim (Needle)
    if any(x in full_str for x in ["갑", "신", "묘", "오"]):
        traits.append("**'현침살(Sharp Needle)'**: 남들이 못 보는 것을 찌르는 통찰력 (의료/IT/비평/미용)")
    # 2. Yeokma (Travel)
    if any(x in full_str for x in ["인", "신", "사", "해"]):
        traits.append("**'역마살(Global Wings)'**: 한 곳에 머물면 병이 나는 활동성 (무역/영업/여행/유튜브)")
    # 3. Dohwa (Peach Blossom)
    if any(x in full_str for x in ["자", "오", "묘", "유"]):
        traits.append("**'도화살(Attraction)'**: 가만히 있어도 시선을 끄는 매력 (마케팅/방송/예술)")
    # 4. Gwegang (Power)
    if ("진" in full_str and "술" in full_str) or day_stem in ["경", "임", "무"]:
        traits.append("**'괴강/백호(Boss Energy)'**: 평범함을 거부하고 난세를 평정하는 강력한 리더십")

    # Element Analysis for Job Advice
    wood = full_str.count('갑') + full_str.count('을') + full_str.count('인') + full_str.count('묘')
    fire = full_str.count('병') + full_str.count('정') + full_str.count('사') + full_str.count('오')
    earth = full_str.count('무') + full_str.count('기') + full_str.count('진') + full_str.count('술') + full_str.count('축') + full_str.count('미')
    metal = full_str.count('경') + full_str.count('신') + full_str.count('신') + full_str.count('유')
    water = full_str.count('임') + full_str.count('계') + full_str.count('해') + full_str.count('자')

    counts = {'목': wood, '화': fire, '토': earth, '금': metal, '수': water}
    max_elem = max(counts, key=counts.get)
    min_elem = min(counts, key=counts.get)

    job_advice_map = {
        '목': "교육, 기획, 건축, 육아 등 **'무언가를 키우고 시작하는 일'**",
        '화': "방송, 디자인, IT, 에너지 등 **'자신을 화려하게 드러내는 일'**",
        '토': "부동산, 중개, 컨설팅, 농업 등 **'기반을 다지고 중재하는 일'**",
        '금': "금융, 의료, 군인, 공학 등 **'냉철하게 자르고 결단하는 일'**",
        '수': "해외, 무역, 연구, 요식업 등 **'유연하게 흐르거나 지혜를 쓰는 일'**"
    }
    
    talent_desc = "\n".join([f"- {t}" for t in traits]) if traits else "- 특별한 살(殺) 없이 맑고 평온하여 귀인의 도움을 받는 명(命)"

    # -----------------------------------------------------
    # C. 2025 PREDICTION (EUL-SA YEAR LOGIC)
    # -----------------------------------------------------
    future_desc = ""
    # Sa (Snake) vs Day Branch
    if day_branch == "해":
        future_desc = "2025년(을사년)은 **'사해충(Big Crash)'**의 해. 앉은 자리가 흔들리니 **'이직, 이사, 부서이동'**이 강력하게 들어옵니다. 이는 나쁜 것이 아니라 낡은 껍질을 깨는 운이니 변화를 받아들이십시오. (4월, 10월 주의)"
    elif day_branch in ["신", "인"]:
        future_desc = "2025년은 **'인사신 삼형(Adjustment)'**의 해. 내가 가진 권한이나 환경이 **'강제로 조정'**되는 시기입니다. 직장 내 권력 다툼이나 수술수가 있을 수 있으니, 인간관계에서 적을 만들지 마십시오."
    elif day_branch in ["유", "축"]:
        future_desc = "2025년은 뱀(사)과 합을 이루어 **'금국(Metal Alliance)'**을 형성합니다. 귀인이나 새로운 파트너를 만나 **'문서를 잡거나 단체를 결성'**하기 아주 좋은 시기입니다."
    else:
        future_desc = "2025년은 폭풍우가 비켜가는 **'안정과 내실'**의 시기입니다. 무리한 확장보다는 현재의 위치에서 실력을 갈고닦으면 하반기에 큰 결실이 있습니다."

    # -----------------------------------------------------
    # D. HEALTH RISKS (MISSING ELEMENT)
    # -----------------------------------------------------
    health_map = {
        '목': "간, 담, 신경성 두통, 근육 피로",
        '화': "심장, 혈압, 시력, 소장",
        '토': "위장, 소화기, 피부 트러블, 허리",
        '금': "폐, 호흡기, 뼈, 관절, 대장",
        '수': "신장, 방광, 생식기, 우울감"
    }
    health_desc = f"에너지가 가장 부족한 오행은 **'{min_elem}'**입니다. **[{health_map[min_elem]}]** 관련 건강 관리에 유의하십시오."

    return {
        "metaphor": metaphor_sentence,
        "talents": talent_desc,
        "career": job_advice_map[max_elem],
        "future": future_desc,
        "health": health_desc
    }

def generate_ai_response(messages):
    """Fallback mechanism to ensure response generation."""
    models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"]
    for model in models:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=0.6, max_tokens=2500, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except: continue
    yield "⚠️ 신령이 깊은 명상에 잠겨 응답할 수 없습니다. 잠시 후 다시 시도해주세요."

# ==========================================
# 3. UI LAYOUT & INTERACTION
# ==========================================
with st.sidebar:
    st.title("📜 상담 기록")
    if st.button("🔄 새로운 상담 시작 (Reset)"):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    st.caption("Developed by Shinryeong AI V2.5")

st.title("🔮 신령 (Shinryeong)")
st.markdown("### \"운명은 정해진 것이 아니라, 흐르는 데이터다.\"")
st.info("⚠️ 본 서비스는 사주명리학 데이터를 기반으로 냉철한 분석을 제공합니다. 위로보다는 해결책을 드립니다.")

# ------------------------------------------
# A. INPUT FORM (DATA COLLECTION)
# ------------------------------------------
if not st.session_state.analysis_complete:
    with st.form("input_form"):
        col1, col2 = st.columns(2)
        with col1:
            b_date = st.date_input("생년월일 (Date of Birth)", min_value=datetime(1940,1,1))
            b_time = st.time_input("태어난 시간 (Birth Time)", value=time(12,0), step=60)
            cal_type = st.radio("달력 기준", ["양력 (Solar)", "음력 (Lunar)"])
        with col2:
            gender = st.radio("성별 (Gender)", ["남성", "여성"])
            loc = st.text_input("태어난 지역 (Birth City)", placeholder="예: 서울, 부산, LA, Tokyo")
        
        concern = st.text_area("현재 가장 큰 고민은 무엇인가요?", height=80, 
                             placeholder="예: 이번에 이직을 해도 될까요? / 연애운이 궁금합니다.")
        
        submit_btn = st.form_submit_button("⚡ 신령 소환하여 천기누설 듣기")

    if submit_btn:
        if not loc:
            st.error("⚠️ 정확한 시차 계산을 위해 '태어난 지역'을 입력해주세요.")
        else:
            with st.spinner("⏳ 천문 데이터를 계산하고 만세력을 해독 중입니다..."):
                coords, city_name = get_coordinates(loc)
                if coords:
                    # 1. Calculate Core Saju Data
                    is_lunar = True if "음력" in cal_type else False
                    saju_res = calculate_saju_v3(
                        b_date.year, b_date.month, b_date.day, 
                        b_time.hour, b_time.minute, coords[0], coords[1], is_lunar
                    )
                    
                    # 2. RUN LOGIC INJECTION (Get Facts)
                    facts = analyze_saju_logic(saju_res)
                    
                    # 3. Render Static Summary Table
                    st.success(f"{city_name} 기준, 진태양시 적용 완료.")
                    st.markdown(f"""
                    | 구분 | 내용 |
                    | :--- | :--- |
                    | **사주팔자** | {saju_res['Year']} / {saju_res['Month']} / {saju_res['Day']} / {saju_res['Time']} |
                    | **핵심형상** | {facts['metaphor']} |
                    """)
                    
                    # 4. Build Foolproof System Prompt
                    final_q = concern if concern else "종합적인 운세와 기질 분석"
                    
                    sys_prompt = f"""
[SYSTEM ROLE]
You are 'Shinryeong' (신령), a divine Saju Master.
Tone: Mystical, Authoritative, but Logical. (Korean Hage-che: ~하게나, ~이라네).
Language: **KOREAN ONLY**.

[INSTRUCTION]
I have already calculated the User's Destiny Facts. 
You are NOT a calculator. You are a **Storyteller**.
Take the [Computed Facts] below and expand them into a deeply insightful reading.

[COMPUTED FACTS (ABSOLUTE TRUTH)]
1. **Identity (Metaphor):** {facts['metaphor']}
2. **Talents (Weapons):** {facts['talents']}
3. **Career Path:** {facts['career']}
4. **2025 Future Forecast:** {facts['future']}
5. **Health Weakness:** {facts['health']}
6. **User's Concern:** "{final_q}"

[RESPONSE FORMAT]
## 📜 신령의 정밀 분석 보고서

### 1. 🐅 그대의 타고난 그릇 (Identity)
(Use Fact 1. Explain the nature metaphor vividly.)

### 2. 🗡️ 하늘이 내린 무기 (Talents)
(Use Fact 2 & 3. Explain their hidden talents and best career path.)

### 3. ☁️ 2025년(을사년)의 천기누설 (Future)
(Use Fact 4. Deliver the prediction clearly. Be direct about risks or opportunities.)

### 4. ⚡ 신령의 처방 (Solution)
(Address the User's Concern: "{final_q}")
* **행동지침:** (Practical advice based on Fact 4)
* **건강관리:** (Advice based on Fact 5)
* **개운법:** (Suggest a lucky color or direction based on their Elements)

> **[면책]** 운명은 정해진 것이 아니라 개척하는 것입니다. 이 분석은 통계적 참고자료입니다.
"""
                    st.session_state.saju_context = sys_prompt
                    st.session_state.analysis_complete = True
                    
                    # 5. Generate Initial Analysis
                    messages = [{"role": "system", "content": sys_prompt}, 
                                {"role": "user", "content": "분석 결과를 지금 바로 들려주게."}]
                    
                    with st.chat_message("assistant"):
                        response_container = st.empty()
                        full_text = ""
                        for chunk in generate_ai_response(messages):
                            full_text += chunk
                            response_container.markdown(full_text + "▌")
                        response_container.markdown(full_text)
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                    
                    st.rerun()

                else:
                    st.error("⚠️ 입력하신 도시를 찾을 수 없습니다. (예: Seoul, Busan, New York)")

# ------------------------------------------
# B. CHAT INTERFACE (AFTER ANALYSIS)
# ------------------------------------------
else:
    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if user_input := st.chat_input("신령에게 추가로 궁금한 점을 물어보세요..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Context-Aware Request
        # We only feed the System Prompt + Last 2 interactions to save tokens/focus
        context_msgs = [{"role": "system", "content": st.session_state.saju_context}]
        recent_history = st.session_state.messages[-4:] 
        context_msgs.extend(recent_history)
        
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_text = ""
            for chunk in generate_ai_response(context_msgs):
                full_text += chunk
                response_container.markdown(full_text + "▌")
            response_container.markdown(full_text)
            st.session_state.messages.append({"role": "assistant", "content": full_text})
