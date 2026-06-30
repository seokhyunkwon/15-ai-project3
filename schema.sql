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
  region_name VARCHAR(50) NOT NULL UNIQUE,
  province VARCHAR(50) NOT NULL,
  description VARCHAR(255) NULL
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
  tags VARCHAR(500) NULL,
  indoor_outdoor ENUM('실내', '야외', '혼합') NULL,
  recommended_for VARCHAR(255) NULL,
  budget_level ENUM('저렴', '보통', '비쌈') NULL,
  opening_hours VARCHAR(255) NULL,
  source_api VARCHAR(80) NULL,
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
  price_level ENUM('LOW', 'MID', 'HIGH') NOT NULL DEFAULT 'MID',
  phone VARCHAR(50) NULL,
  CONSTRAINT fk_accommodations_regions FOREIGN KEY (region_id) REFERENCES regions(region_id),
  CONSTRAINT uq_accommodations_region_name UNIQUE (region_id, accommodation_name)
) ENGINE=InnoDB;

CREATE TABLE restaurants (
  restaurant_id INT AUTO_INCREMENT PRIMARY KEY,
  region_id INT NOT NULL,
  restaurant_name VARCHAR(120) NOT NULL,
  food_type VARCHAR(50) NOT NULL,
  address VARCHAR(255) NULL,
  price_level ENUM('LOW', 'MID', 'HIGH') NOT NULL DEFAULT 'MID',
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

ALTER TABLE members
  ADD CONSTRAINT fk_members_preferred_region FOREIGN KEY (preferred_region_id) REFERENCES regions(region_id);

INSERT INTO regions (region_name, province, description) VALUES
('서울', '서울특별시', '도심 문화, 야간 명소, 궁궐 여행에 강한 지역'),
('부산', '부산광역시', '바다, 영화, 시장, 야경 코스가 풍부한 지역'),
('경주', '경상북도', '역사 유적과 한옥 감성이 강한 지역'),
('제주', '제주특별자치도', '자연 경관과 드라이브 코스가 풍부한 지역'),
('강릉', '강원특별자치도', '바다, 커피거리, 자연 휴식 코스가 좋은 지역'),
('대구', '대구광역시', '도심 미식, 근대골목, 산책 코스가 있는 지역'),
('인천', '인천광역시', '섬, 항구, 차이나타운, 공항 접근성이 좋은 지역'),
('광주', '광주광역시', '예술, 역사, 미식 여행에 어울리는 지역'),
('대전', '대전광역시', '과학, 도심 산책, 근교 자연을 함께 볼 수 있는 지역'),
('울산', '울산광역시', '해안, 산업관광, 산악 경관이 함께 있는 지역'),
('세종', '세종특별자치시', '도심 공원과 행정도시 기반의 산책 코스가 있는 지역'),
('경기', '경기도', '수도권 근교 여행지와 가족형 관광지가 많은 지역'),
('강원', '강원특별자치도', '산, 바다, 호수, 계절 여행지가 풍부한 지역'),
('충북', '충청북도', '호수, 산림, 내륙 휴양 코스가 좋은 지역'),
('충남', '충청남도', '서해안, 온천, 역사 도시가 있는 지역'),
('전북', '전북특별자치도', '한옥, 미식, 산악 경관이 어울리는 지역'),
('전남', '전라남도', '섬, 남도 미식, 해안 관광지가 풍부한 지역'),
('경북', '경상북도', '역사 유산과 전통 문화 여행지가 풍부한 지역'),
('경남', '경상남도', '남해안, 섬, 역사 도시를 함께 볼 수 있는 지역');

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

INSERT INTO members (username, password_hash, name, email, preferred_region_id, role) VALUES
('demo', '0ead2060b65992dca4769af601a1b3a35ef38cfad2c2c465bb160ea764157c5d', '데모회원', 'demo@example.com', 3, 'USER'),
('admin', 'ac9689e2272427085e35b9d3e3e8bed88cb3434828b43b86fc0596cad4c6e270', '관리자', 'admin@example.com', 1, 'ADMIN');

INSERT INTO places (region_id, place_name, address, overview, phone, latitude, longitude, source_url, average_rating) VALUES
(1, '경복궁', '서울 종로구 사직로 161', '조선 왕조의 대표 궁궐로 역사 여행 코스의 중심지입니다.', '02-3700-3900', 37.5796170, 126.9770410, 'https://www.royalpalace.go.kr', 4.70),
(1, '남산서울타워', '서울 용산구 남산공원길 105', '서울 야경을 한눈에 볼 수 있는 전망 명소입니다.', '02-3455-9277', 37.5511690, 126.9882270, 'https://www.seoultower.co.kr', 4.50),
(2, '해운대해수욕장', '부산 해운대구 우동', '부산을 대표하는 바다 여행지입니다.', '051-749-7614', 35.1586980, 129.1603840, NULL, 4.60),
(2, '감천문화마을', '부산 사하구 감내2로 203', '계단식 마을과 벽화가 어우러진 부산의 대표 문화 관광지입니다.', '051-204-1444', 35.0974860, 129.0106680, NULL, 4.40),
(3, '불국사', '경북 경주시 불국로 385', '신라 불교문화와 세계유산의 가치를 함께 볼 수 있는 명소입니다.', '054-746-9913', 35.7900130, 129.3320180, NULL, 4.80),
(3, '동궁과 월지', '경북 경주시 원화로 102', '야간 산책과 사진 촬영으로 유명한 경주 대표 명소입니다.', '054-750-8655', 35.8347020, 129.2266320, NULL, 4.70),
(4, '성산일출봉', '제주 서귀포시 성산읍 성산리', '일출과 화산 지형을 함께 즐길 수 있는 제주 대표 자연 명소입니다.', '064-783-0959', 33.4580560, 126.9425000, NULL, 4.80),
(4, '협재해수욕장', '제주 제주시 한림읍 협재리', '맑은 바다와 비양도 풍경이 어우러진 해변 명소입니다.', NULL, 33.3948670, 126.2391670, NULL, 4.60),
(5, '안목해변 커피거리', '강원 강릉시 창해로14번길', '바다를 보며 카페 투어를 즐기기 좋은 강릉 대표 코스입니다.', NULL, 37.7711130, 128.9473910, NULL, 4.50),
(5, '오죽헌', '강원 강릉시 율곡로3139번길 24', '신사임당과 율곡 이이의 역사적 흔적을 볼 수 있는 명소입니다.', '033-660-3301', 37.7791130, 128.8786740, NULL, 4.40);

INSERT INTO place_categories (place_id, category_id)
SELECT p.place_id, c.category_id
FROM places p
JOIN categories c ON
  (p.place_name IN ('경복궁', '불국사', '오죽헌') AND c.category_name = '역사')
  OR (p.place_name IN ('해운대해수욕장', '성산일출봉', '협재해수욕장', '안목해변 커피거리') AND c.category_name = '자연')
  OR (p.place_name IN ('남산서울타워', '동궁과 월지') AND c.category_name = '야간')
  OR (p.place_name IN ('안목해변 커피거리', '감천문화마을') AND c.category_name = '미식')
  OR (p.place_name IN ('경복궁', '불국사', '성산일출봉') AND c.category_name = '가족');

INSERT INTO festivals (region_id, place_id, festival_name, start_date, end_date, fee_info, homepage, overview, source_url) VALUES
(1, NULL, '서울빛초롱축제', '2026-12-01', '2026-12-31', '무료', 'https://www.stolantern.com', '서울 도심 야간 관광과 어울리는 겨울 빛 축제입니다.', NULL),
(2, NULL, '부산불꽃축제', '2026-11-07', '2026-11-07', '일부 유료', 'https://www.bfo.or.kr', '광안리 일대에서 열리는 부산 대표 야간 축제입니다.', NULL),
(3, NULL, '경주 벚꽃축제', '2027-03-27', '2027-04-05', '무료', NULL, '경주의 역사 유적과 봄꽃을 함께 즐길 수 있는 계절 축제입니다.', NULL),
(4, NULL, '제주 들불축제', '2027-03-01', '2027-03-03', '무료', NULL, '제주의 자연과 전통문화를 체험하는 대표 축제입니다.', NULL),
(5, NULL, '강릉 커피축제', '2026-10-10', '2026-10-13', '무료', NULL, '커피 도시 강릉의 카페와 로컬 문화를 즐길 수 있는 축제입니다.', NULL);

INSERT INTO accommodations (region_id, accommodation_name, address, price_level, phone) VALUES
(1, '종로 시티스테이', '서울 종로구', 'MID', '02-0000-1000'),
(2, '해운대 오션호텔', '부산 해운대구', 'HIGH', '051-000-2000'),
(3, '경주 한옥스테이', '경북 경주시', 'MID', '054-000-3000'),
(4, '제주 바람스테이', '제주 제주시', 'MID', '064-000-4000'),
(5, '강릉 커피펜션', '강원 강릉시', 'LOW', '033-000-5000');

INSERT INTO restaurants (region_id, restaurant_name, food_type, address, price_level) VALUES
(1, '서촌 한식당', '한식', '서울 종로구', 'MID'),
(2, '해운대 밀면집', '밀면', '부산 해운대구', 'LOW'),
(3, '경주 쌈밥거리', '한식', '경북 경주시', 'MID'),
(4, '제주 흑돼지거리', '흑돼지', '제주 제주시', 'HIGH'),
(5, '안목 커피로스터스', '카페', '강원 강릉시', 'MID');

INSERT INTO favorites (member_id, place_id)
SELECT m.member_id, p.place_id
FROM members m
JOIN places p ON p.place_name IN ('불국사', '동궁과 월지')
WHERE m.username = 'demo';

INSERT INTO reviews (member_id, place_id, rating, content)
SELECT m.member_id, p.place_id, 5, '야간 코스로 넣기 좋고 발표용 샘플 데이터로도 보기 좋습니다.'
FROM members m
JOIN places p ON p.place_name = '동궁과 월지'
WHERE m.username = 'demo';

INSERT INTO crawl_logs (source_name, source_url, status, inserted_count, message) VALUES
('seed', 'schema.sql', 'SUCCESS', 10, '초기 샘플 관광지와 축제 데이터를 삽입했습니다.');
