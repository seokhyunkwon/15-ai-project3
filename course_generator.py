from __future__ import annotations

from typing import Any

from recommender import safe_text


COURSE_SLOTS = {
    "반나절": ["오전", "점심", "오후"],
    "당일치기": ["오전", "점심", "오후", "카페", "저녁", "야경"],
    "1박 2일": ["1일차 오전", "1일차 점심", "1일차 오후", "1일차 저녁", "2일차 오전", "2일차 점심", "2일차 오후"],
}

SLOT_KEYWORDS = {
    "오전": ["관광지", "자연", "역사", "문화", "공원", "해변"],
    "점심": ["미식", "음식", "식당", "맛집", "시장"],
    "오후": ["관광지", "자연", "문화", "사진", "마을", "거리"],
    "카페": ["카페", "커피", "디저트", "미식"],
    "저녁": ["미식", "음식", "식당", "맛집"],
    "야경": ["야간", "야경", "전망", "타워", "대교", "해변"],
}


def place_text(place: dict[str, Any]) -> str:
    return " ".join(
        safe_text(place.get(key))
        for key in ("place_name", "categories", "tags", "overview", "address")
        if place.get(key)
    )


def has_image(place: dict[str, Any]) -> bool:
    return any(safe_text(place.get(key)) for key in ("image_path", "image_url", "image_original_url"))


def brief_description(value: Any, fallback: str = "소개 정보가 없습니다.", max_length: int = 180) -> str:
    text = " ".join(safe_text(value).split())
    if not text:
        return fallback
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def slot_keywords(slot: str) -> list[str]:
    for key, keywords in SLOT_KEYWORDS.items():
        if key in slot:
            return keywords
    return SLOT_KEYWORDS["오후"]


def pick_place(
    places: list[dict[str, Any]],
    used_place_ids: set[int],
    keywords: list[str],
) -> dict[str, Any] | None:
    keyword_matches = []
    fallback = []
    for place in places:
        place_id = int(place.get("place_id") or 0)
        if not place_id or place_id in used_place_ids:
            continue
        text = place_text(place)
        if any(keyword in text for keyword in keywords):
            keyword_matches.append(place)
        else:
            fallback.append(place)
    candidates = keyword_matches or fallback
    image_candidates = [place for place in candidates if has_image(place)]
    return (image_candidates or candidates or [None])[0]


def generate_course(scored_places: list[dict[str, Any]], duration: str) -> list[dict[str, Any]]:
    slots = COURSE_SLOTS.get(duration, COURSE_SLOTS["당일치기"])
    used_place_ids: set[int] = set()
    course: list[dict[str, Any]] = []

    for slot in slots:
        place = pick_place(scored_places, used_place_ids, slot_keywords(slot))
        if not place:
            continue
        place_id = int(place.get("place_id") or 0)
        used_place_ids.add(place_id)
        course.append(
            {
                "time_slot": slot,
                "place_id": place_id,
                "place_name": safe_text(place.get("place_name"), "이름 없음"),
                "category": safe_text(place.get("categories"), "-"),
                "address": safe_text(place.get("address"), "주소 정보 없음"),
                "recommendation_score": place.get("recommendation_score", 0),
                "score_reasons": place.get("score_reasons") or [],
                "description": brief_description(place.get("overview")),
                "image_path": place.get("image_path"),
                "image_url": place.get("image_url"),
                "image_original_url": place.get("image_original_url"),
                "source_url": place.get("source_url"),
                "latitude": place.get("latitude"),
                "longitude": place.get("longitude"),
            }
        )
    return course


def course_description(course: list[dict[str, Any]], duration: str, transport: str) -> str:
    if not course:
        return "조건에 맞는 코스를 만들 장소가 아직 부족합니다."
    first = course[0]["place_name"]
    last = course[-1]["place_name"]
    return f"{duration} 일정으로 {first}에서 시작해 {last}까지 이어지는 {transport} 기준 추천 코스입니다."
