-- Initialize Data Warehouse Database
-- This script runs on first container startup

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schemas for Data Warehouse layers
CREATE SCHEMA IF NOT EXISTS staging;    -- Bronze/Staging layer
CREATE SCHEMA IF NOT EXISTS dw;         -- Silver/Core DW layer
CREATE SCHEMA IF NOT EXISTS mart;       -- Gold/Mart layer
CREATE SCHEMA IF NOT EXISTS reconcile;  -- Reconciliation layer

-- Will be populated by dbt models
