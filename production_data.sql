-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主机： localhost
-- 生成日期： 2026-02-21 01:24:44
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
(1, 1, 'Plugged and Abandoned Well Type Oil & Gas', 'Oil & Gas', 'Williston', 64, 0),
(2, 2, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 608, 884),
(3, 4, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 339, 609),
(4, 6, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 1800, 4200),
(5, 8, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 787, 1000),
(6, 9, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 592, 872),
(7, 10, 'Inactive', 'N/A', 'N/A', 0, 0),
(8, 11, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 1400, 1000),
(9, 12, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 520, 794),
(10, 13, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 711, 3900),
(11, 14, 'Active', 'N/A', 'N/A', 0, 0),
(12, 15, 'Plugged and Abandoned', 'N/A', 'N/A', 0, 0),
(13, 16, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 967, 4100),
(14, 17, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 518, 518),
(15, 21, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 511, 1700),
(16, 27, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 852, 2700),
(17, 28, 'Inactive', 'N/A', 'N/A', 0, 0),
(18, 29, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 387, 666),
(19, 31, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 565, 843),
(20, 32, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 229, 493),
(21, 35, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 717, 2500),
(22, 36, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 1000, 211),
(23, 39, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 537, 537),
(24, 40, 'N/A', 'N/A', 'N/A', 0, 0),
(25, 41, 'Abandoned', 'N/A', 'N/A', 0, 0),
(26, 42, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 1000, 2100),
(27, 43, 'N/A', 'N/A', 'N/A', 0, 0),
(28, 44, 'Plugged and Abandoned', 'N/A', 'N/A', 0, 0),
(29, 45, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 1500, 3400),
(30, 50, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 296, 193),
(31, 51, 'Active', 'N/A', 'N/A', 0, 0),
(32, 64, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 1100, 2500),
(33, 65, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 714, 1100),
(34, 68, 'N/A', 'N/A', 'N/A', 0, 0),
(35, 69, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 275, 2500),
(36, 70, 'N/A', 'N/A', 'N/A', 0, 0),
(37, 71, 'N/A', 'N/A', 'N/A', 0, 0),
(38, 72, 'N/A', 'N/A', 'N/A', 0, 0),
(39, 73, 'N/A', 'N/A', 'N/A', 0, 0),
(40, 74, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 1300, 4000),
(41, 75, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 540, 3600),
(42, 76, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 396, 1000),
(43, 77, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 292, 553),
(44, 78, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 227, 1500),
(45, 79, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 248, 1300),
(46, 80, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 321, 1200),
(47, 81, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 135, 770),
(48, 82, 'N/A', 'N/A', 'N/A', 0, 0),
(49, 83, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 185, 451),
(50, 84, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 285, 1100),
(51, 85, 'Abandoned', 'N/A', 'N/A', 0, 0),
(52, 86, 'N/A', 'N/A', 'N/A', 0, 0),
(53, 87, 'N/A', 'N/A', 'N/A', 0, 0),
(54, 88, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 318, 2400),
(55, 89, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 158, 743),
(56, 90, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 723, 3800),
(57, 91, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 357, 2900),
(58, 92, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 206, 1900),
(59, 95, 'Active Well Type Oil & Gas', 'Oil & Gas', 'Williston', 489, 1800);

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
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=473;

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
