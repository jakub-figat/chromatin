-- Create test database if it doesn't exist
SELECT 'CREATE DATABASE chromatin_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chromatin_test')\gexec