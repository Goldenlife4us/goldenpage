# ============================================================
# SEO 규칙 검증기 (Phase 1 - API 불필요, 즉시 사용 가능)
#
# 네이버 스마트스토어 / 쿠팡 / 11번가 상품명 규칙을
# 자동으로 체크하여 위반 항목을 알려줍니다.
#
# 참고: school.itemscout.io, trendhunterclass.com 규칙 기반
# ============================================================

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """SEO 검증 결과를 담는 데이터 클래스"""
    channel: str
    product_name: str
    is_valid: bool = True
    errors: list = field(default_factory=list)    # 반드시 고쳐야 하는 위반
    warnings: list = field(default_factory=list)  # 권장 수정 사항
    score: int = 100  # SEO 점수 (100점 만점)

    def __str__(self):
        lines = [f"[{self.channel}] '{self.product_name}'  →  SEO 점수: {self.score}/100"]
        if self.errors:
            for e in self.errors:
                lines.append(f"  ❌ {e}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠  {w}")
        if self.is_valid and not self.warnings:
            lines.append("  ✅ 이상 없음")
        return "\n".join(lines)


# ── 스마트스토어 규칙 ──────────────────────────────────────

# 허용되는 특수문자만 정의 (이 외 문자가 있으면 경고)
SMARTSTORE_ALLOWED_SPECIAL = set("() -·[]/&+,~.")

# 금지 패턴: 이벤트/할인 문구
SMARTSTORE_BANNED_PROMO_WORDS = [
    "무료배송", "할인", "쿠폰", "적립", "증정", "이벤트",
    "특가", "세일", "sale", "SALE", "% off", "%off",
    "buy", "BUY", "빠른배송", "당일출고", "오늘출발",
]

# 금지 패턴: 반복 단어 (같은 단어 3회 이상)
def _check_repeated_words(name: str) -> list:
    """상품명에서 3회 이상 반복된 단어를 찾습니다."""
    words = re.findall(r'[가-힣a-zA-Z0-9]+', name)
    from collections import Counter
    counts = Counter(words)
    return [word for word, cnt in counts.items() if cnt >= 3 and len(word) >= 2]


def validate_smartstore(product_name: str) -> ValidationResult:
    """스마트스토어 상품명 SEO 규칙을 검증합니다."""
    result = ValidationResult(channel="스마트스토어", product_name=product_name)

    # 1. 글자수 체크 (너무 짧거나 긴 경우)
    if len(product_name) < 10:
        result.warnings.append(f"상품명이 너무 짧습니다 ({len(product_name)}자). 15자 이상 권장.")
        result.score -= 10
    if len(product_name) > 100:
        result.errors.append(f"상품명이 너무 깁니다 ({len(product_name)}자). 100자 이하로 줄이세요.")
        result.is_valid = False
        result.score -= 20

    # 2. 허용되지 않는 특수문자 체크
    illegal_chars = []
    for ch in product_name:
        if not (ch.isalnum() or '가' <= ch <= '힣' or ch == ' '):
            if ch not in SMARTSTORE_ALLOWED_SPECIAL:
                illegal_chars.append(ch)
    if illegal_chars:
        result.errors.append(f"허용되지 않는 특수문자: {set(illegal_chars)}")
        result.is_valid = False
        result.score -= 15

    # 3. 프로모션 문구 금지
    for word in SMARTSTORE_BANNED_PROMO_WORDS:
        if word in product_name:
            result.errors.append(f"금지 프로모션 문구 포함: '{word}'")
            result.is_valid = False
            result.score -= 15
            break

    # 4. 단어 반복 체크 (3회 이상)
    repeated = _check_repeated_words(product_name)
    if repeated:
        result.warnings.append(f"단어 반복 주의 (3회↑): {repeated} → 페널티 위험")
        result.score -= 10

    # 5. 한글 포함 여부 (한국 상품은 한글 포함 권장)
    korean_chars = re.findall(r'[가-힣]', product_name)
    if len(korean_chars) < 3:
        result.warnings.append("한글이 너무 적습니다. 주요 키워드는 한글로 입력하세요.")
        result.score -= 5

    # 6. 상품명에 브랜드가 앞에 오는지 체크 (권장)
    result.score = max(0, result.score)
    return result


# ── 쿠팡 규칙 ────────────────────────────────────────────

# 쿠팡 2025: 핵심 키워드는 앞 40자 안에, 전체 80자 이내
COUPANG_MAX_LENGTH = 80
COUPANG_KEYWORD_ZONE = 40  # 핵심 키워드가 들어와야 할 앞부분 길이

COUPANG_BANNED_CHARS = ['★', '☆', '♥', '♡', '▶', '◀', '■', '□', '●', '○', '◎']


def validate_coupang(product_name: str) -> ValidationResult:
    """쿠팡 상품명 SEO 규칙을 검증합니다."""
    result = ValidationResult(channel="쿠팡", product_name=product_name)

    # 1. 80자 제한
    if len(product_name) > COUPANG_MAX_LENGTH:
        result.errors.append(
            f"80자 초과 ({len(product_name)}자). {len(product_name) - COUPANG_MAX_LENGTH}자 줄이세요."
        )
        result.is_valid = False
        result.score -= 25

    # 2. 특수문자 남용 체크
    for ch in COUPANG_BANNED_CHARS:
        if ch in product_name:
            result.errors.append(f"쿠팡 금지 특수문자: '{ch}'")
            result.is_valid = False
            result.score -= 10

    # 3. 앞 40자 키워드 배치 체크
    front_40 = product_name[:COUPANG_KEYWORD_ZONE]
    korean_in_front = re.findall(r'[가-힣]+', front_40)
    if not korean_in_front:
        result.warnings.append(f"앞 {COUPANG_KEYWORD_ZONE}자 안에 한글 키워드가 없습니다. 핵심 키워드를 앞으로 이동하세요.")
        result.score -= 15

    # 4. 프로모션 문구 (쿠팡은 상품명에 넣는 경우 있지만 권장하지 않음)
    for word in ["100% 정품", "정품보장", "AS보장"]:
        if word in product_name:
            result.warnings.append(f"'{word}' - 쿠팡 자체 인증 문구는 상품명보다 속성에 입력하세요.")
            result.score -= 5

    result.score = max(0, result.score)
    return result


# ── 11번가 규칙 ──────────────────────────────────────────

def validate_eleventh(product_name: str) -> ValidationResult:
    """11번가 상품명 SEO 규칙을 검증합니다."""
    result = ValidationResult(channel="11번가", product_name=product_name)

    # 1. 글자수 체크
    if len(product_name) > 100:
        result.errors.append(f"상품명 100자 초과 ({len(product_name)}자).")
        result.is_valid = False
        result.score -= 20

    # 2. 허위/과장 표현
    exaggerated = ["세계최고", "1등", "최고의", "최상의", "완벽한", "무조건"]
    for word in exaggerated:
        if word in product_name:
            result.warnings.append(f"과장 표현 주의: '{word}' - 심사 반려 가능성 있음")
            result.score -= 10

    # 3. 특수문자 남용
    special_count = len(re.findall(r'[^\w\s가-힣]', product_name))
    if special_count > 5:
        result.warnings.append(f"특수문자 {special_count}개 - 3개 이하 권장")
        result.score -= 10

    result.score = max(0, result.score)
    return result


# ── 통합 검증 함수 ────────────────────────────────────────

def validate_all_channels(product_name: str, channels: list = None) -> list:
    """
    상품명을 모든 채널 규칙에 대해 한번에 검증합니다.

    사용 예:
        results = validate_all_channels("프리미엄 스테인리스 텀블러 500ml 보온보냉")
        for r in results:
            print(r)
    """
    if channels is None:
        channels = ["smartstore", "coupang", "11st"]

    validators = {
        "smartstore": validate_smartstore,
        "coupang":    validate_coupang,
        "11st":       validate_eleventh,
    }

    results = []
    for ch in channels:
        if ch in validators:
            results.append(validators[ch](product_name))
    return results


def validate_dataframe(df, name_column: str = "상품명"):
    """
    DataFrame의 상품명 컬럼 전체를 일괄 검증합니다.

    Returns:
        검증 결과 요약 DataFrame
    """
    import pandas as pd
    rows = []
    for _, row in df.iterrows():
        name = str(row.get(name_column, ""))
        for result in validate_all_channels(name):
            rows.append({
                "상품명":    name,
                "채널":      result.channel,
                "통과여부":  "✅" if result.is_valid else "❌",
                "SEO점수":   result.score,
                "오류":      " | ".join(result.errors) if result.errors else "",
                "경고":      " | ".join(result.warnings) if result.warnings else "",
            })
    return pd.DataFrame(rows)


# ── 직접 실행 테스트 ─────────────────────────────────────

if __name__ == "__main__":
    test_names = [
        "프리미엄 스테인리스 텀블러 500ml 보온보냉",                    # 정상
        "무료배송!! 텀블러 텀블러 텀블러 최고의 텀블러 ★특가★",          # 다중 위반
        "텀블러",                                                     # 너무 짧음
        "TUMBLER STAINLESS STEEL 500ML VACUUM INSULATED BOTTLE",     # 한글 없음
        "[당일출고] 스테인리스 보온텀블러 500ml 직장인 차량용 보냉보온",   # 쿠팡 스타일
    ]

    print("=" * 60)
    print("  SEO 상품명 검증기 테스트")
    print("=" * 60)

    for name in test_names:
        print(f"\n▶ 테스트: {name}")
        print("-" * 50)
        for result in validate_all_channels(name):
            print(result)
