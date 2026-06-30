-- 지역 검색이 섞여 보이는 기존 수집 데이터를 정리하고 다시 수집하기 위한 SQL입니다.
-- 실행 전 HeidiSQL에서 현재 DB가 맞는지 먼저 확인하세요.
SELECT DATABASE();

-- 1) 지역 코드가 정상적으로 들어갔는지 확인
SELECT region_id, region_name, province, tour_area_code, tour_sigungu_code
FROM regions
WHERE region_name LIKE '%대구%' OR province LIKE '%대구%' OR region_name LIKE '%부산%' OR province LIKE '%부산%'
ORDER BY tour_area_code, tour_sigungu_code, region_id;

-- 2) 주소와 region_id가 섞인 의심 데이터 확인
SELECT p.place_id, p.place_name, p.address, p.region_id, r.region_name, r.province
FROM places p
JOIN regions r ON r.region_id = p.region_id
WHERE p.address LIKE '%대구%'
  AND r.region_name NOT LIKE '%대구%'
  AND r.province NOT LIKE '%대구%';

SELECT rt.restaurant_id, rt.restaurant_name, rt.address, rt.region_id, r.region_name, r.province
FROM restaurants rt
JOIN regions r ON r.region_id = rt.region_id
WHERE rt.address LIKE '%대구%'
  AND r.region_name NOT LIKE '%대구%'
  AND r.province NOT LIKE '%대구%';

SELECT a.accommodation_id, a.accommodation_name, a.address, a.region_id, r.region_name, r.province
FROM accommodations a
JOIN regions r ON r.region_id = a.region_id
WHERE a.address LIKE '%대구%'
  AND r.region_name NOT LIKE '%대구%'
  AND r.province NOT LIKE '%대구%';

-- 3) API로 잘못 들어간 추천 대상 데이터 초기화
-- 회원/지역/카테고리는 유지하고, 관광지/식당/숙소/축제 및 관련 사용자 찜/리뷰/코스만 비웁니다.
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE course_items;
TRUNCATE TABLE travel_courses;
TRUNCATE TABLE favorites;
TRUNCATE TABLE reviews;
TRUNCATE TABLE place_categories;
TRUNCATE TABLE places;
TRUNCATE TABLE restaurants;
TRUNCATE TABLE accommodations;
TRUNCATE TABLE festivals;
SET FOREIGN_KEY_CHECKS = 1;

-- 4) 이후 PowerShell에서 다시 실행
-- python collector.py --service-key "본인키" --regions-only
-- python collector.py --service-key "본인키" --all --limit-per-area 5

-- 5) 재수집 후 검증
SELECT COUNT(*) AS region_count FROM regions;
SELECT COUNT(*) AS place_count FROM places;
SELECT COUNT(*) AS restaurant_count FROM restaurants;
SELECT COUNT(*) AS accommodation_count FROM accommodations;
SELECT COUNT(*) AS festival_count FROM festivals;

SELECT p.place_id, p.place_name, p.address, r.region_name, r.province
FROM places p
JOIN regions r ON r.region_id = p.region_id
WHERE r.region_name LIKE '%대구%' OR r.province LIKE '%대구%'
ORDER BY p.place_id DESC
LIMIT 30;
