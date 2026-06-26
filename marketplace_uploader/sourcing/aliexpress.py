# ============================================================
# AliExpress 소싱 모듈 (해외 드롭쉬핑)
#
# AliExpress Open Platform의 공식 드롭쉬핑 API를 사용합니다.
# 해외 배송 상품 소싱에 적합합니다.
#
# 공식 API: https://openservice.aliexpress.com/
# 등록 절차: AliExpress Open Platform 개발자 등록
# 주의: 해외 배송 (7~20일), 관세 별도, 반품 복잡
# ============================================================

import os
import time
import hashlib
import hmac
from sourcing.base import BaseSourcingClient, SourcingProduct

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class AliExpressClient(BaseSourcingClient):
    """
    AliExpress Open Platform 드롭쉬핑 API 클라이언트

    설정:
        export ALIEXPRESS_APP_KEY="your_app_key"
        export ALIEXPRESS_APP_SECRET="your_app_secret"
        export ALIEXPRESS_ACCESS_TOKEN="your_access_token"

    주의사항:
    - 배송 기간: 7~20일 (국내 대비 느림)
    - 관세: 150달러 이상 별도 부과
    - 반품/교환: 복잡, 고객 불만 위험
    - 추천 카테고리: 저가 생활용품, 패션 액세서리, 전자 소품
    """

    SOURCE_NAME = "aliexpress"
    SOURCE_LABEL = "AliExpress"
    BASE_URL = "https://api-sg.aliexpress.com/sync"

    def __init__(self, app_key: str = None, app_secret: str = None, access_token: str = None):
        super().__init__()
        self.app_key = app_key or os.getenv("ALIEXPRESS_APP_KEY", "")
        self.app_secret = app_secret or os.getenv("ALIEXPRESS_APP_SECRET", "")
        self.access_token = access_token or os.getenv("ALIEXPRESS_ACCESS_TOKEN", "")
        self._api_configured = all([self.app_key, self.app_secret])

    def _sign(self, params: dict) -> str:
        """API 요청 서명을 생성합니다 (HMAC-SHA256)."""
        sorted_params = sorted(params.items())
        sign_str = "".join(f"{k}{v}" for k, v in sorted_params)
        sign_bytes = hmac.new(
            self.app_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()
        return sign_bytes

    def search_products(
        self,
        keyword: str,
        max_results: int = 30,
        min_price: int = 0,
        max_price: int = 999999,
        **kwargs,
    ) -> list:
        """AliExpress에서 키워드로 드롭쉬핑 가능 상품을 검색합니다."""
        if not self._api_configured:
            return self._demo_products(keyword, min(max_results, 5))

        if not HAS_REQUESTS:
            raise ImportError("pip install requests 를 실행하세요")

        products = []
        page = 1

        while len(products) < max_results:
            timestamp = str(int(time.time() * 1000))
            params = {
                "app_key":     self.app_key,
                "timestamp":   timestamp,
                "sign_method": "sha256",
                "method":      "aliexpress.ds.product.search",
                "keywords":    keyword,
                "page_no":     page,
                "page_size":   min(20, max_results),
                "min_sale_price": min_price * 100,  # 센트 단위
                "max_sale_price": min(max_price * 100, 99999999),
                "ship_to_country": "KR",
                "target_currency": "KRW",
                "target_language": "KO",
            }
            if self.access_token:
                params["session"] = self.access_token
            params["sign"] = self._sign(params)

            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[AliExpress] API 오류: {e}")
                break

            result = data.get("aliexpress_ds_product_search_response", {})
            items = result.get("products", {}).get("traffic_product_dto", [])
            if not items:
                break

            for item in items:
                p = self._parse(item)
                if p:
                    products.append(p)

            if len(items) < 20:
                break
            page += 1
            time.sleep(0.5)

        return products[:max_results]

    def _parse(self, item: dict) -> SourcingProduct:
        try:
            price_info = item.get("sku_info", {})
            price_krw = int(float(price_info.get("sku_price", "0").replace(",", "")) * 1400)

            return SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=str(item.get("product_id", "")),
                product_name=item.get("product_title", ""),
                category=item.get("first_level_category_name", "기타"),
                supply_price=price_krw,
                consumer_price=int(price_krw * 2.5),
                min_order_qty=1,
                stock_qty=int(item.get("product_stock", 999)),
                shipping_type="해외직배",
                shipping_days=int(item.get("logistics_delivery_time", 14)),
                supplier_name=item.get("store_info", {}).get("store_name", "AliExpress"),
                image_url=item.get("product_main_image_url", ""),
                product_url=f"https://www.aliexpress.com/item/{item.get('product_id', '')}.html",
                origin_country="중국산",
            )
        except Exception:
            return None

    def _demo_products(self, keyword: str, count: int) -> list:
        import random
        return [
            SourcingProduct(
                source=self.SOURCE_NAME,
                product_id=f"AE-DEMO-{i}",
                product_name=f"[AliExpress 데모] {keyword} {i+1}",
                category="생활용품",
                supply_price=random.randint(1500, 8000),
                consumer_price=random.randint(5000, 25000),
                min_order_qty=1,
                stock_qty=999,
                shipping_type="해외직배",
                shipping_days=random.randint(7, 20),
                supplier_name="AliExpressStore",
                image_url="",
                product_url="",
                origin_country="중국산",
            )
            for i in range(count)
        ]
