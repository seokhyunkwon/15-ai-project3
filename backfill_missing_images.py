from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import requests

import collector
import database as db


KOR_SERVICE_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
DETAIL_IMAGE_URL = f"{KOR_SERVICE_BASE_URL}/detailImage2"
PHOTO_GALLERY_BASE_URL = "https://apis.data.go.kr/B551011/PhotoGalleryService1"
PHOTO_GALLERY_SEARCH_URL = f"{PHOTO_GALLERY_BASE_URL}/gallerySearchList1"


def safe_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_service_key(service_key: str) -> str:
    return unquote(service_key.strip())


def api_get(service_key: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "serviceKey": clean_service_key(service_key),
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
        raise RuntimeError(f"API JSON parse failed: {preview}") from exc

    header = payload.get("response", {}).get("header", {})
    result_code = str(header.get("resultCode", "")).strip()
    result_msg = str(header.get("resultMsg", "")).strip()
    if result_code and result_code not in {"0000", "0"}:
        raise RuntimeError(f"API error resultCode={result_code}, resultMsg={result_msg}")
    return payload


def items_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = payload.get("response")
    if not isinstance(response, dict):
        return []

    body = response.get("body")
    if not isinstance(body, dict):
        return []

    items_container = body.get("items")
    if not items_container:
        return []

    if isinstance(items_container, dict):
        items = items_container.get("item", [])
    elif isinstance(items_container, list):
        items = items_container
    else:
        return []

    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def ensure_schemas() -> None:
    collector.ensure_collection_schema()
    db.ensure_recommendation_schema()
    db.ensure_advanced_api_schema()


def fetch_missing_place_rows(limit: int) -> list[dict[str, Any]]:
    limit_sql = f"LIMIT {max(1, int(limit))}" if limit else ""
    return db.fetch_all(
        f"""
        SELECT
          p.place_id,
          p.place_name,
          p.external_id,
          p.content_type_id,
          r.region_name,
          r.province
        FROM places p
        JOIN regions r ON r.region_id = p.region_id
        WHERE COALESCE(p.image_path, '') = ''
          AND COALESCE(p.image_url, '') = ''
          AND COALESCE(p.image_original_url, '') = ''
          AND COALESCE(p.external_id, '') <> ''
        ORDER BY p.place_id
        {limit_sql}
        """
    )


def update_place_image_if_still_missing(
    place_id: int,
    image_path: str | None,
    image_original_url: str | None,
    image_saved_at: str | None,
    priority_score: int,
) -> bool:
    if not image_path and not image_original_url:
        return False

    saved_at = image_saved_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    affected = db.execute(
        """
        UPDATE places
        SET image_path = %s,
            image_original_url = %s,
            image_saved_at = %s,
            has_tour_image = TRUE,
            photo_priority_score = GREATEST(COALESCE(photo_priority_score, 0), %s)
        WHERE place_id = %s
          AND COALESCE(image_path, '') = ''
          AND COALESCE(image_url, '') = ''
          AND COALESCE(image_original_url, '') = ''
        """,
        (image_path, image_original_url, saved_at, priority_score, place_id),
    )
    return affected > 0


def first_image_url_from_detail_item(item: dict[str, Any]) -> str | None:
    for key in ("originimgurl", "smallimageurl", "imgurl", "imageurl"):
        url = safe_text(item.get(key))
        if url:
            return url
    return None


def fetch_detail_image_urls(service_key: str, content_id: str, limit: int) -> list[str]:
    payload = api_get(
        service_key,
        DETAIL_IMAGE_URL,
        {
            "contentId": content_id,
            "imageYN": "Y",
            "subImageYN": "Y",
            "numOfRows": max(1, int(limit)),
            "pageNo": 1,
        },
    )
    urls: list[str] = []
    for item in items_from_payload(payload):
        url = first_image_url_from_detail_item(item)
        if url and url not in urls:
            urls.append(url)
    return urls


def photo_external_id(item: dict[str, Any], image_url: str | None) -> str:
    content_id = safe_text(item.get("galContentId")) or safe_text(item.get("contentid"))
    if content_id:
        return content_id[:120]

    digest_source = "|".join(
        safe_text(item.get(key)) or ""
        for key in ("galTitle", "galWebImageUrl", "galPhotographyLocation")
    )
    if image_url:
        digest_source += f"|{image_url}"
    return hashlib.sha1(digest_source.encode("utf-8")).hexdigest()


def tour_photo_row(
    item: dict[str, Any],
    region_name: str | None,
    place_name: str | None,
) -> dict[str, Any] | None:
    image_url = (
        safe_text(item.get("galWebImageUrl"))
        or safe_text(item.get("galImageUrl"))
        or safe_text(item.get("imageUrl"))
    )
    title = safe_text(item.get("galTitle")) or place_name
    if not image_url and not title:
        return None

    return {
        "external_id": photo_external_id(item, image_url),
        "region_name": region_name,
        "place_name": place_name,
        "title": title,
        "image_url": image_url,
        "location": safe_text(item.get("galPhotographyLocation")),
        "photographer": safe_text(item.get("galPhotographer")),
        "shot_date": safe_text(item.get("galPhotographyMonth")),
        "keywords": safe_text(item.get("galSearchKeyword")),
        "raw_json": item,
    }


def keyword_candidates(region_name: str | None, place_name: str | None) -> list[str]:
    candidates: list[str] = []
    if region_name and place_name:
        candidates.append(f"{region_name} {place_name}")
    if place_name:
        candidates.append(place_name)
    return list(dict.fromkeys(candidates))


def fetch_tour_photo_rows(
    service_key: str,
    region_name: str | None,
    place_name: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for keyword in keyword_candidates(region_name, place_name):
        payload = api_get(
            service_key,
            PHOTO_GALLERY_SEARCH_URL,
            {
                "arrange": "A",
                "keyword": keyword,
                "numOfRows": max(1, int(limit)),
                "pageNo": 1,
            },
        )
        for item in items_from_payload(payload):
            row = tour_photo_row(item, region_name, place_name)
            if not row:
                continue
            external_id = str(row["external_id"])
            if external_id in seen_ids:
                continue
            seen_ids.add(external_id)
            rows.append(row)

        if rows:
            break

    return rows


def save_representative_image(
    image_url: str | None,
    source_name: str,
    file_stem: str,
) -> tuple[str | None, str | None, str | None]:
    if not image_url:
        return None, None, None
    return collector.save_image_from_url(image_url, "places", f"{file_stem}_{source_name}")


def backfill_missing_images(
    service_key: str,
    limit: int,
    detail_image_limit: int,
    photo_limit: int,
    sleep_seconds: float,
    dry_run: bool,
) -> dict[str, int]:
    ensure_schemas()
    places = fetch_missing_place_rows(limit)
    stats = {
        "candidates": len(places),
        "detail_checked": 0,
        "detail_filled": 0,
        "photo_checked": 0,
        "photo_rows_saved": 0,
        "photo_filled": 0,
        "failed": 0,
    }

    for place in places:
        place_id = int(place["place_id"])
        place_name = safe_text(place.get("place_name"))
        region_name = safe_text(place.get("region_name"))
        content_id = safe_text(place.get("external_id"))
        file_stem = content_id or str(place_id)
        filled = False

        if content_id:
            try:
                stats["detail_checked"] += 1
                detail_urls = fetch_detail_image_urls(service_key, content_id, detail_image_limit)
                if detail_urls:
                    image_path, original_url, saved_at = save_representative_image(
                        detail_urls[0],
                        "detail",
                        file_stem,
                    )
                    if dry_run:
                        filled = True
                    else:
                        filled = update_place_image_if_still_missing(
                            place_id,
                            image_path,
                            original_url,
                            saved_at,
                            priority_score=20,
                        )
                    if filled:
                        stats["detail_filled"] += 1
            except Exception as exc:
                stats["failed"] += 1
                print(f"[detailImage2 failed] place_id={place_id}, content_id={content_id}: {exc}")

        if not filled:
            try:
                stats["photo_checked"] += 1
                photo_rows = fetch_tour_photo_rows(service_key, region_name, place_name, photo_limit)
                stats["photo_rows_saved"] += len(photo_rows)

                if not dry_run:
                    for row in photo_rows:
                        db.upsert_tour_photo(row)

                first_photo_url = next((safe_text(row.get("image_url")) for row in photo_rows if row.get("image_url")), None)
                if first_photo_url:
                    image_path, original_url, saved_at = save_representative_image(
                        first_photo_url,
                        "photo",
                        file_stem,
                    )
                    if dry_run:
                        filled = True
                    else:
                        filled = update_place_image_if_still_missing(
                            place_id,
                            image_path,
                            original_url,
                            saved_at,
                            priority_score=15,
                        )
                    if filled:
                        stats["photo_filled"] += 1
            except Exception as exc:
                stats["failed"] += 1
                print(f"[PhotoGallery failed] place_id={place_id}, keyword={region_name} {place_name}: {exc}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if not dry_run:
        db.log_tour_api_usage(
            "detailImage2",
            "Korea Tourism Organization KorService2 detailImage2",
            DETAIL_IMAGE_URL,
            "SUCCESS",
            stats["detail_filled"],
            f"Missing place image backfill detailImage2 stats={stats}",
        )
        db.log_tour_api_usage(
            "PhotoGalleryService1",
            "Korea Tourism Organization PhotoGalleryService1",
            PHOTO_GALLERY_SEARCH_URL,
            "SUCCESS",
            stats["photo_rows_saved"],
            f"Missing place image backfill photo gallery stats={stats}",
        )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill missing place images without rerunning the full collector.")
    parser.add_argument("--service-key", default=None, help="TourAPI service key. Defaults to env/secrets used by collector.py.")
    parser.add_argument("--limit", type=int, default=100, help="Max missing places to process in one run. Use 0 for all.")
    parser.add_argument("--detail-image-limit", type=int, default=10, help="Max detailImage2 rows per place.")
    parser.add_argument("--photo-limit", type=int, default=5, help="Max PhotoGallery rows per keyword.")
    parser.add_argument("--sleep", type=float, default=0.15, help="Delay between places to be gentle on APIs.")
    parser.add_argument("--dry-run", action="store_true", help="Call APIs but do not update DB rows.")
    args = parser.parse_args()

    key = args.service_key or collector.configured_service_key()
    if not key:
        raise SystemExit("TourAPI service key is required. Set TOUR_API_SERVICE_KEY or pass --service-key.")

    stats = backfill_missing_images(
        service_key=key,
        limit=args.limit,
        detail_image_limit=args.detail_image_limit,
        photo_limit=args.photo_limit,
        sleep_seconds=args.sleep,
        dry_run=args.dry_run,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
