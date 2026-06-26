# ============================================================
# AI SEO 최적화 엔진 (Phase 2 - Claude API 필요)
#
# Claude API를 사용해 상품 정보를 입력받아
# 채널별 최적화된 상품명, 태그, 상품 설명을 자동 생성합니다.
#
# API 발급: https://console.anthropic.com → API Keys
# 참고: 모델 claude-sonnet-4-6 (2026년 6월 기준 최신)
# ============================================================

import os
import json
from typing import Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# 채널별 SEO 규칙 요약 (프롬프트에 주입)
CHANNEL_SEO_RULES = {
    "smartstore": """
- 총 길이: 15~100자
- 허용 특수문자: ( ) - · [ ] / & + , ~ . 만 사용
- 금지: 셀러명, 쇼핑몰명, 할인/쿠폰 문구, 무료배송 등 프로모션 문구
- 금지: 같은 단어 3회 이상 반복
- 구조 권장: [브랜드] [상품명] [주요속성] [용량/사이즈]
- 인기도 영향: 클릭수(7일), 판매량(30일), 리뷰수
""",
    "coupang": """
- 총 길이: 80자 이하 (필수)
- 핵심 키워드는 앞 40자 안에 배치
- 3~5개 핵심 키워드를 자연스럽게 포함
- 썸네일: 흰 배경 필수 (2025년부터)
- 구조 권장: [핵심키워드] [상품명] [주요특성] [수량/사이즈]
""",
    "11st": """
- 총 길이: 100자 이하
- 브랜드 + 상품명 + 주요 특성 포함
- 과장 표현 금지 (세계최고, 1등 등)
- 검색 키워드 자연스럽게 포함
""",
}


class SEOOptimizer:
    """
    Claude AI를 활용한 채널별 SEO 최적화 엔진

    설정 방법:
    - 환경변수: export ANTHROPIC_API_KEY="your_key"
    - config/settings.py에 입력
    """

    MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 1024

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._api_configured = bool(self.api_key) and HAS_ANTHROPIC

        if self._api_configured:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def optimize_product_name(
        self,
        base_name: str,
        category: str,
        features: list,
        channel: str,
        brand: str = "",
    ) -> str:
        """
        상품 기본 정보를 바탕으로 채널 최적화된 상품명을 생성합니다.

        Args:
            base_name: 기본 상품명
            category:  카테고리
            features:  주요 특성 목록 (예: ["500ml", "보온12시간", "스테인리스"])
            channel:   대상 채널 ("smartstore", "coupang", "11st")
            brand:     브랜드명

        Returns:
            SEO 최적화된 상품명
        """
        if not self._api_configured:
            return self._rule_based_optimization(base_name, features, channel, brand)

        rules = CHANNEL_SEO_RULES.get(channel, "")
        features_str = ", ".join(features)

        prompt = f"""당신은 한국 오픈마켓 SEO 전문가입니다.
아래 상품 정보를 바탕으로 {channel} 채널에 최적화된 상품명을 1개만 생성하세요.

상품 정보:
- 기본 상품명: {base_name}
- 카테고리: {category}
- 브랜드: {brand or '없음'}
- 주요 특성: {features_str}

{channel} 채널 SEO 규칙:
{rules}

요구사항:
- 규칙을 엄격히 준수하세요
- 검색량이 많을 만한 키워드를 자연스럽게 포함하세요
- 상품명만 출력하세요 (설명이나 이유 없이)
"""

        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except Exception as e:
            print(f"[경고] AI 상품명 생성 실패: {e}. 규칙 기반으로 대체합니다.")
            return self._rule_based_optimization(base_name, features, channel, brand)

    def generate_tags(self, product_name: str, category: str, features: list) -> list:
        """
        상품 정보를 바탕으로 검색 태그를 생성합니다.

        Returns:
            태그 목록 (10~15개)
        """
        if not self._api_configured:
            return self._rule_based_tags(product_name, features)

        prompt = f"""한국 오픈마켓(네이버 쇼핑) 검색 최적화를 위한 태그를 생성하세요.

상품명: {product_name}
카테고리: {category}
주요 특성: {', '.join(features)}

요구사항:
- 10~15개의 태그를 쉼표로 구분하여 출력
- 검색량이 많은 키워드 우선
- 상품과 직접 관련된 키워드만 포함
- 태그만 출력 (설명 없이)

예시 형식: 텀블러,보온텀블러,스테인리스텀블러,보온보냉,직장인텀블러,...
"""

        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            tags_str = message.content[0].text.strip()
            return [t.strip() for t in tags_str.split(",") if t.strip()][:15]
        except Exception as e:
            print(f"[경고] AI 태그 생성 실패: {e}")
            return self._rule_based_tags(product_name, features)

    def _rule_based_optimization(
        self, base_name: str, features: list, channel: str, brand: str
    ) -> str:
        """API 없을 때 규칙 기반으로 상품명을 조합합니다."""
        parts = []
        if brand:
            parts.append(brand)
        parts.append(base_name)
        for f in features[:2]:  # 주요 특성 최대 2개
            if f not in base_name:
                parts.append(f)

        result = " ".join(parts)

        # 쿠팡: 80자 제한
        if channel == "coupang" and len(result) > 80:
            result = result[:77] + "..."

        return result

    def _rule_based_tags(self, product_name: str, features: list) -> list:
        """API 없을 때 규칙 기반으로 태그를 생성합니다."""
        import re
        # 상품명에서 단어 추출
        words = re.findall(r'[가-힣a-zA-Z0-9]+', product_name)
        tags = list(dict.fromkeys(words + features))  # 중복 제거
        return tags[:15]

    def batch_optimize(self, products: list, channels: list = None) -> list:
        """
        여러 상품을 일괄 최적화합니다.

        Args:
            products: {"name", "category", "features", "brand"} 딕셔너리 목록
            channels: 최적화할 채널 목록

        Returns:
            최적화된 상품 목록
        """
        if channels is None:
            channels = ["smartstore", "coupang", "11st"]

        optimized = []
        for product in products:
            result = dict(product)
            for channel in channels:
                key = f"{channel}_상품명"
                result[key] = self.optimize_product_name(
                    base_name=product.get("name", ""),
                    category=product.get("category", ""),
                    features=product.get("features", []),
                    channel=channel,
                    brand=product.get("brand", ""),
                )
            tags = self.generate_tags(
                product_name=product.get("name", ""),
                category=product.get("category", ""),
                features=product.get("features", []),
            )
            result["tags"] = ",".join(tags)
            optimized.append(result)
        return optimized


# ── 직접 실행 테스트 ─────────────────────────────────────

if __name__ == "__main__":
    optimizer = SEOOptimizer()

    test_products = [
        {
            "name":     "스테인리스 텀블러",
            "category": "주방용품",
            "brand":    "골든라이프",
            "features": ["500ml", "보온12시간", "보냉24시간", "차량용"],
        },
        {
            "name":     "천연 대나무 도마",
            "category": "주방용품",
            "brand":    "",
            "features": ["대형", "40x25cm", "항균", "친환경"],
        },
    ]

    print("=" * 60)
    print("  AI SEO 상품명 최적화 테스트")
    print(f"  (API {'설정됨' if optimizer._api_configured else '미설정 → 규칙 기반 대체'})")
    print("=" * 60)

    for product in test_products:
        print(f"\n원본: {product['name']}")
        for ch in ["smartstore", "coupang", "11st"]:
            optimized = optimizer.optimize_product_name(
                base_name=product["name"],
                category=product["category"],
                features=product["features"],
                channel=ch,
                brand=product.get("brand", ""),
            )
            print(f"  [{ch}] {optimized}")

        tags = optimizer.generate_tags(
            product_name=product["name"],
            category=product["category"],
            features=product["features"],
        )
        print(f"  [태그] {', '.join(tags[:8])} ...")
