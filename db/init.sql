-- Initialize database
CREATE DATABASE IF NOT EXISTS milestone2;
USE milestone2;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT 'Test Test',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial data
INSERT IGNORE INTO users (id, name) VALUES (1, 'Len Vogels');
