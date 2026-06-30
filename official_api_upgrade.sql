USE travel_course_db;

-- 공식 API로 설명 가능한 기능을 저장하기 위한 컬럼/테이블 추가
-- 카테고리 기반 추천, 지역 기반 추천, 사진 우선, 축제 날짜, 요금 일부,
-- 방문자 수, 중심 관광지, 연관 관광지, 집중률/혼잡도, 관광 수요/다양성,
-- 카카오맵 실시간 검색, 날씨, GPT 교통비 추정 저장용입니다.

DROP PROCEDURE IF EXISTS add_column_if_missing;
DELIMITER //
CREATE PROCEDURE add_column_if_missing(
  IN p_table_name VARCHAR(64),
  IN p_column_name VARCHAR(64),
  IN p_column_def TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = p_table_name
      AND COLUMN_NAME = p_column_name
  ) THEN
    SET @sql_text = CONCAT('ALTER TABLE `', p_table_name, '` ADD COLUMN ', p_column_def);
    PREPARE stmt FROM @sql_text;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END//
DELIMITER ;

-- 장소 공식 필드
CALL add_column_if_missing('places', 'content_type_id', '`content_type_id` VARCHAR(20) NULL COMMENT ''TourAPI contenttypeid''');
CALL add_column_if_missing('places', 'content_type_name', '`content_type_name` VARCHAR(80) NULL COMMENT ''TourAPI 콘텐츠 타입명''');
CALL add_column_if_missing('places', 'cat1', '`cat1` VARCHAR(80) NULL COMMENT ''TourAPI 대분류''');
CALL add_column_if_missing('places', 'cat2', '`cat2` VARCHAR(80) NULL COMMENT ''TourAPI 중분류''');
CALL add_column_if_missing('places', 'cat3', '`cat3` VARCHAR(80) NULL COMMENT ''TourAPI 소분류''');
CALL add_column_if_missing('places', 'lcls_systm1', '`lcls_systm1` VARCHAR(100) NULL COMMENT ''TourAPI 분류체계1''');
CALL add_column_if_missing('places', 'lcls_systm2', '`lcls_systm2` VARCHAR(100) NULL COMMENT ''TourAPI 분류체계2''');
CALL add_column_if_missing('places', 'lcls_systm3', '`lcls_systm3` VARCHAR(100) NULL COMMENT ''TourAPI 분류체계3''');
CALL add_column_if_missing('places', 'use_fee', '`use_fee` VARCHAR(500) NULL COMMENT ''TourAPI 상세정보 이용요금/이용안내''');
CALL add_column_if_missing('places', 'parking_fee', '`parking_fee` VARCHAR(255) NULL COMMENT ''TourAPI 주차요금/주차안내''');
CALL add_column_if_missing('places', 'has_tour_image', '`has_tour_image` BOOLEAN NOT NULL DEFAULT FALSE COMMENT ''TourAPI 대표이미지 보유 여부''');
CALL add_column_if_missing('places', 'photo_priority_score', '`photo_priority_score` DECIMAL(8,2) NOT NULL DEFAULT 0 COMMENT ''사진 우선 노출 점수''');
CALL add_column_if_missing('places', 'detail_common_json', '`detail_common_json` LONGTEXT NULL COMMENT ''TourAPI detailCommon 원본 JSON''');
CALL add_column_if_missing('places', 'detail_intro_json', '`detail_intro_json` LONGTEXT NULL COMMENT ''TourAPI detailIntro 원본 JSON''');
CALL add_column_if_missing('places', 'detail_info_json', '`detail_info_json` LONGTEXT NULL COMMENT ''TourAPI detailInfo 원본 JSON''');
CALL add_column_if_missing('places', 'tour_api_updated_at', '`tour_api_updated_at` DATETIME NULL COMMENT ''TourAPI 상세정보 갱신 시각''');

-- 축제 공식 필드
CALL add_column_if_missing('festivals', 'content_type_id', '`content_type_id` VARCHAR(20) NULL COMMENT ''TourAPI contenttypeid''');
CALL add_column_if_missing('festivals', 'content_type_name', '`content_type_name` VARCHAR(80) NULL COMMENT ''TourAPI 콘텐츠 타입명''');
CALL add_column_if_missing('festivals', 'cat1', '`cat1` VARCHAR(80) NULL COMMENT ''TourAPI 대분류''');
CALL add_column_if_missing('festivals', 'cat2', '`cat2` VARCHAR(80) NULL COMMENT ''TourAPI 중분류''');
CALL add_column_if_missing('festivals', 'cat3', '`cat3` VARCHAR(80) NULL COMMENT ''TourAPI 소분류''');
CALL add_column_if_missing('festivals', 'event_place', '`event_place` VARCHAR(255) NULL COMMENT ''TourAPI 행사장소''');
CALL add_column_if_missing('festivals', 'playtime', '`playtime` VARCHAR(255) NULL COMMENT ''TourAPI 행사시간''');
CALL add_column_if_missing('festivals', 'sponsor', '`sponsor` VARCHAR(255) NULL COMMENT ''TourAPI 주최/주관''');
CALL add_column_if_missing('festivals', 'detail_intro_json', '`detail_intro_json` LONGTEXT NULL COMMENT ''TourAPI detailIntro 원본 JSON''');

-- 식당 공식 필드. 평균 식사가격이 아니라 공식 메뉴/영업/주차 정보만 저장합니다.
CALL add_column_if_missing('restaurants', 'phone', '`phone` VARCHAR(80) NULL COMMENT ''TourAPI 전화번호''');
CALL add_column_if_missing('restaurants', 'source_url', '`source_url` VARCHAR(500) NULL COMMENT ''공식/검색 정보 URL''');
CALL add_column_if_missing('restaurants', 'external_id', '`external_id` VARCHAR(80) NULL COMMENT ''TourAPI contentid''');
CALL add_column_if_missing('restaurants', 'content_type_id', '`content_type_id` VARCHAR(20) NULL COMMENT ''TourAPI contenttypeid''');
CALL add_column_if_missing('restaurants', 'content_type_name', '`content_type_name` VARCHAR(80) NULL COMMENT ''TourAPI 콘텐츠 타입명''');
CALL add_column_if_missing('restaurants', 'cat1', '`cat1` VARCHAR(80) NULL COMMENT ''TourAPI 대분류''');
CALL add_column_if_missing('restaurants', 'cat2', '`cat2` VARCHAR(80) NULL COMMENT ''TourAPI 중분류''');
CALL add_column_if_missing('restaurants', 'cat3', '`cat3` VARCHAR(80) NULL COMMENT ''TourAPI 소분류''');
CALL add_column_if_missing('restaurants', 'first_menu', '`first_menu` VARCHAR(255) NULL COMMENT ''TourAPI 대표메뉴''');
CALL add_column_if_missing('restaurants', 'treat_menu', '`treat_menu` VARCHAR(500) NULL COMMENT ''TourAPI 취급메뉴''');
CALL add_column_if_missing('restaurants', 'open_time', '`open_time` VARCHAR(255) NULL COMMENT ''TourAPI 영업시간''');
CALL add_column_if_missing('restaurants', 'rest_date', '`rest_date` VARCHAR(255) NULL COMMENT ''TourAPI 쉬는날''');
CALL add_column_if_missing('restaurants', 'parking_info', '`parking_info` VARCHAR(255) NULL COMMENT ''TourAPI 주차정보''');
CALL add_column_if_missing('restaurants', 'detail_intro_json', '`detail_intro_json` LONGTEXT NULL COMMENT ''TourAPI detailIntro 원본 JSON''');

-- 숙소 공식 필드. 실제 숙박요금이 아니라 공식 체크인/체크아웃/예약/객실/주차 정보만 저장합니다.
CALL add_column_if_missing('accommodations', 'source_url', '`source_url` VARCHAR(500) NULL COMMENT ''공식/검색 정보 URL''');
CALL add_column_if_missing('accommodations', 'external_id', '`external_id` VARCHAR(80) NULL COMMENT ''TourAPI contentid''');
CALL add_column_if_missing('accommodations', 'content_type_id', '`content_type_id` VARCHAR(20) NULL COMMENT ''TourAPI contenttypeid''');
CALL add_column_if_missing('accommodations', 'content_type_name', '`content_type_name` VARCHAR(80) NULL COMMENT ''TourAPI 콘텐츠 타입명''');
CALL add_column_if_missing('accommodations', 'cat1', '`cat1` VARCHAR(80) NULL COMMENT ''TourAPI 대분류''');
CALL add_column_if_missing('accommodations', 'cat2', '`cat2` VARCHAR(80) NULL COMMENT ''TourAPI 중분류''');
CALL add_column_if_missing('accommodations', 'cat3', '`cat3` VARCHAR(80) NULL COMMENT ''TourAPI 소분류''');
CALL add_column_if_missing('accommodations', 'checkin_time', '`checkin_time` VARCHAR(120) NULL COMMENT ''TourAPI 체크인''');
CALL add_column_if_missing('accommodations', 'checkout_time', '`checkout_time` VARCHAR(120) NULL COMMENT ''TourAPI 체크아웃''');
CALL add_column_if_missing('accommodations', 'room_count', '`room_count` VARCHAR(120) NULL COMMENT ''TourAPI 객실 수''');
CALL add_column_if_missing('accommodations', 'reservation_url', '`reservation_url` VARCHAR(500) NULL COMMENT ''TourAPI 예약 URL''');
CALL add_column_if_missing('accommodations', 'parking_info', '`parking_info` VARCHAR(255) NULL COMMENT ''TourAPI 주차정보''');
CALL add_column_if_missing('accommodations', 'detail_intro_json', '`detail_intro_json` LONGTEXT NULL COMMENT ''TourAPI detailIntro 원본 JSON''');


CREATE TABLE IF NOT EXISTS live_kakao_places (
  kakao_place_id VARCHAR(80) PRIMARY KEY,
  region_name VARCHAR(80) NULL,
  keyword VARCHAR(120) NULL,
  place_name VARCHAR(180) NOT NULL,
  category_name VARCHAR(255) NULL,
  address_name VARCHAR(255) NULL,
  road_address_name VARCHAR(255) NULL,
  phone VARCHAR(80) NULL,
  place_url VARCHAR(500) NULL,
  latitude DECIMAL(10, 7) NULL,
  longitude DECIMAL(10, 7) NULL,
  raw_json LONGTEXT NULL,
  fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_live_kakao_region (region_name),
  INDEX idx_live_kakao_keyword (keyword)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS weather_cache (
  weather_id INT AUTO_INCREMENT PRIMARY KEY,
  region_name VARCHAR(80) NULL,
  target_date DATE NULL,
  latitude DECIMAL(10, 7) NULL,
  longitude DECIMAL(10, 7) NULL,
  weather_source VARCHAR(40) NULL,
  condition_text VARCHAR(120) NULL,
  temp DECIMAL(6, 2) NULL,
  feels_like DECIMAL(6, 2) NULL,
  humidity DECIMAL(6, 2) NULL,
  wind_speed DECIMAL(6, 2) NULL,
  raw_json LONGTEXT NULL,
  fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_weather_region_date (region_name, target_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transport_estimates (
  estimate_id INT AUTO_INCREMENT PRIMARY KEY,
  origin_text VARCHAR(180) NOT NULL,
  destination_text VARCHAR(180) NOT NULL,
  travel_date DATE NULL,
  people INT NOT NULL DEFAULT 1,
  provider VARCHAR(40) NOT NULL DEFAULT 'openai',
  estimate_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_transport_route (origin_text, destination_text, travel_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP PROCEDURE IF EXISTS add_column_if_missing;

SELECT 'official api upgrade complete' AS result_message;
