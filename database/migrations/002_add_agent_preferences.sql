-- Migration: Add user_agent_preferences table
-- Description: Stores user preferences for different agent types
-- Created: 2024-01-01

-- Create user_agent_preferences table
CREATE TABLE IF NOT EXISTS user_agent_preferences (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    weight FLOAT NOT NULL DEFAULT 0.0 CHECK (weight >= -1.0 AND weight <= 1.0),
    keywords TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one preference per user per agent type
    UNIQUE(user_id, agent_type)
);

-- Create index for faster lookups by user_id
CREATE INDEX IF NOT EXISTS idx_user_agent_preferences_user_id ON user_agent_preferences(user_id);

-- Create index for lookups by agent_type
CREATE INDEX IF NOT EXISTS idx_user_agent_preferences_agent_type ON user_agent_preferences(agent_type);

-- Create composite index for user_id + agent_type lookups
CREATE INDEX IF NOT EXISTS idx_user_agent_preferences_user_agent ON user_agent_preferences(user_id, agent_type);

-- Add comment to table
COMMENT ON TABLE user_agent_preferences IS 'Stores user-specific preferences for agent prioritization';
COMMENT ON COLUMN user_agent_preferences.user_id IS 'Telegram user ID';
COMMENT ON COLUMN user_agent_preferences.agent_type IS 'Type of agent (e.g., web_search, todoist, news)';
COMMENT ON COLUMN user_agent_preferences.weight IS 'Preference weight from -1.0 (avoid) to 1.0 (prefer)';
COMMENT ON COLUMN user_agent_preferences.keywords IS 'List of keywords that trigger this preference';
