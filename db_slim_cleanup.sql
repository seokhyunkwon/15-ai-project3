-- db_slim_cleanup.sql
-- 목적: 현재 사이트 기능에서 쓰지 않는 중복/미사용 테이블을 제거합니다.
-- 기준: 카테고리/지역/사진/축제 날짜/방문자 수/중심 관광지/연관 관광지/집중률/수요·다양성/카카오 장소/기상청 날씨/GPT 교통비 기능은 유지합니다.
-- 실행 전 HeidiSQL에서 DB 백업을 먼저 권장합니다.

USE `travel_course_db`;

SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;

-- 1) 보조 카테고리 연결 테이블 제거
-- restaurants/accommodations/festivals 자체에 cat1/cat2/cat3가 있고,
-- 현재 추천/화면은 places + place_categories 중심으로 동작하므로 별도 연결 테이블은 제거합니다.
DROP TABLE IF EXISTS `accommodation_categories`;
DROP TABLE IF EXISTS `restaurant_categories`;
DROP TABLE IF EXISTS `festival_categories`;

-- 2) 현재 코드에서 사용하지 않는 과거/중복 테이블 제거
DROP TABLE IF EXISTS `search_logs`;
DROP TABLE IF EXISTS `gpt_recommendation_logs`;
DROP TABLE IF EXISTS `popular_places_daily`;
DROP TABLE IF EXISTS `route_estimates`;
DROP TABLE IF EXISTS `weather_forecasts`;
DROP TABLE IF EXISTS `tour_place_features`;

SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;

-- 확인용
SHOW TABLES;
