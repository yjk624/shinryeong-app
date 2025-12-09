import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import random
import saju_engine 

# ==========================================
# 0. 설정 & 스타일
# ==========================================
st.set_page_config(page_title="신령: 글로벌 운명 분석", page_icon="🧿", layout="wide") # wide 모드 적용

st.markdown("""
<style>
    .stApp { background-color: #080808; color: #e0e0e0; }
    h1 { color: #ff5252; font-family: 'Gungsuh', serif; text-align: center; font-size: 3em;}
    .big-input { font-size: 1.2em; }
    
    /* 카드 스타일 */
    .shaman-card {
        background-color: #1a1a1a;
        border: 1px solid #333;
        border-left: 5px solid #ff5252;
        padding: 20px;
        margin-bottom: 15px;
        border-radius: 8px;
    }
    .card-head { font-size: 1.1em; color: #ff8a80; font-weight: bold; margin-bottom: 5px;}
    .card-body { font-size: 1.0em; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 세션 & 초기화
# ==========================================
if 'step' not in st.session_state: st.session_state.step = 1
if 'saju_result' not in st.session_state: st.session_state.saju_result = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

# ==========================================
# 2. 메인 화면 (입력 단계별 진행)
# ==========================================
st.title("🧿 신 령 (神 靈)")
st.markdown("<div style='text-align: center; color: #888;'>전 세계 어디서 태어났든, 하늘의 시간을 읽어 운명을 꿰뚫는다.</div>", unsafe_allow_html=True)
st.divider()

# [입력 컨테이너]
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # 탭 대신 모드 선택
        mode = st.radio("분석 모드를 선택하게", ["🧘 개인 정밀 분석", "💞 궁합/커플 분석"], horizontal=True)
        
        with st.form("main_form"):
            st.subheader("📝 정보 입력")
            
            # [본인 정보]
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
            
            # [상대방 정보 - 궁합 시]
            name_b, city_b, date_b, time_b, gender_b = None, None, None, None, None
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
# 3. 분석 로직 및 결과 표시
# ==========================================
if submit:
    with st.spinner("지구 반대편의 별자리까지 계산 중일세..."):
        # 입력 데이터 패키징
        user_a = {
            'name': name_a, 'gender': gender_a, 'city': city_a,
            'year': date_a.year, 'month': date_a.month, 'day': date_a.day,
            'hour': time_a.hour, 'minute': time_a.minute
        }
        
        try:
            if "궁합" not in mode:
                # [개인 분석]
                result = saju_engine.analyze_saju_precision(user_a)
                st.session_state.saju_result = result
            else:
                # [궁합 분석] (간략 구현: 두 명 각각 분석 후 결합)
                user_b = {
                    'name': name_b, 'gender': gender_b, 'city': city_b,
                    'year': date_b.year, 'month': date_b.month, 'day': date_b.day,
                    'hour': time_b.hour, 'minute': time_b.minute
                }
                res_a = saju_engine.analyze_saju_precision(user_a)
                res_b = saju_engine.analyze_saju_precision(user_b)
                
                # 궁합 로직 (saju_engine의 compatibility 호출 대신 여기서 결합 예시)
                # 실제로는 saju_engine.analyze_compatibility_precision 구현 필요
                # 여기서는 res_a와 res_b를 합친 딕셔너리 생성
                st.session_state.saju_result = {
                    'saju': res_a['saju'], # A 기준 표시
                    'saju_b': res_b['saju'],
                    'analytics': res_a['analytics'] + [{"type":"💞 상대방 분석", "title":f"{name_b}의 기질", "content":"(상대방 상세 분석 데이터...)"}],
                    'chat_context': res_a['chat_context'] + res_b['chat_context']
                }
                
        except Exception as e:
            st.error(f"천기누설 오류: {e}")

# ==========================================
# 4. 결과 리포트 & 채팅
# ==========================================
if st.session_state.saju_result:
    res = st.session_state.saju_result
    st.divider()
    
    # [1] 명식 정보 표시
    c_info1, c_info2 = st.columns(2)
    with c_info1:
        st.success(f"👤 **{name_a}** | {res['saju']['location_info']}")
        st.write(f"🏷️ **사주 명식:** {res['saju']['ganji_text']}")
    
    if 'saju_b' in res:
        with c_info2:
            st.info(f"👤 **{name_b}** | {res['saju_b']['location_info']}")
            st.write(f"🏷️ **사주 명식:** {res['saju_b']['ganji_text']}")
            
    # [2] 분석 카드 (가로 배치)
    st.subheader("📜 분석 결과")
    analytics = res.get('analytics', [])
    
    # 2열 그리드로 카드 배치
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
            
    # [3] 채팅
    st.divider()
    st.subheader("💬 신령에게 물어보게")
    
    # 채팅 기록
    for role, msg in st.session_state.chat_history:
        align = "right" if role == "user" else "left"
        bg = "#2b313e" if role == "user" else "#3b2c2c"
        st.markdown(f"<div style='text-align:{align}; background:{bg}; padding:10px; border-radius:10px; margin:5px; display:inline-block;'>{msg}</div><div style='clear:both;'></div>", unsafe_allow_html=True)
        
    if q := st.chat_input("질문 입력..."):
        st.session_state.chat_history.append(("user", q))
        # (답변 로직은 기존과 동일하므로 생략 - 리런 시 처리됨)
        st.session_state.chat_history.append(("assistant", "내 데이터를 찾아보니... (답변 로직 연결 필요)"))
        st.rerun()
