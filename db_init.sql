CREATE DATABASE layerindex CHARACTER SET UTF8;
CREATE USER oelayer@localhost IDENTIFIED BY 'oelayer';
GRANT ALL PRIVILEGES ON layerindex.* TO oelayer@localhost;
FLUSH PRIVILEGES;
