-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主机： localhost
-- 生成日期： 2026-02-18 22:17:55
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
-- 表的结构 `stimulation_data`
--

CREATE TABLE `stimulation_data` (
  `id` int(11) NOT NULL,
  `well_id` int(11) DEFAULT NULL,
  `treatment_type` varchar(255) DEFAULT NULL,
  `total_proppant` double DEFAULT NULL,
  `fluid_volume` double DEFAULT NULL,
  `max_pressure` double DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- 转存表中的数据 `stimulation_data`
--

INSERT INTO `stimulation_data` (`id`, `well_id`, `treatment_type`, `total_proppant`, `fluid_volume`, `max_pressure`) VALUES
(1, 2, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(2, 4, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(3, 6, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(4, 8, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(5, 9, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(6, 10, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(7, 11, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(8, 12, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(9, 13, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(10, 14, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(11, 16, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(12, 17, NULL, NULL, NULL, 4490),
(13, 21, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(14, 27, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(15, 28, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(16, 29, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(17, 31, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(18, 32, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(19, 36, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(20, 39, NULL, NULL, NULL, 500),
(21, 41, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(22, 42, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(23, 43, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(24, 44, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(25, 45, 'Frac / Fracture Treatment', NULL, NULL, NULL);

--
-- 转储表的索引
--

--
-- 表的索引 `stimulation_data`
--
ALTER TABLE `stimulation_data`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_stimulation_data_well` (`well_id`);

--
-- 在导出的表使用AUTO_INCREMENT
--

--
-- 使用表AUTO_INCREMENT `stimulation_data`
--
ALTER TABLE `stimulation_data`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=53;

--
-- 限制导出的表
--

--
-- 限制表 `stimulation_data`
--
ALTER TABLE `stimulation_data`
  ADD CONSTRAINT `stimulation_data_ibfk_1` FOREIGN KEY (`well_id`) REFERENCES `wells` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
