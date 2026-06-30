# 한국관광공사 API 적용 내역

이 프로젝트는 사용자가 사이트 화면에서 API 키를 입력하지 않습니다. 8개 API는 모두 같은 `TOUR_API_SERVICE_KEY`를 `.streamlit/secrets.toml` 또는 환경변수에서 읽어 사용합니다.

앱 실행은 아래처럼 합니다. 앱 화면에는 데이터 수집 탭이나 API 키 입력창을 두지 않습니다.

```powershell
streamlit run app.py
```

데이터 수집만 실행하려면 다음 스크립트를 사용합니다.

```powershell
python collect_approved_apis.py
```

수집 결과와 실패 내역은 `tour_api_usage_logs` 테이블에 저장됩니다. API 응답이 비어 있거나 특정 컬럼이 없어도 앱이 중단되지 않도록 원본 JSON은 보조 테이블의 `raw_json`에 함께 저장합니다.

## 1. 국문 관광정보 서비스

- 공식명: 한국관광공사_국문 관광정보 서비스_GW
- 공공데이터포털 ID: `15101578`
- 코드 위치: `collector.collect_tourapi_full_dataset()`, `collector.fetch_tourapi_area_places()`, `collector.fetch_tourapi_festivals()`
- 주요 호출: `areaBasedList2`, `searchFestival2`
- 가져오는 데이터: 지역별 관광지, 문화시설, 여행코스, 숙박, 음식점, 축제/행사, 대표 이미지 URL, 주소, 좌표, 전화번호, 콘텐츠 ID
- 저장 위치: `places`, `place_categories`, `restaurants`, `accommodations`, `festivals`
- 추천 반영: 검색 후보의 기본 데이터입니다. 카테고리, 지역, 대표사진, 주소, 숙박/음식점 추천에 직접 사용합니다.

## 2. 관광사진 정보

- 공식명: 한국관광공사_관광사진 정보_GW
- 공공데이터포털 ID: `15101914`
- 코드 위치: `collector.fetch_tour_photos()`, `collector._save_tour_photos()`
- 주요 호출 후보: `PhotoGalleryService1/gallerySearchList1`, `PhotoGalleryService1/galleryList1`
- 가져오는 데이터: 사진 제목, 웹 이미지 URL, 촬영지, 촬영자, 촬영월/촬영일, 키워드, 사진 콘텐츠 ID
- 저장 위치: `tour_photos`
- 추천 반영: 결과 요약의 관광사진 저장 건수로 표시합니다. 장소 카드의 대표 이미지는 우선 국문 관광정보의 `firstimage`를 쓰고, 관광사진은 보조 이미지 데이터로 분리 저장합니다.

## 3. 빅데이터 지역별 방문자수

- 공식명: 한국관광공사_빅데이터_지역별 방문자수_GW
- 공공데이터포털 ID: `15101972`
- 코드 위치: `collector._save_visitor_rows()`, `database.api_insights_for_trip()`
- 주요 호출 후보: `DataLabService/metcoRegnVisitrDDList`, `DataLabService/locgoRegnVisitrDDList`, `DataLabService/metcoRegnVisitrMMList`
- 가져오는 데이터: 광역/기초지자체명, 기준일 또는 기준월, 방문자 유형, 방문자 수
- 저장 위치: `region_visitor_stats`
- 추천 반영: 검색 결과 상단의 공공데이터 요약에 해당 지역의 최근 방문자 수를 표시합니다.
- 해석 주의: 방문자수는 이동통신 기반 추정값이며 관광객 수와 완전히 동일하지 않습니다.

## 4. 관광지 집중률 방문자 추이 예측

- 공식명: 한국관광공사_관광지 집중률 방문자 추이 예측 정보
- 공공데이터포털 ID: `15128555`
- 코드 위치: `collector._save_concentration_rows()`, `database.api_score_lookup()`
- 주요 호출 후보: `TatsCnctrService1/tatsCnctrList`, `TatsCnctrService/tatsCnctrList`, `TatsCnctrService1/getTatsCnctrList`
- 가져오는 데이터: 관광지명, 지역명, 기준일, 예측일, 집중률/혼잡도 상대 점수
- 저장 위치: `attraction_concentration`
- 추천 반영: 후보 장소와 관광지명이 일치하고 집중률이 낮으면 소폭 가산합니다. 집중률이 높으면 점수 가산보다 혼잡도 확인 사유로만 사용합니다.

## 5. 관광지별 연관 관광지 정보

- 공식명: 한국관광공사_관광지별 연관 관광지 정보
- 공공데이터포털 ID: `15128560`
- 코드 위치: `collector._save_related_rows()`, `database.api_score_lookup()`
- 주요 호출 후보: `TarRlteService1/tarRlteList`, `TatsRlteService1/tatsRlteList`, `TarRlteService1/getTarRlteList`
- 가져오는 데이터: 기준 관광지명, 연관 관광지명, 연관 유형, 순위, 연결성 점수 또는 내비게이션 집계값
- 저장 위치: `related_attractions`
- 추천 반영: 후보 장소가 연관 관광지 데이터에 포함되면 코스 연결성이 있는 장소로 소폭 가산합니다. 결과 요약에도 대표 연관 관광지를 표시합니다.

## 6. 기초지자체 중심 관광지 정보

- 공식명: 한국관광공사_기초지자체 중심 관광지 정보
- 공공데이터포털 ID: `15128559`
- 코드 위치: `collector._save_center_rows()`, `database.api_score_lookup()`
- 주요 호출 후보: `LocgoHubService1/locgoHubList`, `LocgoHubService/locgoHubList`, `LocgoHubService1/getLocgoHubList`
- 가져오는 데이터: 지역명, 중심 관광지명, 중심 관광지 순위, 내비게이션 검색/이동 기반 집계값
- 저장 위치: `center_attractions`
- 추천 반영: 후보 장소가 중심 관광지에 포함되면 순위가 높을수록 추천 점수를 소폭 가산합니다.

## 7. 지역별 관광 다양성

- 공식명: 한국관광공사_지역별 관광 다양성
- 공공데이터포털 ID: `15151365`
- 코드 위치: `collector._save_regional_metric_rows()`, `database.api_insights_for_trip()`
- 주요 호출 후보: `DemandDvrstService1/demandDvrstList`, `DmandDvrstService1/dmandDvrstList`, `DemandDvrstService1/getDemandDvrstList`
- 가져오는 데이터: 지역별 관광객 다양성, 관광소비 다양성, 국제적 다양성 관련 수치 지표
- 저장 위치: `regional_demand_metrics` (`source_api = DMANDDVRST`)
- 추천 반영: 지역 요약 지표로 표시합니다. 현재는 장소별 직접 가산보다 지역의 여행 수요 특성을 설명하는 보조 데이터로 사용합니다.

## 8. 지역별 관광 자원 수요

- 공식명: 한국관광공사_지역별 관광 자원 수요
- 공공데이터포털 ID: `15152138`
- 코드 위치: `collector._save_regional_metric_rows()`, `database.api_insights_for_trip()`
- 주요 호출 후보: `DemandResrService1/demandResrList`, `DmandResrService1/dmandResrList`, `DemandResrService1/getDemandResrList`
- 가져오는 데이터: 지역별 관광 서비스 수요, 문화 자원 수요, SNS 언급량, 관광 소비액, 내비게이션 목적지 검색량 계열의 수치 지표
- 저장 위치: `regional_demand_metrics` (`source_api = DMANDRESR`)
- 추천 반영: 검색 결과의 공공데이터 요약에 주요 지표명을 보여주고, 향후 지역별 수요가 높은 카테고리를 더 강하게 가산하는 데 사용할 수 있습니다.

## 추천 점수 연결 방식

- 기본 점수: 여행 카테고리, 여행 스타일, 동행, 날씨, 예산, 평점, 리뷰 수, 찜 카테고리로 계산합니다.
- 중심 관광지 API: 장소명이 중심 관광지와 일치하면 최대 약 18점 안쪽에서 가산합니다.
- 연관 관광지 API: 장소명이 기준/연관 관광지와 일치하면 코스 연결성 사유와 함께 가산합니다.
- 집중률 API: 집중률이 낮은 장소는 일정에 넣기 부담이 적은 장소로 소폭 가산합니다.
- 방문자수/다양성/자원수요 API: 장소별 직접 점수보다 지역 요약과 추천 설명 보강에 사용합니다.

## DB 방어 처리

- `app.py` 시작 시 `database.ensure_recommendation_schema()`와 `database.ensure_advanced_api_schema()`를 호출합니다.
- 컬럼이나 테이블이 없으면 가능한 범위에서 추가하고, 실패하면 앱을 멈추지 않습니다.
- 조회 함수는 테이블이 없거나 데이터가 비어 있어도 빈 리스트/기본값을 반환합니다.
- API 수집 실패는 화면 오류가 아니라 `tour_api_usage_logs`에 실패 로그로 남깁니다.
