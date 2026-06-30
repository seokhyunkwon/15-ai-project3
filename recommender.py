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


def _breakdown_item(label: str, points: float, detail: str) -> dict[str, Any]:
    return {"label": label, "points": round(float(points), 1), "detail": detail}


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
    reasons: list[str] = []
    breakdown: list[dict[str, Any]] = []

    def add_points(label: str, points: float, detail: str) -> None:
        nonlocal score
        if points <= 0:
            return
        score += points
        reasons.append(detail)
        breakdown.append(_breakdown_item(label, points, detail))

    destination = safe_text(preferences.get("destination"))
    region_name = safe_text(scored.get("region_name"))
    if destination and destination != "전국" and (destination in region_name or region_name in destination):
        add_points("지역 일치", 18, f"선택한 지역({destination})의 TourAPI/DB 후보입니다.")
    elif destination == "전국":
        add_points("전국 후보", 8, "전국 검색 조건에 포함된 후보입니다.")

    category_matches = matching_categories(scored, preferences)
    if category_matches:
        label = ", ".join(category_matches[:3])
        add_points("카테고리 일치", 25, f"선택 카테고리({label})와 DB 카테고리 또는 TourAPI 분류가 일치합니다.")

    content_type_id = safe_text(scored.get("content_type_id"))
    if content_type_id:
        content_type_name = TOUR_CONTENT_TYPE_NAMES.get(content_type_id, safe_text(scored.get("content_type_name")) or content_type_id)
        scored["content_type_name"] = content_type_name
        add_points("TourAPI 타입 확인", 8, f"국문 관광정보 서비스 contenttypeid={content_type_id}({content_type_name}) 항목입니다.")

    cat_detail = "/".join(safe_text(scored.get(key)) for key in ("cat1", "cat2", "cat3") if safe_text(scored.get(key)))
    if cat_detail:
        add_points("세부 분류 보유", 7, f"TourAPI 세부 분류({cat_detail})가 저장되어 있습니다.")

    if _has_image(scored):
        add_points("대표 사진 보유", 10, "한국관광공사 이미지 또는 관광사진 데이터가 있어 카드/코스에 우선 노출됩니다.")

    if _has_official_detail(scored):
        add_points("상세정보 보유", 8, "detailCommon/detailIntro/detailInfo 기반 상세 정보가 저장되어 있습니다.")

    fee_text = safe_text(scored.get("use_fee") or scored.get("fee_info"))
    if fee_text:
        if "무료" in fee_text:
            add_points("무료/요금 정보", 7, f"공식 상세정보에 요금 정보가 있습니다: {fee_text[:80]}")
        else:
            add_points("요금 정보 보유", 4, f"공식 상세정보의 요금 안내가 있습니다: {fee_text[:80]}")

    rating = safe_float(scored.get("average_rating"))
    review_count = safe_int(scored.get("review_count"))
    if rating and review_count:
        rating_points = min(rating * 5, 25)
        add_points("사용자 평점", rating_points, f"사이트 리뷰 {review_count}개 기준 평균 평점 {rating:.2f}점입니다.")

    for category in category_tokens(scored):
        favorite_count = favorite_category_counts.get(category, 0)
        if favorite_count:
            favorite_points = min(favorite_count * 4, 12)
            add_points("찜 성향", favorite_points, f"사용자가 찜한 {category} 카테고리와 연결됩니다.")
            break

    api_score_boost = safe_float(scored.get("api_score_boost"))
    if api_score_boost:
        api_points = min(api_score_boost, 36)
        api_reasons = [safe_text(reason) for reason in scored.get("api_reasons") or [] if safe_text(reason)]
        api_reason = " / ".join(api_reasons[:3]) or "방문자·중심 관광지·연관 관광지·혼잡도 공공데이터가 반영되었습니다."
        add_points("공공데이터 보정", api_points, api_reason)

    if not breakdown:
        breakdown.append(_breakdown_item("공식 데이터 부족", 0, "지역 후보에는 포함되지만 카테고리/사진/상세정보/방문자 지표가 아직 충분히 저장되지 않았습니다."))
        reasons.append("공식 API 상세정보를 더 수집하면 추천 근거가 보강됩니다.")

    scored["recommendation_score"] = round(score, 1)
    scored["recommendation_reasons"] = reasons[:6]
    scored["recommendation_breakdown"] = breakdown
    scored["display_tags"] = safe_text(scored.get("categories")) or cat_detail or "-"
    return scored


def score_places(
    rows: list[dict[str, Any]],
    preferences: dict[str, Any],
    favorite_category_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    scored = [score_place(row, preferences, favorite_category_counts) for row in rows]
    return sorted(scored, key=lambda item: item.get("recommendation_score", 0), reverse=True)
