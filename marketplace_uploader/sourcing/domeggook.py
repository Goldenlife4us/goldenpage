# ============================================================
# 도매꾹 상품 수집 모듈 (Phase 2 - 도매꾹 API Key 필요)
#
# 도매꾹 OpenAPI로 키워드 검색 → 소싱 후보 상품을 수집합니다.
# 원가, 소비자가, 재고, 상품명, 이미지 URL 등을 가져옵니다.
#
# API 발급: https://openapi.domeggook.com → API Key 관리
# 공식 문서: https://openapi.domeggook.com/main/guide/start
# 제한: 분당 180회, 하루 15,000회
# ============================================================

import os
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class SourcingProduct:
    """도매꾹에서 수집한 소싱 후보 상품"""
    product_no: str          # 도매꾹 상품번호
    product_name: str        # 상품명
    category: str            # 카테고리
    supply_price: int        # 공급가 (원가)
    consumer_price: int      # 소비자 권장가
    min_order_qty: int       # 최소 주문 수량
    stock_qty: int           # 재고 수량
    shipping_type: str       # 배송 방식 (위탁/직배)
    supplier_name: str       # 공급업체명
    image_url: str           # 대표 이미지 URL
    product_url: str         # 상품 상세 URL
    options: list = field(default_factory=list)  # 옵션 목록

    def to_master_row(self, smartstore_markup: float = 2.5) -> dict:
        """
        마스터 상품 DB 형식으로 변환합니다.
        markup: 원가 대비 판매가 배율 (기본 2.5배)
        """
        base_price = round(self.supply_price * smartstore_markup / 100) * 100
        return {
            "상품코드":              f"DG-{self.product_no}",
            "상품명":                self.product_name,
            "카테고리":              self.category,
            "원가":                  self.supply_price,
            "기본판매가":            base_price,
            "스마트스토어_판매가":    base_price,
            "쿠팡_판매가":           round(base_price * 1.05 / 100) * 100,
            "11번가_판매가":         round(base_price * 1.07 / 100) * 100,
            "스마트스토어_상품명":    self.product_name,
            "쿠팡_상품명":           self.product_name,
            "11번가_상품명":         self.product_name,
            "브랜드":                self.supplier_name,
            "제조사":                self.supplier_name,
            "원산지":                "상세페이지 참조",
            "재고수량":              self.stock_qty,
            "옵션명":                "",
            "옵션값":                "",
            "소재":                  "상세페이지 참조",
            "색상":                  "상세페이지 참조",
            "크기":                  "상세페이지 참조",
        }


class DomeggookClient:
    """
    도매꾹 OpenAPI 클라이언트

    API Key 설정 방법:
    1. https://openapi.domeggook.com 접속
    2. 로그인 후 API Key 발급
    3. config/settings.py에 입력 OR 환경변수 설정:
       export DOMEGGOOK_API_KEY="your_api_key"
    """

    BASE_URL = "https://domeggook.com/ssl/api/"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DOMEGGOOK_API_KEY", "")
        self._api_configured = bool(self.api_key)
        self._last_request_time = 0

    def _request(self, params: dict) -> dict:
        """API 요청을 실행합니다. 호출 간격을 자동으로 조절합니다."""
        if not HAS_REQUESTS:
            raise ImportError("pip install requests 를 실행하세요")

        # 분당 180회 제한 → 최소 0.35초 간격
        elapsed = time.time() - self._last_request_time
        if elapsed < 0.35:
            time.sleep(0.35 - elapsed)

        params["aid"] = self.api_key
        params["outputType"] = "json"

        resp = requests.get(self.BASE_URL, params=params, timeout=15)
        self._last_request_time = time.time()
        resp.raise_for_status()
        return resp.json()

    def search_products(
        self,
        keyword: str,
        max_results: int = 30,
        min_price: int = 3000,
        max_price: int = 50000,
        shipping_type: str = "dropship",  # "dropship" = 위탁배송
    ) -> list:
        """
        키워드로 도매꾹 상품을 검색하여 소싱 후보를 반환합니다.

        Args:
            keyword:      검색 키워드
            max_results:  최대 수집 개수
            min_price:    최소 원가 필터
            max_price:    최대 원가 필터
            shipping_type: 배송 방식 필터

        Returns:
            SourcingProduct 목록
        """
        if not self._api_configured:
            print("[경고] 도매꾹 API Key가 설정되지 않았습니다.")
            print("  → config/settings.py에 DOMEGGOOK_API_KEY를 입력하세요")
            return self._get_demo_products(keyword, max_results)

        products = []
        page = 1
        page_size = min(30, max_results)

        while len(products) < max_results:
            params = {
                "mode":       "getGoodsListForSeller",
                "searchWord": keyword,
                "pageNum":    page,
                "pageSize":   page_size,
                "minPrice":   min_price,
                "maxPrice":   max_price,
            }

            try:
                data = self._request(params)
            except Exception as e:
                print(f"[오류] 도매꾹 API 호출 실패: {e}")
                break

            items = data.get("item", [])
            if not items:
                break

            for item in items:
                product = self._parse_product(item)
                if product:
                    products.append(product)

            if len(items) < page_size:
                break  # 마지막 페이지
            page += 1

        return products[:max_results]

    def _parse_product(self, item: dict) -> Optional[SourcingProduct]:
        """API 응답 항목을 SourcingProduct로 변환합니다."""
        try:
            return SourcingProduct(
                product_no=str(item.get("goodsNo", "")),
                product_name=item.get("goodsNm", ""),
                category=item.get("cateName", "기타"),
                supply_price=int(item.get("supplyPrice", 0)),
                consumer_price=int(item.get("consumerPrice", 0)),
                min_order_qty=int(item.get("minOrderQty", 1)),
                stock_qty=int(item.get("stockQty", 0)),
                shipping_type=item.get("deliveryType", ""),
                supplier_name=item.get("comNm", ""),
                image_url=item.get("imageUrl", ""),
                product_url=f"https://domeggook.com/main/goods/goods_view.php?goodsNo={item.get('goodsNo', '')}",
            )
        except (KeyError, ValueError, TypeError):
            return None

    def _get_demo_products(self, keyword: str, count: int = 5) -> list:
        """API 키 없을 때 사용하는 데모 데이터"""
        import random
        demo = []
        for i in range(min(count, 5)):
            price = random.randint(3000, 15000)
            demo.append(SourcingProduct(
                product_no=f"DEMO-{1000 + i}",
                product_name=f"[데모] {keyword} 상품 {i+1}호",
                category="생활용품",
                supply_price=price,
                consumer_price=price * 3,
                min_order_qty=1,
                stock_qty=random.randint(10, 500),
                shipping_type="위탁배송",
                supplier_name="데모공급사",
                image_url="",
                product_url="",
            ))
        return demo


# ── 직접 실행 테스트 ─────────────────────────────────────

if __name__ == "__main__":
    client = DomeggookClient()

    print("=" * 60)
    print("  도매꾹 상품 수집 테스트 (API 미설정 → 데모 데이터)")
    print("=" * 60)

    products = client.search_products("텀블러", max_results=5)

    for p in products:
        print(f"\n상품번호: {p.product_no}")
        print(f"  상품명: {p.product_name}")
        print(f"  원가: {p.supply_price:,}원 / 소비자가: {p.consumer_price:,}원")
        print(f"  재고: {p.stock_qty}개 / 배송: {p.shipping_type}")

        # 마스터 DB 변환 미리보기
        master_row = p.to_master_row(smartstore_markup=2.5)
        print(f"  → 스마트스토어 예상 판매가: {master_row['스마트스토어_판매가']:,}원")
