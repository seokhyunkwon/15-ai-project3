from __future__ import annotations

from datetime import date
import os
from typing import Any
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup


TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
TOUR_API_FESTIVAL_URL = "https://apis.data.go.kr/B551011/KorService2/searchFestival2"
TOUR_API_AREA_BASED_URL = f"{TOUR_API_BASE_URL}/areaBasedList2"
VISITKOREA_FESTIVAL_URL = "https://korean.visitkorea.or.kr/kfes/list/wntyFstvlList.do"


REGION_NAME_TO_ID = {
    "서울": 1,
    "부산": 2,
    "경주": 3,
    "제주": 4,
    "강릉": 5,
}

TOURAPI_REGION_CODES = {
    1: {"areaCode": "1"},
    2: {"areaCode": "6"},
    3: {"areaCode": "35", "sigunguCode": "2"},
    4: {"areaCode": "39"},
    5: {"areaCode": "32", "sigunguCode": "1"},
}

TOURAPI_CONTENT_TYPES = {
    "관광지": "12",
    "문화시설": "14",
    "여행코스": "25",
    "숙박": "32",
    "음식점": "39",
}

CONTENT_TYPE_CATEGORY_NAMES = {
    "12": ["관광지"],
    "14": ["문화시설", "실내"],
    "25": ["여행코스"],
    "32": ["숙박", "실내"],
    "39": ["미식"],
}

FULL_COLLECTION_CONTENT_TYPES = ["12", "14", "25", "32", "39"]

INDOOR_HINTS = ("박물관", "전시", "미술관", "기념관", "센터", "몰", "시장", "식당", "카페", "문화", "실내")
OUTDOOR_HINTS = ("해수욕장", "해변", "공원", "숲", "산", "봉", "길", "전망대", "광장", "섬", "폭포", "호수", "야외")
CAFE_HINTS = ("카페", "커피", "로스터", "디저트")


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


def configured_tourapi_key() -> str | None:
    for name in ("TOUR_API_SERVICE_KEY", "TOURAPI_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY"):
        value = _safe_text(os.getenv(name))
        if value:
            return value
    return None


def _normalize_service_key(service_key: str) -> str:
    key = service_key.strip()
    return unquote(key) if "%" in key else key


def _tourapi_items(endpoint_url: str, service_key: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    request_params = {
        "serviceKey": _normalize_service_key(service_key),
        "MobileOS": "ETC",
        "MobileApp": "TravelCourseStreamlit",
        "_type": "json",
    }
    request_params.update(params)
    response = requests.get(endpoint_url, params=request_params, timeout=10)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"TourAPI JSON 응답을 읽지 못했습니다: {response.text[:160]}") from exc

    header = payload.get("response", {}).get("header", {})
    result_code = str(header.get("resultCode", "0000"))
    if result_code not in {"0000", "0"}:
        result_message = header.get("resultMsg") or "TourAPI 요청 실패"
        raise ValueError(f"TourAPI 오류 {result_code}: {result_message}")

    items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, dict):
        return [items]
    return items or []


def _to_float(value: Any) -> float | None:
    text = _safe_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _infer_indoor_outdoor(text: str, content_type_id: str) -> str:
    if content_type_id in {"14", "32", "39"}:
        return "실내"
    if any(hint in text for hint in INDOOR_HINTS):
        return "실내"
    if any(hint in text for hint in OUTDOOR_HINTS):
        return "야외"
    return "혼합"


def _infer_recommended_for(text: str, content_type_id: str) -> str:
    targets = ["친구"]
    if content_type_id in {"12", "14"} or any(hint in text for hint in ("박물관", "공원", "체험", "역사")):
        targets.append("가족")
    if any(hint in text for hint in ("야경", "전망", "해변", "카페", "거리", "마을")):
        targets.append("연인")
    if any(hint in text for hint in ("산책", "미술관", "박물관", "카페", "숲")):
        targets.append("혼자")
    return ", ".join(dict.fromkeys(targets))


def _category_names_for_item(item: dict[str, Any], content_type_id: str) -> list[str]:
    title = _safe_text(item.get("title")) or ""
    names = list(CONTENT_TYPE_CATEGORY_NAMES.get(content_type_id, ["관광지"]))
    if any(hint in title for hint in CAFE_HINTS):
        names.append("카페")
    if any(hint in title for hint in ("해변", "해수욕장", "공원", "숲", "산", "폭포", "호수")):
        names.append("자연")
    if any(hint in title for hint in ("야경", "전망", "타워", "대교")):
        names.append("야간")
    if any(hint in title for hint in ("궁", "사", "릉", "유적", "박물관", "문화")):
        names.append("역사")
    return list(dict.fromkeys(names))


def _first_image(item: dict[str, Any]) -> str | None:
    return _safe_text(item.get("firstimage")) or _safe_text(item.get("firstimage2"))


def fetch_tourapi_festivals(service_key: str, limit: int = 20) -> list[dict[str, Any]]:
    params = {
        "eventStartDate": date.today().strftime("%Y%m%d"),
        "numOfRows": limit,
        "pageNo": 1,
        "arrange": "A",
    }
    items = _tourapi_items(TOUR_API_FESTIVAL_URL, service_key, params)

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


def fetch_tourapi_area_places(
    service_key: str,
    region_id: int,
    content_type_id: str = "12",
    limit: int = 20,
) -> list[dict[str, Any]]:
    region_codes = TOURAPI_REGION_CODES.get(region_id)
    if not region_codes:
        return []

    params: dict[str, Any] = {
        "numOfRows": max(1, min(int(limit), 100)),
        "pageNo": 1,
        "arrange": "Q",
        "contentTypeId": content_type_id,
        **region_codes,
    }
    items = _tourapi_items(TOUR_API_AREA_BASED_URL, service_key, params)

    places: list[dict[str, Any]] = []
    for item in items[:limit]:
        title = _safe_text(item.get("title")) or "이름 미상 관광지"
        address = _safe_text(item.get("addr1")) or _safe_text(item.get("addr2"))
        tel = _safe_text(item.get("tel"))
        text = " ".join(part for part in [title, address, tel] if part)
        category_names = _category_names_for_item(item, content_type_id)
        if any(category == "카페" for category in category_names):
            category_names.append("미식")

        tags = ", ".join(
            dict.fromkeys(
                [
                    *category_names,
                    "TourAPI",
                    _safe_text(item.get("cat1")) or "",
                    _safe_text(item.get("cat2")) or "",
                    _safe_text(item.get("cat3")) or "",
                ]
            )
        ).strip(", ")
        places.append(
            {
                "region_id": region_id,
                "place_name": title[:120],
                "address": address,
                "overview": address or "한국관광공사 국문 관광정보 서비스에서 수집한 장소입니다.",
                "phone": tel,
                "latitude": _to_float(item.get("mapy")),
                "longitude": _to_float(item.get("mapx")),
                "image_url": _first_image(item),
                "source_url": _first_image(item) or TOUR_API_AREA_BASED_URL,
                "external_id": _safe_text(item.get("contentid")),
                "tags": tags or None,
                "indoor_outdoor": _infer_indoor_outdoor(text, content_type_id),
                "recommended_for": _infer_recommended_for(text, content_type_id),
                "budget_level": "보통" if content_type_id == "39" else None,
                "opening_hours": None,
                "source_api": "TourAPI areaBasedList2",
                "content_type_id": content_type_id,
                "category_names": category_names,
            }
        )
    return places


def collect_tourapi_places(
    service_key: str,
    region_id: int,
    content_type_ids: list[str],
    limit_per_type: int = 20,
) -> tuple[list[dict[str, Any]], str, str]:
    collected: list[dict[str, Any]] = []
    errors: list[str] = []
    for content_type_id in content_type_ids:
        try:
            collected.extend(fetch_tourapi_area_places(service_key, region_id, content_type_id, limit_per_type))
        except Exception as exc:
            errors.append(f"{content_type_id}: {exc}")

    if collected:
        message = f"TourAPI 장소 {len(collected)}건을 수집했습니다."
        if errors:
            message += " 일부 유형은 실패했습니다: " + " / ".join(errors)
        return collected, "SUCCESS", message
    if errors:
        return [], "FAILED", "TourAPI 장소 수집 실패: " + " / ".join(errors)
    return [], "FAILED", "TourAPI 장소 수집 결과가 비어 있습니다."


def collect_tourapi_full_dataset(
    service_key: str,
    region_ids: list[int] | None = None,
    limit_per_type: int = 35,
    festival_limit: int = 100,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str]:
    target_region_ids = region_ids or list(TOURAPI_REGION_CODES.keys())
    places: list[dict[str, Any]] = []
    festivals: list[dict[str, Any]] = []
    errors: list[str] = []

    for region_id in target_region_ids:
        for content_type_id in FULL_COLLECTION_CONTENT_TYPES:
            try:
                places.extend(fetch_tourapi_area_places(service_key, region_id, content_type_id, limit_per_type))
            except Exception as exc:
                errors.append(f"region {region_id} type {content_type_id}: {exc}")

    try:
        festivals = fetch_tourapi_festivals(service_key, festival_limit)
    except Exception as exc:
        errors.append(f"festival: {exc}")

    total = len(places) + len(festivals)
    if total:
        status = "SUCCESS" if not errors else "FALLBACK"
        message = f"TourAPI 전체 수집 {total}건 완료: 장소 {len(places)}건, 축제 {len(festivals)}건"
        if errors:
            message += " / 일부 실패: " + " / ".join(errors[:5])
        return places, festivals, status, message

    message = "TourAPI 전체 수집 결과가 비어 있습니다."
    if errors:
        message += " " + " / ".join(errors[:5])
    return [], [], "FAILED", message


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
