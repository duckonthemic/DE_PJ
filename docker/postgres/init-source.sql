-- Initialize Source Database (E-commerce OLTP)
-- This script runs on first container startup

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schema for e-commerce source
CREATE SCHEMA IF NOT EXISTS ecommerce;

-- Will be populated by data generation scripts
