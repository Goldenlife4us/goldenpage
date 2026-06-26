# ============================================================
# 키워드 수요 조사 모듈 (Phase 2 - 네이버 검색광고 API 필요)
#
# 네이버 검색광고 API로 키워드 검색량/경쟁강도를 조회하고
# "황금키워드" (검색량 많고 경쟁 적은 키워드)를 찾습니다.
#
# API 발급: https://searchad.naver.com → 도구 → API 관리
# 참고 오픈소스: github.com/kyungdongseo/naver_search_ad
#               github.com/taegyumin/python_nevada
# ============================================================

import os
import time
import hashlib
import hmac
import base64
import json
import math
from dataclasses import dataclass
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class KeywordData:
    """키워드 분석 결과"""
    keyword: str
    monthly_pc_search: int      # PC 월간 검색수
    monthly_mobile_search: int  # 모바일 월간 검색수
    total_search: int           # 총 검색수
    pc_click_count: int         # PC 클릭수
    mobile_click_count: int     # 모바일 클릭수
    competition: str            # 경쟁강도: 높음/중간/낮음
    product_count: int          # 쇼핑 상품수 (추정)
    golden_index: float         # 황금지수 = 검색량 / sqrt(상품수)
    recommendation: str         # 소싱 추천 여부

    def __str__(self):
        return (
            f"키워드: {self.keyword}\n"
            f"  월간 검색수: {self.total_search:,}회 (PC {self.monthly_pc_search:,} + 모바일 {self.monthly_mobile_search:,})\n"
            f"  경쟁강도: {self.competition}\n"
            f"  황금지수: {self.golden_index:.2f}\n"
            f"  소싱 추천: {self.recommendation}"
        )


class NaverKeywordResearcher:
    """
    네이버 검색광고 API를 이용한 키워드 분석기

    API 발급 방법:
    1. https://searchad.naver.com 로그인
    2. 상단 메뉴 → 도구 → API 관리
    3. API 이용 신청 클릭
    4. customer_id, access_license, secret_key 복사

    설정 방법:
    - config/settings.py에 키 입력 OR
    - 환경변수로 설정: NAVER_AD_CUSTOMER_ID, NAVER_AD_ACCESS_LICENSE, NAVER_AD_SECRET_KEY
    """

    BASE_URL = "https://api.searchad.naver.com"

    def __init__(
        self,
        customer_id: str = None,
        access_license: str = None,
        secret_key: str = None,
    ):
        # 환경변수 또는 직접 입력에서 API 키 로드
        self.customer_id = customer_id or os.getenv("NAVER_AD_CUSTOMER_ID", "")
        self.access_license = access_license or os.getenv("NAVER_AD_ACCESS_LICENSE", "")
        self.secret_key = secret_key or os.getenv("NAVER_AD_SECRET_KEY", "")

        self._api_configured = all([self.customer_id, self.access_license, self.secret_key])

    def _generate_signature(self, timestamp: str, method: str, path: str) -> str:
        """API 요청에 필요한 HMAC 서명을 생성합니다."""
        message = f"{timestamp}.{method}.{path}"
        hash_bytes = hmac.new(
            self.secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(hash_bytes).decode("utf-8")

    def _get_headers(self, method: str, path: str) -> dict:
        """API 요청 헤더를 생성합니다."""
        timestamp = str(int(time.time() * 1000))
        return {
            "Content-Type":    "application/json;charset=UTF-8",
            "X-Timestamp":     timestamp,
            "X-API-KEY":       self.access_license,
            "X-Customer":      str(self.customer_id),
            "X-Signature":     self._generate_signature(timestamp, method, path),
        }

    def get_keyword_stats(self, keywords: list) -> list:
        """
        키워드 목록의 검색량을 조회합니다.

        Args:
            keywords: 조회할 키워드 목록 (최대 5개씩 나누어 조회)

        Returns:
            KeywordData 객체 목록
        """
        if not self._api_configured:
            print("[경고] 네이버 검색광고 API 키가 설정되지 않았습니다.")
            print("  → config/settings.py에 API 키를 입력하거나")
            print("  → 환경변수를 설정하세요 (README.md 참고)")
            return self._get_demo_data(keywords)

        if not HAS_REQUESTS:
            raise ImportError("pip install requests 를 실행하세요")

        path = "/keywordstool"
        results = []

        # 5개씩 나누어 조회 (API 제한)
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i+5]
            params = {"hintKeywords": ",".join(batch), "showDetail": "1"}

            headers = self._get_headers("GET", path)
            resp = requests.get(
                self.BASE_URL + path,
                headers=headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("keywordList", []):
                kw_data = self._parse_keyword_item(item)
                results.append(kw_data)

            time.sleep(0.3)  # API 호출 간격

        return results

    def _parse_keyword_item(self, item: dict) -> KeywordData:
        """API 응답 항목을 KeywordData로 변환합니다."""
        keyword = item.get("relKeyword", "")
        pc_search = int(item.get("monthlyPcQcCnt", "0").replace("<", "").strip() or 0)
        mobile_search = int(item.get("monthlyMobileQcCnt", "0").replace("<", "").strip() or 0)
        total_search = pc_search + mobile_search

        pc_clicks = item.get("monthlyAvePcClkCnt", 0)
        mobile_clicks = item.get("monthlyAveMobileClkCnt", 0)

        # 경쟁강도: 높음/중간/낮음
        competition_map = {"높음": "높음", "중간": "중간", "낮음": "낮음"}
        competition = competition_map.get(item.get("compIdx", ""), "알수없음")

        # 상품 수 추정 (API에서 직접 제공하지 않으므로 클릭률로 역산)
        # 실제 상품수는 네이버 쇼핑에서 직접 조회 필요
        estimated_products = max(total_search * 2, 1)

        golden_index = total_search / math.sqrt(estimated_products)

        recommendation = self._get_recommendation(golden_index, competition, total_search)

        return KeywordData(
            keyword=keyword,
            monthly_pc_search=pc_search,
            monthly_mobile_search=mobile_search,
            total_search=total_search,
            pc_click_count=pc_clicks,
            mobile_click_count=mobile_clicks,
            competition=competition,
            product_count=estimated_products,
            golden_index=round(golden_index, 2),
            recommendation=recommendation,
        )

    def _get_recommendation(self, golden_index: float, competition: str, total_search: int) -> str:
        """황금지수와 경쟁강도를 바탕으로 소싱 추천 여부를 판단합니다."""
        if total_search < 1000:
            return "❌ 비추천 (검색량 너무 적음)"
        if competition == "높음" and golden_index < 1.0:
            return "❌ 비추천 (경쟁 과다)"
        if golden_index >= 2.0 and competition in ("낮음", "중간"):
            return "⭐⭐⭐ 강력 추천"
        if golden_index >= 1.0:
            return "⭐⭐ 추천"
        if golden_index >= 0.5:
            return "⭐ 검토 필요"
        return "❌ 비추천 (경쟁 과다)"

    def find_golden_keywords(self, seed_keyword: str, top_n: int = 10) -> list:
        """
        시드 키워드에서 파생된 황금키워드를 찾습니다.

        Args:
            seed_keyword: 기본 키워드 (예: "텀블러")
            top_n:        상위 몇 개 반환

        Returns:
            황금지수 순으로 정렬된 KeywordData 목록
        """
        keywords_to_check = [seed_keyword]
        all_results = self.get_keyword_stats(keywords_to_check)

        # 황금지수 내림차순 정렬
        sorted_results = sorted(all_results, key=lambda x: x.golden_index, reverse=True)
        return sorted_results[:top_n]

    def _get_demo_data(self, keywords: list) -> list:
        """API 키 없을 때 사용하는 데모 데이터"""
        import random
        results = []
        for kw in keywords:
            total = random.randint(5000, 200000)
            products = random.randint(1000, 100000)
            golden = total / math.sqrt(products)
            results.append(KeywordData(
                keyword=kw,
                monthly_pc_search=int(total * 0.3),
                monthly_mobile_search=int(total * 0.7),
                total_search=total,
                pc_click_count=int(total * 0.05),
                mobile_click_count=int(total * 0.12),
                competition=random.choice(["낮음", "중간", "높음"]),
                product_count=products,
                golden_index=round(golden, 2),
                recommendation=self._get_recommendation(golden, "중간", total),
            ))
        return results


# ── 직접 실행 테스트 ─────────────────────────────────────

if __name__ == "__main__":
    researcher = NaverKeywordResearcher()

    test_keywords = ["텀블러", "보온도시락", "캔들DIY", "천연비누", "요가매트"]

    print("=" * 60)
    print("  키워드 수요 분석 (API 미설정 → 데모 데이터)")
    print("=" * 60)

    results = researcher.get_keyword_stats(test_keywords)
    results.sort(key=lambda x: x.golden_index, reverse=True)

    for r in results:
        print(f"\n{r}")
    print("\n" + "─" * 60)
    print("⭐ 소싱 추천 키워드:")
    for r in results:
        if "추천" in r.recommendation:
            print(f"  - {r.keyword}  황금지수 {r.golden_index}")
