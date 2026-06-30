# 지역 축제·관광지 맞춤 여행 코스 추천 시스템

Streamlit 화면과 MySQL/MariaDB 데이터베이스를 연결한 DB + 크롤링 프로젝트입니다. HeidiSQL은 DB 생성, 테이블 확인, ERD/관계 확인, SQL 테스트 용도로 사용합니다.

## 프로젝트 포인트

- 공공 관광 데이터 또는 웹 크롤링 결과를 DB에 저장
- 지역, 관광지, 축제, 숙소, 음식점, 카테고리, 회원, 찜, 리뷰, 여행코스를 관계형 DB로 설계
- 회원별 관심 지역과 찜 데이터를 바탕으로 여행 코스 생성
- 축제 기간, 카테고리, 평점, 지역 필터를 활용한 탐색 기능
- 크롤링 성공/실패 이력을 `crawl_logs` 테이블에 저장

## 기술 스택

- Frontend/App: Streamlit
- Language: Python
- DB: MySQL 또는 MariaDB
- DB Client: HeidiSQL
- Crawling/API: requests, BeautifulSoup, 한국관광공사 TourAPI 선택 연동

## 실행 순서

1. MySQL 또는 MariaDB 서버를 실행합니다.
2. HeidiSQL에서 새 세션을 만들고 접속합니다.
3. HeidiSQL에서 `schema.sql` 파일 내용을 실행합니다.
4. Python 패키지를 설치합니다.

```powershell
pip install -r requirements.txt
```

5. DB 접속 정보를 환경 변수로 설정합니다. 수업/발표 환경에서는 `root`보다 전용 계정을 만드는 것을 추천합니다.

```powershell
$env:TRAVEL_DB_HOST="127.0.0.1"
$env:TRAVEL_DB_PORT="3306"
$env:TRAVEL_DB_USER="travel_app"
$env:TRAVEL_DB_PASSWORD="travel1234"
$env:TRAVEL_DB_NAME="travel_course_db"
$env:TRAVEL_DB_AUTH_PLUGIN="mysql_native_password"
$env:TOUR_API_SERVICE_KEY="data.go.kr에서 받은 국문 관광정보 서비스 디코딩 키"
```

6. Streamlit 앱을 실행합니다.

```powershell
streamlit run app.py
```

## HeidiSQL에서 schema.sql 실행하는 법

1. HeidiSQL 실행
2. 왼쪽 세션 목록에서 MySQL/MariaDB 접속
3. 상단 메뉴 `파일` -> `SQL 파일 불러오기` 선택
4. 프로젝트 폴더의 `schema.sql` 선택
5. 쿼리 창에 SQL이 열리면 상단의 파란 실행 버튼 또는 `F9` 실행
6. 왼쪽 DB 목록에서 새로고침
7. `travel_course_db` 데이터베이스가 생겼는지 확인
8. `members`, `regions`, `places`, `festivals`, `travel_courses` 같은 테이블이 보이면 성공

이미 HeidiSQL에서 쿼리를 실행해서 DB가 만들어졌다면, 왼쪽 목록에서 `travel_course_db`가 보이는지 확인하면 됩니다. 안 보이면 왼쪽 패널에서 우클릭 후 `새로고침`을 누르세요.

## HeidiSQL 권장 계정

로컬 DB가 `auth_gssapi_client` 같은 Windows 인증을 요구하면 Python 드라이버가 접속하지 못할 수 있습니다. HeidiSQL에서 관리자 계정으로 접속한 뒤 `heidisql_user.sql`을 한 번 실행하고, 앱은 `travel_app` 계정으로 접속하세요.

```sql
DROP USER IF EXISTS 'travel_app'@'localhost';
DROP USER IF EXISTS 'travel_app'@'127.0.0.1';
CREATE USER 'travel_app'@'localhost' IDENTIFIED BY 'travel1234';
CREATE USER 'travel_app'@'127.0.0.1' IDENTIFIED BY 'travel1234';
ALTER USER 'travel_app'@'localhost'
  IDENTIFIED VIA mysql_native_password USING PASSWORD('travel1234');
ALTER USER 'travel_app'@'127.0.0.1'
  IDENTIFIED VIA mysql_native_password USING PASSWORD('travel1234');
GRANT ALL PRIVILEGES ON travel_course_db.* TO 'travel_app'@'localhost';
GRANT ALL PRIVILEGES ON travel_course_db.* TO 'travel_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

## VisitKorea API 신청/사용 추천

한국관광콘텐츠랩 또는 공공데이터포털에서 신청할 API는 우선 `국문 관광정보 서비스` 하나면 충분합니다. 프로젝트에서는 JSON 응답을 쓰는 방식이 가장 편합니다.

필수로 쓰기 좋은 호출:

| 용도 | API 호출명 | DB 연결 |
| --- | --- | --- |
| 지역 코드 수집 | `areaCode2` | `regions` |
| 관광 카테고리 수집 | `categoryCode2` | `categories` |
| 지역별 관광지 수집 | `areaBasedList2` | `places`, `place_categories` |
| 축제/행사 수집 | `searchFestival2` | `festivals` |
| 상세 설명 수집 | `detailCommon2` | `places.overview`, `festivals.overview` |
| 타입별 상세 정보 | `detailIntro2` | 전화번호, 이용시간, 행사장소, 요금 등 |
| 이미지 수집 | `detailImage2` | 포스터/대표 이미지 확장용 |

추천 `contentTypeId`:

| contentTypeId | 의미 | 프로젝트 활용 |
| --- | --- | --- |
| `12` | 관광지 | 여행지 탐색 |
| `14` | 문화시설 | 박물관/전시/문화 공간 |
| `15` | 행사/공연/축제 | 축제 일정 |
| `25` | 여행코스 | 추천 코스 참고 데이터 |
| `32` | 숙박 | `accommodations` |
| `39` | 음식점 | `restaurants` |

시간이 부족하면 `searchFestival2`, `areaBasedList2`, `detailCommon2` 이 3개만 써도 발표용으로 충분합니다. 더 풍성하게 보이게 하려면 `detailImage2`까지 붙이면 화면 퀄리티가 좋아집니다.

### TourAPI 키 설정

서비스키는 앱 화면에서 직접 입력하지 않습니다. 환경변수나 `.streamlit/secrets.toml`에 아래 이름으로 저장하세요.

```toml
TOUR_API_SERVICE_KEY = "국문 관광정보 서비스 API 키"
```

data.go.kr에서 `Encoding` 키와 `Decoding` 키를 모두 제공하는 경우에는 `Decoding` 키 사용을 권장합니다. 앱은 `%2B` 같은 URL 인코딩 흔적이 있는 키를 한 번 풀어서 요청하므로, 기존에 복사한 인코딩 키도 대부분 그대로 사용할 수 있습니다.

현재 연동된 국문 관광정보 서비스 호출:

- `searchFestival2`: 축제 데이터 수집
- `areaBasedList2`: 지역별 관광지, 문화시설, 음식점, 여행코스 수집

수집된 장소는 기존 `places` 테이블에 저장되고, 유형에 따라 `place_categories`에 `관광지`, `문화시설`, `숙박`, `미식`, `카페`, `자연`, `야간` 같은 카테고리가 연결됩니다. 음식점은 `restaurants`, 숙박은 `accommodations` 테이블에도 함께 저장됩니다.

2026-06-30 전체 수집 실행 결과:

- 장소: 763건
- 축제: 100건
- 합계: 863건
- 대표사진 URL 컬럼 `places.image_url` 추가

## 추가된 맞춤 추천 기능

- `여행지 탐색` 화면에서 여행 스타일, 동행 유형, 예산, 이동수단, 날씨, 여행 시간을 입력해 추천 점수를 계산합니다.
- 평점, 리뷰 수, 선택한 여행 스타일, 날씨 조건, 찜한 카테고리 성향을 합산해 점수 높은 순서로 보여줍니다.
- 각 카드에는 추천 점수, 추천 이유, 태그, 상세 정보, 찜하기, 리뷰 작성, 지도 표시가 함께 노출됩니다.
- `여행 코스 만들기` 화면에는 기존 직접 선택 저장 흐름을 유지하면서, 맞춤 조건 기반 자동 코스 생성 영역을 추가했습니다.
- `내 활동` 화면에서는 찜한 여행지와 찜 카테고리 성향을 확인할 수 있습니다.

추천 점수 계산 방식:

- 여행 스타일과 장소 카테고리/태그/설명이 맞으면 `+30`
- 동행 유형과 맞으면 `+15`
- 비/더움/추움에는 실내 또는 혼합 장소 가중치, 맑음에는 야외 또는 혼합 장소 가중치
- 예산 컬럼이 있고 선택 예산과 맞으면 `+10`
- 평점은 최대 `+40`, 리뷰 수는 최대 `+12`
- 사용자가 많이 찜한 카테고리와 같으면 최대 `+15`

자동 코스 생성 방식:

- 추천 점수가 높은 장소를 먼저 후보로 사용합니다.
- 반나절, 당일치기, 1박 2일에 따라 시간대 개수를 다르게 구성합니다.
- 점심/저녁에는 미식 장소, 카페 시간대에는 카페, 야경 시간대에는 야간/전망/해변 키워드 장소를 우선 배치합니다.
- 장소가 부족하면 남은 추천 후보를 안전하게 채우고, 비어 있으면 안내 메시지만 표시합니다.

## 기존 DB 보강 ALTER TABLE

기존 DB를 삭제하지 않고 추천 기능용 컬럼만 추가하려면 관리자 계정으로 로그인 후 `관리자 SQL` 화면의 `추천용 컬럼 안전 추가` 버튼을 누르거나, HeidiSQL에서 아래 SQL을 실행하세요.

```sql
ALTER TABLE places ADD COLUMN image_url VARCHAR(500) NULL;
ALTER TABLE places ADD COLUMN tags VARCHAR(500) NULL;
ALTER TABLE places ADD COLUMN indoor_outdoor ENUM('실내', '야외', '혼합') NULL;
ALTER TABLE places ADD COLUMN recommended_for VARCHAR(255) NULL;
ALTER TABLE places ADD COLUMN budget_level ENUM('저렴', '보통', '비쌈') NULL;
ALTER TABLE places ADD COLUMN opening_hours VARCHAR(255) NULL;
ALTER TABLE places ADD COLUMN source_api VARCHAR(80) NULL;
```

앱은 위 컬럼이 없어도 `NULL` 기본값으로 처리하도록 작성되어 있으므로, ALTER TABLE을 실행하지 않은 상태에서도 기존 검색과 코스 기능이 중단되지 않습니다.

## 기본 로그인

`schema.sql` 실행 후 아래 계정으로 바로 로그인할 수 있습니다.

- ID: `demo`
- PW: `demo1234`

관리자 계정:

- ID: `admin`
- PW: `admin1234`

## 발표용 15장 구성 예시

1. 프로젝트 소개
2. 선정 배경: 여행 정보 분산 문제
3. 핵심 기능 흐름
4. 사용 기술 스택
5. 전체 시스템 구조
6. 데이터 수집 구조
7. DB ERD
8. 테이블별 역할
9. 주요 관계 설명
10. 크롤링 로그 및 중복 저장 방지
11. 여행지 탐색 화면
12. 여행 코스 생성 화면
13. 찜/리뷰/회원 개인화
14. 테스트 시나리오
15. 개선 방향
