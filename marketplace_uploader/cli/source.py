#!/usr/bin/env python3
# ============================================================
# 소싱 CLI - 키워드로 팔릴 상품 자동 탐색
#
# 사용법:
#   python cli/source.py 텀블러
#   python cli/source.py 텀블러 --max 20 --min-price 5000
# ============================================================

import sys
import os
import argparse
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sourcing.keyword_research import NaverKeywordResearcher
from sourcing.domeggook import DomeggookClient
from processors.margin_calculator import calculate_margin, calculate_recommended_price
from core.seo_validator import validate_all_channels


def main():
    parser = argparse.ArgumentParser(description="키워드로 소싱 후보 상품을 탐색합니다")
    parser.add_argument("keyword", help="검색 키워드 (예: 텀블러)")
    parser.add_argument("--max", type=int, default=10, help="최대 수집 개수 (기본: 10)")
    parser.add_argument("--min-price", type=int, default=3000, help="최소 원가 (기본: 3000)")
    parser.add_argument("--max-price", type=int, default=50000, help="최대 원가 (기본: 50000)")
    parser.add_argument("--target-margin", type=float, default=35.0, help="목표 마진율% (기본: 35)")
    parser.add_argument("--save", action="store_true", help="결과를 마스터 DB에 추가")
    args = parser.parse_args()

    keyword = args.keyword
    print("=" * 60)
    print(f"  소싱 탐색: '{keyword}'")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # STEP 1: 키워드 수요 분석
    print(f"\n[1/3] 키워드 수요 분석 중...")
    researcher = NaverKeywordResearcher()
    keyword_data = researcher.get_keyword_stats([keyword])
    if keyword_data:
        kd = keyword_data[0]
        print(f"  '{keyword}' 월간 검색수: {kd.total_search:,}회")
        print(f"  경쟁강도: {kd.competition} / 황금지수: {kd.golden_index}")
        print(f"  판단: {kd.recommendation}")
        if "비추천" in kd.recommendation:
            print(f"\n  ⚠ 경쟁이 치열하거나 검색량이 적습니다. 계속 진행하시겠습니까?")

    # STEP 2: 도매꾹 상품 수집
    print(f"\n[2/3] 도매꾹 소싱 후보 수집 중 (최대 {args.max}개)...")
    client = DomeggookClient()
    products = client.search_products(
        keyword=keyword,
        max_results=args.max,
        min_price=args.min_price,
        max_price=args.max_price,
    )
    print(f"  → {len(products)}개 상품 수집 완료")

    # STEP 3: 마진 계산 + SEO 검증
    print(f"\n[3/3] 마진 계산 및 SEO 검증 중...")
    rows = []
    for p in products:
        # 목표 마진 기준 추천 판매가 계산
        rec_price = calculate_recommended_price(
            p.supply_price, args.target_margin, "smartstore"
        )
        margin = calculate_margin(p.supply_price, rec_price, "smartstore")

        # 상품명 SEO 검증
        seo_results = validate_all_channels(p.product_name, ["smartstore"])
        seo_score = seo_results[0].score if seo_results else 0
        seo_pass = "✅" if seo_results and seo_results[0].is_valid else "⚠"

        rows.append({
            "상품번호":      p.product_no,
            "상품명":        p.product_name[:40] + ("..." if len(p.product_name) > 40 else ""),
            "원가":          f"{p.supply_price:,}원",
            "추천판매가":    f"{int(rec_price):,}원",
            "마진율":        f"{margin['margin_rate']}%",
            "순이익":        f"{int(margin['net_profit']):,}원",
            "재고":          p.stock_qty,
            "SEO점수":       f"{seo_score}/100 {seo_pass}",
        })

    result_df = pd.DataFrame(rows)
    print(f"\n{'─'*60}")
    print(result_df.to_string(index=False))
    print(f"{'─'*60}")

    # 마스터 DB 저장 옵션
    if args.save and products:
        master_path = "data/master_products.xlsx"
        print(f"\n마스터 DB에 저장 중: {master_path}")
        try:
            existing = pd.read_excel(master_path)
        except FileNotFoundError:
            existing = pd.DataFrame()

        new_rows = [p.to_master_row(smartstore_markup=float(rec_price / max(p.supply_price, 1)))
                    for p in products]
        new_df = pd.DataFrame(new_rows)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_excel(master_path, index=False)
        print(f"  → {len(new_rows)}개 상품 추가 완료 (총 {len(combined)}개)")


if __name__ == "__main__":
    main()
