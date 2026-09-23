-- ============================================================
-- AI SOFTWARE BUG ANALYZER
-- DATABASE SCHEMA
-- ============================================================

CREATE DATABASE IF NOT EXISTS ai_bug_analyzer;

USE ai_bug_analyzer;


-- ============================================================
-- USERS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    reset_token VARCHAR(255) NULL,
    reset_token_expiry DATETIME NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',

    PRIMARY KEY (id)
);


-- ============================================================
-- ANALYSES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS analyses (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NULL,
    language VARCHAR(50) NOT NULL,
    code TEXT NOT NULL,
    result LONGTEXT NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    INDEX idx_analyses_user_id (user_id),

    CONSTRAINT fk_analyses_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);


-- ============================================================
-- DATABASE READY
-- ============================================================