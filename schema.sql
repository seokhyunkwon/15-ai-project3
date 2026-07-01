CREATE DATABASE IF NOT EXISTS travel_course_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE travel_course_db;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS course_items;
DROP TABLE IF EXISTS travel_courses;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS place_categories;
DROP TABLE IF EXISTS festivals;
DROP TABLE IF EXISTS restaurants;
DROP TABLE IF EXISTS accommodations;
DROP TABLE IF EXISTS places;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS crawl_logs;
DROP TABLE IF EXISTS regional_demand_metrics;
DROP TABLE IF EXISTS center_attractions;
DROP TABLE IF EXISTS related_attractions;
DROP TABLE IF EXISTS attraction_concentration;
DROP TABLE IF EXISTS region_visitor_stats;
DROP TABLE IF EXISTS tour_photos;
DROP TABLE IF EXISTS tour_api_usage_logs;
DROP TABLE IF EXISTS members;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE members (
  member_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash CHAR(64) NOT NULL,
  name VARCHAR(50) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  preferred_region_id INT NULL,
  role ENUM('USER', 'ADMIN') NOT NULL DEFAULT 'USER',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE regions (
  region_id INT AUTO_INCREMENT PRIMARY KEY,
  region_name VARCHAR(80) NOT NULL UNIQUE,
  province VARCHAR(50) NOT NULL,
  description VARCHAR(255) NULL,
  tour_area_code VARCHAR(10) NULL,
  tour_sigungu_code VARCHAR(10) NULL,
  kakao_keyword VARCHAR(100) NULL,
  INDEX idx_regions_tour_code (tour_area_code, tour_sigungu_code)
) ENGINE=InnoDB;

CREATE TABLE categories (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  category_name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(255) NULL
) ENGINE=InnoDB;

CREATE TABLE places (
  place_id INT AUTO_INCREMENT PRIMARY KEY,
  region_id INT NOT NULL,
  place_name VARCHAR(120) NOT NULL,
  address VARCHAR(255) NULL,
  overview TEXT NULL,
  phone VARCHAR(50) NULL,
  latitude DECIMAL(10, 7) NULL,
  longitude DECIMAL(10, 7) NULL,
  source_url VARCHAR(500) NULL,
  external_id VARCHAR(80) NULL,
  average_rating DECIMAL(3, 2) NOT NULL DEFAULT 0.00,
  image_url VARCHAR(500) NULL,
  image_path VARCHAR(500) NULL,
  image_original_url VARCHAR(1000) NULL,
  image_saved_at DATETIME NULL,
  tags VARCHAR(500) NULL,
  opening_hours VARCHAR(255) NULL,
  source_api VARCHAR(80) NULL,
  content_type_id VARCHAR(20) NULL,
  content_type_name VARCHAR(80) NULL,
  cat1 VARCHAR(80) NULL,
  cat2 VARCHAR(80) NULL,
  cat3 VARCHAR(80) NULL,
  lcls_systm1 VARCHAR(100) NULL,
  lcls_systm2 VARCHAR(100) NULL,
  lcls_systm3 VARCHAR(100) NULL,
  use_fee VARCHAR(500) NULL,
  parking_fee VARCHAR(255) NULL,
  has_tour_image BOOLEAN NOT NULL DEFAULT FALSE,
  photo_priority_score DECIMAL(8, 2) NOT NULL DEFAULT 0,
  detail_common_json LONGTEXT NULL,
  detail_intro_json LONGTEXT NULL,
  detail_info_json LONGTEXT NULL,
  tour_api_updated_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_places_regions FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT uq_places_region_name UNIQUE (region_id, place_name),
  INDEX idx_places_region (region_id),
  INDEX idx_places_external (external_id)
) ENGINE=InnoDB;

CREATE TABLE festivals (
  festival_id INT AUTO_INCREMENT PRIMARY KEY,
  region_id INT NOT NULL,
  place_id INT NULL,
  festival_name VARCHAR(150) NOT NULL,
  start_date DATE NULL,
  end_date DATE NULL,
  fee_info VARCHAR(255) NULL,
  homepage VARCHAR(500) NULL,
  overview TEXT NULL,
  source_url VARCHAR(500) NULL,
  external_id VARCHAR(80) NULL,
  content_type_id VARCHAR(20) NULL,
  content_type_name VARCHAR(80) NULL,
  cat1 VARCHAR(80) NULL,
  cat2 VARCHAR(80) NULL,
  cat3 VARCHAR(80) NULL,
  event_place VARCHAR(255) NULL,
  playtime VARCHAR(255) NULL,
  sponsor VARCHAR(255) NULL,
  detail_intro_json LONGTEXT NULL,
  image_path VARCHAR(500) NULL,
  image_original_url VARCHAR(1000) NULL,
  image_saved_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_festivals_regions FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT fk_festivals_places FOREIGN KEY (place_id) REFERENCES places(place_id),
  CONSTRAINT uq_festivals_region_name_date UNIQUE (region_id, festival_name, start_date),
  INDEX idx_festivals_period (start_date, end_date)
) ENGINE=InnoDB;

CREATE TABLE accommodations (
  accommodation_id INT AUTO_INCREMENT PRIMARY KEY,
  region_id INT NOT NULL,
  accommodation_name VARCHAR(120) NOT NULL,
  address VARCHAR(255) NULL,
  phone VARCHAR(50) NULL,
  source_url VARCHAR(500) NULL,
  external_id VARCHAR(80) NULL,
  content_type_id VARCHAR(20) NULL,
  content_type_name VARCHAR(80) NULL,
  cat1 VARCHAR(80) NULL,
  cat2 VARCHAR(80) NULL,
  cat3 VARCHAR(80) NULL,
  checkin_time VARCHAR(120) NULL,
  checkout_time VARCHAR(120) NULL,
  room_count VARCHAR(120) NULL,
  reservation_url VARCHAR(500) NULL,
  parking_info VARCHAR(255) NULL,
  detail_intro_json LONGTEXT NULL,
  image_path VARCHAR(500) NULL,
  image_original_url VARCHAR(1000) NULL,
  image_saved_at DATETIME NULL,
  CONSTRAINT fk_accommodations_regions FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT uq_accommodations_region_name UNIQUE (region_id, accommodation_name)
) ENGINE=InnoDB;

CREATE TABLE restaurants (
  restaurant_id INT AUTO_INCREMENT PRIMARY KEY,
  region_id INT NOT NULL,
  restaurant_name VARCHAR(120) NOT NULL,
  food_type VARCHAR(50) NOT NULL,
  address VARCHAR(255) NULL,
  phone VARCHAR(80) NULL,
  source_url VARCHAR(500) NULL,
  external_id VARCHAR(80) NULL,
  content_type_id VARCHAR(20) NULL,
  content_type_name VARCHAR(80) NULL,
  cat1 VARCHAR(80) NULL,
  cat2 VARCHAR(80) NULL,
  cat3 VARCHAR(80) NULL,
  first_menu VARCHAR(255) NULL,
  treat_menu VARCHAR(500) NULL,
  open_time VARCHAR(255) NULL,
  rest_date VARCHAR(255) NULL,
  parking_info VARCHAR(255) NULL,
  detail_intro_json LONGTEXT NULL,
  image_path VARCHAR(500) NULL,
  image_original_url VARCHAR(1000) NULL,
  image_saved_at DATETIME NULL,
  CONSTRAINT fk_restaurants_regions FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT uq_restaurants_region_name UNIQUE (region_id, restaurant_name)
) ENGINE=InnoDB;

CREATE TABLE place_categories (
  place_id INT NOT NULL,
  category_id INT NOT NULL,
  PRIMARY KEY (place_id, category_id),
  CONSTRAINT fk_place_categories_places FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
  CONSTRAINT fk_place_categories_categories FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE
) ENGINE=InnoDB;




CREATE TABLE favorites (
  favorite_id INT AUTO_INCREMENT PRIMARY KEY,
  member_id INT NOT NULL,
  place_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_favorites_members FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
  CONSTRAINT fk_favorites_places FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
  CONSTRAINT uq_favorites_member_place UNIQUE (member_id, place_id)
) ENGINE=InnoDB;

CREATE TABLE reviews (
  review_id INT AUTO_INCREMENT PRIMARY KEY,
  member_id INT NOT NULL,
  place_id INT NOT NULL,
  rating TINYINT NOT NULL,
  content VARCHAR(500) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_reviews_members FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
  CONSTRAINT fk_reviews_places FOREIGN KEY (place_id) REFERENCES places(place_id) ON DELETE CASCADE,
  CONSTRAINT ck_reviews_rating CHECK (rating BETWEEN 1 AND 5),
  INDEX idx_reviews_place (place_id)
) ENGINE=InnoDB;

CREATE TABLE travel_courses (
  course_id INT AUTO_INCREMENT PRIMARY KEY,
  member_id INT NOT NULL,
  course_title VARCHAR(120) NOT NULL,
  region_id INT NOT NULL,
  start_date DATE NULL,
  end_date DATE NULL,
  is_public BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_courses_members FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
  CONSTRAINT fk_courses_regions FOREIGN KEY (region_id) REFERENCES regions(region_id)
) ENGINE=InnoDB;

CREATE TABLE course_items (
  course_item_id INT AUTO_INCREMENT PRIMARY KEY,
  course_id INT NOT NULL,
  place_id INT NOT NULL,
  visit_order INT NOT NULL,
  visit_time TIME NULL,
  memo VARCHAR(255) NULL,
  CONSTRAINT fk_course_items_courses FOREIGN KEY (course_id) REFERENCES travel_courses(course_id) ON DELETE CASCADE,
  CONSTRAINT fk_course_items_places FOREIGN KEY (place_id) REFERENCES places(place_id),
  CONSTRAINT uq_course_items_order UNIQUE (course_id, visit_order),
  INDEX idx_course_items_course (course_id)
) ENGINE=InnoDB;

CREATE TABLE crawl_logs (
  crawl_log_id INT AUTO_INCREMENT PRIMARY KEY,
  source_name VARCHAR(80) NOT NULL,
  source_url VARCHAR(500) NULL,
  status ENUM('SUCCESS', 'FAILED', 'FALLBACK') NOT NULL,
  inserted_count INT NOT NULL DEFAULT 0,
  message VARCHAR(500) NULL,
  crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE tour_api_usage_logs (
  log_id INT AUTO_INCREMENT PRIMARY KEY,
  service_code VARCHAR(40) NOT NULL,
  service_name VARCHAR(120) NOT NULL,
  endpoint_url VARCHAR(500) NULL,
  status VARCHAR(30) NOT NULL,
  fetched_count INT NOT NULL DEFAULT 0,
  message VARCHAR(700) NULL,
  collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_tour_api_usage_service (service_code, collected_at)
) ENGINE=InnoDB;

CREATE TABLE tour_photos (
  photo_id INT AUTO_INCREMENT PRIMARY KEY,
  external_id VARCHAR(120) NULL,
  region_name VARCHAR(80) NULL,
  place_name VARCHAR(150) NULL,
  title VARCHAR(200) NOT NULL,
  image_url VARCHAR(700) NULL,
  location VARCHAR(255) NULL,
  photographer VARCHAR(120) NULL,
  shot_date VARCHAR(30) NULL,
  keywords VARCHAR(500) NULL,
  raw_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_tour_photos_external (external_id),
  INDEX idx_tour_photos_region (region_name),
  INDEX idx_tour_photos_title (title)
) ENGINE=InnoDB;

CREATE TABLE region_visitor_stats (
  visitor_stat_id INT AUTO_INCREMENT PRIMARY KEY,
  source_api VARCHAR(80) NOT NULL,
  region_name VARCHAR(80) NOT NULL,
  stat_date VARCHAR(20) NULL,
  visitor_type VARCHAR(80) NULL,
  visitor_count DECIMAL(18, 2) NULL,
  raw_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_region_visitor (source_api, region_name, stat_date, visitor_type),
  INDEX idx_region_visitor_region (region_name),
  INDEX idx_region_visitor_date (stat_date)
) ENGINE=InnoDB;

CREATE TABLE attraction_concentration (
  concentration_id INT AUTO_INCREMENT PRIMARY KEY,
  attraction_name VARCHAR(180) NOT NULL,
  region_name VARCHAR(80) NULL,
  base_date VARCHAR(20) NULL,
  forecast_date VARCHAR(20) NULL,
  concentration_score DECIMAL(10, 2) NULL,
  raw_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_attraction_concentration (attraction_name, forecast_date),
  INDEX idx_attraction_concentration_region (region_name),
  INDEX idx_attraction_concentration_name (attraction_name)
) ENGINE=InnoDB;

CREATE TABLE related_attractions (
  related_id INT AUTO_INCREMENT PRIMARY KEY,
  origin_name VARCHAR(180) NOT NULL,
  related_name VARCHAR(180) NOT NULL,
  relation_type VARCHAR(80) NULL,
  rank_no INT NULL,
  score DECIMAL(12, 2) NULL,
  region_name VARCHAR(80) NULL,
  raw_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_related_attractions (origin_name, related_name, relation_type),
  INDEX idx_related_region (region_name),
  INDEX idx_related_origin (origin_name),
  INDEX idx_related_name (related_name)
) ENGINE=InnoDB;

CREATE TABLE center_attractions (
  center_id INT AUTO_INCREMENT PRIMARY KEY,
  region_name VARCHAR(80) NOT NULL,
  attraction_name VARCHAR(180) NOT NULL,
  rank_no INT NULL,
  navi_count DECIMAL(18, 2) NULL,
  raw_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_center_attractions (region_name, attraction_name),
  INDEX idx_center_region (region_name),
  INDEX idx_center_rank (rank_no)
) ENGINE=InnoDB;

CREATE TABLE regional_demand_metrics (
  demand_metric_id INT AUTO_INCREMENT PRIMARY KEY,
  source_api VARCHAR(80) NOT NULL,
  region_name VARCHAR(80) NOT NULL,
  metric_group VARCHAR(80) NOT NULL,
  metric_name VARCHAR(120) NOT NULL,
  metric_value DECIMAL(18, 4) NULL,
  stat_date VARCHAR(20) NULL,
  raw_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_regional_demand_metric (source_api, region_name, metric_group, metric_name, stat_date),
  INDEX idx_regional_demand_region (region_name),
  INDEX idx_regional_demand_group (metric_group)
) ENGINE=InnoDB;


CREATE TABLE live_kakao_places (
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
) ENGINE=InnoDB;

CREATE TABLE weather_cache (
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
) ENGINE=InnoDB;

CREATE TABLE transport_estimates (
  estimate_id INT AUTO_INCREMENT PRIMARY KEY,
  origin_text VARCHAR(180) NOT NULL,
  destination_text VARCHAR(180) NOT NULL,
  travel_date DATE NULL,
  people INT NOT NULL DEFAULT 1,
  provider VARCHAR(40) NOT NULL DEFAULT 'openai',
  estimate_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_transport_route (origin_text, destination_text, travel_date)
) ENGINE=InnoDB;

ALTER TABLE members
  ADD CONSTRAINT fk_members_preferred_region FOREIGN KEY (preferred_region_id) REFERENCES regions(region_id);

INSERT INTO regions (region_name, province, description, tour_area_code, tour_sigungu_code, kakao_keyword) VALUES
('서울', '서울', 'TourAPI 지역 코드 기반 광역 지역입니다. area=1, sigungu=-', '1', NULL, '서울'),
('인천', '인천', 'TourAPI 지역 코드 기반 광역 지역입니다. area=2, sigungu=-', '2', NULL, '인천'),
('대전', '대전', 'TourAPI 지역 코드 기반 광역 지역입니다. area=3, sigungu=-', '3', NULL, '대전'),
('대구', '대구', 'TourAPI 지역 코드 기반 광역 지역입니다. area=4, sigungu=-', '4', NULL, '대구'),
('광주', '광주', 'TourAPI 지역 코드 기반 광역 지역입니다. area=5, sigungu=-', '5', NULL, '광주'),
('부산', '부산', 'TourAPI 지역 코드 기반 광역 지역입니다. area=6, sigungu=-', '6', NULL, '부산'),
('울산', '울산', 'TourAPI 지역 코드 기반 광역 지역입니다. area=7, sigungu=-', '7', NULL, '울산'),
('세종특별자치시', '세종특별자치시', 'TourAPI 지역 코드 기반 광역 지역입니다. area=8, sigungu=-', '8', NULL, '세종특별자치시'),
('경기도', '경기도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=31, sigungu=-', '31', NULL, '경기도'),
('강원특별자치도', '강원특별자치도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=32, sigungu=-', '32', NULL, '강원특별자치도'),
('충청북도', '충청북도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=33, sigungu=-', '33', NULL, '충청북도'),
('충청남도', '충청남도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=34, sigungu=-', '34', NULL, '충청남도'),
('경상북도', '경상북도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=35, sigungu=-', '35', NULL, '경상북도'),
('경상남도', '경상남도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=36, sigungu=-', '36', NULL, '경상남도'),
('전북특별자치도', '전북특별자치도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=37, sigungu=-', '37', NULL, '전북특별자치도'),
('전라남도', '전라남도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=38, sigungu=-', '38', NULL, '전라남도'),
('제주특별자치도', '제주특별자치도', 'TourAPI 지역 코드 기반 광역 지역입니다. area=39, sigungu=-', '39', NULL, '제주특별자치도');

INSERT INTO categories (category_name, description) VALUES
('역사', '궁궐, 유적지, 박물관 중심'),
('자연', '바다, 산, 호수, 산책 중심'),
('축제', '기간성 행사와 지역 축제 중심'),
('미식', '음식점, 시장, 카페 중심'),
('가족', '가족 단위 방문에 적합'),
('야간', '야경과 저녁 활동에 적합'),
('관광지', 'TourAPI 관광지 타입'),
('문화시설', '박물관, 전시관, 공연장 등 실내 문화 공간'),
('카페', '카페와 커피 중심 장소'),
('실내', '비, 더위, 추위에 대응하기 좋은 실내 장소'),
('숙박', '호텔, 펜션, 게스트하우스 등 숙박 시설'),
('여행코스', 'TourAPI 여행코스 타입');
