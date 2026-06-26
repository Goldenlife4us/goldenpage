# ============================================================
# 오너클랜 소싱 모듈 (국내 2위 위탁판매 플랫폼, 500만 상품)
#
# 오너클랜은 스마트스토어/쿠팡 직접 연동 기능을 제공하며,
# 셀러 계정으로 API 연동이 가능합니다.
#
# API 정보: https://ownerclan.com/V2/info_page/storefarm_api_service.php
# 연동 방식: 오너클랜 계정 → 스마트스토어/쿠팡 API Key 등록
# ============================================================

import os
import time
from sourcing.base import BaseSourcingClient, SourcingProduct

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class OwnerClanClient(BaseSourcingClient):
    """
    오너클랜 상품 소싱 클라이언트

    오너클랜 API 특징:
    - 스마트스토어/쿠팡에 직접 상품 전송 기능 지원
    - 주문 자동 수집 및 발주 처리 가능
    - 택배 송장 자동 연동

    설정:
        export OWNERCLAN_API_KEY="your_key"
        export OWNERCLAN_MEMBER_ID="your_id"
    """

    SOURCE_NAME = "ownerclan"
    SOURCE_LABEL = "오너클랜"
    BASE_URL = "https://ownerclan.com/V2/api"

    def __init__(self, api_key: str = None, member_id: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv("OWNERCLAN_API_KEY", "")
        self.member_id = member_id or os.getenv("OWNERCLAN_MEMBER_ID", "")
        self._api_configured = all([self.api_key, self.member_id])

    def search_products(
        self,
        keyword: str,
        max_results: int = 30,
        min_price: int = 0,
        max_price: int = 999999,
        **kwargs,
    ) -> list:
        """키워드로 오너클랜 상품을 검색합니다."""
        if not self._api_configured:
            return self._demo_products(keyword, min(max_results, 5))

        if not HAS_REQUESTS:
            raise ImportError("pip install requests 를 실행하세요")

        products = []
        page = 1

        while len(products) < max_results:
            try:
                resp = requests.post(
                    f"{self.BASE_URL}/product/search",
                    json={
                        "apiKey":    self.api_key,
                        "memberId":  self.member_id,
                        "keyword":   keyword,
                        "page":      page,
                        "pageSize":  min(30, max_results),
                        "minPrice":  min_price,
                        "maxPrice":  max_price,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[오너클랜] API 오류: {e}")
                break

            items = data.get("products", [])
            if not items:
                break

            for item in items:
                p = self._parse(item)
                if p:
                    products.append(p)

            if len(items) < 30:
                break
            page += 1
            time.sleep(0.3)

        return products[:max_results]

    def _parse(self, item: dict):
        try:
            return SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=str(item.get("productNo", "")),
                product_name=item.get("productName", ""),
                category=item.get("category", "기타"),
                supply_price=int(item.get("supplyPrice", 0)),
                consumer_price=int(item.get("consumerPrice", 0)),
                min_order_qty=int(item.get("minOrderQty", 1)),
                stock_qty=int(item.get("stockQty", 0)),
                shipping_type="위탁배송",
                shipping_days=2,
                supplier_name=item.get("companyName", ""),
                image_url=item.get("imageUrl", ""),
                product_url=f"https://ownerclan.com/product/{item.get('productNo', '')}",
                origin_country="국내산",
            )
        except Exception:
            return None

    def _demo_products(self, keyword: str, count: int) -> list:
        import random
        return [
            SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=f"OC-DEMO-{i}",
                product_name=f"[오너클랜 데모] {keyword} {i+1}호",
                category="생활용품",
                supply_price=random.randint(4000, 20000),
                consumer_price=random.randint(12000, 50000),
                min_order_qty=1,
                stock_qty=random.randint(50, 300),
                shipping_type="위탁배송",
                shipping_days=2,
                supplier_name="오너클랜데모공급사",
                image_url="",
                product_url="",
                origin_country="국내산",
            )
            for i in range(count)
        ]
