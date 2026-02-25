"""Database migrations module.

This module provides automatic migration support for the database.
Migrations are run on application startup.
"""

import logging
from pathlib import Path

from nergal.database.connection import DatabaseConnection, get_database

logger = logging.getLogger(__name__)


# Migration files in order
MIGRATIONS = [
    ("001_add_user_integrations", """
        -- Migration: Add user_integrations table for external service tokens
        CREATE TABLE IF NOT EXISTS user_integrations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            integration_type VARCHAR(50) NOT NULL,
            encrypted_token TEXT,
            token_hash VARCHAR(255),
            config JSONB DEFAULT '{}',
            is_active BOOLEAN DEFAULT TRUE,
            last_used_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT user_integrations_unique UNIQUE (user_id, integration_type)
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_integrations_user_id ON user_integrations(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_integrations_type ON user_integrations(integration_type);
        CREATE INDEX IF NOT EXISTS idx_user_integrations_active ON user_integrations(is_active) WHERE is_active = TRUE;
        
        CREATE TRIGGER update_user_integrations_updated_at
            BEFORE UPDATE ON user_integrations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """),
    ("003_add_health_metrics", """
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
    """),
]


async def ensure_migrations_table(db: DatabaseConnection) -> None:
    """Ensure the migrations tracking table exists."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)


async def is_migration_applied(db: DatabaseConnection, migration_id: str) -> bool:
    """Check if a migration has been applied."""
    result = await db.fetchrow(
        "SELECT id FROM schema_migrations WHERE id = $1",
        migration_id
    )
    return result is not None


async def apply_migration(db: DatabaseConnection, migration_id: str, sql: str) -> None:
    """Apply a single migration."""
    async with db.transaction() as conn:
        # Execute the migration SQL
        await conn.execute(sql)
        
        # Record the migration
        await conn.execute(
            "INSERT INTO schema_migrations (id) VALUES ($1)",
            migration_id
        )


async def run_migrations(db: DatabaseConnection | None = None) -> list[str]:
    """Run all pending migrations.
    
    Args:
        db: Database connection. If not provided, uses the singleton.
        
    Returns:
        List of applied migration IDs.
    """
    db = db or get_database()
    applied = []
    
    try:
        # Ensure migrations table exists
        await ensure_migrations_table(db)
        
        # Run each migration in order
        for migration_id, sql in MIGRATIONS:
            if await is_migration_applied(db, migration_id):
                logger.debug(f"Migration {migration_id} already applied")
                continue
            
            logger.info(f"Applying migration: {migration_id}")
            await apply_migration(db, migration_id, sql)
            applied.append(migration_id)
            logger.info(f"Migration {migration_id} applied successfully")
        
        if applied:
            logger.info(f"Applied {len(applied)} migration(s)")
        else:
            logger.debug("No pending migrations")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    
    return applied
