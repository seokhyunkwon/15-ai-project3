# 이번 수정 반영 내용

## 바뀐 점

1. 로그인/회원가입이 페이지 아래에 펼쳐지는 방식이 아니라 Streamlit 모달 창으로 뜨도록 수정했습니다.
2. 검색 결과 출력 순서를 아래 순서로 고정했습니다.
   - 주요 관광지
   - 숙소
   - 식당
   - 축제
   - 추천 코스
3. 로컬에 저장된 `static/images/...` 사진 경로도 정상 표시되도록 수정했습니다.
   - 기존에는 `http://`, `https://` 이미지 주소만 표시해서 로컬 저장 사진이 있어도 안 보였습니다.
4. 주요 관광지, 숙소, 식당, 축제, 추천 코스 카드에 대표 사진을 표시하도록 수정했습니다.
5. 숙소와 식당 이름/버튼을 누르면 네이버 지도 검색 링크로 이동하도록 수정했습니다.
6. 축제 이름/버튼을 누르면 축제 홈페이지 또는 한국관광공사 VisitKorea 검색 링크로 이동하도록 수정했습니다.
7. `collect_approved_apis.py`가 깨져 있던 문제를 수정했습니다.
   - 기존에는 `collector.collect_approved_api_bundle()` 함수가 없어서 실행할 수 없었습니다.
8. 식당/숙소/축제 테이블에 이미지 컬럼이 없을 때 자동으로 추가하는 `ensure_media_schema()`를 추가했습니다.

## 적용 방법

기존 프로젝트에서 아래 파일을 교체하면 됩니다.

- `app.py`
- `database.py`
- `collector.py`
- `course_generator.py`

전체 ZIP을 새 폴더에 풀어서 실행해도 됩니다.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 사진 데이터가 더 필요한 경우

현재 ZIP 안에는 `static/images` 폴더에 이미 수집된 로컬 이미지 파일이 들어 있습니다. 다만 이게 전체 데이터의 끝은 아닙니다.
한국관광공사 TourAPI에서 더 많이 가져오려면 수집 제한 개수를 늘려서 다시 실행하면 됩니다.

PowerShell 예시:

```powershell
$env:TOUR_API_SERVICE_KEY="본인_공공데이터포털_서비스키"
python collector.py --all --limit-per-area 30
```

더 많이 수집하려면 숫자를 올리면 됩니다.

```powershell
$env:TOUR_API_SERVICE_KEY="본인_공공데이터포털_서비스키"
python collector.py --all --limit-per-area 50
```

또는 `.streamlit/secrets.toml`에 키가 이미 있으면 아래처럼 실행해도 됩니다.

```bash
python collect_approved_apis.py
```

주의할 점:

- `--limit-per-area` 값을 크게 하면 데이터와 사진은 더 많이 들어오지만 API 호출 시간이 길어집니다.
- 한국관광공사 데이터 자체에 대표 이미지가 없는 항목은 수집을 다시 해도 사진이 없을 수 있습니다.
- 사진은 DB의 `image_path`, `image_original_url` 컬럼과 `static/images/...` 파일을 기준으로 화면에 표시됩니다.
