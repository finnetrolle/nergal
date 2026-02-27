-- Migration: Add general_reminders table for arbitrary user reminders
-- This table stores user-configured reminders for any purpose

-- Create general_reminders table
CREATE TABLE IF NOT EXISTS general_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User who owns this reminder
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Reminder content
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Reminder time (hour and minute in user's timezone)
    reminder_time TIME NOT NULL,
    
    -- Date when reminder should be sent (for one-time reminders)
    reminder_date DATE,
    
    -- User's timezone at time of creation
    user_timezone VARCHAR(50),
    
    -- Whether reminder is active
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Whether this is a recurring reminder (daily)
    is_recurring BOOLEAN DEFAULT FALSE,
    
    -- Days of week for recurring reminders (0=Monday, 6=Sunday, stored as array)
    recurring_days INTEGER[] DEFAULT ARRAY[0,1,2,3,4,5,6],
    
    -- Last reminder sent
    last_sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_general_reminders_user_id ON general_reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_general_reminders_active ON general_reminders(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_general_reminders_time ON general_reminders(reminder_time);

-- Trigger for updated_at
CREATE TRIGGER update_general_reminders_updated_at
    BEFORE UPDATE ON general_reminders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE general_reminders IS 'Stores general-purpose reminders for users';
COMMENT ON COLUMN general_reminders.recurring_days IS 'Days of week for recurring reminders: 0=Monday, 6=Sunday';
