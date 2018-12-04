-- MySQL dump 10.16  Distrib 10.1.26-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: db
-- ------------------------------------------------------
-- Server version	10.1.26-MariaDB-0+deb9u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `actor`
--

DROP TABLE IF EXISTS `actor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `actor` (
  `id` int(11) DEFAULT NULL,
  `acbid` text,
  `is_coach` text,
  `display_name` text,
  `full_name` text,
  `nationality` text,
  `birthplace` text,
  `birthdate` text,
  `position` text,
  `height` decimal(10,0) DEFAULT NULL,
  `weight` decimal(10,0) DEFAULT NULL,
  `license` text,
  `debut_acb` text,
  `twitter` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;
--
-- Table structure for table `game`
--

DROP TABLE IF EXISTS `game`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `game` (
  `id` int(11) DEFAULT NULL,
  `acbid` text,
  `team_home_id` int(11) DEFAULT NULL,
  `team_away_id` int(11) DEFAULT NULL,
  `competition_phase` text,
  `round_phase` text,
  `journey` int(11) DEFAULT NULL,
  `venue` text,
  `attendance` int(11) DEFAULT NULL,
  `kickoff_time` text,
  `score_home` int(11) DEFAULT NULL,
  `score_away` int(11) DEFAULT NULL,
  `score_home_first` int(11) DEFAULT NULL,
  `score_away_first` int(11) DEFAULT NULL,
  `score_home_second` int(11) DEFAULT NULL,
  `score_away_second` int(11) DEFAULT NULL,
  `score_home_third` int(11) DEFAULT NULL,
  `score_away_third` int(11) DEFAULT NULL,
  `score_home_fourth` int(11) DEFAULT NULL,
  `score_away_fourth` int(11) DEFAULT NULL,
  `score_home_extra` int(11) DEFAULT NULL,
  `score_away_extra` int(11) DEFAULT NULL,
  `db_flag` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `participant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `participant` (
  `id` int(11) DEFAULT NULL,
  `game_id` int(11) DEFAULT NULL,
  `team_id` int(11) DEFAULT NULL,
  `actor_id` int(11) DEFAULT NULL,
  `display_name` text,
  `first_name` text,
  `last_name` text,
  `number` int(11) DEFAULT NULL,
  `is_coach` text,
  `is_referee` text,
  `is_starter` text,
  `minutes` int(11) DEFAULT NULL,
  `point` int(11) DEFAULT NULL,
  `t2_attempt` int(11) DEFAULT NULL,
  `t2` int(11) DEFAULT NULL,
  `t3_attempt` int(11) DEFAULT NULL,
  `t3` int(11) DEFAULT NULL,
  `t1_attempt` int(11) DEFAULT NULL,
  `t1` int(11) DEFAULT NULL,
  `defensive_reb` int(11) DEFAULT NULL,
  `offensive_reb` int(11) DEFAULT NULL,
  `assist` int(11) DEFAULT NULL,
  `steal` int(11) DEFAULT NULL,
  `turnover` int(11) DEFAULT NULL,
  `counterattack` int(11) DEFAULT NULL,
  `block` int(11) DEFAULT NULL,
  `received_block` int(11) DEFAULT NULL,
  `dunk` int(11) DEFAULT NULL,
  `fault` int(11) DEFAULT NULL,
  `received_fault` int(11) DEFAULT NULL,
  `plus_minus` int(11) DEFAULT NULL,
  `efficiency` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;


--
-- Table structure for table `team`
--

DROP TABLE IF EXISTS `team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `team` (
  `id` int(11) DEFAULT NULL,
  `acbid` text,
  `founded_year` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `teamName`
--

DROP TABLE IF EXISTS `teamname`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `teamname` (
  `id` int(11) DEFAULT NULL,
  `team_id` int(11) DEFAULT NULL,
  `name` text,
  `season` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2018-09-08 22:53:50