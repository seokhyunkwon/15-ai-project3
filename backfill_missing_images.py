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

TARGETS: dict[str, dict[str, Any]] = {
    "places": {
        "table": "places",
        "pk": "place_id",
        "name_col": "place_name",
        "folder": "places",
        "has_image_url_col": True,
        "extra_update": "has_tour_image = TRUE, photo_priority_score = GREATEST(COALESCE(photo_priority_score, 0), %s)",
        "extra_params": lambda score: [score],
    },
    "restaurants": {
        "table": "restaurants",
        "pk": "restaurant_id",
        "name_col": "restaurant_name",
        "folder": "restaurants",
        "has_image_url_col": False,
        "extra_update": None,
        "extra_params": lambda score: [],
    },
    "accommodations": {
        "table": "accommodations",
        "pk": "accommodation_id",
        "name_col": "accommodation_name",
        "folder": "accommodations",
        "has_image_url_col": False,
        "extra_update": None,
        "extra_params": lambda score: [],
    },
    "festivals": {
        "table": "festivals",
        "pk": "festival_id",
        "name_col": "festival_name",
        "folder": "festivals",
        "has_image_url_col": False,
        "extra_update": None,
        "extra_params": lambda score: [],
    },
}


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


def existing_columns(table: str) -> set[str]:
    rows = db.fetch_all(
        f"""
        SELECT COLUMN_NAME AS column_name
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = '{table}'
        """
    )
    return {str(row.get("column_name") or row.get("COLUMN_NAME")) for row in rows}


def image_empty_condition(table_alias: str, has_image_url_col: bool) -> str:
    parts = [
        f"COALESCE({table_alias}.image_path, '') = ''",
        f"COALESCE({table_alias}.image_original_url, '') = ''",
    ]
    if has_image_url_col:
        parts.insert(1, f"COALESCE({table_alias}.image_url, '') = ''")
    return " AND ".join(parts)


def fetch_missing_rows(target_name: str, limit: int) -> list[dict[str, Any]]:
    target = TARGETS[target_name]
    table = target["table"]
    pk = target["pk"]
    name_col = target["name_col"]
    has_image_url_col = bool(target["has_image_url_col"])
    limit_sql = f"LIMIT {max(1, int(limit))}" if limit else ""

    return db.fetch_all(
        f"""
        SELECT
          t.{pk} AS row_id,
          t.{name_col} AS item_name,
          t.external_id,
          t.content_type_id,
          r.region_name,
          r.province
        FROM {table} t
        JOIN regions r ON r.region_id = t.region_id
        WHERE {image_empty_condition('t', has_image_url_col)}
          AND COALESCE(t.external_id, '') <> ''
        ORDER BY t.{pk}
        {limit_sql}
        """
    )


def update_image_if_still_missing(
    target_name: str,
    row_id: int,
    image_path: str | None,
    image_original_url: str | None,
    image_saved_at: str | None,
    priority_score: int,
) -> bool:
    if not image_path and not image_original_url:
        return False

    target = TARGETS[target_name]
    table = target["table"]
    pk = target["pk"]
    has_image_url_col = bool(target["has_image_url_col"])
    saved_at = image_saved_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    set_parts = [
        "image_path = %s",
        "image_original_url = %s",
        "image_saved_at = %s",
    ]
    params: list[Any] = [image_path, image_original_url, saved_at]

    # places 테이블에만 있는 사진 점수 컬럼은 있을 때만 업데이트합니다.
    columns = existing_columns(table)
    if target.get("extra_update") and {"has_tour_image", "photo_priority_score"}.issubset(columns):
        set_parts.append(str(target["extra_update"]))
        params.extend(target["extra_params"](priority_score))

    params.append(row_id)

    affected = db.execute(
        f"""
        UPDATE {table}
        SET {', '.join(set_parts)}
        WHERE {pk} = %s
          AND {image_empty_condition('', has_image_url_col).replace('.image', 'image')}
        """,
        tuple(params),
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
    item_name: str | None,
) -> dict[str, Any] | None:
    image_url = (
        safe_text(item.get("galWebImageUrl"))
        or safe_text(item.get("galImageUrl"))
        or safe_text(item.get("imageUrl"))
    )
    title = safe_text(item.get("galTitle")) or item_name
    if not image_url and not title:
        return None

    return {
        "external_id": photo_external_id(item, image_url),
        "region_name": region_name,
        "place_name": item_name,
        "title": title,
        "image_url": image_url,
        "location": safe_text(item.get("galPhotographyLocation")),
        "photographer": safe_text(item.get("galPhotographer")),
        "shot_date": safe_text(item.get("galPhotographyMonth")),
        "keywords": safe_text(item.get("galSearchKeyword")),
        "raw_json": item,
    }


def keyword_candidates(region_name: str | None, item_name: str | None) -> list[str]:
    candidates: list[str] = []
    if region_name and item_name:
        candidates.append(f"{region_name} {item_name}")
    if item_name:
        candidates.append(item_name)
    return list(dict.fromkeys(candidates))


def fetch_tour_photo_rows(
    service_key: str,
    region_name: str | None,
    item_name: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for keyword in keyword_candidates(region_name, item_name):
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
            row = tour_photo_row(item, region_name, item_name)
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
    folder: str,
    source_name: str,
    file_stem: str,
) -> tuple[str | None, str | None, str | None]:
    if not image_url:
        return None, None, None
    return collector.save_image_from_url(image_url, folder, f"{file_stem}_{source_name}")


def process_target(
    target_name: str,
    service_key: str,
    limit: int,
    detail_image_limit: int,
    photo_limit: int,
    sleep_seconds: float,
    dry_run: bool,
) -> dict[str, int]:
    rows = fetch_missing_rows(target_name, limit)
    target = TARGETS[target_name]
    folder = target["folder"]

    stats = {
        "candidates": len(rows),
        "detail_checked": 0,
        "detail_filled": 0,
        "photo_checked": 0,
        "photo_rows_found": 0,
        "photo_filled": 0,
        "failed": 0,
    }

    for row in rows:
        row_id = int(row["row_id"])
        item_name = safe_text(row.get("item_name"))
        region_name = safe_text(row.get("region_name"))
        content_id = safe_text(row.get("external_id"))
        file_stem = f"{target_name}_{content_id or row_id}"
        filled = False

        if content_id:
            try:
                stats["detail_checked"] += 1
                detail_urls = fetch_detail_image_urls(service_key, content_id, detail_image_limit)
                if detail_urls:
                    image_path, original_url, saved_at = save_representative_image(
                        detail_urls[0],
                        folder,
                        "detail",
                        file_stem,
                    )
                    if dry_run:
                        filled = True
                    else:
                        filled = update_image_if_still_missing(
                            target_name,
                            row_id,
                            image_path,
                            original_url,
                            saved_at,
                            priority_score=20,
                        )
                    if filled:
                        stats["detail_filled"] += 1
            except Exception as exc:
                stats["failed"] += 1
                print(f"[detailImage2 failed] target={target_name}, id={row_id}, content_id={content_id}: {exc}")

        if not filled:
            try:
                stats["photo_checked"] += 1
                photo_rows = fetch_tour_photo_rows(service_key, region_name, item_name, photo_limit)
                stats["photo_rows_found"] += len(photo_rows)

                first_photo_url = next(
                    (safe_text(photo_row.get("image_url")) for photo_row in photo_rows if photo_row.get("image_url")),
                    None,
                )
                if first_photo_url:
                    image_path, original_url, saved_at = save_representative_image(
                        first_photo_url,
                        folder,
                        "photo",
                        file_stem,
                    )
                    if dry_run:
                        filled = True
                    else:
                        filled = update_image_if_still_missing(
                            target_name,
                            row_id,
                            image_path,
                            original_url,
                            saved_at,
                            priority_score=15,
                        )
                    if filled:
                        stats["photo_filled"] += 1
            except Exception as exc:
                stats["failed"] += 1
                print(f"[PhotoGallery failed] target={target_name}, id={row_id}, keyword={region_name} {item_name}: {exc}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return stats


def backfill_missing_images(
    service_key: str,
    targets: list[str],
    limit: int,
    detail_image_limit: int,
    photo_limit: int,
    sleep_seconds: float,
    dry_run: bool,
) -> dict[str, Any]:
    ensure_schemas()
    selected_targets = list(TARGETS.keys()) if "all" in targets else targets
    result: dict[str, Any] = {}

    for target_name in selected_targets:
        if target_name not in TARGETS:
            raise ValueError(f"Unknown target: {target_name}")
        print(f"\n[{target_name}] missing image backfill start")
        result[target_name] = process_target(
            target_name=target_name,
            service_key=service_key,
            limit=limit,
            detail_image_limit=detail_image_limit,
            photo_limit=photo_limit,
            sleep_seconds=sleep_seconds,
            dry_run=dry_run,
        )

    if not dry_run:
        try:
            db.log_tour_api_usage(
                "detailImage2",
                "Korea Tourism Organization KorService2 detailImage2",
                DETAIL_IMAGE_URL,
                "SUCCESS",
                sum(int(v.get("detail_filled", 0)) for v in result.values() if isinstance(v, dict)),
                f"Missing image backfill all targets stats={result}",
            )
            db.log_tour_api_usage(
                "PhotoGalleryService1",
                "Korea Tourism Organization PhotoGalleryService1",
                PHOTO_GALLERY_SEARCH_URL,
                "SUCCESS",
                sum(int(v.get("photo_rows_found", 0)) for v in result.values() if isinstance(v, dict)),
                f"Missing image backfill photo gallery stats={result}",
            )
        except Exception as exc:
            print(f"[tour_api_usage log skipped] {exc}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill missing representative images for places, restaurants, accommodations, and festivals."
    )
    parser.add_argument("--service-key", default=None, help="TourAPI service key. Defaults to env/secrets used by collector.py.")
    parser.add_argument(
        "--target",
        choices=["all", *TARGETS.keys()],
        default="all",
        help="Which table to process. Default: all",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max missing rows per target table. Use 0 for all.")
    parser.add_argument("--detail-image-limit", type=int, default=10, help="Max detailImage2 rows per row.")
    parser.add_argument("--photo-limit", type=int, default=5, help="Max PhotoGallery rows per keyword.")
    parser.add_argument("--sleep", type=float, default=0.15, help="Delay between rows to be gentle on APIs.")
    parser.add_argument("--dry-run", action="store_true", help="Call APIs but do not update DB rows.")
    args = parser.parse_args()

    key = args.service_key or collector.configured_service_key()
    if not key:
        raise SystemExit("TourAPI service key is required. Set TOUR_API_SERVICE_KEY or pass --service-key.")

    stats = backfill_missing_images(
        service_key=key,
        targets=[args.target],
        limit=args.limit,
        detail_image_limit=args.detail_image_limit,
        photo_limit=args.photo_limit,
        sleep_seconds=args.sleep,
        dry_run=args.dry_run,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
