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
    page_title="TravelDB 새 여행 홈",
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
            border-radius: 8px;
            border-color: var(--line);
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
          }

          div[data-testid="stVerticalBlockBorderWrapper"] {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px))) !important;
            margin-left: auto !important;
            margin-right: auto !important;
          }

          div[data-testid="stForm"],
          div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 44px auto 58px !important;
            padding: 22px 24px 24px !important;
            border: 1px solid rgba(226, 232, 240, 0.95) !important;
            border-radius: 12px !important;
            background: rgba(255, 255, 255, 0.97) !important;
            box-shadow: 0 20px 48px rgba(15, 23, 42, 0.16) !important;
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
            border-radius: 8px;
            min-height: 44px;
            padding: 9px 18px;
            border: 1px solid var(--line);
            background: #fff;
            color: var(--ink);
            font-weight: 700;
          }

          .stButton > button:hover,
          .stDownloadButton > button:hover {
            border-color: var(--blue);
            color: var(--blue-dark);
            box-shadow: 0 10px 24px rgba(37, 99, 235, 0.12);
          }

          .stButton > button[kind="primary"] {
            background: var(--blue);
            border-color: var(--blue);
            color: #fff;
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

          .hero-photo {
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

          .nav-auth {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--ink);
            font-size: 0.95rem;
            font-weight: 700;
            white-space: nowrap;
          }

          .nav-auth a {
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
            min-height: calc(100vh - 84px);
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

          .search-intro {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 18px;
          }

          .search-intro h3 {
            margin: 0;
            font-size: 1.25rem;
            color: var(--ink);
          }

          .search-intro p {
            margin: 6px 0 0;
            color: var(--muted);
            line-height: 1.6;
          }

          .search-chip {
            flex: 0 0 auto;
            padding: 8px 11px;
            border-radius: 999px;
            background: #ECFDF5;
            color: #047857;
            font-size: 0.82rem;
            font-weight: 800;
          }

          .quick-grid {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 0 auto 34px;
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 12px;
          }

          .quick-item {
            min-height: 116px;
            padding: 17px 15px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #fff;
            box-shadow: 0 12px 26px rgba(15,23,42,0.06);
          }

          .quick-icon {
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 14px;
            border-radius: 8px;
            background: #EFF6FF;
            color: var(--blue-dark);
            font-weight: 900;
          }

          .quick-title {
            color: var(--ink);
            font-weight: 800;
            margin-bottom: 5px;
          }

          .quick-copy {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.45;
            word-break: keep-all;
          }

          .empty-guide {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 0 auto 42px;
            padding: 22px 24px;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: #fff;
            color: var(--muted);
            line-height: 1.7;
            box-shadow: 0 12px 28px rgba(15,23,42,0.05);
          }

          .public-search {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 46px auto 56px;
            position: relative;
            z-index: 5;
            display: grid;
            grid-template-columns: 1.25fr 1fr 0.7fr auto;
            align-items: center;
            gap: 0;
            overflow: hidden;
            border: 1px solid rgba(226,232,240,0.95);
            border-radius: 14px;
            background: #fff;
            box-shadow: 0 22px 56px rgba(15,23,42,0.22);
          }

          .public-search-cell {
            min-height: 78px;
            padding: 18px 22px;
            border-right: 1px solid var(--line);
          }

          .public-search-label {
            margin-bottom: 7px;
            color: #64748B;
            font-size: 0.84rem;
            font-weight: 800;
          }

          .public-search-value {
            color: #111827;
            font-size: 1rem;
            font-weight: 800;
          }

          .public-search-action {
            min-height: 78px;
            display: flex;
            align-items: center;
            padding: 12px;
          }

          .public-search-action a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 150px;
            min-height: 54px;
            border-radius: 10px;
            background: var(--blue);
            color: #fff;
            text-decoration: none;
            font-weight: 900;
          }

          .public-home-note {
            max-width: min(960px, calc(100vw - clamp(32px, 18vw, 430px)));
            margin: 0 auto 36px;
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
          }

          .public-home-card {
            padding: 20px;
            border-radius: 14px;
            background: #F8FAFC;
            border: 1px solid #EEF2F7;
          }

          .public-home-card strong {
            display: block;
            margin-bottom: 8px;
            color: #111827;
            font-size: 1rem;
          }

          .public-home-card span {
            color: #64748B;
            font-size: 0.92rem;
            line-height: 1.55;
          }

          .card-note {
            color: var(--muted);
            line-height: 1.6;
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
            .nav-auth { gap: 8px; font-size: 0.82rem; }
            .nav-auth a { padding: 8px 9px; }
            .hero-main { max-width: calc(100vw - 32px); min-height: calc(100vh - 84px); padding: 0; }
            .headline .line1,
            .headline .line2 { font-size: 2.35rem; }
            .hero-copy { font-size: 1rem; }
            .public-search {
              grid-template-columns: 1fr;
              margin: 32px 16px 36px;
            }
            .public-search-cell {
              min-height: auto;
              border-right: 0;
              border-bottom: 1px solid var(--line);
              padding: 14px 18px;
            }
            .public-search-action {
              min-height: auto;
              padding: 14px;
            }
            .public-search-action a {
              width: 100%;
            }
            .public-home-note {
              grid-template-columns: 1fr;
              margin-left: 16px;
              margin-right: 16px;
            }
            div[data-testid="stForm"],
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#trip-search-panel) {
              margin: 32px 16px 34px !important;
              padding: 20px !important;
            }
            .search-intro { align-items: flex-start; flex-direction: column; gap: 10px; }
            .quick-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-left: 16px; margin-right: 16px; }
            .quick-item { min-height: 110px; }
          }

          @media (min-width: 768px) and (max-width: 1100px) {
            .quick-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
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
            '<div class="image-empty">'
            f'{safe_empty_text}</div>',
            unsafe_allow_html=True,
        )




def render_score_breakdown(target, row: dict[str, Any]) -> None:
    breakdown = row.get("recommendation_breakdown") or []
    with target.expander("점수 근거", expanded=False):
        visible_items = []
        for item in breakdown:
            raw_label = str(item.get("label") or "점수 항목")
            raw_detail = str(item.get("detail") or "")
            technical_text = f"{raw_label} {raw_detail}"
            if any(token in technical_text for token in ("TourAPI", "DB 후보", "DB 카테고리", "contenttypeid", "content type")):
                continue
            visible_items.append((item, raw_label, raw_detail))
        if not visible_items:
            st.write("선택 조건에 잘 맞는 후보입니다.")
            return
        for item, raw_label, raw_detail in visible_items:
            points = recommender.safe_float(item.get("points"))
            label = html.escape(raw_label)
            detail = html.escape(raw_detail)
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
        f"""
        <div class="public-search">
          <div class="public-search-cell">
            <div class="public-search-label">여행지</div>
            <div class="public-search-value">국내 지역 · 명소 · 축제</div>
          </div>
          <div class="public-search-cell">
            <div class="public-search-label">일정</div>
            <div class="public-search-value">오늘부터 원하는 날짜</div>
          </div>
          <div class="public-search-cell">
            <div class="public-search-label">인원</div>
            <div class="public-search-value">2명</div>
          </div>
          <div class="public-search-action">
            <a target="_self" href="{href_for(auth="login")}">검색 시작</a>
          </div>
        </div>

        <div class="public-home-note">
          <div class="public-home-card">
            <strong>가볼 만한 곳</strong>
            <span>지역과 관심사에 맞는 여행지를 먼저 추천합니다.</span>
          </div>
          <div class="public-home-card">
            <strong>숙소</strong>
            <span>선택한 지역 근처의 숙소 정보를 함께 확인합니다.</span>
          </div>
          <div class="public-home-card">
            <strong>맛집</strong>
            <span>여행 동선에 곁들이기 좋은 음식점을 정리합니다.</span>
          </div>
          <div class="public-home-card">
            <strong>축제</strong>
            <span>여행 날짜에 즐길 만한 행사를 찾아봅니다.</span>
          </div>
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
                지역과 날짜만 고르면 가볼 만한 곳, 숙소, 맛집, 축제 일정을 한 번에 정리해 드립니다.
              </p>
              <div class="hero-badges">
                <span class="hero-badge">여행지</span>
                <span class="hero-badge">숙소</span>
                <span class="hero-badge">맛집</span>
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
        st.markdown(
            """
            <div class="search-intro">
              <div>
                <h3>여행 조건을 선택해 주세요</h3>
                <p>원하는 지역과 날짜, 관심사를 고르면 어울리는 여행 코스를 찾아드립니다.</p>
              </div>
              <span class="search-chip">맞춤 여행 찾기</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
            "관심 있는 여행",
            TRIP_CATEGORIES,
            default=[],
            help="관광지, 자연, 맛집, 카페처럼 이번 여행에서 보고 싶은 것을 골라주세요.",
        )
        submitted = st.button("여행지 찾아보기", type="primary", use_container_width=True, key="trip_search_submit")

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
    section_header("MY TRIP", "이번 여행 요약", "선택한 여행 조건과 추천 결과를 간단히 확인하세요.")
    cols = st.columns(4)
    cols[0].metric("여행지", search.get("destination_label") or search.get("destination") or "전국")
    cols[1].metric("일정", search["duration_label"])
    cols[2].metric("추천 후보", f"{len(places)}곳")
    cols[3].metric("코스 구성", f"{len(course)}개")
    if result["fallback_used"]:
        st.info("선택한 지역의 후보가 적어 다른 지역의 추천 후보도 함께 참고했습니다.")


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

    section_header("TRIP HELPERS", "여행 전에 같이 확인해 보세요", "주변 장소, 날씨, 이동 비용처럼 여행 전에 필요한 정보를 한곳에 모았습니다.")
    tab_kakao, tab_weather, tab_transport = st.tabs(["주변 장소", "날씨", "교통비"])
    api_status = get_live_api_status_safe()

    with tab_kakao:
        st.markdown('<span class="live-pill">주변 장소 찾기</span>', unsafe_allow_html=True)
        default_kakao_keyword = f"{destination} 관광지" if destination != "전국" else "서울 관광지"
        keyword = st.text_input("검색어", value=default_kakao_keyword, key="kakao_live_keyword")
        if st.button("주변 장소 찾기", type="primary", key="kakao_live_search"):
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
                st.warning("검색 결과가 없습니다. '부산 관광지', '제주 맛집', '서울 카페'처럼 지역과 장소 유형을 함께 입력해 보세요.")
            elif api_status.get("kakao"):
                st.info("검색어를 입력하고 버튼을 누르면 주변 장소를 찾아볼 수 있습니다.")
            else:
                st.info("지금은 주변 장소 찾기를 사용할 수 없습니다.")
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
        st.markdown('<span class="live-pill">여행 날짜 날씨</span>', unsafe_allow_html=True)
        center = weather_center_for_region(destination)
        if not center:
            st.info("선택한 지역의 날씨를 찾지 못했습니다.")
        else:
            st.caption(f"조회 지역: {center.get('region_name')}")
            if st.button("날씨 확인", type="primary", key="weather_live_search"):
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
                    st.info("버튼을 누르면 선택한 날짜의 날씨를 확인합니다.")
                else:
                    st.info("지금은 날씨 확인을 사용할 수 없습니다.")

    with tab_transport:
        st.markdown('<span class="live-pill">이동 비용 예상</span>', unsafe_allow_html=True)
        cols = st.columns([1, 1, 0.6])
        origin = cols[0].text_input("출발지", value="서울역", key="transport_origin")
        destination_text = cols[1].text_input("도착지", value=destination if destination != "전국" else "부산", key="transport_destination")
        people = cols[2].number_input("인원", min_value=1, max_value=10, value=adults, step=1, key="transport_people")
        if st.button("교통비 예상하기", type="primary", key="transport_live_search"):
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
            st.info("출발지와 도착지를 입력하면 이동 방법별 예상 시간과 비용을 확인할 수 있습니다.")


def render_course(result: dict[str, Any]) -> None:
    course = result["course"]
    places_by_id = {int(row.get("place_id") or 0): row for row in result.get("places") or [] if row.get("place_id")}
    section_header("ITINERARY", "추천 코스", "하루 동선을 보기 쉽게 시간대별로 정리했습니다.")
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
            render_score_breakdown(cols[2], item)

def render_place_card(row: dict[str, Any], key_prefix: str, favorite_ids: set[int] | None = None) -> None:
    favorite_ids = favorite_ids or set()
    with st.container(border=True):
        top = st.columns([1, 2.8])
        render_card_image(top[0], row, "관광지 사진 없음")
        name = row.get("place_name") or "이름 없음"
        map_url = naver_map_url(name, row.get("address"))
        top[1].markdown(f"### [{name}]({map_url})")
        top[1].caption(f"{row.get('region_name') or '-'} · {row.get('address') or '주소 정보 없음'}")
        top[1].write(row.get("overview") or "소개 정보가 없습니다.")

        info_row = st.columns([1.5, 1, 0.8])
        info_row[0].metric("추천 점수", f"{row.get('recommendation_score', 0):.1f}")
        info_row[0].caption(f"카테고리: {row.get('categories') or '-'} · 태그: {row.get('display_tags') or row.get('tags') or '-'}")
        render_score_breakdown(info_row[1], row)
        render_favorite_heart(info_row[2], row, favorite_ids, key_prefix)

def render_recommendations(result: dict[str, Any]) -> None:
    section_header("ATTRACTIONS", "가볼 만한 곳", "선택한 지역과 관심사에 어울리는 여행지를 추천합니다.")
    places = result["places"][:8]
    if not places:
        st.info("추천할 관광지가 없습니다.")
        return
    favorite_ids = set(result.get("favorite_place_ids") or refresh_favorite_ids())
    for row in places:
        render_place_card(row, "place_fav", favorite_ids)


def render_accommodations(result: dict[str, Any]) -> None:
    section_header("STAY", "숙소", "여행지 근처에서 머물 만한 숙소를 정리했습니다.")
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


def render_restaurants(result: dict[str, Any]) -> None:
    section_header("FOOD", "맛집", "여행 중 들르기 좋은 음식점을 모았습니다.")
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


def render_festivals(result: dict[str, Any]) -> None:
    section_header("FESTIVAL", "축제와 행사", "여행 날짜에 함께 즐길 만한 축제 정보를 확인하세요.")
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
    with st.expander("서비스 정보"):
        if has_key:
            st.success("여행 정보 보강 기능이 준비되어 있습니다.")
        else:
            st.warning("일부 여행 보조 정보는 현재 사용할 수 없습니다.")
        try:
            counts = db.advanced_api_counts()
        except Error:
            counts = {}
        st.write("TravelDB는 저장된 여행지, 숙소, 맛집, 축제 정보를 바탕으로 추천 결과를 구성합니다.")
        st.caption(
            "참고 정보: "
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
            "READY",
            "검색 후 여행 추천을 보여드립니다",
            "조건을 고르고 검색하면 여행지, 숙소, 맛집, 축제, 추천 코스가 순서대로 정리됩니다.",
        )
        st.markdown(
            """
            <div class="empty-guide">
              추천 결과는 실제 검색을 실행한 뒤 표시됩니다. 먼저 위 검색 박스에서 지역, 일정, 인원, 관심사를 선택해 주세요.
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_data_note()


def main() -> None:
    inject_design()
    init_state()
    ok, message = db.test_connection()
    if not ok:
        render_hero()
        st.error("서비스 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        with st.expander("자세한 오류"):
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
