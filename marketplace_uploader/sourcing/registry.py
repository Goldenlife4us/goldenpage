#!/usr/bin/env python3
# ============================================================
# 소싱처 레지스트리 - 멀티소싱 통합 엔진
#
# 모든 소싱처를 한 번에 검색하고 결과를 통합합니다.
# 새 소싱처는 여기에 등록만 하면 자동으로 사용됩니다.
#
# 사용법:
#   python sourcing/registry.py 텀블러
# ============================================================

import sys
import os
import concurrent.futures
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sourcing.domeggook   import DomeggookClient
from sourcing.ownerclan   import OwnerClanClient
from sourcing.onchannel   import OnChannelClient
from sourcing.aliexpress  import AliExpressClient


# ── 소싱처 등록 목록 ──────────────────────────────────────
# 새로운 소싱처를 추가하려면 이 리스트에만 추가하면 됩니다.

ALL_SOURCES = {
    # 국내 소싱처
    "domeggook":  DomeggookClient,
    "ownerclan":  OwnerClanClient,
    "onchannel":  OnChannelClient,
    # 해외 소싱처
    "aliexpress": AliExpressClient,
}

# 소싱처 그룹 (--source 옵션에서 그룹명으로 선택 가능)
SOURCE_GROUPS = {
    "domestic": ["domeggook", "ownerclan", "onchannel"],
    "overseas": ["aliexpress"],
    "all":      list(ALL_SOURCES.keys()),
}


class MultiSourceEngine:
    """
    여러 소싱처를 동시에 검색하는 통합 엔진.

    동작 방식:
    - 설정된 소싱처를 병렬로 동시 검색 (속도 최적화)
    - 결과를 통합하고 중복 제거
    - 황금지수 / 마진율 기준으로 자동 정렬
    """

    def __init__(self, sources: list = None):
        """
        Args:
            sources: 사용할 소싱처 이름 목록.
                     None이면 등록된 모든 소싱처 사용.
        """
        if sources is None:
            sources = list(ALL_SOURCES.keys())

        self.clients = {}
        for name in sources:
            if name in ALL_SOURCES:
                self.clients[name] = ALL_SOURCES[name]()

    def status(self):
        """현재 연결된 소싱처 상태를 출력합니다."""
        print("소싱처 연결 상태:")
        for name, client in self.clients.items():
            print(f"  {client.get_status()}")

    def search(
        self,
        keyword: str,
        max_per_source: int = 20,
        min_price: int = 3000,
        max_price: int = 100000,
        sources: list = None,
        parallel: bool = True,
    ) -> list:
        """
        모든 소싱처에서 동시에 상품을 검색하여 통합 결과를 반환합니다.

        Args:
            keyword:        검색 키워드
            max_per_source: 소싱처당 최대 수집 수 (기본 20개)
            min_price:      최소 원가 필터
            max_price:      최대 원가 필터
            sources:        특정 소싱처만 지정 (None=전체)
            parallel:       병렬 검색 여부 (기본 True)

        Returns:
            SourcingProduct 목록 (마진율 내림차순 정렬)
        """
        active_clients = {
            k: v for k, v in self.clients.items()
            if sources is None or k in sources
        }

        results = []

        if parallel and len(active_clients) > 1:
            # 병렬 검색: 모든 소싱처를 동시에 요청
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_clients)) as executor:
                futures = {
                    executor.submit(
                        client.search_products,
                        keyword,
                        max_per_source,
                        min_price,
                        max_price,
                    ): name
                    for name, client in active_clients.items()
                }
                for future in concurrent.futures.as_completed(futures):
                    source_name = futures[future]
                    try:
                        products = future.result(timeout=30)
                        results.extend(products)
                        print(f"  [{source_name}] {len(products)}개 수집")
                    except Exception as e:
                        print(f"  [{source_name}] 오류: {e}")
        else:
            # 순차 검색
            for name, client in active_clients.items():
                try:
                    products = client.search_products(keyword, max_per_source, min_price, max_price)
                    results.extend(products)
                    print(f"  [{name}] {len(products)}개 수집")
                except Exception as e:
                    print(f"  [{name}] 오류: {e}")

        # 중복 제거 + 마진율 기준 정렬
        seen = set()
        unique = []
        for p in results:
            key = (p.source, p.product_id)
            if key not in seen:
                seen.add(key)
                unique.append(p)

        unique.sort(key=lambda x: x.margin_ratio, reverse=True)
        return unique

    def search_to_dataframe(
        self,
        keyword: str,
        target_margin: float = 0.35,
        **kwargs,
    ) -> pd.DataFrame:
        """
        검색 결과를 분석용 DataFrame으로 반환합니다.
        마진 계산 및 SEO 점수도 함께 포함됩니다.
        """
        from processors.margin_calculator import calculate_margin, calculate_recommended_price
        from core.seo_validator import validate_all_channels

        products = self.search(keyword, **kwargs)
        rows = []

        for p in products:
            rec_price = calculate_recommended_price(p.supply_price, target_margin * 100, "smartstore")
            margin = calculate_margin(p.supply_price, rec_price, "smartstore")
            seo = validate_all_channels(p.product_name, ["smartstore"])
            seo_score = seo[0].score if seo else 0

            rows.append({
                "소싱처":       p.source,
                "상품명":       p.product_name[:35] + ("..." if len(p.product_name) > 35 else ""),
                "원가":         p.supply_price,
                "추천판매가":   int(rec_price),
                "마진율(%)":    margin["margin_rate"],
                "순이익(원)":   int(margin["net_profit"]),
                "재고":         p.stock_qty,
                "배송":         p.shipping_type,
                "배송일":       f"{p.shipping_days}일",
                "SEO점수":      seo_score,
                "원산지":       p.origin_country,
            })

        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def save_to_master(
        self,
        products: list,
        master_path: str = "data/master_products.xlsx",
        target_margin: float = 0.35,
    ) -> int:
        """
        수집된 상품을 마스터 DB에 추가합니다.

        Returns:
            추가된 상품 수
        """
        import os as _os
        _os.makedirs("data", exist_ok=True)

        new_rows = [p.to_master_row(target_margin) for p in products]
        new_df = pd.DataFrame(new_rows)

        try:
            existing = pd.read_excel(master_path)
            # 이미 있는 상품코드는 덮어쓰지 않음
            existing_codes = set(existing["상품코드"].astype(str))
            new_df = new_df[~new_df["상품코드"].astype(str).isin(existing_codes)]
            combined = pd.concat([existing, new_df], ignore_index=True)
        except FileNotFoundError:
            combined = new_df

        combined.to_excel(master_path, index=False)
        return len(new_df)


# ── 직접 실행 테스트 ─────────────────────────────────────

if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else "텀블러"

    print("=" * 65)
    print(f"  멀티소싱 통합 검색: '{keyword}'")
    print("=" * 65)

    engine = MultiSourceEngine()
    engine.status()
    print()

    print(f"[병렬 검색 시작] 소싱처 {len(engine.clients)}곳 동시 탐색...")
    df = engine.search_to_dataframe(
        keyword,
        max_per_source=5,
        min_price=3000,
        max_price=50000,
        target_margin=0.35,
    )

    if df.empty:
        print("검색 결과가 없습니다.")
    else:
        print(f"\n{'─'*65}")
        print(df.to_string(index=False))
        print(f"{'─'*65}")
        print(f"\n총 {len(df)}개 상품 | 소싱처별: {df['소싱처'].value_counts().to_dict()}")

        best = df.nlargest(3, "마진율(%)")
        print("\n⭐ 마진율 TOP 3:")
        for _, row in best.iterrows():
            print(f"  [{row['소싱처']}] {row['상품명']} → 마진율 {row['마진율(%)']}%, 순이익 {row['순이익(원)']:,}원")
