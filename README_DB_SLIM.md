# DB 슬림화 정리본

`pj3.sql` 기준으로 실제 현재 사이트 기능에 필요한 테이블은 남기고, 중복이거나 현재 코드에서 사용하지 않는 테이블만 제거했습니다.

## 삭제 대상

- `accommodation_categories`, `restaurant_categories`, `festival_categories`
  - 보조 카테고리 연결 테이블입니다.
  - 현재 추천/검색은 `places` + `place_categories` 기준이고, 숙소/식당/축제 테이블에는 `cat1`, `cat2`, `cat3` 공식 분류 컬럼이 이미 있어서 중복입니다.
- `search_logs`
  - 현재 코드에서 검색 로그 저장 기능을 사용하지 않습니다.
- `gpt_recommendation_logs`
  - 이전 GPT 추천 로그용입니다. 현재 교통편/금액 계산은 `transport_estimates`를 사용합니다.
- `popular_places_daily`
  - 현재 인기/방문자 관련 설명은 관광공사 API 테이블을 사용합니다.
- `route_estimates`
  - 이전 교통 추정 테이블입니다. 현재는 `transport_estimates`를 사용합니다.
- `weather_forecasts`
  - 이전 날씨 테이블입니다. 현재 기상청 단기/중기 조회 캐시는 `weather_cache`를 사용합니다.
- `tour_place_features`
  - 범용 특징 테이블이지만 현재 수집/추천 코드에서 실제 저장하지 않아 제거했습니다.

## 유지 대상

- `places`, `restaurants`, `accommodations`, `festivals`
- `regions`, `categories`, `place_categories`
- `tour_photos`
- `region_visitor_stats`
- `center_attractions`
- `related_attractions`
- `attraction_concentration`
- `regional_demand_metrics`
- `live_kakao_places`
- `weather_cache`
- `transport_estimates`
- `tour_api_usage_logs`, `crawl_logs`
- `members`, `favorites`, `reviews`, `travel_courses`, `course_items`

## 적용 순서

1. HeidiSQL에서 DB 백업
2. `db_slim_cleanup.sql` 실행
3. 수정 파일을 프로젝트에 덮어쓰기
4. `streamlit run app.py`
