from __future__ import annotations

import hashlib
import hmac
import importlib
import html
import os
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

import streamlit as st
from mysql.connector import Error

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
          :root {
            --page: #FFFFFF;
            --surface: #FFFFFF;
            --surface-soft: #F1F5F9;
            --ink: #111827;
            --muted: #64748B;
            --line: #E2E8F0;
            --blue: #FF3D5A;
            --blue-dark: #E21F43;
            --teal: #0F766E;
            --amber: #F59E0B;
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
            font-family: 'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', system-ui, sans-serif;
          }

          html, body, .stApp, [data-testid="stAppViewContainer"], .main {
            margin: 0 !important;
            padding: 0 !important;
          }

          [data-testid="stAppViewContainer"] > .main {
            padding-top: 0 !important;
          }

          .stApp {
            background: #fff;
            color: var(--ink);
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
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin-left: auto;
            margin-right: auto;
          }

          h1, h2, h3 {
            color: var(--gray-900);
            letter-spacing: 0;
          }

          p, label, .stMarkdown, .stCaption {
            color: var(--muted);
          }

          div[data-testid="stForm"],
          div[data-testid="stExpander"],
          div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px;
            border-color: var(--line);
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
          }

          div[data-testid="stForm"],
          div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) {
            max-width: min(94vw, 1320px);
            margin: 44px auto 58px !important;
            padding: 0 0 26px !important;
            border: 1px solid rgba(226,232,240,0.95) !important;
            border-radius: 14px !important;
            background: rgba(255,255,255,0.97) !important;
            box-shadow: 0 20px 48px rgba(15,23,42,0.16) !important;
            position: relative;
            z-index: 4;
            overflow: hidden;
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
            border: 1px solid var(--line);
            background: #fff;
            color: var(--ink);
            font-weight: 700;
          }

          .stButton > button:hover,
          .stDownloadButton > button:hover {
            border-color: var(--blue);
            color: var(--blue-dark);
            box-shadow: 0 10px 24px rgba(255, 61, 90, 0.12);
          }

          .stButton > button[kind="primary"] {
            background: var(--blue);
            border-color: var(--blue);
            color: #fff;
          }

          .region-picker {
            display: grid;
            grid-template-columns: minmax(320px, 0.42fr) minmax(420px, 1fr);
            min-height: 232px;
            border-bottom: 1px solid var(--gray-200);
            background: #fff;
          }

          .region-major-panel {
            border-right: 1px solid var(--gray-200);
            background: #fbfcff;
            padding: 16px 12px;
          }

          .region-major-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px 8px;
          }

          .region-major-item,
          .region-minor-item {
            text-decoration: none !important;
            color: var(--gray-900) !important;
            font-weight: 700;
            letter-spacing: 0;
          }

          .region-major-item {
            min-height: 44px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 0 12px;
            border: 2px solid transparent;
            border-radius: 10px;
            font-size: 0.98rem;
          }

          .region-major-item:hover {
            background: #eef3ff;
            color: var(--ink) !important;
          }

          .region-major-item.active {
            background: #edf2ff;
            border-color: var(--ink);
            color: var(--ink) !important;
            box-shadow: inset 0 0 0 1px rgba(31,75,255,0.08);
          }

          .region-count {
            color: #5b6f99;
            font-weight: 700;
          }

          .region-arrow {
            color: var(--ink);
            font-size: 1.35rem;
            line-height: 1;
          }

          .region-minor-panel {
            position: relative;
            padding: 58px 28px 26px;
            background: #fff;
          }

          .region-panel-actions {
            position: absolute;
            right: 20px;
            top: 16px;
            display: flex;
            gap: 14px;
            font-size: 0.88rem;
            font-weight: 700;
          }

          .region-panel-actions a,
          .region-panel-actions span {
            color: var(--gray-500) !important;
            text-decoration: none !important;
          }

          .region-panel-actions a:hover {
            color: var(--ink) !important;
          }

          .region-minor-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(160px, 1fr));
            gap: 22px 34px;
          }

          .region-minor-item {
            display: flex;
            align-items: center;
            gap: 12px;
            min-height: 38px;
            font-size: 0.98rem;
          }

          .region-box {
            width: 20px;
            height: 20px;
            border: 2px solid var(--gray-300);
            background: #fff;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: transparent;
            font-weight: 900;
            font-size: 1.15rem;
            line-height: 1;
          }

          .region-minor-item.active {
            color: var(--gray-900) !important;
          }

          .region-minor-item.active .region-box {
            border-color: #6C7CFF;
            color: #6C7CFF;
          }

          .region-picker-title {
            position: absolute;
            left: -9999px;
          }

          div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) .stButton > button {
            width: 100%;
            border-radius: 8px;
            justify-content: flex-start;
            min-height: 42px;
            padding-left: 14px;
            padding-right: 14px;
          }

          .hero-shell {
            position: relative;
            left: 50%;
            transform: translateX(-50%);
            width: 100vw;
            height: 100vh;
            min-height: 760px;
            overflow: hidden;
            margin: -24px 0 0;
            background: #eef2f7;
          }

          .hero-photo,
          .hero-video {
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            top: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center center;
            z-index: 0;
          }

          .hero-shell::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 110px;
            background: linear-gradient(180deg, rgba(255,255,255,0.88), rgba(255,255,255,0));
            border-bottom: 0;
            z-index: 1;
          }

          .hero-shell::after {
            content: "";
            position: absolute;
            inset: 0;
            background:
              linear-gradient(180deg, rgba(255,255,255,0.34) 0%, rgba(255,255,255,0.08) 30%, rgba(15,23,42,0.20) 100%),
              linear-gradient(90deg, rgba(15,23,42,0.12) 0%, rgba(15,23,42,0.02) 48%, rgba(15,23,42,0.10) 100%);
            z-index: 1;
          }

          .hero-nav {
            position: relative;
            z-index: 2;
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 0 auto;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            height: 84px;
          }

          .nav-left {
            display: flex;
            align-items: center;
            gap: 0;
          }

          .brand {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            font-size: 1.32rem;
            font-weight: 800;
            color: var(--blue);
            white-space: nowrap;
          }

          .brand-mark {
            width: 30px;
            height: 30px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            background: var(--blue);
            color: #fff;
            font-size: 0.9rem;
            font-weight: 800;
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
            color: var(--ink);
            font-size: 0.95rem;
            font-weight: 700;
            white-space: nowrap;
          }

          .nav-auth a,
          .nav-menu a {
            color: var(--ink);
            text-decoration: none;
          }

          .nav-auth a {
            padding: 9px 12px;
            border-radius: 8px;
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(226,232,240,0.90);
          }

          .nav-user {
            color: var(--muted);
          }

          .hero-main {
            position: relative;
            z-index: 2;
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            min-height: calc(100vh - 92px);
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 0;
          }

          .hero-content {
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            max-width: 620px;
            margin-top: -48px;
          }

          .eyebrow {
            margin-bottom: 14px;
            color: rgba(255,255,255,0.88);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
          }

          .headline {
            margin: 0;
            line-height: 1.05;
            font-weight: 800;
            letter-spacing: 0;
            color: var(--ink);
          }

          .headline .line1,
          .headline .line2 {
            display: block;
            font-size: clamp(2.45rem, 4.6vw, 4.15rem);
            word-break: keep-all;
          }

          .headline .line1 {
            color: #fff;
          }

          .headline .line2 {
            color: #fff;
            margin-top: 4px;
          }

          .hero-copy {
            max-width: 35rem;
            margin: 20px auto 0;
            color: rgba(255,255,255,0.86);
            font-size: 1.1rem;
            line-height: 1.65;
            word-break: keep-all;
          }

          .hero-badges {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 22px;
          }

          .hero-badge {
            padding: 8px 11px;
            border-radius: 999px;
            background: rgba(255,255,255,0.18);
            border: 1px solid rgba(255,255,255,0.34);
            color: #fff;
            font-size: 0.84rem;
            font-weight: 700;
          }

          .section-shell {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 42px auto 18px;
          }

          .section-kicker {
            margin-bottom: 8px;
            color: var(--teal);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
          }

          .section-title {
            margin: 0 0 10px;
            color: var(--ink);
            font-size: clamp(1.55rem, 2.4vw, 2.25rem);
            font-weight: 800;
            letter-spacing: 0;
          }

          .section-shell p {
            max-width: 760px;
            margin: 0;
            color: var(--muted);
            line-height: 1.7;
            word-break: keep-all;
          }

          .mini-card {
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 12px 28px rgba(15,23,42,0.06);
          }

          div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 8px !important;
            border: 1px solid rgba(226,232,240,0.95) !important;
            box-shadow: 0 14px 32px rgba(15,23,42,0.07) !important;
            background: #fff !important;
          }

          div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 14px 15px;
          }

          div[data-testid="stMetric"] label {
            color: var(--muted) !important;
            font-weight: 700 !important;
          }

          div[data-testid="stMetricValue"] {
            color: var(--ink);
            font-weight: 800;
          }

          .live-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 999px;
            background: #EFF6FF;
            color: var(--blue-dark);
            font-weight: 800;
            font-size: 0.78rem;
          }

          .weather-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 14px;
            margin-top: 12px;
          }

          .weather-card {
            min-height: 210px;
            padding: 16px;
            border: 1px solid var(--line);
            border-top: 3px solid #0ea5e9;
            border-radius: 16px;
            background: #fff;
            box-shadow: 0 16px 34px rgba(15,23,42,0.06);
          }

          .weather-card.error {
            border-top-color: #ef4444;
            background: #fffafa;
          }

          .weather-date {
            color: var(--gray-900);
            font-size: 0.98rem;
            font-weight: 700;
          }

          .weather-source {
            margin-top: 2px;
            color: var(--gray-500);
            font-size: 0.78rem;
          }

          .weather-condition {
            margin-top: 18px;
            color: var(--ink);
            font-size: 1.28rem;
            font-weight: 800;
          }

          .weather-temp {
            margin-top: 4px;
            color: #0369a1;
            font-size: 2rem;
            font-weight: 800;
          }

          .weather-stats {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 14px;
          }

          .weather-stat {
            padding: 8px 9px;
            border-radius: 10px;
            background: #f8fafc;
          }

          .weather-stat span {
            display: block;
            color: var(--gray-500);
            font-size: 0.72rem;
          }

          .weather-stat strong {
            display: block;
            margin-top: 2px;
            color: var(--gray-900);
            font-size: 0.92rem;
          }

          .weather-error-text {
            margin-top: 18px;
            color: #991b1b;
            font-weight: 700;
          }

          .image-empty {
            height: 168px;
            border: 1px dashed #CBD5E1;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--muted);
            background: #F8FAFC;
            font-size: 0.92rem;
            font-weight: 700;
          }

          [data-testid="stImage"] img {
            border-radius: 8px;
            aspect-ratio: 4 / 3;
            object-fit: cover;
          }

          .block-container [data-testid="stElementContainer"]:has([data-testid="stTabs"]) {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px))) !important;
            margin-left: auto !important;
            margin-right: auto !important;
          }

          [data-testid="stTabs"] {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 0 auto 38px;
            padding: 22px 24px 26px;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: #fff;
            box-shadow: 0 14px 34px rgba(15,23,42,0.06);
          }

          [data-testid="stTabs"] [role="tablist"] {
            justify-content: center;
            gap: 8px;
            border-bottom: 1px solid var(--line);
          }

          [data-testid="stTabs"] [role="tab"] {
            padding: 10px 14px;
            font-weight: 800;
          }

          [data-testid="stTabs"] [role="tabpanel"] {
            padding-top: 24px;
          }

          @media (max-width: 767px) {
            .hero-shell { height: 100vh; min-height: 650px; }
            .hero-nav { max-width: calc(100vw - 32px); gap: 12px; }
            .brand { font-size: 1.1rem; }
            .brand-mark { width: 28px; height: 28px; }
            .hero-main { max-width: calc(100vw - 32px); min-height: calc(100vh - 84px); padding: 0; }
            .headline .line1,
            .headline .line2 { font-size: 2.35rem; }
            .hero-copy { font-size: 1rem; }
            .nav-auth { gap: 12px; font-size: 0.86rem; }
            div[data-testid="stForm"],
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) {
              margin: 32px 16px 34px !important;
            }
            .region-picker { grid-template-columns: 1fr; }
            .region-major-panel { border-right: 0; border-bottom: 1px solid var(--gray-200); }
            .region-minor-panel { padding: 56px 18px 20px; }
            .region-minor-grid { grid-template-columns: 1fr 1fr; gap: 16px 18px; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("trip_result", None)


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

def render_login_dialog() -> None:
    st.write("여행지 검색과 여행 보조 정보는 로그인 후 이용할 수 있습니다.")
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
          <p>여행지 검색, 여행 보조 정보, 찜하기 기능은 로그인한 회원에게만 제공됩니다. 로그인과 회원가입은 화면 우측 상단에서 할 수 있습니다.</p>
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
          <video class="hero-photo" autoplay muted loop playsinline
            src="https://plugin-assets.open-design.ai/plugins/skyelite-private-jets/hf_20260328_091828_e240eb17-6edc-4129-ad9d-98678e3fd238-86655b.mp4">
          </video>
          <div class="hero-nav">
            <div class="nav-left">
              <div class="brand"><span class="brand-mark">T</span>TravelDB</div>
            </div>
            <div class="nav-auth">
              {auth_html}
            </div>
          </div>
          <div class="hero-main">
            <div class="hero-content">
              <p class="eyebrow">TRAVEL PLANNER</p>
              <h1 class="headline">
                <span class="line1">이번 여행,</span>
                <span class="line2">어디로 떠날까요?</span>
              </h1>
              <p class="hero-copy">
                지역과 날짜만 고르면 가볼 만한 곳, 날씨, 이동 비용, AI 추천 코스를 한 번에 정리해 드립니다.
              </p>
              <div class="hero-badges">
                <span class="hero-badge">관광지</span>
                <span class="hero-badge">식당</span>
                <span class="hero-badge">숙소</span>
                <span class="hero-badge">축제</span>
              </div>
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


REGION_SHORT_NAMES = {
    "전국": "전국",
    "서울": "서울",
    "부산": "부산",
    "대구": "대구",
    "인천": "인천",
    "광주": "광주",
    "대전": "대전",
    "울산": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


def region_short_name(region_name: str) -> str:
    return REGION_SHORT_NAMES.get(region_name, region_name)


def region_place_counts(hierarchy: dict[str, list[dict[str, str]]]) -> tuple[dict[str, int], dict[str, int]]:
    try:
        rows = db.fetch_all(
            """
            SELECT
              r.region_name,
              r.tour_area_code,
              r.tour_sigungu_code,
              COUNT(DISTINCT p.place_id)
                + COUNT(DISTINCT a.accommodation_id)
                + COUNT(DISTINCT rt.restaurant_id) AS place_count
            FROM regions r
            LEFT JOIN places p ON p.region_id = r.region_id
            LEFT JOIN accommodations a ON a.region_id = r.region_id
            LEFT JOIN restaurants rt ON rt.region_id = r.region_id
            GROUP BY r.region_id, r.region_name, r.tour_area_code, r.tour_sigungu_code
            """
        )
    except Error:
        return {}, {}

    minor_counts = {str(row.get("region_name") or ""): int(row.get("place_count") or 0) for row in rows}
    area_counts: dict[str, int] = {}
    for row in rows:
        area_code = str(row.get("tour_area_code") or "")
        if not area_code:
            continue
        area_counts[area_code] = area_counts.get(area_code, 0) + int(row.get("place_count") or 0)

    major_counts: dict[str, int] = {"전국": sum(minor_counts.values())}
    area_by_major = {
        str(row.get("region_name") or ""): str(row.get("tour_area_code") or "")
        for row in rows
        if str(row.get("tour_area_code") or "") and not str(row.get("tour_sigungu_code") or "")
    }
    for major in hierarchy:
        if major == "전국":
            continue
        area_code = area_by_major.get(major)
        if area_code:
            major_counts[major] = area_counts.get(area_code, 0)
        else:
            major_counts[major] = minor_counts.get(major, 0)
    return major_counts, minor_counts


def format_count(count: int | None) -> str:
    return f"({int(count or 0):,})"


def set_region_major(major_region: str, default_minor_value: str) -> None:
    st.session_state["region_major"] = major_region
    st.session_state[f"region_minor_value_{major_region}"] = default_minor_value


def set_region_minor(major_region: str, minor_value: str) -> None:
    st.session_state["region_major"] = major_region
    st.session_state[f"region_minor_value_{major_region}"] = minor_value


def sync_region_selection(hierarchy: dict[str, list[dict[str, str]]]) -> tuple[str, dict[str, str]]:
    major_options = list(hierarchy.keys())
    stored_major = st.session_state.get("region_major")
    major_region = stored_major if stored_major in hierarchy else major_options[0]

    minor_options = hierarchy.get(major_region) or [{"label": "전체", "value": major_region, "display": f"{major_region} 전체"}]
    stored_minor = st.session_state.get(f"region_minor_value_{major_region}")
    selected_region = next(
        (
            option
            for option in minor_options
            if option["value"] == stored_minor
        ),
        minor_options[0],
    )
    st.session_state["region_major"] = major_region
    st.session_state[f"region_minor_value_{major_region}"] = selected_region["value"]
    return major_region, selected_region


def render_region_picker(hierarchy: dict[str, list[dict[str, str]]]) -> tuple[str, dict[str, str]]:
    major_region, selected_region = sync_region_selection(hierarchy)
    minor_options = hierarchy.get(major_region) or [{"label": "전체", "value": major_region, "display": f"{major_region} 전체"}]
    major_counts, minor_counts = region_place_counts(hierarchy)

    left, right = st.columns([0.42, 1.0])
    with left:
        major_items = list(hierarchy.keys())
        for index in range(0, len(major_items), 2):
            cols = st.columns(2)
            for offset, col in enumerate(cols):
                item_index = index + offset
                if item_index >= len(major_items):
                    continue
                major = major_items[item_index]
                options = hierarchy.get(major) or [{"value": major}]
                default_minor = options[0].get("value") or major
                active = major == major_region
                label = f"{region_short_name(major)} {format_count(major_counts.get(major))}"
                if active:
                    label = f"{label} ›"
                col.button(
                    label,
                    key=f"region_major_btn_{major}",
                    type="secondary",
                    use_container_width=True,
                    on_click=set_region_major,
                    args=(major, default_minor),
                )

    with right:
        for index in range(0, len(minor_options), 3):
            cols = st.columns(3)
            for offset, col in enumerate(cols):
                item_index = index + offset
                if item_index >= len(minor_options):
                    continue
                option = minor_options[item_index]
                label = option["label"]
                if label == "전체":
                    label = f"{region_short_name(major_region)}전체"
                count_key = major_region if option["label"] == "전체" else option["value"]
                count = major_counts.get(major_region) if option["label"] == "전체" else minor_counts.get(count_key)
                active = option["value"] == selected_region["value"]
                prefix = "✓ " if active else "□ "
                col.button(
                    f"{prefix}{label} {format_count(count)}",
                    key=f"region_minor_btn_{major_region}_{option['value']}",
                    type="secondary",
                    use_container_width=True,
                    on_click=set_region_minor,
                    args=(major_region, option["value"]),
                )
    return major_region, selected_region


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

    with st.container(border=True):
        st.markdown('<span id="trip-search-panel"></span>', unsafe_allow_html=True)
        major_region, selected_region = render_region_picker(hierarchy)
        destination = selected_region["value"]
        destination_label = selected_region["display"]
        top = st.columns(2)
        start_date = top[0].date_input("출발일", value=default_start)
        end_date = top[1].date_input("돌아오는 날", value=default_end)
        bottom = st.columns([2.1, 0.72])
        categories = bottom[0].multiselect(
            "여행 카테고리",
            TRIP_CATEGORIES,
            default=[],
            help="원하는 여행 스타일을 골라주세요.",
        )
        submitted = bottom[1].button("검색", type="primary", use_container_width=True, key="trip_search_submit")

    if not submitted:
        return None

    if end_date < start_date:
        st.warning("돌아오는 날은 출발일 이후로 선택해주세요.")
        return None

    return {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "categories": categories,
        "region_major": major_region,
        "region_minor": selected_region["label"],
        "destination_label": destination_label,
        "duration_label": duration_from_dates(start_date, end_date),
    }


def trip_preferences(search: dict[str, Any]) -> dict[str, Any]:
    selected_categories = list(search.get("categories") or [])
    return {
        "travel_style": style_from_categories(selected_categories),
        "selected_categories": selected_categories,
        "selected_db_categories": category_db_names(selected_categories),
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
    rows = db.search_places_for_planner(search["destination"], db_categories, limit=0)
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

    preferences = trip_preferences(search)
    scored = recommender.score_places(rows, preferences, favorite_bias())
    try:
        favorite_place_ids = db.favorite_place_ids(st.session_state.user["member_id"])
    except Error:
        favorite_place_ids = set()
    restaurants = db.search_restaurants_for_region(search["destination"], limit=0)
    accommodations = db.search_accommodations_for_region(search["destination"], limit=0)
    festivals = db.search_festivals_for_region(search["destination"], limit=0)
    return {
        "search": search,
        "preferences": preferences,
        "places": scored,
        "course": [],
        "restaurants": restaurants,
        "accommodations": accommodations,
        "festivals": festivals,
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
    selected_categories = ", ".join(search.get("categories") or []) or "전체"
    cols = st.columns(3)
    cols[0].metric("여행지", search.get("destination_label") or search.get("destination") or "전국")
    cols[1].metric("일정", search["duration_label"])
    cols[2].metric("카테고리", selected_categories)


def render_score_reasons(target, row: dict[str, Any]) -> None:
    reasons = [str(reason).strip() for reason in row.get("score_reasons") or [] if str(reason).strip()]
    if not reasons:
        return
    with target.expander("점수 근거", expanded=False):
        for reason in reasons:
            st.write(f"- {reason}")


def pager_slice(items: list[dict[str, Any]], key: str, page_size: int = 12) -> list[dict[str, Any]]:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    current = int(st.session_state.get(key, 1) or 1)
    current = max(1, min(current, total_pages))
    st.session_state[key] = current

    start = (current - 1) * page_size
    return items[start : start + page_size]


def render_pager(items: list[dict[str, Any]], key: str, page_size: int = 12) -> None:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    current = int(st.session_state.get(key, 1) or 1)
    current = max(1, min(current, total_pages))
    st.session_state[key] = current

    st.markdown("")
    cols = st.columns([0.8, 1.4, 0.8, 4.0])
    if cols[0].button("이전", key=f"{key}_prev", disabled=current <= 1, use_container_width=True):
        st.session_state[key] = max(1, current - 1)
        st.rerun()
    cols[1].markdown(f"**{current} / {total_pages} 페이지** · 총 {total:,}개")
    if cols[2].button("다음", key=f"{key}_next", disabled=current >= total_pages, use_container_width=True):
        st.session_state[key] = min(total_pages, current + 1)
        st.rerun()


def _money(value: Any) -> str:
    try:
        return f"{int(value):,}원"
    except Exception:
        return "-"


WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def _coerce_date(value: Any, fallback: date) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return fallback
    return fallback


def trip_dates(start_value: Any, end_value: Any) -> list[date]:
    start = _coerce_date(start_value, date.today())
    end = _coerce_date(end_value, start)
    if end < start:
        end = start
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def weather_meta_key(destination: str, center: dict[str, Any], dates: list[date]) -> dict[str, str]:
    first = dates[0] if dates else date.today()
    last = dates[-1] if dates else first
    return {
        "destination": str(destination or "전국"),
        "center": str(center.get("region_name") or ""),
        "latitude": str(center.get("latitude") or ""),
        "longitude": str(center.get("longitude") or ""),
        "start": first.isoformat(),
        "end": last.isoformat(),
    }


def _weather_number(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "-"
    try:
        number = float(value)
        text = str(int(number)) if number.is_integer() else f"{number:.1f}"
    except Exception:
        text = str(value)
    return f"{text}{suffix}"


def _weather_day_label(target: date, first_day: date) -> str:
    index = (target - first_day).days + 1
    weekday = WEEKDAY_LABELS[target.weekday()]
    return f"{index}일차 · {target.month}.{target.day}({weekday})"


def weather_card_html(entry: dict[str, Any], first_day: date) -> str:
    target = _coerce_date(entry.get("target_date"), first_day)
    title = html.escape(_weather_day_label(target, first_day))
    subtitle = html.escape(target.isoformat())
    error = entry.get("error")
    if error:
        error_text = html.escape(str(error))
        return (
            '<div class="weather-card error">'
            f'<div class="weather-date">{title}</div>'
            f'<div class="weather-source">{subtitle}</div>'
            '<div class="weather-error-text">조회 실패</div>'
            f'<div class="weather-source">{error_text}</div>'
            "</div>"
        )

    weather = entry.get("weather") or {}
    condition = html.escape(str(weather.get("condition") or "정보 없음"))
    provider = html.escape(str(weather.get("provider") or weather.get("source") or "기상청"))
    temp = html.escape(_weather_number(weather.get("temp"), "℃"))
    min_temp = html.escape(_weather_number(weather.get("min_temp"), "℃"))
    max_temp = html.escape(_weather_number(weather.get("max_temp"), "℃"))
    rain = html.escape(_weather_number(weather.get("precip_probability"), "%"))
    return (
        '<div class="weather-card">'
        f'<div class="weather-date">{title}</div>'
        f'<div class="weather-source">{subtitle} · {provider}</div>'
        f'<div class="weather-condition">{condition}</div>'
        f'<div class="weather-temp">{temp}</div>'
        '<div class="weather-stats">'
        f'<div class="weather-stat"><span>최저 / 최고</span><strong>{min_temp} / {max_temp}</strong></div>'
        f'<div class="weather-stat"><span>강수확률</span><strong>{rain}</strong></div>'
        "</div>"
        "</div>"
    )


def render_weather_cards(entries: list[dict[str, Any]], first_day: date) -> None:
    cards = "".join(weather_card_html(entry, first_day) for entry in entries)
    st.markdown(f'<div class="weather-grid">{cards}</div>', unsafe_allow_html=True)
    notes = [
        str((entry.get("weather") or {}).get("note") or "")
        for entry in entries
        if (entry.get("weather") or {}).get("note")
    ]
    if notes:
        with st.expander("예보 기준 자세히 보기"):
            for note in dict.fromkeys(notes):
                st.caption(note)


def weather_center_for_region(destination: str) -> dict[str, Any] | None:
    try:
        center = db.region_center(destination)
    except Error:
        center = None
    if center and center.get("latitude") and center.get("longitude"):
        return center
    return None


def live_api_status_safe() -> dict[str, bool]:
    try:
        return external_services.live_api_status()
    except Exception:
        return {"kakao": False, "kma_short": False, "kma_mid": False, "openai": False}


def render_live_api_tabs(result: dict[str, Any]) -> None:
    search = result.get("search") or {}
    destination = str(search.get("destination") or "전국")
    destination_label = str(search.get("destination_label") or destination)
    start_date = search.get("start_date") or date.today()
    end_date = search.get("end_date") or start_date
    api_status = live_api_status_safe()
    kakao_context = "|".join(
        [
            destination_label,
            str(start_date),
            str(search.get("duration_label") or ""),
            ",".join(search.get("categories") or []),
        ]
    )
    if st.session_state.get("kakao_course_context") != kakao_context:
        st.session_state["kakao_course_context"] = kakao_context
        st.session_state.pop("kakao_live_rows", None)
        st.session_state.pop("kakao_openai_itinerary", None)
        st.session_state.pop("kakao_live_searched", None)

    section_header("MORE", "여행 보조 정보", "카카오맵 위치 정보를 바탕으로 AI 코스, 날씨, 이동 비용을 함께 확인할 수 있습니다.")
    tab_kakao, tab_weather, tab_transport = st.tabs([
        "카카오 MAP API & OPENAI API 추천코스",
        "날씨 API",
        "OPENAI API 비용산정",
    ])

    with tab_kakao:
        course_scope = f"{destination_label} 인기 관광지"
        if search.get("region_minor") == "전체" and destination_label != "전국":
            course_scope = f"{destination_label} 인기 관광지"
        default_keyword = f"{course_scope} {search.get('duration_label') or ''} 코스 추천".strip()
        keyword = st.text_input("AI 요청", value=default_keyword, key=f"kakao_live_keyword_{kakao_context}")
        if st.button("AI 추천코스 만들기", type="primary", key="kakao_live_search"):
            try:
                kakao_query = course_scope
                rows = external_services.search_kakao_places(kakao_query, region="" if destination == "전국" else destination, size=10)
                try:
                    db.save_kakao_places(destination, kakao_query, rows)
                except Error:
                    pass
                st.session_state["kakao_live_rows"] = rows
                itinerary = external_services.itinerary_from_kakao_with_gpt(
                    destination=destination_label,
                    travel_date=str(start_date),
                    duration=str(search.get("duration_label") or ""),
                    categories=list(search.get("categories") or []),
                    kakao_places=rows,
                )
                st.session_state["kakao_openai_itinerary"] = itinerary
                st.session_state["kakao_live_searched"] = True
            except Exception as exc:
                st.error(f"추천코스를 만들지 못했습니다: {exc}")

        rows = st.session_state.get("kakao_live_rows") or []
        itinerary = st.session_state.get("kakao_openai_itinerary")
        if not rows:
            if st.session_state.get("kakao_live_searched"):
                st.info("카카오맵에서 위치 정보를 찾지 못했습니다. 선택 지역을 조금 더 넓게 잡아보세요.")
            elif not api_status.get("kakao") or not api_status.get("openai"):
                st.info("카카오 REST API 키와 OPENAI_API_KEY를 설정하면 코스를 만들 수 있습니다.")
        if itinerary:
            st.subheader(itinerary.get("course_title") or "추천코스")
            st.write(itinerary.get("summary") or "")
            for day in itinerary.get("days") or []:
                st.markdown(f"### Day {day.get('day')} · {day.get('theme') or '일정'}")
                for stop in day.get("stops") or []:
                    with st.container(border=True):
                        cols = st.columns([0.65, 2.6, 0.9])
                        cols[0].metric("순서", stop.get("order") or "-")
                        cols[0].caption(stop.get("time") or "")
                        name = stop.get("place_name") or "장소"
                        url = stop.get("kakao_url") or naver_map_url(name, stop.get("address"))
                        cols[1].markdown(f"### [{name}]({url})")
                        cols[1].caption(stop.get("address") or "주소 정보 없음")
                        cols[1].write(stop.get("reason") or "")
                        if stop.get("move_tip"):
                            cols[1].caption(f"이동: {stop.get('move_tip')}")
                        cols[2].link_button("카카오맵", url, use_container_width=True)
            notes = [str(note).strip() for note in itinerary.get("notes") or [] if str(note).strip()]
            if notes:
                with st.expander("여행 팁", expanded=False):
                    for note in notes:
                        st.write(f"- {note}")
        elif rows:
            with st.expander("AI가 참고한 카카오맵 위치 정보", expanded=False):
                for row in rows[:10]:
                    with st.container(border=True):
                        cols = st.columns([2.4, 0.8])
                        name = row.get("place_name") or "이름 없음"
                        url = row.get("place_url") or naver_map_url(name, row.get("road_address_name") or row.get("address_name"))
                        cols[0].markdown(f"### [{name}]({url})")
                        cols[0].caption(row.get("category_name") or "장소")
                        cols[0].write(row.get("road_address_name") or row.get("address_name") or "주소 정보 없음")
                        cols[1].link_button("카카오맵", url, use_container_width=True)

    with tab_weather:
        center = weather_center_for_region(destination)
        if not center:
            st.info("날씨를 확인할 좌표가 아직 없습니다.")
        else:
            weather_days = trip_dates(start_date, end_date)
            first_day = weather_days[0]
            last_day = weather_days[-1]
            meta = weather_meta_key(destination, center, weather_days)
            st.caption(
                f"조회 기준: {center.get('region_name') or destination_label} · "
                f"{center.get('latitude')} / {center.get('longitude')} · "
                f"{first_day.isoformat()} ~ {last_day.isoformat()} ({len(weather_days)}일)"
            )
            if len(weather_days) > 10:
                st.caption("기상청 예보 제공 범위를 벗어난 날짜는 카드에 조회 실패 사유로 표시됩니다.")
            if st.button(f"전체 일정 날씨 조회 ({len(weather_days)}일)", type="primary", key="weather_live_search"):
                weather_entries: list[dict[str, Any]] = []
                with st.spinner("날짜별 날씨를 불러오는 중입니다..."):
                    for target_day in weather_days:
                        try:
                            weather = external_services.weather_for_date(
                                float(center["latitude"]),
                                float(center["longitude"]),
                                target_day,
                                region_name=str(center.get("region_name") or destination_label),
                            )
                            try:
                                db.save_weather_snapshot(
                                    str(center.get("region_name") or destination_label),
                                    target_day,
                                    center.get("latitude"),
                                    center.get("longitude"),
                                    weather,
                                )
                            except Error:
                                pass
                            weather_entries.append({"target_date": target_day.isoformat(), "weather": weather})
                        except Exception as exc:
                            weather_entries.append({"target_date": target_day.isoformat(), "error": str(exc)})
                st.session_state["weather_live_results"] = {"meta": meta, "items": weather_entries}

            weather_state = st.session_state.get("weather_live_results")
            weather_entries = []
            if isinstance(weather_state, dict) and weather_state.get("meta") == meta:
                weather_entries = list(weather_state.get("items") or [])

            if weather_entries:
                render_weather_cards(weather_entries, first_day)
            elif api_status.get("kma_short") or api_status.get("kma_mid"):
                st.info("기상청 키가 감지됐습니다. 버튼을 누르면 전체 일정의 날짜별 예보를 확인합니다.")
            else:
                st.info("기상청 키를 설정하면 전체 일정의 날짜별 날씨를 볼 수 있습니다.")

    with tab_transport:
        cols = st.columns([1, 1, 0.55])
        origin = cols[0].text_input("출발지", value="서울", key="transport_origin")
        destination_text = cols[1].text_input("도착지", value=destination if destination != "전국" else "", key="transport_destination")
        people = cols[2].number_input("인원", min_value=1, max_value=10, value=2, step=1, key="transport_people")
        if st.button("교통비 보기", type="primary", key="transport_live_search"):
            try:
                estimate = external_services.transport_estimate_with_gpt(origin, destination_text, str(start_date), int(people))
                try:
                    db.save_transport_estimate(origin, destination_text, start_date, int(people), estimate)
                except Error:
                    pass
                st.session_state["transport_estimate"] = estimate
            except Exception as exc:
                st.error(f"교통비를 계산하지 못했습니다: {exc}")

        estimate = st.session_state.get("transport_estimate")
        if estimate:
            for option in estimate.get("options") or []:
                with st.container(border=True):
                    cols = st.columns([1.0, 1.35, 2.1])

                    cols[0].subheader(option.get("mode") or "교통편")

                    cols[1].markdown(
                        f"""
                        <div style="
                            border: 1px solid #e5e7eb;
                            border-radius: 12px;
                            padding: 14px 18px;
                            margin-bottom: 14px;
                            background: #ffffff;
                        ">
                            <div style="font-size:14px; color:#64748b; font-weight:600;">예상 시간</div>
                            <div style="font-size:34px; color:#64748b; font-weight:800;">
                                {option.get('estimated_time_minutes', '-')}분
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    cols[1].markdown(
                        f"""
                        <div style="
                            border: 1px solid #e5e7eb;
                            border-radius: 12px;
                            padding: 14px 18px;
                            background: #ffffff;
                        ">
                            <div style="font-size:14px; color:#64748b; font-weight:600;">예상 금액</div>
                            <div style="
                                font-size:27px;
                                color:#64748b;
                                font-weight:800;
                                white-space: normal;
                                word-break: keep-all;
                                line-height: 1.25;
                            ">
                                {_money(option.get('estimated_cost_min'))} ~ {_money(option.get('estimated_cost_max'))}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    cols[2].write(option.get("route_summary") or "-")
        elif not api_status.get("openai"):
            st.info("비용 계산 키를 설정하면 교통편별 예상 금액을 볼 수 있습니다.")

def render_place_card(row: dict[str, Any], key_prefix: str, favorite_ids: set[int] | None = None) -> None:
    favorite_ids = favorite_ids or set()
    with st.container(border=True):
        top = st.columns([1, 2.4, 0.9])
        render_card_image(top[0], row, "관광지 사진 없음")
        name = row.get("place_name") or "이름 없음"
        map_url = naver_map_url(name, row.get("address"))
        top[1].markdown(f"### [{name}]({map_url})")
        top[1].caption(row.get("region_name") or "-")
        top[1].write(row.get("overview") or "소개 정보가 없습니다.")
        render_favorite_heart(top[2], row, favorite_ids, key_prefix)
        top[2].metric("추천 점수", f"{recommender.safe_float(row.get('recommendation_score')):.1f}")
        render_score_reasons(top[2], row)
        top[2].link_button("네이버 지도", map_url, use_container_width=True)

        if row.get("categories"):
            st.caption(f"분류: {row.get('categories')}")

def render_recommendations(result: dict[str, Any]) -> None:
    places = result["places"]
    if not places:
        st.info("추천할 관광지가 없습니다.")
        return
    favorite_ids = set(result.get("favorite_place_ids") or refresh_favorite_ids())
    for row in pager_slice(places, "places_page", page_size=12):
        render_place_card(row, "place_fav", favorite_ids)
    render_pager(places, "places_page", page_size=12)


def render_accommodations(result: dict[str, Any]) -> None:
    accommodations = result["accommodations"]
    if not accommodations:
        st.info("해당 지역에는 아직 준비된 숙소가 없습니다.")
        return
    for item in pager_slice(accommodations, "accommodations_page", page_size=12):
        with st.container(border=True):
            cols = st.columns([1, 2.4, 0.9])
            render_card_image(cols[0], item, "숙소 사진 없음")
            name = item.get("accommodation_name") or "이름 없음"
            map_url = naver_map_url(name, item.get("address"))
            cols[1].markdown(f"### [{name}]({map_url})")
            cols[1].caption(f"{item.get('region_name') or '-'} · {item.get('address') or '주소 정보 없음'}")
            cols[2].link_button("네이버 지도", map_url, use_container_width=True)
    render_pager(accommodations, "accommodations_page", page_size=12)


def render_restaurants(result: dict[str, Any]) -> None:
    restaurants = result["restaurants"]
    if not restaurants:
        st.info("해당 지역에는 아직 준비된 식당이 없습니다.")
        return
    for item in pager_slice(restaurants, "restaurants_page", page_size=12):
        with st.container(border=True):
            cols = st.columns([1, 2.4, 0.9])
            render_card_image(cols[0], item, "식당 사진 없음")
            name = item.get("restaurant_name") or "이름 없음"
            map_url = naver_map_url(name, item.get("address"))
            cols[1].markdown(f"### [{name}]({map_url})")
            cols[1].caption(f"{item.get('region_name') or '-'} · {item.get('address') or '주소 정보 없음'}")
            cols[2].link_button("네이버 지도", map_url, use_container_width=True)
    render_pager(restaurants, "restaurants_page", page_size=12)


def render_festivals(result: dict[str, Any]) -> None:
    festivals = result.get("festivals") or []
    if not festivals:
        st.info("해당 지역에는 아직 준비된 축제가 없습니다.")
        return
    for item in pager_slice(festivals, "festivals_page", page_size=12):
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
    render_pager(festivals, "festivals_page", page_size=12)


def render_result_tabs(result: dict[str, Any]) -> None:
    section_header("RESULTS", "검색 결과", "선택한 지역의 관광지, 식당, 숙소, 축제를 탭으로 나눠 확인할 수 있습니다.")
    tab_places, tab_restaurants, tab_accommodations, tab_festivals = st.tabs([
        f"관광지 {len(result.get('places') or []):,}",
        f"식당 {len(result.get('restaurants') or []):,}",
        f"숙소 {len(result.get('accommodations') or []):,}",
        f"축제 {len(result.get('festivals') or []):,}",
    ])
    with tab_places:
        render_recommendations(result)
    with tab_restaurants:
        render_restaurants(result)
    with tab_accommodations:
        render_accommodations(result)
    with tab_festivals:
        render_festivals(result)


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
            st.error(f"추천 결과를 불러오지 못했습니다: {exc}")
            st.session_state.trip_result = None

    result = st.session_state.trip_result
    if result:
        render_summary(result)
        render_live_api_tabs(result)
        render_result_tabs(result)
    else:
        section_header(
            "ONE SEARCH",
            "검색 한 번으로 코스, 숙소, 식당까지",
            "지역과 날짜, 카테고리를 고르면 여러 탭을 오가지 않고 한 화면에서 추천 결과를 확인합니다.",
        )
        cols = st.columns(3)
        samples = [
            ("1", "카테고리 선택", "관광지, 미식, 카페, 자연처럼 여행 목적을 먼저 고릅니다."),
            ("2", "지역 맞춤 결과", "선택한 지역의 관광지, 숙소, 식당을 한 화면에 모아봅니다."),
            ("3", "코스 통합 출력", "방문지, 숙소, 식당을 일정 흐름에 맞춰 확인합니다."),
        ]
        for col, (num, title, body) in zip(cols, samples):
            with col:
                with st.container(border=True):
                    st.caption(num)
                    st.subheader(title)
                    st.write(body)

def main() -> None:
    inject_design()
    init_state()
    ok, message = db.test_connection()
    if not ok:
        render_hero()
        st.error("서비스 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요.")
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
