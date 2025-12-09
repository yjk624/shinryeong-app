import json
import pandas as pd
import os
import random

# ==========================================
# 1. 데이터베이스 로더 (DB Loader)
# ==========================================
class SajuDB:
    def __init__(self):
        self.db_folder = "saju_db" # 폴더명 확인
        
        self.glossary = self.load_csv('saju_glossary_v2.csv')
        self.five_elements = self.load_json('five_elements_matrix.json')
        self.timeline = self.load_json('timeline_db.json')
        self.shinsal = self.load_json('shinsal_db.json')
        self.love = self.load_json('love_db.json')
        self.health = self.load_json('health_db.json')
        self.career = self.load_json('career_db.json')
        self.symptom = self.load_json('symptom_mapping.json')
        # 궁합 DB가 없다면 love_db로 대체됨
        self.compatibility = self.load_json('compatibility_db.json')

    def load_json(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_csv(self, filename):
        full_path = os.path.join(self.db_folder, filename)
        try:
            return pd.read_csv(full_path)
        except FileNotFoundError:
            return pd.DataFrame()

db = SajuDB()

# ==========================================
# 2. 사주 만세력 계산 (Calculator)
# ==========================================
# (간단한 로직 예시 - 실제 정밀 계산은 ephem 라이브러리 활용 권장)
CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
OHENG_MAP = {
    '갑': '목', '을': '목', '병': '화', '정': '화', '무': '토',
    '기': '토', '경': '금', '신': '금', '임': '수', '계': '수',
    '인': '목', '묘': '목', '사': '화', '오': '화', '진': '토', '술': '토', '축': '토', '미': '토',
    '신': '금', '유': '금', '해': '수', '자': '수'
}

def get_ganji_dummy(year, month, day, hour):
    # 실제로는 복잡한 절기력 알고리즘이 필요하나, 여기서는 데모용 매핑을 사용합니다.
    # 랜덤성을 부여하지 않고 입력값에 고정된 결과를 내도록 해시 사용
    seed = year + month + day + hour
    
    y_idx = (year - 4) % 60
    stem_year = CHEONGAN[y_idx % 10]
    branch_year = JIJI[y_idx % 12]
    
    # 월/일/시는 간단히 모듈로 연산 (데모용)
    stem_day = CHEONGAN[(seed) % 10]
    branch_day = JIJI[(seed) % 12]
    
    # 오행 개수 계산 (가상)
    oheng_counts = {'목': 0, '화': 0, '토': 0, '금': 0, '수': 0}
    # 일간의 오행 추가
    day_elem = OHENG_MAP[stem_day]
    oheng_counts[day_elem] += 1
    # 임의로 오행 추가 (실제론 사주 8글자 전체 분석 필요)
    for _ in range(3):
        rand_elem = list(oheng_counts.keys())[seed % 5]
        oheng_counts[rand_elem] += 1
        
    return {
        'ganji_text': f"{stem_year}{branch_year}년 {stem_day}{branch_day}일생",
        'day_stem': stem_day,
        'day_elem': day_elem,
        'five_elem_counts': oheng_counts
    }

# ==========================================
# 3. 개인 분석 엔진 (Individual)
# ==========================================
def analyze_saju(user_input):
    saju = get_ganji_dummy(user_input['year'], user_input['month'], user_input['day'], user_input['hour'])
    
    report = {
        "saju": saju,
        "analytics": [],
        "chat_context": []
    }
    
    # [1] 오행 분석 (성격/건강)
    counts = saju['five_elem_counts']
    for elem, count in counts.items():
        if count >= 3: # 과다
            key = f"{elem}({_get_eng(elem)})"
            if db.five_elements and 'imbalance_analysis' in db.five_elements:
                data = db.five_elements['imbalance_analysis'].get(key, {}).get('excess', {})
                if data:
                    report['analytics'].append({
                        "type": "⚠️ 타고난 기질 (과다)",
                        "title": data.get('title'),
                        "content": data.get('shamanic_voice')
                    })
                    report['chat_context'].append(f"{elem} 기운이 너무 강함")

    # [2] 2026년 운세
    if db.timeline and 'future_flow_db' in db.timeline:
        flow = db.timeline['future_flow_db'].get('2026_Byeong_O', {})
        report['analytics'].append({
            "type": "🔮 2026년 병오년 예언",
            "title": flow.get('year_title'),
            "content": f"{flow.get('summary')}\n\n[여름 경고] {flow.get('Q2_Summer', {}).get('shamanic_warning')}"
        })
        
    # [3] 직업/적성 (Career) - career_db.json 활용
    # 가장 강한 오행을 기반으로 매핑 (간략화)
    strongest = max(counts, key=counts.get)
    # 예: 목->식상, 화->재성 등 가상의 매핑 (실제론 십성 계산 필요)
    mapping_mock = {'목': '식상_발달', '화': '재성_발달', '토': '비겁_태과', '금': '관성_발달', '수': '인성_발달'}
    job_key = mapping_mock.get(strongest) + f"({_get_eng_job(strongest)})" # 키 형식 맞추기
    
    if db.career and 'modern_jobs' in db.career:
        # 키 매칭 시도 (정확한 키가 안 맞을 수 있으니 loop 검색)
        job_data = None
        for k, v in db.career['modern_jobs'].items():
            if mapping_mock.get(strongest).split('_')[0] in k:
                job_data = v
                break
        
        if job_data:
             report['analytics'].append({
                "type": "💼 신령의 천직 점지",
                "title": f"'{strongest}' 기운을 쓰는 직업",
                "content": f"**[적성]** {job_data.get('trait')}\n\n**[추천 직업]** {job_data.get('jobs')}\n\n📢 {job_data.get('shamanic_voice')}"
            })

    return report

# ==========================================
# 4. 궁합 분석 엔진 (Compatibility) [NEW]
# ==========================================
def analyze_compatibility(user_a, user_b):
    saju_a = get_ganji_dummy(user_a['year'], user_a['month'], user_a['day'], user_a['hour'])
    saju_b = get_ganji_dummy(user_b['year'], user_b['month'], user_b['day'], user_b['hour'])
    
    report = {
        "saju_a": saju_a,
        "saju_b": saju_b,
        "analytics": [],
        "chat_context": []
    }
    
    # [1] 일간(Day Stem) 조화 분석
    elem_a = saju_a['day_elem']
    elem_b = saju_b['day_elem']
    
    relation = _check_relation(elem_a, elem_b) # 생/극/비화
    
    # DB에서 멘트 가져오기 (love_db)
    compatibility_text = "자네들 사이엔 특별한 기록이 없구먼."
    if db.love and 'basic_compatibility' in db.love:
        matrix = db.love['basic_compatibility'].get('element_harmony', {})
        # 키 생성 (예: wood_fire)
        key_eng = f"{_get_eng(elem_a).lower()}_{_get_eng(elem_b).lower()}"
        key_eng_rev = f"{_get_eng(elem_b).lower()}_{_get_eng(elem_a).lower()}"
        
        if key_eng in matrix:
            compatibility_text = matrix[key_eng]
        elif key_eng_rev in matrix:
            compatibility_text = matrix[key_eng_rev]
        else:
            compatibility_text = f"서로 {elem_a}와 {elem_b}로 만났으니, {_get_relation_desc(relation)}"

    report['analytics'].append({
        "type": "💞 궁합 총평 (속궁합)",
        "title": f"{user_a['name']}({elem_a}) vs {user_b['name']}({elem_b})",
        "content": f"**[관계 정의]** {relation}\n\n📢 {compatibility_text}"
    })
    
    # [2] 갈등 트리거 (Conflict) - love_db 활용
    # 예시로 A나 B 중 한 명의 특징을 잡아 경고
    if db.love and 'conflict_triggers' in db.love:
        # 랜덤하게 하나의 경고를 가져오거나 조건에 맞춰 출력 (데모용 랜덤)
        triggers = list(db.love['conflict_triggers'].values())
        warning = random.choice(triggers)
        
        report['analytics'].append({
            "type": "⚡ 이별 주의보 (갈등 원인)",
            "title": "왜 자꾸 싸우는가?",
            "content": f"**[위험 요소]** {warning.get('fight_reason')}\n\n📢 {warning.get('shamanic_voice')}"
        })

    return report

# --- Helpers ---
def _get_eng(kor):
    m = {'목': 'Wood', '화': 'Fire', '토': 'Earth', '금': 'Metal', '수': 'Water'}
    return m.get(kor, '')

def _get_eng_job(kor): # career_db 키 매칭용
    m = {'목': 'Output', '화': 'Wealth', '토': 'Self', '금': 'Official', '수': 'Input'}
    return m.get(kor, 'Output')

def _check_relation(a, b):
    # 오행 상생상극 로직 (간단 버전)
    order = ['목', '화', '토', '금', '수']
    idx_a = order.index(a)
    idx_b = order.index(b)
    
    if idx_a == idx_b: return "비화 (친구 같은 사이)"
    if (idx_a + 1) % 5 == idx_b: return "상생 (A가 B를 돕는 관계)"
    if (idx_b + 1) % 5 == idx_a: return "상생 (B가 A를 돕는 관계)"
    return "상극 (서로 부딪히는 관계)"

def _get_relation_desc(rel):
    if "상생" in rel: return "서로가 서로에게 힘이 되어주는 귀한 인연이네."
    if "비화" in rel: return "친구처럼 투닥거리며 평생 함께할 수 있어."
    return "초반엔 불꽃이 튀지만 나중엔 서로 생채기를 낼 수 있으니 조심하게."
