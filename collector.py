from __future__ import annotations

from datetime import date
from typing import Any

import requests
from bs4 import BeautifulSoup


TOUR_API_FESTIVAL_URL = "https://apis.data.go.kr/B551011/KorService2/searchFestival2"
VISITKOREA_FESTIVAL_URL = "https://korean.visitkorea.or.kr/kfes/list/wntyFstvlList.do"


REGION_NAME_TO_ID = {
    "서울": 1,
    "부산": 2,
    "경주": 3,
    "제주": 4,
    "강릉": 5,
}


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_from_yyyymmdd(value: Any) -> str | None:
    text = _safe_text(value)
    if not text or len(text) != 8:
        return None
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


def fetch_tourapi_festivals(service_key: str, limit: int = 20) -> list[dict[str, Any]]:
    params = {
        "serviceKey": service_key,
        "MobileOS": "ETC",
        "MobileApp": "TravelCourseStreamlit",
        "_type": "json",
        "eventStartDate": date.today().strftime("%Y%m%d"),
        "numOfRows": limit,
        "pageNo": 1,
        "arrange": "A",
    }
    response = requests.get(TOUR_API_FESTIVAL_URL, params=params, timeout=8)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]

    festivals: list[dict[str, Any]] = []
    for item in items[:limit]:
        addr = _safe_text(item.get("addr1")) or ""
        region_id = 1
        for region_name, mapped_id in REGION_NAME_TO_ID.items():
            if region_name in addr:
                region_id = mapped_id
                break
        festivals.append(
            {
                "region_id": region_id,
                "festival_name": _safe_text(item.get("title")) or "이름 미상 축제",
                "start_date": _date_from_yyyymmdd(item.get("eventstartdate")),
                "end_date": _date_from_yyyymmdd(item.get("eventenddate")),
                "fee_info": None,
                "homepage": None,
                "overview": addr or "한국관광공사 TourAPI에서 수집한 축제 정보입니다.",
                "source_url": _safe_text(item.get("firstimage")) or TOUR_API_FESTIVAL_URL,
                "external_id": _safe_text(item.get("contentid")),
            }
        )
    return festivals


def crawl_visitkorea_festival_titles(limit: int = 10) -> list[dict[str, Any]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        )
    }
    response = requests.get(VISITKOREA_FESTIVAL_URL, headers=headers, timeout=8)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    candidates = soup.select(".tit, .title, [class*=title], [class*=tit]")

    seen: set[str] = set()
    festivals: list[dict[str, Any]] = []
    for node in candidates:
        title = node.get_text(" ", strip=True)
        if len(title) < 3 or title in seen:
            continue
        seen.add(title)
        festivals.append(
            {
                "region_id": 1,
                "festival_name": title[:150],
                "start_date": None,
                "end_date": None,
                "fee_info": None,
                "homepage": VISITKOREA_FESTIVAL_URL,
                "overview": "대한민국 구석구석 축제 페이지에서 HTML 크롤링으로 수집한 제목 후보입니다.",
                "source_url": VISITKOREA_FESTIVAL_URL,
                "external_id": None,
            }
        )
        if len(festivals) >= limit:
            break
    return festivals


def fallback_places() -> list[dict[str, Any]]:
    return [
        {
            "region_id": 1,
            "place_name": "서울숲",
            "address": "서울 성동구 뚝섬로 273",
            "overview": "도심 속 산책과 피크닉을 즐기기 좋은 자연형 공원입니다.",
            "phone": None,
            "latitude": 37.544388,
            "longitude": 127.037442,
            "source_url": "fallback",
            "external_id": "fallback-seoul-forest",
        },
        {
            "region_id": 2,
            "place_name": "광안리해수욕장",
            "address": "부산 수영구 광안해변로",
            "overview": "광안대교 야경과 해변 산책으로 유명한 부산 대표 명소입니다.",
            "phone": None,
            "latitude": 35.153169,
            "longitude": 129.118666,
            "source_url": "fallback",
            "external_id": "fallback-gwangalli",
        },
        {
            "region_id": 3,
            "place_name": "첨성대",
            "address": "경북 경주시 인왕동 839-1",
            "overview": "신라 시대 천문 관측 유적으로 경주 역사 코스의 핵심 장소입니다.",
            "phone": None,
            "latitude": 35.834722,
            "longitude": 129.219167,
            "source_url": "fallback",
            "external_id": "fallback-cheomseongdae",
        },
    ]


def fallback_festivals() -> list[dict[str, Any]]:
    return [
        {
            "region_id": 1,
            "festival_name": "한강 여름 야시장",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "fee_info": "무료",
            "homepage": None,
            "overview": "야간 관광과 미식 코스를 결합하기 좋은 샘플 축제 데이터입니다.",
            "source_url": "fallback",
            "external_id": "fallback-hangang-night",
        },
        {
            "region_id": 3,
            "festival_name": "경주 문화유산 야행",
            "start_date": "2026-09-12",
            "end_date": "2026-09-14",
            "fee_info": "무료",
            "homepage": None,
            "overview": "역사 유적과 야간 콘텐츠를 결합한 샘플 축제 데이터입니다.",
            "source_url": "fallback",
            "external_id": "fallback-gyeongju-night",
        },
    ]


def collect_festival_data(service_key: str | None = None, limit: int = 20) -> tuple[list[dict[str, Any]], str, str]:
    if service_key:
        try:
            festivals = fetch_tourapi_festivals(service_key, limit)
            if festivals:
                return festivals, "SUCCESS", "TourAPI 축제 데이터를 수집했습니다."
        except Exception as exc:
            return fallback_festivals(), "FALLBACK", f"TourAPI 호출 실패로 샘플 축제를 사용했습니다: {exc}"

    try:
        festivals = crawl_visitkorea_festival_titles(min(limit, 10))
        if festivals:
            return festivals, "SUCCESS", "HTML 크롤링으로 축제 제목 후보를 수집했습니다."
    except Exception as exc:
        return fallback_festivals(), "FALLBACK", f"HTML 크롤링 실패로 샘플 축제를 사용했습니다: {exc}"

    return fallback_festivals(), "FALLBACK", "수집된 축제 데이터가 없어 샘플 데이터를 사용했습니다."
