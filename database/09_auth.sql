-- 09_auth.sql : login accounts for the website (run AFTER 02_create_tables.sql)
USE airport_aodb;

CREATE TABLE IF NOT EXISTS AppUser (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,           -- hashed, never plain text
    full_name     VARCHAR(100),
    role          VARCHAR(10)  NOT NULL DEFAULT 'user',
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    DATETIME     NULL,
    CONSTRAINT chk_app_role CHECK (role IN ('admin','user'))
);
-- The first accounts are created by:  python seed_users.py
-- (a password hash cannot be produced in plain SQL)
