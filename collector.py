from __future__ import annotations

import argparse
import json
import os
import re
import tomllib
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup

import database as db

TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
TOUR_API_AREA_CODE_URL = f"{TOUR_API_BASE_URL}/areaCode2"
TOUR_API_AREA_BASED_URL = f"{TOUR_API_BASE_URL}/areaBasedList2"
TOUR_API_FESTIVAL_URL = f"{TOUR_API_BASE_URL}/searchFestival2"
TOUR_API_DETAIL_COMMON_URL = f"{TOUR_API_BASE_URL}/detailCommon2"
TOUR_API_DETAIL_INTRO_URL = f"{TOUR_API_BASE_URL}/detailIntro2"
TOUR_API_DETAIL_INFO_URL = f"{TOUR_API_BASE_URL}/detailInfo2"
VISITKOREA_FESTIVAL_URL = "https://korean.visitkorea.or.kr/kfes/list/wntyFstvlList.do"
VISITKOREA_SEARCH_URL = "https://korean.visitkorea.or.kr/search/search_list.do"

CONTENT_TYPES = {
    "places": "12",          # 관광지
    "festivals": "15",      # 축제/행사
    "accommodations": "32", # 숙소
    "restaurants": "39",    # 음식점
}

CONTENT_TYPE_NAMES = {
    "12": "관광지",
    "14": "문화시설",
    "15": "축제",
    "25": "여행코스",
    "28": "레포츠",
    "32": "숙박",
    "38": "쇼핑",
    "39": "음식점",
}

IMAGE_ROOT = Path(os.getenv("TRAVEL_IMAGE_ROOT", "static/images"))

_SAFE_NAME_RE = re.compile(r"[^0-9A-Za-z가-힣_.-]+")
_COLUMNS_CACHE: dict[str, set[str]] = {}


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_from_yyyymmdd(value: Any) -> str | None:
    text = _safe_text(value)
    if not text or len(text) != 8 or not text.isdigit():
        return None
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


def _float_or_none(value: Any) -> float | None:
    text = _safe_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_service_key(service_key: str) -> str:
    # 공공데이터포털에서 받은 Encoding Key를 넣어도 동작하도록 한 번 디코딩한다.
    return unquote(service_key.strip())


def visitkorea_search_url(keyword: str | None) -> str:
    text = _safe_text(keyword) or "축제"
    return f"{VISITKOREA_SEARCH_URL}?keyword={quote(text)}"


def configured_service_key() -> str | None:
    key_names = (
        "TOUR_API_SERVICE_KEY",
        "TOURAPI_SERVICE_KEY",
        "TOUR_API_KEY",
        "DATA_GO_KR_SERVICE_KEY",
        "VISITKOREA_PHOTO_SERVICE_KEY",
        "VISITKOREA_BIGDATA_SERVICE_KEY",
    )
    for name in key_names:
        value = os.getenv(name)
        if value:
            return str(value).strip()

    secrets_path = Path(".streamlit/secrets.toml")
    if secrets_path.exists():
        try:
            data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
            for name in key_names:
                value = data.get(name)
                if value:
                    return str(value).strip()
        except Exception:
            pass
    return None


def _table_columns(table_name: str) -> set[str]:
    if table_name not in _COLUMNS_CACHE:
        rows = db.fetch_all(f"SHOW COLUMNS FROM `{table_name}`")
        _COLUMNS_CACHE[table_name] = {row["Field"] for row in rows}
    return _COLUMNS_CACHE[table_name]


def _filter_existing_columns(table_name: str, data: dict[str, Any]) -> dict[str, Any]:
    columns = _table_columns(table_name)
    return {key: value for key, value in data.items() if key in columns}


def _entity_exists_by_external_id(entity_type: str, external_id: Any) -> bool:
    content_id = _safe_text(external_id)
    if not content_id:
        return False
    if entity_type not in {"places", "restaurants", "accommodations"}:
        return False
    if "external_id" not in _table_columns(entity_type):
        return False
    row = db.fetch_one(
        f"SELECT 1 AS exists_flag FROM `{entity_type}` WHERE external_id = %s LIMIT 1",
        (content_id,),
    )
    return bool(row)


def _upsert_row(table_name: str, data: dict[str, Any], skip_update: set[str] | None = None) -> None:
    """테이블에 존재하는 컬럼만 골라서 INSERT ... ON DUPLICATE KEY UPDATE 실행."""
    data = _filter_existing_columns(table_name, data)
    if not data:
        return

    skip_update = skip_update or set()
    columns = list(data.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(f"`{col}`" for col in columns)
    update_cols = [col for col in columns if col not in skip_update]

    if update_cols:
        update_sql = ", ".join(f"`{col}` = VALUES(`{col}`)" for col in update_cols)
    else:
        update_sql = f"`{columns[0]}` = `{columns[0]}`"

    sql = f"""
        INSERT INTO `{table_name}` ({column_sql})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {update_sql}
    """
    db.execute(sql, tuple(data[col] for col in columns))


def _ensure_column(table_name: str, column_name: str, ddl: str) -> None:
    """컬럼이 없으면 추가한다. 이미 있거나 권한 문제 등이 있으면 수집은 계속 진행한다."""
    try:
        columns = _table_columns(table_name)
    except Exception:
        return
    if column_name in columns:
        return
    try:
        db.execute(f"ALTER TABLE `{table_name}` ADD COLUMN {ddl}")
        _COLUMNS_CACHE.pop(table_name, None)
    except Exception:
        _COLUMNS_CACHE.pop(table_name, None)


def _ensure_table(sql: str) -> None:
    try:
        db.execute(sql)
    except Exception:
        pass


def ensure_collection_schema() -> None:
    """TourAPI 재수집에 필요한 확장 컬럼/매핑 테이블을 보장한다."""
    _ensure_column("regions", "tour_area_code", "tour_area_code VARCHAR(10) NULL COMMENT 'TourAPI 지역 코드'")
    _ensure_column("regions", "tour_sigungu_code", "tour_sigungu_code VARCHAR(10) NULL COMMENT 'TourAPI 시군구 코드'")
    _ensure_column("regions", "kakao_keyword", "kakao_keyword VARCHAR(100) NULL COMMENT '지도 API 검색용 키워드'")
    try:
        db.execute("ALTER TABLE regions ADD INDEX idx_regions_tour_code (tour_area_code, tour_sigungu_code)")
    except Exception:
        pass

    for table_name in ("places", "festivals", "restaurants", "accommodations"):
        _ensure_column(table_name, "image_path", "image_path VARCHAR(500) NULL COMMENT 'HDD/프로젝트 내부 저장 이미지 경로'")
        _ensure_column(table_name, "image_original_url", "image_original_url VARCHAR(1000) NULL COMMENT 'API 원본 이미지 URL'")
        _ensure_column(table_name, "image_saved_at", "image_saved_at DATETIME NULL COMMENT '이미지 저장 시각'")

    # 공식 API에서 직접 제공되거나 상세조회로 확인 가능한 필드만 추가한다.
    for table_name in ("places", "festivals", "restaurants", "accommodations"):
        _ensure_column(table_name, "content_type_id", "content_type_id VARCHAR(20) NULL COMMENT 'TourAPI contenttypeid'")
        _ensure_column(table_name, "content_type_name", "content_type_name VARCHAR(80) NULL COMMENT 'TourAPI 콘텐츠 타입명'")
        _ensure_column(table_name, "cat1", "cat1 VARCHAR(80) NULL COMMENT 'TourAPI 대분류'")
        _ensure_column(table_name, "cat2", "cat2 VARCHAR(80) NULL COMMENT 'TourAPI 중분류'")
        _ensure_column(table_name, "cat3", "cat3 VARCHAR(80) NULL COMMENT 'TourAPI 소분류'")
        _ensure_column(table_name, "detail_intro_json", "detail_intro_json LONGTEXT NULL COMMENT 'TourAPI detailIntro 원본 JSON'")
        _ensure_column(table_name, "source_url", "source_url VARCHAR(500) NULL COMMENT '공식/검색 정보 URL'")
        _ensure_column(table_name, "external_id", "external_id VARCHAR(80) NULL COMMENT 'TourAPI contentid'")

    _ensure_column("places", "lcls_systm1", "lcls_systm1 VARCHAR(100) NULL COMMENT 'TourAPI 분류체계1'")
    _ensure_column("places", "lcls_systm2", "lcls_systm2 VARCHAR(100) NULL COMMENT 'TourAPI 분류체계2'")
    _ensure_column("places", "lcls_systm3", "lcls_systm3 VARCHAR(100) NULL COMMENT 'TourAPI 분류체계3'")
    _ensure_column("places", "use_fee", "use_fee VARCHAR(500) NULL COMMENT 'TourAPI 상세정보 이용요금'")
    _ensure_column("places", "parking_fee", "parking_fee VARCHAR(255) NULL COMMENT 'TourAPI 상세정보 주차요금'")
    _ensure_column("places", "opening_hours", "opening_hours VARCHAR(255) NULL COMMENT 'TourAPI 이용시간'")
    _ensure_column("places", "has_tour_image", "has_tour_image BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'TourAPI 대표이미지 보유 여부'")
    _ensure_column("places", "photo_priority_score", "photo_priority_score DECIMAL(8,2) NOT NULL DEFAULT 0 COMMENT '사진 우선 노출 점수'")
    _ensure_column("places", "detail_common_json", "detail_common_json LONGTEXT NULL COMMENT 'TourAPI detailCommon 원본 JSON'")
    _ensure_column("places", "detail_info_json", "detail_info_json LONGTEXT NULL COMMENT 'TourAPI detailInfo 원본 JSON'")
    _ensure_column("places", "tour_api_updated_at", "tour_api_updated_at DATETIME NULL COMMENT 'TourAPI 상세정보 갱신 시각'")

    _ensure_column("festivals", "event_place", "event_place VARCHAR(255) NULL COMMENT 'TourAPI 행사 장소'")
    _ensure_column("festivals", "playtime", "playtime VARCHAR(255) NULL COMMENT 'TourAPI 공연/행사 시간'")
    _ensure_column("festivals", "sponsor", "sponsor VARCHAR(255) NULL COMMENT 'TourAPI 주최/주관'")
    _ensure_column("restaurants", "phone", "phone VARCHAR(80) NULL COMMENT 'TourAPI 전화번호'")
    _ensure_column("restaurants", "first_menu", "first_menu VARCHAR(255) NULL COMMENT 'TourAPI 대표 메뉴'")
    _ensure_column("restaurants", "treat_menu", "treat_menu VARCHAR(500) NULL COMMENT 'TourAPI 취급 메뉴'")
    _ensure_column("restaurants", "open_time", "open_time VARCHAR(255) NULL COMMENT 'TourAPI 영업 시간'")
    _ensure_column("restaurants", "rest_date", "rest_date VARCHAR(255) NULL COMMENT 'TourAPI 쉬는 날'")
    _ensure_column("restaurants", "parking_info", "parking_info VARCHAR(255) NULL COMMENT 'TourAPI 주차 정보'")
    _ensure_column("accommodations", "source_url", "source_url VARCHAR(500) NULL COMMENT '공식/검색 정보 URL'")
    _ensure_column("accommodations", "external_id", "external_id VARCHAR(80) NULL COMMENT 'TourAPI contentid'")
    _ensure_column("accommodations", "content_type_id", "content_type_id VARCHAR(20) NULL COMMENT 'TourAPI contenttypeid'")
    _ensure_column("accommodations", "content_type_name", "content_type_name VARCHAR(80) NULL COMMENT 'TourAPI 콘텐츠 타입명'")
    _ensure_column("accommodations", "cat1", "cat1 VARCHAR(80) NULL COMMENT 'TourAPI 대분류'")
    _ensure_column("accommodations", "cat2", "cat2 VARCHAR(80) NULL COMMENT 'TourAPI 중분류'")
    _ensure_column("accommodations", "cat3", "cat3 VARCHAR(80) NULL COMMENT 'TourAPI 소분류'")
    _ensure_column("accommodations", "checkin_time", "checkin_time VARCHAR(120) NULL COMMENT 'TourAPI 체크인'")
    _ensure_column("accommodations", "checkout_time", "checkout_time VARCHAR(120) NULL COMMENT 'TourAPI 체크아웃'")
    _ensure_column("accommodations", "room_count", "room_count VARCHAR(120) NULL COMMENT 'TourAPI 객실 수'")
    _ensure_column("accommodations", "reservation_url", "reservation_url VARCHAR(500) NULL COMMENT 'TourAPI 예약 URL'")
    _ensure_column("accommodations", "parking_info", "parking_info VARCHAR(255) NULL COMMENT 'TourAPI 주차 정보'")


def _tourapi_get(service_key: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "serviceKey": _clean_service_key(service_key),
        "MobileOS": "ETC",
        "MobileApp": "TravelCourseStreamlit",
        "_type": "json",
        **params,
    }
    response = requests.get(endpoint, params=merged, timeout=15)
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        preview = response.text[:300].replace("\n", " ")
        raise RuntimeError(f"TourAPI JSON 파싱 실패: {preview}") from exc

    header = payload.get("response", {}).get("header", {})
    result_code = str(header.get("resultCode", "")).strip()
    result_msg = str(header.get("resultMsg", "")).strip()
    if result_code and result_code not in {"0000", "0"}:
        raise RuntimeError(f"TourAPI 오류 resultCode={result_code}, resultMsg={result_msg}")
    return payload


def _items_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    TourAPI 응답에서 item 목록만 안전하게 꺼낸다.

    주의: 데이터가 없는 지역/조건에서는 TourAPI가
    items를 {"item": [...]} 형태가 아니라 빈 문자열("")로 주는 경우가 있다.
    그 상태에서 .get("item")을 호출하면
    'str' object has no attribute 'get' 오류가 나므로 타입을 먼저 검사한다.
    """
    if not isinstance(payload, dict):
        return []

    response = payload.get("response")
    if not isinstance(response, dict):
        return []

    body = response.get("body")
    if not isinstance(body, dict):
        return []

    items_container = body.get("items")
    if not items_container:
        return []

    # 정상적인 TourAPI 형태: {"items": {"item": [...]}}
    if isinstance(items_container, dict):
        items = items_container.get("item", [])
    # 일부 API/응답 형태: {"items": [...]}
    elif isinstance(items_container, list):
        items = items_container
    # 데이터 없음: {"items": ""} 같은 형태
    else:
        return []

    if not items:
        return []
    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _body_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response")
    if not isinstance(response, dict):
        return {}
    body = response.get("body")
    return body if isinstance(body, dict) else {}


def _api_page(service_key: str, endpoint: str, params: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    payload = _tourapi_get(service_key, endpoint, params)
    body = _body_from_payload(payload)
    try:
        total_count = int(body.get("totalCount") or 0)
    except (TypeError, ValueError):
        total_count = 0
    return _items_from_payload(payload), total_count


def _api_items(service_key: str, endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _tourapi_get(service_key, endpoint, params)
    return _items_from_payload(payload)


def _slug(text: str, default: str = "image") -> str:
    text = _SAFE_NAME_RE.sub("_", text.strip())
    text = text.strip("._-")
    return text[:80] or default


def save_image_from_url(image_url: str | None, folder: str, file_stem: str) -> tuple[str | None, str | None, str | None]:
    """API 이미지 URL을 HDD에 저장하고 DB에 넣을 상대 경로를 반환한다."""
    image_url = _safe_text(image_url)
    if not image_url:
        return None, None, None

    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
    except Exception:
        # 다운로드 실패 시 원본 URL만 남긴다.
        return None, image_url, None

    content_type = response.headers.get("Content-Type", "").lower()
    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"
    else:
        parsed_ext = Path(urlparse(image_url).path).suffix.lower()
        if parsed_ext in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = parsed_ext

    target_dir = IMAGE_ROOT / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_slug(file_stem)}{ext}"
    target_path = target_dir / filename
    target_path.write_bytes(response.content)

    # Streamlit 실행 위치 기준으로 쓰기 편하게 상대 경로 저장
    saved_path = str(target_path).replace("\\", "/")
    return saved_path, image_url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")



def _normalize_tour_code(value: Any) -> str | None:
    text = _safe_text(value)
    if text in {None, "", "0", "00"}:
        return None
    return text

def upsert_region(region_name: str, province: str, area_code: str | None, sigungu_code: str | None = None) -> int:
    ensure_collection_schema()
    area_code = _normalize_tour_code(area_code)
    sigungu_code = _normalize_tour_code(sigungu_code)
    data = {
        "region_name": region_name,
        "province": province,
        "description": f"TourAPI 지역 코드 기반으로 동기화된 지역입니다. area={area_code}, sigungu={sigungu_code or '-'}",
        "tour_area_code": area_code,
        "tour_sigungu_code": sigungu_code,
        "kakao_keyword": region_name,
    }
    _upsert_row("regions", data, skip_update={"region_name"})

    if "tour_area_code" in _table_columns("regions"):
        row = db.fetch_one(
            """
            SELECT region_id
            FROM regions
            WHERE tour_area_code = %s
              AND (
                tour_sigungu_code = %s
                OR ((tour_sigungu_code IS NULL OR tour_sigungu_code = '') AND %s IS NULL)
              )
            LIMIT 1
            """,
            (area_code, sigungu_code, sigungu_code),
        )
        if row:
            return int(row["region_id"])

    row = db.fetch_one("SELECT region_id FROM regions WHERE region_name = %s", (region_name,))
    if not row:
        raise RuntimeError(f"지역 저장 실패: {region_name}")
    return int(row["region_id"])


def sync_regions_from_tourapi(service_key: str, include_sigungu: bool = True) -> int:
    """TourAPI 지역코드/시군구코드를 regions 테이블에 동기화한다."""
    ensure_collection_schema()
    inserted_or_updated = 0
    areas = _api_items(
        service_key,
        TOUR_API_AREA_CODE_URL,
        {"numOfRows": 100, "pageNo": 1},
    )

    for area in areas:
        area_code = _safe_text(area.get("code"))
        area_name = _safe_text(area.get("name"))
        if not area_code or not area_name:
            continue

        # 광역 지역: 서울, 부산, 제주 등 기존 5개와 이름이 같으면 UPDATE됨
        upsert_region(area_name, area_name, area_code, None)
        inserted_or_updated += 1

        if not include_sigungu:
            continue

        try:
            sigungus = _api_items(
                service_key,
                TOUR_API_AREA_CODE_URL,
                {"areaCode": area_code, "numOfRows": 300, "pageNo": 1},
            )
        except Exception:
            sigungus = []

        for sigungu in sigungus:
            sigungu_code = _safe_text(sigungu.get("code"))
            sigungu_name = _safe_text(sigungu.get("name"))
            if not sigungu_code or not sigungu_name:
                continue

            # 중구/남구처럼 여러 지역에 중복되는 이름이 많으므로 광역명을 붙여 유니크하게 만든다.
            region_name = f"{area_name} {sigungu_name}"
            upsert_region(region_name, area_name, area_code, sigungu_code)
            inserted_or_updated += 1

    return inserted_or_updated


def resolve_region_id(area_code: Any, sigungu_code: Any = None) -> int | None:
    """TourAPI areaCode/sigunguCode로 DB에 실제 저장된 region_id를 찾는다.

    고정값(예: 대구=6)을 쓰지 않고 regions 테이블의 tour_area_code,
    tour_sigungu_code를 기준으로 조회한다.
    """
    ensure_collection_schema()
    area_code = _normalize_tour_code(area_code)
    sigungu_code = _normalize_tour_code(sigungu_code)
    if not area_code:
        return None

    if sigungu_code and "tour_area_code" in _table_columns("regions"):
        row = db.fetch_one(
            """
            SELECT region_id
            FROM regions
            WHERE tour_area_code = %s AND tour_sigungu_code = %s
            ORDER BY region_id
            LIMIT 1
            """,
            (area_code, sigungu_code),
        )
        if row:
            return int(row["region_id"])

    if "tour_area_code" in _table_columns("regions"):
        row = db.fetch_one(
            """
            SELECT region_id
            FROM regions
            WHERE tour_area_code = %s
              AND (tour_sigungu_code IS NULL OR tour_sigungu_code = '')
            ORDER BY region_id
            LIMIT 1
            """,
            (area_code,),
        )
        if row:
            return int(row["region_id"])

    return None


def ensure_category(category_name: str, description: str | None = None) -> int:
    _upsert_row(
        "categories",
        {
            "category_name": category_name,
            "description": description or f"{category_name} 관련 항목",
        },
        skip_update={"category_name"},
    )
    row = db.fetch_one("SELECT category_id FROM categories WHERE category_name = %s", (category_name,))
    if not row:
        raise RuntimeError(f"카테고리 저장 실패: {category_name}")
    return int(row["category_id"])


def attach_category(entity_type: str, entity_id: int, category_name: str) -> None:
    mapping = {
        "places": ("place_categories", "place_id"),
    }
    if entity_type not in mapping:
        return

    table_name, id_column = mapping[entity_type]
    try:
        _table_columns(table_name)
    except Exception:
        return

    category_id = ensure_category(category_name)
    db.execute(
        f"""
        INSERT IGNORE INTO `{table_name}` (`{id_column}`, category_id)
        VALUES (%s, %s)
        """,
        (entity_id, category_id),
    )


def _address(item: dict[str, Any]) -> str | None:
    addr1 = _safe_text(item.get("addr1"))
    addr2 = _safe_text(item.get("addr2"))
    return " ".join(part for part in [addr1, addr2] if part) or None


def _find_entity_id(table_name: str, id_column: str, name_column: str, region_id: int, name: str) -> int | None:
    row = db.fetch_one(
        f"""
        SELECT `{id_column}` AS id
        FROM `{table_name}`
        WHERE region_id = %s AND `{name_column}` = %s
        ORDER BY `{id_column}` DESC
        LIMIT 1
        """,
        (region_id, name),
    )
    return int(row["id"]) if row else None




def fetch_detail_bundle(service_key: str, content_id: str | None, content_type_id: str | None) -> dict[str, Any]:
    if not content_id:
        return {}
    detail: dict[str, Any] = {}
    try:
        common_items = _api_items(
            service_key,
            TOUR_API_DETAIL_COMMON_URL,
            {
                "contentId": content_id,
                "defaultYN": "Y",
                "firstImageYN": "Y",
                "areacodeYN": "Y",
                "catcodeYN": "Y",
                "addrinfoYN": "Y",
                "mapinfoYN": "Y",
                "overviewYN": "Y",
                "numOfRows": 1,
                "pageNo": 1,
            },
        )
        if common_items:
            detail["common"] = common_items[0]
    except Exception:
        pass
    if content_type_id:
        try:
            intro_items = _api_items(
                service_key,
                TOUR_API_DETAIL_INTRO_URL,
                {"contentId": content_id, "contentTypeId": content_type_id, "numOfRows": 1, "pageNo": 1},
            )
            if intro_items:
                detail["intro"] = intro_items[0]
        except Exception:
            pass
        try:
            info_items = _api_items(
                service_key,
                TOUR_API_DETAIL_INFO_URL,
                {"contentId": content_id, "contentTypeId": content_type_id, "numOfRows": 20, "pageNo": 1},
            )
            if info_items:
                detail["info"] = info_items
        except Exception:
            pass
    return detail


def enrich_item_with_details(service_key: str, item: dict[str, Any]) -> dict[str, Any]:
    content_id = _safe_text(item.get("contentid")) or _safe_text(item.get("contentId"))
    content_type_id = _safe_text(item.get("contenttypeid")) or _safe_text(item.get("contentTypeId"))
    detail = fetch_detail_bundle(service_key, content_id, content_type_id)
    if not detail:
        return dict(item)
    merged = dict(item)
    common = detail.get("common") or {}
    intro = detail.get("intro") or {}
    if common:
        merged.update({k: v for k, v in common.items() if v not in (None, "")})
    merged["_detail_common_json"] = common or None
    merged["_detail_intro_json"] = intro or None
    merged["_detail_info_json"] = detail.get("info") or None
    return merged


def _json_or_none(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    return json.dumps(value, ensure_ascii=False)


def _plain_html(value: Any) -> str | None:
    text = _safe_text(value)
    if not text:
        return None
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True) or text


def _official_base(item: dict[str, Any], content_type_id: str | None, content_id: str | None) -> dict[str, Any]:
    return {
        "external_id": content_id,
        "content_type_id": content_type_id,
        "content_type_name": CONTENT_TYPE_NAMES.get(str(content_type_id or ""), None),
        "cat1": _safe_text(item.get("cat1")),
        "cat2": _safe_text(item.get("cat2")),
        "cat3": _safe_text(item.get("cat3")),
        "source_url": visitkorea_search_url(_safe_text(item.get("title"))),
        "detail_common_json": _json_or_none(item.get("_detail_common_json")),
        "detail_intro_json": _json_or_none(item.get("_detail_intro_json")),
        "detail_info_json": _json_or_none(item.get("_detail_info_json")),
        "tour_api_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

def save_tourapi_item(entity_type: str, item: dict[str, Any]) -> bool:
    region_id = resolve_region_id(item.get("areacode"), item.get("sigungucode"))
    if not region_id:
        return False

    content_id = _safe_text(item.get("contentid")) or _safe_text(item.get("contentId"))
    content_type_id = _safe_text(item.get("contenttypeid")) or _safe_text(item.get("contentTypeId"))
    title = _safe_text(item.get("title"))
    if not title:
        return False

    first_image = _safe_text(item.get("firstimage")) or _safe_text(item.get("firstimage2"))
    image_path, image_original_url, image_saved_at = save_image_from_url(
        first_image,
        entity_type,
        content_id or title,
    )

    common = {
        "region_id": region_id,
        "address": _address(item),
        "phone": _safe_text(item.get("tel")),
        "image_path": image_path,
        "image_original_url": image_original_url,
        "image_saved_at": image_saved_at,
    }
    official = _official_base(item, content_type_id, content_id)
    intro = item.get("_detail_intro_json") or {}
    overview = _plain_html(item.get("overview")) or _address(item)

    if entity_type == "places":
        data = {
            **common,
            **official,
            "place_name": title[:120],
            "overview": overview or "한국관광공사 TourAPI에서 수집한 관광지 정보입니다.",
            "latitude": _float_or_none(item.get("mapy")),
            "longitude": _float_or_none(item.get("mapx")),
            "use_fee": _plain_html(intro.get("usefee") or intro.get("usetime") or intro.get("usetimeculture") or intro.get("usetimeleports")),
            "parking_fee": _plain_html(intro.get("parkingfee") or intro.get("parking")),
            "opening_hours": _plain_html(intro.get("usetime") or intro.get("usetimeculture") or intro.get("usetimeleports")),
            "has_tour_image": bool(image_path or image_original_url),
            "photo_priority_score": 10 if (image_path or image_original_url) else 0,
        }
        _upsert_row("places", data, skip_update={"region_id", "place_name"})
        entity_id = _find_entity_id("places", "place_id", "place_name", region_id, title[:120])
        if entity_id:
            attach_category("places", entity_id, "관광지")
        return True

    if entity_type == "festivals":
        data = {
            **common,
            **official,
            "festival_name": title[:150],
            "start_date": _date_from_yyyymmdd(item.get("eventstartdate")) or _date_from_yyyymmdd(item.get("eventStartDate")),
            "end_date": _date_from_yyyymmdd(item.get("eventenddate")) or _date_from_yyyymmdd(item.get("eventEndDate")),
            "fee_info": _plain_html(intro.get("usetimefestival") or intro.get("sponsor1")),
            "homepage": _plain_html((item.get("_detail_common_json") or {}).get("homepage")),
            "overview": overview or "한국관광공사 TourAPI에서 수집한 축제 정보입니다.",
            "event_place": _plain_html(intro.get("eventplace")),
            "playtime": _plain_html(intro.get("playtime")),
            "sponsor": _plain_html(intro.get("sponsor1") or intro.get("sponsor2")),
        }
        _upsert_row("festivals", data, skip_update={"region_id", "festival_name", "start_date"})
        entity_id = _find_entity_id("festivals", "festival_id", "festival_name", region_id, title[:150])
        if entity_id:
            attach_category("festivals", entity_id, "축제")
        return True

    if entity_type == "restaurants":
        data = {
            **common,
            **official,
            "restaurant_name": title[:120],
            "food_type": "음식점",
            "first_menu": _plain_html(intro.get("firstmenu")),
            "treat_menu": _plain_html(intro.get("treatmenu")),
            "open_time": _plain_html(intro.get("opentimefood")),
            "rest_date": _plain_html(intro.get("restdatefood")),
            "parking_info": _plain_html(intro.get("parkingfood")),
        }
        _upsert_row("restaurants", data, skip_update={"region_id", "restaurant_name"})
        entity_id = _find_entity_id("restaurants", "restaurant_id", "restaurant_name", region_id, title[:120])
        if entity_id:
            attach_category("restaurants", entity_id, "미식")
        return True

    if entity_type == "accommodations":
        data = {
            **common,
            **official,
            "accommodation_name": title[:120],
            "checkin_time": _plain_html(intro.get("checkintime")),
            "checkout_time": _plain_html(intro.get("checkouttime")),
            "room_count": _plain_html(intro.get("roomcount")),
            "reservation_url": _plain_html(intro.get("reservationurl")),
            "parking_info": _plain_html(intro.get("parkinglodging")),
        }
        _upsert_row("accommodations", data, skip_update={"region_id", "accommodation_name"})
        entity_id = _find_entity_id("accommodations", "accommodation_id", "accommodation_name", region_id, title[:120])
        if entity_id:
            attach_category("accommodations", entity_id, "숙소")
        return True

    return False


def fetch_tourapi_festivals(service_key: str, limit: int = 100) -> list[dict[str, Any]]:
    """
    축제 수집:
    1) searchFestival2로 날짜 포함 축제 수집
    2) 결과가 0이면 areaBasedList2 + contentTypeId=15로 fallback 수집
    """
    sync_regions_from_tourapi(service_key, include_sigungu=True)

    items: list[dict[str, Any]] = []
    areas = _api_items(
        service_key,
        TOUR_API_AREA_CODE_URL,
        {"numOfRows": 100, "pageNo": 1},
    )

    # 오늘 날짜로만 잡으면 미래 축제가 적을 수 있으므로 올해 1월 1일부터 조회
    start_date = f"{date.today().year}0101"
    collection_limit = max(0, int(limit or 0))
    per_page = 100 if collection_limit == 0 else max(1, min(collection_limit, 100))

    # 1차: searchFestival2 사용
    for area in areas:
        area_code = _safe_text(area.get("code"))
        if not area_code:
            continue

        page_no = 1
        while True:
            try:
                rows, total_count = _api_page(
                    service_key,
                    TOUR_API_FESTIVAL_URL,
                    {
                        "eventStartDate": start_date,
                        "areaCode": area_code,
                        "numOfRows": per_page,
                        "pageNo": page_no,
                        "arrange": "A",
                    },
                )
            except Exception as exc:
                print(f"[축제 searchFestival2 실패] areaCode={area_code}: {exc}")
                break
            if not rows:
                break
            items.extend(rows)
            if collection_limit and len(items) >= collection_limit:
                break
            if total_count and page_no * per_page >= total_count:
                break
            if len(rows) < per_page:
                break
            page_no += 1

        if collection_limit and len(items) >= collection_limit:
            break

    # 2차: 그래도 0건이면 areaBasedList2 + contentTypeId=15로 fallback
    if not items:
        print("[축제] searchFestival2 결과 0건 → areaBasedList2 contentTypeId=15로 재시도")

        for area in areas:
            area_code = _safe_text(area.get("code"))
            if not area_code:
                continue

            try:
                rows = _api_items(
                    service_key,
                    TOUR_API_AREA_BASED_URL,
                    {
                        "contentTypeId": "15",
                        "areaCode": area_code,
                        "numOfRows": per_page,
                        "pageNo": 1,
                        "arrange": "A",
                    },
                )
                items.extend(rows)
            except Exception as exc:
                print(f"[축제 areaBasedList2 실패] areaCode={area_code}: {exc}")

            if collection_limit and len(items) >= collection_limit:
                break

    festivals: list[dict[str, Any]] = []

    for item in (items[:collection_limit] if collection_limit else items):
        item = enrich_item_with_details(service_key, item)
        region_id = resolve_region_id(item.get("areacode"), item.get("sigungucode"))
        if not region_id:
            print(
                "[축제 저장 스킵] 지역 매칭 실패:",
                item.get("title"),
                item.get("areacode"),
                item.get("sigungucode"),
            )
            continue

        title = _safe_text(item.get("title")) or "이름 미상 축제"
        addr = _address(item) or ""
        first_image = _safe_text(item.get("firstimage")) or _safe_text(item.get("firstimage2"))

        image_path, image_original_url, image_saved_at = save_image_from_url(
            first_image,
            "festivals",
            _safe_text(item.get("contentid")) or title,
        )

        official = _official_base(item, _safe_text(item.get("contenttypeid")) or "15", _safe_text(item.get("contentid")))
        intro = item.get("_detail_intro_json") or {}
        festivals.append(
            {
                "region_id": region_id,
                **official,
                "festival_name": title[:150],
                "start_date": _date_from_yyyymmdd(item.get("eventstartdate"))
                or _date_from_yyyymmdd(item.get("eventStartDate")),
                "end_date": _date_from_yyyymmdd(item.get("eventenddate"))
                or _date_from_yyyymmdd(item.get("eventEndDate")),
                "fee_info": _plain_html(intro.get("usetimefestival")),
                "homepage": _plain_html((item.get("_detail_common_json") or {}).get("homepage")),
                "overview": _plain_html(item.get("overview")) or addr or "한국관광공사 TourAPI에서 수집한 축제/행사 정보입니다.",
                "event_place": _plain_html(intro.get("eventplace")),
                "playtime": _plain_html(intro.get("playtime")),
                "sponsor": _plain_html(intro.get("sponsor1") or intro.get("sponsor2")),
                "image_path": image_path,
                "image_original_url": image_original_url,
                "image_saved_at": image_saved_at,
            }
        )

    print(f"[축제] 최종 변환 완료: {len(festivals)}건")
    return festivals


def fetch_area_based_items(
    service_key: str,
    entity_type: str,
    limit_per_area: int = 10,
    include_sigungu: bool = True,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    content_type_id = CONTENT_TYPES[entity_type]
    areas = _api_items(service_key, TOUR_API_AREA_CODE_URL, {"numOfRows": 100, "pageNo": 1})
    all_items: list[dict[str, Any]] = []
    seen_content_ids: set[str] = set()

    for area in areas:
        area_code = _safe_text(area.get("code"))
        if not area_code:
            continue

        targets: list[tuple[str, str | None]] = []
        if include_sigungu:
            try:
                sigungus = _api_items(
                    service_key,
                    TOUR_API_AREA_CODE_URL,
                    {"areaCode": area_code, "numOfRows": 300, "pageNo": 1},
                )
            except Exception:
                sigungus = []
            targets = [
                (area_code, _safe_text(sigungu.get("code")))
                for sigungu in sigungus
                if _safe_text(sigungu.get("code"))
            ]
        if not targets:
            targets = [(area_code, None)]

        area_count = 0
        area_limit = max(0, int(limit_per_area or 0))
        for target_area_code, sigungu_code in targets:
            page_no = 1
            while True:
                request_rows = max(1, min(int(page_size or 100), 1000))
                if area_limit:
                    remaining = area_limit - area_count
                    if remaining <= 0:
                        break
                    request_rows = min(request_rows, remaining)

                params: dict[str, Any] = {
                    "contentTypeId": content_type_id,
                    "areaCode": target_area_code,
                    "numOfRows": request_rows,
                    "pageNo": page_no,
                    "arrange": "A",
                }
                if sigungu_code:
                    params["sigunguCode"] = sigungu_code

                rows, total_count = _api_page(service_key, TOUR_API_AREA_BASED_URL, params)
                if not rows:
                    break

                for row in rows:
                    content_id = _safe_text(row.get("contentid")) or _safe_text(row.get("contentId"))
                    dedupe_key = content_id or "|".join(
                        [
                            _safe_text(row.get("title")) or "",
                            _safe_text(row.get("addr1")) or "",
                            _safe_text(row.get("mapx")) or "",
                            _safe_text(row.get("mapy")) or "",
                        ]
                    )
                    if dedupe_key and dedupe_key in seen_content_ids:
                        continue
                    if dedupe_key:
                        seen_content_ids.add(dedupe_key)
                    all_items.append(row)
                    area_count += 1
                    if area_limit and area_count >= area_limit:
                        break

                if area_limit and area_count >= area_limit:
                    break
                if total_count and page_no * request_rows >= total_count:
                    break
                if len(rows) < request_rows:
                    break
                page_no += 1

            if area_limit and area_count >= area_limit:
                break

    return all_items


def collect_full_tourapi_data(service_key: str, limit_per_area: int = 10, include_sigungu: bool = True) -> dict[str, int]:
    """지역 + 관광지 + 축제 + 숙소 + 음식점을 TourAPI에서 다시 수집해 DB에 저장."""
    stats = {
        "regions": sync_regions_from_tourapi(service_key, include_sigungu=include_sigungu),
        "places": 0,
        "festivals": 0,
        "restaurants": 0,
        "accommodations": 0,
    }

    for entity_type in ["places", "restaurants", "accommodations"]:
        try:
            items = fetch_area_based_items(
                service_key,
                entity_type,
                limit_per_area=limit_per_area,
                include_sigungu=include_sigungu,
            )
            for item in items:
                content_id = _safe_text(item.get("contentid")) or _safe_text(item.get("contentId"))
                if _entity_exists_by_external_id(entity_type, content_id):
                    continue
                enriched = enrich_item_with_details(service_key, item)
                if save_tourapi_item(entity_type, enriched):
                    stats[entity_type] += 1
        except Exception as exc:
            db.log_crawl(
                f"tourapi_{entity_type}",
                TOUR_API_AREA_BASED_URL,
                "FAILED",
                stats[entity_type],
                f"{entity_type} 수집 실패: {exc}",
            )

    # 축제는 행사 시작/종료일을 받기 위해 searchFestival2 사용
    try:
        festival_limit = 0 if int(limit_per_area or 0) == 0 else max(20, limit_per_area * 17)
        festivals = fetch_tourapi_festivals(service_key, limit=festival_limit)
        for festival in festivals:
            _upsert_row("festivals", festival, skip_update={"region_id", "festival_name", "start_date"})
            stats["festivals"] += 1
    except Exception as exc:
        db.log_crawl("tourapi_festivals", TOUR_API_FESTIVAL_URL, "FAILED", stats["festivals"], f"축제 수집 실패: {exc}")

    db.log_crawl(
        "tourapi_full_sync",
        TOUR_API_BASE_URL,
        "SUCCESS",
        sum(v for k, v in stats.items() if k != "regions"),
        f"TourAPI 전체 동기화 완료: {stats}",
    )
    return stats


def crawl_visitkorea_festival_titles(limit: int = 10) -> list[dict[str, Any]]:
    crawl_limit = max(0, int(limit or 0))
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
    fallback_region = db.fetch_one("SELECT region_id FROM regions ORDER BY region_id LIMIT 1")
    fallback_region_id = int(fallback_region["region_id"]) if fallback_region else 1

    for node in candidates:
        title = node.get_text(" ", strip=True)
        if len(title) < 3 or title in seen:
            continue
        seen.add(title)
        festivals.append(
            {
                "region_id": fallback_region_id,
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
        if crawl_limit and len(festivals) >= crawl_limit:
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
                return festivals, "SUCCESS", "TourAPI 지역 동기화 후 전국 축제 데이터를 수집했습니다."
            return [], "SUCCESS", "TourAPI 호출은 성공했지만 수집된 축제가 없습니다."
        except Exception as exc:
            return fallback_festivals(), "FALLBACK", f"TourAPI 호출 실패로 샘플 축제를 사용했습니다: {exc}"

    try:
        crawl_limit = 0 if int(limit or 0) == 0 else min(limit, 10)
        festivals = crawl_visitkorea_festival_titles(crawl_limit)
        if festivals:
            return festivals, "SUCCESS", "HTML 크롤링으로 축제 제목 후보를 수집했습니다."
    except Exception as exc:
        return fallback_festivals(), "FALLBACK", f"HTML 크롤링 실패로 샘플 축제를 사용했습니다: {exc}"

    return fallback_festivals(), "FALLBACK", "수집된 축제 데이터가 없어 샘플 데이터를 사용했습니다."


def collect_approved_api_bundle(service_key: str | None = None, limit_per_area: int = 20) -> dict[str, Any]:
    """collect_approved_apis.py에서 바로 호출하는 호환용 전체 수집 함수."""
    key = service_key or configured_service_key()
    if not key:
        return {
            "status": "FAILED",
            "message": "TOUR_API_SERVICE_KEY 또는 TOUR_API_KEY 환경변수가 필요합니다.",
            "stats": {},
        }

    try:
        stats = collect_full_tourapi_data(key, limit_per_area=limit_per_area, include_sigungu=True)
        return {"status": "SUCCESS", "message": "TourAPI 전체 수집 완료", "stats": stats}
    except Exception as exc:
        return {"status": "FAILED", "message": str(exc), "stats": {}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Travel 프로젝트 TourAPI 데이터 재수집기")
    parser.add_argument("--service-key", default=os.getenv("TOUR_API_KEY"), help="한국관광공사 TourAPI 서비스키")
    parser.add_argument("--regions-only", action="store_true", help="지역 코드만 동기화")
    parser.add_argument("--all", action="store_true", help="지역/관광지/음식점/숙소/축제 전체 수집")
    parser.add_argument("--limit-per-area", type=int, default=10, help="광역 지역 1개당 수집 개수. 0이면 시군구별 전체 페이지를 수집")
    parser.add_argument("--no-sigungu", action="store_true", help="시군구 지역은 만들지 않고 광역 지역만 동기화")
    args = parser.parse_args()

    if not args.service_key:
        raise SystemExit("TourAPI 서비스키가 필요합니다. --service-key 또는 TOUR_API_KEY 환경변수를 사용하세요.")

    if args.regions_only:
        count = sync_regions_from_tourapi(args.service_key, include_sigungu=not args.no_sigungu)
        print(f"지역 동기화 완료: {count}건")
        return

    if args.all:
        stats = collect_full_tourapi_data(
            args.service_key,
            limit_per_area=args.limit_per_area,
            include_sigungu=not args.no_sigungu,
        )
        print(f"전체 수집 완료: {stats}")
        return

    festival_limit = 0 if int(args.limit_per_area or 0) == 0 else args.limit_per_area * 17
    festivals, status, message = collect_festival_data(args.service_key, limit=festival_limit)
    inserted = 0
    for row in festivals:
        _upsert_row("festivals", row, skip_update={"region_id", "festival_name", "start_date"})
        inserted += 1
    db.log_crawl("tourapi_festival_cli", TOUR_API_FESTIVAL_URL, status, inserted, message)
    print(f"축제 수집 완료: {inserted}건, {status}, {message}")


if __name__ == "__main__":
    main()
