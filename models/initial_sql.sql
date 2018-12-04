-- MySQL dump 10.16  Distrib 10.1.26-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: db
-- ------------------------------------------------------
-- Server version	10.1.26-MariaDB-0+deb9u1

SET SQL_SAFE_UPDATES = 0;

DELETE FROM actor;
ALTER TABLE actor AUTO_INCREMENT = 1;


DELETE FROM game;
ALTER TABLE game AUTO_INCREMENT = 1;


DELETE FROM participant;
ALTER TABLE participant AUTO_INCREMENT = 1;


DELETE FROM teamname;
ALTER TABLE teamname AUTO_INCREMENT = 1;

DELETE FROM team;
ALTER TABLE team AUTO_INCREMENT = 1;

SET SQL_SAFE_UPDATES = 1;