#!/usr/bin/env python3
"""Fetch KR stock prices from Naver mobile API → stock-data.json."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# 시총 상위 위주 (~50)
STOCKS: dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스",
    "005380": "현대차",
    "006400": "삼성SDI",
    "051910": "LG화학",
    "035420": "NAVER",
    "000270": "기아",
    "005490": "POSCO홀딩스",
    "035720": "카카오",
    "068270": "셀트리온",
    "105560": "KB금융",
    "055550": "신한지주",
    "012330": "현대모비스",
    "028260": "삼성물산",
    "066570": "LG전자",
    "003670": "포스코퓨처엠",
    "032830": "삼성생명",
    "086790": "하나금융지주",
    "003550": "LG",
    "017670": "SK텔레콤",
    "034730": "SK",
    "015760": "한국전력",
    "096770": "SK이노베이션",
    "009150": "삼성전기",
    "033780": "KT&G",
    "003490": "대한항공",
    "030200": "KT",
    "010130": "고려아연",
    "011200": "HMM",
    "018260": "삼성에스디에스",
    "316140": "우리금융지주",
    "024110": "기업은행",
    "034020": "두산에너빌리티",
    "009540": "HD한국조선해양",
    "010950": "S-Oil",
    "259960": "크래프톤",
    "352820": "하이브",
    "047810": "한국항공우주",
    "011070": "LG이노텍",
    "036570": "엔씨소프트",
    "251270": "넷마블",
    "090430": "아모레퍼시픽",
    "042700": "한미반도체",
    "138040": "메리츠금융지주",
    "267250": "HD현대",
    "000810": "삼성화재",
    "161390": "한국타이어앤테크놀로지",
    "012450": "한화에어로스페이스",
}

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
OUT = Path(__file__).resolve().parent / "stock-data.json"
TIMEOUT = 15


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_price(s: object) -> int | None:
    if s is None:
        return None
    text = str(s).replace(",", "").replace(" ", "")
    try:
        return int(float(text))
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


def fetch_one(code: str, fallback_name: str) -> dict:
    url = f"https://m.stock.naver.com/api/stock/{code}/basic"
    req = Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        return {"name": fallback_name, "error": str(e), "updated": _now_iso()}

    name = payload.get("stockName") or fallback_name
    price = _parse_price(payload.get("closePrice"))
    change_pct = _parse_pct(payload.get("fluctuationsRatio"))
    updated = payload.get("localTradedAt") or _now_iso()

    if price is None:
        return {
            "name": name,
            "error": "parse_failed: price not found",
            "updated": _now_iso(),
        }

    return {
        "name": name,
        "price": price,
        "change_pct": change_pct if change_pct is not None else 0.0,
        "updated": updated,
    }


def main() -> int:
    results: dict[str, dict] = {}
    ok = 0
    for code, name in STOCKS.items():
        row = fetch_one(code, name)
        results[code] = row
        if "error" in row:
            print(f"[ERR] {code} {name}: {row['error']}", file=sys.stderr)
        else:
            ok += 1
            print(f"[OK]  {code} {row['name']}: {row['price']} ({row['change_pct']}%)")

    payload = {"updated": _now_iso(), "stocks": results}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT} ({ok}/{len(STOCKS)} ok)")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
