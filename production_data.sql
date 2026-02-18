-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主机： localhost
-- 生成日期： 2026-02-18 22:18:04
-- 服务器版本： 10.4.28-MariaDB
-- PHP 版本： 8.2.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 数据库： `oil_wells`
--

-- --------------------------------------------------------

--
-- 表的结构 `production_data`
--

CREATE TABLE `production_data` (
  `id` int(11) NOT NULL,
  `well_id` int(11) DEFAULT NULL,
  `well_status` varchar(100) DEFAULT NULL,
  `well_type` varchar(100) DEFAULT NULL,
  `closest_city` varchar(255) DEFAULT NULL,
  `oil_barrels` double DEFAULT NULL,
  `gas_mcf` double DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- 转存表中的数据 `production_data`
--

INSERT INTO `production_data` (`id`, `well_id`, `well_status`, `well_type`, `closest_city`, `oil_barrels`, `gas_mcf`) VALUES
(1, 1, 'Plugged and Abandoned', 'Oil & Gas', 'Williston', 64, NULL),
(2, 2, 'Active', 'Oil & Gas', 'Williston', 608, 884),
(3, 4, 'Active', 'Oil & Gas', 'Williston', 339, 609),
(4, 6, 'Active', 'Oil & Gas', 'Williston', 1800, 4200),
(5, 8, 'Active', 'Oil & Gas', 'Williston', 787, 1000),
(6, 9, 'Active', 'Oil & Gas', 'Williston', 592, 872),
(7, 10, 'Inactive', 'Oil & Gas', 'Williston', NULL, NULL),
(8, 11, 'Active', 'Oil & Gas', 'Williston', 1400, 1000),
(9, 12, 'Active', 'Oil & Gas', 'Williston', 520, 794),
(10, 13, 'Active', 'Oil & Gas', 'Williston', 711, 3900),
(11, 14, 'Active', 'Oil & Gas', 'Williston', NULL, NULL),
(12, 15, 'Plugged and Abandoned', 'Oil & Gas', 'Williston', NULL, NULL),
(13, 16, 'Active', 'Oil & Gas', 'Williston', 967, 4100),
(14, 17, 'Active', 'Oil & Gas', 'Williston', 518, 518),
(15, 21, 'Active', 'Oil & Gas', 'Williston', 511, 1700),
(16, 27, 'Active', 'Oil & Gas', 'Williston', 852, 2700),
(17, 28, 'Inactive', 'Oil & Gas', 'Williston', NULL, NULL),
(18, 29, 'Active', 'Oil & Gas', 'Williston', 387, 666),
(19, 31, 'Active', 'Oil & Gas', 'Williston', 565, 843),
(20, 32, 'Active', 'Oil & Gas', 'Williston', 229, 493),
(21, 35, 'Active', 'Oil & Gas', 'Williston', 717, 2500),
(22, 36, 'Active', 'Oil & Gas', 'Williston', 1000, 211),
(23, 39, 'Active', 'Oil & Gas', 'Williston', 537, 537),
(24, 40, 'Active', 'Oil & Gas', 'Williston', 63, 12),
(25, 41, 'Abandoned', 'Oil & Gas', 'Williston', NULL, NULL);

--
-- 转储表的索引
--

--
-- 表的索引 `production_data`
--
ALTER TABLE `production_data`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_production_data_well` (`well_id`);

--
-- 在导出的表使用AUTO_INCREMENT
--

--
-- 使用表AUTO_INCREMENT `production_data`
--
ALTER TABLE `production_data`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=60;

--
-- 限制导出的表
--

--
-- 限制表 `production_data`
--
ALTER TABLE `production_data`
  ADD CONSTRAINT `production_data_ibfk_1` FOREIGN KEY (`well_id`) REFERENCES `wells` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
