import hashlib
import json
import os
from contextlib import contextmanager
from typing import Any, Iterable

import mysql.connector
from mysql.connector import Error


RECOMMENDATION_PLACE_COLUMNS = {
    "image_url": "ALTER TABLE places ADD COLUMN image_url VARCHAR(500) NULL",
    "tags": "ALTER TABLE places ADD COLUMN tags VARCHAR(500) NULL",
    "indoor_outdoor": "ALTER TABLE places ADD COLUMN indoor_outdoor ENUM('실내', '야외', '혼합') NULL",
    "recommended_for": "ALTER TABLE places ADD COLUMN recommended_for VARCHAR(255) NULL",
    "budget_level": "ALTER TABLE places ADD COLUMN budget_level ENUM('저렴', '보통', '비쌈') NULL",
    "opening_hours": "ALTER TABLE places ADD COLUMN opening_hours VARCHAR(255) NULL",
    "source_api": "ALTER TABLE places ADD COLUMN source_api VARCHAR(80) NULL",
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
          p.average_rating,
          {optional_selects},
          (
            SELECT GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ')
            FROM place_categories pc
            JOIN categories c ON c.category_id = pc.category_id
            WHERE pc.place_id = p.place_id
          ) AS categories,
          (
            SELECT COUNT(*)
            FROM reviews rv
            WHERE rv.place_id = p.place_id
          ) AS review_count
        FROM places p
        JOIN regions r ON r.region_id = p.region_id
        {where_sql}
        ORDER BY p.average_rating DESC, p.place_name
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
    if region_keyword and region_keyword != "전국":
        like = f"%{region_keyword}%"
        filters.append("(r.region_name LIKE %s OR r.province LIKE %s OR p.address LIKE %s)")
        params.extend([like, like, like])
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
    params.append(limit)
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    optional_selects = ",\n          ".join(place_optional_selects("p"))
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
          p.average_rating,
          {optional_selects},
          (
            SELECT GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ')
            FROM place_categories pc
            JOIN categories c ON c.category_id = pc.category_id
            WHERE pc.place_id = p.place_id
          ) AS categories,
          (
            SELECT COUNT(*)
            FROM reviews rv
            WHERE rv.place_id = p.place_id
          ) AS review_count
        FROM places p
        JOIN regions r ON r.region_id = p.region_id
        {where_sql}
        ORDER BY p.average_rating DESC, p.place_name
        LIMIT %s
        """,
        params,
    )


def search_restaurants_for_region(region_keyword: str, limit: int = 8) -> list[dict[str, Any]]:
    params: list[Any] = []
    filters = []
    if region_keyword and region_keyword != "전국":
        like = f"%{region_keyword}%"
        filters.append("(r.region_name LIKE %s OR r.province LIKE %s OR rt.address LIKE %s)")
        params.extend([like, like, like])
    params.append(limit)
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    return fetch_all(
        f"""
        SELECT
          rt.restaurant_id,
          rt.restaurant_name,
          rt.food_type,
          rt.address,
          rt.price_level,
          r.region_name
        FROM restaurants rt
        JOIN regions r ON r.region_id = rt.region_id
        {where_sql}
        ORDER BY rt.restaurant_name
        LIMIT %s
        """,
        params,
    )


def search_accommodations_for_region(region_keyword: str, limit: int = 6) -> list[dict[str, Any]]:
    params: list[Any] = []
    filters = []
    if region_keyword and region_keyword != "전국":
        like = f"%{region_keyword}%"
        filters.append("(r.region_name LIKE %s OR r.province LIKE %s OR a.address LIKE %s)")
        params.extend([like, like, like])
    params.append(limit)
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    return fetch_all(
        f"""
        SELECT
          a.accommodation_id,
          a.accommodation_name,
          a.address,
          a.price_level,
          a.phone,
          r.region_name
        FROM accommodations a
        JOIN regions r ON r.region_id = a.region_id
        {where_sql}
        ORDER BY a.accommodation_name
        LIMIT %s
        """,
        params,
    )


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
        SELECT f.favorite_id, p.place_id, p.place_name, r.region_name, p.address, p.average_rating
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
        SELECT p.place_id, p.place_name, p.address, p.overview, p.average_rating
        FROM places p
        {category_join}
        WHERE p.region_id = %s
        {category_filter}
        ORDER BY p.average_rating DESC, p.place_name
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
    return execute(
        """
        INSERT INTO restaurants (region_id, restaurant_name, food_type, address, price_level)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          food_type = VALUES(food_type),
          address = VALUES(address),
          price_level = VALUES(price_level)
        """,
        (
            row["region_id"],
            row["place_name"],
            row.get("food_type") or "음식점",
            row.get("address"),
            "MID",
        ),
    )


def upsert_accommodation_from_place(row: dict[str, Any]) -> int:
    return execute(
        """
        INSERT INTO accommodations (region_id, accommodation_name, address, price_level, phone)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          address = VALUES(address),
          price_level = VALUES(price_level),
          phone = VALUES(phone)
        """,
        (
            row["region_id"],
            row["place_name"],
            row.get("address"),
            "MID",
            row.get("phone"),
        ),
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
    execute(
        """
        INSERT INTO festivals (region_id, festival_name, start_date, end_date, fee_info, homepage, overview, source_url, external_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          end_date = VALUES(end_date),
          fee_info = VALUES(fee_info),
          homepage = VALUES(homepage),
          overview = VALUES(overview),
          source_url = VALUES(source_url),
          external_id = VALUES(external_id)
        """,
        (
            row["region_id"],
            row["festival_name"],
            row.get("start_date"),
            row.get("end_date"),
            row.get("fee_info"),
            row.get("homepage"),
            row.get("overview"),
            row.get("source_url"),
            row.get("external_id"),
        ),
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
    if not region_keyword or region_keyword == "전국":
        return ""
    params.append(f"%{region_keyword}%")
    return f"WHERE {alias}.region_name LIKE %s"


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
    if region_keyword and region_keyword != "전국":
        related_filters.append("ra.region_name LIKE %s")
        related_params.append(f"%{region_keyword}%")
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
        if region_keyword and region_keyword != "전국":
            metric_filters.append("m.region_name LIKE %s")
            metric_params.append(f"%{region_keyword}%")
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
    if region_keyword and region_keyword != "전국":
        related_where = "WHERE ra.region_name LIKE %s"
        related_params.append(f"%{region_keyword}%")
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

    def matches(candidate: str, target: str) -> bool:
        candidate = candidate.strip()
        target = target.strip()
        return bool(candidate and target and (candidate in target or target in candidate))

    for name in clean_names:
        scored = result[name]
        for row in center_rows:
            attraction = str(row.get("attraction_name") or "")
            if not matches(attraction, name):
                continue
            rank_no = _safe_int(row.get("rank_no")) or 100
            scored["boost"] += max(4, 18 - min(rank_no, 100) / 8)
            scored["reasons"].append("내비게이션 연계 기준 중심 관광지 데이터에 포함됩니다.")
            break

        for row in related_rows:
            origin = str(row.get("origin_name") or "")
            related = str(row.get("related_name") or "")
            if matches(origin, name) or matches(related, name):
                scored["boost"] += 8
                scored["reasons"].append("연관 관광지 API에서 주변 코스 연결성이 확인됩니다.")
                break

        for row in concentration_rows:
            attraction = str(row.get("attraction_name") or "")
            if not matches(attraction, name):
                continue
            score = _safe_float(row.get("concentration_score"))
            if score is not None and score <= 70:
                scored["boost"] += 6
                scored["reasons"].append("방문 집중률 예측이 비교적 낮아 일정에 넣기 부담이 적습니다.")
            elif score is not None:
                scored["reasons"].append("방문 집중률 예측 데이터가 있어 혼잡도 확인이 가능합니다.")
            break

    return {name: value for name, value in result.items() if value["boost"] or value["reasons"]}


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
