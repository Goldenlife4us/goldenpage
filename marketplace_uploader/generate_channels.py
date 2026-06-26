#!/usr/bin/env python3
# ============================================================
# 메인 실행 파일 - 채널별 업로드 파일 생성기
#
# 사용법:
#   python generate_channels.py
#   python generate_channels.py --input data/master_products.xlsx
#   python generate_channels.py --channel smartstore
#   python generate_channels.py --channel coupang --channel 11st
#
# 처음 실행한다면: python create_sample.py 를 먼저 실행하세요
# ============================================================

import os
import sys
import argparse
import pandas as pd
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가 (상대 임포트 해결)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processors.smartstore import transform_to_smartstore
from processors.coupang import transform_to_coupang
from processors.eleventh import transform_to_eleventh


def parse_args():
    """커맨드라인 인자를 파싱합니다."""
    parser = argparse.ArgumentParser(
        description="마스터 상품 파일을 채널별 업로드 파일로 변환합니다",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python generate_channels.py                          # 모든 채널 생성
  python generate_channels.py --channel smartstore     # 스마트스토어만
  python generate_channels.py --channel coupang 11st   # 쿠팡, 11번가만
  python generate_channels.py --input 내상품목록.xlsx  # 다른 입력 파일 사용
        """,
    )
    parser.add_argument(
        "--input",
        default="data/master_products.xlsx",
        help="마스터 상품 파일 경로 (기본값: data/master_products.xlsx)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="출력 폴더 경로 (기본값: output)",
    )
    parser.add_argument(
        "--channel",
        nargs="+",
        choices=["smartstore", "coupang", "11st"],
        default=["smartstore", "coupang", "11st"],
        help="생성할 채널 선택 (기본값: 모두)",
    )
    return parser.parse_args()


def load_master_file(file_path: str) -> pd.DataFrame:
    """마스터 상품 엑셀 파일을 읽어 DataFrame으로 반환합니다."""
    if not os.path.exists(file_path):
        print(f"[오류] 파일을 찾을 수 없습니다: {file_path}")
        print("  → python create_sample.py 를 먼저 실행하여 샘플 파일을 만드세요")
        sys.exit(1)

    print(f"마스터 파일 로딩 중: {file_path}")
    df = pd.read_excel(file_path)

    # 빈 행 제거
    df = df.dropna(subset=["상품코드"])
    df = df.reset_index(drop=True)

    print(f"  → 상품 {len(df)}개 로딩 완료")
    return df


def save_channel_file(df: pd.DataFrame, output_dir: str, channel: str) -> str:
    """채널별 DataFrame을 엑셀 파일로 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)

    # 채널명 → 파일명 매핑
    filename_map = {
        "smartstore": "channel_smartstore.xlsx",
        "coupang":    "channel_coupang.xlsx",
        "11st":       "channel_11st.xlsx",
    }
    filename = filename_map.get(channel, f"channel_{channel}.xlsx")
    output_path = os.path.join(output_dir, filename)

    # 엑셀로 저장 (컬럼 너비 자동 조정)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="상품목록")

        # 컬럼 너비를 내용에 맞게 자동 조정
        worksheet = writer.sheets["상품목록"]
        for col_idx, col in enumerate(df.columns, 1):
            # 헤더와 데이터 중 가장 긴 문자열 기준으로 너비 설정
            max_len = len(str(col))
            for val in df[col]:
                max_len = max(max_len, len(str(val)))
            # 한글은 2바이트이므로 실제 픽셀 너비를 맞추기 위해 조정
            adjusted_width = min(max_len * 1.5 + 2, 50)
            worksheet.column_dimensions[
                worksheet.cell(1, col_idx).column_letter
            ].width = adjusted_width

    return output_path


def print_summary(df: pd.DataFrame, channel: str, output_path: str):
    """생성된 파일의 요약 정보를 출력합니다."""
    channel_name_map = {
        "smartstore": "스마트스토어",
        "coupang":    "쿠팡",
        "11st":       "11번가",
    }
    channel_name = channel_name_map.get(channel, channel)

    avg_margin = df["마진율(%)"].mean()
    total_profit = df["순이익(원)"].sum()
    min_margin = df["마진율(%)"].min()
    max_margin = df["마진율(%)"].max()

    print(f"\n[{channel_name}] 생성 완료 → {output_path}")
    print(f"  상품 수     : {len(df)}개")
    print(f"  평균 마진율 : {avg_margin:.1f}%")
    print(f"  마진율 범위 : {min_margin:.1f}% ~ {max_margin:.1f}%")
    print(f"  총 예상 순이익 (전체 재고 판매 시): {total_profit:,.0f}원")

    # 마진율이 낮은 상품 경고 (10% 미만)
    low_margin = df[df["마진율(%)"] < 10]
    if not low_margin.empty:
        print(f"  ⚠ 마진율 10% 미만 상품: {len(low_margin)}개")
        for _, row in low_margin.iterrows():
            print(f"     - {row['상품명']} ({row['마진율(%)']:.1f}%)")


def main():
    """메인 실행 함수"""
    args = parse_args()

    print("=" * 60)
    print("  마켓플레이스 채널별 업로드 파일 생성기")
    print(f"  실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 마스터 파일 로딩
    master_df = load_master_file(args.input)

    # 채널별 처리 함수 매핑
    channel_processors = {
        "smartstore": transform_to_smartstore,
        "coupang":    transform_to_coupang,
        "11st":       transform_to_eleventh,
    }

    generated_files = []

    # 선택된 채널에 대해 변환 및 저장
    for channel in args.channel:
        print(f"\n처리 중: {channel} ...")
        processor = channel_processors[channel]

        # 변환
        channel_df = processor(master_df)

        # 저장
        output_path = save_channel_file(channel_df, args.output_dir, channel)
        generated_files.append(output_path)

        # 요약 출력
        print_summary(channel_df, channel, output_path)

    # 최종 결과 요약
    print("\n" + "=" * 60)
    print("모든 파일 생성 완료!")
    print(f"출력 폴더: {os.path.abspath(args.output_dir)}")
    for f in generated_files:
        size_kb = os.path.getsize(f) // 1024
        print(f"  - {os.path.basename(f)} ({size_kb}KB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
