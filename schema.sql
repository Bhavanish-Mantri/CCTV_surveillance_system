-- ============================================================
-- schema.sql — CCTV AI Attendance & Intruder Detection System
-- Run: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS `cctv_attendance`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `cctv_attendance`;

-- ── users ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `users` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `name`       VARCHAR(255) NOT NULL,
  `image_path` TEXT,
  `encoding`   LONGBLOB              COMMENT 'Pickle-serialised 128-d face encoding',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── attendance ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `attendance` (
  `id`         INT      NOT NULL AUTO_INCREMENT,
  `user_id`    INT      NOT NULL,
  `timestamp`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `confidence` FLOAT             COMMENT '0-1 score (1 - face_distance)',
  PRIMARY KEY (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── intruders ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `intruders` (
  `id`         INT      NOT NULL AUTO_INCREMENT,
  `image_path` TEXT              COMMENT 'Relative path under /static',
  `timestamp`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `confidence` FLOAT             COMMENT 'Face distance to nearest known user',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
