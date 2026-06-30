import hashlib
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
