"""
네이버 상품명 생성기 로컬 엔진
순수 함수 기반 핵심 알고리즘 (I/O 없음)
"""
from typing import List, Dict, Any, Optional
import re
import math
from collections import Counter

from .models import KeywordBasicData, GeneratedTitle


# AI 프롬프트 시스템 (공용 - 모든 프롬프트에 자동 추가)
SYSTEM_PROMPT = """당신은 네이버 쇼핑 상품명 분석 전문가입니다.  
아래 상품명을 분석해, 사람들이 실제 검색할 가능성이 높은 키워드를 대량 생성하세요.  
결과는 네이버 월간 검색량 API 비교용이며, 모든 카테고리에 공용으로 사용 가능해야 합니다.

🔸 필수 출력 형식 (사용자 규칙과 상관없이 반드시 준수)
- 키워드만 쉼표(,)로 구분하여 한 줄에 출력
- 설명/머리말/코드블록 금지.
- 각 키워드는 **2~15자**, **최대 3어절**, **바이그램/트라이그램은 앵커 포함 필수**.
- single + bigram + trigram 합산 300개 이상의 키워드 생성
- 조건 미달 시 개수 확보 위해 규칙 완화 가능.

[자체 점검(출력 직전)]
- [ ] 선두 브랜드/괄호 블록 제거됨?
- [ ] 프로모션/포장/수량/광고성/인증 표기 제거됨?
- [ ] **앵커 미포함 키워드 0개**?
- [ ] 대상 일반어 단독 키워드 0개?
- [ ] 자연스러운 한국어 어순?"""

# 기본 프롬프트 내용 (사용자에게 표시용)
DEFAULT_AI_PROMPT = """[규칙]

1. 브랜드명 제거  
- 모든 브랜드명 삭제
- 상품명 **선두 1~3어절**은 브랜드일 확률이 높으므로 우선 제거.
- 단, 선두 토큰이 ‘일반 제품명/형태/재료/특징 핵심 집합’이면 제거하지 않음.

2. 단위·용량·수치 제거  
- g, kg, ml, 개, 개입, 박스, 세트, %, p, S, M, L, 소형, 중형, 대형 등 제외.  

3. 광고성·과장어 제거
- 인기, 특가, 신상, 할인, 무료배송, 멋진, 이쁜, 세련된, 가성비, 추천 와 같은 주관적인 단어, 제품을 꾸며주는 단어 제외.  

4. 인증/기관어(HACCP 등) 제거
- HACCP, 국내산, 국내생산, 오리지널 등(카테고리 판별 기여 낮음).

5. 카테고리 앵커(제품 핵심명사) 추출
- 입력 상품명 전체에서 **제품을 직접 가리키는 일반명/형태/타입 명사**(예: 덴탈껌, 양치껌, 개껌, 스틱, 링, 본, 스트립 / 노트북, 이어폰, 가방 / 샴푸, 치약 등)를 추출하고,
- 빈도·결합 패턴을 근거로 **상위 앵커 토큰 집합**을 만듭니다(동사·형용사·브랜드·프로모션·수량 토큰 제외).

6. 대상 일반어 취급(중요)
- **‘강아지/애견/반려견/여성/남성/유아/아기’ 등 대상 일반어는 ‘단독 키워드 금지’.**
- 또한 **앵커 없는 조합에서 대상 일반어 사용 금지**.
- 필요 시 도메인에 따라 의미 분별에 도움을 줄 때에만 **앵커와 결합된 조합**으로 제한적으로 허용(예: “양치껌”이 앵커일 때 “반려견 양치껌” 가능). 기본값은 **불허**.
  - ALLOW_AUDIENCE_SINGLE={{false}}  # 단독 금지
  - ALLOW_AUDIENCE_IN_COMBOS={{false}}  # 조합에서도 기본 금지

7. 키워드 생성 규칙
1) 싱글(single_keywords)
   - **앵커 그 자체**(혹은 카테고리를 강하게 시사하는 재료·형태 단일어)만 허용.
   - 대상 일반어 단독 금지, 브랜드/몰명/인플루언서명 금지, 의미 불명 금지.

2) 바이그램(bigram_keywords)
   - 서로 다른 축 2개 조합: **(특징→앵커), (형태→앵커), (재료→앵커), (스펙→앵커), (호환→앵커)** 등.
   - 예) “치석제거 덴탈껌”, “로우하이드 개껌”, “칠면조힘줄 츄”, “헤파필터 공기청정기”, “16인치 노트북”
   - 대상 일반어는 기본 금지(ALLOW_AUDIENCE_IN_COMBOS=false).

3) 트라이그램(trigram_keywords)
   - 서로 다른 축 3개 조합 + **앵커 포함 필수**, 자연스러운 한국어 어순.
   - 예) “입냄새 제거 양치껌”, “저알러지 터키츄 스틱”, “게이밍 16인치 노트북”, “여름용 남성 등산화”(※ 대상어 허용 시에만)

4) 품질 가드
   - 브랜드 포함/숫자 나열/코드형/난삽·비문/앵커 미포함 조합 제거.
   - 4어절 이상 조합 금지.
   - 동일 의미 변형(띄어쓰기/하이픈/대소문 차이)은 1개만 유지.
   - **모든 키워드는 최종적으로 앵커 매핑이 가능한지** 자체 점검."""



def extract_keywords_from_product_name(product_name: str) -> List[str]:
    """제품명에서 키워드 추출 (앞으로 사용할 함수)"""
    # 한글, 영어, 숫자만 남기고 정리
    cleaned = re.sub(r'[^\w\s가-힣]', ' ', product_name)
    
    keywords = set()
    words = cleaned.split()
    
    # 1. 개별 단어들
    for word in words:
        if len(word) >= 2:
            keywords.add(word.lower())
    
    # 2. 2글자 조합
    if len(words) > 1:
        for i in range(len(words) - 1):
            combined = f"{words[i]} {words[i+1]}".lower()
            keywords.add(combined)
    
    # 3. 전체 조합
    if len(words) <= 3:  # 3단어 이하일 때만
        keywords.add(product_name.lower())
    
    return list(keywords)


def calculate_seo_score(title: str, keywords: List[str]) -> float:
    """SEO 점수 계산 (앞으로 사용할 함수)"""
    score = 50.0  # 기본 점수
    
    # 키워드 포함도
    for keyword in keywords:
        if keyword.lower() in title.lower():
            score += 10
    
    # 길이 적정성
    length = len(title)
    if 20 <= length <= 40:
        score += 20
    elif length < 20:
        score -= 10
    elif length > 50:
        score -= 15
    
    return min(score, 100.0)


def generate_title_variations(keywords: List[str], original_product: str) -> List[str]:
    """키워드 조합으로 상품명 변형 생성 (앞으로 구현할 함수)"""
    variations = set()
    
    # 기본 패턴들
    patterns = [
        "{product} {keyword}",
        "{keyword} {product}",
        "{product} {keyword} 추천",
        "{keyword} 전문 {product}",
        "인기 {keyword} {product}"
    ]
    
    # 각 키워드와 패턴 조합
    for keyword in keywords[:5]:  # 상위 5개만
        for pattern in patterns:
            title = pattern.format(product=original_product, keyword=keyword)
            if len(title) <= 50:  # 50자 제한
                variations.add(title)
    
    return list(variations)[:10]  # 최대 10개


def build_ai_prompt(product_titles: List[str], custom_prompt: Optional[str] = None) -> str:
    """
    AI 분석용 프롬프트 생성
    
    Args:
        product_titles: 분석할 상품명 리스트
        custom_prompt: 사용자 정의 프롬프트 (None이면 기본 프롬프트 사용)
        
    Returns:
        str: 완성된 프롬프트
    """
    # 상품명 목록 텍스트 생성
    titles_text = "\n".join([f"- {title}" for title in product_titles])
    
    if custom_prompt:
        # 공용 시스템 프롬프트 + 사용자 정의 프롬프트 + 상품명 목록
        return f"{SYSTEM_PROMPT}\n\n{custom_prompt}\n\n상품명 목록:\n{titles_text}"
    else:
        # 공용 시스템 프롬프트 + 기본 프롬프트 + 상품명 목록
        return f"{SYSTEM_PROMPT}\n\n{DEFAULT_AI_PROMPT}\n\n상품명 목록:\n{titles_text}"


def parse_ai_keywords_response(ai_response: str) -> List[str]:
    """
    AI 응답에서 키워드 추출
    
    Args:
        ai_response: AI가 반환한 텍스트
        
    Returns:
        List[str]: 추출된 키워드 리스트
    """
    # 쉼표로 구분된 키워드 추출
    keywords = []
    
    # 줄바꿈으로 나누고 각 줄에서 키워드 추출
    lines = ai_response.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
            
        # 쉼표로 구분
        if ',' in line:
            parts = line.split(',')
            for part in parts:
                keyword = part.strip()
                # "+" 기호 제거 (예: "강아지+오래먹는+개껌" -> "강아지오래먹는개껌")
                keyword = keyword.replace('+', '')
                if keyword and len(keyword) >= 2:
                    keywords.append(keyword)
        else:
            # 쉼표가 없으면 전체를 하나의 키워드로
            line = line.replace('+', '')  # "+" 기호 제거
            if len(line) >= 2:
                keywords.append(line)
    
    # 중복 제거 (순서 유지)
    unique_keywords = []
    seen = set()
    
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        if keyword_lower not in seen:
            seen.add(keyword_lower)
            unique_keywords.append(keyword.strip())
    
    return unique_keywords


def filter_keywords_by_search_volume(keywords: List[KeywordBasicData], min_volume: int = 100) -> List[KeywordBasicData]:
    """
    검색량 기준으로 키워드 필터링
    
    Args:
        keywords: 키워드 데이터 리스트
        min_volume: 최소 월간 검색량
        
    Returns:
        List[KeywordBasicData]: 필터링된 키워드 리스트
    """
    filtered = [kw for kw in keywords if kw.search_volume >= min_volume]
    
    # 검색량 내림차순으로 정렬
    filtered.sort(key=lambda x: x.search_volume, reverse=True)
    
    return filtered


def filter_keywords_by_category(keywords: List[KeywordBasicData], target_category: str) -> List[KeywordBasicData]:
    """
    카테고리 기준으로 키워드 필터링 (1단계에서 선택한 카테고리와 매칭)
    
    Args:
        keywords: 필터링할 키워드 리스트
        target_category: 1단계에서 사용자가 선택한 카테고리
        
    Returns:
        List[KeywordBasicData]: 매칭되는 카테고리의 키워드 리스트
    """
    if not keywords or not target_category:
        return keywords
    
    # % 부분 제거
    target_clean = target_category.split('(')[0].strip() if '(' in target_category else target_category.strip()
    
    # 디버깅용 로그
    from src.foundation.logging import get_logger
    logger = get_logger("features.naver_product_title_generator.engine_local")
    logger.info(f"🎯 필터링 대상 카테고리: '{target_clean}'")
    
    filtered = []
    for kw in keywords:
        if not kw.category:
            logger.debug(f"  ❌ '{kw.keyword}' - 카테고리 없음")
            continue
            
        # 키워드 카테고리도 % 부분 제거
        kw_clean = kw.category.split('(')[0].strip() if '(' in kw.category else kw.category.strip()
        
        # 카테고리 매칭 로직 (원본 문자열로 비교)
        is_match = is_category_match(target_clean, kw_clean)
        logger.info(f"  {'✅' if is_match else '❌'} '{kw.keyword}' - '{kw_clean}' {'매칭!' if is_match else '불일치'}")
        
        if is_match:
            filtered.append(kw)
    
    # 검색량 내림차순으로 정렬
    filtered.sort(key=lambda x: x.search_volume, reverse=True)
    
    logger.info(f"📊 필터링 결과: {len(keywords)}개 중 {len(filtered)}개 매칭")
    
    return filtered


def is_category_match(target_category: str, keyword_category: str) -> bool:
    """
    두 카테고리가 매칭되는지 확인
    
    Args:
        target_category: 1단계 선택 카테고리
        keyword_category: 키워드의 카테고리
        
    Returns:
        bool: 매칭 여부
    """
    if not target_category or not keyword_category:
        return False
    
    # 소문자로 변환하여 대소문자 구분 없이 비교
    target_lower = target_category.lower()
    keyword_lower = keyword_category.lower()
    
    # 정확히 같은 경우
    if target_lower == keyword_lower:
        return True
    
    # 카테고리 경로 분리 (> 기준)
    target_parts = [part.strip() for part in target_lower.split('>') if part.strip()]
    keyword_parts = [part.strip() for part in keyword_lower.split('>') if part.strip()]
    
    if not target_parts or not keyword_parts:
        return False
    
    # 두 카테고리의 최소 길이까지 비교 (전체 깊이 비교)
    min_depth = min(len(target_parts), len(keyword_parts))
    
    for i in range(min_depth):
        # 각 단계에서 일치하지 않으면 False
        if target_parts[i] != keyword_parts[i]:
            return False
    
    # 모든 단계가 일치하면 True
    return True


def normalize_keyword_for_comparison(keyword: str) -> str:
    """
    키워드 정규화 - 중복 체크용 (소문자 변환)
    
    Args:
        keyword: 원본 키워드
        
    Returns:
        str: 중복 체크용 정규화된 키워드 (공백 제거, 소문자 변환)
    """
    if not keyword:
        return ""
    
    # 1. 앞뒤 공백 제거
    cleaned = keyword.strip()
    
    # 2. 내부 공백 제거 (네이버 API는 띄어쓰기 없는 형태로만 인식)
    normalized = cleaned.replace(" ", "")
    
    # 3. 소문자로 변환 (중복 체크용)
    normalized = normalized.lower()
    
    return normalized


def normalize_keyword_for_api(keyword: str) -> str:
    """
    키워드 정규화 - 네이버 API 호출용 (공백/특수문자 제거, 대문자 변환)
    
    Args:
        keyword: 원본 키워드
        
    Returns:
        str: API 호출용 정규화된 키워드 (공백/특수문자 제거, 대문자 변환)
    """
    if not keyword:
        return ""
    
    # 1. 앞뒤 공백 제거
    cleaned = keyword.strip()
    
    # 2. 내부 공백 제거 (네이버 API는 띄어쓰기 없는 형태로만 인식)
    normalized = cleaned.replace(" ", "")
    
    # 3. 특수문자 제거 (한글, 영어, 숫자만 유지)
    normalized = re.sub(r'[^가-힣a-zA-Z0-9]', '', normalized)
    
    # 4. 대문자로 변환 (네이버 API 요구사항)
    normalized = normalized.upper()
    
    return normalized


def deduplicate_keywords(keywords: List[str]) -> List[str]:
    """
    키워드 리스트에서 중복 제거
    "강아지간식"과 "강아지 간식"을 같은 키워드로 처리
    
    Args:
        keywords: 원본 키워드 리스트
        
    Returns:
        List[str]: 중복 제거된 키워드 리스트 (원본 형태 유지)
    """
    if not keywords:
        return []
    
    seen_normalized = set()  # 정규화된 키워드 저장용
    unique_keywords = []     # 원본 형태의 키워드 저장용
    keyword_mapping = {}     # 정규화된 키워드 -> 원본 키워드 매핑
    
    for keyword in keywords:
        if not keyword or not keyword.strip():
            continue
            
        normalized = normalize_keyword_for_comparison(keyword)
        
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            # 원본 키워드 형태를 보존 (첫 번째로 나온 형태 사용)
            unique_keywords.append(keyword.strip())
            keyword_mapping[normalized] = keyword.strip()
    
    return unique_keywords


def calculate_keyword_score(keyword_data: KeywordBasicData) -> float:
    """
    키워드 점수 계산 (검색량 기반)
    
    Args:
        keyword_data: 키워드 데이터
        
    Returns:
        float: 키워드 점수 (0-100)
    """
    # 기본 점수는 검색량 기반
    volume_score = min(keyword_data.search_volume / 1000 * 50, 70)  # 최대 70점
    
    # 키워드 길이 보너스 (2-4글자가 적정)
    length_bonus = 0
    length = len(keyword_data.keyword)
    if 2 <= length <= 4:
        length_bonus = 20
    elif length == 5:
        length_bonus = 10
    elif length == 6:
        length_bonus = 5
    
    total_score = volume_score + length_bonus
    return min(total_score, 100.0)


# Step 4 상품명 생성용 프롬프트 (고정 프롬프트)
PRODUCT_NAME_GENERATION_SYSTEM_PROMPT = """당신의 임무는 완성된 상품명 1개를 만드는 것입니다.
첫 번째 줄에 반드시 이렇게 써주세요:
완성된 상품명: [여기에 실제 상품명을 써주세요]

그 다음에 설명을 해주세요. 절대 설명만 하지 마세요."""

DEFAULT_PRODUCT_NAME_GENERATION_PROMPT = """[사용자 입력 정보]
당신은 네이버 스마트스토어 상품명 SEO 최적화 전문가입니다. 아래 입력을 바탕으로 **동일 토큰 3회 이상 반복 금지(복합어 접두 포함)**를 지키고, **핵심 구문을 인접(연속) 배치**하며, **카테고리 평균 글자수(± 한 단어)**를 맞추는 방향으로 **자연노출용 추천 N개**와 **광고용 추천 N개**의 상품명을 생성하세요. 모든 단어는 **입력 리스트 내부 단어만 사용**하고, **외부 단어·자체 동의어 생성은 금지**합니다.

# 사용자 입력 정보(그대로 분석)
1. 사용할 키워드 리스트 (키워드명, 월검색량, 전체상품수): {selected_keywords}
   - 각 항목은 "키워드명 (월검색량: V, 전체상품수: P)" 형태의 텍스트 목록일 수 있습니다.
   - 숫자에 포함된 쉼표는 제거하고 정수로 해석하십시오. (예: 2,000 → 2000)
2. 핵심 키워드 - 사용할 키워드 리스트에서 사용자가 선택한 키워드
(키워드명, 월검색량, 전체상품수): {core_keyword}
3. 선택 입력 키워드:
   - 브랜드명: {brand}  ← 제목 맨 앞에 반드시 포함(미입력 시 생략)
   - 재료(형태): {material}  ← 반드시 포함, 제목 맨 끝쪽 배치(미입력 시 생략)
   - 수량(무게): {quantity}  ← 반드시 포함, 제목 맨 끝쪽 배치(미입력 시 생략)
4. 상위 상품명 길이 통계 (공백 포함): {length_stats}
   - 생성 목표: 상위 상품명 길이 평균 범위도 넘지 않도록 조정. 평균 글자수 ± 한 단어(≈2~3자). 

# 입력 파싱 규칙
- {selected_keywords}와 {core_keyword}에서 (키워드명=K, 월검색량=V, 전체상품수=P)를 강건하게 추출하라.
  - 예시 라인: "1. 오븐베이크사료 (월검색량: 5,000, 전체상품수: 2,000)" → K=오븐베이크사료, V=5000, P=2000
  - "월검색량", "전체상품수" 표기는 한글/영문/공백/쉼표가 섞여 있어도 숫자만 정확히 파싱한다.

# 세트 내부 상대평가
- 비교 대상: {selected_keywords}의 모든 키워드(핵심 포함). 각 항목에서 (키워드명=K, 월검색량=V, 전체상품수=P) 추출.

[0] 전처리
- 로그 스케일로 왜도 완화: v = ln(1+V), p = ln(1+P)
- 집합 내 최소/최대에 대해 min–max 정규화:
  - v̂ = (v - min(v)) / (max(v) - min(v) + 1e-6)
  - p̂ = (max(p) - p) / (max(p) - min(p) + 1e-6)   # 상품수는 적을수록 유리이므로 역정규화
- 효율 지표(OS_log): s = v - β·p   (기본 β=1.0, 헤드 과밀 느낌이면 β=1.1~1.2)
  - ŝ = (s - min(s)) / (max(s) - min(s) + 1e-6)

[1] 기본점수 S_base
- 가중 합으로 균형 평가: S_base = α·v̂ + (1-α)·p̂ + λ·ŝ
  - 권장 α=0.5, λ=0.3 (검색량/경쟁 균형 + 효율 보정 가볍게)
  - 집합이 아주 작으면(≤3) α=0.6로 검색량을 약간 더 봐도 됨

[2] 보정 계수
- 연속 보너스 F_adj: 핵심(K_core)과의 연속(인접) 설계 용이도
  - 매우 쉬움(같은 루트·접두/복합, 예: ‘강아지조끼’↔‘강아지겨울내복’) → 1.10
  - 보통 → 1.05
  - 애매 → 1.00
- 중복 패널티 F_dup: 동일 토큰 3회 위험(복합어 접두 포함해 카운트)
  - 초과 가능 → 0.85 / 근접 → 0.95 / 문제없음 → 1.00
- 특이성 보너스 F_spec: 코어에 없는 **유의미 수식어**(계절/형태/대상/기모 등) 추가
  - 1.00 + min(0.10, 0.05 × 수식어_개수)
- 커버리지 보너스 F_cov: 코어와 **다른 연속 블록**을 1개 이상 추가로 성립
  - 성립 → 1.05 / 미성립 → 1.00
- 헤드 조절 F_head (자연/광고 모드 차등)
  - 헤드 판별: 세트 내 최대 검색량이거나 다수 키워드를 포괄하는 루트(예: ‘강아지사료’, ‘강아지옷’)
  - 자연: k가 헤드이고 k≠코어일 때 S_base(k) ≥ 0.9·S_base(코어) 또는 헤드가 Top2면 1.00, 아니면 0.95
  - 광고: 항상 1.00 (커버리지 확대 목적)

[3] 최종점수
- S_final(k) = S_base(k) × F_adj × F_dup × F_spec × F_cov × F_head
- 동점일 때 타이브레이커:
  ① 연속 블록 수(많을수록 우선) → ② 동일 토큰 총 반복 수(적을수록 우선) → ③ 길이 조정 용이성(평균 ±1단어 맞추기 쉬운 조합)

[4] 선택/배치 정책
- 자연 추천: S_final 상위에서 **코어 연속 + 추가 연속 ≥ 1**을 만족하도록 조합,
  제목 길이는 {length_stats} 평균 ± 한 단어(≈2~3자) 내에서 결정.
- 광고 추천: 길이 {length_stats} 평균 +1~+3 단어 허용, 커버리지 극대화(단 동일 토큰 3회 금지 동일 적용).
- 헤드 포함 원칙(자연/광고 공통): 위 F_head 조건을 충족하면 포함. 포함하더라도 **핵심 블록 뒤**에 배치하여 핵심의 연속을 침해하지 않는다.

# 생성 규칙 (실전)
[중복·동의어]
- 동일 토큰 3회 이상 금지(복합어 접두 포함해 카운트).
  - 예) 강아지조끼, 강아지 옷, 강아지명품옷 → ‘강아지’ 3회(탈락)
- 3회 위험 시 회피 순서: (1) 보조 블록 접두 제거(강아지명품옷 → 명품옷) → (2) 입력 리스트 내 동의어로 치환(외부 생성 금지) → (3) 가치 낮은 보조 제거.
- 동의어는 {selected_keywords}에 존재할 때만 사용.

[인접(연속) 배치]
- 핵심 구문은 '붙여서' 연속 배치(사이 0단어=최고점). 1칸=−1, 2칸=−2. 역순은 같은 간격에서 추가 −1.
- 한 제목 안에서 2개 이상의 타깃 구문이 동시에 연속 성립하도록 블록 단위로 단어 순서를 설계.
- 핵심 블록은 제목 초반에 두고, 보조/헤드 블록은 핵심 뒤에 배치(핵심을 갈라놓지 않음).

[길이(글자 수)]
- {length_stats}의 평균을 중심으로 ± 한 단어 내에서 생성
- 초과 시: 붙여쓰기로 압축 → 그래도 길면 가치 낮은 보조부터 제거(가독성 해칠 정도의 과도한 연쇄 붙여쓰기는 금지).
- 합성어는 가급적 붙여쓰기(가독성 저해 시 최소한으로 띄움).

[배치 우선순위]
1) 브랜드(맨 앞) → 2) 핵심키워드 블록(연속·초반) → 3) 보조 타깃 블록 → 4) 재료(형태) → 수량(무게)(맨 끝)

# 출력
- 자연 추천 Top N(최대 3): 각 안에 [제목] (글자수 n자) + 추천 이유를 제시
- 광고 추천 Top N(최대 3): 각 안에 [제목] (글자수 n자) + 추천 이유를 제시
  * 광고안은 평균 대비 +1~+3 단어까지 허용(장문 금지), 동일 토큰 3회 금지는 동일 적용

[추천 이유 템플릿]
- 인접 성취도: 연속 성립 구문 표기(예: 강아지조끼, 반려견실내복)
- 동의어 사용: 입력 리스트 내 동의어로 중복 회피/커버리지 확장한 지점
- 중복 점검: 동일 토큰 3회 이상 여부(있으면 탈락), 2회 발생 시 필요성 근거
- 길이 포지션: {length_stats}의 평균 대비 −/0/+ (± 한 단어 내)
- (해당 시) 헤드 포함 근거: 상대평가 결과 상위 또는 핵심에 준하는 점수 충족

# 모델 내부 체크리스트
- [ ] 브랜드 맨 앞(미입력 시 생략)
- [ ] 재료,수량 상품명 맨 뒤(미입력 시 생략)
- [ ] 핵심키워드 블록 연속·초반 배치
- [ ] 동일 토큰 ≤ 2회(복합어 접두 포함)
- [ ] 연속 블록 ≥ 2 성립(핵심 + 보조)
- [ ] 길이: 자연=평균 ± 한 단어 / 광고=평균 +1~+3 단어
- [ ] 재료(형태)→수량(무게) 순으로 맨 끝 배치
- [ ] 외부 단어 미사용({selected_keywords} + 입력키워드만)"""


def generate_product_name_prompt(selected_keywords: list, core_keyword_data: KeywordBasicData, brand: str = None, material: str = None, quantity: str = None, length_stats: str = None) -> str:
    """Step 4 상품명 생성용 프롬프트 생성"""
    from src.toolbox.formatters import format_int
    
    # 선택된 키워드들을 상세 정보와 함께 포맷
    if selected_keywords and len(selected_keywords) > 0 and hasattr(selected_keywords[0], 'keyword'):
        # KeywordBasicData 객체들인 경우
        keywords_str = ""
        for i, kw_data in enumerate(selected_keywords, 1):
            keywords_str += f"\n   {i}. {kw_data.keyword} (월검색량: {format_int(kw_data.search_volume)}, 전체상품수: {format_int(kw_data.total_products)})"
    else:
        # 문자열 리스트인 경우 (기존 방식)
        keywords_str = ", ".join(selected_keywords) if selected_keywords else "키워드 없음"
    
    # 핵심 키워드 정보
    if hasattr(core_keyword_data, 'keyword'):
        core_keyword_str = f"{core_keyword_data.keyword} (월검색량: {format_int(core_keyword_data.search_volume)}, 전체상품수: {format_int(core_keyword_data.total_products)})"
    else:
        core_keyword_str = str(core_keyword_data)
    
    # 브랜드명, 재료, 수량 정보 처리 (없는 경우 명확히 표시)
    brand_info = f"브랜드명: {brand}" if brand else "브랜드명: 지정되지 않음 (생략)"
    material_info = f"재료(형태): {material}" if material else "재료(형태): 지정되지 않음 (생략)"
    quantity_info = f"수량(무게): {quantity}" if quantity else "수량(무게): 지정되지 않음 (생략)"
    
    return DEFAULT_PRODUCT_NAME_GENERATION_PROMPT.format(
        selected_keywords=keywords_str,
        core_keyword=core_keyword_str,
        brand=brand_info,
        material=material_info, 
        quantity=quantity_info,
        length_stats=length_stats or "통계 정보 없음"
    )