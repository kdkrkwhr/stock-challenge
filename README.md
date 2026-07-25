# 스톡챌린지

개인용 주식 등락률 모니터링 (GitHub Pages + PWA). KR + US(테슬라 등).

## URL

https://kdkrkwhr.github.io/stock-challenge/

## 기능

- 첫 방문 닉네임만 (가입 없음, localStorage)
- 내 종목 등락률 랭킹바 + 스파크라인(간단 차트, 로컬 이력)
- US/KR 필터 탭
- 오늘 최고·최저 등락 하이라이트 (상단 hl 바)
- 챌린지 스코어: 내 픽 평균 등락률 (헤더 표시)
- 회사 정보: 이름/영문/시장/거래소/산업/로고/통화
- 웹에서 **크롬 앱 설치(다운로드)** 버튼 (standalone에선 숨김)
- 친구 픽 공유: 내 종목을 코드로 복사해 공유/가져오기 (로컬, base64)
- 등락률 알림 임계치: 설정한 ±N% 넘는 픽에 🔔 배지 (기본 ±5%)
- 즐겨찾기(★): 픽 카드별 별표, 탭으로 즐찾만 필터, 정렬 시 상단 고정 (로컬)
- 챌린지 스코어보드: 친구 공유코드로 참가자 추가 → 닉네임별 합산 등락 랭킹 (로컬)
- 다크/라이트 테마 토글: 헤더 🌙/☀️ 버튼, 선택 localStorage 저장
- 오프라인 안내 문구 + 새 버전 업데이트 배너 (PWA SW)
- 헤더 🔄 버튼으로 시세 수동 새로고침 (자동 10분 외 즉시 반영)

## 구조

- `index.html` — UI / PWA 설치
- `manifest.json` · `sw.js` · `icon-*.png` — 크롬 앱
- `fetch_stocks.py` — 네이버 금융 (KR + US)
- `stock-data.json` — Actions 10분마다 갱신
- `.github/workflows/stock.yml` — 평일 장중 cron

## 로컬

```bash
python fetch_stocks.py
# index.html 브라우저로 열기 (PWA 설치는 https/Pages에서)
```
