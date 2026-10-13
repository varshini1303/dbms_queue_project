-- =============================================================
-- Bank Queue Management System — Database Export for XAMPP
-- Import this in phpMyAdmin: http://localhost/phpmyadmin
-- Database: bank_queue
-- =============================================================

CREATE DATABASE IF NOT EXISTS `bank_queue` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `bank_queue`;

-- 1. Users Table
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `full_name` VARCHAR(120) NOT NULL,
  `phone` VARCHAR(20) NOT NULL UNIQUE,
  `email` VARCHAR(120) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` VARCHAR(20) DEFAULT 'CUSTOMER',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Services Table
DROP TABLE IF EXISTS `services`;
CREATE TABLE `services` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `code` VARCHAR(10) NOT NULL UNIQUE,
  `name` VARCHAR(100) NOT NULL,
  `description` TEXT NOT NULL,
  `estimated_time` VARCHAR(20) DEFAULT '10 min',
  `duration_minutes` INT DEFAULT 10,
  `prefix` VARCHAR(5) DEFAULT 'A',
  `icon` VARCHAR(50) DEFAULT 'banknote',
  `is_active` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Counters Table
DROP TABLE IF EXISTS `counters`;
CREATE TABLE `counters` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL,
  `desk_label` VARCHAR(100) NOT NULL,
  `description` VARCHAR(255) DEFAULT '',
  `status` VARCHAR(20) DEFAULT 'ONLINE',
  `staff_name` VARCHAR(100) DEFAULT 'Staff Member',
  `current_token_id` INT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Tokens Table
DROP TABLE IF EXISTS `tokens`;
CREATE TABLE `tokens` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `token_number` VARCHAR(20) NOT NULL UNIQUE,
  `service_id` INT NOT NULL,
  `counter_id` INT NULL,
  `user_id` INT NULL,
  `customer_name` VARCHAR(120) NOT NULL,
  `customer_phone` VARCHAR(20) NOT NULL,
  `customer_email` VARCHAR(120) NULL,
  `customer_account_number` VARCHAR(50) NULL,
  `booking_date` VARCHAR(20) NOT NULL,
  `time_slot` VARCHAR(50) NOT NULL,
  `status` VARCHAR(30) DEFAULT 'WAITING',
  `estimated_wait_minutes` INT DEFAULT 15,
  `recommended_arrival_time` VARCHAR(50) NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `called_at` DATETIME NULL,
  `completed_at` DATETIME NULL,
  INDEX (`token_number`),
  INDEX (`customer_phone`),
  INDEX (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Contact Messages Table
DROP TABLE IF EXISTS `contact_messages`;
CREATE TABLE `contact_messages` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL,
  `email` VARCHAR(120) NOT NULL,
  `message` TEXT NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed Banking Services
INSERT INTO `services` (`id`, `code`, `name`, `description`, `estimated_time`, `duration_minutes`, `prefix`, `icon`, `is_active`) VALUES
(1, 'DEP', 'Cash Deposit', 'Deposit cash safely into your account.', '8 min', 8, 'A', 'banknote', 1),
(2, 'WTH', 'Cash Withdrawal', 'Withdraw cash with assisted counter service.', '10 min', 10, 'A', 'credit-card', 1),
(3, 'ACC', 'Account Opening', 'Open a new savings or current account.', '25 min', 25, 'B', 'wallet-cards', 1),
(4, 'PBK', 'Passbook Update', 'Update and print your latest transactions.', '5 min', 5, 'D', 'file-text', 1),
(5, 'CHQ', 'Cheque Services', 'Cheque deposit, clearing and related support.', '12 min', 12, 'C', 'check-square', 1),
(6, 'CRD', 'ATM / Debit Card', 'Card issue, replacement and PIN assistance.', '15 min', 15, 'C', 'credit-card', 1),
(7, 'OTH', 'Other Services', 'General customer service and inquiries.', '15 min', 15, 'B', 'help-circle', 1)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- Seed Counters
INSERT INTO `counters` (`id`, `name`, `desk_label`, `description`, `status`, `staff_name`, `current_token_id`) VALUES
(1, 'Counter 1', 'Cash services', 'High-volume cash deposit and withdrawals', 'ONLINE', 'Ramesh Kumar', NULL),
(2, 'Counter 2', 'Account Services', 'New account openings and customer KYC', 'ONLINE', 'Priya Sharma', NULL),
(3, 'Counter 3', 'Cheque & Card Desk', 'Cheque deposit, clearing, and debit cards', 'ONLINE', 'Vikram Singh', NULL),
(4, 'Counter 4', 'Quick Services & Passbook', 'Passbook updates and general inquiries', 'ONLINE', 'Sneha Patel', NULL)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

-- Seed Demo Users
INSERT INTO `users` (`full_name`, `phone`, `email`, `password_hash`, `role`) VALUES
('Branch Manager', '+919876543210', 'manager@bankqueue.example', '7b47e2a44b:e44b82bc6a22fcf118eb3d052a', 'ADMIN'),
('Rohit Sharma', '+919876543211', 'rohit@example.com', '7b47e2a44b:e44b82bc6a22fcf118eb3d052a', 'CUSTOMER')
ON DUPLICATE KEY UPDATE `full_name`=VALUES(`full_name`);

-- Seed Active Demo Tokens
INSERT INTO `tokens` (`token_number`, `service_id`, `counter_id`, `customer_name`, `customer_phone`, `booking_date`, `time_slot`, `status`, `estimated_wait_minutes`, `recommended_arrival_time`) VALUES
('A104', 1, 1, 'Ananya Rao', '+919876500104', 'Today', '10:15 AM', 'SERVING', 0, '10:15 AM'),
('A105', 1, 1, 'Karthik Verma', '+919876500105', 'Today', '10:30 AM', 'APPROACHING', 8, '10:25 AM'),
('A108', 1, 1, 'Meera Patel', '+919876500108', 'Today', '10:30 AM', 'APPROACHING', 12, '10:20 AM'),
('B201', 3, 2, 'Arjun Menon', '+919876500201', 'Today', '10:00 AM', 'SERVING', 0, '10:00 AM'),
('C102', 5, 3, 'Neha Gupta', '+919876500302', 'Today', '11:00 AM', 'WAITING', 15, '10:50 AM')
ON DUPLICATE KEY UPDATE `status`=VALUES(`status`);

UPDATE `counters` SET `current_token_id` = 1 WHERE `id` = 1;
UPDATE `counters` SET `current_token_id` = 4 WHERE `id` = 2;
