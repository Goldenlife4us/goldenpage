# ============================================================
# API 키 및 전역 설정 파일
#
# 사용법:
#   1. 이 파일을 직접 편집하거나
#   2. 환경변수로 설정 (보안상 권장):
#      export NAVER_AD_CUSTOMER_ID="123456"
#      export DOMEGGOOK_API_KEY="abcdef"
#      export ANTHROPIC_API_KEY="sk-ant-..."
# ============================================================

import os

# ── 네이버 검색광고 API (키워드 검색량 조회) ─────────────
# 발급: https://searchad.naver.com → 도구 → API 관리
NAVER_AD_CUSTOMER_ID    = os.getenv("NAVER_AD_CUSTOMER_ID", "")
NAVER_AD_ACCESS_LICENSE = os.getenv("NAVER_AD_ACCESS_LICENSE", "")
NAVER_AD_SECRET_KEY     = os.getenv("NAVER_AD_SECRET_KEY", "")

# ── 도매꾹 OpenAPI (소싱 상품 수집) ─────────────────────
# 발급: https://openapi.domeggook.com → API Key 관리
DOMEGGOOK_API_KEY = os.getenv("DOMEGGOOK_API_KEY", "")

# ── Claude API (AI SEO 최적화) ───────────────────────────
# 발급: https://console.anthropic.com → API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 네이버 커머스 API (스마트스토어 자동 업로드) ─────────
# 발급: https://developers.naver.com → 앱 등록
NAVER_COMMERCE_CLIENT_ID     = os.getenv("NAVER_COMMERCE_CLIENT_ID", "")
NAVER_COMMERCE_CLIENT_SECRET = os.getenv("NAVER_COMMERCE_CLIENT_SECRET", "")

# ── 쿠팡 WING API (쿠팡 자동 업로드) ────────────────────
# 발급: 쿠팡 Wing → 판매자 정보 → API Key 발급
COUPANG_ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY", "")
COUPANG_SECRET_KEY = os.getenv("COUPANG_SECRET_KEY", "")
COUPANG_VENDOR_ID  = os.getenv("COUPANG_VENDOR_ID", "")

# ── 11번가 OpenAPI (11번가 자동 업로드) ─────────────────
# 발급: 11번가 셀러 오피스 → API 관리
ELEVENTH_API_KEY = os.getenv("ELEVENTH_API_KEY", "")

# ── 설정 확인 함수 ───────────────────────────────────────

def check_api_status():
    """현재 설정된 API 키 상태를 확인합니다."""
    apis = {
        "네이버 검색광고 API": all([NAVER_AD_CUSTOMER_ID, NAVER_AD_ACCESS_LICENSE, NAVER_AD_SECRET_KEY]),
        "도매꾹 API":          bool(DOMEGGOOK_API_KEY),
        "Claude AI API":       bool(ANTHROPIC_API_KEY),
        "스마트스토어 API":     all([NAVER_COMMERCE_CLIENT_ID, NAVER_COMMERCE_CLIENT_SECRET]),
        "쿠팡 WING API":       all([COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY, COUPANG_VENDOR_ID]),
        "11번가 API":           bool(ELEVENTH_API_KEY),
    }

    phase_map = {
        "네이버 검색광고 API": "Phase 2",
        "도매꾹 API":          "Phase 2",
        "Claude AI API":       "Phase 2",
        "스마트스토어 API":     "Phase 3",
        "쿠팡 WING API":       "Phase 3",
        "11번가 API":           "Phase 3",
    }

    print("=" * 50)
    print("  API 설정 상태")
    print("=" * 50)
    for name, configured in apis.items():
        status = "✅ 설정됨" if configured else "❌ 미설정"
        phase = phase_map.get(name, "")
        print(f"  {status}  {name} ({phase})")
    print()


if __name__ == "__main__":
    check_api_status()
