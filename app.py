import streamlit as st
import pandas as pd
import os
import json
import datetime
from saju_engine import process_saju_input  # 자네가 올린 엔진 파일

# --------------------------------------------------------------------------
# 1. [기초 공사] 페이지 설정 및 데이터 로딩 함수 (절대 경로 사용)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="신령님의 사주 상담소",
    page_icon="🔮",
    layout="wide"
)

# 데이터 캐싱 (속도 향상)
@st.cache_data
def load_db():
    """JSON 데이터베이스를 로드하여 딕셔너리로 반환"""
    db = {}
    # 현재 app.py가 있는 폴더 위치를 기준으로 data 폴더 경로 설정
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_path, "data")
    
    files = {
        "career": "career_db.json",
        "health": "health_db.json",
        "shinsal": "shinsal_db.json",
        "timeline": "timeline_db.json"
    }
    
    for key, filename in files.items():
        try:
            path = os.path.join(data_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                db[key] = json.load(f)
        except FileNotFoundError:
            # 파일이 없을 경우 빈 딕셔너리로 처리 (에러 방지)
            db[key] = {}
            
    return db

# DB 로드 실행
DB = load_db()

# --------------------------------------------------------------------------
# 2. [두뇌] 사주 결과와 DB를 연결하는 '매핑 로직' (가장 중요!)
# --------------------------------------------------------------------------
def get_shaman_advice(saju_result):
    """
    saju_engine의 분석 결과를 바탕으로 JSON DB에서 딱 맞는 '신령의 목소리'를 추출함.
    AI가 헤매지 않도록 정답 텍스트를 미리 뽑아내는 과정.
    """
    advice_context = []
    
    # (1) 일간(Day Master) 기반 건강 조언 매핑
    # saju_engine에서 일간 오행(예: 목, 화..)을 가져온다고 가정
    day_master_element = saju_result.get('day_master_element', '목') # 기본값 목
    
    # DB 키와 매칭 (health_db.json 구조 참고)
    # 예: 목 -> "목(Wood)_문제"
    health_key = f"{day_master_element}({process_english_element(day_master_element)})_문제"
    
    health_data = DB['health'].get('health_remedy', {}).get(health_key, {})
    if health_data:
        advice_context.append(f"🔴 [건강/신체 리스크]: {health_data.get('shamanic_voice')}")
        advice_context.append(f"   - 추천 음식: {health_data.get('food_remedy')}")
        advice_context.append(f"   - 개운 행동: {health_data.get('action_remedy')}")

    # (2) 격국/강약 기반 직업 조언 매핑
    # 엔진에서 '비겁_태과' 같은 키워드를 주거나, 로직으로 판단해야 함
    # 여기서는 예시로 'dominant_ten_god'이 결과에 있다고 가정
    dominant = saju_result.get('dominant_ten_god', '비겁_태과') # 예시 키
    
    # DB 키 매칭 (career_db.json 구조 참고)
    # career_db 키가 "비겁_태과(Self_Strong)" 형태이므로 매칭 필요
    # *실제 구현 시 saju_engine이 뱉는 값과 json 키를 일치시키는 작업 필수*
    career_key_map = {
        "비겁": "비겁_태과(Self_Strong)",
        "식상": "식상_발달(Output_Strong)",
        "재성": "재성_발달(Wealth_Strong)",
        "관성": "관성_발달(Official_Strong)",
        "인성": "인성_발달(Input_Strong)"
    }
    
    # 매핑된 키 찾기 (포함 여부로 대략적 매칭)
    matched_career_key = None
    for key in DB['career'].get('modern_jobs', {}):
        if dominant in key: # "비겁"이 "비겁_태과..." 안에 있으면 선택
            matched_career_key = key
            break
            
    if matched_career_key:
        job_data = DB['career']['modern_jobs'][matched_career_key]
        advice_context.append(f"🔵 [직업/성향]: {job_data.get('shamanic_voice')}")
        advice_context.append(f"   - 추천 직업: {job_data.get('jobs')}")
        advice_context.append(f"   - 일하는 스타일: {job_data.get('work_style')}")

    return "\n".join(advice_context)

def process_english_element(korean_element):
    """한글 오행을 영문으로 변환 (DB 키 매칭용)"""
    mapping = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}
    return mapping.get(korean_element, 'Wood')

# --------------------------------------------------------------------------
# 3. [UI] 사이드바 입력창 (기존 유지)
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("🏯 신령의 사주 입력")
    st.info("정확한 생년월일시를 입력하게.")
    
    with st.form("saju_form"):
        name = st.text_input("이름", "아무개")
        col1, col2 = st.columns(2)
        with col1:
            gender = st.selectbox("성별", ["남자", "여자"])
        with col2:
            calendar_type = st.selectbox("양력/음력", ["양력", "음력", "음력(윤달)"])
            
        birth_date = st.date_input("생년월일", datetime.date(1990, 1, 1), min_value=datetime.date(1930, 1, 1))
        birth_hour = st.selectbox("태어난 시간", [f"{i:02d}:30" for i in range(24)] + ["모름"])
        
        submitted = st.form_submit_button("🔮 운세 보기")

# --------------------------------------------------------------------------
# 4. [메인] 채팅 인터페이스 및 로직 처리
# --------------------------------------------------------------------------
st.title("🔮 신령님의 호통 사주")
st.markdown("---")

# 세션 상태 초기화 (대화 기록 저장용)
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 초기 인사말
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "어서 오게. 자네의 생년월일을 왼쪽에 입력하고 '운세 보기'를 누르면, 내가 아주 따끔하게 인생을 봐주겠네."
    })

# 채팅 기록 화면에 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --------------------------------------------------------------------------
# [핵심] '운세 보기' 버튼 클릭 시 로직
# --------------------------------------------------------------------------
if submitted:
    # 1. 사주 엔진 호출 (계산)
    # 실제 saju_engine.py의 함수 호출. 
    # *주의: process_saju_input의 리턴값이 딕셔너리 형태라고 가정*
    try:
        # 가상의 결과 데이터 (엔진 연동 전 테스트용, 실제론 engine 결과 사용)
        # engine_result = process_saju_input(name, gender, ...) 
        
        # [테스트용 가짜 데이터] - 엔진 연결 후 삭제하세요
        engine_result = {
            "name": name,
            "day_master_element": "화",  # 예: 병화/정화
            "dominant_ten_god": "재성",   # 예: 재성이 강함
            "saju_text": "자네는 불덩이 같은 사주야." # 엔진에서 나온 기본 텍스트
        }
        
        # 2. DB에서 '신령의 목소리' 추출 (Mapping)
        shaman_context = get_shaman_advice(engine_result)
        
        # 3. 최종 답변 생성 (AI 없이도 완벽한 답변 구성)
        final_response = f"""
        **[신령의 분석 결과]**
        
        어흠, 자네 사주를 풀어보니 기가 막히는구먼.
        
        {shaman_context}
        
        ---
        **신령의 한마디:**
        "듣기 좋은 소리는 안 하네. 위 내용을 명심하고 살게나."
        """
        
        # 4. 채팅창에 결과 추가
        st.session_state.messages.append({"role": "assistant", "content": final_response})
        # 즉시 리런하여 화면 갱신
        st.rerun()
        
    except Exception as e:
        st.error(f"에러가 났구먼: {e}")

# --------------------------------------------------------------------------
# 5. [추가] 사용자가 채팅으로 추가 질문할 때 (LLM 연동 부분)
# --------------------------------------------------------------------------
if prompt := st.chat_input("신령님께 궁금한 것을 물어보게..."):
    # 사용자 메시지 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ---------------------------------------------------------
    # 여기에 LLM (OpenAI 등) 코드가 들어가야 함.
    # 하지만 '저성능' 혹은 '답이 없음' 문제 해결을 위해
    # LLM 없이도 동작하는 '룰 기반 답변'을 예시로 넣음.
    # ---------------------------------------------------------
    
    with st.chat_message("assistant"):
        # AI 연결 전 임시 응답 (혹은 저성능 AI를 위한 프롬프트 구성)
        response_text = "지금은 내가 기도 중이라(API 미연동) 긴 대화는 어렵네. 위 분석 결과나 다시 꼼꼼히 읽어보게!"
        
        # 만약 OpenAI를 쓴다면 아래 주석을 풀고 사용하게
        # client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        # completion = client.chat.completions.create(
        #    model="gpt-3.5-turbo",
        #    messages=[
        #        {"role": "system", "content": "당신은 호통치는 무속인 '신령'입니다."},
        #        {"role": "user", "content": prompt}
        #    ]
        # )
        # response_text = completion.choices[0].message.content
        
        st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})

# --------------------------------------------------------------------------
# [법적 면책 조항]
# --------------------------------------------------------------------------
st.markdown("---")
st.caption("⚠️ 본 서비스는 심심풀이용이며, 법적/의학적 효력은 없습니다.")
