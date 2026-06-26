# ============================================================
# 스마트스토어 채널 변환 모듈
# 마스터 상품 데이터를 스마트스토어 업로드 양식으로 변환합니다
# ============================================================

import pandas as pd
from config.channel_config import (
    SMARTSTORE_CATEGORY_MAP,
    CHANNEL_SHIPPING_FEE,
    CHANNEL_FREE_SHIPPING_THRESHOLD,
    SMARTSTORE_COLUMNS,
)
from processors.margin_calculator import calculate_margin


def transform_to_smartstore(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    마스터 상품 DataFrame을 스마트스토어 업로드용 DataFrame으로 변환합니다.

    Args:
        master_df: master_products.xlsx에서 읽은 원본 데이터

    Returns:
        스마트스토어 업로드용 DataFrame
    """
    rows = []

    for _, row in master_df.iterrows():
        # 마진 계산
        margin_info = calculate_margin(
            cost_price=float(row.get("원가", 0)),
            sale_price=float(row.get("스마트스토어_판매가", row.get("기본판매가", 0))),
            channel="smartstore",
        )

        # 판매가 기준 무료배송 여부 결정
        sale_price = margin_info["sale_price"]
        threshold = CHANNEL_FREE_SHIPPING_THRESHOLD["smartstore"]
        is_free_shipping = "Y" if sale_price >= threshold else "N"
        shipping_fee = 0 if is_free_shipping == "Y" else CHANNEL_SHIPPING_FEE["smartstore"]

        # 카테고리 코드 매핑 (마스터의 카테고리 텍스트 → 스마트스토어 코드)
        category_text = str(row.get("카테고리", "기타"))
        category_code = SMARTSTORE_CATEGORY_MAP.get(category_text, SMARTSTORE_CATEGORY_MAP["기타"])

        # 스마트스토어용 상품명: 기본 상품명 그대로 사용 (채널별 특화 명칭이 있으면 우선 사용)
        product_name = str(row.get("스마트스토어_상품명", row.get("상품명", "")))

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
            "옵션명":             str(row.get("옵션명", "")),
            "옵션값":             str(row.get("옵션값", "")),
            "고시정보_품명":      str(row.get("상품명", "")),
            "고시정보_소재":      str(row.get("소재", "상세페이지 참조")),
            "고시정보_색상":      str(row.get("색상", "상세페이지 참조")),
            "고시정보_크기":      str(row.get("크기", "상세페이지 참조")),
            "마진율(%)":          margin_info["margin_rate"],
            "순이익(원)":         int(margin_info["net_profit"]),
        })

    result_df = pd.DataFrame(rows, columns=SMARTSTORE_COLUMNS)
    return result_df
