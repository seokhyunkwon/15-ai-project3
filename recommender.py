from __future__ import annotations

from decimal import Decimal
from typing import Any


TRAVEL_STYLES = [
    "맛집 위주",
    "관광지 위주",
    "카페 위주",
    "자연 경관",
    "사진 명소",
    "가족 여행",
    "연인 여행",
    "혼자 여행",
]

COMPANION_TYPES = ["혼자", "친구", "연인", "가족"]
BUDGET_LEVELS = ["저렴", "보통", "비쌈"]
TRANSPORT_TYPES = ["도보", "대중교통", "자가용"]
WEATHER_TYPES = ["맑음", "비", "흐림", "더움", "추움"]
DURATION_TYPES = ["반나절", "당일치기", "1박 2일"]


STYLE_KEYWORDS = {
    "맛집 위주": ["미식", "음식", "맛집", "식당", "시장", "먹거리"],
    "관광지 위주": ["관광지", "명소", "역사", "문화", "축제", "코스"],
    "카페 위주": ["카페", "커피", "디저트", "로스터"],
    "자연 경관": ["자연", "해변", "해수욕장", "공원", "숲", "산", "바다", "호수", "폭포"],
    "사진 명소": ["사진", "야경", "전망", "타워", "대교", "마을", "거리"],
    "가족 여행": ["가족", "박물관", "공원", "체험", "역사", "문화"],
    "연인 여행": ["연인", "야경", "전망", "카페", "해변", "거리"],
    "혼자 여행": ["혼자", "산책", "미술관", "박물관", "카페", "숲"],
}

WEATHER_RULES = {
    "비": ("실내", 20, "비 오는 날 방문하기 좋은 실내 장소입니다."),
    "맑음": ("야외", 15, "맑은 날 걷기 좋은 야외 장소입니다."),
    "더움": ("실내", 15, "더운 날 쉬어가기 좋은 실내 장소입니다."),
    "추움": ("실내", 15, "추운 날 방문 부담이 적은 실내 장소입니다."),
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


def combined_text(row: dict[str, Any]) -> str:
    parts = [
        row.get("place_name"),
        row.get("categories"),
        row.get("tags"),
        row.get("overview"),
        row.get("address"),
        row.get("recommended_for"),
        row.get("indoor_outdoor"),
    ]
    return " ".join(safe_text(part) for part in parts if part)


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def category_tokens(row: dict[str, Any]) -> list[str]:
    raw = safe_text(row.get("categories"))
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def score_place(
    row: dict[str, Any],
    preferences: dict[str, Any],
    favorite_category_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    scored = dict(row)
    text = combined_text(scored)
    categories = category_tokens(scored)
    favorite_category_counts = favorite_category_counts or {}

    score = 0.0
    reasons: list[str] = []

    style = safe_text(preferences.get("travel_style"))
    style_keywords = STYLE_KEYWORDS.get(style, [])
    if style_keywords and contains_any(text, style_keywords):
        score += 30
        reasons.append(f"사용자가 선택한 {style} 여행 스타일과 잘 맞습니다.")

    companion = safe_text(preferences.get("companion"))
    companion_keywords = STYLE_KEYWORDS.get(f"{companion} 여행", [companion])
    if companion and contains_any(text, companion_keywords):
        score += 15
        reasons.append(f"{companion} 여행에 적합한 장소입니다.")

    weather = safe_text(preferences.get("weather"))
    indoor_outdoor = safe_text(scored.get("indoor_outdoor"), "혼합")
    if weather in WEATHER_RULES:
        target, points, message = WEATHER_RULES[weather]
        if indoor_outdoor == target or indoor_outdoor == "혼합":
            score += points
            reasons.append(message)
    elif weather == "흐림":
        score += 5
        reasons.append("흐린 날에도 무난하게 방문하기 좋은 장소입니다.")

    budget = safe_text(preferences.get("budget"))
    place_budget = safe_text(scored.get("budget_level"))
    if budget and place_budget and budget == place_budget:
        score += 10
        reasons.append(f"예산 조건({budget})과 맞습니다.")

    rating = safe_float(scored.get("average_rating"))
    if rating:
        rating_points = min(rating * 8, 40)
        score += rating_points
        if rating >= 4.5:
            reasons.append("평점이 높아 우선 추천되었습니다.")

    review_count = safe_int(scored.get("review_count"))
    if review_count:
        score += min(review_count * 2, 12)
        reasons.append("리뷰가 있어 선택 신뢰도가 높습니다.")

    for category in categories:
        favorite_count = favorite_category_counts.get(category, 0)
        if favorite_count:
            score += min(favorite_count * 5, 15)
            reasons.append(f"찜한 {category} 카테고리와 비슷한 장소입니다.")
            break

    if not reasons:
        reasons.append("지역과 기본 조건에 맞는 후보 장소입니다.")

    scored["recommendation_score"] = round(score, 1)
    scored["recommendation_reasons"] = reasons[:4]
    scored["display_tags"] = safe_text(scored.get("tags")) or safe_text(scored.get("categories"), "-")
    return scored


def score_places(
    rows: list[dict[str, Any]],
    preferences: dict[str, Any],
    favorite_category_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    scored = [score_place(row, preferences, favorite_category_counts) for row in rows]
    return sorted(scored, key=lambda item: item.get("recommendation_score", 0), reverse=True)
