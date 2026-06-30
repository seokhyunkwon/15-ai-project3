USE travel_course_db;

-- 추천 점수 근거가 "기본 후보"로만 보이는 경우를 줄이기 위한 데이터 보강 SQL입니다.
-- app.py 실행 시 database.ensure_recommendation_schema()가 아래 컬럼을 자동 추가하지만,
-- 수동으로 확인하고 싶으면 SHOW COLUMNS 쿼리를 먼저 실행하세요.

SHOW COLUMNS FROM places LIKE 'budget_level';
SHOW COLUMNS FROM places LIKE 'recommended_for';
SHOW COLUMNS FROM places LIKE 'tags';
SHOW COLUMNS FROM places LIKE 'indoor_outdoor';

-- 1) 카테고리 기반 tags 보강
UPDATE places p
LEFT JOIN (
    SELECT pc.place_id,
           GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ') AS category_names
    FROM place_categories pc
    JOIN categories c ON c.category_id = pc.category_id
    GROUP BY pc.place_id
) cat ON cat.place_id = p.place_id
SET p.tags = COALESCE(NULLIF(p.tags, ''), cat.category_names)
WHERE cat.category_names IS NOT NULL;

-- 2) 실내/야외 힌트 보강
UPDATE places p
LEFT JOIN (
    SELECT pc.place_id,
           GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ') AS category_names
    FROM place_categories pc
    JOIN categories c ON c.category_id = pc.category_id
    GROUP BY pc.place_id
) cat ON cat.place_id = p.place_id
SET p.indoor_outdoor = CASE
    WHEN p.indoor_outdoor IS NOT NULL THEN p.indoor_outdoor
    WHEN CONCAT_WS(' ', p.place_name, p.overview, cat.category_names) REGEXP '박물관|미술관|전시|문화시설|카페|실내' THEN '실내'
    WHEN CONCAT_WS(' ', p.place_name, p.overview, cat.category_names) REGEXP '해변|해수욕장|공원|산|숲|거리|둘레길|자연|야외' THEN '야외'
    ELSE '혼합'
END;

-- 3) 예산 힌트 보강
UPDATE places p
LEFT JOIN (
    SELECT pc.place_id,
           GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ') AS category_names
    FROM place_categories pc
    JOIN categories c ON c.category_id = pc.category_id
    GROUP BY pc.place_id
) cat ON cat.place_id = p.place_id
SET p.budget_level = CASE
    WHEN p.budget_level IS NOT NULL THEN p.budget_level
    WHEN CONCAT_WS(' ', p.place_name, p.overview, cat.category_names) REGEXP '무료|공원|해변|해수욕장|산책|거리|시장|둘레길|자연' THEN '저렴'
    WHEN CONCAT_WS(' ', p.place_name, p.overview, cat.category_names) REGEXP '호텔|리조트|프리미엄|럭셔리|고급|테마파크' THEN '비쌈'
    ELSE '보통'
END;

-- 4) 주동행인 힌트 보강
UPDATE places p
LEFT JOIN (
    SELECT pc.place_id,
           GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ') AS category_names
    FROM place_categories pc
    JOIN categories c ON c.category_id = pc.category_id
    GROUP BY pc.place_id
) cat ON cat.place_id = p.place_id
SET p.recommended_for = CASE
    WHEN p.recommended_for IS NOT NULL AND p.recommended_for <> '' THEN p.recommended_for
    WHEN CONCAT_WS(' ', p.place_name, p.overview, cat.category_names) REGEXP '야경|전망|카페|해변|산책|사진|일몰|거리' THEN '연인, 친구'
    WHEN CONCAT_WS(' ', p.place_name, p.overview, cat.category_names) REGEXP '가족|아이|어린이|체험|공원|박물관|역사|문화|전시' THEN '가족'
    WHEN CONCAT_WS(' ', p.place_name, p.overview, cat.category_names) REGEXP '미술관|박물관|카페|숲|둘레길|조용|산책' THEN '혼자'
    ELSE '혼자, 친구, 연인, 가족'
END;

-- 5) 보강 결과 확인
SELECT
    p.place_id,
    p.place_name,
    r.region_name,
    p.budget_level,
    p.recommended_for,
    p.indoor_outdoor,
    p.tags,
    GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', ') AS categories
FROM places p
JOIN regions r ON r.region_id = p.region_id
LEFT JOIN place_categories pc ON pc.place_id = p.place_id
LEFT JOIN categories c ON c.category_id = pc.category_id
GROUP BY p.place_id, p.place_name, r.region_name, p.budget_level, p.recommended_for, p.indoor_outdoor, p.tags
ORDER BY r.region_name, p.place_name
LIMIT 100;
