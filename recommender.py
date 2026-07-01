from __future__ import annotations

from decimal import Decimal
from typing import Any

TRIP_CATEGORY_KEYWORDS = {
    "관광지": ["관광지", "명소", "여행코스", "유적", "공원", "전망"],
    "자연": ["자연", "바다", "해변", "해수욕장", "산", "숲", "공원", "호수", "폭포", "일출"],
    "미식": ["미식", "맛집", "식당", "음식", "먹거리", "시장", "향토", "한식"],
    "카페": ["카페", "커피", "디저트", "로스터", "베이커리"],
    "문화시설": ["문화시설", "문화", "전시", "박물관", "미술관", "공연", "체험"],
    "역사": ["역사", "궁", "궁궐", "유적", "문화재", "사찰", "박물관", "왕릉"],
    "사진 명소": ["사진", "포토", "전망", "야경", "일출", "일몰", "해변", "정원"],
    "야간": ["야간", "야경", "밤", "전망", "불빛", "조명"],
    "숙박": ["숙박", "호텔", "펜션", "리조트", "게스트하우스"],
    "축제": ["축제", "행사", "페스티벌", "공연"],
    "여행코스": ["여행코스", "코스", "둘레길", "거리", "길", "투어"],
}

TOUR_CONTENT_TYPE_NAMES = {
    "12": "관광지",
    "14": "문화시설",
    "15": "축제",
    "25": "여행코스",
    "28": "레포츠",
    "32": "숙박",
    "38": "쇼핑",
    "39": "음식점",
}


def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [safe_text(item) for item in value if safe_text(item)]
    raw = safe_text(value)
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def category_tokens(row: dict[str, Any]) -> list[str]:
    return _as_list(row.get("categories"))


def combined_text(row: dict[str, Any]) -> str:
    parts = [
        row.get("place_name"),
        row.get("categories"),
        row.get("tags"),
        row.get("overview"),
        row.get("address"),
        row.get("content_type_name"),
        row.get("cat1"),
        row.get("cat2"),
        row.get("cat3"),
        row.get("lcls_systm1"),
        row.get("lcls_systm2"),
        row.get("lcls_systm3"),
    ]
    return " ".join(safe_text(part) for part in parts if safe_text(part))


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def _has_image(row: dict[str, Any]) -> bool:
    return bool(row.get("image_path") or row.get("image_url") or row.get("image_original_url"))


def _has_official_detail(row: dict[str, Any]) -> bool:
    return bool(
        row.get("detail_common_json")
        or row.get("detail_intro_json")
        or row.get("detail_info_json")
        or row.get("opening_hours")
        or row.get("use_fee")
        or row.get("parking_fee")
    )


def _detail_score(row: dict[str, Any]) -> float:
    overview = safe_text(row.get("overview"))
    score = min(len(overview) / 70, 14) if overview else 0
    if safe_text(row.get("address")):
        score += 4
    if row.get("latitude") and row.get("longitude"):
        score += 6
    if safe_text(row.get("phone")):
        score += 2
    if safe_text(row.get("source_url")):
        score += 2
    return min(score, 22)


def _stable_spread(row: dict[str, Any]) -> float:
    seed = safe_text(row.get("place_id") or row.get("external_id") or row.get("place_name"))
    if not seed:
        return 0
    return (sum(ord(char) for char in seed) % 17) / 10


def matching_categories(row: dict[str, Any], preferences: dict[str, Any]) -> list[str]:
    text = combined_text(row)
    row_categories = set(category_tokens(row))
    selected = _as_list(preferences.get("selected_categories"))
    selected_db = _as_list(preferences.get("selected_db_categories"))
    content_type_name = safe_text(row.get("content_type_name"))
    cat_values = {safe_text(row.get(key)) for key in ("cat1", "cat2", "cat3", "lcls_systm1", "lcls_systm2", "lcls_systm3") if safe_text(row.get(key))}

    matched: list[str] = []
    for category in selected_db + selected:
        if not category:
            continue
        keywords = TRIP_CATEGORY_KEYWORDS.get(category, [category])
        if (
            category in row_categories
            or category == content_type_name
            or category in cat_values
            or contains_any(text, keywords)
        ):
            matched.append(category)
    return list(dict.fromkeys(matched))


def score_place(
    row: dict[str, Any],
    preferences: dict[str, Any],
    favorite_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    scored = dict(row)
    favorite_category_counts = favorite_category_counts or {}
    score = 0.0
    score_reasons: list[tuple[float, str]] = []

    def add_points(points: float, reason: str | None = None) -> None:
        nonlocal score
        if points <= 0:
            return
        score += points
        if reason:
            score_reasons.append((points, reason))

    destination = safe_text(preferences.get("destination"))
    region_name = safe_text(scored.get("region_name"))
    if destination and destination != "전국" and (destination in region_name or region_name in destination):
        if destination == region_name:
            add_points(34, f"지역 일치: 선택한 지역({destination})과 정확히 맞는 장소입니다.")
        else:
            add_points(24, f"지역권 일치: 선택한 지역({destination})과 같은 권역의 장소입니다.")
    elif destination == "전국":
        add_points(4)

    category_matches = matching_categories(scored, preferences)
    if category_matches:
        label = ", ".join(category_matches[:3])
        category_points = 28 + min(len(category_matches) * 4, 12)
        add_points(category_points, f"취향 일치: 선택한 카테고리와 연결됩니다. ({label})")

    content_type_id = safe_text(scored.get("content_type_id"))
    if content_type_id:
        content_type_name = TOUR_CONTENT_TYPE_NAMES.get(content_type_id, safe_text(scored.get("content_type_name")) or content_type_id)
        scored["content_type_name"] = content_type_name
        add_points(5, f"장소 유형: {content_type_name} 유형으로 분류된 장소입니다.")

    cat_detail = "/".join(safe_text(scored.get(key)) for key in ("cat1", "cat2", "cat3") if safe_text(scored.get(key)))
    if cat_detail:
        add_points(4 + min(cat_detail.count("/") * 2, 4), "세부 분류: 장소 성격을 판단할 수 있는 분류 정보가 있습니다.")

    if _has_image(scored):
        add_points(11, "대표 이미지: 사진이 있어 방문 전 분위기를 확인하기 좋습니다.")

    if _has_official_detail(scored):
        add_points(7, "이용 정보: 소개, 이용시간, 요금 같은 상세 정보가 비교적 갖춰져 있습니다.")

    detail_points = _detail_score(scored)
    if detail_points >= 14:
        detail_bits = []
        if safe_text(scored.get("address")):
            detail_bits.append("주소")
        if scored.get("latitude") and scored.get("longitude"):
            detail_bits.append("좌표")
        if safe_text(scored.get("overview")):
            detail_bits.append("소개")
        label = ", ".join(detail_bits) or "기본 정보"
        add_points(detail_points, f"정보 충실도: {label} 정보가 있어 일정에 넣기 좋습니다.")
    elif detail_points:
        add_points(detail_points)

    fee_text = safe_text(scored.get("use_fee") or scored.get("fee_info"))
    if fee_text:
        fee_preview = fee_text[:36] + ("..." if len(fee_text) > 36 else "")
        if "무료" in fee_text or "free" in fee_text.lower():
            add_points(5, f"요금 정보: 무료 또는 요금 안내가 확인됩니다. ({fee_preview})")
        else:
            add_points(2, f"요금 정보: 방문 전 참고할 요금 안내가 있습니다. ({fee_preview})")

    for category in category_tokens(scored):
        favorite_count = favorite_category_counts.get(category, 0)
        if favorite_count:
            favorite_points = min(favorite_count * 4, 12)
            add_points(favorite_points, f"찜 기반 취향: 내가 찜한 {category} 계열 장소와 연결됩니다.")
            break

    api_score_boost = safe_float(scored.get("api_score_boost"))
    if api_score_boost:
        api_points = min(api_score_boost * 1.35, 48)
        add_points(api_points, "인기도/동선성: 방문 흐름과 주변 관광지 연결성을 함께 반영했습니다.")

    score += _stable_spread(scored)
    scored["recommendation_score"] = round(score, 1)
    seen_reasons: set[str] = set()
    display_reasons: list[str] = []
    for points, reason in sorted(score_reasons, key=lambda item: item[0], reverse=True):
        if reason in seen_reasons:
            continue
        seen_reasons.add(reason)
        display_reasons.append(f"+{points:.1f}점 · {reason}")
    scored["score_reasons"] = display_reasons[:6]
    scored["display_tags"] = safe_text(scored.get("categories")) or cat_detail or "-"
    return scored


def score_places(
    rows: list[dict[str, Any]],
    preferences: dict[str, Any],
    favorite_category_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    scored = [score_place(row, preferences, favorite_category_counts) for row in rows]
    return sorted(
        scored,
        key=lambda item: (
            1 if _has_image(item) else 0,
            item.get("recommendation_score", 0),
        ),
        reverse=True,
    )
