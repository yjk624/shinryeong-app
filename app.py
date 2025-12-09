import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import random

# [중요] saju_engine이 같은 폴더에 있어야 함
import saju_engine 

# ==========================================
# 0. 기본 설정 & 스타일 (Shaman UI)
# ==========================================
st.set_page_config(
    page_title="신령(神靈): AI 형이상학 분석가",
    page_icon="🧿",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 신비롭고 어두운 테마 적용 (CSS)
st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    h1, h2, h3 {
        color: #ff8a80 !important; /* 붉은색 포인트 */
        font-family: 'Unbatang', serif;
    }
    
    /* 입력 필드 스타일 */
    .stTextInput > div > div > input {
        background-color: #262730;
        color: white;
        border: 1px solid #4f4f4f;
    }
    
    /* 리포트 박스 스타일 */
    .shaman-card {
        background-color: #1e1e1e;
        border: 2px solid #5c0000; /* 진한 붉은 테두리 */
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .shaman-card-title {
        color: #ff5252;
        font-size: 1.3em;
        font-weight: bold;
        margin-bottom: 10px;
        border-bottom: 1px solid #444;
        padding-bottom: 5px;
    }
    .shaman-highlight {
        color: #ffd700; /* 금색 강조 */
        font-weight: bold;
    }
    
    /* 채팅 메시지 스타일 */
    .chat-user {
        background-color: #2b313e;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        text-align: right;
    }
    .chat-bot {
        background-color: #3b2c2c; /* 붉은 톤의 어두운 배경 */
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        border-left: 3px solid #ff5252;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 시크릿(Secrets) 로드 & 구글 시트 연결
# ==========================================
def get_google_sheet_client():
    """Streamlit Secrets에서 구글 인증 정보를 가져와 연결"""
    try:
        # st.secrets["gcp_service_account"]에 JSON 내용이 있다고 가정
        if "gcp_service_account" in st.secrets:
            # 딕셔너리 형태로 바로 사용
            creds_dict = dict(st.secrets["gcp_service_account"])
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client
        else:
            return None
    except Exception as e:
        st.error(f"구글 시트 연결 오류: {e}")
        return None

def save_to_sheet(client, data_row):
    """데이터를 구글 시트에 저장"""
    if not client:
        return
    try:
        # 시트 이름이 'user_data'라고 가정 (없으면 미리 만들어야 함)
        sheet = client.open('user_data').sheet1
        sheet.append_row(data_row)
    except Exception as e:
        # 사용자에겐 에러를 굳이 보여주지 않음 (로그만 남김)
        print(f"시트 저장 실패: {e}")

# ==========================================
# 2. 세션 상태 초기화
# ==========================================
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    # 초기 인사말
    st.session_state.chat_history.append(("assistant", "내 눈을 바라보게. 궁금한 게 있으면 물어봐. 내 명부(DB)에 있는 건 다 알려주지."))
    
if 'saju_result' not in st.session_state:
    st.session_state.saju_result = None

# ==========================================
# 3. 사이드바: 사주 정보 입력
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4743/4743125.png", width=80) # 신비로운 아이콘 예시
    st.title("정보 입력")
    
    with st.form("input_form"):
        name = st.text_input("이름 (선택)", "익명")
        birth_date = st.date_input("생년월일", min_value=datetime(1940, 1, 1))
        birth_time = st.time_input("태어난 시간")
        gender = st.selectbox("성별", ["남성", "여성"])
        
        submitted = st.form_submit_button("운명 분석 시작 (Analyze)")
        
    st.markdown("---")
    st.caption("🔒 모든 정보는 암호화되어 처리되며, 분석 즉시 파기됩니다.")

# ==========================================
# 4. 메인 로직: 사주 분석 & 리포트 생성
# ==========================================
if submitted:
    with st.spinner("신령이 붓을 들어 사주를 적어내려갑니다..."):
        # 1. 입력 데이터 가공
        user_input = {
            'year': birth_date.year,
            'month': birth_date.month,
            'day': birth_date.day,
            'hour': birth_time.hour,
            'gender': gender
        }
        
        # 2. 엔진 호출 (saju_db 폴더를 뒤져서 분석)
        try:
            result = saju_engine.analyze_saju(user_input)
            st.session_state.saju_result = result
            
            # 3. 구글 시트 저장 시도
            client = get_google_sheet_client()
            if client:
                save_data = [
                    str(datetime.now()), 
                    name, 
                    gender, 
                    f"{birth_date} {birth_time}",
                    str(result.get('saju', {}).get('ganji_text', ''))
                ]
                save_to_sheet(client, save_data)
                
        except Exception as e:
            st.error(f"분석 중 천기누설 오류가 발생했네: {e}")

# ==========================================
# 5. UI: 분석 리포트 출력
# ==========================================
st.title("🧿 신령(神靈)")
st.subheader("데이터로 보는 당신의 형이상학적 본질")

if st.session_state.saju_result:
    report = st.session_state.saju_result
    
    # [상단] 사주 팔자 요약
    saju_info = report.get('saju', {})
    st.info(f"📅 **사주 명식**: {saju_info.get('ganji_text', '정보 없음')} | {gender}")
    
    # [중단] 분석 카드 나열 (Engine에서 가져온 데이터)
    analytics = report.get('analytics', [])
    
    if not analytics:
        st.warning("특이 사항이 없거나 DB 연결에 실패했네. 평범한 게 가장 좋은 것이지.")
    
    for item in analytics:
        # HTML/CSS를 이용한 커스텀 카드 출력
        st.markdown(f"""
        <div class="shaman-card">
            <div class="shaman-card-title">{item.get('type', '알 수 없음')}</div>
            <div style="font-size: 1.15em; font-weight: bold; color: #fff; margin-bottom: 8px;">
                {item.get('title', '')}
            </div>
            <div style="line-height: 1.6; color: #ccc;">
                {item.get('content', '').replace('\n', '<br>')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
else:
    st.write("👈 왼쪽 사이드바에 생년월일을 입력하고 **'분석 시작'**을 누르게.")
    st.write("자네의 운명이 데이터베이스 속에 잠들어 있네.")

# ==========================================
# 6. UI: 채팅 기능 (DB 기반 지식 검색)
# ==========================================
st.divider()
st.subheader("💬 신령과의 대화")
st.caption("분석 결과나 사주 용어에 대해 물어보게. (예: '내 재물운은?', '역마살이 뭐야?')")

# 1. 채팅창 출력
for role, message in st.session_state.chat_history:
    if role == "user":
        st.markdown(f'<div class="chat-user">👤 <b>당신:</b> {message}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-bot">🧿 <b>신령:</b> {message}</div>', unsafe_allow_html=True)

# 2. 질문 입력 처리
if prompt := st.chat_input("질문을 입력하게..."):
    # 사용자 메시지 저장
    st.session_state.chat_history.append(("user", prompt))
    st.rerun() # 화면 갱신 후 답변 생성으로 넘어감

# 3. 답변 생성 로직 (Rerun 후 실행됨)
if st.session_state.chat_history and st.session_state.chat_history[-1][0] == "user":
    user_query = st.session_state.chat_history[-1][1]
    
    # --- [신령의 뇌] DB 검색 알고리즘 ---
    response = ""
    found_answer = False
    
    # (A) saju_glossary_v2.csv 검색 (용어 정의)
    glossary = saju_engine.db.glossary
    if not glossary.empty:
        for idx, row in glossary.iterrows():
            term = row['Term'].split('(')[0] # '비견(比肩)' -> '비견'만 추출
            if term in user_query:
                response += f"📖 **[{row['Term']}]**에 대해 궁금한가?\n{row['Shamanic_Voice']}\n\n"
                found_answer = True
                # 너무 많이 나오면 지저분하므로 하나 찾으면 break 할 수도 있음 (선택사항)
    
    # (B) 현재 분석 리포트 컨텍스트 검색 (개인화된 답변)
    if st.session_state.saju_result:
        # 채팅 컨텍스트(saju_engine에서 생성한 요약본) 활용
        context_list = st.session_state.saju_result.get('chat_context', [])
        
        # 키워드 매칭
        keywords = {
            '재물': ['편재', '정재', '돈', '사업', '재성'],
            '직업': ['관성', '식상', '취업', '승진', '적성'],
            '건강': ['오행', '과다', '고립', '병원'],
            '연애': ['도화', '홍염', '관성', '재성', '궁합', '결혼'],
            '2026': ['2026', '내년', '병오'],
        }
        
        for key, synonyms in keywords.items():
            if any(s in user_query for s in synonyms):
                # 해당 주제와 관련된 리포트 내용이 있는지 확인
                related_info = [ctx for ctx in context_list if key in ctx or any(s in ctx for s in synonyms)]
                if related_info:
                    response += f"💡 자네 사주를 보니 **{key}** 쪽으로는 이런 게 보이네:\n"
                    for info in related_info:
                        response += f"- {info}\n"
                    response += "\n"
                    found_answer = True
                    
    # (C) 못 찾았을 때의 기본 답변 (Fallback)
    if not found_answer:
        default_responses = [
            "흐음... 내 명부(DB)에는 딱히 적힌 게 없구먼. 질문을 좀 더 쉽게, 단어 위주로 해보게.",
            "천기누설이라 말해주기 어렵거나, 자네 사주랑은 상관없는 얘기야.",
            "그건 나중에 유료 결제하면 알려주지. (농담일세)",
            "내 DB에 없는 내용이야. '재물', '건강', '2026년' 처럼 콕 집어서 물어봐."
        ]
        response = random.choice(default_responses)

    # 답변 저장
    st.session_state.chat_history.append(("assistant", response))
    st.rerun()
