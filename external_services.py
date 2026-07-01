from __future__ import annotations

import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import unquote
from xml.etree import ElementTree as ET

import requests

KST = timezone(timedelta(hours=9))


def _secret(name: str) -> str | None:
    """환경변수와 Streamlit secrets에서 키를 최대한 유연하게 찾는다.

    학생 프로젝트에서는 secrets.toml에
    KAKAO_REST_API_KEY = "..."처럼 최상위에 넣기도 하고,
    [api]
    KAKAO_REST_API_KEY = "..."처럼 섹션 안에 넣기도 해서 둘 다 지원한다.
    """
    candidates = [name, name.upper(), name.lower()]

    for candidate in candidates:
        value = os.getenv(candidate)
        if value:
            return str(value).strip()

    try:
        import streamlit as st  # type: ignore

        def find_in_mapping(mapping: Any) -> str | None:
            for candidate in candidates:
                try:
                    value = mapping.get(candidate)
                except Exception:
                    value = None
                if value:
                    return str(value).strip()
            return None

        value = find_in_mapping(st.secrets)
        if value:
            return value

        for section in ("api", "apis", "keys", "secrets", "weather", "kakao", "kma", "openai"):
            try:
                nested = st.secrets.get(section)
            except Exception:
                nested = None
            if nested:
                value = find_in_mapping(nested)
                if value:
                    return value
    except Exception:
        return None
    return None


def _data_go_key(*names: str) -> str | None:
    for name in names:
        value = _secret(name)
        if value:
            # data.go.kr의 Encoding 키를 requests params에 그대로 넣으면 이중 인코딩될 수 있어
            # 한 번 디코딩해서 넘긴다. Decoding 키는 그대로 유지된다.
            return unquote(value.strip())
    return None


def _strip_kakao_prefix(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if text.lower().startswith("kakaoak "):
        text = text.split(" ", 1)[1].strip()
    return text or None


def kakao_api_key() -> str | None:
    return _strip_kakao_prefix(
        _secret("KAKAO_REST_API_KEY")
        or _secret("KAKAO_LOCAL_API_KEY")
        or _secret("KAKAO_MAP_API_KEY")
        or _secret("KAKAO_API_KEY")
    )


def kma_short_api_key() -> str | None:
    return _data_go_key(
        "KMA_SHORT_FORECAST_SERVICE_KEY",
        "KMA_SHORT_API_KEY",
        "KMA_SERVICE_KEY",
        "DATA_GO_KR_SERVICE_KEY",
    )


def kma_mid_api_key() -> str | None:
    return _data_go_key(
        "KMA_MID_FORECAST_SERVICE_KEY",
        "KMA_MID_API_KEY",
        "KMA_SERVICE_KEY",
        "DATA_GO_KR_SERVICE_KEY",
    )


def weather_api_key() -> str | None:
    """이전 코드 호환용. 이제 OpenWeather가 아니라 기상청 키 존재 여부를 확인한다."""
    return kma_short_api_key() or kma_mid_api_key()


def live_api_status() -> dict[str, bool]:
    return {
        "kakao": bool(kakao_api_key()),
        "kma_short": bool(kma_short_api_key()),
        "kma_mid": bool(kma_mid_api_key()),
        "openai": bool(openai_api_key()),
    }


def openai_api_key() -> str | None:
    return _secret("OPENAI_API_KEY")


def openai_model() -> str:
    return _secret("OPENAI_MODEL") or "gpt-4.1-mini"



def search_kakao_places(keyword: str, region: str = "", size: int = 10) -> list[dict[str, Any]]:
    """카카오 로컬 키워드 검색.

    카카오 Local API는 '실시간 인기순'을 직접 주는 API가 아니라 키워드 장소 검색 API다.
    그래서 사용자가 입력한 문장에 결과가 없으면 '인기' 같은 수식어를 제거하고,
    지역 + 관광지/맛집/카페 식으로 몇 번 더 검색해서 빈 화면을 줄인다.
    """
    key = kakao_api_key()
    if not key:
        raise RuntimeError("KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")

    raw_keyword = str(keyword or "").strip()
    raw_region = str(region or "").strip()

    def clean_query(text: str) -> str:
        return " ".join(text.replace("실시간", "").replace("인기", "").split()).strip()

    candidates: list[str] = []
    if raw_keyword:
        candidates.append(raw_keyword)
    cleaned = clean_query(raw_keyword)
    if cleaned and cleaned not in candidates:
        candidates.append(cleaned)
    if raw_region and raw_region != "전국":
        for suffix in ("관광지", "명소", "맛집", "카페", "축제"):
            q = f"{raw_region} {suffix}".strip()
            if q not in candidates:
                candidates.append(q)
    else:
        # 카카오 Local API에서 '전국 관광지' 같은 광역 검색은 결과가 비는 경우가 많다.
        # 전국 선택 시에는 대표 도시 검색어로 대체해서 최소한 결과를 보여준다.
        for q in ("서울 관광지", "부산 관광지", "제주 관광지"):
            if q not in candidates:
                candidates.append(q)

    last_detail = ""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []

    for query in candidates:
        if not query:
            continue
        response = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {key}"},
            params={"query": query, "size": max(1, min(int(size), 15)), "sort": "accuracy"},
            timeout=8,
        )
        if response.status_code == 401:
            raise RuntimeError("카카오 인증 실패입니다. JavaScript 키가 아니라 REST API 키를 KAKAO_REST_API_KEY에 넣어주세요.")
        if response.status_code == 403:
            detail = ""
            try:
                body = response.json()
                detail = body.get("msg") or body.get("message") or json.dumps(body, ensure_ascii=False)
            except Exception:
                detail = (response.text or "")[:300]
            raise RuntimeError(
                "카카오 Local API 403 오류입니다. "
                "코드 문제가 아니라 카카오 Developers 앱 설정 문제일 가능성이 큽니다. "
                "[내 애플리케이션 > 제품 설정 > 카카오맵]에서 사용 설정을 켜고, "
                "REST API 키를 KAKAO_REST_API_KEY에 넣었는지 확인하세요. "
                f"카카오 응답: {detail or '응답 본문 없음'}"
            )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = (response.text or "")[:500]
            raise RuntimeError(f"카카오 API HTTP 오류({response.status_code}): {detail}") from exc

        payload = response.json()
        docs = list(payload.get("documents") or [])
        last_detail = f"검색어 '{query}' 결과 {len(docs)}건"
        for doc in docs:
            key_id = str(doc.get("id") or doc.get("place_url") or doc.get("place_name") or "")
            if not key_id or key_id in seen:
                continue
            seen.add(key_id)
            doc["_searched_query"] = query
            merged.append(doc)
            if len(merged) >= size:
                return merged

    if not merged:
        # 오류가 아니라 검색 결과가 0건인 상황을 화면에서 구분할 수 있게 빈 리스트를 반환한다.
        return []
    return merged


# -----------------------------------------------------------------------------
# 기상청 단기/중기예보
# -----------------------------------------------------------------------------


def _parse_target_date(target_date: date | str | None) -> date:
    if isinstance(target_date, str):
        try:
            return datetime.fromisoformat(target_date).date()
        except ValueError:
            return date.today()
    return target_date or date.today()


def _json_or_kma_error(response: requests.Response) -> dict[str, Any]:
    text = response.text or ""
    try:
        return response.json()
    except Exception:
        # serviceKey 오류/승인 오류가 XML로 내려오는 경우가 많아서 메시지를 사람이 읽게 변환한다.
        if text.lstrip().startswith("<"):
            try:
                root = ET.fromstring(text)
                code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode") or "UNKNOWN"
                msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg") or text[:300]
                raise RuntimeError(f"기상청/공공데이터 API 오류({code}): {msg}")
            except RuntimeError:
                raise
            except Exception:
                pass
        raise RuntimeError(f"기상청 API 응답이 JSON이 아닙니다. serviceKey가 Encoding 키라면 Decoding 키로 바꿔보세요. 응답: {text[:300]}")


def _request_data_go_json(path: str, params: dict[str, Any], *, timeout: int = 10) -> dict[str, Any]:
    """공공데이터포털 기상청 API 호출 공통 함수.

    중기예보 공식 문서의 요청주소는 http://apis.data.go.kr/... 형태다.
    일부 환경에서 https가 502를 반환하는 경우가 있어 http를 우선 사용하고,
    실패 시 https도 한 번 더 시도한다.
    """
    errors: list[str] = []
    for base in ("http://apis.data.go.kr", "https://apis.data.go.kr"):
        url = f"{base}{path}"
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code >= 500:
                errors.append(f"{response.status_code} Server Error from {base}: {(response.text or '')[:200]}")
                continue
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                detail = (response.text or "")[:500]
                raise RuntimeError(f"공공데이터포털 HTTP 오류({response.status_code}): {detail}") from exc
            return _json_or_kma_error(response)
        except requests.RequestException as exc:
            errors.append(f"{base}: {exc}")
            continue
    raise RuntimeError(
        "기상청/공공데이터포털 서버가 응답하지 않았습니다. "
        "잠시 후 다시 시도하거나, 공공데이터포털에서 해당 API 활용신청 승인 여부를 확인하세요. "
        + " / ".join(errors[-3:])
    )



def _mid_tmfc_candidates(now: datetime | None = None) -> list[str]:
    """중기예보 tmFc 후보를 넉넉하게 생성한다.

    공공데이터포털 중기예보는 최근 발표시각만 조회 가능하고, 서버 반영 지연 또는
    서버 기준일 차이로 오늘 06/18시가 99 오류를 반환하는 경우가 있다. 그래서
    최신 발표부터 과거 3일치 06/18시까지 순서대로 재시도한다.
    """
    now = now or datetime.now(KST)
    first = _latest_mid_tmfc(now)
    dt = datetime.strptime(first, "%Y%m%d%H%M").replace(tzinfo=KST)
    candidates: list[str] = []
    for _ in range(8):
        value = dt.strftime("%Y%m%d%H%M")
        if value not in candidates:
            candidates.append(value)
        if dt.hour == 18:
            dt = dt.replace(hour=6)
        else:
            dt = (dt - timedelta(days=1)).replace(hour=18)
    return candidates

def _kma_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = payload.get("response") or {}
    header = response.get("header") or {}
    result_code = str(header.get("resultCode") or "")
    if result_code and result_code != "00":
        msg = header.get("resultMsg") or "기상청 API 오류"
        raise RuntimeError(f"기상청 API 오류({result_code}): {msg}")
    body = response.get("body") or {}
    items = body.get("items") or {}
    item = items.get("item") or []
    if isinstance(item, dict):
        return [item]
    return list(item or [])


def _latlon_to_kma_grid(lat: float, lon: float) -> tuple[int, int]:
    """위도/경도를 기상청 단기예보 nx/ny 격자로 변환한다."""
    re = 6371.00877  # 지구 반경(km)
    grid = 5.0
    slat1 = 30.0
    slat2 = 60.0
    olon = 126.0
    olat = 38.0
    xo = 43
    yo = 136

    degrad = math.pi / 180.0
    re_grid = re / grid
    slat1_rad = slat1 * degrad
    slat2_rad = slat2 * degrad
    olon_rad = olon * degrad
    olat_rad = olat * degrad

    sn = math.tan(math.pi * 0.25 + slat2_rad * 0.5) / math.tan(math.pi * 0.25 + slat1_rad * 0.5)
    sn = math.log(math.cos(slat1_rad) / math.cos(slat2_rad)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1_rad * 0.5)
    sf = (sf**sn) * math.cos(slat1_rad) / sn
    ro = math.tan(math.pi * 0.25 + olat_rad * 0.5)
    ro = re_grid * sf / (ro**sn)

    ra = math.tan(math.pi * 0.25 + lat * degrad * 0.5)
    ra = re_grid * sf / (ra**sn)
    theta = lon * degrad - olon_rad
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn
    x = int(ra * math.sin(theta) + xo + 0.5)
    y = int(ro - ra * math.cos(theta) + yo + 0.5)
    return x, y


def _latest_short_base(now: datetime | None = None) -> tuple[str, str]:
    # 단기예보 발표 시각. 실제 반영 지연을 고려해 45분 이전 발표만 사용한다.
    now = now or datetime.now(KST)
    safe_now = now - timedelta(minutes=45)
    base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
    current_hm = safe_now.strftime("%H%M")
    for base_time in reversed(base_times):
        if current_hm >= base_time:
            return safe_now.strftime("%Y%m%d"), base_time
    previous = safe_now - timedelta(days=1)
    return previous.strftime("%Y%m%d"), "2300"


def _latest_mid_tmfc(now: datetime | None = None) -> str:
    # 중기예보 발표 시각은 06시/18시. 반영 지연을 고려해 90분 이전 발표만 사용한다.
    now = now or datetime.now(KST)
    safe_now = now - timedelta(minutes=90)
    hm = safe_now.strftime("%H%M")
    if hm >= "1800":
        return safe_now.strftime("%Y%m%d") + "1800"
    if hm >= "0600":
        return safe_now.strftime("%Y%m%d") + "0600"
    previous = safe_now - timedelta(days=1)
    return previous.strftime("%Y%m%d") + "1800"


PTY_TEXT = {
    "0": "강수 없음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
    "5": "빗방울",
    "6": "빗방울/눈날림",
    "7": "눈날림",
}
SKY_TEXT = {"1": "맑음", "3": "구름많음", "4": "흐림"}


def _format_number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace("℃", "").replace("%", "").strip())
    except Exception:
        return None


def _category_value(items: list[dict[str, Any]], category: str, fcst_date: str, preferred_time: str = "1200") -> Any:
    same_day = [item for item in items if str(item.get("category")) == category and str(item.get("fcstDate")) == fcst_date]
    if not same_day:
        return None
    chosen = min(same_day, key=lambda item: abs(int(str(item.get("fcstTime") or "0000")[:2]) - int(preferred_time[:2])))
    return chosen.get("fcstValue")


def _condition_from_short(pty: Any, sky: Any) -> str:
    pty_s = str(pty) if pty is not None else "0"
    if pty_s not in {"0", "None", ""}:
        return PTY_TEXT.get(pty_s, f"강수형태 {pty_s}")
    sky_s = str(sky) if sky is not None else ""
    return SKY_TEXT.get(sky_s, "정보 없음")


def _short_weather_for_date(lat: float, lon: float, target: date) -> dict[str, Any]:
    key = kma_short_api_key()
    if not key:
        raise RuntimeError("KMA_SHORT_FORECAST_SERVICE_KEY가 설정되어 있지 않습니다.")

    nx, ny = _latlon_to_kma_grid(float(lat), float(lon))
    base_date, base_time = _latest_short_base()
    payload = _request_data_go_json(
        "/1360000/VilageFcstInfoService_2.0/getVilageFcst",
        {
            "serviceKey": key,
            "pageNo": 1,
            "numOfRows": 1000,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny,
        },
        timeout=10,
    )
    items = _kma_items(payload)
    target_ymd = target.strftime("%Y%m%d")

    # 낮 12시 기준으로 대표 날씨를 잡는다. 없으면 해당 날짜 첫 예보를 사용한다.
    available_times = sorted({str(item.get("fcstTime")) for item in items if str(item.get("fcstDate")) == target_ymd})
    if not available_times:
        raise RuntimeError("선택 날짜에 해당하는 단기예보 데이터가 없습니다.")
    preferred_time = min(available_times, key=lambda value: abs(int(value[:2]) - 12))

    tmp = _category_value(items, "TMP", target_ymd, preferred_time)
    tmn = _category_value(items, "TMN", target_ymd, preferred_time)
    tmx = _category_value(items, "TMX", target_ymd, preferred_time)
    pop = _category_value(items, "POP", target_ymd, preferred_time)
    reh = _category_value(items, "REH", target_ymd, preferred_time)
    wsd = _category_value(items, "WSD", target_ymd, preferred_time)
    pty = _category_value(items, "PTY", target_ymd, preferred_time)
    sky = _category_value(items, "SKY", target_ymd, preferred_time)

    condition = _condition_from_short(pty, sky)
    return {
        "source": "kma_short",
        "provider": "기상청 단기예보",
        "target_date": target.isoformat(),
        "condition": condition,
        "temp": _format_number(tmp),
        "min_temp": _format_number(tmn),
        "max_temp": _format_number(tmx),
        "feels_like": None,
        "humidity": _format_number(reh),
        "wind_speed": _format_number(wsd),
        "precip_probability": _format_number(pop),
        "nx": nx,
        "ny": ny,
        "base_date": base_date,
        "base_time": base_time,
        "note": f"기상청 단기예보 기준입니다. 발표시각 {base_date} {base_time}, 대표 시간 {preferred_time}.",
        "raw_json": {"base_date": base_date, "base_time": base_time, "nx": nx, "ny": ny, "items": items},
    }


LAND_REGIONS = [
    ("서울", "11B00000"),
    ("인천", "11B00000"),
    ("경기", "11B00000"),
    ("수원", "11B00000"),
    ("강원", "11D10000"),
    ("춘천", "11D10000"),
    ("원주", "11D10000"),
    ("강릉", "11D20000"),
    ("속초", "11D20000"),
    ("충북", "11C10000"),
    ("청주", "11C10000"),
    ("충남", "11C20000"),
    ("대전", "11C20000"),
    ("세종", "11C20000"),
    ("전북", "11F10000"),
    ("전주", "11F10000"),
    ("군산", "11F10000"),
    ("전남", "11F20000"),
    ("광주", "11F20000"),
    ("목포", "11F20000"),
    ("여수", "11F20000"),
    ("경북", "11H10000"),
    ("대구", "11H10000"),
    ("안동", "11H10000"),
    ("포항", "11H10000"),
    ("경남", "11H20000"),
    ("부산", "11H20000"),
    ("울산", "11H20000"),
    ("창원", "11H20000"),
    ("제주", "11G00000"),
]

TEMP_REGIONS = [
    ("서울", "11B10101"),
    ("인천", "11B20201"),
    ("수원", "11B20601"),
    ("파주", "11B20305"),
    ("춘천", "11D10301"),
    ("원주", "11D10401"),
    ("강릉", "11D20501"),
    ("속초", "11D20401"),
    ("청주", "11C10301"),
    ("대전", "11C20401"),
    ("세종", "11C20404"),
    ("전주", "11F10201"),
    ("군산", "21F10501"),
    ("광주", "11F20501"),
    ("목포", "21F20801"),
    ("여수", "11F20401"),
    ("대구", "11H10701"),
    ("안동", "11H10501"),
    ("포항", "11H10201"),
    ("부산", "11H20201"),
    ("울산", "11H20101"),
    ("창원", "11H20301"),
    ("제주", "11G00201"),
    ("서귀포", "11G00401"),
]


def _normalize_region_text(region_name: str | None) -> str:
    return str(region_name or "").replace("특별시", "").replace("광역시", "").replace("특별자치시", "").replace("특별자치도", "").replace("도", "")


def _region_code(region_name: str | None, table: list[tuple[str, str]], default: str) -> str:
    text = _normalize_region_text(region_name)
    for keyword, code in table:
        if keyword in text:
            return code
    return default



def _mid_weather_for_date(target: date, region_name: str | None = None) -> dict[str, Any]:
    key = kma_mid_api_key()
    if not key:
        raise RuntimeError("KMA_MID_FORECAST_SERVICE_KEY가 설정되어 있지 않습니다.")

    today = datetime.now(KST).date()
    diff_days = (target - today).days
    if diff_days < 4:
        raise RuntimeError("선택 날짜가 중기예보 범위보다 가깝습니다. 단기예보를 사용하세요.")
    if diff_days > 10:
        raise RuntimeError("기상청 중기예보는 보통 10일 후까지 조회할 수 있습니다.")

    land_reg_id = _region_code(region_name, LAND_REGIONS, "11B00000")
    temp_reg_id = _region_code(region_name, TEMP_REGIONS, "11B10101")

    errors: list[str] = []
    land: dict[str, Any] = {}
    temp: dict[str, Any] = {}
    tmfc = ""
    lead_day = diff_days

    for tmfc_candidate in _mid_tmfc_candidates():
        try:
            tmfc_date = datetime.strptime(tmfc_candidate, "%Y%m%d%H%M").date()
            candidate_lead_day = (target - tmfc_date).days
            # 중기예보 필드는 발표일 기준 3~10일 후만 존재한다.
            if candidate_lead_day < 3 or candidate_lead_day > 10:
                continue

            land_payload = _request_data_go_json(
                "/1360000/MidFcstInfoService/getMidLandFcst",
                {
                    "serviceKey": key,
                    "pageNo": 1,
                    "numOfRows": 10,
                    "dataType": "JSON",
                    "regId": land_reg_id,
                    "tmFc": tmfc_candidate,
                },
                timeout=10,
            )
            land_items = _kma_items(land_payload)
            temp_payload = _request_data_go_json(
                "/1360000/MidFcstInfoService/getMidTa",
                {
                    "serviceKey": key,
                    "pageNo": 1,
                    "numOfRows": 10,
                    "dataType": "JSON",
                    "regId": temp_reg_id,
                    "tmFc": tmfc_candidate,
                },
                timeout=10,
            )
            temp_items = _kma_items(temp_payload)
            land = land_items[0] if land_items else {}
            temp = temp_items[0] if temp_items else {}
            if land or temp:
                tmfc = tmfc_candidate
                lead_day = candidate_lead_day
                break
        except Exception as exc:
            errors.append(f"{tmfc_candidate}: {exc}")
            continue

    if not tmfc:
        hint = (
            "중기예보 API는 발표시각(tmFc)을 최근 조회 가능 범위 안에서만 받습니다. "
            "PC 날짜/시간이 실제 날짜와 다르면 99 오류가 날 수 있으니 Windows 날짜/시간 자동 설정도 확인하세요."
        )
        detail = " / ".join(errors[-3:]) if errors else "재시도할 수 있는 발표시각이 없었습니다."
        raise RuntimeError(f"기상청 중기예보 데이터를 가져오지 못했습니다. {hint} 마지막 오류: {detail}")

    # 3~7일은 오전/오후, 8~10일은 일 단위 필드가 제공된다.
    if 3 <= lead_day <= 7:
        wf_am = land.get(f"wf{lead_day}Am")
        wf_pm = land.get(f"wf{lead_day}Pm")
        rn_am = _format_number(land.get(f"rnSt{lead_day}Am"))
        rn_pm = _format_number(land.get(f"rnSt{lead_day}Pm"))
        if wf_am and wf_pm and wf_am != wf_pm:
            condition = f"오전 {wf_am} / 오후 {wf_pm}"
        else:
            condition = str(wf_pm or wf_am or "정보 없음")
        pop_values = [value for value in [rn_am, rn_pm] if value is not None]
        precip_probability = max(pop_values) if pop_values else None
    else:
        condition = str(land.get(f"wf{lead_day}") or "정보 없음")
        precip_probability = _format_number(land.get(f"rnSt{lead_day}"))

    min_temp = _format_number(temp.get(f"taMin{lead_day}"))
    max_temp = _format_number(temp.get(f"taMax{lead_day}"))
    avg_temp = None
    if min_temp is not None and max_temp is not None:
        avg_temp = round((min_temp + max_temp) / 2, 1)

    return {
        "source": "kma_mid",
        "provider": "기상청 중기예보",
        "target_date": target.isoformat(),
        "condition": condition,
        "temp": avg_temp,
        "min_temp": min_temp,
        "max_temp": max_temp,
        "feels_like": None,
        "humidity": None,
        "wind_speed": None,
        "precip_probability": precip_probability,
        "land_reg_id": land_reg_id,
        "temp_reg_id": temp_reg_id,
        "tmFc": tmfc,
        "lead_day": lead_day,
        "note": f"기상청 중기예보 기준입니다. 발표시각 {tmfc}, 발표일 기준 {lead_day}일 후 예보, 육상예보코드 {land_reg_id}, 기온예보코드 {temp_reg_id}.",
        "raw_json": {"tmFc": tmfc, "lead_day": lead_day, "land_reg_id": land_reg_id, "temp_reg_id": temp_reg_id, "land": land, "temp": temp},
    }


def weather_for_date(
    lat: float,
    lon: float,
    target_date: date | str | None = None,
    region_name: str | None = None,
) -> dict[str, Any]:
    """여행 날짜에 따라 기상청 단기/중기예보를 자동 선택한다.

    - 오늘~3일 뒤: 기상청 단기예보(getVilageFcst)
    - 4~10일 뒤: 기상청 중기예보(getMidLandFcst/getMidTa)
    - 10일 이후: 기상청 예보 제공 범위 밖으로 안내
    """
    target = _parse_target_date(target_date)
    today = datetime.now(KST).date()
    diff_days = (target - today).days

    if diff_days < 0:
        raise RuntimeError("지난 날짜의 날씨는 예보 API로 조회할 수 없습니다.")
    if diff_days <= 3:
        return _short_weather_for_date(float(lat), float(lon), target)
    if diff_days <= 10:
        return _mid_weather_for_date(target, region_name=region_name)
    raise RuntimeError("기상청 단기/중기예보 제공 범위를 벗어난 날짜입니다. 오늘 기준 10일 이내 날짜를 선택하세요.")


# -----------------------------------------------------------------------------
# GPT 교통편/비용 추정
# -----------------------------------------------------------------------------


def transport_estimate_with_gpt(origin: str, destination: str, travel_date: str, people: int = 1) -> dict[str, Any]:
    """OpenAI Responses API로 교통편/비용 추정 JSON을 생성한다. 실제 예매 요금이 아니라 발표용 추정치다."""
    key = openai_api_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "travel_date": {"type": "string"},
            "people": {"type": "integer"},
            "currency": {"type": "string"},
            "disclaimer": {"type": "string"},
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "mode": {"type": "string"},
                        "route_summary": {"type": "string"},
                        "estimated_time_minutes": {"type": "integer"},
                        "estimated_cost_min": {"type": "integer"},
                        "estimated_cost_max": {"type": "integer"},
                        "pros": {"type": "string"},
                        "cons": {"type": "string"},
                    },
                    "required": [
                        "mode",
                        "route_summary",
                        "estimated_time_minutes",
                        "estimated_cost_min",
                        "estimated_cost_max",
                        "pros",
                        "cons",
                    ],
                },
            },
            "recommended_option": {"type": "string"},
        },
        "required": [
            "origin",
            "destination",
            "travel_date",
            "people",
            "currency",
            "disclaimer",
            "options",
            "recommended_option",
        ],
    }
    prompt = f"""
한국 국내 여행 교통편을 추정해줘.
출발지: {origin}
도착지: {destination}
날짜: {travel_date}
인원: {people}명

조건:
- 실제 예매 API가 아니므로 반드시 추정치라고 밝혀줘.
- 교통수단은 반드시 기차, 고속버스, 자가용, 택시를 각각 별도 옵션으로 분리해줘.
- "자가용/택시"처럼 두 교통수단을 하나의 옵션으로 합치지 마.
- 비용은 1인 기준 왕복 KRW 범위로 제시해줘.
- 자가용 비용은 연료비 + 고속도로 통행료 기준으로 추정해줘.
- 택시 비용은 장거리 택시요금 기준으로 추정해줘.
- 장거리 이동에서 택시 비용은 자가용보다 훨씬 비싸야 하며, KTX/버스보다 싸게 나오면 안 돼.
- 예상 금액 말고 1인당 왕복 예상 금액이라는 워딩을 사용해줘.
- 내가 아는 서울 - 대구 KTX 왕복 비용은 1인당 약 9만원 정도이고 서울 - 대구 택시 비용은 편도로 약 30만원인데 자꾸 오류가 나네? 정확한 분석 부탁해 
- JSON 스키마를 정확히 지켜줘.
""".strip()

    payload = {
        "model": openai_model(),
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "transport_estimate",
                "schema": schema,
                "strict": True,
            }
        },
    }
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()

    # Responses API SDK 없이 REST 응답에서 JSON 텍스트를 최대한 안전하게 찾는다.
    text_parts: list[str] = []
    for item in payload.get("output") or []:
        for content in item.get("content") or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                text_parts.append(content["text"])
    output_text = "\n".join(text_parts).strip()
    if not output_text and payload.get("output_text"):
        output_text = str(payload.get("output_text"))
    if not output_text:
        raise RuntimeError("OpenAI 응답에서 JSON 텍스트를 찾지 못했습니다.")
    return json.loads(output_text)


def itinerary_from_kakao_with_gpt(
    destination: str,
    travel_date: str,
    duration: str,
    categories: list[str] | tuple[str, ...] | None,
    kakao_places: list[dict[str, Any]],
) -> dict[str, Any]:
    """카카오 장소 검색 결과를 기반으로 OpenAI가 이동 동선을 고려한 코스를 만든다."""
    key = openai_api_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")
    if not kakao_places:
        raise RuntimeError("코스를 만들 카카오 장소 결과가 없습니다.")

    compact_places: list[dict[str, Any]] = []
    for place in kakao_places[:10]:
        compact_places.append(
            {
                "place_name": place.get("place_name"),
                "category_name": place.get("category_name"),
                "address": place.get("road_address_name") or place.get("address_name"),
                "phone": place.get("phone"),
                "place_url": place.get("place_url"),
                "x": place.get("x"),
                "y": place.get("y"),
            }
        )

    def normalize_place_name(value: Any) -> str:
        text = str(value or "").strip().lower()
        for token in (" ", "\t", "\n", "-", "_", "·", ".", ",", "(", ")", "[", "]"):
            text = text.replace(token, "")
        return text

    def dedupe_itinerary(data: dict[str, Any]) -> dict[str, Any]:
        seen: set[str] = set()
        for day in data.get("days") or []:
            unique_stops: list[dict[str, Any]] = []
            for stop in day.get("stops") or []:
                key_name = normalize_place_name(stop.get("place_name"))
                if not key_name or key_name in seen:
                    continue
                seen.add(key_name)
                stop["order"] = len(unique_stops) + 1
                unique_stops.append(stop)
            day["stops"] = unique_stops
        return data

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "destination": {"type": "string"},
            "travel_date": {"type": "string"},
            "duration": {"type": "string"},
            "course_title": {"type": "string"},
            "summary": {"type": "string"},
            "days": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "day": {"type": "integer"},
                        "theme": {"type": "string"},
                        "stops": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "order": {"type": "integer"},
                                    "time": {"type": "string"},
                                    "place_name": {"type": "string"},
                                    "address": {"type": "string"},
                                    "kakao_url": {"type": "string"},
                                    "reason": {"type": "string"},
                                    "move_tip": {"type": "string"},
                                },
                                "required": [
                                    "order",
                                    "time",
                                    "place_name",
                                    "address",
                                    "kakao_url",
                                    "reason",
                                    "move_tip",
                                ],
                            },
                        },
                    },
                    "required": ["day", "theme", "stops"],
                },
            },
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["destination", "travel_date", "duration", "course_title", "summary", "days", "notes"],
    }

    prompt = f"""
카카오맵에서 확보한 장소의 주소, 좌표, 카카오맵 링크를 위치 정보로 활용해서 한국 여행 코스를 구성해줘.
여행지: {destination}
날짜: {travel_date}
기간: {duration}
선호 카테고리: {", ".join(categories or []) or "특별히 없음"}

카카오맵 위치 정보 JSON:
{json.dumps(compact_places, ensure_ascii=False)}

조건:
- 해당 지역의 인기 관광지를 중심으로 코스를 추천해줘.
- 아래 위치 정보에 있는 장소를 우선 사용하고, 장소가 부족할 때만 해당 지역의 대표 관광지를 보완해줘.
- 같은 장소는 전체 일정에서 딱 한 번만 사용해. 날짜가 달라도 같은 관광지를 반복 방문하게 만들지 마.
- 예: 경복궁을 1일차에 넣었다면 2일차, 3일차, 4일차에는 절대 다시 넣지 마.
- 궁궐, 시장, 전망대, 공원, 거리, 박물관처럼 성격이 다른 장소를 섞어줘.
- 하루 3~4곳 안에서 간결하게 구성해줘.
- 좌표와 주소를 보고 왕복/역주행이 심하지 않도록 가까운 동선끼리 묶어줘.
- 숙소 체크인/식사/휴식 흐름이 자연스럽게 오전, 점심, 오후, 저녁 순서가 되게 해줘.
- 카카오 URL이 있으면 kakao_url에 그대로 넣어줘. 보완한 장소처럼 URL이 없으면 빈 문자열로 둬.
- 사용자가 바로 읽는 화면이므로 내부 점수, API 설명, 관리자용 문구는 쓰지 마.
- JSON 스키마를 정확히 지켜줘.
""".strip()

    request_payload = {
        "model": openai_model(),
        "input": prompt,
        "max_output_tokens": 1800,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "kakao_itinerary",
                "schema": schema,
                "strict": True,
            }
        },
    }
    response = None
    for attempt in range(2):
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=request_payload,
                timeout=(10, 75),
            )
            break
        except requests.exceptions.Timeout as exc:
            if attempt == 1:
                raise RuntimeError("OpenAI 응답이 지연되고 있습니다. 잠시 후 다시 시도하거나 검색어를 더 구체적으로 줄여주세요.") from exc
    if response is None:
        raise RuntimeError("OpenAI 응답을 받지 못했습니다.")
    response.raise_for_status()
    payload = response.json()

    text_parts: list[str] = []
    for item in payload.get("output") or []:
        for content in item.get("content") or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                text_parts.append(content["text"])
    output_text = "\n".join(text_parts).strip()
    if not output_text and payload.get("output_text"):
        output_text = str(payload.get("output_text"))
    if not output_text:
        raise RuntimeError("OpenAI 응답에서 코스 JSON을 찾지 못했습니다.")
    return dedupe_itinerary(json.loads(output_text))
