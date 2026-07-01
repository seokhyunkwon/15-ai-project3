from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Any

import collector
import database as db


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def missing_place_regions(include_broad_regions: bool = False) -> list[dict[str, Any]]:
    """관광지가 0건인 TourAPI 지역만 반환한다.

    시군구가 있는 광역 지역은 시군구 단위로만 수집한다. 이렇게 해야
    제주특별자치도 전체 호출과 제주시/서귀포시 호출이 중복되지 않는다.
    """
    collector.ensure_collection_schema()
    rows = db.fetch_all(
        """
        SELECT
          r.region_id,
          r.region_name,
          r.province,
          r.tour_area_code,
          r.tour_sigungu_code,
          COUNT(p.place_id) AS place_count
        FROM regions r
        LEFT JOIN places p ON p.region_id = r.region_id
        WHERE r.tour_area_code IS NOT NULL
          AND r.tour_area_code <> ''
        GROUP BY
          r.region_id,
          r.region_name,
          r.province,
          r.tour_area_code,
          r.tour_sigungu_code
        HAVING place_count = 0
        ORDER BY
          CASE WHEN r.tour_area_code REGEXP '^[0-9]+$' THEN CAST(r.tour_area_code AS UNSIGNED) ELSE 999 END,
          CASE
            WHEN r.tour_sigungu_code IS NULL OR r.tour_sigungu_code = '' THEN 0
            WHEN r.tour_sigungu_code REGEXP '^[0-9]+$' THEN CAST(r.tour_sigungu_code AS UNSIGNED)
            ELSE 999
          END,
          r.region_name
        """
    )
    child_area_codes = {
        str(row.get("tour_area_code") or "")
        for row in rows
        if str(row.get("tour_sigungu_code") or "").strip()
    }
    if include_broad_regions:
        return rows
    return [
        row
        for row in rows
        if str(row.get("tour_sigungu_code") or "").strip()
        or str(row.get("tour_area_code") or "") not in child_area_codes
    ]


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
    region_limit = max(0, int(limit or 0))
    while True:
        request_rows = max(1, min(int(page_size or 100), 1000))
        if region_limit:
            remaining = region_limit - len(rows)
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

        if region_limit and len(rows) >= region_limit:
            break
        if total_count and page_no * request_rows >= total_count:
            break
        if len(page_rows) < request_rows:
            break
        page_no += 1

    return rows[:region_limit] if region_limit else rows


def collect_missing_places(service_key: str, limit_per_region: int, page_size: int, dry_run: bool = False) -> dict[str, Any]:
    regions = missing_place_regions()
    stats: dict[str, Any] = {
        "target_regions": len(regions),
        "fetched": 0,
        "inserted_or_updated": 0,
        "regions": [],
    }

    for region in regions:
        rows = fetch_place_rows_for_region(service_key, region, limit_per_region, page_size)
        region_result = {
            "region_name": region.get("region_name"),
            "fetched": len(rows),
            "saved": 0,
        }
        stats["fetched"] += len(rows)

        if not dry_run:
            for row in rows:
                content_id = collector._safe_text(row.get("contentid")) or collector._safe_text(row.get("contentId"))
                if collector._entity_exists_by_external_id("places", content_id):
                    continue
                enriched = collector.enrich_item_with_details(service_key, row)
                if collector.save_tourapi_item("places", enriched):
                    region_result["saved"] += 1
                    stats["inserted_or_updated"] += 1

        stats["regions"].append(region_result)
        print(f"[관광지] {region_result['region_name']}: 조회 {region_result['fetched']}건, 저장 {region_result['saved']}건")

    return stats


def collect_festivals(service_key: str, limit: int, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        festival_limit = max(0, int(limit or 0))
        rows = []
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
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="관광지가 없는 지역과 축제만 TourAPI에서 추가 수집합니다.")
    parser.add_argument("--service-key", default=None, help="공공데이터포털 TourAPI 서비스키. 생략하면 환경변수/secrets.toml 사용")
    parser.add_argument("--place-limit-per-region", type=int, default=50, help="관광지 0건 지역별 수집 개수. 0이면 해당 지역 전체")
    parser.add_argument("--festival-limit", type=int, default=100, help="축제 수집 개수. 0이면 전체")
    parser.add_argument("--page-size", type=int, default=100, help="TourAPI 페이지당 요청 개수")
    parser.add_argument("--skip-places", action="store_true", help="관광지 수집 건너뛰기")
    parser.add_argument("--skip-festivals", action="store_true", help="축제 수집 건너뛰기")
    parser.add_argument("--dry-run", action="store_true", help="API 조회 대상만 확인하고 DB 저장은 하지 않음")
    args = parser.parse_args()

    service_key = args.service_key or collector.configured_service_key()
    if not service_key:
        raise SystemExit("TourAPI 서비스키가 필요합니다. --service-key 또는 TOUR_API_KEY/TOUR_API_SERVICE_KEY를 설정하세요.")

    collector.ensure_collection_schema()
    collector.sync_regions_from_tourapi(service_key, include_sigungu=True)

    result: dict[str, Any] = {}
    if not args.skip_places:
        result["places"] = collect_missing_places(
            service_key,
            limit_per_region=args.place_limit_per_region,
            page_size=args.page_size,
            dry_run=args.dry_run,
        )
    if not args.skip_festivals:
        result["festivals"] = collect_festivals(service_key, limit=args.festival_limit, dry_run=args.dry_run)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
