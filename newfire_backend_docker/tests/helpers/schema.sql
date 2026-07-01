-- Test Database Schema for NewFire Backend Tenant/RBAC Tests
-- This schema creates all tables needed for isolated testing

-- Drop existing tables if they exist (for clean test setup)
DROP TABLE IF EXISTS client_notes CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    onboarded BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now()
);

-- Companies table (tenants)
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    paperclip_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT now()
);

-- Agents table
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role TEXT,
    description TEXT,
    system_prompt TEXT,
    model VARCHAR(100) DEFAULT 'gemma4:26b',
    provider VARCHAR(50) DEFAULT 'local',
    openclaw_worker_id VARCHAR(255),
    icon VARCHAR(50) DEFAULT 'MessageSquare',
    color VARCHAR(100) DEFAULT 'from-blue-500 to-blue-600',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now()
);

-- Conversations table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    messages JSONB DEFAULT '[]',
    updated_at TIMESTAMP DEFAULT now()
);

-- Client notes table
CREATE TABLE client_notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_agents_company_id ON agents(company_id);
CREATE INDEX idx_conversations_user_agent ON conversations(user_id, agent_id);
CREATE INDEX idx_companies_user_id ON companies(user_id);
CREATE INDEX idx_users_email ON users(email);

-- Comments for documentation
COMMENT ON TABLE users IS 'Application users with authentication credentials';
COMMENT ON TABLE companies IS 'Tenant/company entities that own agents and data';
COMMENT ON TABLE agents IS 'AI agents owned by companies with tenant isolation';
COMMENT ON TABLE conversations IS 'Chat conversations between users and agents';
COMMENT ON TABLE client_notes IS 'Key-value notes associated with users';