# ============================================================
# 도매꾹 소싱 모듈 (국내 1위 위탁판매 플랫폼, 850만 상품)
#
# 도매꾹 OpenAPI로 키워드 검색 → 소싱 후보 상품을 수집합니다.
#
# API 발급: https://openapi.domeggook.com → API Key 관리
# 공식 문서: https://openapi.domeggook.com/main/guide/start
# 제한: 분당 180회, 하루 15,000회
# ============================================================

import os
import time
from typing import Optional
from sourcing.base import BaseSourcingClient, SourcingProduct

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class DomeggookClient(BaseSourcingClient):
    """
    도매꾹 OpenAPI 클라이언트

    설정:
        export DOMEGGOOK_API_KEY="your_api_key"
    """

    SOURCE_NAME = "domeggook"
    SOURCE_LABEL = "도매꾹"
    BASE_URL = "https://domeggook.com/ssl/api/"

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv("DOMEGGOOK_API_KEY", "")
        self._api_configured = bool(self.api_key)
        self._last_request_time = 0

    def _request(self, params: dict) -> dict:
        """API 요청. 분당 180회 제한을 자동으로 맞춥니다."""
        if not HAS_REQUESTS:
            raise ImportError("pip install requests 를 실행하세요")

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
        **kwargs,
    ) -> list:
        """키워드로 도매꾹 상품을 검색하여 소싱 후보를 반환합니다."""
        if not self._api_configured:
            return self._demo_products(keyword, min(max_results, 5))

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
                print(f"[도매꾹] API 오류: {e}")
                break

            items = data.get("item", [])
            if not items:
                break

            for item in items:
                p = self._parse(item)
                if p:
                    products.append(p)

            if len(items) < page_size:
                break
            page += 1

        return products[:max_results]

    def _parse(self, item: dict) -> Optional[SourcingProduct]:
        try:
            return SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=str(item.get("goodsNo", "")),
                product_name=item.get("goodsNm", ""),
                category=item.get("cateName", "기타"),
                supply_price=int(item.get("supplyPrice", 0)),
                consumer_price=int(item.get("consumerPrice", 0)),
                min_order_qty=int(item.get("minOrderQty", 1)),
                stock_qty=int(item.get("stockQty", 0)),
                shipping_type="위탁배송",
                shipping_days=2,
                supplier_name=item.get("comNm", ""),
                image_url=item.get("imageUrl", ""),
                product_url=f"https://domeggook.com/main/goods/goods_view.php?goodsNo={item.get('goodsNo', '')}",
                origin_country="국내산",
            )
        except Exception:
            return None

    def _demo_products(self, keyword: str, count: int) -> list:
        import random
        return [
            SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=f"DG-DEMO-{i}",
                product_name=f"[도매꾹 데모] {keyword} {i+1}호",
                category="생활용품",
                supply_price=random.randint(3000, 15000),
                consumer_price=random.randint(9000, 40000),
                min_order_qty=1,
                stock_qty=random.randint(10, 500),
                shipping_type="위탁배송",
                shipping_days=2,
                supplier_name="도매꾹데모공급사",
                image_url="",
                product_url="",
                origin_country="국내산",
            )
            for i in range(count)
        ]
