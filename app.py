import streamlit as st
import pandas as pd
import os
import json
import datetime
from saju_engine import process_saju_input, process_love_compatibility # 만능 엔진 불러오기
from typing import Dict, Any, Optional

# --------------------------------------------------------------------------
# 1. [기초 공사] 페이지 설정 및 데이터 로딩 함수 (10개 DB 로드)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="신령님의 AI 형이상학 분석소",
    page_icon="🔮",
    layout="wide"
)

# 데이터 캐싱 (속도 향상)
@st.cache_data
def load_db():
    """JSON 데이터베이스를 로드하여 딕셔너리로 반환"""
    db = {}
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 🚨🚨🚨 모든 10개 DB 파일을 명시 🚨🚨🚨
    files = {
        "career": "career_db.json",
        "health": "health_db.json",
        "shinsal": "shinsal_db.json",
        "timeline": "timeline_db.json",
        "love": "love_db.json", 
        "five_elements": "five_elements_matrix.json",
        "symptom": "symptom_mapping.json",
        "lifecycle": "lifecycle_pillar_db.json",
        "identity": "identity_db.json",           
        "compatibility": "compatibility_db.json" 
    }
    
    for key, filename in files.items():
        try:
            path = os.path.join(base_path, filename) 
            with open(path, "r", encoding="utf-8") as f:
                db[key] = json.load(f)
        except FileNotFoundError:
            st.error(f"경고: {filename} 데이터베이스 파일을 찾을 수 없네! 파일을 'app.py'와 같은 위치에 두게나.")
            db[key] = {} 
        except json.JSONDecodeError:
            st.error(f"경고: {filename} 파일이 JSON 형식이 아니네. 다시 확인하게!")
            db[key] = {}
            
    return db

# 데이터베이스 로드
db = load_db()

# 세션 상태 초기화 (생략 - 이전 버전과 동일)
if "messages" not in st.session_state: st.session_state.messages = []
if 'analysis_report' not in st.session_state: st.session_state.analysis_report = None
if 'user_a_input' not in st.session_state: st.session_state.user_a_input = None
if 'user_b_input' not in st.session_state: st.session_state.user_b_input = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = 'none'

# --------------------------------------------------------------------------
# 2. [입력창] 사주/궁합 정보 입력 사이드바 (생략 - 이전 버전과 동일)
# --------------------------------------------------------------------------

def saju_input_form(key_prefix: str) -> Optional[Dict[str, Any]]:
    # 이전 버전과 동일한 함수 내용 (Streamlit 위젯 입력)
    with st.container():
        name = st.text_input("이름 (혹은 별명)", key=f"{key_prefix}_name")
        col1, col2 = st.columns(2)
        
        with col1:
            date_col, time_col = st.columns(2)
            with date_col:
                date = st.date_input("생년월일", value=datetime.date(1990, 1, 1), key=f"{key_prefix}_date")
            with time_col:
                time = st.time_input("태어난 시 (24시)", value=datetime.time(9, 30), key=f"{key_prefix}_time", step=900)
            
            is_lunar = st.radio("달력 종류", ('양력(陽)', '음력(陰)'), horizontal=True, key=f"{key_prefix}_lunar") == '음력(陰)'
            is_leap_month = False
            if is_lunar:
                is_leap_month = st.checkbox("윤달인가?", key=f"{key_prefix}_leap")
            
        with col2:
            gender = st.radio("성별", ('남', '여'), horizontal=True, key=f"{key_prefix}_gender")
            city = st.text_input("태어난 도시/지역 (예: Busan)", key=f"{key_prefix}_city", help="진태양시 보정을 위한 경도 정보가 필요하다네.")
            
        if name and city:
            birth_dt = datetime.datetime.combine(date, time)
            return {
                "name": name, "birth_dt": birth_dt, "is_lunar": is_lunar, 
                "is_leap_month": is_leap_month, "gender": gender, "city": city
            }
        return None

with st.sidebar:
    st.image("https://images.unsplash.com/photo-1549488344-9c869150041d?w=400&h=400&fit=crop", caption="신령의 성소(Sacred Place)", use_column_width=True)
    st.header("운명의 입력창 📜")
    
    analysis_mode = st.radio(
        "어떤 분석이 필요한가?",
        ('👤 개인 사주 분석', '💞 남녀 궁합 분석'),
        index=0
    )
    
    # 개인 사주 분석 모드
    if analysis_mode == '👤 개인 사주 분석':
        st.subheader("1. 나의 정보")
        user_a_data = saju_input_form('user_a')
        if st.button("운명 분석 시작", use_container_width=True, key='saju_start_btn'):
            if user_a_data:
                st.session_state.user_a_input = user_a_data
                st.session_state.user_b_input = None
                with st.spinner('천기(天機)를 열어 데이터를 추출 중이네...'):
                    report = process_saju_input(user_a_data, db)
                    st.session_state.analysis_report = report
                    st.session_state.analysis_mode = 'saju'
                st.session_state.messages = [] 
                st.session_state.messages.append({"role": "assistant", "content": "분석을 마쳤네. 이제 보고서를 꼼꼼히 읽어보게!"})
                st.rerun()
            else: st.error("이름과 태어난 지역까지 입력해야 분석할 수 있네!")

    # 남녀 궁합 분석 모드
    elif analysis_mode == '💞 남녀 궁합 분석':
        st.subheader("1. 남자 (혹은 본인)")
        user_a_data = saju_input_form('user_a_comp')
        st.subheader("2. 여자 (혹은 상대방)")
        user_b_data = saju_input_form('user_b_comp')
        if st.button("궁합 분석 시작", use_container_width=True, key='love_start_btn'):
            if user_a_data and user_b_data:
                st.session_state.user_a_input = user_a_data
                st.session_state.user_b_input = user_b_data
                with st.spinner('두 사람의 인연줄(緣)을 엮어 분석 중이네...'):
                    report = process_love_compatibility(user_a_data, user_b_data, db)
                    st.session_state.analysis_report = report
                    st.session_state.analysis_mode = 'love'
                st.session_state.messages = [] 
                st.session_state.messages.append({"role": "assistant", "content": "두 사람의 궁합 분석을 마쳤네. 인연의 매듭을 풀어보게."})
                st.rerun()
            else: st.error("두 사람의 정보(이름, 지역 포함)를 모두 입력해야 궁합을 볼 수 있네!")

# --------------------------------------------------------------------------
# 3. [본문] 분석 보고서 출력 (강화)
# --------------------------------------------------------------------------

st.title("신령님의 AI 형이상학 분석소 📜")
st.caption("인간의 감정 대신, 데이터 기반의 객관적인 운명 분석을 제공하네.")

# 초기 메시지
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": "이 신령에게 **생년월일시(양력/음력), 성별, 태어난 지역**을 알려주게. 그리고 자네의 **고민**이 있다면 편하게 털어놓아 보게나."
    })
    
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.analysis_report:
    report = st.session_state.analysis_report
    
    if st.session_state.analysis_mode == 'saju':
        user_a = st.session_state.user_a_input
        st.subheader(f"## {user_a['name']}의 사주 분석 보고서 📜")
        
        saju_data = report['saju']
        st.markdown(f"> **생년월일시 (진태양시 기준):** {report['user']['true_solar_dt']}")
        st.markdown(f"> **사주 여덟 글자:** {saju_data['year_gan']}{saju_data['year_ji']} {saju_data['month_gan']}{saju_data['month_ji']} **{saju_data['day_gan']}{saju_data['day_ji']}** {saju_data['time_gan']}{saju_data['time_ji']}")
        
    elif st.session_state.analysis_mode == 'love':
        user_a = st.session_state.user_a_input
        user_b = st.session_state.user_b_input
        st.subheader(f"## {user_a['name']} ❤️ {user_b['name']} 궁합 분석 보고서 💘")
        
    st.markdown("---")
    
    for analysis in report['analytics']:
        st.markdown(f"### {analysis['type']} - {analysis['title']}")
        st.markdown(analysis['content'])
        st.markdown("---")

    # Disclaimer 추가
    st.markdown("""
> **[법적 면책 조항]**
> 본 분석은 명리학적 통계 데이터에 기반한 정보 제공 목적이며, 의학적 진단이나 법률적 확정 판결이 아닙니다. 중요한 결정은 반드시 전문가와 상의하십시오.
""")

# --------------------------------------------------------------------------
# 4. [대화창] 신령의 역할 수행 (룰 기반 응답 강화)
# --------------------------------------------------------------------------
if prompt := st.chat_input("신령님께 궁금한 것을 물어보게..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response_text = "지금은 내가 기도 중이라(API 미연동) 긴 대화는 어렵네. 위 분석 결과나 다시 꼼꼼히 읽어보게!"
    
    if st.session_state.analysis_report:
        
        if "언제" in prompt or "시기" in prompt or "좋아질까요" in prompt:
             response_text = "운명의 흐름은 끊임없이 변하는 법! **'세운 분석'** 항목을 보게. 자네에게 **가장 위험한 시기**와 **결실을 맺는 시기**가 명시되어 있네."
        elif "직업" in prompt or "진로" in prompt or "적성" in prompt:
             response_text = "보고서의 **'직업 및 적성 분석'**과 **'일주 기질 분석'** 항목을 집중해서 보게. 자네의 **타고난 천직**은 이미 정해져 있네. 그 기운을 따라야 평생 편안하네."
        elif "궁합" in prompt or "사랑" in prompt or "결혼" in prompt:
             response_text = "**'일간 기운 궁합 분석'**의 점수는 봤는가? 그리고 **'갈등 원인'** 항목을 보게. 상대의 단점만 보지 말고, 그 원인을 이해하고 **어떻게 보완할지** 고민해야 하네."
        elif "건강" in prompt or "아파요" in prompt:
             response_text = "**'오행 불균형 & 개운법'**과 **'습한/조열한 사주 진단'** 부분을 다시 읽어보게. 자네 몸의 근본적인 **에너지 문제**와 **환경적 요인**이 자세히 나와 있네. 처방전을 따르도록 하게."
        else:
             response_text = f"자네의 질문('{prompt}')은 이미 보고서에 답이 들어있거나, 아직 때가 되지 않아 천기누설에 해당하네. 보고서를 다시 보게나!"
    
    with st.chat_message("assistant"):
        st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
