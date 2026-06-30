# API 키 설정 안내

`.streamlit/secrets.toml` 파일에 아래처럼 넣으세요.

```toml
TOUR_API_SERVICE_KEY = "한국관광공사_공공데이터포털_서비스키"

# 카카오는 JavaScript 키가 아니라 REST API 키를 넣어야 합니다.
KAKAO_REST_API_KEY = "카카오_REST_API_키"

# 공공데이터포털 키가 같아도 각각 따로 넣어도 됩니다.
KMA_SHORT_FORECAST_SERVICE_KEY = "기상청_단기예보_서비스키"
KMA_MID_FORECAST_SERVICE_KEY = "기상청_중기예보_서비스키"
WEATHER_API_PROVIDER = "KMA"

OPENAI_API_KEY = "OpenAI_API_키"
OPENAI_MODEL = "gpt-4.1-mini"

# 선택 사항: 새로고침 후 로그인 유지용 서명 키
APP_LOGIN_SECRET = "아무_긴_랜덤_문자열"
```

섹션을 쓰고 싶으면 아래처럼 `[api]` 안에 넣어도 이번 수정본에서는 읽습니다.

```toml
[api]
KAKAO_REST_API_KEY = "카카오_REST_API_키"
KMA_SHORT_FORECAST_SERVICE_KEY = "기상청_단기예보_서비스키"
KMA_MID_FORECAST_SERVICE_KEY = "기상청_중기예보_서비스키"
OPENAI_API_KEY = "OpenAI_API_키"
```

주의 사항:

- 카카오 장소 검색은 `KAKAO_REST_API_KEY`를 사용합니다. JavaScript 키를 넣으면 인증 실패가 납니다.
- 기상청/공공데이터포털 키는 `requests.get(..., params=...)` 방식으로 호출하므로 Decoding 인증키가 가장 편합니다. Encoding 인증키를 넣어도 코드에서 한 번 디코딩하도록 보완했습니다.
- 로그인 유지 기능은 `?session=...` 서명 토큰을 URL에 남기는 발표/실습용 방식입니다. 실제 서비스라면 만료시간이 있는 세션 테이블이나 보안 쿠키 방식을 쓰는 것이 더 안전합니다.

## 카카오 403이 뜰 때

`KAKAO_REST_API_KEY`에 JavaScript 키가 아니라 REST API 키를 넣어야 합니다.
그리고 카카오 Developers에서 해당 앱의 `제품 설정 > 카카오맵` 사용 설정이 켜져 있어야 Local API 검색이 됩니다.

## 기상청 중기예보 502가 뜰 때

이번 수정본은 기상청 중기예보 공식 요청 주소인 `http://apis.data.go.kr/...`를 우선 사용하고, 실패하면 `https://apis.data.go.kr/...`도 재시도합니다.
또한 최신 `tmFc`가 서버에 아직 반영되지 않았을 때를 대비해 최근 발표시각 후보를 자동으로 재시도합니다.
그래도 실패하면 공공데이터포털에서 `기상청_단기예보 조회서비스`, `기상청_중기예보 조회서비스`가 모두 활용신청 승인 상태인지 확인하세요.
