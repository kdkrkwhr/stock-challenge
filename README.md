# 스톡챌린지

개인용 주식 등락률 모니터 (GitHub Pages). KR + US(테슬라 등).

## URL

https://kdkrkwhr.github.io/stock-challenge/

## 기능

- 첫 방문 닉네임만 (가입 없음, localStorage)
- 픽 종목 등락률 랭킹바
- 회사 정보: 이름/영문/시장/거래소/산업/로고/통화

## 구조

- `index.html` — UI
- `fetch_stocks.py` — 네이버 금융 (KR + US)
- `stock-data.json` — Actions 10분마다 갱신
- `.github/workflows/stock.yml` — 평일 장중 cron

## 로컬

```bash
python fetch_stocks.py
# index.html 브라우저로 열기
```
