-- 白名單（透過 phpMyAdmin 手動 insert 維護）
CREATE TABLE IF NOT EXISTS whitelist_users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  line_user_id VARCHAR(64) NOT NULL UNIQUE,
  display_name VARCHAR(100),
  note VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 持股
CREATE TABLE IF NOT EXISTS stock_holdings (
  id BINARY(16) NOT NULL PRIMARY KEY,
  line_user_id VARCHAR(64) NOT NULL,
  market ENUM('TW','US') NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  name VARCHAR(100),
  category VARCHAR(50),
  shares DECIMAL(18,4) NOT NULL,
  avg_price DECIMAL(18,4) NOT NULL,
  purchase_date DATE,
  note VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user (line_user_id),
  INDEX idx_user_category (line_user_id, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
