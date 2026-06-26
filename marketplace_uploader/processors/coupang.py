# ============================================================
# 쿠팡 채널 변환 모듈
# 마스터 상품 데이터를 쿠팡 업로드 양식으로 변환합니다
# ============================================================

import pandas as pd
from config.channel_config import (
    COUPANG_CATEGORY_MAP,
    CHANNEL_SHIPPING_FEE,
    CHANNEL_FREE_SHIPPING_THRESHOLD,
    COUPANG_COLUMNS,
)
from processors.margin_calculator import calculate_margin


def transform_to_coupang(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    마스터 상품 DataFrame을 쿠팡 업로드용 DataFrame으로 변환합니다.

    쿠팡 특이사항:
    - 수수료가 높기 때문에 쿠팡 전용 판매가가 있으면 우선 사용
    - 무료배송 기준금액이 19,800원으로 낮음
    - 상품명 앞에 브랜드를 붙이는 경우가 많음

    Args:
        master_df: master_products.xlsx에서 읽은 원본 데이터

    Returns:
        쿠팡 업로드용 DataFrame
    """
    rows = []

    for _, row in master_df.iterrows():
        # 쿠팡 전용 판매가가 있으면 사용, 없으면 기본 판매가 사용
        sale_price = float(row.get("쿠팡_판매가", row.get("기본판매가", 0)))

        margin_info = calculate_margin(
            cost_price=float(row.get("원가", 0)),
            sale_price=sale_price,
            channel="coupang",
        )

        sale_price = margin_info["sale_price"]
        threshold = CHANNEL_FREE_SHIPPING_THRESHOLD["coupang"]
        is_free_shipping = "Y" if sale_price >= threshold else "N"
        shipping_fee = 0 if is_free_shipping == "Y" else CHANNEL_SHIPPING_FEE["coupang"]

        category_text = str(row.get("카테고리", "기타"))
        category_code = COUPANG_CATEGORY_MAP.get(category_text, COUPANG_CATEGORY_MAP["기타"])

        # 쿠팡 상품명: 채널 전용 명칭이 있으면 우선 사용
        product_name = str(row.get("쿠팡_상품명", row.get("상품명", "")))

        rows.append({
            "상품번호":           str(row.get("상품코드", "")),
            "상품명":             product_name,
            "판매가":             int(sale_price),
            "배송비":             shipping_fee,
            "무료배송여부":       is_free_shipping,
            "카테고리코드":       category_code,
            "브랜드":             str(row.get("브랜드", "")),
            "제조사":             str(row.get("제조사", "")),
            "원산지":             str(row.get("원산지", "국내산")),
            "재고수량":           int(row.get("재고수량", 0)),
            "옵션종류":           str(row.get("옵션명", "")),
            "옵션값":             str(row.get("옵션값", "")),
            "상품고시_품명":      str(row.get("상품명", "")),
            "상품고시_소재":      str(row.get("소재", "상세페이지 참조")),
            "상품고시_색상":      str(row.get("색상", "상세페이지 참조")),
            "상품고시_크기":      str(row.get("크기", "상세페이지 참조")),
            "마진율(%)":          margin_info["margin_rate"],
            "순이익(원)":         int(margin_info["net_profit"]),
        })

    result_df = pd.DataFrame(rows, columns=COUPANG_COLUMNS)
    return result_df
