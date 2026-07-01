from __future__ import annotations

import hashlib
import hmac
import importlib
import html
import os
import sys
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

import pandas as pd
import streamlit as st
from mysql.connector import Error

import course_generator
import database as db
import external_services
import recommender

db = importlib.reload(db)
external_services = importlib.reload(external_services)


st.set_page_config(
    page_title="TravelDB 맞춤 여행 추천",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


MAJOR_REGION_ORDER = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]

REGION_FALLBACK_CENTERS = {
    "전국": {"region_name": "서울", "latitude": 37.5665, "longitude": 126.9780},
    "서울": {"region_name": "서울", "latitude": 37.5665, "longitude": 126.9780},
    "부산": {"region_name": "부산", "latitude": 35.1796, "longitude": 129.0756},
    "대구": {"region_name": "대구", "latitude": 35.8714, "longitude": 128.6014},
    "인천": {"region_name": "인천", "latitude": 37.4563, "longitude": 126.7052},
    "광주": {"region_name": "광주", "latitude": 35.1595, "longitude": 126.8526},
    "대전": {"region_name": "대전", "latitude": 36.3504, "longitude": 127.3845},
    "울산": {"region_name": "울산", "latitude": 35.5384, "longitude": 129.3114},
    "세종": {"region_name": "세종", "latitude": 36.4800, "longitude": 127.2890},
    "경기": {"region_name": "경기", "latitude": 37.4138, "longitude": 127.5183},
    "강원": {"region_name": "강원", "latitude": 37.8228, "longitude": 128.1555},
    "충북": {"region_name": "충북", "latitude": 36.6357, "longitude": 127.4917},
    "충남": {"region_name": "충남", "latitude": 36.6588, "longitude": 126.6728},
    "전북": {"region_name": "전북", "latitude": 35.7175, "longitude": 127.1530},
    "전남": {"region_name": "전남", "latitude": 34.8679, "longitude": 126.9910},
    "경북": {"region_name": "경북", "latitude": 36.4919, "longitude": 128.8889},
    "경남": {"region_name": "경남", "latitude": 35.4606, "longitude": 128.2132},
    "제주": {"region_name": "제주", "latitude": 33.4996, "longitude": 126.5312},
    "경주": {"region_name": "경주", "latitude": 35.8562, "longitude": 129.2247},
    "강릉": {"region_name": "강릉", "latitude": 37.7519, "longitude": 128.8761},
    "세종특별자치시": {"region_name": "세종특별자치시", "latitude": 36.4800, "longitude": 127.2890},
    "경기도": {"region_name": "경기도", "latitude": 37.4138, "longitude": 127.5183},
    "강원특별자치도": {"region_name": "강원특별자치도", "latitude": 37.8228, "longitude": 128.1555},
    "충청북도": {"region_name": "충청북도", "latitude": 36.6357, "longitude": 127.4917},
    "충청남도": {"region_name": "충청남도", "latitude": 36.6588, "longitude": 126.6728},
    "전북특별자치도": {"region_name": "전북특별자치도", "latitude": 35.7175, "longitude": 127.1530},
    "전라남도": {"region_name": "전라남도", "latitude": 34.8679, "longitude": 126.9910},
    "경상북도": {"region_name": "경상북도", "latitude": 36.4919, "longitude": 128.8889},
    "경상남도": {"region_name": "경상남도", "latitude": 35.4606, "longitude": 128.2132},
    "제주특별자치도": {"region_name": "제주특별자치도", "latitude": 33.4996, "longitude": 126.5312},
}


TRIP_CATEGORIES = [
    "관광지",
    "자연",
    "미식",
    "카페",
    "문화시설",
    "역사",
    "사진 명소",
    "야간",
    "숙박",
    "축제",
    "여행코스",
]

CATEGORY_TO_DB = {
    "관광지": ["관광지"],
    "자연": ["자연"],
    "미식": ["미식"],
    "카페": ["카페", "미식"],
    "문화시설": ["문화시설"],
    "역사": ["역사"],
    "사진 명소": ["야간", "자연", "관광지"],
    "야간": ["야간"],
    "숙박": ["숙박"],
    "축제": ["축제"],
    "여행코스": ["여행코스"],
}


def inject_design() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

          :root {
            --ink: #202A36;
            --ink-hover: #1A2229;
            --gray-50: #F9FAFB;
            --gray-100: #F3F4F6;
            --gray-200: #E5E7EB;
            --gray-300: #D1D5DB;
            --gray-500: #6B7280;
            --gray-600: #4B5563;
            --gray-700: #374151;
            --gray-800: #1F2937;
            --gray-900: #111827;
          }

          html, body, [class*="css"] {
            font-family: 'Inter', 'Apple SD Gothic Neo', 'Noto Sans KR', system-ui, sans-serif;
          }

          html, body, .stApp, [data-testid="stAppViewContainer"], .main {
            margin: 0 !important;
            padding: 0 !important;
          }

          [data-testid="stAppViewContainer"] > .main {
            padding-top: 0 !important;
          }

          .stApp {
            background: var(--gray-50);
            color: var(--gray-900);
          }

          header[data-testid="stHeader"],
          [data-testid="stHeader"],
          div[data-testid="stToolbar"],
          [data-testid="stToolbar"],
          div[data-testid="stDecoration"],
          [data-testid="stStatusWidget"],
          [data-testid="stDeployButton"],
          .stDeployButton,
          #MainMenu,
          footer {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
          }

          .block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
          }

          .block-container [data-testid="stElementContainer"]:not(:has(.hero-shell)):not(:has(style)),
          .block-container [data-testid="stHorizontalBlock"],
          .block-container [data-testid="stDataFrame"],
          .block-container [data-testid="stAlert"] {
            max-width: calc(100vw - clamp(32px, 6vw, 96px));
            margin-left: auto;
            margin-right: auto;
          }

          h1, h2, h3 {
            color: var(--gray-900);
            letter-spacing: 0;
          }

          p, label, .stMarkdown, .stCaption {
            color: var(--gray-600);
          }

          div[data-testid="stForm"],
          div[data-testid="stExpander"],
          div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px;
            border-color: var(--gray-200);
            box-shadow: 0 16px 38px rgba(17,24,39,0.04);
          }

          div[data-testid="stForm"],
          div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) {
            max-width: min(92vw, 1180px);
            margin: -116px auto 44px !important;
            padding: 24px 26px 28px !important;
            border: 1px solid rgba(209,213,219,0.86) !important;
            border-radius: 16px !important;
            background: rgba(255,255,255,0.96) !important;
            box-shadow: 0 22px 44px rgba(17,24,39,0.16) !important;
            position: relative;
            z-index: 4;
          }

          div[data-testid="stForm"] label,
          div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) label {
            color: var(--gray-700) !important;
            font-weight: 600 !important;
          }

          .stButton > button,
          .stDownloadButton > button {
            border-radius: 9999px;
            min-height: 42px;
            padding: 8px 18px;
            border: 1px solid var(--gray-300);
            background: #fff;
            color: var(--gray-800);
            font-weight: 500;
          }

          .stButton > button:hover,
          .stDownloadButton > button:hover {
            border-color: var(--ink);
            color: var(--ink);
          }

          .stButton > button[kind="primary"] {
            background: var(--ink);
            border-color: var(--ink);
            color: #fff;
          }

          .hero-shell {
            position: relative;
            left: 50%;
            transform: translateX(-50%);
            width: 100vw;
            height: calc(100vh + 24px);
            min-height: 690px;
            overflow: hidden;
            margin: -24px 0 36px;
            background: #f9fafb;
          }

          .hero-video {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center center;
            z-index: 0;
          }

          .hero-shell::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(rgba(249,250,251,0.16), rgba(249,250,251,0.30));
            z-index: 1;
          }

          .hero-nav {
            position: relative;
            z-index: 2;
            max-width: 80rem;
            margin: 0 auto;
            padding: 24px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 48px;
          }

          .nav-left {
            display: flex;
            align-items: center;
            gap: 48px;
          }

          .brand {
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--gray-900);
          }

          .nav-menu {
            display: flex;
            gap: 30px;
            color: var(--gray-900);
            font-size: 0.96rem;
            font-weight: 600;
          }

          .nav-auth {
            display: flex;
            align-items: center;
            gap: 18px;
            color: var(--gray-900);
            font-size: 0.95rem;
            font-weight: 600;
            white-space: nowrap;
          }

          .nav-auth a,
          .nav-menu a {
            color: var(--gray-900);
            text-decoration: none;
          }

          .nav-user {
            color: var(--gray-600);
          }

          .hero-main {
            position: relative;
            z-index: 2;
            min-height: calc(100vh - 92px);
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 0 24px;
          }

          .hero-content {
            text-align: center;
            margin-top: -270px;
            display: flex;
            flex-direction: column;
            align-items: center;
          }

          .eyebrow {
            margin-bottom: 16px;
            color: var(--gray-600);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
          }

          .headline {
            margin: 0;
            line-height: 0.95;
            font-weight: 500;
            letter-spacing: 0;
          }

          .headline .line1,
          .headline .line2 {
            display: block;
            font-size: clamp(3.75rem, 7vw, 6rem);
          }

          .headline .line1 {
            color: var(--gray-500);
          }

          .headline .line2 {
            color: var(--ink);
            margin-top: -8px;
          }

          .hero-copy {
            max-width: 42rem;
            margin: 24px auto;
            color: var(--gray-600);
            font-size: 1.12rem;
            line-height: 1.65;
            word-break: keep-all;
          }

          .section-shell {
            max-width: calc(100vw - clamp(32px, 6vw, 96px));
            margin: 30px auto;
          }

          .section-kicker {
            margin-bottom: 8px;
            color: var(--gray-500);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
          }

          .section-title {
            margin: 0 0 12px;
            color: var(--ink);
            font-size: clamp(1.7rem, 3vw, 2.5rem);
            font-weight: 600;
          }

          .mini-card {
            background: #fff;
            border: 1px solid var(--gray-200);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 16px 38px rgba(17,24,39,0.04);
          }

          div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 22px !important;
            border: 1px solid rgba(229,231,235,0.95) !important;
            box-shadow: 0 18px 42px rgba(15,23,42,0.07) !important;
            background: #fff !important;
          }

          div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%);
            border: 1px solid var(--gray-200);
            border-radius: 16px;
            padding: 12px 14px;
          }

          .live-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 999px;
            background: #fff7ed;
            color: #9a3412;
            font-weight: 700;
            font-size: 0.78rem;
          }

          @media (max-width: 767px) {
            .nav-menu { display: none; }
            .hero-nav { padding: 20px 22px; }
            .hero-content { margin-top: -190px; }
            .nav-auth { gap: 12px; font-size: 0.86rem; }
            div[data-testid="stForm"],
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) {
              margin: -82px 16px 34px !important;
              padding: 20px !important;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("trip_result", None)


def configured_api_key() -> str | None:
    for name in (
        "TOUR_API_SERVICE_KEY",
        "TOURAPI_SERVICE_KEY",
        "DATA_GO_KR_SERVICE_KEY",
        "VISITKOREA_PHOTO_SERVICE_KEY",
        "VISITKOREA_BIGDATA_SERVICE_KEY",
    ):
        value = os.getenv(name)
        if value:
            return value.strip()
    try:
        for name in (
            "TOUR_API_SERVICE_KEY",
            "TOURAPI_SERVICE_KEY",
            "DATA_GO_KR_SERVICE_KEY",
            "VISITKOREA_PHOTO_SERVICE_KEY",
            "VISITKOREA_BIGDATA_SERVICE_KEY",
        ):
            value = st.secrets.get(name)
            if value:
                return str(value).strip()
    except Exception:
        return None
    return None


def _login_secret() -> str:
    # 새로고침 로그인 유지를 위한 서명용 값. 별도 설정이 없으면 DB 비밀번호를 사용한다.
    # 발표/실습용이며, 실제 서비스라면 별도 세션 테이블/쿠키 만료시간을 두는 방식이 더 안전하다.
    return (
        os.getenv("APP_LOGIN_SECRET")
        or os.getenv("LOGIN_SECRET_KEY")
        or str(db.db_config().get("password") or "traveldb-local-secret")
    )


def _login_token(member_id: int) -> str:
    raw = str(int(member_id)).encode("utf-8")
    signature = hmac.new(_login_secret().encode("utf-8"), raw, hashlib.sha256).hexdigest()[:32]
    return f"{int(member_id)}.{signature}"


def _verify_login_token(token: str | None) -> int | None:
    if not token or "." not in str(token):
        return None
    member_text, signature = str(token).split(".", 1)
    if not member_text.isdigit():
        return None
    expected = _login_token(int(member_text)).split(".", 1)[1]
    if hmac.compare_digest(signature, expected):
        return int(member_text)
    return None


def restore_login() -> None:
    if st.session_state.get("user"):
        return
    member_id = _verify_login_token(query_value("session"))
    if not member_id:
        return
    try:
        user = db.get_member_by_id(member_id)
    except Error:
        user = None
    if user:
        st.session_state.user = user


def persist_login(user: dict[str, Any]) -> None:
    st.session_state.user = user
    try:
        st.query_params.clear()
        st.query_params["session"] = _login_token(int(user["member_id"]))
    except Exception:
        pass


def clear_login() -> None:
    st.session_state.user = None
    try:
        st.query_params.clear()
    except Exception:
        pass


def query_value(name: str) -> str | None:
    try:
        value = st.query_params.get(name)
    except Exception:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


def href_for(**params: str) -> str:
    bits = [f"{key}={quote(str(value))}" for key, value in params.items() if value]
    return "?" + "&".join(bits) if bits else "?"


def close_auth_modal() -> None:
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()


def naver_map_url(name: str | None, address: str | None = None) -> str:
    query = " ".join(part for part in [str(name or "").strip(), str(address or "").strip()] if part)
    return f"https://map.naver.com/p/search/{quote(query or '여행지')}"


def visitkorea_search_url(name: str | None) -> str:
    return f"https://korean.visitkorea.or.kr/search/search_list.do?keyword={quote(str(name or '').strip() or '축제')}"


def first_valid_url(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text.startswith(("http://", "https://")):
            return text
    return None


def image_source(row: dict[str, Any]) -> str | None:
    for key in ("image_path", "image_url", "image_original_url"):
        value = str(row.get(key) or "").strip()
        if not value:
            continue
        if value.startswith(("http://", "https://")):
            return value
        if os.path.exists(value):
            return value
        candidate = os.path.join(os.getcwd(), value.replace("/", os.sep))
        if os.path.exists(candidate):
            return candidate
    return None


def render_card_image(target, row: dict[str, Any], empty_text: str = "대표사진 없음") -> None:
    src = image_source(row)
    if src:
        target.image(src, use_container_width=True)
    else:
        safe_empty_text = html.escape(empty_text)
        target.markdown(
            '<div style="height:150px;border:1px dashed #D1D5DB;border-radius:14px;'
            'display:flex;align-items:center;justify-content:center;color:#6B7280;'
            'background:#F9FAFB;font-size:0.92rem;">'
            f'{safe_empty_text}</div>',
            unsafe_allow_html=True,
        )




def rating_display(row: dict[str, Any]) -> str:
    rating = recommender.safe_float(row.get("average_rating"))
    review_count = recommender.safe_int(row.get("review_count"))
    if rating <= 0:
        return "평점 없음"
    if review_count <= 0:
        return f"{rating:.2f}"
    return f"{rating:.2f}"


def rating_caption(row: dict[str, Any]) -> str:
    rating = recommender.safe_float(row.get("average_rating"))
    review_count = recommender.safe_int(row.get("review_count"))
    if rating <= 0:
        return "TourAPI 원천 데이터에는 별점이 없어 리뷰가 없으면 평점이 표시되지 않습니다."
    if review_count > 0:
        return f"리뷰 {review_count}개 기준"
    return "기존 DB에 저장된 평점 기준"


def render_score_breakdown(target, row: dict[str, Any]) -> None:
    breakdown = row.get("recommendation_breakdown") or []
    with target.expander("점수 근거", expanded=False):
        if not breakdown:
            st.write("선택한 지역과 카테고리에 포함된 기본 후보입니다.")
            return
        for item in breakdown:
            points = recommender.safe_float(item.get("points"))
            label = html.escape(str(item.get("label") or "점수 항목"))
            detail = html.escape(str(item.get("detail") or ""))
            if points > 0:
                st.markdown(f"**+{points:.1f}점 · {label}**")
            else:
                st.markdown(f"**{label}**")
            if detail:
                st.caption(detail)


def refresh_favorite_ids() -> set[int]:
    user = st.session_state.get("user")
    if not user:
        return set()
    try:
        favorite_ids = db.favorite_place_ids(user["member_id"])
    except Error:
        favorite_ids = set()
    if st.session_state.get("trip_result") is not None:
        st.session_state.trip_result["favorite_place_ids"] = favorite_ids
    return favorite_ids


def render_favorite_heart(target, row: dict[str, Any], favorite_ids: set[int], key_prefix: str) -> None:
    user = st.session_state.get("user")
    place_id = int(row.get("place_id") or 0)
    if not user or not place_id:
        return
    is_favorite = place_id in favorite_ids
    heart = "♥" if is_favorite else "♡"
    help_text = "찜 해제" if is_favorite else "찜하기"
    if target.button(heart, key=f"{key_prefix}_{place_id}", help=help_text, use_container_width=True):
        result = db.toggle_favorite(user["member_id"], place_id)
        refresh_favorite_ids()
        st.toast("찜에 추가했습니다." if result == "added" else "찜에서 삭제했습니다.")
        st.rerun()


def course_item_with_image(item: dict[str, Any], places_by_id: dict[int, dict[str, Any]]) -> dict[str, Any]:
    merged = dict(item)
    place_id = int(item.get("place_id") or 0)
    source = places_by_id.get(place_id) or {}
    for key in ("image_path", "image_url", "image_original_url"):
        if not merged.get(key) and source.get(key):
            merged[key] = source.get(key)
    if not merged.get("recommendation_breakdown") and source.get("recommendation_breakdown"):
        merged["recommendation_breakdown"] = source.get("recommendation_breakdown")
    if not merged.get("average_rating") and source.get("average_rating"):
        merged["average_rating"] = source.get("average_rating")
    if not merged.get("review_count") and source.get("review_count"):
        merged["review_count"] = source.get("review_count")
    return merged

def render_login_dialog() -> None:
    st.write("여행지 검색과 추천 코스 기능은 로그인 후 이용할 수 있습니다.")
    username = st.text_input("아이디", value="", key="login_username")
    password = st.text_input("비밀번호", value="", type="password", key="login_password")
    cols = st.columns([1, 1])
    if cols[0].button("로그인", type="primary", use_container_width=True, key="login_submit"):
        user = db.authenticate(username, password)
        if user:
            persist_login(user)
            st.rerun()
        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    if cols[1].button("닫기", use_container_width=True, key="login_close"):
        close_auth_modal()


def render_signup_dialog() -> None:
    st.write("회원가입 후 여행 조건에 맞는 추천 결과를 확인할 수 있습니다.")
    cols = st.columns(2)
    new_username = cols[0].text_input("아이디", key="signup_username")
    name = cols[1].text_input("이름", key="signup_name")
    new_password = st.text_input("비밀번호", type="password", key="signup_password")
    btn_cols = st.columns([1, 1])
    if btn_cols[0].button("회원가입", type="primary", use_container_width=True, key="signup_submit"):
        clean_username = str(new_username or "").strip()
        clean_name = str(name or "").strip()
        if not all([clean_username, clean_name, new_password]):
            st.warning("모든 항목을 입력해주세요.")
            return
        try:
            local_email = f"{clean_username}@traveldb.local"[:120]
            db.create_member(clean_username, new_password, clean_name, local_email, None)
            st.success("회원가입이 완료되었습니다. 이제 로그인해주세요.")
        except Error as exc:
            st.error(f"회원가입 실패: {exc}")
    if btn_cols[1].button("닫기", use_container_width=True, key="signup_close"):
        close_auth_modal()


if hasattr(st, "dialog"):
    render_login_modal = st.dialog("로그인")(render_login_dialog)
    render_signup_modal = st.dialog("회원가입")(render_signup_dialog)
else:
    render_login_modal = render_login_dialog
    render_signup_modal = render_signup_dialog


def render_account_panel() -> None:
    mode = query_value("auth")
    if mode not in {"login", "signup"} or st.session_state.user:
        return
    if mode == "login":
        render_login_modal()
    else:
        render_signup_modal()


def go_auth(mode: str) -> None:
    try:
        st.query_params.clear()
        st.query_params["auth"] = mode
    except Exception:
        pass
    st.rerun()


def render_login_required() -> None:
    st.markdown(
        """
        <div class="section-shell">
          <div class="section-kicker">LOGIN REQUIRED</div>
          <h2 class="section-title">로그인 후 이용할 수 있습니다</h2>
          <p>여행지 검색, 추천 코스, 숙소/식당 추천, 찜하기 기능은 로그인한 회원에게만 제공됩니다. 로그인과 회원가입은 화면 우측 상단에서 할 수 있습니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    if st.session_state.user:
        user_name = html.escape(str(st.session_state.user["name"]))
        auth_html = f'<span class="nav-user">{user_name}님</span><a target="_self" href="{href_for(logout="1")}">로그아웃</a>' 
    else:
        auth_html = f'<a target="_self" href="{href_for(auth="login")}">로그인</a><a target="_self" href="{href_for(auth="signup")}">회원가입</a>' 
    st.markdown(
        f"""
        <section class="hero-shell">
          <video class="hero-video" autoplay muted loop playsinline
            src="https://plugin-assets.open-design.ai/plugins/skyelite-private-jets/hf_20260328_091828_e240eb17-6edc-4129-ad9d-98678e3fd238-86655b.mp4">
          </video>
          <div class="hero-nav">
            <div class="nav-left">
              <div class="brand">TravelDB</div>
              <div class="nav-menu">
                <span>데이터</span>
                <span>추천</span>
                <span>코스</span>
                <span>문의</span>
              </div>
            </div>
            <div class="nav-auth">
              {auth_html}
            </div>
          </div>
          <div class="hero-main">
            <div class="hero-content">
              <p class="eyebrow">공공 관광 데이터</p>
              <h1 class="headline">
                <span class="line1">Curated.</span>
                <span class="line2">Accessible.</span>
              </h1>
              <p class="hero-copy">
                어디로, 며칠 동안, 어떤 취향으로 떠날지만 고르면 코스와 숙소, 식당을 한 번에 정리합니다.
              </p>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def category_db_names(selected: list[str]) -> list[str]:
    names: list[str] = []
    for category in selected:
        names.extend(CATEGORY_TO_DB.get(category, [category]))
    return list(dict.fromkeys(names))


def duration_from_dates(start_date: date, end_date: date) -> str:
    nights = max((end_date - start_date).days, 0)
    if nights <= 0:
        return "당일치기"
    if nights == 1:
        return "1박 2일"
    return f"{nights}박 {nights + 1}일"


def style_from_categories(categories: list[str]) -> str:
    if "미식" in categories:
        return "맛집 위주"
    if "카페" in categories:
        return "카페 위주"
    if "자연" in categories:
        return "자연 경관"
    if "사진 명소" in categories:
        return "사진 명소"
    if "축제" in categories:
        return "축제/행사"
    return "관광지 위주"


def _region_code(row: dict[str, Any], key: str) -> str:
    return str(row.get(key) or "").strip()


def _minor_region_label(region_name: str, major_name: str, province: str) -> str:
    for prefix in (major_name, province):
        prefix = str(prefix or "").strip()
        if prefix and region_name.startswith(prefix + " "):
            return region_name[len(prefix) + 1 :].strip() or region_name
    if major_name == "세종특별자치시" and region_name == "세종특별자치시 세종특별자치시":
        return "세종특별자치시"
    return region_name


def _fallback_region_hierarchy(rows: list[dict[str, Any]] | None = None) -> dict[str, list[dict[str, str]]]:
    hierarchy: dict[str, list[dict[str, str]]] = {
        "전국": [{"label": "전체", "value": "전국", "display": "전국"}]
    }
    grouped: dict[str, list[dict[str, str]]] = {region_name: [] for region_name in MAJOR_REGION_ORDER}
    seen: set[tuple[str, str]] = set()

    for row in rows or []:
        region_name = str(row.get("region_name") or "").strip()
        province = str(row.get("province") or "").strip()
        if not region_name:
            continue
        major_name = next(
            (
                major
                for major in MAJOR_REGION_ORDER
                if region_name == major
                or province == major
                or region_name.startswith(major + " ")
                or province.startswith(major + " ")
            ),
            None,
        )
        if not major_name or region_name == major_name:
            continue
        label = _minor_region_label(region_name, major_name, province)
        key = (major_name, region_name)
        if key in seen:
            continue
        grouped[major_name].append({"label": label, "value": region_name, "display": region_name})
        seen.add(key)

    for region_name in MAJOR_REGION_ORDER:
        hierarchy[region_name] = [{"label": "전체", "value": region_name, "display": f"{region_name} 전체"}]
        hierarchy[region_name].extend(grouped.get(region_name, []))
    return hierarchy


def region_hierarchy_options() -> dict[str, list[dict[str, str]]]:
    try:
        rows = db.get_region_options()
    except Error:
        rows = []

    hierarchy: dict[str, list[dict[str, str]]] = {
        "전국": [{"label": "전체", "value": "전국", "display": "전국"}]
    }
    if not rows:
        return _fallback_region_hierarchy(rows)

    major_rows = [
        row
        for row in rows
        if _region_code(row, "tour_area_code") and not _region_code(row, "tour_sigungu_code")
    ]
    child_rows: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        area_code = _region_code(row, "tour_area_code")
        sigungu_code = _region_code(row, "tour_sigungu_code")
        if area_code and sigungu_code:
            child_rows.setdefault(area_code, []).append(row)

    order = {name: index for index, name in enumerate(MAJOR_REGION_ORDER)}
    major_rows.sort(key=lambda row: order.get(str(row.get("region_name") or ""), 999))
    if not major_rows:
        return _fallback_region_hierarchy(rows)

    for major in major_rows:
        major_name = str(major.get("region_name") or "").strip()
        area_code = _region_code(major, "tour_area_code")
        if not major_name:
            continue
        options = [{"label": "전체", "value": major_name, "display": f"{major_name} 전체"}]
        for child in child_rows.get(area_code, []):
            child_name = str(child.get("region_name") or "").strip()
            if not child_name:
                continue
            label = _minor_region_label(child_name, major_name, str(child.get("province") or ""))
            options.append({"label": label, "value": child_name, "display": child_name})
        hierarchy[major_name] = options
    return hierarchy


def render_search_form() -> dict[str, Any] | None:
    if not st.session_state.get("user"):
        return None

    default_start = date.today() + timedelta(days=5)
    default_end = default_start + timedelta(days=1)
    hierarchy = region_hierarchy_options()
    major_options = list(hierarchy.keys())

    with st.container(border=True):
        st.markdown('<span id="trip-search-panel"></span>', unsafe_allow_html=True)
        top = st.columns([1.05, 1.15, 0.95, 0.95, 0.65])
        major_region = top[0].selectbox("대분류 지역", major_options, index=0, key="region_major")
        minor_options = hierarchy.get(major_region) or [{"label": "전체", "value": major_region, "display": f"{major_region} 전체"}]
        minor_labels = [option["label"] for option in minor_options]
        minor_label = top[1].selectbox("소분류 지역", minor_labels, index=0, key=f"region_minor_{major_region}")
        selected_region = next((option for option in minor_options if option["label"] == minor_label), minor_options[0])
        destination = selected_region["value"]
        destination_label = selected_region["display"]
        start_date = top[2].date_input("출발일", value=default_start)
        end_date = top[3].date_input("돌아오는 날", value=default_end)
        adults = top[4].number_input("인원", min_value=1, max_value=10, value=2, step=1)
        categories = st.multiselect(
            "여행 카테고리",
            TRIP_CATEGORIES,
            default=[],
            help="주동행인/예산처럼 API에 없는 조건은 제거하고, TourAPI의 콘텐츠 타입·세부 분류 기준으로 추천합니다.",
        )
        submitted = st.button("검색", type="primary", use_container_width=True, key="trip_search_submit")

    if not submitted:
        return None

    if end_date < start_date:
        st.warning("돌아오는 날은 출발일 이후로 선택해주세요.")
        return None

    return {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "adults": adults,
        "categories": categories,
        "region_major": major_region,
        "region_minor": minor_label,
        "destination_label": destination_label,
        "duration_label": duration_from_dates(start_date, end_date),
    }


def trip_preferences(search: dict[str, Any]) -> dict[str, Any]:
    selected_categories = list(search.get("categories") or [])
    return {
        "travel_style": style_from_categories(selected_categories),
        "selected_categories": selected_categories,
        "selected_db_categories": category_db_names(selected_categories),
        "adults": search.get("adults"),
        "destination": search.get("destination"),
        "duration": "1박 2일" if "1박" in search["duration_label"] else "당일치기",
    }


def favorite_bias() -> dict[str, int]:
    user = st.session_state.get("user")
    if not user:
        return {}
    try:
        return db.favorite_category_counts(user["member_id"])
    except Error:
        return {}


def build_trip_result(search: dict[str, Any]) -> dict[str, Any]:
    if not st.session_state.get("user"):
        raise PermissionError("로그인 후 이용할 수 있습니다.")

    db_categories = category_db_names(search["categories"])
    rows = db.search_places_for_planner(search["destination"], db_categories, limit=180)
    # 지역을 선택했는데 후보가 없다고 해서 전국 후보로 자동 대체하지 않는다.
    # 자동 대체를 하면 사용자는 "대구"를 검색했는데 부산/서울 결과가 섞여 보일 수 있다.
    fallback_used = False

    try:
        api_boosts = db.api_score_lookup(search["destination"], [str(row.get("place_name") or "") for row in rows])
    except Error:
        api_boosts = {}
    for row in rows:
        place_name = str(row.get("place_name") or "")
        boost = api_boosts.get(place_name)
        if boost:
            row["api_score_boost"] = boost.get("boost", 0)
            row["api_reasons"] = boost.get("reasons", [])

    preferences = trip_preferences(search)
    scored = recommender.score_places(rows, preferences, favorite_bias())
    course = course_generator.generate_course(scored, preferences["duration"])
    try:
        favorite_place_ids = db.favorite_place_ids(st.session_state.user["member_id"])
    except Error:
        favorite_place_ids = set()
    restaurants = db.search_restaurants_for_region(search["destination"], limit=8)
    accommodations = db.search_accommodations_for_region(search["destination"], limit=6)
    festivals = db.search_festivals_for_region(search["destination"], limit=6)
    try:
        insights = db.api_insights_for_trip(search["destination"], [str(row.get("place_name") or "") for row in scored[:12]])
    except Error:
        insights = {}
    return {
        "search": search,
        "preferences": preferences,
        "places": scored,
        "course": course,
        "restaurants": restaurants,
        "accommodations": accommodations,
        "festivals": festivals,
        "api_insights": insights,
        "favorite_place_ids": favorite_place_ids,
        "fallback_used": fallback_used,
    }


def section_header(kicker: str, title: str, body: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-shell">
          <div class="section-kicker">{kicker}</div>
          <h2 class="section-title">{title}</h2>
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary(result: dict[str, Any]) -> None:
    search = result["search"]
    places = result["places"]
    course = result["course"]
    insights = result.get("api_insights") or {}
    cols = st.columns(4)
    cols[0].metric("여행지", search.get("destination_label") or search.get("destination") or "전국")
    cols[1].metric("일정", search["duration_label"])
    cols[2].metric("추천 후보", f"{len(places)}곳")
    cols[3].metric("코스 구성", f"{len(course)}개")
    if result["fallback_used"]:
        st.info("선택한 지역에 데이터가 부족해 전국 후보를 함께 참고했습니다. API 수집 지역을 넓히면 정확도가 올라갑니다.")

    with st.expander("추천에 반영한 공공데이터"):
        visitor = insights.get("visitor")
        if visitor:
            count = visitor.get("visitor_count")
            count_text = f"{int(count):,}명" if count is not None else "집계값 없음"
            st.write(f"방문자수: {visitor.get('region_name')} · {visitor.get('stat_date') or '-'} · {count_text}")
        centers = insights.get("centers") or []
        if centers:
            st.write("중심 관광지: " + ", ".join(str(row.get("attraction_name")) for row in centers[:5]))
        related = insights.get("related") or []
        if related:
            st.write("연관 관광지: " + ", ".join(f"{row.get('origin_name')}→{row.get('related_name')}" for row in related[:4]))
        demand = insights.get("demand_metrics") or []
        diversity = insights.get("diversity_metrics") or []
        if demand:
            st.write("관광 자원 수요 지표: " + ", ".join(str(row.get("metric_name")) for row in demand[:4]))
        if diversity:
            st.write("관광 다양성 지표: " + ", ".join(str(row.get("metric_name")) for row in diversity[:4]))
        photo_count = int(insights.get("photo_count") or 0)
        st.caption(f"관광사진 저장 건수: {photo_count}건 · 데이터가 비어 있으면 기본 추천 로직으로 계속 계산합니다.")
        st.caption("평점은 사이트 리뷰 평균값입니다. 주동행인/숙박요금/식사가격처럼 승인 API에서 직접 제공되지 않는 값은 추천 조건에서 제외했습니다.")


def _money(value: Any) -> str:
    try:
        return f"{int(value):,}원"
    except Exception:
        return "-"


def weather_center_for_region(destination: str) -> dict[str, Any] | None:
    try:
        center = db.region_center(destination)
    except Error:
        center = None
    if center and center.get("latitude") and center.get("longitude"):
        return center

    text = str(destination or "전국")
    for keyword, fallback in REGION_FALLBACK_CENTERS.items():
        if keyword == text or keyword in text or text in keyword:
            return dict(fallback)
    return dict(REGION_FALLBACK_CENTERS["전국"])




def get_live_api_status_safe() -> dict[str, bool]:
    """external_services.py가 예전 버전이거나 Streamlit 캐시가 남아 있어도 앱이 죽지 않게 한다."""
    status_func = getattr(external_services, "live_api_status", None)
    if callable(status_func):
        try:
            return status_func()
        except Exception:
            pass

    def has_key(*names: str) -> bool:
        for name in names:
            if os.getenv(name):
                return True
            try:
                if st.secrets.get(name):
                    return True
                for section in ("api", "apis", "keys", "secrets", "weather", "kakao", "kma", "openai"):
                    nested = st.secrets.get(section)
                    if nested and nested.get(name):
                        return True
            except Exception:
                pass
        return False

    return {
        "kakao": has_key("KAKAO_REST_API_KEY", "KAKAO_LOCAL_API_KEY", "KAKAO_API_KEY"),
        "kma_short": has_key("KMA_SHORT_FORECAST_SERVICE_KEY", "KMA_SHORT_API_KEY", "KMA_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY"),
        "kma_mid": has_key("KMA_MID_FORECAST_SERVICE_KEY", "KMA_MID_API_KEY", "KMA_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY"),
        "openai": has_key("OPENAI_API_KEY"),
    }


def render_live_api_tabs(result: dict[str, Any]) -> None:
    search = result.get("search") or {}
    destination = str(search.get("destination") or "전국")
    start_date = search.get("start_date") or date.today()
    adults = int(search.get("adults") or 1)

    section_header("LIVE API", "실시간 API 보강", "카카오맵, 기상청 단기/중기예보, GPT API 키가 있으면 실시간 장소·날씨·교통비 추정까지 확인합니다.")
    tab_kakao, tab_weather, tab_transport = st.tabs(["카카오맵 인기 장소", "날짜별 날씨", "교통편 금액 계산"])
    api_status = get_live_api_status_safe()

    with tab_kakao:
        st.markdown('<span class="live-pill">Kakao Local API</span>', unsafe_allow_html=True)
        default_kakao_keyword = f"{destination} 관광지" if destination != "전국" else "서울 관광지"
        keyword = st.text_input("검색어", value=default_kakao_keyword, key="kakao_live_keyword")
        if st.button("카카오맵 실시간 검색", type="primary", key="kakao_live_search"):
            try:
                rows = external_services.search_kakao_places(keyword, region="" if destination == "전국" else destination, size=10)
                try:
                    db.save_kakao_places(destination, keyword, rows)
                except Error:
                    pass
                st.session_state["kakao_live_rows"] = rows
                st.session_state["kakao_live_searched"] = True
                st.session_state["kakao_live_last_keyword"] = keyword
            except Exception as exc:
                st.error(f"카카오맵 검색 실패: {exc}")
        rows = st.session_state.get("kakao_live_rows") or []
        if not rows:
            if st.session_state.get("kakao_live_searched"):
                st.warning("카카오 API 호출은 성공했지만 검색 결과가 0건입니다. '부산 관광지', '제주 맛집', '서울 카페'처럼 지역+장소유형으로 다시 검색해보세요.")
            elif api_status.get("kakao"):
                st.info("카카오 REST 키는 감지됐습니다. 검색 버튼을 누르면 카카오 Local API 결과를 표시합니다. '인기'는 카카오 공식 정렬값이 아니라 키워드 검색 결과입니다.")
            else:
                st.info("KAKAO_REST_API_KEY가 감지되지 않았습니다. secrets.toml 최상위 또는 [api] 섹션에 REST API 키를 넣어주세요.")
        for row in rows[:10]:
            with st.container(border=True):
                cols = st.columns([2.4, 0.8])
                name = row.get("place_name") or "이름 없음"
                url = row.get("place_url") or naver_map_url(name, row.get("road_address_name") or row.get("address_name"))
                cols[0].markdown(f"### [{name}]({url})")
                cols[0].caption((row.get("category_name") or "카테고리 정보 없음") + (f" · 검색어: {row.get('_searched_query')}" if row.get("_searched_query") else ""))
                cols[0].write(row.get("road_address_name") or row.get("address_name") or "주소 정보 없음")
                cols[1].link_button("카카오맵", url, use_container_width=True)

    with tab_weather:
        st.markdown('<span class="live-pill">KMA Weather API</span>', unsafe_allow_html=True)
        center = weather_center_for_region(destination)
        if not center:
            st.info("날씨 조회에 사용할 지역 좌표를 찾지 못했습니다.")
        else:
            st.caption(f"조회 기준 좌표: {center.get('region_name')} · {center.get('latitude')} / {center.get('longitude')}")
            if st.button("선택 날짜 날씨 조회", type="primary", key="weather_live_search"):
                try:
                    weather = external_services.weather_for_date(float(center["latitude"]), float(center["longitude"]), start_date, region_name=str(center.get("region_name") or destination))
                    try:
                        db.save_weather_snapshot(str(center.get("region_name") or destination), start_date, center.get("latitude"), center.get("longitude"), weather)
                    except Error:
                        pass
                    st.session_state["weather_live_result"] = weather
                except Exception as exc:
                    st.error(f"날씨 조회 실패: {exc}")
            weather = st.session_state.get("weather_live_result")
            if weather:
                cols = st.columns(4)
                cols[0].metric("예보 출처", weather.get("provider") or weather.get("source") or "기상청")
                cols[1].metric("날씨", weather.get("condition") or "정보 없음")
                temp_text = "-" if weather.get("temp") is None else f"{weather.get('temp')}℃"
                cols[2].metric("대표 기온", temp_text)
                rain_text = "-" if weather.get("precip_probability") is None else f"{weather.get('precip_probability')}%"
                cols[3].metric("강수확률", rain_text)

                detail_cols = st.columns(4)
                min_text = "-" if weather.get("min_temp") is None else f"{weather.get('min_temp')}℃"
                max_text = "-" if weather.get("max_temp") is None else f"{weather.get('max_temp')}℃"
                humidity_text = "-" if weather.get("humidity") is None else f"{weather.get('humidity')}%"
                wind_text = "-" if weather.get("wind_speed") is None else f"{weather.get('wind_speed')}m/s"
                detail_cols[0].metric("최저", min_text)
                detail_cols[1].metric("최고", max_text)
                detail_cols[2].metric("습도", humidity_text)
                detail_cols[3].metric("풍속", wind_text)
                if weather.get("note"):
                    st.caption(weather["note"])
            else:
                if api_status.get("kma_short") or api_status.get("kma_mid"):
                    st.info("기상청 키는 감지됐습니다. 선택 날짜 날씨 조회 버튼을 누르면 오늘~3일 뒤는 단기예보, 4~10일 뒤는 중기예보를 사용합니다.")
                else:
                    st.info("KMA_SHORT_FORECAST_SERVICE_KEY와 KMA_MID_FORECAST_SERVICE_KEY가 감지되지 않았습니다. secrets.toml 최상위 또는 [api] 섹션에 넣어주세요.")

    with tab_transport:
        st.markdown('<span class="live-pill">OpenAI JSON Parsing</span>', unsafe_allow_html=True)
        cols = st.columns([1, 1, 0.6])
        origin = cols[0].text_input("출발지", value="서울역", key="transport_origin")
        destination_text = cols[1].text_input("도착지", value=destination if destination != "전국" else "부산", key="transport_destination")
        people = cols[2].number_input("인원", min_value=1, max_value=10, value=adults, step=1, key="transport_people")
        if st.button("GPT로 교통편/금액 JSON 계산", type="primary", key="transport_live_search"):
            try:
                estimate = external_services.transport_estimate_with_gpt(origin, destination_text, str(start_date), int(people))
                try:
                    db.save_transport_estimate(origin, destination_text, start_date, int(people), estimate)
                except Error:
                    pass
                st.session_state["transport_estimate"] = estimate
            except Exception as exc:
                st.error(f"교통비 계산 실패: {exc}")
        estimate = st.session_state.get("transport_estimate")
        if estimate:
            st.caption(estimate.get("disclaimer") or "실제 예매 요금이 아닌 추정값입니다.")
            options = estimate.get("options") or []
            for option in options:
                with st.container(border=True):
                    cols = st.columns([1.1, 1.2, 2.0])
                    cols[0].subheader(option.get("mode") or "교통편")
                    cols[1].metric("예상 시간", f"{option.get('estimated_time_minutes', '-')}분")
                    cols[1].metric("예상 금액", f"{_money(option.get('estimated_cost_min'))} ~ {_money(option.get('estimated_cost_max'))}")
                    cols[2].write(option.get("route_summary") or "-")
                    cols[2].caption(f"장점: {option.get('pros') or '-'} / 단점: {option.get('cons') or '-'}")
        else:
            st.info("OPENAI_API_KEY를 설정하면 출발·도착지를 JSON 형태로 파싱해 교통편별 예상 금액을 보여줍니다.")


def render_course(result: dict[str, Any]) -> None:
    course = result["course"]
    places_by_id = {int(row.get("place_id") or 0): row for row in result.get("places") or [] if row.get("place_id")}
    section_header("ITINERARY", "추천 코스", "추천 점수와 카테고리를 기준으로 시간대별 방문 순서를 정리했습니다.")
    if not course:
        st.info("코스를 만들 후보가 아직 부족합니다.")
        return

    for item in course:
        item = course_item_with_image(item, places_by_id)
        with st.container(border=True):
            cols = st.columns([1.1, 2.4, 0.9])
            render_card_image(cols[0], item, "코스 사진 없음")
            cols[1].write(f"**{item['time_slot']}**")
            map_url = naver_map_url(item.get("place_name"), item.get("address"))
            cols[1].markdown(f"### [{item['place_name']}]({map_url})")
            cols[1].caption(f"{item['category']} · {item['address']}")
            cols[1].write(item["reason"])
            cols[2].metric("추천 점수", f"{item.get('recommendation_score', 0):.1f}")
            cols[2].metric("평점", rating_display(item))
            cols[2].caption(rating_caption(item))
            render_score_breakdown(cols[2], item)
            cols[2].link_button("네이버 지도", map_url, use_container_width=True)

def render_place_card(row: dict[str, Any], key_prefix: str, favorite_ids: set[int] | None = None) -> None:
    favorite_ids = favorite_ids or set()
    with st.container(border=True):
        top = st.columns([1, 2.4, 0.9])
        render_card_image(top[0], row, "관광지 사진 없음")
        name = row.get("place_name") or "이름 없음"
        map_url = naver_map_url(name, row.get("address"))
        top[1].markdown(f"### [{name}]({map_url})")
        top[1].caption(f"{row.get('region_name') or '-'} · {row.get('address') or '주소 정보 없음'}")
        top[1].write(row.get("overview") or "소개 정보가 없습니다.")
        render_favorite_heart(top[2], row, favorite_ids, key_prefix)
        top[2].metric("추천 점수", f"{row.get('recommendation_score', 0):.1f}")
        top[2].metric("평점", rating_display(row))
        top[2].caption(rating_caption(row))
        render_score_breakdown(top[2], row)
        top[2].link_button("네이버 지도", map_url, use_container_width=True)

        reasons = row.get("recommendation_reasons") or []
        for reason in reasons[:3]:
            st.write(f"- {reason}")
        st.caption(f"카테고리: {row.get('categories') or '-'} · 태그: {row.get('display_tags') or row.get('tags') or '-'}")

def render_recommendations(result: dict[str, Any]) -> None:
    section_header("ATTRACTIONS", "주요 관광지", "지역, 카테고리, 사진, 상세정보, 방문자/중심/연관/집중률 공공데이터로 점수를 계산했습니다.")
    places = result["places"][:8]
    if not places:
        st.info("추천할 관광지가 없습니다.")
        return
    favorite_ids = set(result.get("favorite_place_ids") or refresh_favorite_ids())
    for row in places:
        render_place_card(row, "place_fav", favorite_ids)


def render_accommodations(result: dict[str, Any]) -> None:
    section_header("STAY", "숙소", "선택한 지역의 숙박 데이터를 네이버 지도 링크와 함께 정리했습니다.")
    accommodations = result["accommodations"]
    if not accommodations:
        st.info("해당 지역 숙소 데이터가 아직 없습니다.")
        return
    for item in accommodations:
        with st.container(border=True):
            cols = st.columns([1, 2.4, 0.9])
            render_card_image(cols[0], item, "숙소 사진 없음")
            name = item.get("accommodation_name") or "이름 없음"
            map_url = naver_map_url(name, item.get("address"))
            cols[1].markdown(f"### [{name}]({map_url})")
            cols[1].caption(f"{item.get('region_name') or '-'} · {item.get('address') or '주소 정보 없음'}")
            cols[1].write(f"전화: {item.get('phone') or '정보 없음'}")
            cols[2].link_button("네이버 지도", map_url, use_container_width=True)


def render_restaurants(result: dict[str, Any]) -> None:
    section_header("FOOD", "식당", "선택한 지역의 음식점 데이터를 네이버 지도 링크와 함께 정리했습니다.")
    restaurants = result["restaurants"]
    if not restaurants:
        st.info("해당 지역 식당 데이터가 아직 없습니다.")
        return
    for item in restaurants:
        with st.container(border=True):
            cols = st.columns([1, 2.4, 0.9])
            render_card_image(cols[0], item, "식당 사진 없음")
            name = item.get("restaurant_name") or "이름 없음"
            map_url = naver_map_url(name, item.get("address"))
            cols[1].markdown(f"### [{name}]({map_url})")
            cols[1].caption(f"{item.get('region_name') or '-'} · {item.get('address') or '주소 정보 없음'}")
            cols[1].write(f"종류: {item.get('food_type') or '음식점'}")
            cols[2].link_button("네이버 지도", map_url, use_container_width=True)


def render_festivals(result: dict[str, Any]) -> None:
    section_header("FESTIVAL", "축제", "선택한 지역의 축제/행사 데이터를 공식 정보 링크와 함께 정리했습니다.")
    festivals = result.get("festivals") or []
    if not festivals:
        st.info("해당 지역 축제 데이터가 아직 없습니다.")
        return
    for item in festivals:
        with st.container(border=True):
            cols = st.columns([1, 2.4, 0.9])
            render_card_image(cols[0], item, "축제 사진 없음")
            name = item.get("festival_name") or "이름 없음"
            info_url = first_valid_url(item.get("homepage"), item.get("source_url")) or visitkorea_search_url(name)
            cols[1].markdown(f"### [{name}]({info_url})")
            period = " ~ ".join(str(x) for x in [item.get("start_date"), item.get("end_date")] if x) or "기간 정보 없음"
            cols[1].caption(f"{item.get('region_name') or '-'} · {period}")
            cols[1].write(item.get("overview") or "소개 정보가 없습니다.")
            cols[2].write(f"입장료: {item.get('fee_info') or '정보 없음'}")
            cols[2].link_button("축제 정보", info_url, use_container_width=True)


def render_data_note() -> None:
    has_key = configured_api_key() is not None
    with st.expander("데이터 적용 상태"):
        if has_key:
            st.success("API 키가 설정되어 있습니다. 화면에서는 키를 입력받지 않습니다.")
        else:
            st.warning("API 키가 설정되지 않았습니다. `.streamlit/secrets.toml`에 키를 추가하면 데이터 보강 수집을 실행할 수 있습니다.")
        try:
            counts = db.advanced_api_counts()
        except Error:
            counts = {}
        st.write(
            "8개 승인 TourAPI는 같은 공공데이터포털 키로 연결합니다. 카테고리/지역/사진/축제기간/요금 일부/방문자/중심·연관·집중률/수요·다양성만 추천 근거로 사용합니다. "
            "카카오맵·기상청 단기/중기예보·GPT API는 별도 키가 있을 때 실시간 탭에서만 호출합니다."
        )
        st.caption(
            "저장 현황: "
            f"사진 {counts.get('tour_photos', 0)}건 · "
            f"방문자수 {counts.get('region_visitor_stats', 0)}건 · "
            f"집중률 {counts.get('attraction_concentration', 0)}건 · "
            f"연관 {counts.get('related_attractions', 0)}건 · "
            f"중심 {counts.get('center_attractions', 0)}건 · "
            f"수요/다양성 {counts.get('regional_demand_metrics', 0)}건"
        )


def render_app() -> None:
    render_hero()
    render_account_panel()
    if not st.session_state.get("user"):
        render_login_required()
        return

    search = render_search_form()
    if search:
        try:
            st.session_state.trip_result = build_trip_result(search)
        except PermissionError as exc:
            st.warning(str(exc))
            st.session_state.trip_result = None
        except Error as exc:
            st.error(f"추천 데이터를 불러오지 못했습니다: {exc}")
            st.session_state.trip_result = None

    result = st.session_state.trip_result
    if result:
        render_summary(result)
        render_live_api_tabs(result)
        render_recommendations(result)
        render_accommodations(result)
        render_restaurants(result)
        render_festivals(result)
        render_course(result)
    else:
        section_header(
            "ONE SEARCH",
            "검색 한 번으로 코스, 숙소, 식당까지",
            "지역과 날짜, 카테고리를 고르면 여러 탭을 오가지 않고 한 화면에서 추천 결과를 확인합니다.",
        )
        cols = st.columns(3)
        samples = [
            ("1", "카테고리 선택", "관광지, 미식, 카페, 자연처럼 여행 목적을 먼저 고릅니다."),
            ("2", "추천 점수 계산", "지역, 카테고리, 사진, 상세정보, 방문자/중심/연관 관광지 지표로 후보를 정렬합니다."),
            ("3", "코스 통합 출력", "방문지, 숙소, 식당, 추천 이유를 한 번에 보여줍니다."),
        ]
        for col, (num, title, body) in zip(cols, samples):
            with col:
                with st.container(border=True):
                    st.caption(num)
                    st.subheader(title)
                    st.write(body)

    render_data_note()


def main() -> None:
    inject_design()
    init_state()
    ok, message = db.test_connection()
    if not ok:
        render_hero()
        st.error("DB 연결에 실패했습니다. HeidiSQL/MariaDB 설정을 확인해주세요.")
        st.code(message)
        st.code(f"Python: {sys.executable}\nDB config: {dict(db.db_config(), password='********')}")
        return
    try:
        db.ensure_recommendation_schema()
        db.ensure_media_schema()
        db.ensure_advanced_api_schema()
    except Error:
        pass
    if query_value("logout") == "1":
        clear_login()
        st.rerun()
    restore_login()
    render_app()


if __name__ == "__main__":
    main()
