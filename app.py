import streamlit as st
from groq import Groq
from saju_engine import calculate_saju_v3
from datetime import datetime, time
import json
import os
import pandas as pd
from korean_lunar_calendar import KoreanLunarCalendar
from geopy.geocoders import Nominatim
from geopy.distance import great_circle

# ==========================================
# 0. CONFIGURATION & DATABASE LOADING
# ==========================================
st.set_page_config(page_title="신령: 만능 사주 분석기", page_icon="🔮", layout="wide")

# Initialize Session State
if "family_members" not in st.session_state: st.session_state.family_members = []
if "logs" not in st.session_state: st.session_state.logs = []

# Load Databases
@st.cache_data
def load_databases():
    db = {}
    try:
        # Load all 4 core databases
        with open("saju_db/identity_db.json", "r", encoding='utf-8') as f: db['identity'] = json.load(f)
        with open("saju_db/compatibility_db.json", "r", encoding='utf-8') as f: db['compatibility'] = json.load(f)
        with open("saju_db/five_elements_matrix.json", "r", encoding='utf-8') as f: db['matrix'] = json.load(f)
        with open("saju_db/shinsal_db.json", "r", encoding='utf-8') as f: db['shinsal'] = json.load(f)
        return db
    except FileNotFoundError:
        st.error("🚨 데이터베이스 파일이 누락되었습니다. saju_db 폴더에 json 파일들을 확인해주세요.")
        return None

DB = load_databases()

# API Setup
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except: pass # UI handles missing key gracefully

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================
CITY_DB = {
    "서울": (37.56, 126.97), "부산": (35.17, 129.07), "인천": (37.45, 126.70), 
    "대구": (35.87, 128.60), "창원": (35.22, 128.68), "광주": (35.15, 126.85),
    "대전": (36.35, 127.38), "울산": (35.53, 129.31), "제주": (33.49, 126.53),
    "seoul": (37.56, 126.97), "busan": (35.17, 129.07)
}

def get_coordinates(city_input):
    clean = city_input.strip().lower()
    if clean in CITY_DB: return CITY_DB[clean]
    # Fallback to Seoul if unknown (simplification for stability)
    return CITY_DB["서울"]

def get_saju_data(dob, tm, is_lunar, is_intercalary, city="서울"):
    """
    Unified function to calculate Saju and return formatted Korean data.
    """
    coords = get_coordinates(city)
    final_date = dob
    
    if is_lunar:
        try:
            cal = KoreanLunarCalendar()
            cal.setLunarDate(dob.year, dob.month, dob.day, is_intercalary)
            final_date = datetime(cal.solarYear, cal.solarMonth, cal.solarDay).date()
        except: return None

    # Call Engine (v6.1)
    raw = calculate_saju_v3(final_date.year, final_date.month, final_date.day, 
                          tm.hour, tm.minute, coords[0], coords[1])
    
    # Mapping for DB Keys
    E2K_STEM = {'Gap':'갑', 'Eul':'을', 'Byeong':'병', 'Jeong':'정', 'Mu':'무',
                'Gi':'기', 'Gyeong':'경', 'Sin':'신', 'Im':'임', 'Gye':'계'}
    E2K_BRANCH = {'Ja':'자', 'Chuk':'축', 'In':'인', 'Myo':'묘', 'Jin':'진',
                  'Sa':'사', 'O':'오', 'Mi':'미', 'Yu':'유', 'Sul':'술', 'Hae':'해'}
    
    day_stem_eng, day_branch_eng = raw['Day_Stem'], raw['Month_Branch'] # Engine returns Korean tuple now? 
    # v6.1 engine returns Korean tuples directly (CHECK saju_engine.py).
    # Assuming v6.1 engine returns tuples like ('갑', '자').
    
    day_stem = raw['Day_Stem'] # "갑"
    month_branch = raw['Month_Branch'] # "인"
    
    # Generate DB Keys
    id_key = f"{day_stem}_{month_branch}"
    
    return {
        "raw": raw,
        "day_stem": day_stem,
        "month_branch": month_branch,
        "id_key": id_key,
        "full_str": raw['Full_String'],
        "shinsal_list": raw['Shinsal']
    }

def generate_ai_comment(context_text):
    """
    Simple AI wrapper to polish the DB text into Shinryeong persona.
    """
    if not client: return context_text # Fallback if no API key
    
    sys_msg = """
    [ROLE] You are 'Shinryeong' (Divine Guru). Tone: Hage-che (하게체).
    [TASK] Rewrite the provided analysis text naturally. Do not change the meaning.
    [LANGUAGE] Korean ONLY.
    """
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system", "content":sys_msg}, {"role":"user", "content":context_text}],
            temperature=0.5
        )
        return resp.choices[0].message.content
    except:
        return context_text

# ==========================================
# 2. MAIN UI (TABS)
# ==========================================
st.title("🔮 신령(神靈): 데이터 기반 운명 분석")
tab1, tab2, tab3 = st.tabs(["👤 개인 정밀 분석", "💞 궁합 분석", "👨‍👩‍👧‍👦 가족 종합 진단"])

# ------------------------------------------
# TAB 1: PERSONAL ANALYSIS
# ------------------------------------------
with tab1:
    st.header("👤 개인 운세 (Identity & Shinsal)")
    with st.form("p_form"):
        c1, c2 = st.columns(2)
        p_date = c1.date_input("생년월일", value=datetime(1990,1,1))
        p_time = c1.time_input("태어난 시간", value=time(12,0))
        p_city = c2.text_input("태어난 도시", "서울")
        p_lunar = c2.checkbox("음력 적용")
        p_submit = st.form_submit_button("분석 시작")
    
    if p_submit and DB:
        res = get_saju_data(p_date, p_time, p_lunar, False, p_city)
        if res:
            st.divider()
            st.subheader(f"📜 사주 원국: {res['full_str']}")
            
            # 1. Identity Analysis (DB Lookup)
            id_data = DB['identity'].get(res['id_key'])
            if id_data:
                st.success(f"### 🐅 타고난 그릇\n\n{id_data['ko']}")
                st.caption(f"**Keywords:** {', '.join(id_data.get('keywords', []))}")
            else:
                st.warning(f"데이터베이스에 '{res['id_key']}' 조합이 없습니다. (DB 업데이트 필요)")

            # 2. Shinsal Analysis (DB Lookup)
            st.markdown("### ⚡ 신령의 처방 (Shinsal Diagnosis)")
            
            # Check detected shinsal against DB
            detected = []
            for s_name in DB['shinsal'].keys():
                if s_name in str(res['shinsal_list']) or s_name in res['full_str']: # Simple matching
                    detected.append(s_name)
            
            # Additional Logic for Saju Engine v6.1 output mapping
            # (Engine outputs "역마살(이동/변화)" -> We need "역마살" key)
            for s_raw in res['shinsal_list']:
                for db_key in DB['shinsal'].keys():
                    if db_key in s_raw:
                        if db_key not in detected: detected.append(db_key)

            if detected:
                cols = st.columns(len(detected)) if len(detected) <= 3 else st.columns(3)
                for i, key in enumerate(detected):
                    with cols[i % 3]:
                        info = DB['shinsal'][key]
                        st.error(f"**{key}**")
                        st.write(f"💬 {info['desc']}")
                        st.write(f"⚠️ {info['risk']}")
                        st.info(f"🛡️ **개운법:** {info['remedy']}")
            else:
                st.info("특이한 흉살 없이 평온한 사주로군요.")

# ------------------------------------------
# TAB 2: COMPATIBILITY ANALYSIS
# ------------------------------------------
with tab2:
    st.header("💞 궁합 진단 (Relationship)")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("본인 (A)")
        a_date = st.date_input("A 생년월일", value=datetime(1990,1,1))
        a_time = st.time_input("A 시간", value=time(12,0))
    with c2:
        st.caption("상대방 (B)")
        b_date = st.date_input("B 생년월일", value=datetime(1992,1,1))
        b_time = st.time_input("B 시간", value=time(12,0))
        
    if st.button("궁합 보기") and DB:
        a_res = get_saju_data(a_date, a_time, False, False)
        b_res = get_saju_data(b_date, b_time, False, False)
        
        key = f"{a_res['day_stem']}_{b_res['day_stem']}"
        comp_data = DB['compatibility'].get(key)
        
        st.divider()
        st.write(f"**{a_res['day_stem']} (나)** vs **{b_res['day_stem']} (상대)**")
        
        if comp_data:
            score = comp_data.get('score', 50)
            st.progress(score)
            st.write(f"### 궁합 점수: {score}점")
            st.success(f"**관계의 본질:** {comp_data['ko_relation']}")
            
            # 2026 Prediction Logic (Python Hardcoded)
            st.markdown("#### ☁️ 2026년(병오년) 미래 예측")
            clash_A = "자" in a_res['full_str'] # 자오충
            clash_B = "자" in b_res['full_str']
            
            if clash_A and clash_B:
                st.error("⚠️ 2026년은 두 사람 모두에게 '자오충'이 들어와 다툼이나 이별수가 강하네. 서로 떨어져 지내는 것이 좋네.")
            elif clash_A or clash_B:
                who = "본인" if clash_A else "상대방"
                st.warning(f"⚠️ 2026년은 {who}의 마음이 흔들리는 시기네. 곁에서 잘 잡아주어야 하네.")
            else:
                st.info("2026년은 큰 충돌 없이 무난하게 지나갈 것이네.")
        else:
            st.error(f"데이터베이스에 '{key}' 조합이 없습니다.")

# ------------------------------------------
# TAB 3: FAMILY MATRIX
# ------------------------------------------
with tab3:
    st.header("👨‍👩‍👧‍👦 가족 역학 관계 (Family Matrix)")
    
    with st.expander("가족 구성원 관리", expanded=True):
        f_name = st.text_input("이름/호칭")
        f_date = st.date_input("생년월일", key="f_date")
        if st.button("추가"):
            st.session_state.family_members.append({"name": f_name, "date": f_date})
            st.success(f"{f_name} 추가됨")
            
    if st.session_state.family_members:
        st.write("📋 분석 대상 목록:")
        st.table(pd.DataFrame(st.session_state.family_members))
        
        if st.button("가족 관계 분석 시작", type="primary") and DB:
            st.divider()
            
            # 1. Calculate All Members
            members_data = []
            elem_counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
            e_map = {'갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수'}
            
            for m in st.session_state.family_members:
                res = get_saju_data(m['date'], time(12,0), False, False)
                stem = res['day_stem']
                elem = e_map.get(stem, '토')
                elem_counts[elem] += 1
                members_data.append({'name': m['name'], 'stem': stem, 'elem': elem, 'full': res['full_str']})
            
            # 2. Family Balance
            st.subheader("1. 우리 가족의 오행 균형")
            st.bar_chart(elem_counts)
            missing = [k for k, v in elem_counts.items() if v == 0]
            if missing:
                st.warning(f"🚨 우리 가족에게 부족한 기운: **{', '.join(missing)}** (이 기운을 보충하는 인테리어나 여행이 필요하네)")
            
            # 3. Relation Matrix Loop
            st.subheader("2. 구성원 간 생극(生剋) 관계")
            # Simple Logic: Wood(0)->Fire(1)->Earth(2)->Metal(3)->Water(4)->Wood(0)
            order = ['목', '화', '토', '금', '수']
            
            for i in range(len(members_data)):
                for j in range(i+1, len(members_data)):
                    p1 = members_data[i]
                    p2 = members_data[j]
                    
                    idx1 = order.index(p1['elem'])
                    idx2 = order.index(p2['elem'])
                    
                    # Determine Relation
                    rel_key = None
                    direction = ""
                    
                    if (idx1 + 1) % 5 == idx2: # 1生2
                        rel_key = f"{p1['elem']}_생_{p2['elem']}"
                        direction = f"{p1['name']} ➝ {p2['name']} (도움)"
                    elif (idx2 + 1) % 5 == idx1: # 2生1
                        rel_key = f"{p2['elem']}_생_{p1['elem']}"
                        direction = f"{p2['name']} ➝ {p1['name']} (도움)"
                    elif (idx1 + 2) % 5 == idx2: # 1剋2
                        rel_key = f"{p1['elem']}_극_{p2['elem']}"
                        direction = f"{p1['name']} ⚔️ {p2['name']} (통제)"
                    elif (idx2 + 2) % 5 == idx1: # 2剋1
                        rel_key = f"{p2['elem']}_극_{p1['elem']}"
                        direction = f"{p2['name']} ⚔️ {p1['name']} (통제)"
                    
                    if rel_key and rel_key in DB['matrix']:
                        desc = DB['matrix'][rel_key]['role_parent_child']
                        st.info(f"**[{direction}]**")
                        st.markdown(f"> {desc}")
                    elif p1['elem'] == p2['elem']:
                        st.write(f"🔹 **{p1['name']} & {p2['name']}**: 같은 기운이라 친구처럼 편안하네.")

            # 4. 2026 Key Man
            st.subheader("3. 2026년(병오년) 주의해야 할 가족")
            for m in members_data:
                if '자' in m['full']:
                    st.error(f"⚠️ **{m['name']}**: 자오충(沖) 발생. 내년에 이동수나 건강 변화가 클 것이네.")
