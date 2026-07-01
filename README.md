# Travel Course Recommendation

Streamlit + MySQL/MariaDB 기반 여행 코스 추천 프로젝트입니다. 한국관광공사 TourAPI 데이터를 수집해 관광지, 식당, 숙소, 축제 정보를 DB에 저장하고, 저장된 이미지와 추천 점수를 화면에 표시합니다.

## Tech Stack

- App: Streamlit
- Language: Python
- Database: MySQL or MariaDB
- Data source: 한국관광공사 TourAPI, 관광사진 정보 API
- Main scripts:
  - `app.py`: Streamlit 앱
  - `collector.py`: TourAPI 전체 수집
  - `backfill_missing_images.py`: 대표 이미지가 비어 있는 관광지 보강
  - `schema.sql`: 초기 DB 스키마
  - `heidisql_user.sql`: 로컬 DB 사용자 생성 예시

## Setup

1. MySQL 또는 MariaDB를 실행합니다.
2. HeidiSQL 등 DB 클라이언트에서 DB와 사용자를 준비합니다.
   - 새 환경이면 `heidisql_user.sql`을 먼저 실행합니다.
   - 그 다음 `schema.sql`을 실행해 테이블을 생성합니다.
3. Python 패키지를 설치합니다.

```powershell
pip install -r requirements.txt
```

4. 환경변수를 설정합니다.

```powershell
$env:TRAVEL_DB_HOST="127.0.0.1"
$env:TRAVEL_DB_PORT="3306"
$env:TRAVEL_DB_USER="travel_app"
$env:TRAVEL_DB_PASSWORD="travel1234"
$env:TRAVEL_DB_NAME="travel_course_db"
$env:TRAVEL_DB_AUTH_PLUGIN="mysql_native_password"
$env:TOUR_API_SERVICE_KEY="공공데이터포털_TourAPI_서비스키"
```

`.streamlit/secrets.toml`에 넣어도 됩니다. 이 파일은 커밋하지 않습니다.

```toml
TOUR_API_SERVICE_KEY = "공공데이터포털_TourAPI_서비스키"
```

5. 앱을 실행합니다.

```powershell
streamlit run app.py
```

## Data Collection

전체 데이터 수집:

```powershell
$env:TOUR_API_KEY="공공데이터포털_TourAPI_서비스키"
python collector.py --all --limit-per-area 50
```

`--limit-per-area 50`은 광역 지역별 50개까지만 가져오는 빠른 수집입니다. TourAPI에 있는 항목을 끝까지 수집하려면 아래처럼 `0`을 사용합니다.

```powershell
$env:TOUR_API_KEY="공공데이터포털_TourAPI_서비스키"
python collector.py --all --limit-per-area 0
```

`--limit-per-area 0`은 시군구를 순회하고 페이지를 끝까지 넘기므로 수집 시간, API 호출량, 이미지 용량이 크게 늘어납니다. 공공데이터포털 일 호출 제한이 있다면 여러 날에 나눠 실행하세요. 수집 순서는 대략 관광지, 식당, 숙소, 축제 순서입니다.

식당과 숙소는 그대로 두고, 관광지가 비어 있는 지역과 축제만 추가 수집:

```powershell
$env:TOUR_API_KEY="공공데이터포털_TourAPI_서비스키"
python collect_missing_places_and_festivals.py --place-limit-per-region 50 --festival-limit 100
```

관광지가 비어 있는 지역을 끝까지 채우고 축제도 전체 수집하려면:

```powershell
$env:TOUR_API_KEY="공공데이터포털_TourAPI_서비스키"
python collect_missing_places_and_festivals.py --place-limit-per-region 0 --festival-limit 0
```

먼저 대상만 확인하려면 `--dry-run`을 붙입니다.

대표 이미지가 비어 있는 관광지는 전체 수집이 끝난 뒤 별도 백필 스크립트로 보강합니다.

```powershell
python backfill_missing_images.py --limit 20 --dry-run
python backfill_missing_images.py --limit 0
```

백필 순서:

1. `places.external_id`를 TourAPI `contentId`로 보고 `detailImage2` 조회
2. 그래도 이미지가 없으면 지역명/관광지명 키워드로 `PhotoGalleryService1/gallerySearchList1` 조회
3. 찾은 이미지는 `static/images/places`에 저장하고 DB의 `places.image_path`, `places.image_original_url`을 채움
4. 관광사진 API 결과는 `tour_photos`에도 저장

## DB Export And Restore

수집한 DB 데이터는 Git에 자동으로 들어가지 않습니다. 다른 PC에서 같은 데이터를 쓰려면 SQL dump를 만들어 커밋하거나 별도로 전달해야 합니다.

예시:

```powershell
mysqldump -u travel_app -p --default-character-set=utf8mb4 travel_course_db > travel_course_db_dump.sql
```

다른 PC에서 복원:

```powershell
mysql -u travel_app -p --default-character-set=utf8mb4 travel_course_db < travel_course_db_dump.sql
```

HeidiSQL을 사용한다면 `도구` 또는 우클릭 메뉴의 SQL 내보내기/가져오기로 같은 작업을 할 수 있습니다.

## Image Assets And GitHub Release

이미지 파일은 용량이 커서 Git 커밋 대상에서 제외합니다.

현재 `.gitignore` 정책:

```gitignore
static/images/
release-assets/
*.zip
```

이미지는 압축해서 GitHub Release asset으로 올립니다. Repo에는 코드와 SQL dump만 커밋하고, `static/images` 압축 파일은 Release에 첨부합니다.

압축:

```powershell
New-Item -ItemType Directory -Force release-assets
Compress-Archive -Path .\static -DestinationPath .\release-assets\static-images-2026-07-01.zip -CompressionLevel Optimal -Force
```

다른 PC에서 복원:

```powershell
Expand-Archive .\static-images-2026-07-01.zip -DestinationPath . -Force
```

압축 파일 안에 `static/images/...` 구조가 들어가야 앱에서 DB의 `image_path`와 맞습니다.

권장 release 흐름:

1. 수집 완료
2. DB SQL dump 생성
3. `static/images` 압축
4. 코드 + SQL dump 커밋
5. 브랜치 push
6. GitHub Release 생성
7. 이미지 zip을 Release asset으로 첨부

백필을 나중에 실행했다면 DB와 이미지가 다시 바뀌므로 SQL dump와 이미지 zip도 다시 만들어야 합니다.

## Git Workflow

임시 보존용 release와 최종 release를 분리하면 안전합니다.

- 수집 직후: `v-data-prebackfill-YYYY-MM-DD`
- 백필 후 최종본: `v-data-final-YYYY-MM-DD`

Release는 브랜치가 아니라 태그에 붙습니다. `sh` 브랜치 기준으로 임시 release를 만들어도 나중에 `develop` 또는 `main`에 merge할 수 있습니다. 최종 배포용 release는 merge 이후 `develop` 또는 `main` 최신 커밋 기준으로 새로 만드는 것을 권장합니다.

## Default Accounts

`schema.sql` 초기 데이터 기준:

- User: `demo` / `demo1234`
- Admin: `admin` / `admin1234`

## Notes

- API 키와 DB 비밀번호는 커밋하지 않습니다.
- 채팅, 캡처, 발표 자료에 실제 API 키가 노출되면 재발급을 고려합니다.
- `static/images`를 커밋하지 않기 때문에 다른 PC에서는 반드시 Release zip을 받아 압축 해제해야 사진이 보입니다.
- DB만 복원하고 이미지를 풀지 않으면 화면에는 이미지 경로만 있고 실제 사진은 표시되지 않습니다.
