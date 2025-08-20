-- USERS tablosu
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    company_name VARCHAR(100),
    is_active BOOLEAN DEFAULT 1
);

-- CAMPAIGNS tablosu
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT,
    encrypted_link TEXT
);

-- CAMPAIGN_TRACKING tablosu
CREATE TABLE IF NOT EXISTS campaign_tracking (
    tracking_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    campaign_id INT,
    clicked BOOLEAN DEFAULT 0,
    opened BOOLEAN DEFAULT 0,
    compromised BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
);

-- IMPORT_LOGS tablosu
CREATE TABLE IF NOT EXISTS import_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    file_name TEXT,
    imported_by VARCHAR(100),
    import_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_rows INT,
    success_count INT,
    error_count INT
);

-- ERROR_LOGS tablosu
CREATE TABLE IF NOT EXISTS error_logs (
    error_id INT AUTO_INCREMENT PRIMARY KEY,
    error_message TEXT,
    stack_trace TEXT,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    component VARCHAR(100)
);

-- ACTION_LOGS tablosu
CREATE TABLE IF NOT EXISTS action_logs (
    action_id INT AUTO_INCREMENT PRIMARY KEY,
    user VARCHAR(100),
    action_type ENUM('add', 'edit', 'delete'),
    affected_table VARCHAR(50),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- LOGIN_ATTEMPTS tablosu
CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    campaign_id INT,
    submitted_email VARCHAR(150),
    submitted_pass VARCHAR(150),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
);