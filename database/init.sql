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

-- =============================================================================
-- Web Search Telemetry Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS web_search_telemetry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Request information
    query TEXT NOT NULL,                            -- Search query
    user_id BIGINT,                                 -- User who initiated search (nullable for system searches)
    session_id VARCHAR(255),                        -- Session identifier
    
    -- Request parameters
    result_count_requested INTEGER DEFAULT 10,      -- Requested number of results
    recency_filter VARCHAR(50),                     -- Time filter (oneDay, oneWeek, etc.)
    domain_filter TEXT,                             -- Domain whitelist filter
    
    -- Response information
    status VARCHAR(50) NOT NULL,                    -- success, error, timeout, empty
    results_count INTEGER DEFAULT 0,                -- Actual number of results returned
    results JSONB DEFAULT '[]',                     -- Search results (limited data)
    
    -- Error information
    error_type VARCHAR(255),                        -- Exception class name
    error_message TEXT,                             -- Error message
    error_stack_trace TEXT,                         -- Full stack trace for debugging
    
    -- API response details
    http_status_code INTEGER,                       -- HTTP status code from API
    api_response_time_ms INTEGER,                   -- Time taken for API to respond
    api_session_id VARCHAR(255),                    -- MCP session ID
    
    -- Raw response data for debugging
    raw_response JSONB,                             -- Raw API response (truncated if needed)
    raw_response_truncated BOOLEAN DEFAULT FALSE,   -- Whether raw response was truncated
    
    -- Timing information
    total_duration_ms INTEGER,                      -- Total time for search operation
    init_duration_ms INTEGER,                       -- Time for MCP initialization
    tools_list_duration_ms INTEGER,                 -- Time for tools/list call
    search_call_duration_ms INTEGER,                -- Time for actual search call
    
    -- Provider information
    provider_name VARCHAR(255),                     -- Search provider name
    tool_used VARCHAR(255),                         -- MCP tool name used
    
    -- Retry information
    retry_count INTEGER DEFAULT 0,                  -- Number of retry attempts
    retry_reasons JSONB DEFAULT '[]',               -- List of error categories that triggered retries
    total_retry_delay_ms INTEGER,                   -- Total time spent in retry delays
    
    -- Error classification
    error_category VARCHAR(50),                     -- Classified error category (transient, auth, quota, etc.)
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Migration: Add retry columns if they don't exist (for existing databases)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'web_search_telemetry' AND column_name = 'retry_count') THEN
        ALTER TABLE web_search_telemetry ADD COLUMN retry_count INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'web_search_telemetry' AND column_name = 'retry_reasons') THEN
        ALTER TABLE web_search_telemetry ADD COLUMN retry_reasons JSONB DEFAULT '[]';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'web_search_telemetry' AND column_name = 'total_retry_delay_ms') THEN
        ALTER TABLE web_search_telemetry ADD COLUMN total_retry_delay_ms INTEGER;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'web_search_telemetry' AND column_name = 'error_category') THEN
        ALTER TABLE web_search_telemetry ADD COLUMN error_category VARCHAR(50);
    END IF;
END $$;

-- Indexes for web search telemetry
CREATE INDEX IF NOT EXISTS idx_web_search_telemetry_user_id ON web_search_telemetry(user_id);
CREATE INDEX IF NOT EXISTS idx_web_search_telemetry_session ON web_search_telemetry(session_id);
CREATE INDEX IF NOT EXISTS idx_web_search_telemetry_status ON web_search_telemetry(status);
CREATE INDEX IF NOT EXISTS idx_web_search_telemetry_created ON web_search_telemetry(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_search_telemetry_query ON web_search_telemetry USING gin(to_tsvector('english', query));

-- =============================================================================
-- Web Search Telemetry Views
-- =============================================================================

-- View for failed searches with details
CREATE OR REPLACE VIEW web_search_failures AS
SELECT
    id,
    query,
    user_id,
    session_id,
    status,
    error_type,
    error_message,
    error_category,
    http_status_code,
    api_response_time_ms,
    total_duration_ms,
    retry_count,
    provider_name,
    created_at
FROM web_search_telemetry
WHERE status IN ('error', 'timeout')
ORDER BY created_at DESC;

-- View for empty searches (successful but no results)
CREATE OR REPLACE VIEW web_search_empty_results AS
SELECT
    id,
    query,
    user_id,
    session_id,
    results_count,
    api_response_time_ms,
    total_duration_ms,
    raw_response,
    created_at
FROM web_search_telemetry
WHERE status = 'success' AND results_count = 0
ORDER BY created_at DESC;

-- View for search statistics
CREATE OR REPLACE VIEW web_search_stats AS
SELECT
    DATE(created_at) as search_date,
    COUNT(*) as total_searches,
    COUNT(*) FILTER (WHERE status = 'success') as successful_searches,
    COUNT(*) FILTER (WHERE status = 'error') as failed_searches,
    COUNT(*) FILTER (WHERE status = 'timeout') as timed_out_searches,
    COUNT(*) FILTER (WHERE status = 'success' AND results_count = 0) as empty_result_searches,
    AVG(api_response_time_ms) FILTER (WHERE status = 'success') as avg_response_time_ms,
    AVG(total_duration_ms) as avg_total_duration_ms,
    AVG(results_count) FILTER (WHERE status = 'success') as avg_results_count,
    -- New retry statistics
    SUM(retry_count) as total_retries,
    AVG(retry_count) FILTER (WHERE retry_count > 0) as avg_retries_when_retried,
    COUNT(*) FILTER (WHERE retry_count > 0) as searches_with_retries,
    -- Error category breakdown
    COUNT(*) FILTER (WHERE error_category = 'transient') as transient_errors,
    COUNT(*) FILTER (WHERE error_category = 'auth') as auth_errors,
    COUNT(*) FILTER (WHERE error_category = 'quota') as quota_errors,
    COUNT(*) FILTER (WHERE error_category = 'service') as service_errors
FROM web_search_telemetry
GROUP BY DATE(created_at)
ORDER BY search_date DESC;

-- View for error category analysis
CREATE OR REPLACE VIEW web_search_error_categories AS
SELECT
    error_category,
    COUNT(*) as error_count,
    COUNT(DISTINCT user_id) as affected_users,
    AVG(retry_count) as avg_retries,
    AVG(total_retry_delay_ms) as avg_retry_delay_ms,
    MAX(created_at) as last_occurrence
FROM web_search_telemetry
WHERE error_category IS NOT NULL
GROUP BY error_category
ORDER BY error_count DESC;

-- =============================================================================
-- Cleanup Function for Old Telemetry
-- =============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_telemetry(days_to_keep INTEGER DEFAULT 90)
RETURNS void AS $$
BEGIN
    DELETE FROM web_search_telemetry
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;
