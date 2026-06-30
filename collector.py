from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import tomllib
from typing import Any
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

import database as db


TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
TOUR_API_FESTIVAL_URL = "https://apis.data.go.kr/B551011/KorService2/searchFestival2"
TOUR_API_AREA_BASED_URL = f"{TOUR_API_BASE_URL}/areaBasedList2"
VISITKOREA_FESTIVAL_URL = "https://korean.visitkorea.or.kr/kfes/list/wntyFstvlList.do"
PHOTO_GALLERY_BASE_URL = "https://apis.data.go.kr/B551011/PhotoGalleryService1"
DATA_LAB_BASE_URL = "https://apis.data.go.kr/B551011/DataLabService"
TOUR_API_PROVIDER_BASE_URL = "https://apis.data.go.kr/B551011"


TOURAPI_REGION_META = {
    "서울": {"areaCode": "1", "province": "서울특별시", "description": "도심 문화, 궁궐, 쇼핑, 야간 명소가 풍부한 지역"},
    "부산": {"areaCode": "6", "province": "부산광역시", "description": "바다, 시장, 영화, 야경 코스가 풍부한 지역"},
    "대구": {"areaCode": "4", "province": "대구광역시", "description": "도심 미식, 근대골목, 산책 코스가 있는 지역"},
    "인천": {"areaCode": "2", "province": "인천광역시", "description": "섬, 항구, 차이나타운, 공항 접근성이 좋은 지역"},
    "광주": {"areaCode": "5", "province": "광주광역시", "description": "예술, 역사, 미식 여행에 어울리는 지역"},
    "대전": {"areaCode": "3", "province": "대전광역시", "description": "과학, 도심 산책, 근교 자연을 함께 볼 수 있는 지역"},
    "울산": {"areaCode": "7", "province": "울산광역시", "description": "해안, 산업관광, 산악 경관이 함께 있는 지역"},
    "세종": {"areaCode": "8", "province": "세종특별자치시", "description": "도심 공원과 행정도시 기반의 산책 코스가 있는 지역"},
    "경기": {"areaCode": "31", "province": "경기도", "description": "수도권 근교 여행지와 가족형 관광지가 많은 지역"},
    "강원": {"areaCode": "32", "province": "강원특별자치도", "description": "산, 바다, 호수, 계절 여행지가 풍부한 지역"},
    "충북": {"areaCode": "33", "province": "충청북도", "description": "호수, 산림, 내륙 휴양 코스가 좋은 지역"},
    "충남": {"areaCode": "34", "province": "충청남도", "description": "서해안, 온천, 역사 도시가 있는 지역"},
    "경북": {"areaCode": "35", "province": "경상북도", "description": "역사 유산과 전통 문화 여행지가 풍부한 지역"},
    "경남": {"areaCode": "36", "province": "경상남도", "description": "남해안, 섬, 역사 도시를 함께 볼 수 있는 지역"},
    "전북": {"areaCode": "37", "province": "전북특별자치도", "description": "한옥, 미식, 산악 경관이 어울리는 지역"},
    "전남": {"areaCode": "38", "province": "전라남도", "description": "섬, 남도 미식, 해안 관광지가 풍부한 지역"},
    "제주": {"areaCode": "39", "province": "제주특별자치도", "description": "자연 경관과 드라이브 코스가 풍부한 지역"},
    "경주": {"areaCode": "35", "sigunguCode": "2", "province": "경상북도", "description": "신라 역사 유적과 야간 산책 코스가 강한 지역"},
    "강릉": {"areaCode": "32", "sigunguCode": "1", "province": "강원특별자치도", "description": "바다, 커피거리, 자연 휴식 코스가 좋은 지역"},
}

REGION_NAME_TO_ID = {
    "서울": 1,
    "부산": 2,
    "경주": 3,
    "제주": 4,
    "강릉": 5,
    "대구": 6,
    "인천": 7,
    "광주": 8,
    "대전": 9,
    "울산": 10,
    "세종": 11,
    "경기": 12,
    "강원": 13,
    "충북": 14,
    "충남": 15,
    "전북": 16,
    "전남": 17,
    "경북": 18,
    "경남": 19,
}
TOURAPI_REGION_CODES = {REGION_NAME_TO_ID[name]: {key: value for key, value in meta.items() if key in {"areaCode", "sigunguCode"}} for name, meta in TOURAPI_REGION_META.items()}

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

APPROVED_API_SERVICES = {
    "KOR": {
        "name": "한국관광공사_국문 관광정보 서비스_GW",
        "data_go_kr_id": "15101578",
        "storage": "places, festivals, restaurants, accommodations, place_categories",
    },
    "PHOTOG": {
        "name": "한국관광공사_관광사진 정보_GW",
        "data_go_kr_id": "15101914",
        "storage": "tour_photos",
        "endpoints": [
            f"{PHOTO_GALLERY_BASE_URL}/gallerySearchList1",
            f"{PHOTO_GALLERY_BASE_URL}/galleryList1",
        ],
    },
    "DATALAB": {
        "name": "한국관광공사_빅데이터_지역별 방문자수_GW",
        "data_go_kr_id": "15101972",
        "storage": "region_visitor_stats",
        "endpoints": [
            f"{DATA_LAB_BASE_URL}/metcoRegnVisitrDDList",
            f"{DATA_LAB_BASE_URL}/locgoRegnVisitrDDList",
            f"{DATA_LAB_BASE_URL}/metcoRegnVisitrMMList",
        ],
    },
    "TATSCNCTR": {
        "name": "한국관광공사_관광지 집중률 방문자 추이 예측 정보",
        "data_go_kr_id": "15128555",
        "storage": "attraction_concentration",
        "endpoints": [
            f"{TOUR_API_PROVIDER_BASE_URL}/TatsCnctrService1/tatsCnctrList",
            f"{TOUR_API_PROVIDER_BASE_URL}/TatsCnctrService/tatsCnctrList",
            f"{TOUR_API_PROVIDER_BASE_URL}/TatsCnctrService1/getTatsCnctrList",
        ],
    },
    "TARRLTE": {
        "name": "한국관광공사_관광지별 연관 관광지 정보",
        "data_go_kr_id": "15128560",
        "storage": "related_attractions",
        "endpoints": [
            f"{TOUR_API_PROVIDER_BASE_URL}/TarRlteService1/tarRlteList",
            f"{TOUR_API_PROVIDER_BASE_URL}/TatsRlteService1/tatsRlteList",
            f"{TOUR_API_PROVIDER_BASE_URL}/TarRlteService1/getTarRlteList",
        ],
    },
    "LOCGOHUB": {
        "name": "한국관광공사_기초지자체 중심 관광지 정보",
        "data_go_kr_id": "15128559",
        "storage": "center_attractions",
        "endpoints": [
            f"{TOUR_API_PROVIDER_BASE_URL}/LocgoHubService1/locgoHubList",
            f"{TOUR_API_PROVIDER_BASE_URL}/LocgoHubService/locgoHubList",
            f"{TOUR_API_PROVIDER_BASE_URL}/LocgoHubService1/getLocgoHubList",
        ],
    },
    "DMANDDVRST": {
        "name": "한국관광공사_지역별 관광 다양성",
        "data_go_kr_id": "15151365",
        "storage": "regional_demand_metrics",
        "endpoints": [
            f"{TOUR_API_PROVIDER_BASE_URL}/DemandDvrstService1/demandDvrstList",
            f"{TOUR_API_PROVIDER_BASE_URL}/DmandDvrstService1/dmandDvrstList",
            f"{TOUR_API_PROVIDER_BASE_URL}/DemandDvrstService1/getDemandDvrstList",
        ],
    },
    "DMANDRESR": {
        "name": "한국관광공사_지역별 관광 자원 수요",
        "data_go_kr_id": "15152138",
        "storage": "regional_demand_metrics",
        "endpoints": [
            f"{TOUR_API_PROVIDER_BASE_URL}/DemandResrService1/demandResrList",
            f"{TOUR_API_PROVIDER_BASE_URL}/DmandResrService1/dmandResrList",
            f"{TOUR_API_PROVIDER_BASE_URL}/DemandResrService1/getDemandResrList",
        ],
    },
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


def configured_tourapi_key() -> str | None:
    for name in ("TOUR_API_SERVICE_KEY", "TOURAPI_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY"):
        value = _safe_text(os.getenv(name))
        if value:
            return value
    secrets_path = Path(".streamlit") / "secrets.toml"
    if secrets_path.exists():
        try:
            values = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            values = {}
        for name in (
            "TOUR_API_SERVICE_KEY",
            "TOURAPI_SERVICE_KEY",
            "DATA_GO_KR_SERVICE_KEY",
            "VISITKOREA_PHOTO_SERVICE_KEY",
            "VISITKOREA_BIGDATA_SERVICE_KEY",
        ):
            value = _safe_text(values.get(name))
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


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    candidates = [
        payload.get("response", {}).get("body", {}).get("items", {}).get("item"),
        payload.get("response", {}).get("body", {}).get("items"),
        payload.get("body", {}).get("items", {}).get("item"),
        payload.get("body", {}).get("items"),
        payload.get("items", {}).get("item") if isinstance(payload.get("items"), dict) else payload.get("items"),
        payload.get("data"),
        payload.get("result"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return [candidate]
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def _tourapi_items_any(endpoint_url: str, service_key: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    request_params = {
        "serviceKey": _normalize_service_key(service_key),
        "MobileOS": "ETC",
        "MobileApp": "TravelCourseStreamlit",
        "_type": "json",
    }
    request_params.update({key: value for key, value in params.items() if value is not None})
    response = requests.get(endpoint_url, params=request_params, timeout=10)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"TourAPI JSON 응답을 읽지 못했습니다: {response.text[:160]}") from exc

    header = payload.get("response", {}).get("header", {}) if isinstance(payload, dict) else {}
    result_code = str(header.get("resultCode", "0000"))
    if result_code not in {"0000", "0"}:
        result_message = header.get("resultMsg") or "TourAPI 요청 실패"
        raise ValueError(f"TourAPI 오류 {result_code}: {result_message}")
    return _extract_items(payload)


def _try_api_candidates(
    service_key: str,
    endpoint_urls: list[str],
    params: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None, str, str]:
    errors: list[str] = []
    for endpoint_url in endpoint_urls:
        try:
            items = _tourapi_items_any(endpoint_url, service_key, params)
        except Exception as exc:
            errors.append(f"{endpoint_url.rsplit('/', 1)[-1]}: {exc}")
            continue
        if items:
            return items, endpoint_url, "SUCCESS", f"{len(items)}건 수신"
        errors.append(f"{endpoint_url.rsplit('/', 1)[-1]}: empty")
    message = " / ".join(errors[:4]) if errors else "응답이 비어 있습니다."
    return [], endpoint_urls[0] if endpoint_urls else None, "FAILED", message


def _coalesce(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if _safe_text(value):
            return value
    return None


def _numeric_value(item: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = item.get(key)
        if value is None or value == "":
            continue
        try:
            return float(str(value).replace(",", ""))
        except ValueError:
            continue
    return None


def _first_numeric_field(item: dict[str, Any], excluded: set[str] | None = None) -> tuple[str | None, float | None]:
    excluded = excluded or set()
    for key, value in item.items():
        if key in excluded or value in (None, ""):
            continue
        try:
            return key, float(str(value).replace(",", ""))
        except ValueError:
            continue
    return None, None


def _region_name_from_item(item: dict[str, Any]) -> str:
    parts = [
        _safe_text(_coalesce(item, "areaNm", "areaName", "sidoNm", "ctprvnNm", "signguNm", "sigunguNm", "regionName")),
        _safe_text(_coalesce(item, "signguNm", "sigunguName", "sggNm")),
    ]
    clean_parts = [part for part in parts if part]
    return " ".join(dict.fromkeys(clean_parts)) or "지역 미상"


def _raw_json(item: dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, default=str)


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


def ensure_known_regions(region_names: list[str] | None = None) -> dict[str, int]:
    target_names = region_names or list(TOURAPI_REGION_META.keys())
    region_ids: dict[str, int] = {}
    for region_name in target_names:
        meta = TOURAPI_REGION_META.get(region_name)
        if not meta:
            continue
        try:
            region_ids[region_name] = db.ensure_region(region_name, meta.get("province"), meta.get("description"))
        except Exception:
            fallback_id = REGION_NAME_TO_ID.get(region_name)
            if fallback_id:
                region_ids[region_name] = fallback_id
    return region_ids


def _region_codes_for_name(region_name: str) -> dict[str, str] | None:
    meta = TOURAPI_REGION_META.get(region_name)
    if not meta:
        return None
    return {key: str(value) for key, value in meta.items() if key in {"areaCode", "sigunguCode"}}


def _region_specs(region_names: list[str] | None = None, region_ids: list[int] | None = None) -> list[tuple[str, int, dict[str, str]]]:
    if region_names:
        target_names = [name for name in region_names if name in TOURAPI_REGION_META]
    elif region_ids:
        id_to_name = {region_id: region_name for region_name, region_id in REGION_NAME_TO_ID.items()}
        target_names = [id_to_name[region_id] for region_id in region_ids if region_id in id_to_name]
    else:
        target_names = list(TOURAPI_REGION_META.keys())

    ensured_ids = ensure_known_regions(target_names)
    specs: list[tuple[str, int, dict[str, str]]] = []
    for region_name in target_names:
        region_id = ensured_ids.get(region_name)
        codes = _region_codes_for_name(region_name)
        if region_id and codes:
            specs.append((region_name, region_id, codes))
    return specs


def _region_id_from_address(address: str) -> int:
    for region_name in TOURAPI_REGION_META:
        if region_name in address:
            ids = ensure_known_regions([region_name])
            return ids.get(region_name, REGION_NAME_TO_ID.get(region_name, 1))
    return REGION_NAME_TO_ID.get("서울", 1)


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
        region_id = _region_id_from_address(addr)
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
    region_codes: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    region_codes = region_codes or TOURAPI_REGION_CODES.get(region_id)
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
    region_names: list[str] | None = None,
    limit_per_type: int = 35,
    festival_limit: int = 100,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str]:
    target_regions = _region_specs(region_names=region_names, region_ids=region_ids)
    places: list[dict[str, Any]] = []
    festivals: list[dict[str, Any]] = []
    errors: list[str] = []

    for region_name, region_id, region_codes in target_regions:
        for content_type_id in FULL_COLLECTION_CONTENT_TYPES:
            try:
                places.extend(
                    fetch_tourapi_area_places(
                        service_key,
                        region_id,
                        content_type_id,
                        limit_per_type,
                        region_codes=region_codes,
                    )
                )
            except Exception as exc:
                errors.append(f"{region_name} type {content_type_id}: {exc}")

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


def _previous_month_params(limit: int) -> dict[str, Any]:
    today = date.today()
    month = today.month - 1
    year = today.year
    if month == 0:
        month = 12
        year -= 1
    base_ym = f"{year}{month:02d}"
    return {
        "numOfRows": max(1, min(int(limit), 100)),
        "pageNo": 1,
        "baseYm": base_ym,
        "startYm": base_ym,
        "endYm": base_ym,
        "baseYmd": f"{base_ym}01",
        "startYmd": f"{base_ym}01",
        "endYmd": f"{base_ym}28",
    }


def fetch_tour_photos(service_key: str, keyword: str | None = None, limit: int = 30) -> tuple[list[dict[str, Any]], str | None, str, str]:
    params: dict[str, Any] = {
        "numOfRows": max(1, min(int(limit), 100)),
        "pageNo": 1,
        "arrange": "A",
    }
    if keyword:
        params["keyword"] = keyword
    service = APPROVED_API_SERVICES["PHOTOG"]
    return _try_api_candidates(service_key, service["endpoints"], params)


def _photo_row(item: dict[str, Any], keyword: str | None = None) -> dict[str, Any]:
    title = _safe_text(_coalesce(item, "galTitle", "title", "photoTitle", "cntntsNm")) or "제목 없음"
    location = _safe_text(_coalesce(item, "galPhotographyLocation", "photographyLocation", "location", "addr1"))
    keywords = _safe_text(_coalesce(item, "galSearchKeyword", "keywords", "tag", "searchKeyword"))
    region_name = keyword if keyword and keyword in " ".join([title, location or "", keywords or ""]) else None
    return {
        "external_id": _safe_text(_coalesce(item, "galContentId", "contentId", "photoId", "id")),
        "region_name": region_name,
        "place_name": title[:150],
        "title": title[:200],
        "image_url": _safe_text(_coalesce(item, "galWebImageUrl", "webImageUrl", "imageUrl", "imgUrl", "firstimage")),
        "location": location,
        "photographer": _safe_text(_coalesce(item, "galPhotographer", "photographer")),
        "shot_date": _safe_text(_coalesce(item, "galPhotographyMonth", "photographyMonth", "shotDate", "createdtime")),
        "keywords": keywords,
        "raw_json": item,
    }


def _save_tour_photos(rows: list[dict[str, Any]], keyword: str | None = None) -> int:
    saved = 0
    for item in rows:
        try:
            db.upsert_tour_photo(_photo_row(item, keyword))
            saved += 1
        except Exception:
            continue
    return saved


def _save_visitor_rows(items: list[dict[str, Any]], source_api: str) -> int:
    saved = 0
    excluded = {"areaCode", "signguCode", "areaNm", "signguNm", "baseYmd", "baseYm", "daywkDivCd", "daywkDivNm", "touDivCd", "touDivNm"}
    for item in items:
        metric_name, fallback_value = _first_numeric_field(item, excluded)
        try:
            db.upsert_region_visitor_stat(
                {
                    "source_api": source_api,
                    "region_name": _region_name_from_item(item),
                    "stat_date": _safe_text(_coalesce(item, "baseYmd", "baseYm", "stdYmd", "stdYm")),
                    "visitor_type": _safe_text(_coalesce(item, "touDivNm", "visitorType", "typeNm", "daywkDivNm", metric_name or "")),
                    "visitor_count": _numeric_value(item, "touNum", "visitorCount", "visitrCnt", "cnt", "totalCnt") or fallback_value,
                    "raw_json": item,
                }
            )
            saved += 1
        except Exception:
            continue
    return saved


def _save_concentration_rows(items: list[dict[str, Any]]) -> int:
    saved = 0
    for item in items:
        name = _safe_text(_coalesce(item, "tAtsNm", "tatsNm", "tourspotNm", "poiNm", "attractionName", "rlteTatsNm"))
        if not name:
            continue
        try:
            db.upsert_attraction_concentration(
                {
                    "attraction_name": name[:180],
                    "region_name": _region_name_from_item(item),
                    "base_date": _safe_text(_coalesce(item, "baseYmd", "baseYm", "stdYmd")),
                    "forecast_date": _safe_text(_coalesce(item, "fcstYmd", "forecastYmd", "predYmd", "baseYmd")),
                    "concentration_score": _numeric_value(item, "cnctrRate", "cnctrScore", "concentrationRate", "predictionValue", "rate"),
                    "raw_json": item,
                }
            )
            saved += 1
        except Exception:
            continue
    return saved


def _save_related_rows(items: list[dict[str, Any]]) -> int:
    saved = 0
    for item in items:
        origin = _safe_text(_coalesce(item, "baseTatsNm", "originName", "hubTatsNm", "tAtsNm", "tatsNm"))
        related = _safe_text(_coalesce(item, "rlteTatsNm", "relatedName", "rlteNm", "rlteTatsName", "poiNm"))
        if not origin or not related or origin == related:
            continue
        try:
            db.upsert_related_attraction(
                {
                    "origin_name": origin[:180],
                    "related_name": related[:180],
                    "relation_type": _safe_text(_coalesce(item, "rlteCtgryNm", "rlteType", "category", "typeNm")),
                    "rank_no": _coalesce(item, "rlteRank", "rank", "rankNo", "rnum"),
                    "score": _numeric_value(item, "score", "rlteScore", "naviCnt", "searchCnt", "srchCnt"),
                    "region_name": _region_name_from_item(item),
                    "raw_json": item,
                }
            )
            saved += 1
        except Exception:
            continue
    return saved


def _save_center_rows(items: list[dict[str, Any]]) -> int:
    saved = 0
    for item in items:
        name = _safe_text(_coalesce(item, "hubTatsNm", "tAtsNm", "tatsNm", "tourspotNm", "poiNm", "attractionName"))
        if not name:
            continue
        try:
            db.upsert_center_attraction(
                {
                    "region_name": _region_name_from_item(item),
                    "attraction_name": name[:180],
                    "rank_no": _coalesce(item, "hubRank", "rank", "rankNo", "rnum"),
                    "navi_count": _numeric_value(item, "naviCnt", "srchCnt", "searchCnt", "visitCnt", "cnt"),
                    "raw_json": item,
                }
            )
            saved += 1
        except Exception:
            continue
    return saved


def _save_regional_metric_rows(items: list[dict[str, Any]], source_api: str, metric_group: str) -> int:
    saved = 0
    excluded = {
        "areaCode",
        "signguCode",
        "areaNm",
        "signguNm",
        "sidoNm",
        "ctprvnNm",
        "baseYmd",
        "baseYm",
        "stdYmd",
        "stdYm",
        "rnum",
    }
    for item in items:
        region_name = _region_name_from_item(item)
        stat_date = _safe_text(_coalesce(item, "baseYmd", "baseYm", "stdYmd", "stdYm"))
        for key, value in item.items():
            if key in excluded or value in (None, ""):
                continue
            try:
                numeric_value = float(str(value).replace(",", ""))
            except ValueError:
                continue
            try:
                db.upsert_regional_demand_metric(
                    {
                        "source_api": source_api,
                        "region_name": region_name,
                        "metric_group": metric_group,
                        "metric_name": key,
                        "metric_value": numeric_value,
                        "stat_date": stat_date,
                        "raw_json": item,
                    }
                )
                saved += 1
            except Exception:
                continue
    return saved


def _log_bundle_result(service_code: str, endpoint_url: str | None, status: str, count: int, message: str) -> dict[str, Any]:
    service = APPROVED_API_SERVICES[service_code]
    db.log_tour_api_usage(service_code, service["name"], endpoint_url, status, count, message)
    return {
        "service_code": service_code,
        "service_name": service["name"],
        "status": status,
        "saved_count": count,
        "message": message,
        "endpoint_url": endpoint_url,
    }


def collect_approved_api_bundle(
    service_key: str | None = None,
    region_names: list[str] | None = None,
    place_names: list[str] | None = None,
    limit_per_type: int = 25,
    advanced_limit: int = 80,
    photo_limit_per_keyword: int = 12,
) -> list[dict[str, Any]]:
    key = service_key or configured_tourapi_key()
    if not key:
        raise ValueError("TOUR_API_SERVICE_KEY가 설정되어 있지 않습니다.")

    db.ensure_recommendation_schema()
    db.ensure_advanced_api_schema()
    target_region_names = region_names or list(TOURAPI_REGION_META.keys())
    ensure_known_regions(target_region_names)
    results: list[dict[str, Any]] = []

    try:
        places, festivals, status, message = collect_tourapi_full_dataset(
            key,
            region_names=target_region_names,
            limit_per_type=limit_per_type,
            festival_limit=min(100, max(20, advanced_limit)),
        )
        saved = 0
        for row in places:
            try:
                db.upsert_tourapi_place(row)
                saved += 1
            except Exception:
                continue
        for row in festivals:
            try:
                db.upsert_festival(row)
                saved += 1
            except Exception:
                continue
        results.append(_log_bundle_result("KOR", TOUR_API_AREA_BASED_URL, status, saved, message))
    except Exception as exc:
        results.append(_log_bundle_result("KOR", TOUR_API_AREA_BASED_URL, "FAILED", 0, str(exc)))

    photo_saved = 0
    photo_messages: list[str] = []
    photo_endpoint: str | None = None
    photo_keywords = list(dict.fromkeys([*target_region_names, *(place_names or [])]))[:30]
    for keyword in photo_keywords:
        items, endpoint_url, status, message = fetch_tour_photos(key, keyword, photo_limit_per_keyword)
        photo_endpoint = endpoint_url or photo_endpoint
        if status == "SUCCESS":
            photo_saved += _save_tour_photos(items, keyword)
        else:
            photo_messages.append(f"{keyword}: {message}")
    photo_status = "SUCCESS" if photo_saved else "FAILED"
    photo_message = f"관광사진 {photo_saved}건 저장"
    if photo_messages:
        photo_message += " / 일부 실패: " + " / ".join(photo_messages[:3])
    results.append(_log_bundle_result("PHOTOG", photo_endpoint, photo_status, photo_saved, photo_message))

    generic_plan = [
        ("DATALAB", _previous_month_params(advanced_limit), lambda items: _save_visitor_rows(items, "DATALAB")),
        ("TATSCNCTR", _previous_month_params(advanced_limit), _save_concentration_rows),
        ("TARRLTE", _previous_month_params(advanced_limit), _save_related_rows),
        ("LOCGOHUB", _previous_month_params(advanced_limit), _save_center_rows),
        ("DMANDDVRST", _previous_month_params(advanced_limit), lambda items: _save_regional_metric_rows(items, "DMANDDVRST", "관광 다양성")),
        ("DMANDRESR", _previous_month_params(advanced_limit), lambda items: _save_regional_metric_rows(items, "DMANDRESR", "관광 자원 수요")),
    ]
    for service_code, params, saver in generic_plan:
        service = APPROVED_API_SERVICES[service_code]
        items, endpoint_url, status, message = _try_api_candidates(key, service["endpoints"], params)
        saved_count = 0
        if status == "SUCCESS":
            try:
                saved_count = saver(items)
            except Exception as exc:
                status = "FAILED"
                message = f"저장 실패: {exc}"
        results.append(_log_bundle_result(service_code, endpoint_url, status, saved_count, message))

    return results


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
