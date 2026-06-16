# 혼자살림

1인 가구를 위한 소형가전·생활용품 비교 가이드 블로그. Astro로 만든 정적 사이트이며,
쿠팡파트너스 + 구글 애드센스로 수익화하는 것을 목표로 합니다.

## 구조

```text
src/
├── content/blog/      # 글(Markdown). 새 글을 추가하면 frontmatter 스키마는
│                       # src/content.config.ts 참고
├── layouts/Layout.astro
└── pages/              # index, blog/[...id], about, disclosure
```

## 로컬 실행

```sh
npm install
npm run dev       # http://localhost:4321/goldenpage/
npm run build     # ./dist 에 정적 빌드
```

## 자동화

- `.github/workflows/deploy.yml` — `main` 브랜치에 push되면 GitHub Pages로 자동 배포
- `.github/workflows/weekly-content.yml` — 매주 월요일, 기존 글과 중복되지 않는 새 글을
  자동으로 작성해서 `main`에 직접 커밋·푸시 (Claude Code Action 사용)

## 시작 전에 사용자가 직접 해야 하는 일 ("큰 결정")

아래는 본인 명의/결제가 필요해서 대행할 수 없는 항목입니다. 사이트 자체는 이미
무료로 동작하니, 아래는 실제로 수익화·자동화를 켜기 전에 처리하면 됩니다.

1. **GitHub Pages 활성화**: 저장소 Settings → Pages → Source를 "GitHub Actions"로 설정
2. **`ANTHROPIC_API_KEY` 시크릿 등록**: 주간 자동 글쓰기를 켜려면 Settings → Secrets and
   variables → Actions에 등록 (안 하면 `weekly-content.yml`은 그냥 실패하고 사이트엔
   영향 없음)
3. **쿠팡파트너스 가입**: 승인 후 발급되는 제휴 링크로 각 글의
   `(쿠팡파트너스 링크 연결 예정...)` placeholder를 교체
4. **구글 애드센스 가입 및 승인**: 승인 후 광고 스니펫을 `Layout.astro`에 추가
5. **(선택) 커스텀 도메인 구매**: 연결 후 `astro.config.mjs`의 `site`/`base` 값을
   업데이트해야 함 (현재는 `https://goldenlife4us.github.io/goldenpage/` 기준)

## 예산 메모

월 10만원 예산 기준: 커스텀 도메인(연 1~2만원 수준) + 주간 자동 글쓰기 API 비용
(글 1편당 수십~백여 원 수준, 빈도는 `weekly-content.yml`의 cron으로 조절 가능)
정도면 충분히 여유 있게 운영 가능합니다.
