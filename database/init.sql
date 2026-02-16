-- Nergal Bot Database Initialization Script
-- This script creates the necessary tables for user memory management

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Users Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,                          -- Telegram user ID
    telegram_username VARCHAR(255),                 -- Telegram username
    first_name VARCHAR(255),                        -- User's first name
    last_name VARCHAR(255),                         -- User's last name
    language_code VARCHAR(10),                      -- User's language code
    is_allowed BOOLEAN DEFAULT FALSE,               -- Whether user is allowed to use the bot
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT users_telegram_username_key UNIQUE (telegram_username)
);

-- Index for faster lookups by username
CREATE INDEX IF NOT EXISTS idx_users_telegram_username ON users(telegram_username);

-- Index for faster lookups by is_allowed status
CREATE INDEX IF NOT EXISTS idx_users_is_allowed ON users(is_allowed) WHERE is_allowed = TRUE;

-- =============================================================================
-- Migration: Add is_allowed column if it doesn't exist (for existing databases)
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'is_allowed') THEN
        ALTER TABLE users ADD COLUMN is_allowed BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- =============================================================================
-- Long-term Memory (User Profile) Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Personal information
    preferred_name VARCHAR(255),                    -- How the user prefers to be called
    age INTEGER,                                    -- User's age
    location VARCHAR(255),                          -- City, country
    timezone VARCHAR(50),                           -- User's timezone
    occupation VARCHAR(255),                        -- Job or profession
    languages TEXT[],                               -- Languages the user speaks
    
    -- Preferences
    interests TEXT[],                               -- Topics of interest
    expertise_areas TEXT[],                         -- Areas of expertise
    communication_style VARCHAR(50),                -- preferred communication style
    
    -- Additional profile data as JSONB for flexibility
    custom_attributes JSONB DEFAULT '{}',           -- Any other collected information
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT user_profiles_user_id_key UNIQUE (user_id)
);

-- =============================================================================
-- Profile Facts Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS profile_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    fact_type VARCHAR(100) NOT NULL,                -- Type of fact (name, location, interest, etc.)
    fact_key VARCHAR(255) NOT NULL,                 -- Specific key (e.g., "favorite_color")
    fact_value TEXT NOT NULL,                       -- The actual fact value
    confidence FLOAT DEFAULT 1.0,                    -- Confidence level (0-1)
    source VARCHAR(255),                            -- How this fact was learned
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,            -- Optional expiration for temporary facts
    
    CONSTRAINT profile_facts_unique UNIQUE (user_id, fact_type, fact_key)
);

-- Indexes for profile facts
CREATE INDEX IF NOT EXISTS idx_profile_facts_user_id ON profile_facts(user_id);
CREATE INDEX IF NOT EXISTS idx_profile_facts_type ON profile_facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_profile_facts_expires ON profile_facts(expires_at) WHERE expires_at IS NOT NULL;

-- =============================================================================
-- Short-term Memory (Conversation History) Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,               -- Conversation session identifier
    
    role VARCHAR(20) NOT NULL,                      -- 'user', 'assistant', or 'system'
    content TEXT NOT NULL,                          -- Message content
    
    -- Metadata
    agent_type VARCHAR(100),                        -- Which agent handled this message
    tokens_used INTEGER,                            -- Token count if available
    processing_time_ms INTEGER,                     -- Processing time in milliseconds
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for conversation history
CREATE INDEX IF NOT EXISTS idx_conversation_messages_user_id ON conversation_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_session ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created ON conversation_messages(created_at DESC);

-- =============================================================================
-- Memory Extraction Events Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS memory_extraction_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id UUID REFERENCES conversation_messages(id) ON DELETE SET NULL,
    
    extracted_facts JSONB NOT NULL,                 -- Facts extracted from the message
    extraction_confidence FLOAT,                    -- Overall confidence of extraction
    was_applied BOOLEAN DEFAULT FALSE,              -- Whether facts were applied to profile
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for extraction events
CREATE INDEX IF NOT EXISTS idx_memory_extraction_user_id ON memory_extraction_events(user_id);

-- =============================================================================
-- Sessions Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id VARCHAR(255) PRIMARY KEY,                    -- Session identifier
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,              -- When session ended
    message_count INTEGER DEFAULT 0,                -- Number of messages in session
    
    metadata JSONB DEFAULT '{}'                     -- Additional session metadata
);

-- Index for sessions
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_started ON conversation_sessions(started_at DESC);

-- =============================================================================
-- Functions and Triggers
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profile_facts_updated_at
    BEFORE UPDATE ON profile_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Cleanup Function for Old Messages
-- =============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_messages(days_to_keep INTEGER DEFAULT 30)
RETURNS void AS $$
BEGIN
    DELETE FROM conversation_messages
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    DELETE FROM memory_extraction_events
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL
    AND was_applied = TRUE;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Views for Common Queries
-- =============================================================================

-- View for getting user's complete profile with facts
CREATE OR REPLACE VIEW user_complete_profile AS
SELECT 
    u.id AS user_id,
    u.telegram_username,
    u.first_name,
    u.last_name,
    u.language_code,
    p.preferred_name,
    p.age,
    p.location,
    p.timezone,
    p.occupation,
    p.languages,
    p.interests,
    p.expertise_areas,
    p.communication_style,
    p.custom_attributes,
    jsonb_object_agg(
        pf.fact_type || '.' || pf.fact_key,
        jsonb_build_object(
            'value', pf.fact_value,
            'confidence', pf.confidence,
            'source', pf.source
        )
    ) AS facts
FROM users u
LEFT JOIN user_profiles p ON u.id = p.user_id
LEFT JOIN profile_facts pf ON u.id = pf.user_id
GROUP BY u.id, u.telegram_username, u.first_name, u.last_name, u.language_code,
         p.preferred_name, p.age, p.location, p.timezone, p.occupation,
         p.languages, p.interests, p.expertise_areas, p.communication_style, p.custom_attributes;

-- View for recent conversation history
CREATE OR REPLACE VIEW recent_conversations AS
SELECT 
    cm.user_id,
    cm.session_id,
    cm.role,
    cm.content,
    cm.agent_type,
    cm.created_at,
    u.telegram_username
FROM conversation_messages cm
JOIN users u ON cm.user_id = u.id
ORDER BY cm.created_at DESC
LIMIT 1000;
