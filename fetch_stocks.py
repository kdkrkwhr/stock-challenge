#!/usr/bin/env python3
"""Fetch KR + US stock prices from Naver → stock-data.json (full company info)."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# (code, name, market) — market: KR | US
# KR: 6-digit KRX code via m.stock.naver.com
# US: Naver reutersCode e.g. TSLA.O via api.stock.naver.com
STOCKS: list[tuple[str, str, str]] = [
    # KR — 시총/인기
    ("005930", "삼성전자", "KR"),
    ("000660", "SK하이닉스", "KR"),
    ("373220", "LG에너지솔루션", "KR"),
    ("207940", "삼성바이오로직스", "KR"),
    ("005380", "현대차", "KR"),
    ("006400", "삼성SDI", "KR"),
    ("051910", "LG화학", "KR"),
    ("035420", "NAVER", "KR"),
    ("000270", "기아", "KR"),
    ("005490", "POSCO홀딩스", "KR"),
    ("035720", "카카오", "KR"),
    ("068270", "셀트리온", "KR"),
    ("105560", "KB금융", "KR"),
    ("055550", "신한지주", "KR"),
    ("012330", "현대모비스", "KR"),
    ("028260", "삼성물산", "KR"),
    ("066570", "LG전자", "KR"),
    ("003670", "포스코퓨처엠", "KR"),
    ("032830", "삼성생명", "KR"),
    ("086790", "하나금융지주", "KR"),
    ("003550", "LG", "KR"),
    ("017670", "SK텔레콤", "KR"),
    ("034730", "SK", "KR"),
    ("015760", "한국전력", "KR"),
    ("096770", "SK이노베이션", "KR"),
    ("009150", "삼성전기", "KR"),
    ("033780", "KT&G", "KR"),
    ("003490", "대한항공", "KR"),
    ("030200", "KT", "KR"),
    ("010130", "고려아연", "KR"),
    ("011200", "HMM", "KR"),
    ("018260", "삼성에스디에스", "KR"),
    ("316140", "우리금융지주", "KR"),
    ("024110", "기업은행", "KR"),
    ("034020", "두산에너빌리티", "KR"),
    ("009540", "HD한국조선해양", "KR"),
    ("010950", "S-Oil", "KR"),
    ("259960", "크래프톤", "KR"),
    ("352820", "하이브", "KR"),
    ("047810", "한국항공우주", "KR"),
    ("011070", "LG이노텍", "KR"),
    ("036570", "엔씨소프트", "KR"),
    ("251270", "넷마블", "KR"),
    ("090430", "아모레퍼시픽", "KR"),
    ("042700", "한미반도체", "KR"),
    ("138040", "메리츠금융지주", "KR"),
    ("267250", "HD현대", "KR"),
    ("000810", "삼성화재", "KR"),
    ("161390", "한국타이어앤테크놀로지", "KR"),
    ("012450", "한화에어로스페이스", "KR"),
    # US — 나스닥/대표
    ("TSLA.O", "테슬라", "US"),
    ("AAPL.O", "애플", "US"),
    ("NVDA.O", "엔비디아", "US"),
    ("MSFT.O", "마이크로소프트", "US"),
    ("AMZN.O", "아마존", "US"),
    ("GOOGL.O", "알파벳A", "US"),
    ("META.O", "메타", "US"),
    ("NFLX.O", "넷플릭스", "US"),
    ("AMD.O", "AMD", "US"),
    ("INTC.O", "인텔", "US"),
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
OUT = Path(__file__).resolve().parent / "stock-data.json"
TIMEOUT = 15


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_price(s: object) -> float | None:
    if s is None:
        return None
    text = str(s).replace(",", "").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_pct(s: object) -> float | None:
    if s is None:
        return None
    text = str(s).replace("%", "").replace(",", "").replace("+", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _currency(payload: dict, market: str) -> str:
    ct = payload.get("currencyType")
    if isinstance(ct, dict) and ct.get("code"):
        return str(ct["code"])
    if isinstance(ct, str) and ct:
        return ct
    return "USD" if market == "US" else "KRW"


def _industry(payload: dict) -> str | None:
    ind = payload.get("industryCodeType")
    if isinstance(ind, dict):
        return ind.get("industryGroupKor") or ind.get("name")
    return None


def _exchange(payload: dict) -> str | None:
    ex = payload.get("stockExchangeType")
    if isinstance(ex, dict):
        return ex.get("nameKor") or ex.get("name") or ex.get("nameEng")
    return payload.get("stockExchangeName")


def fetch_one(code: str, fallback_name: str, market: str) -> dict:
    if market == "US":
        url = f"https://api.stock.naver.com/stock/{code}/basic"
    else:
        url = f"https://m.stock.naver.com/api/stock/{code}/basic"

    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        return {
            "name": fallback_name,
            "name_eng": None,
            "symbol": code.split(".")[0],
            "market": market,
            "exchange": None,
            "industry": None,
            "currency": "USD" if market == "US" else "KRW",
            "logo": None,
            "error": str(e),
            "updated": _now_iso(),
        }

    name = payload.get("stockName") or fallback_name
    name_eng = payload.get("stockNameEng")
    symbol = payload.get("symbolCode") or code.split(".")[0]
    price = _parse_price(payload.get("closePrice"))
    change_pct = _parse_pct(payload.get("fluctuationsRatio"))
    updated = payload.get("localTradedAt") or _now_iso()
    logo = payload.get("itemLogoPngUrl") or payload.get("itemLogoUrl")

    base = {
        "name": name,
        "name_eng": name_eng,
        "symbol": symbol,
        "market": market,
        "exchange": _exchange(payload),
        "industry": _industry(payload),
        "currency": _currency(payload, market),
        "logo": logo,
        "updated": updated,
    }

    if price is None:
        return {**base, "error": "parse_failed: price not found", "updated": _now_iso()}

    return {
        **base,
        "price": price,
        "change_pct": change_pct if change_pct is not None else 0.0,
    }


def main() -> int:
    results: dict[str, dict] = {}
    ok = 0
    for i, (code, name, market) in enumerate(STOCKS):
        if i and i % 8 == 0:
            time.sleep(0.4)  # ponytail: naive throttle so Actions doesn't trip rate limits
        row = fetch_one(code, name, market)
        # key: KR=6digit, US=symbol (TSLA) so search/UI stays clean
        key = row.get("symbol") or code.split(".")[0]
        results[key] = row
        if "error" in row:
            print(f"[ERR] {key} {name}: {row['error']}", file=sys.stderr)
        else:
            ok += 1
            cur = row.get("currency") or ""
            print(f"[OK]  {key} {row['name']}: {row['price']} {cur} ({row['change_pct']}%)")

    payload = {
        "updated": _now_iso(),
        "count": len(results),
        "stocks": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT} ({ok}/{len(STOCKS)} ok)")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
