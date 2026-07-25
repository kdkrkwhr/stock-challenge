#!/usr/bin/env python3
"""Fetch ALL KR+US listed stocks via Naver marketValue pages → sharded JSON.

Shards under data/ (one file per exchange). stock-data.json is the manifest.
List endpoints already include price/change — no per-symbol /basic calls.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MANIFEST = ROOT / "stock-data.json"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
TIMEOUT = 30
PAGE_SIZE = 100
# ponytail: naive throttle; bump if Actions starts getting 429s
SLEEP_EVERY = 5
SLEEP_SEC = 0.35

# (market, exchange_slug, list_url, shard_relpath)
SOURCES: list[tuple[str, str, str, str]] = [
    (
        "KR",
        "KOSPI",
        "https://m.stock.naver.com/api/stocks/marketValue/KOSPI",
        "data/kospi.json",
    ),
    (
        "KR",
        "KOSDAQ",
        "https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ",
        "data/kosdaq.json",
    ),
    (
        "US",
        "NASDAQ",
        "https://api.stock.naver.com/stock/exchange/NASDAQ/marketValue",
        "data/nasdaq.json",
    ),
    (
        "US",
        "NYSE",
        "https://api.stock.naver.com/stock/exchange/NYSE/marketValue",
        "data/nyse.json",
    ),
    (
        "US",
        "AMEX",
        "https://api.stock.naver.com/stock/exchange/AMEX/marketValue",
        "data/amex.json",
    ),
]


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


def _exchange(payload: dict, fallback: str) -> str:
    ex = payload.get("stockExchangeType")
    if isinstance(ex, dict):
        return ex.get("nameKor") or ex.get("name") or ex.get("nameEng") or fallback
    if isinstance(ex, str) and ex:
        return ex
    return payload.get("stockExchangeName") or fallback


# 재시도 설정 (네이버 429/5xx/타임아웃 같은 일시적 실패 대비)
MAX_ATTEMPTS = 3


def _get_json(url: str) -> dict:
    last_err: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            last_err = e
            # 4xx 클라이언트 오류는 재시도해도 소용없음 — 바로 포기
            if isinstance(e, HTTPError) and e.code in (400, 401, 403, 404):
                break
            if attempt < MAX_ATTEMPTS:
                sleep = SLEEP_SEC * attempt
                print(
                    f"[RETRY] {url} (시도 {attempt} 실패: {e}); {sleep:.1f}s 대기",
                    file=sys.stderr,
                )
                time.sleep(sleep)
    raise last_err


def row_from_list_item(item: dict, market: str, exchange_slug: str) -> tuple[str, dict] | None:
    """Normalize a marketValue list item → (key, row). Skip junk rows."""
    if item.get("stockEndType") and item.get("stockEndType") not in ("stock", "etf", "etn"):
        # keep ETF/ETN too — they're pickable; skip only weird types
        pass

    symbol = (
        item.get("symbolCode")
        or item.get("itemCode")
        or (item.get("reutersCode") or "").split(".")[0]
    )
    if not symbol:
        return None
    symbol = str(symbol).strip()
    if not symbol:
        return None

    # KR keys stay 6-digit codes; US keys stay ticker (TSLA)
    key = str(item.get("itemCode") or symbol).strip()
    if market == "US":
        key = symbol

    name = item.get("stockName") or symbol
    price = _parse_price(item.get("closePrice"))
    change_pct = _parse_pct(item.get("fluctuationsRatio"))
    logo = item.get("itemLogoPngUrl") or item.get("itemLogoUrl")
    updated = item.get("localTradedAt") or _now_iso()

    row: dict = {
        "name": name,
        "name_eng": item.get("stockNameEng"),
        "symbol": symbol,
        "market": market,
        "exchange": _exchange(item, exchange_slug),
        "industry": _industry(item),
        "currency": _currency(item, market),
        "logo": logo,
        "updated": updated,
    }
    if price is None:
        row["error"] = "parse_failed: price not found"
    else:
        row["price"] = price
        row["change_pct"] = change_pct if change_pct is not None else 0.0
    return key, row


def fetch_market(market: str, exchange_slug: str, base_url: str) -> dict[str, dict]:
    results: dict[str, dict] = {}
    page = 1
    total = None
    reqs = 0
    while True:
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}page={page}&pageSize={PAGE_SIZE}"
        try:
            payload = _get_json(url)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            print(f"[ERR] {exchange_slug} page {page}: {e}", file=sys.stderr)
            break

        reqs += 1
        if total is None:
            total = int(payload.get("totalCount") or 0)
            print(f"[{exchange_slug}] totalCount={total}")

        stocks = payload.get("stocks") or []
        if not stocks:
            break

        for item in stocks:
            if not isinstance(item, dict):
                continue
            parsed = row_from_list_item(item, market, exchange_slug)
            if not parsed:
                continue
            key, row = parsed
            results[key] = row

        print(f"[{exchange_slug}] page {page}: +{len(stocks)} (acc {len(results)})")

        if total and len(results) >= total:
            break
        if len(stocks) < PAGE_SIZE:
            break
        page += 1
        if reqs % SLEEP_EVERY == 0:
            time.sleep(SLEEP_SEC)

    return results


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shards_meta: list[dict] = []
    grand_ok = 0
    grand_n = 0

    for market, exchange_slug, url, rel in SOURCES:
        stocks = fetch_market(market, exchange_slug, url)
        ok = sum(1 for r in stocks.values() if "error" not in r)
        grand_ok += ok
        grand_n += len(stocks)

        out = ROOT / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated": _now_iso(),
            "market": market,
            "exchange": exchange_slug,
            "count": len(stocks),
            "stocks": stocks,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        size_kb = out.stat().st_size / 1024
        print(f"Wrote {out} ({ok}/{len(stocks)} ok, {size_kb:.0f} KB)")
        shards_meta.append(
            {
                "path": rel.replace("\\", "/"),
                "market": market,
                "exchange": exchange_slug,
                "count": len(stocks),
            }
        )

    manifest = {
        "updated": _now_iso(),
        "count": grand_n,
        "ok": grand_ok,
        "shards": shards_meta,
        # empty — prices live in shards; kept for old clients that expect .stocks
        "stocks": {},
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nManifest {MANIFEST} — {grand_ok}/{grand_n} ok across {len(shards_meta)} shards")
    return 0 if grand_ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
