-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主机： localhost
-- 生成日期： 2026-02-21 01:24:26
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
(53, 2, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(54, 4, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(55, 6, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(56, 8, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(57, 9, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(58, 10, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(59, 11, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(60, 12, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(61, 13, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(62, 14, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(63, 16, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(64, 17, NULL, NULL, NULL, 4490),
(65, 21, 'Frac / Fracture Treatment', NULL, NULL, 12500),
(66, 27, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(67, 28, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(68, 29, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(69, 31, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(70, 32, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(71, 36, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(72, 39, NULL, NULL, NULL, 500),
(73, 41, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(74, 42, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(75, 43, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(76, 44, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(77, 45, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(78, 51, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(79, 64, 'Stimulation', NULL, NULL, NULL),
(80, 65, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(81, 68, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(82, 69, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(83, 70, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(84, 71, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(85, 72, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(86, 73, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(87, 74, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(88, 75, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(89, 76, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(90, 77, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(91, 78, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(92, 79, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(93, 80, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(94, 81, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(95, 82, 'Stimulation', NULL, NULL, NULL),
(96, 83, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(97, 84, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(98, 85, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(99, 86, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(100, 87, 'Frac / Fracture Treatment', NULL, NULL, NULL),
(101, 88, NULL, NULL, NULL, 2500),
(102, 89, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(103, 92, 'Frac / Fracture Treatment', NULL, NULL, 9000),
(104, 95, 'Frac / Fracture Treatment', NULL, NULL, NULL);

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
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=105;

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
