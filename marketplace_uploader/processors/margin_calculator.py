# ============================================================
# 마진 계산 모듈
# 원가, 판매가, 채널 수수료, 배송비를 입력받아 마진을 계산합니다
# ============================================================

from config.channel_config import CHANNEL_FEE_RATE, CHANNEL_SHIPPING_FEE


def calculate_margin(cost_price: float, sale_price: float, channel: str) -> dict:
    """
    상품 하나의 마진을 계산합니다.

    Args:
        cost_price: 원가 (매입가)
        sale_price: 판매가
        channel:    채널명 ("smartstore", "coupang", "11st")

    Returns:
        마진 계산 결과 딕셔너리
    """
    # 채널 수수료율 가져오기 (없으면 기본 10%)
    fee_rate = CHANNEL_FEE_RATE.get(channel, 0.10)

    # 채널 수수료 금액 계산
    channel_fee = sale_price * fee_rate

    # 배송비 (셀러 부담분 - 보통 무료배송이면 셀러가 부담)
    # 여기서는 배송비를 0으로 가정 (고객에게 별도 청구하는 경우)
    seller_shipping_cost = 0

    # 순이익 = 판매가 - 원가 - 채널수수료 - 배송부담비용
    net_profit = sale_price - cost_price - channel_fee - seller_shipping_cost

    # 마진율 = 순이익 / 판매가 * 100
    if sale_price > 0:
        margin_rate = (net_profit / sale_price) * 100
    else:
        margin_rate = 0.0

    return {
        "sale_price":    round(sale_price, 0),
        "cost_price":    round(cost_price, 0),
        "channel_fee":   round(channel_fee, 0),
        "net_profit":    round(net_profit, 0),
        "margin_rate":   round(margin_rate, 1),
    }


def calculate_recommended_price(cost_price: float, target_margin_rate: float, channel: str) -> float:
    """
    목표 마진율에 맞는 권장 판매가를 역산합니다.

    Args:
        cost_price:         원가
        target_margin_rate: 목표 마진율 (예: 30 → 30%)
        channel:            채널명

    Returns:
        권장 판매가 (원 단위, 10원 단위 반올림)
    """
    fee_rate = CHANNEL_FEE_RATE.get(channel, 0.10)
    target_rate = target_margin_rate / 100

    # 판매가 = 원가 / (1 - 수수료율 - 목표마진율)
    denominator = 1 - fee_rate - target_rate
    if denominator <= 0:
        # 목표 마진율이 너무 높으면 계산 불가 → 원가의 2배 반환
        return cost_price * 2

    recommended = cost_price / denominator

    # 10원 단위로 반올림
    return round(recommended / 10) * 10
