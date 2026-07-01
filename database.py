import hashlib
import json
import os
from contextlib import contextmanager
from typing import Any, Iterable

import mysql.connector
from mysql.connector import Error


RECOMMENDATION_PLACE_COLUMNS = {
    "image_url": "ALTER TABLE places ADD COLUMN image_url VARCHAR(500) NULL",
    "image_path": "ALTER TABLE places ADD COLUMN image_path VARCHAR(500) NULL",
    "image_original_url": "ALTER TABLE places ADD COLUMN image_original_url VARCHAR(1000) NULL",
    "image_saved_at": "ALTER TABLE places ADD COLUMN image_saved_at DATETIME NULL",
    "tags": "ALTER TABLE places ADD COLUMN tags VARCHAR(500) NULL",
    "opening_hours": "ALTER TABLE places ADD COLUMN opening_hours VARCHAR(255) NULL",
    "source_api": "ALTER TABLE places ADD COLUMN source_api VARCHAR(80) NULL",
    "content_type_id": "ALTER TABLE places ADD COLUMN content_type_id VARCHAR(20) NULL",
    "content_type_name": "ALTER TABLE places ADD COLUMN content_type_name VARCHAR(80) NULL",
    "cat1": "ALTER TABLE places ADD COLUMN cat1 VARCHAR(80) NULL",
    "cat2": "ALTER TABLE places ADD COLUMN cat2 VARCHAR(80) NULL",
    "cat3": "ALTER TABLE places ADD COLUMN cat3 VARCHAR(80) NULL",
    "lcls_systm1": "ALTER TABLE places ADD COLUMN lcls_systm1 VARCHAR(100) NULL",
    "lcls_systm2": "ALTER TABLE places ADD COLUMN lcls_systm2 VARCHAR(100) NULL",
    "lcls_systm3": "ALTER TABLE places ADD COLUMN lcls_systm3 VARCHAR(100) NULL",
    "use_fee": "ALTER TABLE places ADD COLUMN use_fee VARCHAR(500) NULL",
    "parking_fee": "ALTER TABLE places ADD COLUMN parking_fee VARCHAR(255) NULL",
    "has_tour_image": "ALTER TABLE places ADD COLUMN has_tour_image BOOLEAN NOT NULL DEFAULT FALSE",
    "photo_priority_score": "ALTER TABLE places ADD COLUMN photo_priority_score DECIMAL(8, 2) NOT NULL DEFAULT 0",
    "detail_common_json": "ALTER TABLE places ADD COLUMN detail_common_json LONGTEXT NULL",
    "detail_intro_json": "ALTER TABLE places ADD COLUMN detail_intro_json LONGTEXT NULL",
    "detail_info_json": "ALTER TABLE places ADD COLUMN detail_info_json LONGTEXT NULL",
    "tour_api_updated_at": "ALTER TABLE places ADD COLUMN tour_api_updated_at DATETIME NULL",
}


MEDIA_COLUMNS = {
    "festivals": {
        "image_path": "ALTER TABLE festivals ADD COLUMN image_path VARCHAR(500) NULL",
        "image_original_url": "ALTER TABLE festivals ADD COLUMN image_original_url VARCHAR(1000) NULL",
        "image_saved_at": "ALTER TABLE festivals ADD COLUMN image_saved_at DATETIME NULL",
    },
    "restaurants": {
        "image_path": "ALTER TABLE restaurants ADD COLUMN image_path VARCHAR(500) NULL",
        "image_original_url": "ALTER TABLE restaurants ADD COLUMN image_original_url VARCHAR(1000) NULL",
        "image_saved_at": "ALTER TABLE restaurants ADD COLUMN image_saved_at DATETIME NULL",
    },
    "accommodations": {
        "image_path": "ALTER TABLE accommodations ADD COLUMN image_path VARCHAR(500) NULL",
        "image_original_url": "ALTER TABLE accommodations ADD COLUMN image_original_url VARCHAR(1000) NULL",
        "image_saved_at": "ALTER TABLE accommodations ADD COLUMN image_saved_at DATETIME NULL",
    },
}


ADVANCED_API_TABLES = {
    "tour_api_usage_logs": """
        CREATE TABLE IF NOT EXISTS tour_api_usage_logs (
          log_id INT AUTO_INCREMENT PRIMARY KEY,
          service_code VARCHAR(40) NOT NULL,
          service_name VARCHAR(120) NOT NULL,
          endpoint_url VARCHAR(500) NULL,
          status VARCHAR(30) NOT NULL,
          fetched_count INT NOT NULL DEFAULT 0,
          message VARCHAR(700) NULL,
          collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_tour_api_usage_service (service_code, collected_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "tour_photos": """
        CREATE TABLE IF NOT EXISTS tour_photos (
          photo_id INT AUTO_INCREMENT PRIMARY KEY,
          external_id VARCHAR(120) NULL,
          region_name VARCHAR(80) NULL,
          place_name VARCHAR(150) NULL,
          title VARCHAR(200) NOT NULL,
          image_url VARCHAR(700) NULL,
          location VARCHAR(255) NULL,
          photographer VARCHAR(120) NULL,
          shot_date VARCHAR(30) NULL,
          keywords VARCHAR(500) NULL,
          raw_json LONGTEXT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uq_tour_photos_external (external_id),
          INDEX idx_tour_photos_region (region_name),
          INDEX idx_tour_photos_title (title)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "region_visitor_stats": """
        CREATE TABLE IF NOT EXISTS region_visitor_stats (
          visitor_stat_id INT AUTO_INCREMENT PRIMARY KEY,
          source_api VARCHAR(80) NOT NULL,
          region_name VARCHAR(80) NOT NULL,
          stat_date VARCHAR(20) NULL,
          visitor_type VARCHAR(80) NULL,
          visitor_count DECIMAL(18, 2) NULL,
          raw_json LONGTEXT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uq_region_visitor (source_api, region_name, stat_date, visitor_type),
          INDEX idx_region_visitor_region (region_name),
          INDEX idx_region_visitor_date (stat_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "attraction_concentration": """
        CREATE TABLE IF NOT EXISTS attraction_concentration (
          concentration_id INT AUTO_INCREMENT PRIMARY KEY,
          attraction_name VARCHAR(180) NOT NULL,
          region_name VARCHAR(80) NULL,
          base_date VARCHAR(20) NULL,
          forecast_date VARCHAR(20) NULL,
          concentration_score DECIMAL(10, 2) NULL,
          raw_json LONGTEXT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uq_attraction_concentration (attraction_name, forecast_date),
          INDEX idx_attraction_concentration_region (region_name),
          INDEX idx_attraction_concentration_name (attraction_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "related_attractions": """
        CREATE TABLE IF NOT EXISTS related_attractions (
          related_id INT AUTO_INCREMENT PRIMARY KEY,
          origin_name VARCHAR(180) NOT NULL,
          related_name VARCHAR(180) NOT NULL,
          relation_type VARCHAR(80) NULL,
          rank_no INT NULL,
          score DECIMAL(12, 2) NULL,
          region_name VARCHAR(80) NULL,
          raw_json LONGTEXT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uq_related_attractions (origin_name, related_name, relation_type),
          INDEX idx_related_region (region_name),
          INDEX idx_related_origin (origin_name),
          INDEX idx_related_name (related_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "center_attractions": """
        CREATE TABLE IF NOT EXISTS center_attractions (
          center_id INT AUTO_INCREMENT PRIMARY KEY,
          region_name VARCHAR(80) NOT NULL,
          attraction_name VARCHAR(180) NOT NULL,
          rank_no INT NULL,
          navi_count DECIMAL(18, 2) NULL,
          raw_json LONGTEXT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uq_center_attractions (region_name, attraction_name),
          INDEX idx_center_region (region_name),
          INDEX idx_center_rank (rank_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "regional_demand_metrics": """
        CREATE TABLE IF NOT EXISTS regional_demand_metrics (
          demand_metric_id INT AUTO_INCREMENT PRIMARY KEY,
          source_api VARCHAR(80) NOT NULL,
          region_name VARCHAR(80) NOT NULL,
          metric_group VARCHAR(80) NOT NULL,
          metric_name VARCHAR(120) NOT NULL,
          metric_value DECIMAL(18, 4) NULL,
          stat_date VARCHAR(20) NULL,
          raw_json LONGTEXT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uq_regional_demand_metric (source_api, region_name, metric_group, metric_name, stat_date),
          INDEX idx_regional_demand_region (region_name),
          INDEX idx_regional_demand_group (metric_group)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "live_kakao_places": """
        CREATE TABLE IF NOT EXISTS live_kakao_places (
          kakao_place_id VARCHAR(80) PRIMARY KEY,
          region_name VARCHAR(80) NULL,
          keyword VARCHAR(120) NULL,
          place_name VARCHAR(180) NOT NULL,
          category_name VARCHAR(255) NULL,
          address_name VARCHAR(255) NULL,
          road_address_name VARCHAR(255) NULL,
          phone VARCHAR(80) NULL,
          place_url VARCHAR(500) NULL,
          latitude DECIMAL(10, 7) NULL,
          longitude DECIMAL(10, 7) NULL,
          raw_json LONGTEXT NULL,
          fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_live_kakao_region (region_name),
          INDEX idx_live_kakao_keyword (keyword)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "weather_cache": """
        CREATE TABLE IF NOT EXISTS weather_cache (
          weather_id INT AUTO_INCREMENT PRIMARY KEY,
          region_name VARCHAR(80) NULL,
          target_date DATE NULL,
          latitude DECIMAL(10, 7) NULL,
          longitude DECIMAL(10, 7) NULL,
          weather_source VARCHAR(40) NULL,
          condition_text VARCHAR(120) NULL,
          temp DECIMAL(6, 2) NULL,
          feels_like DECIMAL(6, 2) NULL,
          humidity DECIMAL(6, 2) NULL,
          wind_speed DECIMAL(6, 2) NULL,
          raw_json LONGTEXT NULL,
          fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_weather_region_date (region_name, target_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    "transport_estimates": """
        CREATE TABLE IF NOT EXISTS transport_estimates (
          estimate_id INT AUTO_INCREMENT PRIMARY KEY,
          origin_text VARCHAR(180) NOT NULL,
          destination_text VARCHAR(180) NOT NULL,
          travel_date DATE NULL,
          people INT NOT NULL DEFAULT 1,
          provider VARCHAR(40) NOT NULL DEFAULT 'openai',
          estimate_json LONGTEXT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_transport_route (origin_text, destination_text, travel_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("TRAVEL_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("TRAVEL_DB_PORT", "3306")),
        "user": os.getenv("TRAVEL_DB_USER", "travel_app"),
        "password": os.getenv("TRAVEL_DB_PASSWORD", "travel1234"),
        "database": os.getenv("TRAVEL_DB_NAME", "travel_course_db"),
        "charset": "utf8mb4",
        "use_unicode": True,
        "auth_plugin": os.getenv("TRAVEL_DB_AUTH_PLUGIN", "mysql_native_password"),
    }


@contextmanager
def get_connection():
    config = db_config()
    try:
        conn = mysql.connector.connect(**config)
    except Error as exc:
        if "auth_gssapi_client" not in str(exc):
            raise
        retry_config = config.copy()
        retry_config["auth_plugin"] = "mysql_native_password"
        conn = mysql.connector.connect(**retry_config)
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, tuple(params or ()))
        rows = cursor.fetchall()
        cursor.close()
        return rows


def fetch_one(query: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def execute(query: str, params: Iterable[Any] | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params or ()))
        conn.commit()
        row_id = cursor.lastrowid
        cursor.close()
        return row_id


def execute_many(query: str, rows: list[Iterable[Any]]) -> int:
    if not rows:
        return 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(query, rows)
        conn.commit()
        count = cursor.rowcount
        cursor.close()
        return count


def get_table_columns(table_name: str) -> set[str]:
    try:
        rows = fetch_all(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            (table_name,),
        )
    except Error:
        return set()
    return {row["COLUMN_NAME"] for row in rows}


def place_optional_selects(alias: str = "p") -> list[str]:
    columns = get_table_columns("places")
    selects = []
    for column in RECOMMENDATION_PLACE_COLUMNS:
        if column in columns:
            selects.append(f"{alias}.{column}")
        else:
            selects.append(f"NULL AS {column}")
    return selects


def media_optional_selects(table_name: str, alias: str) -> list[str]:
    columns = get_table_columns(table_name)
    selects: list[str] = []
    for column in ("image_path", "image_original_url", "image_saved_at"):
        if column in columns:
            selects.append(f"{alias}.{column}")
        else:
            selects.append(f"NULL AS {column}")
    return selects


def ensure_recommendation_schema() -> list[str]:
    existing = get_table_columns("places")
    results: list[str] = []
    for column, sql in RECOMMENDATION_PLACE_COLUMNS.items():
        if column in existing:
            results.append(f"{column}: already exists")
            continue
        try:
            execute(sql)
            results.append(f"{column}: added")
        except Error as exc:
            results.append(f"{column}: skipped ({exc})")
    return results


def ensure_media_schema() -> list[str]:
    """숙소/식당/축제 이미지 컬럼이 없는 기존 DB도 화면에서 바로 쓸 수 있게 보강한다."""
    results: list[str] = []
    for table_name, columns in MEDIA_COLUMNS.items():
        existing = get_table_columns(table_name)
        for column, sql in columns.items():
            if column in existing:
                results.append(f"{table_name}.{column}: already exists")
                continue
            try:
                execute(sql)
                results.append(f"{table_name}.{column}: added")
            except Error as exc:
                results.append(f"{table_name}.{column}: skipped ({exc})")
    return results


def ensure_advanced_api_schema() -> list[str]:
    results: list[str] = []
    for table_name, sql in ADVANCED_API_TABLES.items():
        try:
            execute(sql)
            results.append(f"{table_name}: ready")
        except Error as exc:
            results.append(f"{table_name}: skipped ({exc})")
    return results


def recommendation_schema_sql() -> str:
    return ";\n".join(RECOMMENDATION_PLACE_COLUMNS.values()) + ";"


def duplicate_cleanup_sql() -> str:
    return """
-- 같은 지역 안에서 이름이 같은 장소 중 가장 작은 place_id만 남기는 예시입니다.
-- 실제 삭제 전 SELECT로 결과를 먼저 확인하세요.
SELECT region_id, place_name, COUNT(*) AS duplicate_count
FROM places
GROUP BY region_id, place_name
HAVING COUNT(*) > 1;

DELETE p
FROM places p
JOIN (
  SELECT region_id, place_name, MIN(place_id) AS keep_place_id
  FROM places
  GROUP BY region_id, place_name
  HAVING COUNT(*) > 1
) d
  ON d.region_id = p.region_id
 AND d.place_name = p.place_name
 AND d.keep_place_id <> p.place_id;
""".strip()


def test_connection() -> tuple[bool, str]:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            cursor.close()
        return True, f"{db_name} 연결 성공"
    except Error as exc:
        return False, str(exc)


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT member_id, username, name, email, role, preferred_region_id
        FROM members
        WHERE username = %s AND password_hash = %s
        """,
        (username, hash_password(password)),
    )


def get_member_by_username(username: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT member_id, username, name, email, role, preferred_region_id
        FROM members
        WHERE username = %s
        """,
        (username,),
    )


def get_member_by_id(member_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT member_id, username, name, email, role, preferred_region_id
        FROM members
        WHERE member_id = %s
        """,
        (member_id,),
    )


def create_member(username: str, password: str, name: str, email: str, preferred_region_id: int | None) -> int:
    return execute(
        """
        INSERT INTO members (username, password_hash, name, email, preferred_region_id)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username, hash_password(password), name, email, preferred_region_id),
    )


def get_regions() -> list[dict[str, Any]]:
    return fetch_all("SELECT region_id, region_name, province, description FROM regions ORDER BY region_name")


def get_region_options() -> list[dict[str, Any]]:
    columns = get_table_columns("regions")
    optional_columns = []
    for column in ("tour_area_code", "tour_sigungu_code", "kakao_keyword"):
        optional_columns.append(column if column in columns else f"NULL AS {column}")
    return fetch_all(
        f"""
        SELECT
          region_id,
          region_name,
          province,
          description,
          {", ".join(optional_columns)}
        FROM regions
        ORDER BY
          CASE WHEN tour_area_code REGEXP '^[0-9]+$' THEN CAST(tour_area_code AS UNSIGNED) ELSE 999 END,
          CASE
            WHEN tour_sigungu_code IS NULL OR tour_sigungu_code = '' THEN 0
            WHEN tour_sigungu_code REGEXP '^[0-9]+$' THEN CAST(tour_sigungu_code AS UNSIGNED)
            ELSE 999
          END,
          region_name
        """
    )


def ensure_region(region_name: str, province: str | None = None, description: str | None = None) -> int:
    existing = fetch_one("SELECT region_id FROM regions WHERE region_name = %s", (region_name,))
    if existing:
        if province or description:
            execute(
                """
                UPDATE regions
                SET province = COALESCE(%s, province),
                    description = COALESCE(%s, description)
                WHERE region_name = %s
                """,
                (province, description, region_name),
            )
        return int(existing["region_id"])
    return execute(
        "INSERT INTO regions (region_name, province, description) VALUES (%s, %s, %s)",
        (region_name, province or region_name, description),
    )


def get_categories() -> list[dict[str, Any]]:
    return fetch_all("SELECT category_id, category_name, description FROM categories ORDER BY category_name")


def normalize_region_keyword(region_keyword: str | None) -> str:
    """사용자 입력 지역명을 검색용으로 정리한다."""
    if not region_keyword:
        return "전국"
    keyword = str(region_keyword).strip()
    aliases = {
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
        "경기도": "경기",
        "강원도": "강원",
        "강원특별자치도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전라북도": "전북",
        "전북특별자치도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
        "제주특별자치도": "제주",
    }
    return aliases.get(keyword, keyword)


def region_keyword_candidates(region_keyword: str | None) -> list[str]:
    if not region_keyword:
        return ["전국"]
    keyword = str(region_keyword).strip()
    if keyword.endswith(" 전체"):
        keyword = keyword[:-3].strip()
    alias_pairs = {
        "서울": "서울특별시",
        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광주광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",
        "세종": "세종특별자치시",
        "경기": "경기도",
        "강원": "강원특별자치도",
        "충북": "충청북도",
        "충남": "충청남도",
        "전북": "전북특별자치도",
        "전남": "전라남도",
        "경북": "경상북도",
        "경남": "경상남도",
        "제주": "제주특별자치도",
    }
    candidates = [keyword, normalize_region_keyword(keyword)]
    if keyword in alias_pairs:
        candidates.append(alias_pairs[keyword])
    for short_name, full_name in alias_pairs.items():
        if keyword == full_name:
            candidates.append(short_name)
            break
    return [item for item in dict.fromkeys(candidates) if item and item != "전국"]


def region_match_sql(alias: str, region_keyword: str | None, params: list[Any]) -> str:
    """regions 테이블 기준 지역 필터를 만든다.

    주의: 장소/숙소/식당의 address LIKE를 지역 필터에 섞지 않는다.
    address 기준으로 필터링하면 region_id가 잘못 들어간 기존 데이터 때문에
    '대구 검색인데 부산 region_id가 붙은 행'이 다시 노출될 수 있다.
    """
    candidates = region_keyword_candidates(region_keyword)
    if not candidates or candidates == ["전국"]:
        return ""
    clauses = []
    for keyword in candidates:
        like = f"%{keyword}%"
        clauses.append(f"({alias}.region_name = %s OR {alias}.province = %s OR {alias}.region_name LIKE %s OR {alias}.province LIKE %s)")
        params.extend([keyword, keyword, like, like])
    return "(" + " OR ".join(clauses) + ")"


def region_where_sql(alias: str, region_keyword: str | None, params: list[Any]) -> str:
    clause = region_match_sql(alias, region_keyword, params)
    return f"WHERE {clause}" if clause else ""


def get_region_id_for_keyword(region_keyword: str | None) -> int | None:
    """화면에서 선택한 지역명에 해당하는 대표 region_id를 DB에서 찾는다."""
    params: list[Any] = []
    clause = region_match_sql("r", region_keyword, params)
    if not clause:
        return None
    candidates = region_keyword_candidates(region_keyword)
    placeholders = ", ".join(["%s"] * len(candidates))
    row = fetch_one(
        f"""
        SELECT r.region_id
        FROM regions r
        WHERE {clause}
        ORDER BY
          CASE
            WHEN r.region_name IN ({placeholders}) THEN 0
            WHEN r.province IN ({placeholders}) AND (r.tour_sigungu_code IS NULL OR r.tour_sigungu_code = '') THEN 1
            ELSE 2
          END,
          r.region_id
        LIMIT 1
        """,
        (*params, *candidates, *candidates),
    )
    return int(row["region_id"]) if row else None


def dashboard_counts() -> dict[str, int]:
    row = fetch_one(
        """
        SELECT
          (SELECT COUNT(*) FROM regions) AS regions,
          (SELECT COUNT(*) FROM places) AS places,
          (SELECT COUNT(*) FROM festivals) AS festivals,
          (SELECT COUNT(*) FROM travel_courses) AS courses,
          (SELECT COUNT(*) FROM favorites) AS favorites,
          (SELECT COUNT(*) FROM reviews) AS reviews
        """
    )
    return {key: int(value or 0) for key, value in (row or {}).items()}


def popular_categories() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT c.category_name, COUNT(*) AS place_count
        FROM categories c
        JOIN place_categories pc ON pc.category_id = c.category_id
        GROUP BY c.category_id, c.category_name
        ORDER BY place_count DESC, c.category_name
        """
    )


def upcoming_festivals(limit: int = 8) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT f.festival_id, f.festival_name, r.region_name, f.start_date, f.end_date, f.fee_info, f.overview
        FROM festivals f
        JOIN regions r ON r.region_id = f.region_id
        WHERE f.end_date IS NULL OR f.end_date >= CURDATE()
        ORDER BY COALESCE(f.start_date, '2999-12-31'), f.festival_name
        LIMIT %s
        """,
        (limit,),
    )


def search_places(region_id: int | None, category_id: int | None, keyword: str = "") -> list[dict[str, Any]]:
    params: list[Any] = []
    filters = []
    if region_id:
        filters.append("p.region_id = %s")
        params.append(region_id)
    if category_id:
        filters.append(
            """
            EXISTS (
              SELECT 1
              FROM place_categories pc_filter
              WHERE pc_filter.place_id = p.place_id AND pc_filter.category_id = %s
            )
            """
        )
        params.append(category_id)
    if keyword:
        filters.append("(p.place_name LIKE %s OR p.overview LIKE %s OR p.address LIKE %s)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    optional_selects = ",\n          ".join(place_optional_selects("p"))
    return fetch_all(
        f"""
        SELECT
          p.place_id,
          p.place_name,
          r.region_name,
          p.address,
          p.overview,
          p.phone,
          p.latitude,
          p.longitude,
          p.source_url,
          {optional_selects},
          (
            SELECT GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ')
            FROM place_categories pc
            JOIN categories c ON c.category_id = pc.category_id
            WHERE pc.place_id = p.place_id
          ) AS categories
        FROM places p
        JOIN regions r ON r.region_id = p.region_id
        {where_sql}
        ORDER BY p.place_name
        """,
        params,
    )


def search_places_for_planner(
    region_keyword: str,
    category_names: list[str] | None = None,
    keyword: str = "",
    limit: int = 160,
) -> list[dict[str, Any]]:
    params: list[Any] = []
    filters = []
    region_clause = region_match_sql("r", region_keyword, params)
    if region_clause:
        filters.append(region_clause)
    if category_names:
        placeholders = ", ".join(["%s"] * len(category_names))
        filters.append(
            f"""
            EXISTS (
              SELECT 1
              FROM place_categories pc_filter
              JOIN categories c_filter ON c_filter.category_id = pc_filter.category_id
              WHERE pc_filter.place_id = p.place_id AND c_filter.category_name IN ({placeholders})
            )
            """
        )
        params.extend(category_names)
    if keyword:
        like = f"%{keyword}%"
        filters.append("(p.place_name LIKE %s OR p.overview LIKE %s OR p.address LIKE %s)")
        params.extend([like, like, like])
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    optional_selects = ",\n          ".join(place_optional_selects("p"))
    limit_value = int(limit or 0)
    limit_sql = "LIMIT %s" if limit_value > 0 else ""
    if limit_value > 0:
        params.append(limit_value)
    return fetch_all(
        f"""
        SELECT
          p.place_id,
          p.place_name,
          r.region_name,
          r.province,
          p.address,
          p.overview,
          p.phone,
          p.latitude,
          p.longitude,
          p.source_url,
          {optional_selects},
          (
            SELECT GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ')
            FROM place_categories pc
            JOIN categories c ON c.category_id = pc.category_id
            WHERE pc.place_id = p.place_id
          ) AS categories
        FROM places p
        JOIN regions r ON r.region_id = p.region_id
        {where_sql}
        ORDER BY p.place_name
        {limit_sql}
        """,
        params,
    )


def search_restaurants_for_region(region_keyword: str, limit: int = 8) -> list[dict[str, Any]]:
    params: list[Any] = []
    filters = []
    region_clause = region_match_sql("r", region_keyword, params)
    if region_clause:
        filters.append(region_clause)
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    media_selects = ",\n          ".join(media_optional_selects("restaurants", "rt"))
    limit_value = int(limit or 0)
    limit_sql = "LIMIT %s" if limit_value > 0 else ""
    if limit_value > 0:
        params.append(limit_value)
    return fetch_all(
        f"""
        SELECT
          rt.restaurant_id,
          rt.restaurant_name,
          rt.food_type,
          rt.address,
          r.region_name,
          {media_selects}
        FROM restaurants rt
        JOIN regions r ON r.region_id = rt.region_id
        {where_sql}
        ORDER BY rt.restaurant_name
        {limit_sql}
        """,
        params,
    )


def search_accommodations_for_region(region_keyword: str, limit: int = 6) -> list[dict[str, Any]]:
    params: list[Any] = []
    filters = []
    region_clause = region_match_sql("r", region_keyword, params)
    if region_clause:
        filters.append(region_clause)
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    media_selects = ",\n          ".join(media_optional_selects("accommodations", "a"))
    limit_value = int(limit or 0)
    limit_sql = "LIMIT %s" if limit_value > 0 else ""
    if limit_value > 0:
        params.append(limit_value)
    return fetch_all(
        f"""
        SELECT
          a.accommodation_id,
          a.accommodation_name,
          a.address,
          r.region_name,
          {media_selects}
        FROM accommodations a
        JOIN regions r ON r.region_id = a.region_id
        {where_sql}
        ORDER BY a.accommodation_name
        {limit_sql}
        """,
        params,
    )


def search_festivals_for_region(region_keyword: str, limit: int = 6) -> list[dict[str, Any]]:
    params: list[Any] = []
    filters: list[str] = []
    region_clause = region_match_sql("r", region_keyword, params)
    if region_clause:
        filters.append(region_clause)
    # 날짜가 없는 축제도 정보 카드로 보여준다. 날짜가 있으면 종료되지 않은 축제를 우선 정렬한다.
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    media_selects = ",\n          ".join(media_optional_selects("festivals", "f"))
    limit_value = int(limit or 0)
    limit_sql = "LIMIT %s" if limit_value > 0 else ""
    if limit_value > 0:
        params.append(limit_value)
    return fetch_all(
        f"""
        SELECT
          f.festival_id,
          f.festival_name,
          r.region_name,
          f.start_date,
          f.end_date,
          f.fee_info,
          f.homepage,
          f.overview,
          f.source_url,
          {media_selects}
        FROM festivals f
        JOIN regions r ON r.region_id = f.region_id
        {where_sql}
        ORDER BY
          CASE WHEN f.end_date IS NOT NULL AND f.end_date < CURDATE() THEN 1 ELSE 0 END,
          COALESCE(f.start_date, '2999-12-31'),
          f.festival_name
        {limit_sql}
        """,
        params,
    )



def favorite_place_ids(member_id: int) -> set[int]:
    """현재 회원이 찜한 place_id 목록을 세트로 반환한다."""
    try:
        rows = fetch_all(
            "SELECT place_id FROM favorites WHERE member_id = %s",
            (member_id,),
        )
    except Error:
        return set()
    return {int(row["place_id"]) for row in rows if row.get("place_id") is not None}

def toggle_favorite(member_id: int, place_id: int) -> str:
    existing = fetch_one(
        "SELECT favorite_id FROM favorites WHERE member_id = %s AND place_id = %s",
        (member_id, place_id),
    )
    if existing:
        execute("DELETE FROM favorites WHERE favorite_id = %s", (existing["favorite_id"],))
        return "removed"
    execute("INSERT INTO favorites (member_id, place_id) VALUES (%s, %s)", (member_id, place_id))
    return "added"


def add_review(member_id: int, place_id: int, rating: int, content: str) -> int:
    review_id = execute(
        """
        INSERT INTO reviews (member_id, place_id, rating, content)
        VALUES (%s, %s, %s, %s)
        """,
        (member_id, place_id, rating, content),
    )
    execute(
        """
        UPDATE places p
        SET average_rating = (
          SELECT ROUND(AVG(rating), 2)
          FROM reviews
          WHERE place_id = %s
        )
        WHERE p.place_id = %s
        """,
        (place_id, place_id),
    )
    return review_id


def get_favorites(member_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT f.favorite_id, p.place_id, p.place_name, r.region_name, p.address
        FROM favorites f
        JOIN places p ON p.place_id = f.place_id
        JOIN regions r ON r.region_id = p.region_id
        WHERE f.member_id = %s
        ORDER BY f.created_at DESC
        """,
        (member_id,),
    )


def favorite_category_counts(member_id: int) -> dict[str, int]:
    try:
        rows = fetch_all(
            """
            SELECT c.category_name, COUNT(*) AS favorite_count
            FROM favorites f
            JOIN place_categories pc ON pc.place_id = f.place_id
            JOIN categories c ON c.category_id = pc.category_id
            WHERE f.member_id = %s
            GROUP BY c.category_id, c.category_name
            ORDER BY favorite_count DESC
            """,
            (member_id,),
        )
    except Error:
        return {}
    return {row["category_name"]: int(row["favorite_count"] or 0) for row in rows}


def create_course(member_id: int, title: str, region_id: int, place_ids: list[int], start_date: Any, end_date: Any) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO travel_courses (member_id, course_title, region_id, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (member_id, title, region_id, start_date, end_date),
        )
        course_id = cursor.lastrowid
        item_rows = [(course_id, place_id, index + 1) for index, place_id in enumerate(place_ids)]
        cursor.executemany(
            """
            INSERT INTO course_items (course_id, place_id, visit_order)
            VALUES (%s, %s, %s)
            """,
            item_rows,
        )
        conn.commit()
        cursor.close()
        return course_id


def get_member_courses(member_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
          tc.course_id,
          tc.course_title,
          r.region_name,
          tc.start_date,
          tc.end_date,
          tc.created_at,
          COUNT(ci.course_item_id) AS item_count
        FROM travel_courses tc
        JOIN regions r ON r.region_id = tc.region_id
        LEFT JOIN course_items ci ON ci.course_id = tc.course_id
        WHERE tc.member_id = %s
        GROUP BY tc.course_id, tc.course_title, r.region_name, tc.start_date, tc.end_date, tc.created_at
        ORDER BY tc.created_at DESC
        """,
        (member_id,),
    )


def get_course_items(course_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT ci.visit_order, p.place_name, r.region_name, p.address, ci.memo
        FROM course_items ci
        JOIN places p ON p.place_id = ci.place_id
        JOIN regions r ON r.region_id = p.region_id
        WHERE ci.course_id = %s
        ORDER BY ci.visit_order
        """,
        (course_id,),
    )


def recommend_places(region_id: int, category_id: int | None, limit: int = 5) -> list[dict[str, Any]]:
    params: list[Any] = [region_id]
    category_join = ""
    category_filter = ""
    if category_id:
        category_join = "JOIN place_categories pc ON pc.place_id = p.place_id"
        category_filter = "AND pc.category_id = %s"
        params.append(category_id)
    params.append(limit)
    return fetch_all(
        f"""
        SELECT p.place_id, p.place_name, p.address, p.overview
        FROM places p
        {category_join}
        WHERE p.region_id = %s
        {category_filter}
        ORDER BY p.place_name
        LIMIT %s
        """,
        params,
    )


def ensure_category(category_name: str, description: str | None = None) -> int:
    existing = fetch_one("SELECT category_id FROM categories WHERE category_name = %s", (category_name,))
    if existing:
        return int(existing["category_id"])
    return execute(
        "INSERT INTO categories (category_name, description) VALUES (%s, %s)",
        (category_name, description),
    )


def link_place_category(place_id: int, category_id: int) -> None:
    execute(
        """
        INSERT IGNORE INTO place_categories (place_id, category_id)
        VALUES (%s, %s)
        """,
        (place_id, category_id),
    )


def upsert_place(row: dict[str, Any]) -> int:
    base_columns = [
        "region_id",
        "place_name",
        "address",
        "overview",
        "phone",
        "latitude",
        "longitude",
        "source_url",
        "external_id",
    ]
    place_columns = get_table_columns("places")
    optional_columns = [column for column in RECOMMENDATION_PLACE_COLUMNS if column in place_columns]
    columns = base_columns + optional_columns
    placeholders = ", ".join(["%s"] * len(columns))
    update_columns = [column for column in columns if column not in {"region_id", "place_name"}]
    update_sql = ",\n          ".join(f"{column} = VALUES({column})" for column in update_columns)
    params = tuple(row.get(column) for column in columns)

    execute(
        f"""
        INSERT INTO places ({", ".join(columns)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
          {update_sql}
        """,
        params,
    )
    saved = fetch_one(
        """
        SELECT place_id
        FROM places
        WHERE region_id = %s AND place_name = %s
        """,
        (row["region_id"], row["place_name"]),
    )
    return int(saved["place_id"]) if saved else 0


def upsert_place_with_categories(row: dict[str, Any]) -> int:
    place_id = upsert_place(row)
    for category_name in row.get("category_names") or []:
        clean_name = str(category_name).strip()
        if not clean_name:
            continue
        category_id = ensure_category(clean_name, "TourAPI 또는 추천 로직에서 자동 등록한 카테고리")
        link_place_category(place_id, category_id)
    return place_id


def upsert_restaurant_from_place(row: dict[str, Any]) -> int:
    restaurant_columns = get_table_columns("restaurants")
    columns = ["region_id", "restaurant_name", "food_type", "address"]
    for column in (
        "phone",
        "source_url",
        "external_id",
        "content_type_id",
        "content_type_name",
        "cat1",
        "cat2",
        "cat3",
        "first_menu",
        "treat_menu",
        "open_time",
        "rest_date",
        "parking_info",
        "detail_intro_json",
        "image_path",
        "image_original_url",
        "image_saved_at",
    ):
        if column in restaurant_columns:
            columns.append(column)
    values = {
        "region_id": row["region_id"],
        "restaurant_name": row["place_name"],
        "food_type": row.get("food_type") or row.get("content_type_name") or "음식점",
        "address": row.get("address"),
        "phone": row.get("phone"),
        "source_url": row.get("source_url"),
        "external_id": row.get("external_id"),
        "content_type_id": row.get("content_type_id"),
        "content_type_name": row.get("content_type_name"),
        "cat1": row.get("cat1"),
        "cat2": row.get("cat2"),
        "cat3": row.get("cat3"),
        "first_menu": row.get("first_menu"),
        "treat_menu": row.get("treat_menu"),
        "open_time": row.get("open_time"),
        "rest_date": row.get("rest_date"),
        "parking_info": row.get("parking_info"),
        "detail_intro_json": row.get("detail_intro_json"),
        "image_path": row.get("image_path"),
        "image_original_url": row.get("image_original_url"),
        "image_saved_at": row.get("image_saved_at"),
    }
    placeholders = ", ".join(["%s"] * len(columns))
    update_columns = [column for column in columns if column not in {"region_id", "restaurant_name"}]
    update_sql = ",\n          ".join(f"{column} = VALUES({column})" for column in update_columns)
    return execute(
        f"""
        INSERT INTO restaurants ({", ".join(columns)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
          {update_sql}
        """,
        tuple(values.get(column) for column in columns),
    )


def upsert_accommodation_from_place(row: dict[str, Any]) -> int:
    accommodation_columns = get_table_columns("accommodations")
    columns = ["region_id", "accommodation_name", "address"]
    for column in (
        "phone",
        "source_url",
        "external_id",
        "content_type_id",
        "content_type_name",
        "cat1",
        "cat2",
        "cat3",
        "checkin_time",
        "checkout_time",
        "room_count",
        "reservation_url",
        "parking_info",
        "detail_intro_json",
        "image_path",
        "image_original_url",
        "image_saved_at",
    ):
        if column in accommodation_columns:
            columns.append(column)
    values = {
        "region_id": row["region_id"],
        "accommodation_name": row["place_name"],
        "address": row.get("address"),
        "phone": row.get("phone"),
        "source_url": row.get("source_url"),
        "external_id": row.get("external_id"),
        "content_type_id": row.get("content_type_id"),
        "content_type_name": row.get("content_type_name"),
        "cat1": row.get("cat1"),
        "cat2": row.get("cat2"),
        "cat3": row.get("cat3"),
        "checkin_time": row.get("checkin_time"),
        "checkout_time": row.get("checkout_time"),
        "room_count": row.get("room_count"),
        "reservation_url": row.get("reservation_url"),
        "parking_info": row.get("parking_info"),
        "detail_intro_json": row.get("detail_intro_json"),
        "image_path": row.get("image_path"),
        "image_original_url": row.get("image_original_url"),
        "image_saved_at": row.get("image_saved_at"),
    }
    placeholders = ", ".join(["%s"] * len(columns))
    update_columns = [column for column in columns if column not in {"region_id", "accommodation_name"}]
    update_sql = ",\n          ".join(f"{column} = VALUES({column})" for column in update_columns)
    return execute(
        f"""
        INSERT INTO accommodations ({", ".join(columns)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
          {update_sql}
        """,
        tuple(values.get(column) for column in columns),
    )


def upsert_tourapi_place(row: dict[str, Any]) -> int:
    place_id = upsert_place_with_categories(row)
    content_type_id = str(row.get("content_type_id") or "")
    try:
        if content_type_id == "39":
            upsert_restaurant_from_place(row)
        elif content_type_id == "32":
            upsert_accommodation_from_place(row)
    except Error:
        pass
    return place_id


def upsert_festival(row: dict[str, Any]) -> None:
    festival_columns = get_table_columns("festivals")
    columns = ["region_id", "festival_name", "start_date", "end_date", "fee_info", "homepage", "overview", "source_url", "external_id"]
    for column in ("image_path", "image_original_url", "image_saved_at"):
        if column in festival_columns:
            columns.append(column)
    values = {column: row.get(column) for column in columns}
    values["region_id"] = row["region_id"]
    values["festival_name"] = row["festival_name"]
    placeholders = ", ".join(["%s"] * len(columns))
    update_columns = [column for column in columns if column not in {"region_id", "festival_name", "start_date"}]
    update_sql = ",\n          ".join(f"{column} = VALUES({column})" for column in update_columns)
    execute(
        f"""
        INSERT INTO festivals ({", ".join(columns)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
          {update_sql}
        """,
        tuple(values[column] for column in columns),
    )


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value or {}, ensure_ascii=False, default=str)
    except TypeError:
        return "{}"


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def log_tour_api_usage(
    service_code: str,
    service_name: str,
    endpoint_url: str | None,
    status: str,
    fetched_count: int,
    message: str,
) -> None:
    try:
        execute(
            """
            INSERT INTO tour_api_usage_logs
              (service_code, service_name, endpoint_url, status, fetched_count, message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (service_code, service_name, endpoint_url, status, int(fetched_count or 0), message[:700]),
        )
    except Error:
        pass


def upsert_tour_photo(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO tour_photos
          (external_id, region_name, place_name, title, image_url, location, photographer, shot_date, keywords, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          region_name = VALUES(region_name),
          place_name = VALUES(place_name),
          title = VALUES(title),
          image_url = VALUES(image_url),
          location = VALUES(location),
          photographer = VALUES(photographer),
          shot_date = VALUES(shot_date),
          keywords = VALUES(keywords),
          raw_json = VALUES(raw_json)
        """,
        (
            row.get("external_id"),
            row.get("region_name"),
            row.get("place_name"),
            row.get("title") or "제목 없음",
            row.get("image_url"),
            row.get("location"),
            row.get("photographer"),
            row.get("shot_date"),
            row.get("keywords"),
            _json_text(row.get("raw_json")),
        ),
    )


def upsert_region_visitor_stat(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO region_visitor_stats
          (source_api, region_name, stat_date, visitor_type, visitor_count, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          visitor_count = VALUES(visitor_count),
          raw_json = VALUES(raw_json)
        """,
        (
            row.get("source_api") or "DATALAB_VISITOR",
            row.get("region_name") or "지역 미상",
            row.get("stat_date"),
            row.get("visitor_type"),
            _safe_float(row.get("visitor_count")),
            _json_text(row.get("raw_json")),
        ),
    )


def upsert_attraction_concentration(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO attraction_concentration
          (attraction_name, region_name, base_date, forecast_date, concentration_score, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          region_name = VALUES(region_name),
          base_date = VALUES(base_date),
          concentration_score = VALUES(concentration_score),
          raw_json = VALUES(raw_json)
        """,
        (
            row.get("attraction_name") or "관광지 미상",
            row.get("region_name"),
            row.get("base_date"),
            row.get("forecast_date"),
            _safe_float(row.get("concentration_score")),
            _json_text(row.get("raw_json")),
        ),
    )


def upsert_related_attraction(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO related_attractions
          (origin_name, related_name, relation_type, rank_no, score, region_name, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          rank_no = VALUES(rank_no),
          score = VALUES(score),
          region_name = VALUES(region_name),
          raw_json = VALUES(raw_json)
        """,
        (
            row.get("origin_name") or "기준 관광지 미상",
            row.get("related_name") or "연관 관광지 미상",
            row.get("relation_type"),
            _safe_int(row.get("rank_no")),
            _safe_float(row.get("score")),
            row.get("region_name"),
            _json_text(row.get("raw_json")),
        ),
    )


def upsert_center_attraction(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO center_attractions
          (region_name, attraction_name, rank_no, navi_count, raw_json)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          rank_no = VALUES(rank_no),
          navi_count = VALUES(navi_count),
          raw_json = VALUES(raw_json)
        """,
        (
            row.get("region_name") or "지역 미상",
            row.get("attraction_name") or "관광지 미상",
            _safe_int(row.get("rank_no")),
            _safe_float(row.get("navi_count")),
            _json_text(row.get("raw_json")),
        ),
    )


def upsert_regional_demand_metric(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO regional_demand_metrics
          (source_api, region_name, metric_group, metric_name, metric_value, stat_date, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          metric_value = VALUES(metric_value),
          raw_json = VALUES(raw_json)
        """,
        (
            row.get("source_api") or "REGIONAL_METRIC",
            row.get("region_name") or "지역 미상",
            row.get("metric_group") or "metric",
            row.get("metric_name") or "value",
            _safe_float(row.get("metric_value")),
            row.get("stat_date"),
            _json_text(row.get("raw_json")),
        ),
    )


def advanced_api_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name in ADVANCED_API_TABLES:
        try:
            row = fetch_one(f"SELECT COUNT(*) AS count_value FROM {table_name}")
            counts[table_name] = int((row or {}).get("count_value") or 0)
        except Error:
            counts[table_name] = 0
    return counts


def _region_filter_sql(alias: str, region_keyword: str, params: list[Any]) -> str:
    return region_where_sql(alias, region_keyword, params)


def api_insights_for_trip(region_keyword: str, place_names: list[str] | None = None) -> dict[str, Any]:
    insights: dict[str, Any] = {
        "visitor": None,
        "centers": [],
        "related": [],
        "demand_metrics": [],
        "diversity_metrics": [],
        "photo_count": 0,
        "latest_logs": [],
    }
    params: list[Any] = []
    where_sql = _region_filter_sql("v", region_keyword, params)
    try:
        insights["visitor"] = fetch_one(
            f"""
            SELECT region_name, stat_date, visitor_type, visitor_count
            FROM region_visitor_stats v
            {where_sql}
            ORDER BY stat_date DESC, visitor_count DESC
            LIMIT 1
            """,
            params,
        )
    except Error:
        pass

    params = []
    where_sql = _region_filter_sql("c", region_keyword, params)
    try:
        insights["centers"] = fetch_all(
            f"""
            SELECT region_name, attraction_name, rank_no, navi_count
            FROM center_attractions c
            {where_sql}
            ORDER BY COALESCE(rank_no, 9999), COALESCE(navi_count, 0) DESC
            LIMIT 5
            """,
            params,
        )
    except Error:
        pass

    related_params: list[Any] = []
    related_filters: list[str] = []
    related_region_clause = region_match_sql("ra", region_keyword, related_params)
    if related_region_clause:
        related_filters.append(related_region_clause)
    clean_names = [name for name in (place_names or []) if name][:10]
    if clean_names:
        name_filters = []
        for name in clean_names:
            name_filters.append("(ra.origin_name LIKE %s OR ra.related_name LIKE %s)")
            like = f"%{name[:40]}%"
            related_params.extend([like, like])
        related_filters.append("(" + " OR ".join(name_filters) + ")")
    related_where = "WHERE " + " AND ".join(related_filters) if related_filters else ""
    try:
        insights["related"] = fetch_all(
            f"""
            SELECT origin_name, related_name, relation_type, rank_no, score, region_name
            FROM related_attractions ra
            {related_where}
            ORDER BY COALESCE(rank_no, 9999), COALESCE(score, 0) DESC
            LIMIT 5
            """,
            related_params,
        )
    except Error:
        pass

    for source_api, key in (("DMANDRESR", "demand_metrics"), ("DMANDDVRST", "diversity_metrics")):
        metric_params: list[Any] = [source_api]
        metric_filters = ["m.source_api = %s"]
        metric_region_clause = region_match_sql("m", region_keyword, metric_params)
        if metric_region_clause:
            metric_filters.append(metric_region_clause)
        metric_where = "WHERE " + " AND ".join(metric_filters)
        try:
            insights[key] = fetch_all(
                f"""
                SELECT region_name, metric_group, metric_name, metric_value, stat_date
                FROM regional_demand_metrics m
                {metric_where}
                ORDER BY stat_date DESC, metric_value DESC
                LIMIT 4
                """,
                metric_params,
            )
        except Error:
            pass

    photo_params: list[Any] = []
    photo_filters: list[str] = []
    if region_keyword and region_keyword != "전국":
        photo_filters.append("(p.region_name LIKE %s OR p.location LIKE %s OR p.keywords LIKE %s)")
        like = f"%{region_keyword}%"
        photo_params.extend([like, like, like])
    photo_where = "WHERE " + " AND ".join(photo_filters) if photo_filters else ""
    try:
        row = fetch_one(f"SELECT COUNT(*) AS count_value FROM tour_photos p {photo_where}", photo_params)
        insights["photo_count"] = int((row or {}).get("count_value") or 0)
    except Error:
        pass

    try:
        insights["latest_logs"] = fetch_all(
            """
            SELECT service_code, service_name, status, fetched_count, message, collected_at
            FROM tour_api_usage_logs
            ORDER BY collected_at DESC
            LIMIT 8
            """
        )
    except Error:
        pass
    return insights


def api_score_lookup(region_keyword: str, place_names: list[str]) -> dict[str, dict[str, Any]]:
    if not place_names:
        return {}

    clean_names = [str(name).strip() for name in place_names if str(name).strip()]
    result = {name: {"boost": 0.0, "reasons": []} for name in clean_names}
    center_rows: list[dict[str, Any]] = []
    related_rows: list[dict[str, Any]] = []
    concentration_rows: list[dict[str, Any]] = []
    photo_rows: list[dict[str, Any]] = []
    visitor_row: dict[str, Any] | None = None
    demand_rows: list[dict[str, Any]] = []

    params: list[Any] = []
    where_sql = _region_filter_sql("c", region_keyword, params)
    try:
        center_rows = fetch_all(
            f"""
            SELECT attraction_name, rank_no, navi_count
            FROM center_attractions c
            {where_sql}
            ORDER BY COALESCE(rank_no, 9999)
            LIMIT 120
            """,
            params,
        )
    except Error:
        center_rows = []

    related_params: list[Any] = []
    related_where = ""
    related_region_clause = region_match_sql("ra", region_keyword, related_params)
    if related_region_clause:
        related_where = f"WHERE {related_region_clause}"
    try:
        related_rows = fetch_all(
            f"""
            SELECT origin_name, related_name, rank_no, score
            FROM related_attractions ra
            {related_where}
            ORDER BY COALESCE(rank_no, 9999), COALESCE(score, 0) DESC
            LIMIT 200
            """,
            related_params,
        )
    except Error:
        related_rows = []

    concentration_params: list[Any] = []
    concentration_where = _region_filter_sql("ac", region_keyword, concentration_params)
    try:
        concentration_rows = fetch_all(
            f"""
            SELECT attraction_name, concentration_score
            FROM attraction_concentration ac
            {concentration_where}
            ORDER BY forecast_date DESC
            LIMIT 200
            """,
            concentration_params,
        )
    except Error:
        concentration_rows = []

    visitor_params: list[Any] = []
    visitor_where = _region_filter_sql("v", region_keyword, visitor_params)
    try:
        visitor_row = fetch_one(
            f"""
            SELECT region_name, stat_date, visitor_count
            FROM region_visitor_stats v
            {visitor_where}
            ORDER BY stat_date DESC, visitor_count DESC
            LIMIT 1
            """,
            visitor_params,
        )
    except Error:
        visitor_row = None

    demand_params: list[Any] = ["DMANDRESR", "DMANDDVRST"]
    demand_filters = ["m.source_api IN (%s, %s)"]
    demand_region_clause = region_match_sql("m", region_keyword, demand_params)
    if demand_region_clause:
        demand_filters.append(demand_region_clause)
    try:
        demand_rows = fetch_all(
            f"""
            SELECT source_api, metric_group, metric_name, metric_value, stat_date
            FROM regional_demand_metrics m
            WHERE {' AND '.join(demand_filters)}
            ORDER BY stat_date DESC, metric_value DESC
            LIMIT 6
            """,
            demand_params,
        )
    except Error:
        demand_rows = []

    photo_params: list[Any] = []
    photo_filters: list[str] = []
    if region_keyword and region_keyword != "전국":
        like = f"%{region_keyword}%"
        photo_filters.append("(tp.region_name LIKE %s OR tp.location LIKE %s OR tp.keywords LIKE %s)")
        photo_params.extend([like, like, like])
    photo_where = "WHERE " + " AND ".join(photo_filters) if photo_filters else ""
    try:
        photo_rows = fetch_all(
            f"""
            SELECT place_name, title, keywords, region_name
            FROM tour_photos tp
            {photo_where}
            ORDER BY created_at DESC
            LIMIT 200
            """,
            photo_params,
        )
    except Error:
        photo_rows = []

    def matches(candidate: str, target: str) -> bool:
        candidate = candidate.strip()
        target = target.strip()
        return bool(candidate and target and (candidate in target or target in candidate))

    region_boost = 0.0
    region_reasons: list[str] = []
    if visitor_row and visitor_row.get("visitor_count") is not None:
        region_boost += 5
        region_reasons.append("지역별 방문자수_GW 데이터가 있어 지역 인기 지표가 반영됩니다.")
    if demand_rows:
        region_boost += 5
        region_reasons.append("지역별 관광 자원 수요/관광 다양성 지표가 결과 설명에 반영됩니다.")

    for name in clean_names:
        scored = result[name]
        if region_boost:
            scored["boost"] += region_boost
            scored["reasons"].extend(region_reasons)

        for row in center_rows:
            attraction = str(row.get("attraction_name") or "")
            if not matches(attraction, name):
                continue
            rank_no = _safe_int(row.get("rank_no")) or 100
            scored["boost"] += max(4, 18 - min(rank_no, 100) / 8)
            scored["reasons"].append("기초지자체 중심 관광지 정보 API에 포함됩니다.")
            break

        for row in related_rows:
            origin = str(row.get("origin_name") or "")
            related = str(row.get("related_name") or "")
            if matches(origin, name) or matches(related, name):
                scored["boost"] += 8
                scored["reasons"].append("관광지별 연관 관광지 정보 API에서 코스 연결성이 확인됩니다.")
                break

        for row in concentration_rows:
            attraction = str(row.get("attraction_name") or "")
            if not matches(attraction, name):
                continue
            score = _safe_float(row.get("concentration_score"))
            if score is not None and score <= 70:
                scored["boost"] += 6
                scored["reasons"].append("관광지 집중률 방문자 추이 예측 정보상 혼잡 부담이 낮은 편입니다.")
            elif score is not None:
                scored["reasons"].append("관광지 집중률 방문자 추이 예측 정보로 혼잡도 확인이 가능합니다.")
            break

        for row in photo_rows:
            if matches(str(row.get("place_name") or row.get("title") or ""), name):
                scored["boost"] += 6
                scored["reasons"].append("관광사진 정보_GW 데이터와 매칭되어 사진 우선 추천에 반영됩니다.")
                break

    return {name: value for name, value in result.items() if value["boost"] or value["reasons"]}


def region_center(region_keyword: str | None) -> dict[str, Any] | None:
    params: list[Any] = []
    clause = region_match_sql("r", region_keyword, params)
    where_sql = f"WHERE {clause}" if clause else ""
    row = fetch_one(
        f"""
        SELECT
          r.region_name,
          AVG(p.latitude) AS latitude,
          AVG(p.longitude) AS longitude
        FROM regions r
        LEFT JOIN places p ON p.region_id = r.region_id AND p.latitude IS NOT NULL AND p.longitude IS NOT NULL
        {where_sql}
        GROUP BY r.region_id, r.region_name
        HAVING latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY r.region_id
        LIMIT 1
        """,
        params,
    )
    if row:
        return row
    return fetch_one(
        """
        SELECT region_name, AVG(latitude) AS latitude, AVG(longitude) AS longitude
        FROM places p
        JOIN regions r ON r.region_id = p.region_id
        WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
        GROUP BY r.region_name
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """
    )


def save_kakao_places(region_name: str, keyword: str, rows: list[dict[str, Any]]) -> int:
    ensure_advanced_api_schema()
    count = 0
    for row in rows:
        kakao_id = str(row.get("id") or "").strip()
        if not kakao_id:
            continue
        execute(
            """
            INSERT INTO live_kakao_places (
              kakao_place_id, region_name, keyword, place_name, category_name,
              address_name, road_address_name, phone, place_url, latitude, longitude, raw_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              region_name = VALUES(region_name),
              keyword = VALUES(keyword),
              place_name = VALUES(place_name),
              category_name = VALUES(category_name),
              address_name = VALUES(address_name),
              road_address_name = VALUES(road_address_name),
              phone = VALUES(phone),
              place_url = VALUES(place_url),
              latitude = VALUES(latitude),
              longitude = VALUES(longitude),
              raw_json = VALUES(raw_json),
              fetched_at = CURRENT_TIMESTAMP
            """,
            (
                kakao_id,
                region_name,
                keyword,
                row.get("place_name"),
                row.get("category_name"),
                row.get("address_name"),
                row.get("road_address_name"),
                row.get("phone"),
                row.get("place_url"),
                _safe_float(row.get("y")),
                _safe_float(row.get("x")),
                json.dumps(row, ensure_ascii=False),
            ),
        )
        count += 1
    return count


def save_weather_snapshot(region_name: str, target_date: Any, lat: Any, lon: Any, weather: dict[str, Any]) -> int:
    ensure_advanced_api_schema()
    return execute(
        """
        INSERT INTO weather_cache (
          region_name, target_date, latitude, longitude, weather_source,
          condition_text, temp, feels_like, humidity, wind_speed, raw_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            region_name,
            target_date,
            lat,
            lon,
            weather.get("source"),
            weather.get("condition"),
            weather.get("temp"),
            weather.get("feels_like"),
            weather.get("humidity"),
            weather.get("wind_speed"),
            json.dumps(weather.get("raw_json") or weather, ensure_ascii=False),
        ),
    )


def save_transport_estimate(origin: str, destination: str, travel_date: Any, people: int, estimate: dict[str, Any]) -> int:
    ensure_advanced_api_schema()
    return execute(
        """
        INSERT INTO transport_estimates (origin_text, destination_text, travel_date, people, estimate_json)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (origin, destination, travel_date, people, json.dumps(estimate, ensure_ascii=False)),
    )


def log_crawl(source_name: str, source_url: str | None, status: str, inserted_count: int, message: str) -> None:
    execute(
        """
        INSERT INTO crawl_logs (source_name, source_url, status, inserted_count, message)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (source_name, source_url, status, inserted_count, message[:500]),
    )


def recent_crawl_logs(limit: int = 10) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT source_name, source_url, status, inserted_count, message, crawled_at
        FROM crawl_logs
        ORDER BY crawled_at DESC
        LIMIT %s
        """,
        (limit,),
    )
