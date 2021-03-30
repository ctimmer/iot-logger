-- phpMyAdmin SQL Dump
-- version 4.6.6deb5
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Mar 29, 2021 at 07:58 PM
-- Server version: 10.3.27-MariaDB-0+deb10u1
-- PHP Version: 7.3.27-1~deb10u1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `iotlogger`
--

-- --------------------------------------------------------

--
-- Table structure for table `devices`
--

CREATE TABLE `devices` (
  `device_key` bigint(11) NOT NULL,
  `device_id` varchar(40) NOT NULL,
  `type_key` bigint(20) NOT NULL DEFAULT 99,
  `description` varchar(1023) NOT NULL DEFAULT '',
  `device_retention_days` int(11) NOT NULL DEFAULT 367,
  `log_date` timestamp NULL DEFAULT NULL,
  `log_data` longtext NOT NULL DEFAULT '{}'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `device_groups`
--

CREATE TABLE `device_groups` (
  `device_key` bigint(20) NOT NULL,
  `group_key` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `device_log`
--

CREATE TABLE `device_log` (
  `device_key` bigint(20) NOT NULL,
  `log_date` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `log_data` longtext NOT NULL DEFAULT '{}'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `device_types`
--

CREATE TABLE `device_types` (
  `type_key` bigint(20) NOT NULL,
  `name` varchar(40) NOT NULL,
  `log_retention_days` int(11) NOT NULL DEFAULT 32
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `device_types`
--

INSERT INTO `device_types` (`type_key`, `name`, `log_retention_days`) VALUES
(99, 'Unknown', 32),
(100, 'Computer', 32);

-- --------------------------------------------------------

--
-- Table structure for table `groups`
--

CREATE TABLE `groups` (
  `group_key` bigint(20) NOT NULL,
  `group_id` varchar(40) NOT NULL DEFAULT '',
  `description` varchar(1024) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `devices`
--
ALTER TABLE `devices`
  ADD PRIMARY KEY (`device_id`),
  ADD UNIQUE KEY `device_key` (`device_key`);

--
-- Indexes for table `device_groups`
--
ALTER TABLE `device_groups`
  ADD PRIMARY KEY (`device_key`,`group_key`),
  ADD UNIQUE KEY `group_device_idx` (`group_key`,`device_key`);

--
-- Indexes for table `device_log`
--
ALTER TABLE `device_log`
  ADD PRIMARY KEY (`device_key`,`log_date`) USING BTREE,
  ADD UNIQUE KEY `date_dev_idx` (`log_date`,`device_key`);

--
-- Indexes for table `device_types`
--
ALTER TABLE `device_types`
  ADD PRIMARY KEY (`type_key`),
  ADD UNIQUE KEY `type_name_index` (`name`);

--
-- Indexes for table `groups`
--
ALTER TABLE `groups`
  ADD PRIMARY KEY (`group_key`),
  ADD UNIQUE KEY `group_id_idx` (`group_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `devices`
--
ALTER TABLE `devices`
  MODIFY `device_key` bigint(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=128;
--
-- AUTO_INCREMENT for table `device_types`
--
ALTER TABLE `device_types`
  MODIFY `type_key` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=106;
--
-- AUTO_INCREMENT for table `groups`
--
ALTER TABLE `groups`
  MODIFY `group_key` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=102;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
