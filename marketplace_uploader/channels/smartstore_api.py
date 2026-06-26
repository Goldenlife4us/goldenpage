# ============================================================
# 스마트스토어 자동 업로드 모듈 (Phase 3 - 네이버 커머스 API)
#
# 네이버 커머스 API를 통해 스마트스토어에 상품을 자동 등록합니다.
#
# 참고: github.com/commerce-api-naver/commerce-api
# API 발급: https://developers.naver.com/apps/#/register
# 조건: 스마트스토어 계정 + 판매자 API 신청
# ============================================================

import os
import time
import hashlib
import hmac
import base64
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class SmartStoreAPI:
    """
    네이버 커머스 API 스마트스토어 상품 등록 클라이언트

    설정 방법:
    1. 스마트스토어 계정 개설
    2. https://developers.naver.com → 앱 등록 → 커머스 API 신청
    3. Client ID / Client Secret 발급
    4. 환경변수 설정:
       export NAVER_COMMERCE_CLIENT_ID="your_id"
       export NAVER_COMMERCE_CLIENT_SECRET="your_secret"
    """

    # 네이버 커머스 API 베이스 URL
    BASE_URL = "https://api.commerce.naver.com/external"

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.getenv("NAVER_COMMERCE_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("NAVER_COMMERCE_CLIENT_SECRET", "")
        self._api_configured = all([self.client_id, self.client_secret])
        self._access_token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> str:
        """OAuth 2.0 액세스 토큰을 발급받습니다. 만료 시 자동 갱신."""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        timestamp = str(int(time.time() * 1000))
        password = f"{self.client_id}_{timestamp}"

        # HMAC-SHA256 서명
        hashed = hmac.new(
            self.client_secret.encode("utf-8"),
            password.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        client_secret_sign = base64.b64encode(hashed).decode("utf-8")

        resp = requests.post(
            f"{self.BASE_URL}/v1/oauth2/token",
            data={
                "client_id":          self.client_id,
                "timestamp":          timestamp,
                "client_secret_sign": client_secret_sign,
                "grant_type":         "client_credentials",
                "type":               "SELF",
            },
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()

        self._access_token = token_data["access_token"]
        self._token_expires_at = time.time() + token_data.get("expires_in", 3600)
        return self._access_token

    def _get_headers(self) -> dict:
        """API 요청 헤더를 반환합니다."""
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type":  "application/json;charset=UTF-8",
        }

    def register_product(self, product_data: dict) -> dict:
        """
        스마트스토어에 상품을 등록합니다.

        Args:
            product_data: 상품 정보 딕셔너리 (아래 형식 참고)

        Returns:
            등록 결과 (product_id 포함)

        product_data 형식:
        {
            "originProduct": {
                "statusType": "SALE",
                "saleType": "NEW",
                "name": "상품명",
                "detailContent": "상품 상세 설명 HTML",
                "images": {"representativeImage": {"url": "이미지URL"}},
                "salePrice": 22000,
                "stockQuantity": 100,
                "deliveryInfo": {
                    "deliveryType": "DELIVERY",
                    "deliveryFee": {"deliveryFeeType": "PAID", "baseFee": 3000}
                },
                "category": {"id": "50000803"},
            }
        }
        """
        if not self._api_configured:
            print("[⚠] 스마트스토어 API가 설정되지 않았습니다.")
            print("  NAVER_COMMERCE_CLIENT_ID / NAVER_COMMERCE_CLIENT_SECRET 환경변수를 설정하세요.")
            return {"status": "SKIPPED", "reason": "API_NOT_CONFIGURED"}

        try:
            resp = requests.post(
                f"{self.BASE_URL}/v2/products",
                headers=self._get_headers(),
                json=product_data,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            print(f"  ✅ 스마트스토어 등록 완료 - 상품 ID: {result.get('originProductNo')}")
            return result
        except requests.HTTPError as e:
            print(f"  ❌ 등록 실패: {e.response.text}")
            return {"status": "ERROR", "error": str(e)}

    def bulk_register(self, products: list, delay: float = 1.0) -> list:
        """
        여러 상품을 순차적으로 등록합니다.

        Args:
            products: product_data 딕셔너리 목록
            delay:    상품 간 대기 시간 (초) - API 과부하 방지

        Returns:
            각 상품의 등록 결과 목록
        """
        results = []
        for i, product in enumerate(products, 1):
            name = product.get("originProduct", {}).get("name", f"상품 {i}")
            print(f"[{i}/{len(products)}] 등록 중: {name}")
            result = self.register_product(product)
            results.append(result)
            if i < len(products):
                time.sleep(delay)
        return results

    @staticmethod
    def build_product_payload(row: dict) -> dict:
        """
        마스터 상품 DB의 행(row)을 스마트스토어 API 페이로드로 변환합니다.

        Args:
            row: master_products.xlsx의 한 행 (딕셔너리)
        """
        from config.channel_config import SMARTSTORE_CATEGORY_MAP, CHANNEL_SHIPPING_FEE

        category_text = str(row.get("카테고리", "기타"))
        category_code = SMARTSTORE_CATEGORY_MAP.get(category_text, SMARTSTORE_CATEGORY_MAP["기타"])
        sale_price = int(row.get("스마트스토어_판매가", row.get("기본판매가", 0)))

        return {
            "originProduct": {
                "statusType":    "SALE",
                "saleType":      "NEW",
                "name":          str(row.get("스마트스토어_상품명", row.get("상품명", ""))),
                "detailContent": f"<p>{row.get('상품명', '')}</p>",
                "images":        {
                    "representativeImage": {
                        "url": str(row.get("대표이미지URL", ""))
                    }
                },
                "salePrice":     sale_price,
                "stockQuantity": int(row.get("재고수량", 0)),
                "deliveryInfo":  {
                    "deliveryType": "DELIVERY",
                    "deliveryFee":  {
                        "deliveryFeeType": "PAID",
                        "baseFee": CHANNEL_SHIPPING_FEE["smartstore"],
                    },
                },
                "category":      {"id": category_code},
            }
        }


# ── 직접 실행 테스트 ─────────────────────────────────────

if __name__ == "__main__":
    api = SmartStoreAPI()
    status = "설정됨" if api._api_configured else "미설정 (Phase 3에서 구현)"
    print(f"스마트스토어 API 상태: {status}")
    print("  → 자동 업로드는 NAVER_COMMERCE_CLIENT_ID/SECRET 설정 후 사용 가능")
