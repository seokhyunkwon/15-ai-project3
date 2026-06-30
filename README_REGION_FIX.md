# 지역 검색 오류 수정 안내

이번 수정은 `대구`로 검색했을 때 `부산` 결과가 섞여 보이는 문제를 막기 위한 수정입니다.

## 수정 내용

1. `database.py`
   - 지역 필터에서 `address LIKE '%대구%'`를 제거했습니다.
   - 이제 지역 검색은 반드시 `regions.region_name`, `regions.province` 기준으로만 필터링합니다.
   - 선택 지역 결과가 없을 때 전국 결과로 자동 대체하지 않도록 `app.py`도 수정했습니다.

2. `collector.py`
   - `region_id` 고정값을 쓰지 않고 TourAPI `areaCode`, `sigunguCode`를 기준으로 DB의 실제 `regions.region_id`를 조회합니다.
   - 수집 실행 시 필요한 컬럼과 N:M 카테고리 테이블을 자동 보강합니다.

3. `schema.sql`
   - 새로 DB를 만드는 경우에도 `tour_area_code`, `tour_sigungu_code`, 이미지 경로 컬럼, N:M 카테고리 테이블이 생성되도록 보강했습니다.

## 적용 순서

PowerShell:

```powershell
cd C:\Users\Win11Pro\Documents\travel
streamlit run app.py
```

수집 재실행:

```powershell
python collector.py --service-key "본인키" --regions-only
python collector.py --service-key "본인키" --all --limit-per-area 5
```

이미 잘못 들어간 데이터가 있으면 HeidiSQL에서 `region_cleanup_and_resync.sql`을 실행한 뒤 재수집하세요.

## 중요

서비스키가 노출된 적이 있으면 공공데이터포털에서 재발급 후 `.streamlit/secrets.toml` 또는 환경변수에 새 키를 넣으세요.
