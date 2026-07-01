from __future__ import annotations

import argparse
import json
import re
from datetime import date
from typing import Any

import collector
import database as db


MAJOR_ALIASES = {
    "서울": "서울",
    "서울시": "서울",
    "서울특별시": "서울",
    "인천": "인천",
    "인천시": "인천",
    "인천광역시": "인천",
    "대전": "대전",
    "대전시": "대전",
    "대전광역시": "대전",
    "대구": "대구",
    "대구시": "대구",
    "대구광역시": "대구",
    "광주": "광주",
    "광주시": "광주",
    "광주광역시": "광주",
    "부산": "부산",
    "부산시": "부산",
    "부산광역시": "부산",
    "울산": "울산",
    "울산시": "울산",
    "울산광역시": "울산",
    "세종": "세종특별자치시",
    "세종시": "세종특별자치시",
    "경기": "경기도",
    "경기도": "경기도",
    "강원": "강원특별자치도",
    "강원도": "강원특별자치도",
    "강원특별자치도": "강원특별자치도",
    "충북": "충청북도",
    "충청북도": "충청북도",
    "충남": "충청남도",
    "충청남도": "충청남도",
    "전북": "전북특별자치도",
    "전라북도": "전북특별자치도",
    "전북특별자치도": "전북특별자치도",
    "전남": "전라남도",
    "전라남도": "전라남도",
    "경북": "경상북도",
    "경상북도": "경상북도",
    "경남": "경상남도",
    "경상남도": "경상남도",
    "제주": "제주특별자치도",
    "제주도": "제주특별자치도",
    "제주특별자치도": "제주특별자치도",
}

TOUR_AREA_CODES = {
    "서울": "1",
    "인천": "2",
    "대전": "3",
    "대구": "4",
    "광주": "5",
    "부산": "6",
    "울산": "7",
    "세종특별자치시": "8",
    "경기도": "31",
    "강원특별자치도": "32",
    "충청북도": "33",
    "충청남도": "34",
    "경상북도": "35",
    "경상남도": "36",
    "전북특별자치도": "37",
    "전라남도": "38",
    "제주특별자치도": "39",
}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def normalize_major_name(value: Any) -> str:
    text = str(value or "").strip()
    return MAJOR_ALIASES.get(text, text)


def parse_target_majors(value: str | None) -> set[str]:
    if not value:
        return set()
    parts = [part.strip() for part in re.split(r"[,，]+", value) if part.strip()]
    return {normalize_major_name(part) for part in parts}


def major_regions(target_names: set[str]) -> list[dict[str, Any]]:
    rows = db.fetch_all(
        """
        SELECT region_id, region_name, province, tour_area_code, tour_sigungu_code
        FROM regions
        WHERE tour_area_code IS NOT NULL
          AND tour_area_code <> ''
          AND (tour_sigungu_code IS NULL OR tour_sigungu_code = '')
        ORDER BY
          CASE WHEN tour_area_code REGEXP '^[0-9]+$' THEN CAST(tour_area_code AS UNSIGNED) ELSE 999 END,
          region_name
        """
    )
    if not target_names:
        return rows
    return [row for row in rows if normalize_major_name(row.get("region_name")) in target_names]


def child_regions(major: dict[str, Any]) -> list[dict[str, Any]]:
    area_code = str(major.get("tour_area_code") or "").strip()
    if not area_code:
        return []
    return db.fetch_all(
        """
        SELECT region_id, region_name, province, tour_area_code, tour_sigungu_code
        FROM regions
        WHERE tour_area_code = %s
          AND tour_sigungu_code IS NOT NULL
          AND tour_sigungu_code <> ''
        ORDER BY
          CASE WHEN tour_sigungu_code REGEXP '^[0-9]+$' THEN CAST(tour_sigungu_code AS UNSIGNED) ELSE 999 END,
          region_name
        """,
        (area_code,),
    )


def ensure_child_regions(service_key: str, major: dict[str, Any]) -> list[dict[str, Any]]:
    children = child_regions(major)
    if children:
        return children

    area_code = str(major.get("tour_area_code") or "").strip()
    if not area_code:
        area_code = TOUR_AREA_CODES.get(normalize_major_name(major.get("region_name")), "")
    if not area_code:
        return []

    try:
        sigungus = collector._api_items(
            service_key,
            collector.TOUR_API_AREA_CODE_URL,
            {"areaCode": area_code, "numOfRows": 300, "pageNo": 1},
        )
    except Exception:
        return []

    area_name = str(major.get("region_name") or major.get("province") or "").strip()
    for sigungu in sigungus:
        sigungu_code = collector._safe_text(sigungu.get("code"))
        sigungu_name = collector._safe_text(sigungu.get("name"))
        if not sigungu_code or not sigungu_name:
            continue
        collector.upsert_region(f"{area_name} {sigungu_name}", area_name, area_code, sigungu_code)

    return child_regions(major)


def fetch_place_rows_for_region(
    service_key: str,
    region: dict[str, Any],
    limit: int,
    page_size: int,
) -> list[dict[str, Any]]:
    area_code = str(region.get("tour_area_code") or "").strip()
    sigungu_code = str(region.get("tour_sigungu_code") or "").strip()
    if not area_code:
        return []

    rows: list[dict[str, Any]] = []
    page_no = 1
    row_limit = max(0, _int(limit))

    while True:
        request_rows = max(1, min(_int(page_size, 100), 1000))
        if row_limit:
            remaining = row_limit - len(rows)
            if remaining <= 0:
                break
            request_rows = min(request_rows, remaining)

        params: dict[str, Any] = {
            "contentTypeId": collector.CONTENT_TYPES["places"],
            "areaCode": area_code,
            "numOfRows": request_rows,
            "pageNo": page_no,
            "arrange": "A",
        }
        if sigungu_code:
            params["sigunguCode"] = sigungu_code

        page_rows, total_count = collector._api_page(service_key, collector.TOUR_API_AREA_BASED_URL, params)
        if not page_rows:
            break

        rows.extend(page_rows)
        if row_limit and len(rows) >= row_limit:
            break
        if total_count and page_no * request_rows >= total_count:
            break
        if len(page_rows) < request_rows:
            break
        page_no += 1

    return rows[:row_limit] if row_limit else rows


def save_place_rows(service_key: str, rows: list[dict[str, Any]], dry_run: bool) -> dict[str, int]:
    stats = {"fetched": len(rows), "saved": 0, "skipped_existing": 0}
    if dry_run:
        return stats

    for row in rows:
        content_id = collector._safe_text(row.get("contentid")) or collector._safe_text(row.get("contentId"))
        if collector._entity_exists_by_external_id("places", content_id):
            stats["skipped_existing"] += 1
            continue
        enriched = collector.enrich_item_with_details(service_key, row)
        if collector.save_tourapi_item("places", enriched):
            stats["saved"] += 1
    return stats


def collect_places_by_area(
    service_key: str,
    majors: list[dict[str, Any]],
    limit_per_area: int,
    page_size: int,
    dry_run: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {"mode": "area", "areas": [], "fetched": 0, "saved": 0, "skipped_existing": 0}
    area_limit = max(0, _int(limit_per_area))

    for major in majors:
        targets = ensure_child_regions(service_key, major) or [major]
        area_rows: list[dict[str, Any]] = []
        target_results: list[dict[str, Any]] = []

        for target in targets:
            remaining = 0 if area_limit == 0 else area_limit - len(area_rows)
            if area_limit and remaining <= 0:
                break
            rows = fetch_place_rows_for_region(service_key, target, remaining, page_size)
            area_rows.extend(rows)
            target_results.append({"region_name": target.get("region_name"), "fetched": len(rows)})

        save_stats = save_place_rows(service_key, area_rows[:area_limit] if area_limit else area_rows, dry_run)
        area_result = {
            "region_name": major.get("region_name"),
            "fetched": save_stats["fetched"],
            "saved": save_stats["saved"],
            "skipped_existing": save_stats["skipped_existing"],
            "targets": target_results,
        }
        result["areas"].append(area_result)
        result["fetched"] += save_stats["fetched"]
        result["saved"] += save_stats["saved"]
        result["skipped_existing"] += save_stats["skipped_existing"]
        print(
            f"[관광지/광역] {area_result['region_name']}: "
            f"조회 {area_result['fetched']}건, 저장 {area_result['saved']}건, 기존 {area_result['skipped_existing']}건"
        )

    return result


def collect_places_by_sigungu(
    service_key: str,
    majors: list[dict[str, Any]],
    limit_per_sigungu: int,
    page_size: int,
    dry_run: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {"mode": "sigungu", "areas": [], "fetched": 0, "saved": 0, "skipped_existing": 0}

    for major in majors:
        targets = ensure_child_regions(service_key, major) or [major]
        area_result: dict[str, Any] = {
            "region_name": major.get("region_name"),
            "targets": [],
            "fetched": 0,
            "saved": 0,
            "skipped_existing": 0,
        }

        for target in targets:
            rows = fetch_place_rows_for_region(service_key, target, limit_per_sigungu, page_size)
            save_stats = save_place_rows(service_key, rows, dry_run)
            target_result = {
                "region_name": target.get("region_name"),
                "fetched": save_stats["fetched"],
                "saved": save_stats["saved"],
                "skipped_existing": save_stats["skipped_existing"],
            }
            area_result["targets"].append(target_result)
            area_result["fetched"] += save_stats["fetched"]
            area_result["saved"] += save_stats["saved"]
            area_result["skipped_existing"] += save_stats["skipped_existing"]
            print(
                f"[관광지/시군구] {target_result['region_name']}: "
                f"조회 {target_result['fetched']}건, 저장 {target_result['saved']}건, 기존 {target_result['skipped_existing']}건"
            )

        result["areas"].append(area_result)
        result["fetched"] += area_result["fetched"]
        result["saved"] += area_result["saved"]
        result["skipped_existing"] += area_result["skipped_existing"]

    return result


def collect_festivals(service_key: str, limit: int, dry_run: bool) -> dict[str, int]:
    if dry_run:
        rows = []
        festival_limit = max(0, _int(limit))
        areas = collector._api_items(service_key, collector.TOUR_API_AREA_CODE_URL, {"numOfRows": 100, "pageNo": 1})
        for area in areas:
            area_code = collector._safe_text(area.get("code"))
            if not area_code:
                continue
            page_rows, _ = collector._api_page(
                service_key,
                collector.TOUR_API_FESTIVAL_URL,
                {
                    "eventStartDate": f"{date.today().year}0101",
                    "areaCode": area_code,
                    "numOfRows": 100 if not festival_limit else min(festival_limit, 100),
                    "pageNo": 1,
                    "arrange": "A",
                },
            )
            rows.extend(page_rows)
            if festival_limit and len(rows) >= festival_limit:
                break
        return {"fetched": len(rows[:festival_limit] if festival_limit else rows), "saved": 0}

    festivals = collector.fetch_tourapi_festivals(service_key, limit=limit)
    stats = {"fetched": len(festivals), "saved": 0}
    for festival in festivals:
        collector._upsert_row("festivals", festival, skip_update={"region_id", "festival_name", "start_date"})
        stats["saved"] += 1
    print(f"[축제] 조회 {stats['fetched']}건, 저장 {stats['saved']}건")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="TourAPI 관광지와 축제만 제한 수집합니다.")
    parser.add_argument("--service-key", default=None, help="공공데이터포털 TourAPI 서비스키. 생략하면 환경변수/secrets.toml 사용")
    parser.add_argument("--target-majors", default=None, help='수집할 광역 지역. 예: "충북,충남,전북,전남,경북,경남,제주"')
    parser.add_argument("--place-mode", choices=("area", "sigungu"), default="area", help="area=광역별 제한, sigungu=시군구별 제한")
    parser.add_argument("--place-limit", type=int, default=50, help="관광지 수집 개수. area 모드는 광역별, sigungu 모드는 시군구별. 0이면 전체")
    parser.add_argument("--festival-limit", type=int, default=100, help="축제 수집 개수. 0이면 전체")
    parser.add_argument("--page-size", type=int, default=100, help="TourAPI 페이지당 요청 개수")
    parser.add_argument("--skip-places", action="store_true", help="관광지 수집 건너뛰기")
    parser.add_argument("--skip-festivals", action="store_true", help="축제 수집 건너뛰기")
    parser.add_argument("--dry-run", action="store_true", help="조회 대상만 확인하고 DB에는 저장하지 않음")
    args = parser.parse_args()

    service_key = args.service_key or collector.configured_service_key()
    if not service_key:
        raise SystemExit("TourAPI 서비스키가 필요합니다. --service-key 또는 TOUR_API_KEY/TOUR_API_SERVICE_KEY를 설정하세요.")

    collector.ensure_collection_schema()
    collector.sync_regions_from_tourapi(service_key, include_sigungu=True)

    targets = parse_target_majors(args.target_majors)
    majors = major_regions(targets)
    if targets and not majors:
        raise SystemExit(f"대상 광역 지역을 찾지 못했습니다: {', '.join(sorted(targets))}")

    result: dict[str, Any] = {
        "target_majors": [major.get("region_name") for major in majors],
        "dry_run": bool(args.dry_run),
    }

    if not args.skip_places:
        if args.place_mode == "sigungu":
            result["places"] = collect_places_by_sigungu(
                service_key,
                majors,
                limit_per_sigungu=args.place_limit,
                page_size=args.page_size,
                dry_run=args.dry_run,
            )
        else:
            result["places"] = collect_places_by_area(
                service_key,
                majors,
                limit_per_area=args.place_limit,
                page_size=args.page_size,
                dry_run=args.dry_run,
            )

    if not args.skip_festivals:
        result["festivals"] = collect_festivals(service_key, limit=args.festival_limit, dry_run=args.dry_run)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
