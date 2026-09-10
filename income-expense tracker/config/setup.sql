-- =============================================
--  DATABASE SETUP — run this once in phpMyAdmin
--  or via: mysql -u root -p < config/setup.sql
-- =============================================

CREATE DATABASE IF NOT EXISTS finance_tracker
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE finance_tracker;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id           INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    full_name    VARCHAR(100)    NOT NULL,
    email        VARCHAR(150)    NOT NULL UNIQUE,
    password     VARCHAR(255)    NOT NULL,          -- bcrypt hash
    created_at   TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id           INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    user_id      INT UNSIGNED    NOT NULL,
    type         ENUM('income','expense') NOT NULL,
    category     VARCHAR(80)     NOT NULL,
    amount       DECIMAL(12,2)   NOT NULL,
    description  VARCHAR(255)    DEFAULT NULL,
    date         DATE            NOT NULL,
    created_at   TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Budgets table
CREATE TABLE IF NOT EXISTS budgets (
    id           INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    user_id      INT UNSIGNED    NOT NULL,
    category     VARCHAR(80)     NOT NULL,
    amount       DECIMAL(12,2)   NOT NULL,
    month        DATE            NOT NULL,
    created_at   TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_cat_month (user_id, category, month),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sample data (optional — remove in production)
INSERT IGNORE INTO transactions (user_id, type, category, amount, description, date) VALUES
(1, 'income',  'Salary',        3500.00, 'Monthly salary',   CURDATE()),
(1, 'income',  'Freelance',      800.00, 'Web project',      DATE_SUB(CURDATE(), INTERVAL 5 DAY)),
(1, 'expense', 'Food',           120.00, 'Groceries',        DATE_SUB(CURDATE(), INTERVAL 2 DAY)),
(1, 'expense', 'Transport',       60.00, 'Fuel',             DATE_SUB(CURDATE(), INTERVAL 3 DAY)),
(1, 'expense', 'Bills',          200.00, 'Electricity',      DATE_SUB(CURDATE(), INTERVAL 7 DAY)),
(1, 'expense', 'Entertainment',   85.00, 'Netflix + cinema', DATE_SUB(CURDATE(), INTERVAL 10 DAY));
