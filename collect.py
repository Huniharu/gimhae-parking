"""김해공항 주차장 잔여석 수집기 (GitHub Actions에서 매시간 실행)

한국공항공사_전국공항 실시간 주차정보_GW API를 호출해
김해공항(PUS) 주차장별 잔여면수를 data/gimhae_parking.csv에 한 줄씩 추가한다.
서비스키는 환경변수 DATA_GO_KR_KEY(GitHub Secrets)로만 받는다.
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

KST = timezone(timedelta(hours=9))
END_DATE = datetime(2026, 10, 30, 23, 59, tzinfo=KST)  # 수집 종료 시각

# 한국공항공사 전국공항 실시간 주차정보 GW 활용가이드(2026-08-11 제정) 기준
ENDPOINTS = ["https://apis.data.go.kr/B551178/parking-realtime-status/info"]
AIRPORT = "PUS"  # 김해국제공항

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "gimhae_parking.csv"
RAW_DIR = ROOT / "data" / "raw"
FIELDS = ["collected_at_kst", "lot", "available", "total", "occupied", "source_time"]


def pick(item, *keys):
    """여러 후보 필드명 중 처음으로 값이 있는 것을 반환 (API 필드명 변경 대비)."""
    lower = {k.lower(): v for k, v in item.items()}
    for k in keys:
        v = lower.get(k.lower())
        if v not in (None, ""):
            return v
    return None


def to_int(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def extract_items(payload):
    """data.go.kr 표준 응답(response.body.items.item) 및 변형 구조에서 항목 리스트 추출."""
    node = payload
    for key in ("response", "body", "items", "item"):
        if isinstance(node, dict) and key in node:
            node = node[key]
    if isinstance(node, dict):
        node = [node]
    if not isinstance(node, list):
        # 다른 구조일 경우 dict 안의 첫 리스트를 찾는다
        stack = [payload]
        while stack:
            cur = stack.pop()
            if isinstance(cur, list) and cur and isinstance(cur[0], dict):
                return cur
            if isinstance(cur, dict):
                stack.extend(cur.values())
        return []
    return node


def fetch(key):
    params = {"serviceKey": key, "schAirportCode": AIRPORT, "type": "json",
              "numOfRows": 100, "pageNo": 1}
    last_err = None
    for url in ENDPOINTS:
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # 다음 엔드포인트 시도
            last_err = f"{url}: {e}"
    raise RuntimeError(f"API 호출 실패 - {last_err}")


def main():
    now = datetime.now(KST)
    if now > END_DATE:
        print("수집 기간(10/30) 종료 - 아무것도 하지 않음")
        return

    key = os.environ.get("DATA_GO_KR_KEY")
    if not key:
        sys.exit("환경변수 DATA_GO_KR_KEY가 없습니다 (GitHub Secrets 확인)")

    payload = fetch(key)
    header = payload.get("response", {}).get("header", {}) if isinstance(payload, dict) else {}
    if header and str(header.get("resultCode")) not in ("00", "0"):
        sys.exit(f"API 오류: {header.get('resultCode')} {header.get('resultMsg')}")

    # 원본 응답도 날짜별로 보관 (필드 해석 문제 생겨도 나중에 복구 가능)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAW_DIR / f"{now:%Y%m%d}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": now.isoformat(), "payload": payload}, ensure_ascii=False) + "\n")

    rows = []
    for it in extract_items(payload):
        airport = str(pick(it, "aprKor", "aprEng", "airportKor", "airportEng") or "")
        if airport and not any(s in airport for s in ("김해", "PUS", "Gimhae", "GIMHAE")):
            continue
        lot = pick(it, "parkingAirportCodeName", "parkingLotName", "parkingName",
                   "parkName", "prkplceNm", "lotName", "name")
        total = to_int(pick(it, "parkingFullSpace", "parkingTotalSpace", "totalSpace"))
        occupied = to_int(pick(it, "parkingIstay", "parkingOccupiedSpace", "occupiedSpace"))
        available = to_int(pick(it, "parkingAvailableSpace", "availableSpace",
                                "parkingPossibleSpace", "remainSpace", "emptyCnt",
                                "available"))
        if available is None and total is not None and occupied is not None:
            available = total - occupied
        src_time = " ".join(str(x) for x in (pick(it, "parkingGetdate", "sysGetdate"),
                                               pick(it, "parkingGettime", "sysGettime")) if x)
        rows.append({
            "collected_at_kst": now.strftime("%Y-%m-%d %H:%M"),
            "lot": lot or "UNKNOWN",
            "available": available,
            "total": total,
            "occupied": occupied,
            "source_time": src_time,
        })

    if not rows:
        sys.exit("김해공항 주차장 항목을 찾지 못했습니다. data/raw의 원본 응답을 확인하세요.")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)

    for r in rows:
        print(f"{r['collected_at_kst']}  {r['lot']}: 잔여 {r['available']} / 전체 {r['total']}")


if __name__ == "__main__":
    main()
