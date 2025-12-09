import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import random
import saju_engine 
# [진단용 코드 - 확인 후 삭제하세요]
import os
st.write("📂 현재 위치:", os.getcwd())
db_path = "saju_db"
if os.path.exists(db_path):
    st.success(f"✅ '{db_path}' 폴더를 찾았습니다!")
    files = os.listdir(db_path)
    st.write(f"📄 폴더 내 파일 목록 ({len(files)}개):", files)
else:
    st.error(f"❌ '{db_path}' 폴더가 없습니다! JSON 파일들을 이 이름의 폴더 안에 넣으세요.")
# ==========================================
# 0. 설정 & 스타일
# ==========================================
st.set_page_config(page_title="신령: AI 점술가", page_icon="🧿", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    h1, h2, h3 { color: #ff8a80 !important; font-family: 'Unbatang', serif; }
    .stTextInput > div > div > input { background-color: #262730; color: white; border: 1px solid #4f4f4f; }
    
    /* 리포트 카드 */
    .shaman-card {
        background-color: #1e1e1e;
        border: 2px solid #5c0000;
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
    
    /* 채팅 스타일 */
    .chat-user { background-color: #2b313e; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: right; }
    .chat-bot { background-color: #3b2c2c; padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 3px solid #ff5252; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 시크릿 로드
# ==========================================
def get_google_sheet_client():
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    return None

def save_to_sheet(client, data_row):
    if not client: return
    try:
        sheet = client.open('user_data').sheet1
        sheet.append_row(data_row)
    except: pass

# ==========================================
# 2. 세션 초기화
# ==========================================
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = [("assistant", "무엇이 궁금하여 찾아왔는가?")]
if 'saju_result' not in st.session_state:
    st.session_state.saju_result = None
if 'mode' not in st.session_state:
    st.session_state.mode = "Personal"

# ==========================================
# 3. 사이드바 (입력 폼)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4743/4743125.png", width=80)
    st.title("운명 조회")
    
    # [모드 선택]
    mode_select = st.radio("분석 종류 선택", ["🧘 개인 정밀 분석", "💞 궁합/커플 분석"])
    st.session_state.mode = "Personal" if "개인" in mode_select else "Couple"
    
    st.markdown("---")
    
    with st.form("input_form"):
        # [A] 본인 정보 (공통)
        st.subheader("본인(A) 정보")
        name_a = st.text_input("이름/별명", "나", key="name_a")
        birth_date_a = st.date_input("생년월일", min_value=datetime(1940, 1, 1), key="date_a")
        birth_time_a = st.time_input("태어난 시간", key="time_a")
        gender_a = st.selectbox("성별", ["남성", "여성"], key="gen_a")
        
        # [B] 상대방 정보 (궁합 모드일 때만 활성화)
        name_b, birth_date_b, birth_time_b, gender_b = None, None, None, None
        if st.session_state.mode == "Couple":
            st.markdown("---")
            st.subheader("상대방(B) 정보")
            name_b = st.text_input("상대 이름", "그 사람", key="name_b")
            birth_date_b = st.date_input("상대 생년월일", min_value=datetime(1940, 1, 1), key="date_b")
            birth_time_b = st.time_input("상대 시간", key="time_b")
            gender_b = st.selectbox("상대 성별", ["여성", "남성"], key="gen_b") # 기본값 반대로
            
        submitted = st.form_submit_button("신령님께 여쭤보기 (Start)")

# ==========================================
# 4. 분석 로직 실행
# ==========================================
if submitted:
    with st.spinner("신령이 명부를 뒤지고 있습니다..."):
        user_a = {'name': name_a, 'year': birth_date_a.year, 'month': birth_date_a.month, 'day': birth_date_a.day, 'hour': birth_time_a.hour, 'gender': gender_a}
        
        try:
            if st.session_state.mode == "Personal":
                # 개인 분석
                result = saju_engine.analyze_saju(user_a)
                save_data = [str(datetime.now()), "PERSONAL", name_a, gender_a, str(birth_date_a)]
            else:
                # 궁합 분석
                user_b = {'name': name_b, 'year': birth_date_b.year, 'month': birth_date_b.month, 'day': birth_date_b.day, 'hour': birth_time_b.hour, 'gender': gender_b}
                result = saju_engine.analyze_compatibility(user_a, user_b)
                save_data = [str(datetime.now()), "COUPLE", f"{name_a}&{name_b}", f"{gender_a}+{gender_b}", "COMPATIBILITY"]
            
            st.session_state.saju_result = result
            
            # 시트 저장
            client = get_google_sheet_client()
            save_to_sheet(client, save_data)
            
        except Exception as e:
            st.error(f"천기누설 중 오류 발생: {e}")

# ==========================================
# 5. 메인 화면 (결과 & 채팅)
# ==========================================
st.title("🧿 신령(神靈)")

if st.session_state.saju_result:
    # 탭으로 결과와 채팅 분리
    tab1, tab2 = st.tabs(["📜 분석 리포트", "💬 신령과의 대화"])
    
    with tab1:
        report = st.session_state.saju_result
        
        # [상단 요약]
        if "saju_b" in report: # 궁합 모드
            st.info(f"💞 **{name_a}** vs **{name_b}**의 궁합 분석 결과일세.")
            col1, col2 = st.columns(2)
            col1.caption(f"{name_a}: {report['saju_a']['ganji_text']}")
            col2.caption(f"{name_b}: {report['saju_b']['ganji_text']}")
        else: # 개인 모드
            st.info(f"👤 **{name_a}**님의 운명 분석 결과일세.")
            st.caption(f"사주 명식: {report['saju']['ganji_text']}")

        # [카드 출력]
        analytics = report.get('analytics', [])
        for item in analytics:
            st.markdown(f"""
            <div class="shaman-card">
                <div class="shaman-card-title">{item['type']}</div>
                <div style="font-size: 1.1em; font-weight: bold; color: #fff; margin-bottom: 10px;">
                    {item['title']}
                </div>
                <div style="color: #ccc; line-height: 1.6;">
                    {item['content'].replace('\n', '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with tab2:
        st.caption("결과에 대해 더 궁금한 점을 물어보게. (예: '우리 언제 결혼해?', '내 직업은?')")
        
        # 채팅창
        for role, msg in st.session_state.chat_history:
            if role == "user":
                st.markdown(f'<div class="chat-user">👤 {msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bot">🧿 {msg}</div>', unsafe_allow_html=True)
                
        if prompt := st.chat_input("질문 입력..."):
            st.session_state.chat_history.append(("user", prompt))
            st.rerun()

    # [채팅 응답 로직 - Rerun 후 실행]
    if st.session_state.chat_history and st.session_state.chat_history[-1][0] == "user":
        last_query = st.session_state.chat_history[-1][1]
        
        # DB 기반 응답 생성
        ans = ""
        
        # 1. 용어 검색
        glossary = saju_engine.db.glossary
        if not glossary.empty:
            for idx, row in glossary.iterrows():
                if row['Term'].split('(')[0] in last_query:
                    ans += f"📖 **{row['Term']}**: {row['Shamanic_Voice']}\n\n"
                    break
        
        # 2. 리포트 컨텍스트 검색
        ctx_list = st.session_state.saju_result.get('chat_context', [])
        if not ans and ctx_list:
            # 단순 랜덤 매칭 (데모용)
            ans = "자네 사주를 보니, " + random.choice(ctx_list) + " 하는 기운이 있어."
            
        if not ans:
            ans = random.choice([
                "그건 내 명부에도 안 나오는구먼.",
                "더 구체적으로 물어보게. '재물', '연애' 처럼 말이야.",
                "천기누설이라 말해줄 수 없네.",
                "궁합이 궁금하면 '궁합' 모드로 다시 해보게."
            ])
            
        st.session_state.chat_history.append(("assistant", ans))
        st.rerun()

else:
    st.write("👈 왼쪽에서 **모드**를 선택하고 정보를 입력하게.")
    st.image("https://media.giphy.com/media/3o7TKSjRrfIPjeiQQo/giphy.gif", width=300) # 신비로운 GIF 예시
