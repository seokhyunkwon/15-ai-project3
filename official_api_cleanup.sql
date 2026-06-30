USE travel_course_db;

-- 승인 API 원본에 직접 존재하지 않아 추천 조건/화면에서 제거할 컬럼 정리
-- 실행해도 기존 리뷰/찜/장소 데이터는 삭제되지 않습니다.

DROP PROCEDURE IF EXISTS drop_column_if_exists;
DELIMITER //
CREATE PROCEDURE drop_column_if_exists(
  IN p_table_name VARCHAR(64),
  IN p_column_name VARCHAR(64)
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = p_table_name
      AND COLUMN_NAME = p_column_name
  ) THEN
    SET @sql_text = CONCAT('ALTER TABLE `', p_table_name, '` DROP COLUMN `', p_column_name, '`');
    PREPARE stmt FROM @sql_text;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END//
DELIMITER ;

CALL drop_column_if_exists('places', 'recommended_for');
CALL drop_column_if_exists('places', 'budget_level');
CALL drop_column_if_exists('restaurants', 'price_level');
CALL drop_column_if_exists('accommodations', 'price_level');

DROP PROCEDURE IF EXISTS drop_column_if_exists;

SELECT 'cleanup complete: unsupported companion/budget/price columns removed' AS result_message;
