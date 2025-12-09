import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import random
import saju_engine 

st.set_page_config(page_title="신령: 글로벌 운명 분석", page_icon="🧿", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #080808; color: #e0e0e0; }
    h1 { color: #ff5252; font-family: 'Gungsuh', serif; text-align: center; font-size: 3em;}
    .shaman-card { background-color: #1a1a1a; border: 1px solid #333; border-left: 5px solid #ff5252; padding: 20px; margin-bottom: 15px; border-radius: 8px; }
    .card-head { font-size: 1.1em; color: #ff8a80; font-weight: bold; margin-bottom: 5px;}
    .card-body { font-size: 1.0em; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# [진단 기능] 사이드바 하단에 DB 상태 표시
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4743/4743125.png", width=80)
    st.title("운명 조회")
    
    # DB 상태 확인 (디버깅용)
    with st.expander("🛠️ 시스템 상태 (Debug)"):
        st.write(f"📂 DB 폴더: `{saju_engine.db.db_folder}`")
        if not os.path.exists(saju_engine.db.db_folder):
            st.error("❌ 폴더가 없습니다!")
        else:
            status = saju_engine.db.load_status
            for file, msg in status.items():
                if "❌" in msg:
                    st.error(f"{file}: {msg}")
                else:
                    st.caption(f"{file}: {msg}")

# ==========================================
# 1. 메인 화면 (입력)
# ==========================================
st.title("🧿 신 령 (神 靈)")
st.markdown("<div style='text-align: center; color: #888;'>전 세계 어디서 태어났든, 하늘의 시간을 읽어 운명을 꿰뚫는다.</div>", unsafe_allow_html=True)
st.divider()

if 'saju_result' not in st.session_state: st.session_state.saju_result = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        mode = st.radio("분석 모드를 선택하게", ["🧘 개인 정밀 분석", "💞 궁합/커플 분석"], horizontal=True)
        
        with st.form("main_form"):
            st.subheader("📝 정보 입력")
            c1, c2 = st.columns(2)
            with c1:
                name_a = st.text_input("이름 (본인)", "나")
                gender_a = st.selectbox("성별", ["남성", "여성"])
            with c2:
                city_a = st.text_input("태어난 도시 (예: Seoul, New York)", "Seoul")
                
            d1, d2 = st.columns(2)
            with d1:
                date_a = st.date_input("생년월일", min_value=datetime(1940, 1, 1))
            with d2:
                time_a = st.time_input("태어난 시간")
            
            # 궁합 모드
            name_b = city_b = date_b = time_b = gender_b = None
            if "궁합" in mode:
                st.markdown("---")
                st.subheader("💕 상대방 정보")
                c3, c4 = st.columns(2)
                with c3:
                    name_b = st.text_input("이름 (상대)", "그 사람")
                    gender_b = st.selectbox("성별 (상대)", ["여성", "남성"])
                with c4:
                    city_b = st.text_input("태어난 도시 (상대)", "Seoul")
                d3, d4 = st.columns(2)
                with d3:
                    date_b = st.date_input("생년월일 (상대)", min_value=datetime(1940, 1, 1))
                with d4:
                    time_b = st.time_input("태어난 시간 (상대)")
            
            submit = st.form_submit_button("🔥 신령의 분석 시작", use_container_width=True)

# ==========================================
# 2. 로직 실행
# ==========================================
if submit:
    with st.spinner("명부를 펼치는 중..."):
        user_a = {'name': name_a, 'gender': gender_a, 'city': city_a, 'year': date_a.year, 'month': date_a.month, 'day': date_a.day, 'hour': time_a.hour, 'minute': time_a.minute}
        try:
            if "궁합" not in mode:
                result = saju_engine.analyze_saju_precision(user_a)
                st.session_state.saju_result = result
            else:
                user_b = {'name': name_b, 'gender': gender_b, 'city': city_b, 'year': date_b.year, 'month': date_b.month, 'day': date_b.day, 'hour': time_b.hour, 'minute': time_b.minute}
                result = saju_engine.analyze_compatibility_precision(user_a, user_b)
                st.session_state.saju_result = result
        except Exception as e:
            st.error(f"오류: {e}")

# ==========================================
# 3. 결과 표시
# ==========================================
if st.session_state.saju_result:
    res = st.session_state.saju_result
    st.divider()
    
    # 명식 정보
    c_info1, c_info2 = st.columns(2)
    with c_info1:
        st.success(f"👤 **{name_a}** | {res['saju']['location_info']}")
        st.write(f"🏷️ **사주 명식:** {res['saju']['ganji_text']}")
    
    if 'saju_b' in res:
        with c_info2:
            st.info(f"👤 **{name_b}** | {res['saju_b']['location_info']}")
            st.write(f"🏷️ **사주 명식:** {res['saju_b']['ganji_text']}")
            
    # 분석 카드
    st.subheader("📜 분석 결과")
    analytics = res.get('analytics', [])
    if not analytics:
        st.warning("⚠️ 분석된 내용이 없습니다. 사이드바의 '시스템 상태'를 확인하여 DB 로드 오류가 있는지 보세요.")
    
    row1 = st.columns(2)
    for i, item in enumerate(analytics):
        with row1[i % 2]:
            st.markdown(f"""
            <div class="shaman-card">
                <div class="card-head">{item['type']}</div>
                <h3>{item['title']}</h3>
                <div class="card-body">{item['content'].replace('\n','<br>')}</div>
            </div>
            """, unsafe_allow_html=True)
            
    # 채팅
    st.divider()
    st.subheader("💬 신령에게 물어보게")
    for role, msg in st.session_state.chat_history:
        align = "right" if role == "user" else "left"
        bg = "#2b313e" if role == "user" else "#3b2c2c"
        st.markdown(f"<div style='text-align:{align}; background:{bg}; padding:10px; border-radius:10px; margin:5px; display:inline-block;'>{msg}</div><div style='clear:both;'></div>", unsafe_allow_html=True)
        
    if q := st.chat_input("질문 입력..."):
        st.session_state.chat_history.append(("user", q))
        
        # 간단 답변 로직
        ans = ""
        glossary = saju_engine.db.glossary
        if not glossary.empty:
            for idx, row in glossary.iterrows():
                if row['Term'].split('(')[0] in q:
                    ans = row['Shamanic_Voice']
                    break
        if not ans:
            ans = "천기누설이라 말해줄 수 없네. (용어 위주로 질문해보게)"
            
        st.session_state.chat_history.append(("assistant", ans))
        st.rerun()
