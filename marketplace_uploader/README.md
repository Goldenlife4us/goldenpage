# 마켓플레이스 채널별 업로드 파일 생성기

한국 오픈마켓(스마트스토어, 쿠팡, 11번가) 멀티채널 판매를 위한 도구입니다.  
`master_products.xlsx` 파일 하나로 각 채널에 맞는 업로드 파일을 자동으로 만들어 줍니다.

---

## 폴더 구조

```
marketplace_uploader/
├── README.md                ← 지금 읽고 있는 설명서
├── requirements.txt         ← 필요한 라이브러리 목록
├── create_sample.py         ← 샘플 마스터 파일 생성 (처음에 1번만 실행)
├── generate_channels.py     ← 메인 실행 파일
├── config/
│   └── channel_config.py   ← 채널별 수수료, 카테고리 설정
├── processors/
│   ├── margin_calculator.py ← 마진 계산 로직
│   ├── smartstore.py        ← 스마트스토어 변환
│   ├── coupang.py           ← 쿠팡 변환
│   └── eleventh.py          ← 11번가 변환
├── data/
│   └── master_products.xlsx ← 입력 파일 (여기에 상품 정보 입력)
└── output/
    ├── channel_smartstore.xlsx
    ├── channel_coupang.xlsx
    └── channel_11st.xlsx
```

---

## 처음 설치하기

### 1단계: Python 설치 확인

터미널(명령 프롬프트)을 열고 아래를 입력하세요:

```bash
python --version
```

`Python 3.8` 이상이 나오면 됩니다. 없으면 https://python.org 에서 설치하세요.

### 2단계: 이 폴더로 이동

```bash
cd marketplace_uploader
```

### 3단계: 필요한 라이브러리 설치

```bash
pip install -r requirements.txt
```

---

## 사용 방법

### STEP 1: 샘플 파일 생성 (처음 1번만)

```bash
python create_sample.py
```

실행하면 `data/master_products.xlsx` 파일이 만들어집니다.  
이 파일을 열어서 내 상품 정보를 입력하세요.

### STEP 2: 채널별 파일 생성

```bash
python generate_channels.py
```

실행하면 `output/` 폴더에 3개의 파일이 만들어집니다:
- `channel_smartstore.xlsx` - 스마트스토어 업로드용
- `channel_coupang.xlsx` - 쿠팡 업로드용
- `channel_11st.xlsx` - 11번가 업로드용

---

## 옵션 기능

### 특정 채널만 생성하기

```bash
# 스마트스토어만 생성
python generate_channels.py --channel smartstore

# 쿠팡과 11번가만 생성
python generate_channels.py --channel coupang 11st
```

### 다른 이름의 마스터 파일 사용하기

```bash
python generate_channels.py --input 내상품목록.xlsx
```

---

## master_products.xlsx 컬럼 설명

엑셀 파일을 직접 편집할 때 참고하세요:

| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| 상품코드 | 내부 관리용 고유 번호 | PRD-001 |
| 상품명 | 기본 상품명 | 프리미엄 텀블러 500ml |
| 카테고리 | 상품 분류 | 주방용품 |
| 원가 | 매입가 (마진 계산 기준) | 8500 |
| 기본판매가 | 채널 전용가 없을 때 사용 | 22000 |
| 스마트스토어_판매가 | 스마트스토어 전용 판매가 | 22000 |
| 쿠팡_판매가 | 쿠팡 전용 판매가 | 23000 |
| 11번가_판매가 | 11번가 전용 판매가 | 23500 |
| 스마트스토어_상품명 | 스마트스토어 전용 상품명 | 프리미엄 텀블러 보온보냉 |
| 쿠팡_상품명 | 쿠팡 전용 상품명 | [무료배송] 프리미엄 텀블러 |
| 11번가_상품명 | 11번가 전용 상품명 | 프리미엄 텀블러 보온12시간 |
| 브랜드 | 브랜드명 | 골든라이프 |
| 제조사 | 제조사명 | (주)골든라이프 |
| 원산지 | 원산지 | 국내산 |
| 재고수량 | 현재 재고 수 | 150 |
| 옵션명 | 옵션 종류 | 색상 |
| 옵션값 | 옵션 목록 (쉼표 구분) | 블랙,실버,화이트 |
| 소재 | 상품 소재 | 스테인리스 스틸 |
| 색상 | 색상 정보 | 블랙/실버 |
| 크기 | 크기/사이즈 | 높이 22cm |

### 사용 가능한 카테고리 목록

- 생활용품
- 주방용품
- 식품
- 의류
- 전자제품
- 뷰티
- 스포츠
- 완구
- 기타

> 다른 카테고리를 추가하려면 `config/channel_config.py`를 수정하세요.

---

## 마진 계산 방식

```
순이익 = 판매가 - 원가 - 채널수수료
마진율 = 순이익 / 판매가 × 100
```

### 채널별 기본 수수료율

| 채널 | 수수료율 |
|------|---------|
| 스마트스토어 | 5.9% |
| 쿠팡 | 10.8% |
| 11번가 | 12.0% |

> 실제 수수료는 카테고리에 따라 다릅니다. `config/channel_config.py`에서 수정하세요.

### 마진율 경고

- 마진율이 **10% 미만**인 상품은 실행 시 경고 메시지가 표시됩니다.

---

## 자주 묻는 질문

**Q: `ModuleNotFoundError` 오류가 나요**  
A: `pip install -r requirements.txt`를 먼저 실행하세요.

**Q: `FileNotFoundError` 오류가 나요**  
A: `python create_sample.py`를 먼저 실행하여 샘플 파일을 만드세요.

**Q: 카테고리 코드를 실제 코드로 바꾸고 싶어요**  
A: `config/channel_config.py` 파일의 카테고리 맵을 수정하세요.

**Q: 수수료율을 실제 내 카테고리에 맞게 바꾸고 싶어요**  
A: `config/channel_config.py`의 `CHANNEL_FEE_RATE` 값을 수정하세요.

---

## 앞으로 추가 예정 기능

- [ ] 실제 플랫폼 API 연동 (자동 업로드)
- [ ] 웹 인터페이스 (Streamlit)
- [ ] 상품 이미지 자동 리사이징
- [ ] 판매 데이터 분석 리포트

---

*이 도구는 오픈마켓 API를 직접 호출하지 않습니다. 엑셀 파일 생성 후 각 플랫폼 셀러 센터에서 수동으로 업로드하세요.*
