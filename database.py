import hashlib
import os
from contextlib import contextmanager
from typing import Any, Iterable

import mysql.connector
from mysql.connector import Error


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
        filters.append("pc.category_id = %s")
        params.append(category_id)
    if keyword:
        filters.append("(p.place_name LIKE %s OR p.overview LIKE %s OR p.address LIKE %s)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""
    return fetch_all(
        f"""
        SELECT
          p.place_id,
          p.place_name,
          r.region_name,
          p.address,
          p.overview,
          p.average_rating,
          GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ') AS categories,
          COUNT(DISTINCT rv.review_id) AS review_count
        FROM places p
        JOIN regions r ON r.region_id = p.region_id
        LEFT JOIN place_categories pc ON pc.place_id = p.place_id
        LEFT JOIN categories c ON c.category_id = pc.category_id
        LEFT JOIN reviews rv ON rv.place_id = p.place_id
        {where_sql}
        GROUP BY p.place_id, p.place_name, r.region_name, p.address, p.overview, p.average_rating
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


def upsert_place(row: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO places (region_id, place_name, address, overview, phone, latitude, longitude, source_url, external_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          address = VALUES(address),
          overview = VALUES(overview),
          phone = VALUES(phone),
          latitude = VALUES(latitude),
          longitude = VALUES(longitude),
          source_url = VALUES(source_url),
          external_id = VALUES(external_id)
        """,
        (
            row["region_id"],
            row["place_name"],
            row.get("address"),
            row.get("overview"),
            row.get("phone"),
            row.get("latitude"),
            row.get("longitude"),
            row.get("source_url"),
            row.get("external_id"),
        ),
    )


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
