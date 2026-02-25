-- Migration: Add health metrics tables
-- This migration creates tables for storing user health metrics like blood pressure

-- =============================================================================
-- Blood Pressure Measurements Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS blood_pressure_measurements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Measurement time (stored as UTC)
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Three consecutive readings (systolic/diastolic in mmHg)
    systolic_1 INTEGER NOT NULL CHECK (systolic_1 > 0 AND systolic_1 < 300),
    diastolic_1 INTEGER NOT NULL CHECK (diastolic_1 > 0 AND diastolic_1 < 200),
    
    systolic_2 INTEGER NOT NULL CHECK (systolic_2 > 0 AND systolic_2 < 300),
    diastolic_2 INTEGER NOT NULL CHECK (diastolic_2 > 0 AND diastolic_2 < 200),
    
    systolic_3 INTEGER NOT NULL CHECK (systolic_3 > 0 AND systolic_3 < 300),
    diastolic_3 INTEGER NOT NULL CHECK (diastolic_3 > 0 AND diastolic_3 < 200),
    
    -- Calculated averages
    systolic_avg FLOAT NOT NULL,
    diastolic_avg FLOAT NOT NULL,
    
    -- Optional notes
    notes TEXT,
    
    -- User's timezone at time of measurement
    user_timezone VARCHAR(50),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for blood pressure measurements
CREATE INDEX IF NOT EXISTS idx_bp_measurements_user_id ON blood_pressure_measurements(user_id);
CREATE INDEX IF NOT EXISTS idx_bp_measurements_measured_at ON blood_pressure_measurements(measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_bp_measurements_user_date ON blood_pressure_measurements(user_id, measured_at DESC);

-- =============================================================================
-- Health Reminders Table (for future extensibility)
-- =============================================================================

CREATE TABLE IF NOT EXISTS health_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Reminder type (blood_pressure, weight, medication, etc.)
    reminder_type VARCHAR(50) NOT NULL,
    
    -- Reminder time (hour and minute in user's timezone)
    reminder_time TIME NOT NULL,
    
    -- User's timezone
    user_timezone VARCHAR(50),
    
    -- Whether reminder is active
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Last reminder sent
    last_sent_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT health_reminders_unique UNIQUE (user_id, reminder_type, reminder_time)
);

-- Index for health reminders
CREATE INDEX IF NOT EXISTS idx_health_reminders_user_id ON health_reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_health_reminders_active ON health_reminders(is_active) WHERE is_active = TRUE;

-- Trigger for updated_at
CREATE TRIGGER update_health_reminders_updated_at
    BEFORE UPDATE ON health_reminders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
