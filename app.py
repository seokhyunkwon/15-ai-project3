from __future__ import annotations

import importlib
import html
import os
import sys
from datetime import date, timedelta
from urllib.parse import quote

import pandas as pd
import streamlit as st
from mysql.connector import Error

import collector
import course_generator
import database as db
import recommender

db = importlib.reload(db)


st.set_page_config(
    page_title="여행 코스 추천 시스템",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


MENU_ITEMS = ["홈", "대시보드", "데이터 수집", "여행지 탐색", "여행 코스 만들기", "내 활동", "관리자 SQL"]


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

          .block-container > div {
            width: 100%;
          }

          .block-container > div:first-child,
          .block-container [data-testid="stVerticalBlock"] > div:first-child,
          .block-container [data-testid="stElementContainer"]:has(style) {
            margin-top: 0 !important;
            padding-top: 0 !important;
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

          section[data-testid="stSidebar"] {
            background: rgba(255,255,255,0.86);
            border-right: 1px solid var(--gray-200);
          }

          section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--gray-700);
          }

          div[data-testid="stMetric"] {
            background: #fff;
            border: 1px solid var(--gray-200);
            border-radius: 12px;
            padding: 18px 18px 16px;
            box-shadow: 0 16px 38px rgba(17,24,39,0.05);
          }

          div[data-testid="stMetricLabel"] p {
            color: var(--gray-500);
            font-weight: 600;
          }

          div[data-testid="stMetricValue"] {
            color: var(--ink);
            font-weight: 600;
          }

          .stButton > button,
          .stDownloadButton > button {
            border-radius: 9999px;
            min-height: 40px;
            padding: 8px 18px;
            border: 1px solid var(--gray-300);
            background: #fff;
            color: var(--gray-800);
            font-weight: 500;
            transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
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

          .stButton > button[kind="primary"]:hover {
            background: var(--ink-hover);
            border-color: var(--ink-hover);
            color: #fff;
          }

          div[data-testid="stForm"],
          div[data-testid="stExpander"],
          div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px;
            border-color: var(--gray-200);
            box-shadow: 0 16px 38px rgba(17,24,39,0.04);
          }

          div[data-testid="stForm"] {
            max-width: min(92vw, 1180px);
            margin: -116px auto 44px !important;
            padding: 26px 28px 30px !important;
            border: 1px solid rgba(209,213,219,0.86) !important;
            border-radius: 14px !important;
            background: rgba(255,255,255,0.94) !important;
            box-shadow: 0 22px 44px rgba(17,24,39,0.16) !important;
            position: relative;
            z-index: 4;
          }

          div[data-testid="stForm"] label {
            color: var(--gray-700) !important;
            font-weight: 600 !important;
          }

          .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
          }

          .stTabs [data-baseweb="tab"] {
            border-radius: 9999px;
            padding: 8px 16px;
            background: #fff;
            border: 1px solid var(--gray-200);
            color: var(--gray-600);
          }

          .stTabs [aria-selected="true"] {
            color: #fff;
            background: var(--ink);
          }

          .hero-shell {
            position: relative;
            left: 50%;
            transform: translateX(-50%);
            width: 100vw;
            height: calc(100vh + 24px);
            min-height: 680px;
            overflow: hidden;
            border-radius: 0;
            margin: -24px 0 36px;
            background:
              linear-gradient(rgba(249,250,251,0.10), rgba(249,250,251,0.18)),
              #f9fafb;
            background-size: cover;
            background-position: center;
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
            background: linear-gradient(rgba(249,250,251,0.18), rgba(249,250,251,0.28));
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
          }

          .nav-left {
            display: flex;
            align-items: center;
            min-width: 0;
          }

          .brand {
            font-size: 1.45rem;
            font-weight: 600;
            color: var(--gray-900);
            text-decoration: none;
          }

          .nav-menu {
            display: flex;
            margin-left: 48px;
            gap: 34px;
            color: var(--gray-900);
            font-size: 0.96rem;
            font-weight: 500;
          }

          .nav-auth {
            display: flex;
            align-items: center;
            gap: 20px;
            color: var(--gray-900);
            font-size: 0.95rem;
            font-weight: 500;
            white-space: nowrap;
          }

          .nav-menu a,
          .nav-auth a {
            color: var(--gray-900);
            text-decoration: none;
          }

          .nav-menu a:hover,
          .nav-auth a:hover,
          .brand:hover {
            color: var(--ink);
          }

          .nav-user {
            color: var(--gray-600);
          }

          .site-nav {
            max-width: calc(100vw - clamp(32px, 6vw, 96px));
            margin: 26px auto 28px;
            padding: 16px 20px;
            border: 1px solid var(--gray-200);
            border-radius: 16px;
            background: rgba(255,255,255,0.9);
            box-shadow: 0 16px 38px rgba(17,24,39,0.04);
            display: flex;
            align-items: center;
            justify-content: space-between;
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
            margin-top: -260px;
            padding: 0 24px;
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
            font-weight: 400;
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
            font-size: 1.125rem;
            line-height: 1.65;
            word-break: keep-all;
          }

          .cta-row {
            display: flex;
            gap: 14px;
            justify-content: center;
            flex-wrap: wrap;
          }

          .pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 40px;
            padding: 8px 18px;
            border-radius: 9999px;
            font-weight: 500;
          }

          .pill-soft {
            background: var(--gray-300);
            color: var(--gray-800);
          }

          .pill-ink {
            background: var(--ink);
            color: #fff;
          }

          .page-heading {
            max-width: calc(100vw - clamp(32px, 6vw, 96px));
            margin: 8px auto 26px;
          }

          .page-heading .kicker {
            margin-bottom: 8px;
            color: var(--gray-500);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
          }

          .page-heading h1 {
            margin: 0;
            color: var(--ink);
            font-size: clamp(2rem, 4vw, 3.25rem);
            font-weight: 500;
            line-height: 1.06;
          }

          .page-heading p {
            max-width: 48rem;
            margin-top: 12px;
            font-size: 1.02rem;
            line-height: 1.65;
          }

          .mini-card {
            background: #fff;
            border: 1px solid var(--gray-200);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 16px 38px rgba(17,24,39,0.04);
          }

          @media (max-width: 767px) {
            .hero-shell {
              min-height: 620px;
            }
            .hero-nav {
              padding: 20px 22px;
            }
            .nav-menu {
              display: none;
            }
            .nav-auth {
              gap: 14px;
              font-size: 0.88rem;
            }
            div[data-testid="stForm"] {
              margin: -80px 16px 34px !important;
              padding: 20px !important;
            }
            .hero-main {
              min-height: calc(100vh - 84px);
            }
            .hero-content { margin-top: -180px; }
            .hero-copy {
              max-width: 22rem;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def nav_href(menu: str | None = None, auth: str | None = None, logout: bool = False, anchor: str | None = None) -> str:
    params: list[str] = []
    if logout:
        params.append("logout=1")
    else:
        user = st.session_state.get("user")
        if user:
            params.append(f"login_user={quote(str(user['username']))}")
        if menu:
            params.append(f"menu={quote(menu)}")
        if auth:
            params.append(f"auth={quote(auth)}")
    href = "?" + "&".join(params) if params else "?"
    if anchor:
        href += f"#{quote(anchor)}"
    return href


def render_nav_html(current_menu: str = "홈", hero: bool = False) -> str:
    user = st.session_state.get("user")
    nav_class = "hero-nav" if hero else "site-nav"
    nav_links = [
        ("데이터", "데이터 수집"),
        ("추천", "여행지 탐색"),
        ("코스", "여행 코스 만들기"),
        ("문의", "내 활동"),
    ]
    link_html = []
    for label, menu in nav_links:
        href = nav_href(menu=menu) if user else nav_href(auth="login", anchor="account-panel")
        link_html.append(f'<a href="{href}">{html.escape(label)}</a>')

    if user:
        auth_html = (
            f'<span class="nav-user">{html.escape(str(user["name"]))}님</span>'
            f'<a href="{nav_href(logout=True)}">로그아웃</a>'
        )
    else:
        auth_html = (
            f'<a href="{nav_href(auth="login", anchor="account-panel")}">로그인</a>'
            f'<a href="{nav_href(auth="signup", anchor="account-panel")}">회원가입</a>'
        )

    return f"""
      <div class="{nav_class}">
        <div class="nav-left">
          <a class="brand" href="{nav_href(menu='홈') if user else '?'}">TravelDB</a>
          <div class="nav-menu">
            {''.join(link_html)}
          </div>
        </div>
        <div class="nav-auth">
          {auth_html}
        </div>
      </div>
    """


def render_site_nav(current_menu: str) -> None:
    st.markdown(render_nav_html(current_menu=current_menu, hero=False), unsafe_allow_html=True)


def render_hero() -> None:
    nav = render_nav_html(current_menu="홈", hero=True)
    st.markdown(
        f"""
        <section class="hero-shell">
          <video class="hero-video" autoplay muted loop playsinline
            src="https://plugin-assets.open-design.ai/plugins/skyelite-private-jets/hf_20260328_091828_e240eb17-6edc-4129-ad9d-98678e3fd238-86655b.mp4">
          </video>
          {nav}
          <div class="hero-main">
            <div class="hero-content">
              <p class="eyebrow">공공 관광 데이터</p>
              <h1 class="headline">
                <span class="line1">Curated.</span>
                <span class="line2">Accessible.</span>
              </h1>
              <p class="hero-copy">
                지역, 관광지, 축제, 리뷰와 여행 코스를 하나의 관계형 데이터베이스로 연결하는 맞춤 여행 플래너.
              </p>
              <div class="cta-row">
                <span class="pill pill-soft">여행지 탐색</span>
                <span class="pill pill-ink">코스 만들기</span>
              </div>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_account_panel(mode: str | None) -> None:
    if mode not in {"login", "signup"}:
        return

    st.markdown('<div id="account-panel"></div>', unsafe_allow_html=True)
    title = "로그인" if mode == "login" else "회원가입"
    body = "데모 계정으로 바로 들어가거나, 새 계정을 만들어 여행 취향을 저장할 수 있습니다."
    render_page_heading("ACCOUNT", title, body)

    with st.container(border=True):
        if mode == "login":
            cols = st.columns([1, 1, 0.8])
            username = cols[0].text_input("아이디", value="demo", key="login_username")
            password = cols[1].text_input("비밀번호", value="demo1234", type="password", key="login_password")
            cols[2].write("")
            cols[2].write("")
            if cols[2].button("로그인", type="primary", use_container_width=True, key="login_submit"):
                user = db.authenticate(username, password)
                if user:
                    persist_login(user)
                    st.rerun()
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        else:
            options = region_options()
            cols = st.columns(2)
            new_username = cols[0].text_input("아이디", key="signup_username")
            name = cols[1].text_input("이름", key="signup_name")
            email = cols[0].text_input("이메일", key="signup_email")
            new_password = cols[1].text_input("비밀번호", type="password", key="signup_password")
            selected_region = st.selectbox("관심 지역", list(options.keys()), key="signup_region")
            if st.button("회원가입", type="primary", use_container_width=True, key="signup_submit"):
                if not all([new_username, name, email, new_password]):
                    st.warning("모든 항목을 입력해주세요.")
                    return
                try:
                    db.create_member(new_username, new_password, name, email, options[selected_region])
                    st.success("회원가입이 완료되었습니다. 오른쪽 상단 로그인 메뉴로 로그인해주세요.")
                except Error as exc:
                    st.error(f"회원가입 실패: {exc}")


def render_trip_search() -> None:
    region_map = region_options()
    default_start = date.today() + timedelta(days=11)
    default_end = default_start + timedelta(days=1)

    with st.form("trip_search_form"):
        destination = st.selectbox("어디로 떠나시나요?", list(region_map.keys()), index=0)
        date_cols = st.columns(2)
        start_date = date_cols[0].date_input("체크인", value=default_start)
        end_date = date_cols[1].date_input("체크아웃", value=default_end)

        guest_cols = st.columns(3)
        adults = guest_cols[0].number_input("성인", min_value=1, max_value=10, value=2, step=1)
        nights = max((end_date - start_date).days, 1)
        guest_cols[1].number_input("객실", min_value=1, max_value=5, value=1, step=1)
        guest_cols[2].text_input("여행 기간", value=f"{nights}박 {nights + 1}일", disabled=True)

        submitted = st.form_submit_button("검색하기", type="primary", use_container_width=True)

    if submitted:
        st.session_state.trip_search = {
            "region_label": destination,
            "region_id": region_map[destination],
            "start_date": start_date,
            "end_date": end_date,
            "adults": adults,
            "nights": nights,
        }
        st.success(f"{destination.split(' ')[0]} 여행지를 {nights}박 {nights + 1}일 일정으로 찾아볼게요.")


def render_page_heading(kicker: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="page-heading">
          <div class="kicker">{kicker}</div>
          <h1>{title}</h1>
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    st.session_state.setdefault("user", None)


def query_param_value(name: str) -> str | None:
    try:
        value = st.query_params.get(name)
    except Exception:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


def persist_login(user: dict[str, object]) -> None:
    st.session_state.user = user
    st.session_state.active_menu = "홈"
    try:
        st.query_params.clear()
        st.query_params["login_user"] = str(user["username"])
        st.query_params["menu"] = "홈"
    except Exception:
        pass


def restore_login_from_query() -> None:
    if st.session_state.get("user"):
        return
    username = query_param_value("login_user")
    if not username:
        return
    try:
        user = db.get_member_by_username(username)
    except Error:
        return
    if user:
        st.session_state.user = user


def clear_login() -> None:
    st.session_state.user = None
    st.session_state.active_menu = "홈"
    try:
        st.query_params.clear()
    except Exception:
        try:
            del st.query_params["login_user"]
            del st.query_params["menu"]
        except Exception:
            pass


def go_to_menu(menu: str) -> None:
    st.session_state.active_menu = menu
    try:
        st.query_params.clear()
        user = st.session_state.get("user")
        if user:
            st.query_params["login_user"] = str(user["username"])
        st.query_params["menu"] = menu
    except Exception:
        pass
    st.rerun()


def region_options() -> dict[str, int]:
    regions = db.get_regions()
    return {f"{row['region_name']} ({row['province']})": row["region_id"] for row in regions}


def category_options() -> dict[str, int]:
    categories = db.get_categories()
    return {row["category_name"]: row["category_id"] for row in categories}


def configured_tourapi_key() -> str | None:
    for name in ("TOUR_API_SERVICE_KEY", "TOURAPI_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY"):
        value = os.getenv(name)
        if value:
            return value.strip()
    try:
        for name in ("TOUR_API_SERVICE_KEY", "TOURAPI_SERVICE_KEY", "DATA_GO_KR_SERVICE_KEY"):
            value = st.secrets.get(name)
            if value:
                return str(value).strip()
    except Exception:
        return None
    return None


def render_preference_controls(key_prefix: str, default_duration: str = "당일치기") -> dict[str, str]:
    cols = st.columns(3)
    travel_style = cols[0].selectbox("여행 스타일", recommender.TRAVEL_STYLES, key=f"{key_prefix}_style")
    companion = cols[1].selectbox("동행 유형", recommender.COMPANION_TYPES, key=f"{key_prefix}_companion")
    budget = cols[2].selectbox("예산", recommender.BUDGET_LEVELS, index=1, key=f"{key_prefix}_budget")

    cols = st.columns(3)
    transport = cols[0].selectbox("이동수단", recommender.TRANSPORT_TYPES, index=1, key=f"{key_prefix}_transport")
    weather = cols[1].selectbox("날씨", recommender.WEATHER_TYPES, key=f"{key_prefix}_weather")
    duration_index = recommender.DURATION_TYPES.index(default_duration) if default_duration in recommender.DURATION_TYPES else 1
    duration = cols[2].selectbox("여행 시간", recommender.DURATION_TYPES, index=duration_index, key=f"{key_prefix}_duration")

    return {
        "travel_style": travel_style,
        "companion": companion,
        "budget": budget,
        "transport": transport,
        "weather": weather,
        "duration": duration,
    }


def favorite_bias_for_user() -> dict[str, int]:
    user = st.session_state.get("user")
    if not user:
        return {}
    try:
        return db.favorite_category_counts(user["member_id"])
    except Error:
        return {}


def render_place_detail(row: dict[str, object]) -> None:
    with st.expander("상세 정보"):
        image_url = row.get("image_url")
        if image_url:
            st.image(str(image_url), caption="대표사진", use_container_width=True)
        left, right = st.columns(2)
        left.write(f"**주소**: {row.get('address') or '주소 정보 없음'}")
        left.write(f"**카테고리**: {row.get('categories') or '-'}")
        left.write(f"**전화번호**: {row.get('phone') or '정보 없음'}")
        left.write(f"**운영시간**: {row.get('opening_hours') or '정보 없음'}")
        right.write(f"**리뷰 수**: {row.get('review_count') or 0}")
        right.write(f"**추천 대상**: {row.get('recommended_for') or '정보 없음'}")
        right.write(f"**실내/야외**: {row.get('indoor_outdoor') or '정보 없음'}")
        right.write(f"**위치**: {row.get('latitude') or '위도 없음'}, {row.get('longitude') or '경도 없음'}")
        st.caption(f"태그: {row.get('display_tags') or row.get('tags') or '-'}")
        st.write(row.get("overview") or "소개 정보가 없습니다.")


def render_recommendation_map(rows: list[dict[str, object]]) -> None:
    map_rows = []
    for row in rows:
        lat = recommender.safe_float(row.get("latitude"), default=None)
        lon = recommender.safe_float(row.get("longitude"), default=None)
        if lat is None or lon is None:
            continue
        map_rows.append({"lat": lat, "lon": lon, "name": row.get("place_name")})
    if not map_rows:
        st.info("위치 정보가 있는 추천 장소가 아직 없습니다.")
        return
    st.map(pd.DataFrame(map_rows), latitude="lat", longitude="lon", size=80)


def render_db_warning(message: str) -> None:
    render_hero()
    if "auth_gssapi_client" in message:
        render_page_heading(
            "DATABASE",
            "MariaDB 계정 인증 방식을 바꿔주세요",
            "`travel_app` 계정이 Windows/GSSAPI 인증으로 잡혀 있어 Python 앱이 접속하지 못하는 상태입니다.",
        )
        st.error("HeidiSQL에서 `heidisql_user.sql`을 실행해 `travel_app` 계정을 비밀번호 인증으로 다시 만들어주세요.")
    elif "Access denied" in message:
        render_page_heading(
            "DATABASE",
            "DB 계정 또는 비밀번호를 확인해주세요",
            "환경 변수의 사용자명/비밀번호와 MariaDB 계정 정보가 일치해야 합니다.",
        )
        st.error("DB 로그인에 실패했습니다. `TRAVEL_DB_USER`, `TRAVEL_DB_PASSWORD` 값을 확인해주세요.")
    else:
        render_page_heading(
            "DATABASE",
            "HeidiSQL에서 스키마를 먼저 실행해주세요",
            "앱은 MySQL/MariaDB 데이터베이스를 직접 읽고 씁니다. DB 세팅이 끝나면 같은 주소에서 로그인 화면으로 전환됩니다.",
        )
        st.error("DB 연결에 실패했습니다. HeidiSQL에서 `schema.sql`을 먼저 실행하고 접속 정보를 확인해주세요.")
    st.code(message)
    safe_config = db.db_config().copy()
    safe_config["password"] = "********"
    st.code(
        "\n".join(
            [
                f"Python: {sys.executable}",
                f"database.py: {db.__file__}",
                f"DB config: {safe_config}",
            ]
        )
    )
    st.info(
        "환경 변수: TRAVEL_DB_HOST, TRAVEL_DB_PORT, TRAVEL_DB_USER, "
        "TRAVEL_DB_PASSWORD, TRAVEL_DB_NAME, TRAVEL_DB_AUTH_PLUGIN"
    )


def render_auth() -> None:
    render_hero()
    render_account_panel(query_param_value("auth"))
    render_trip_search()


def render_home() -> None:
    render_hero()
    render_trip_search()
    render_page_heading(
        "START HERE",
        "추가된 기능은 아래 메뉴에서 바로 사용할 수 있습니다",
        "로그인 후에도 메인 화면을 유지하고, 맞춤 추천·TourAPI 수집·자동 코스 생성으로 바로 이동할 수 있게 정리했습니다.",
    )

    cards = [
        (
            "데이터 수집",
            "한국관광공사 API 키로 관광지, 문화시설, 음식점 데이터를 DB에 저장합니다.",
            "TourAPI 수집하러 가기",
            "데이터 수집",
        ),
        (
            "여행지 탐색",
            "여행 스타일, 날씨, 예산, 동행 유형을 넣으면 추천 점수와 이유를 보여줍니다.",
            "맞춤 추천 보기",
            "여행지 탐색",
        ),
        (
            "여행 코스 만들기",
            "추천 점수가 높은 장소로 반나절, 당일치기, 1박 2일 코스를 자동 생성합니다.",
            "자동 코스 만들기",
            "여행 코스 만들기",
        ),
    ]
    cols = st.columns(3)
    for col, (title, body, button_label, target_menu) in zip(cols, cards):
        with col:
            with st.container(border=True):
                st.subheader(title)
                st.write(body)
                if st.button(button_label, use_container_width=True, key=f"home_go_{target_menu}"):
                    go_to_menu(target_menu)

    more_cols = st.columns(3)
    with more_cols[0]:
        with st.container(border=True):
            st.subheader("내 활동")
            st.write("찜한 장소와 찜 카테고리 성향을 확인합니다.")
            if st.button("찜 목록 보기", use_container_width=True, key="home_go_activity"):
                go_to_menu("내 활동")
    with more_cols[1]:
        with st.container(border=True):
            st.subheader("관리자 SQL")
            st.write("추천용 컬럼 추가 SQL과 중복 정리 SQL을 확인합니다.")
            if st.button("DB 보강 SQL 보기", use_container_width=True, key="home_go_admin"):
                go_to_menu("관리자 SQL")
    with more_cols[2]:
        with st.container(border=True):
            st.subheader("대시보드")
            st.write("수집된 지역, 관광지, 축제, 찜, 리뷰 수를 요약합니다.")
            if st.button("집계 보기", use_container_width=True, key="home_go_dashboard"):
                go_to_menu("대시보드")


def render_sidebar() -> str:
    user = st.session_state.user
    st.sidebar.title("Travel DB")
    st.sidebar.write(f"접속 회원: **{user['name']}**")
    st.sidebar.caption(f"권한: {user['role']}")

    if st.sidebar.button("로그아웃"):
        clear_login()
        st.rerun()

    stored_menu = query_param_value("menu") or st.session_state.get("active_menu") or "홈"
    if stored_menu not in MENU_ITEMS:
        stored_menu = "홈"
    selected_menu = st.sidebar.radio(
        "메뉴",
        MENU_ITEMS,
        index=MENU_ITEMS.index(stored_menu),
    )
    st.session_state.active_menu = selected_menu
    if query_param_value("menu") != selected_menu:
        try:
            st.query_params["menu"] = selected_menu
        except Exception:
            pass
    return selected_menu


def render_dashboard() -> None:
    render_page_heading(
        "DASHBOARD",
        "수집된 여행 데이터 한눈에 보기",
        "지역, 관광지, 축제, 코스, 찜, 리뷰 데이터를 집계해서 발표용 요약 화면으로 보여줍니다.",
    )
    counts = db.dashboard_counts()
    cols = st.columns(6)
    labels = [
        ("지역", "regions"),
        ("관광지", "places"),
        ("축제", "festivals"),
        ("여행코스", "courses"),
        ("찜", "favorites"),
        ("리뷰", "reviews"),
    ]
    for col, (label, key) in zip(cols, labels):
        col.metric(label, counts.get(key, 0))

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("카테고리별 관광지 수")
        rows = db.popular_categories()
        if rows:
            frame = pd.DataFrame(rows)
            st.bar_chart(frame.set_index("category_name")["place_count"])
        else:
            st.info("카테고리 데이터가 아직 없습니다.")

    with right:
        st.subheader("다가오는 축제")
        festivals = db.upcoming_festivals()
        if festivals:
            for item in festivals:
                st.write(
                    f"**{item['festival_name']}** · {item['region_name']} · "
                    f"{item['start_date'] or '-'} ~ {item['end_date'] or '-'}"
                )
                st.caption(item["overview"] or "")
        else:
            st.info("등록된 축제가 없습니다.")


def render_collector() -> None:
    render_page_heading(
        "CRAWLING",
        "축제 데이터를 수집하고 DB에 저장",
        "TourAPI 키는 서버 설정값으로만 읽고, 화면에서는 입력받지 않습니다.",
    )

    service_key = configured_tourapi_key()
    if service_key:
        st.success("TourAPI 서비스키가 설정되어 있습니다. 화면에 키를 노출하지 않고 수집합니다.")
    else:
        st.warning(".streamlit/secrets.toml 또는 환경변수 TOUR_API_SERVICE_KEY를 먼저 설정해주세요.")

    limit = st.slider("수집 개수", min_value=5, max_value=50, value=20, step=5)

    if st.button("축제 데이터 수집 및 DB 저장", type="primary"):
        if not service_key:
            st.warning("TourAPI 서비스키가 설정되지 않아 API 수집을 실행할 수 없습니다.")
            return
        festivals, status, message = collector.collect_festival_data(service_key, limit)
        inserted = 0
        for row in festivals:
            db.upsert_festival(row)
            inserted += 1
        db.log_crawl("festival_collector", collector.VISITKOREA_FESTIVAL_URL, status, inserted, message)
        st.success(f"{inserted}건 처리 완료: {message}")

    if st.button("샘플 관광지 추가 저장"):
        inserted = 0
        for row in collector.fallback_places():
            db.upsert_place(row)
            inserted += 1
        db.log_crawl("place_fallback", "fallback", "FALLBACK", inserted, "발표 시연용 관광지 샘플을 저장했습니다.")
        st.success(f"샘플 관광지 {inserted}건 저장 완료")

    with st.expander("한국관광공사 국문 관광정보 서비스로 장소 수집", expanded=True):
        st.caption("지역별 관광지, 대표사진, 문화시설, 음식점, 숙박, 여행코스 데이터를 기존 DB에 저장합니다.")
        if st.button("전체 TourAPI 데이터 수집", type="primary", use_container_width=True):
            if not service_key:
                st.warning("TourAPI 서비스키가 설정되지 않아 API 수집을 실행할 수 없습니다.")
                return
            try:
                places, festivals, status, message = collector.collect_tourapi_full_dataset(service_key)
                inserted_places = 0
                for row in places:
                    db.upsert_tourapi_place(row)
                    inserted_places += 1
                inserted_festivals = 0
                for row in festivals:
                    db.upsert_festival(row)
                    inserted_festivals += 1
                total = inserted_places + inserted_festivals
                db.log_crawl("tourapi_full_collection", collector.TOUR_API_BASE_URL, status, total, message)
                st.success(f"전체 수집 완료: 장소 {inserted_places}건, 축제 {inserted_festivals}건")
            except Exception as exc:
                db.log_crawl("tourapi_full_collection", collector.TOUR_API_BASE_URL, "FAILED", 0, str(exc))
                st.error(f"TourAPI 전체 수집 실패: {exc}")

        tourapi_region_map = region_options()
        tourapi_region = st.selectbox("수집 지역", list(tourapi_region_map.keys()), key="tourapi_region")
        content_labels = st.multiselect(
            "수집 유형",
            list(collector.TOURAPI_CONTENT_TYPES.keys()),
            default=["관광지", "문화시설", "음식점", "숙박"],
        )
        limit_per_type = st.slider("유형별 수집 개수", min_value=5, max_value=100, value=20, step=5)
        if st.button("TourAPI 장소 수집 및 DB 저장", type="primary"):
            if not service_key:
                st.warning("TourAPI 서비스키가 설정되지 않아 API 수집을 실행할 수 없습니다.")
                return
            content_type_ids = [collector.TOURAPI_CONTENT_TYPES[label] for label in content_labels]
            if not content_type_ids:
                st.warning("수집 유형을 하나 이상 선택해주세요.")
                return
            try:
                places, status, message = collector.collect_tourapi_places(
                    service_key,
                    tourapi_region_map[tourapi_region],
                    content_type_ids,
                    limit_per_type,
                )
                inserted = 0
                for row in places:
                    db.upsert_tourapi_place(row)
                    inserted += 1
                db.log_crawl("tourapi_areaBasedList2", collector.TOUR_API_AREA_BASED_URL, status, inserted, message)
                if inserted:
                    st.success(f"{inserted}건 저장 완료: {message}")
                else:
                    st.warning(message)
            except Exception as exc:
                db.log_crawl("tourapi_areaBasedList2", collector.TOUR_API_AREA_BASED_URL, "FAILED", 0, str(exc))
                st.error(f"TourAPI 수집 실패: {exc}")

    st.subheader("최근 수집 로그")
    logs = db.recent_crawl_logs()
    st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)


def render_place_search() -> None:
    render_page_heading(
        "EXPLORE",
        "지역과 카테고리로 여행지 탐색",
        "관광지, 카테고리, 리뷰, 찜 데이터를 연결해 DB 관계가 화면에서 드러나도록 구성했습니다.",
    )
    region_map = {"전체": None} | region_options()
    category_map = {"전체": None} | category_options()

    col1, col2, col3 = st.columns([1, 1, 1.4])
    selected_region = col1.selectbox("지역", list(region_map.keys()))
    selected_category = col2.selectbox("카테고리", list(category_map.keys()))
    keyword = col3.text_input("검색어")

    with st.expander("맞춤 추천 조건", expanded=True):
        preferences = render_preference_controls("explore", default_duration="당일치기")

    rows = db.search_places(region_map[selected_region], category_map[selected_category], keyword)
    if not rows:
        st.info("조건에 맞는 여행지가 없습니다.")
        return

    rows = recommender.score_places(rows, preferences, favorite_bias_for_user())

    for row in rows:
        with st.container(border=True):
            top = st.columns([3, 1, 1])
            top[0].subheader(row["place_name"])
            top[1].metric("추천 점수", f"{row['recommendation_score']:.1f}")
            top[2].metric("평점", f"{recommender.safe_float(row.get('average_rating')):.2f}")
            st.caption(f"{row['region_name']} · {row['address'] or '주소 정보 없음'}")
            st.write(row["overview"] or "소개 정보가 없습니다.")
            st.caption(
                f"카테고리: {row['categories'] or '-'} · 리뷰 {row['review_count'] or 0}개 · "
                f"태그: {row.get('display_tags') or '-'}"
            )
            for reason in row.get("recommendation_reasons", []):
                st.write(f"- {reason}")
            render_place_detail(row)

            actions = st.columns([1, 1, 4])
            if actions[0].button("찜 토글", key=f"fav-{row['place_id']}"):
                result = db.toggle_favorite(st.session_state.user["member_id"], row["place_id"])
                st.toast("찜에 추가했습니다." if result == "added" else "찜에서 삭제했습니다.")
            with actions[1].popover("리뷰 작성"):
                rating = st.slider("평점", 1, 5, 5, key=f"rating-{row['place_id']}")
                content = st.text_area("리뷰", key=f"review-{row['place_id']}")
                if st.button("저장", key=f"save-review-{row['place_id']}"):
                    if content.strip():
                        db.add_review(st.session_state.user["member_id"], row["place_id"], rating, content.strip())
                        st.success("리뷰를 저장했습니다.")
                    else:
                        st.warning("리뷰 내용을 입력해주세요.")

    with st.expander("추천 장소 지도 보기"):
        render_recommendation_map(rows)


def render_course_builder() -> None:
    render_page_heading(
        "COURSE",
        "방문 순서가 저장되는 여행 코스 만들기",
        "추천 후보를 선택하면 여행 코스와 코스 상세 테이블에 나뉘어 저장됩니다.",
    )
    region_map = region_options()
    category_map = {"상관없음": None} | category_options()

    col1, col2 = st.columns(2)
    selected_region = col1.selectbox("코스 지역", list(region_map.keys()))
    selected_category = col2.selectbox("선호 카테고리", list(category_map.keys()))
    course_title = st.text_input("코스 이름", value=f"{selected_region.split(' ')[0]} 추천 여행 코스")

    date_cols = st.columns(2)
    start_date = date_cols[0].date_input("시작일", value=date.today())
    end_date = date_cols[1].date_input("종료일", value=date.today())

    with st.expander("맞춤 조건으로 여행 코스 자동 생성", expanded=True):
        course_preferences = render_preference_controls("course", default_duration="당일치기")
        candidate_rows = db.search_places(region_map[selected_region], category_map[selected_category], "")
        scored_rows = recommender.score_places(candidate_rows, course_preferences, favorite_bias_for_user())
        generated_course = course_generator.generate_course(scored_rows, course_preferences["duration"])
        st.caption(course_generator.course_description(generated_course, course_preferences["duration"], course_preferences["transport"]))
        if generated_course:
            for item in generated_course:
                with st.container(border=True):
                    left, right = st.columns([1, 3])
                    left.write(f"**{item['time_slot']}**")
                    right.write(f"**{item['place_name']}** · {item['category']}")
                    right.caption(item["address"])
                    right.write(item["reason"])
        else:
            st.info("자동 코스를 만들 추천 후보가 아직 없습니다.")

        if st.button("자동 생성 코스 저장", type="primary", key="save_auto_course"):
            place_ids = [item["place_id"] for item in generated_course if item.get("place_id")]
            if not place_ids:
                st.warning("저장할 장소가 없습니다.")
            else:
                course_id = db.create_course(
                    st.session_state.user["member_id"],
                    course_title,
                    region_map[selected_region],
                    place_ids,
                    start_date,
                    end_date,
                )
                st.success(f"자동 생성 코스가 저장되었습니다. 코스 ID: {course_id}")

    recommendations = db.recommend_places(region_map[selected_region], category_map[selected_category], limit=8)
    if not recommendations:
        st.info("추천할 관광지가 없습니다.")
        return

    place_label_to_id = {
        f"{row['place_name']} · 평점 {row['average_rating']:.2f}": row["place_id"]
        for row in recommendations
    }
    selected_places = st.multiselect(
        "코스에 넣을 여행지를 방문 순서대로 선택",
        list(place_label_to_id.keys()),
        default=list(place_label_to_id.keys())[: min(3, len(place_label_to_id))],
    )

    st.subheader("추천 후보")
    for idx, row in enumerate(recommendations, start=1):
        st.write(f"{idx}. **{row['place_name']}** · {row['address'] or '주소 없음'}")
        st.caption(row["overview"] or "")

    if st.button("코스 저장", type="primary"):
        if not selected_places:
            st.warning("최소 1개 이상의 여행지를 선택해주세요.")
            return
        place_ids = [place_label_to_id[label] for label in selected_places]
        course_id = db.create_course(
            st.session_state.user["member_id"],
            course_title,
            region_map[selected_region],
            place_ids,
            start_date,
            end_date,
        )
        st.success(f"여행 코스가 저장되었습니다. 코스 ID: {course_id}")


def render_my_activity() -> None:
    render_page_heading(
        "MY DATA",
        "회원별 찜과 저장 코스 확인",
        "회원 1명이 여러 찜과 여러 여행 코스를 가질 수 있는 관계를 확인하는 화면입니다.",
    )
    user_id = st.session_state.user["member_id"]

    tab_fav, tab_courses = st.tabs(["찜한 여행지", "내 여행 코스"])

    with tab_fav:
        rows = db.get_favorites(user_id)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            category_counts = db.favorite_category_counts(user_id)
            if category_counts:
                st.caption(
                    "찜 성향: "
                    + ", ".join(f"{category} {count}개" for category, count in category_counts.items())
                )
        else:
            st.info("찜한 여행지가 없습니다.")

    with tab_courses:
        courses = db.get_member_courses(user_id)
        if not courses:
            st.info("저장한 여행 코스가 없습니다.")
            return
        for course in courses:
            with st.expander(f"{course['course_title']} · {course['region_name']} · {course['item_count']}곳"):
                st.caption(f"{course['start_date'] or '-'} ~ {course['end_date'] or '-'}")
                items = db.get_course_items(course["course_id"])
                for item in items:
                    st.write(f"{item['visit_order']}. **{item['place_name']}** · {item['address'] or ''}")


def render_admin_sql() -> None:
    render_page_heading(
        "ADMIN SQL",
        "HeidiSQL 결과와 비교하는 읽기 전용 쿼리",
        "발표 시 DB 클라이언트와 앱 화면이 같은 데이터를 바라본다는 점을 보여줄 수 있습니다.",
    )
    if st.session_state.user["role"] != "ADMIN":
        st.warning("관리자만 사용할 수 있습니다.")
        return

    with st.expander("추천 기능용 DB 보강 SQL"):
        st.caption("기존 DB를 다시 만들지 않고, 없는 컬럼만 안전하게 추가합니다.")
        if st.button("추천용 컬럼 안전 추가"):
            results = db.ensure_recommendation_schema()
            st.code("\n".join(results))
        st.write("HeidiSQL에서 직접 실행할 ALTER TABLE 문")
        st.code(db.recommendation_schema_sql(), language="sql")
        st.write("중복 장소 확인/정리 SQL 예시")
        st.code(db.duplicate_cleanup_sql(), language="sql")

    st.caption("발표 시 HeidiSQL과 같은 결과가 나오는지 비교하기 좋은 읽기 전용 SQL 실행 화면입니다.")
    default_sql = """
SELECT r.region_name, COUNT(p.place_id) AS place_count
FROM regions r
LEFT JOIN places p ON p.region_id = r.region_id
GROUP BY r.region_id, r.region_name
ORDER BY place_count DESC;
""".strip()
    query = st.text_area("SELECT 쿼리", value=default_sql, height=160)
    if st.button("실행"):
        if not query.strip().lower().startswith("select"):
            st.error("안전을 위해 SELECT 쿼리만 실행할 수 있습니다.")
            return
        try:
            st.dataframe(pd.DataFrame(db.fetch_all(query)), use_container_width=True, hide_index=True)
        except Error as exc:
            st.error(f"SQL 실행 실패: {exc}")


def main() -> None:
    inject_design()
    init_state()
    ok, message = db.test_connection()
    if not ok:
        render_db_warning(message)
        return
    if query_param_value("logout") == "1":
        clear_login()
        render_auth()
        return
    restore_login_from_query()

    if not st.session_state.user:
        render_auth()
        return

    menu = render_sidebar()
    if menu != "홈":
        render_site_nav(menu)

    if menu == "홈":
        render_home()
    elif menu == "대시보드":
        render_dashboard()
    elif menu == "데이터 수집":
        render_collector()
    elif menu == "여행지 탐색":
        render_place_search()
    elif menu == "여행 코스 만들기":
        render_course_builder()
    elif menu == "내 활동":
        render_my_activity()
    elif menu == "관리자 SQL":
        render_admin_sql()


if __name__ == "__main__":
    main()
