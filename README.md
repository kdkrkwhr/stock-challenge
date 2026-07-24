# 스톡챌린지

개인용 주식 등락률 모니터링 (GitHub Pages).

## URL

https://kdkrkwhr.github.io/stock-challenge/

## 구조

- `index.html` — 다크 테마 UI, localStorage 픽 저장
- `fetch_stocks.py` — 네이버 금융 크롤링 (stdlib만)
- `stock-data.json` — Actions가 10분마다 갱신
- `.github/workflows/stock.yml` — 평일 장중 cron + 수동 실행

## 로컬

```bash
python fetch_stocks.py
# index.html 을 브라우저로 열기
```
