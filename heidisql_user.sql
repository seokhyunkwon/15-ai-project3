-- MariaDB / HeidiSQL authentication fix for the Streamlit app.
-- Run this after schema.sql while connected as an admin/root account in HeidiSQL.

DROP USER IF EXISTS 'travel_app'@'localhost';
DROP USER IF EXISTS 'travel_app'@'127.0.0.1';
DROP USER IF EXISTS 'travel_app'@'%';

CREATE USER 'travel_app'@'localhost' IDENTIFIED BY 'travel1234';
CREATE USER 'travel_app'@'127.0.0.1' IDENTIFIED BY 'travel1234';
CREATE USER 'travel_app'@'%' IDENTIFIED BY 'travel1234';

-- MariaDB can choose Windows/GSSAPI auth depending on installation settings.
-- Force a password-based plugin that Python clients can use.
ALTER USER 'travel_app'@'localhost'
  IDENTIFIED VIA mysql_native_password USING PASSWORD('travel1234');
ALTER USER 'travel_app'@'127.0.0.1'
  IDENTIFIED VIA mysql_native_password USING PASSWORD('travel1234');
ALTER USER 'travel_app'@'%'
  IDENTIFIED VIA mysql_native_password USING PASSWORD('travel1234');

GRANT ALL PRIVILEGES ON travel_course_db.* TO 'travel_app'@'localhost';
GRANT ALL PRIVILEGES ON travel_course_db.* TO 'travel_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON travel_course_db.* TO 'travel_app'@'%';

FLUSH PRIVILEGES;

SELECT User, Host, plugin
FROM mysql.user
WHERE User = 'travel_app'
ORDER BY Host;
