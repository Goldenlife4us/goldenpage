# ============================================================
# 온채널 소싱 모듈
#
# 온채널은 초보 셀러에게 친화적인 도매 플랫폼으로,
# 스마트스토어/쿠팡 연동 및 주문 자동화를 지원합니다.
#
# API 가이드: https://onchannelnotice.oopy.io/guide/api
# 특징: 주문 자동 수집, 발주, 송장 자동 연동까지 원스톱
# ============================================================

import os
import time
from sourcing.base import BaseSourcingClient, SourcingProduct

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class OnChannelClient(BaseSourcingClient):
    """
    온채널 상품 소싱 클라이언트

    설정:
        export ONCHANNEL_API_KEY="your_key"
    """

    SOURCE_NAME = "onchannel"
    SOURCE_LABEL = "온채널"
    BASE_URL = "https://api.onch3.co.kr"

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv("ONCHANNEL_API_KEY", "")
        self._api_configured = bool(self.api_key)

    def search_products(
        self,
        keyword: str,
        max_results: int = 30,
        min_price: int = 0,
        max_price: int = 999999,
        **kwargs,
    ) -> list:
        if not self._api_configured:
            return self._demo_products(keyword, min(max_results, 5))

        if not HAS_REQUESTS:
            raise ImportError("pip install requests 를 실행하세요")

        products = []
        page = 1

        while len(products) < max_results:
            try:
                resp = requests.get(
                    f"{self.BASE_URL}/v1/products",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    params={
                        "keyword":  keyword,
                        "page":     page,
                        "limit":    min(30, max_results),
                        "minPrice": min_price,
                        "maxPrice": max_price,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[온채널] API 오류: {e}")
                break

            items = data.get("data", [])
            if not items:
                break

            for item in items:
                p = self._parse(item)
                if p:
                    products.append(p)

            if data.get("hasNext") is False:
                break
            page += 1
            time.sleep(0.3)

        return products[:max_results]

    def _parse(self, item: dict):
        try:
            return SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=str(item.get("productCode", "")),
                product_name=item.get("productName", ""),
                category=item.get("category1", "기타"),
                supply_price=int(item.get("supplyPrice", 0)),
                consumer_price=int(item.get("sellPrice", 0)),
                min_order_qty=1,
                stock_qty=int(item.get("stock", 0)),
                shipping_type="위탁배송",
                shipping_days=2,
                supplier_name=item.get("brandName", ""),
                image_url=item.get("mainImage", ""),
                product_url=f"https://www.onch3.co.kr/mall_detailview.html?p_c={item.get('productCode', '')}",
                origin_country="국내산",
            )
        except Exception:
            return None

    def _demo_products(self, keyword: str, count: int) -> list:
        import random
        return [
            SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=f"ONC-DEMO-{i}",
                product_name=f"[온채널 데모] {keyword} {i+1}호",
                category="주방용품",
                supply_price=random.randint(5000, 18000),
                consumer_price=random.randint(15000, 45000),
                min_order_qty=1,
                stock_qty=random.randint(30, 200),
                shipping_type="위탁배송",
                shipping_days=2,
                supplier_name="온채널데모공급사",
                image_url="",
                product_url="",
                origin_country="국내산",
            )
            for i in range(count)
        ]
