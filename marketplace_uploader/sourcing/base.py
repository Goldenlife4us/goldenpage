# ============================================================
# 소싱처 공통 베이스 클래스
#
# 모든 소싱처(도매꾹, 오너클랜, AliExpress 등)는 이 클래스를
# 상속받아 동일한 인터페이스로 사용할 수 있습니다.
#
# 새 소싱처 추가 방법:
#   1. BaseSourcingClient를 상속받는 클래스 작성
#   2. search_products() 메서드 구현
#   3. sourcing/registry.py에 등록
# ============================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SourcingProduct:
    """모든 소싱처에서 공통으로 사용하는 상품 데이터 구조"""
    source: str              # 소싱처 이름 (예: "domeggook", "ownerclan", "aliexpress")
    product_id: str          # 소싱처 내 상품 고유 ID
    product_name: str        # 원본 상품명
    category: str            # 카테고리
    supply_price: int        # 공급가 (원) - 마진 계산 기준
    consumer_price: int      # 소비자 권장가 (원)
    min_order_qty: int       # 최소 주문 수량
    stock_qty: int           # 재고 수량 (0이면 품절)
    shipping_type: str       # 배송 방식 ("위탁배송", "직배", "해외직배")
    shipping_days: int       # 예상 배송일 (일)
    supplier_name: str       # 공급업체/공급사 이름
    image_url: str           # 대표 이미지 URL
    product_url: str         # 상품 원본 URL
    options: list = field(default_factory=list)   # 옵션 목록
    tags: list = field(default_factory=list)      # 키워드 태그
    origin_country: str = "국내산"               # 원산지

    @property
    def is_available(self) -> bool:
        """판매 가능한 상품인지 확인합니다."""
        return self.stock_qty > 0 or self.stock_qty == -1  # -1은 무제한

    @property
    def margin_ratio(self) -> float:
        """소비자가 기준 마진율을 계산합니다."""
        if self.consumer_price <= 0:
            return 0.0
        return (self.consumer_price - self.supply_price) / self.consumer_price

    def to_master_row(self, target_margin: float = 0.35) -> dict:
        """
        마스터 상품 DB 형식으로 변환합니다.

        Args:
            target_margin: 목표 마진율 (기본 35%)
        """
        from processors.margin_calculator import calculate_recommended_price

        ss_price = calculate_recommended_price(self.supply_price, target_margin * 100, "smartstore")
        cp_price = calculate_recommended_price(self.supply_price, target_margin * 100, "coupang")
        es_price = calculate_recommended_price(self.supply_price, target_margin * 100, "11st")

        return {
            "상품코드":              f"{self.source.upper()[:2]}-{self.product_id}",
            "상품명":                self.product_name,
            "카테고리":              self._map_category(),
            "원가":                  self.supply_price,
            "기본판매가":            ss_price,
            "스마트스토어_판매가":    ss_price,
            "쿠팡_판매가":           cp_price,
            "11번가_판매가":         es_price,
            "스마트스토어_상품명":    self.product_name,
            "쿠팡_상품명":           self.product_name,
            "11번가_상품명":         self.product_name,
            "브랜드":                self.supplier_name,
            "제조사":                self.supplier_name,
            "원산지":                self.origin_country,
            "재고수량":              max(self.stock_qty, 0),
            "옵션명":                "",
            "옵션값":                ",".join(self.options) if self.options else "",
            "소재":                  "상세페이지 참조",
            "색상":                  "상세페이지 참조",
            "크기":                  "상세페이지 참조",
            "소싱처":                self.source,
            "소싱처_상품URL":        self.product_url,
        }

    def _map_category(self) -> str:
        """소싱처의 카테고리를 마스터 DB 카테고리로 매핑합니다."""
        from config.channel_config import SMARTSTORE_CATEGORY_MAP
        known = list(SMARTSTORE_CATEGORY_MAP.keys())
        for k in known:
            if k in self.category:
                return k
        return "기타"


class BaseSourcingClient(ABC):
    """
    모든 소싱처 클라이언트가 구현해야 하는 인터페이스.

    새로운 소싱처를 추가할 때 이 클래스를 상속받아
    search_products()만 구현하면 됩니다.
    """

    # 소싱처 이름 (하위 클래스에서 반드시 지정)
    SOURCE_NAME: str = "unknown"
    SOURCE_LABEL: str = "알 수 없는 소싱처"

    def __init__(self):
        self._api_configured = False

    @abstractmethod
    def search_products(
        self,
        keyword: str,
        max_results: int = 30,
        min_price: int = 0,
        max_price: int = 999999,
        **kwargs,
    ) -> list:
        """
        키워드로 상품을 검색하여 SourcingProduct 목록을 반환합니다.
        모든 하위 클래스에서 반드시 구현해야 합니다.
        """
        pass

    @property
    def is_available(self) -> bool:
        """이 소싱처를 현재 사용할 수 있는지 확인합니다."""
        return self._api_configured

    def get_status(self) -> str:
        """소싱처 연결 상태를 문자열로 반환합니다."""
        if self._api_configured:
            return f"✅ {self.SOURCE_LABEL} - 연결됨"
        return f"❌ {self.SOURCE_LABEL} - API Key 필요"
