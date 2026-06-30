from __future__ import annotations

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
import recommender

db = importlib.reload(db)


st.set_page_config(
    page_title="TravelDB 맞춤 여행 추천",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


KOREA_REGIONS = [
    "전국",
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
    "경주",
    "강릉",
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
    "가족",
    "숙박",
]

CATEGORY_TO_DB = {
    "관광지": ["관광지"],
    "자연": ["자연"],
    "미식": ["미식"],
    "카페": ["카페", "미식"],
    "문화시설": ["문화시설", "실내"],
    "역사": ["역사"],
    "사진 명소": ["야간", "자연", "관광지"],
    "야간": ["야간"],
    "가족": ["가족"],
    "숙박": ["숙박"],
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

          div[data-testid="stForm"] {
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

          div[data-testid="stForm"] label {
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

          @media (max-width: 767px) {
            .nav-menu { display: none; }
            .hero-nav { padding: 20px 22px; }
            .hero-content { margin-top: -190px; }
            .nav-auth { gap: 12px; font-size: 0.86rem; }
            div[data-testid="stForm"] {
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


def restore_login() -> None:
    if st.session_state.user:
        return
    try:
        username = st.query_params.get("login_user")
    except Exception:
        username = None
    if not username:
        return
    try:
        user = db.get_member_by_username(str(username))
    except Error:
        return
    if user:
        st.session_state.user = user


def persist_login(user: dict[str, Any]) -> None:
    st.session_state.user = user
    try:
        st.query_params.clear()
        st.query_params["login_user"] = str(user["username"])
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


def render_account_panel() -> None:
    mode = query_value("auth")
    if mode not in {"login", "signup"} or st.session_state.user:
        return

    title = "로그인" if mode == "login" else "회원가입"
    st.markdown(
        f"""
        <div class="section-shell">
          <div class="section-kicker">ACCOUNT</div>
          <h2 class="section-title">{title}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
            st.caption("데모 계정: demo / demo1234")
        else:
            regions = db.get_regions()
            options = {f"{row['region_name']} ({row['province']})": row["region_id"] for row in regions}
            cols = st.columns(2)
            new_username = cols[0].text_input("아이디", key="signup_username")
            name = cols[1].text_input("이름", key="signup_name")
            email = cols[0].text_input("이메일", key="signup_email")
            new_password = cols[1].text_input("비밀번호", type="password", key="signup_password")
            selected_region = st.selectbox("관심 지역", list(options.keys()) or ["전국"], key="signup_region")
            if st.button("회원가입", type="primary", use_container_width=True, key="signup_submit"):
                if not all([new_username, name, email, new_password]):
                    st.warning("모든 항목을 입력해주세요.")
                    return
                try:
                    db.create_member(new_username, new_password, name, email, options.get(selected_region))
                    st.success("회원가입이 완료되었습니다. 오른쪽 상단에서 로그인해주세요.")
                except Error as exc:
                    st.error(f"회원가입 실패: {exc}")


def render_hero() -> None:
    if st.session_state.user:
        user_name = html.escape(str(st.session_state.user["name"]))
        auth_html = f'<span class="nav-user">{user_name}님</span><a href="{href_for(logout="1")}">로그아웃</a>'
    else:
        auth_html = f'<a href="{href_for(auth="login")}">로그인</a><a href="{href_for(auth="signup")}">회원가입</a>'
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
    if "가족" in categories:
        return "가족 여행"
    return "관광지 위주"


def render_search_form() -> dict[str, Any] | None:
    default_start = date.today() + timedelta(days=10)
    default_end = default_start + timedelta(days=1)

    with st.form("trip_search_form"):
        top = st.columns([1.25, 1, 1, 0.75])
        destination = top[0].selectbox("어디로 떠나시나요?", KOREA_REGIONS, index=0)
        start_date = top[1].date_input("출발일", value=default_start)
        end_date = top[2].date_input("돌아오는 날", value=default_end)
        adults = top[3].number_input("인원", min_value=1, max_value=10, value=2, step=1)

        bottom = st.columns([1.8, 1, 1, 0.95])
        categories = bottom[0].multiselect(
            "여행 카테고리",
            TRIP_CATEGORIES,
            default=["관광지", "미식", "카페"],
        )
        companion = bottom[1].selectbox("동행", recommender.COMPANION_TYPES, index=2)
        budget = bottom[2].selectbox("예산", recommender.BUDGET_LEVELS, index=1)
        weather = bottom[3].selectbox("날씨", recommender.WEATHER_TYPES, index=0)

        submitted = st.form_submit_button("검색", type="primary", use_container_width=True)

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
        "companion": companion,
        "budget": budget,
        "weather": weather,
        "duration_label": duration_from_dates(start_date, end_date),
    }


def trip_preferences(search: dict[str, Any]) -> dict[str, Any]:
    return {
        "travel_style": style_from_categories(search["categories"]),
        "companion": search["companion"],
        "budget": search["budget"],
        "transport": "대중교통",
        "weather": search["weather"],
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
    db_categories = category_db_names(search["categories"])
    rows = db.search_places_for_planner(search["destination"], db_categories, limit=180)
    fallback_used = False
    if not rows and search["destination"] != "전국":
        fallback_used = True
        rows = db.search_places_for_planner("전국", db_categories, limit=180)

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
    restaurants = db.search_restaurants_for_region(search["destination"], limit=8)
    accommodations = db.search_accommodations_for_region(search["destination"], limit=6)
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
        "api_insights": insights,
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
    cols[0].metric("여행지", search["destination"])
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


def render_course(result: dict[str, Any]) -> None:
    course = result["course"]
    section_header("ITINERARY", "추천 코스", "추천 점수와 카테고리를 기준으로 시간대별 방문 순서를 정리했습니다.")
    if not course:
        st.info("코스를 만들 후보가 아직 부족합니다.")
        return

    for item in course:
        with st.container(border=True):
            cols = st.columns([0.9, 2.2, 1])
            cols[0].write(f"**{item['time_slot']}**")
            cols[1].subheader(item["place_name"])
            cols[1].caption(f"{item['category']} · {item['address']}")
            cols[1].write(item["reason"])
            cols[2].metric("추천 점수", f"{item.get('recommendation_score', 0):.1f}")


def render_place_card(row: dict[str, Any], key_prefix: str) -> None:
    with st.container(border=True):
        top = st.columns([1, 2.4, 0.9])
        image_url = row.get("image_url") or row.get("source_url")
        if image_url and str(image_url).startswith("http"):
            top[0].image(str(image_url), use_container_width=True)
        else:
            top[0].write("대표사진 없음")
        top[1].subheader(row.get("place_name") or "이름 없음")
        top[1].caption(f"{row.get('region_name') or '-'} · {row.get('address') or '주소 정보 없음'}")
        top[1].write(row.get("overview") or "소개 정보가 없습니다.")
        top[2].metric("추천 점수", f"{row.get('recommendation_score', 0):.1f}")
        top[2].metric("평점", f"{recommender.safe_float(row.get('average_rating')):.2f}")

        reasons = row.get("recommendation_reasons") or []
        for reason in reasons[:3]:
            st.write(f"- {reason}")
        st.caption(f"카테고리: {row.get('categories') or '-'} · 태그: {row.get('display_tags') or row.get('tags') or '-'}")

        if st.session_state.user:
            if st.button("찜하기 / 해제", key=f"{key_prefix}_{row.get('place_id')}", use_container_width=True):
                result = db.toggle_favorite(st.session_state.user["member_id"], row["place_id"])
                st.toast("찜에 추가했습니다." if result == "added" else "찜에서 삭제했습니다.")


def render_recommendations(result: dict[str, Any]) -> None:
    section_header("RECOMMENDED", "추천 여행지", "선택한 카테고리, 날씨, 동행 유형, 찜 성향을 반영해 점수를 계산했습니다.")
    places = result["places"][:8]
    if not places:
        st.info("추천할 여행지가 없습니다.")
        return
    for row in places:
        render_place_card(row, "place_fav")


def render_stays_and_food(result: dict[str, Any]) -> None:
    section_header("STAY & FOOD", "추천 숙소와 식당", "여행지와 같은 지역의 숙박/음식 데이터를 함께 정리했습니다.")
    stay_col, food_col = st.columns(2)

    with stay_col:
        st.subheader("숙소")
        accommodations = result["accommodations"]
        if not accommodations:
            st.info("해당 지역 숙소 데이터가 아직 없습니다.")
        for item in accommodations:
            with st.container(border=True):
                st.write(f"**{item['accommodation_name']}**")
                st.caption(f"{item.get('region_name') or '-'} · {item.get('address') or '주소 정보 없음'}")
                st.write(f"가격대: {item.get('price_level') or '정보 없음'} · 전화: {item.get('phone') or '정보 없음'}")

    with food_col:
        st.subheader("식당")
        restaurants = result["restaurants"]
        if not restaurants:
            st.info("해당 지역 식당 데이터가 아직 없습니다.")
        for item in restaurants:
            with st.container(border=True):
                st.write(f"**{item['restaurant_name']}**")
                st.caption(f"{item.get('region_name') or '-'} · {item.get('address') or '주소 정보 없음'}")
                st.write(f"종류: {item.get('food_type') or '음식점'} · 가격대: {item.get('price_level') or '정보 없음'}")


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
            "8개 승인 API는 모두 같은 키를 사용하도록 연결했습니다. 국문 관광정보는 장소/숙박/식당/축제의 기본 DB가 되고, "
            "관광사진·방문자수·집중률·연관 관광지·중심 관광지·관광 다양성·관광 자원 수요는 추천 점수와 결과 요약을 보강합니다."
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
    search = render_search_form()
    if search:
        try:
            st.session_state.trip_result = build_trip_result(search)
        except Error as exc:
            st.error(f"추천 데이터를 불러오지 못했습니다: {exc}")
            st.session_state.trip_result = None

    result = st.session_state.trip_result
    if result:
        render_summary(result)
        render_course(result)
        render_stays_and_food(result)
        render_recommendations(result)
    else:
        section_header(
            "ONE SEARCH",
            "검색 한 번으로 코스, 숙소, 식당까지",
            "지역과 날짜, 카테고리를 고르면 여러 탭을 오가지 않고 한 화면에서 추천 결과를 확인합니다.",
        )
        cols = st.columns(3)
        samples = [
            ("1", "카테고리 선택", "관광지, 미식, 카페, 자연처럼 여행 목적을 먼저 고릅니다."),
            ("2", "추천 점수 계산", "날씨, 동행, 예산, 평점, 찜 성향을 더해 후보를 정렬합니다."),
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
