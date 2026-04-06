"""
CONFIT Backend - FCM Tokens Migration
====================================
Adds fcm_tokens JSONB column to users table for push notification support.

Revision: 0007
Revises: 0006_egypt_payment_stack
Created: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = '0007_fcm_tokens'
down_revision = '0006_egypt_payment_stack'
branch_labels = None
depends_on = None


def upgrade():
    """Add FCM tokens column to users table."""
    
    # Check if we're using PostgreSQL
    bind = op.get_bind()
    dialect = bind.dialect.name
    
    if dialect == 'postgresql':
        # PostgreSQL: Use JSONB for efficient querying
        op.add_column(
            'users',
            sa.Column('fcm_tokens', JSONB, nullable=True, default=list)
        )
        
        # Add GIN index for JSONB queries
        op.execute(
            "CREATE INDEX idx_users_fcm_tokens ON users USING GIN (fcm_tokens)"
        )
    else:
        # SQLite/others: Use JSON
        op.add_column(
            'users',
            sa.Column('fcm_tokens', sa.JSON, nullable=True, default=list)
        )
    
    # Add column for notification preferences defaults
    op.add_column(
        'users',
        sa.Column('notification_channels', sa.JSON, nullable=True, default=dict)
    )
    
    # Add updated_at trigger for fcm_tokens modifications
    op.execute("""
        CREATE OR REPLACE FUNCTION update_fcm_tokens_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.fcm_tokens != OLD.fcm_tokens THEN
                NEW.updated_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS trigger_update_fcm_tokens ON users;
        CREATE TRIGGER trigger_update_fcm_tokens
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_fcm_tokens_timestamp();
    """)


def downgrade():
    """Remove FCM tokens column from users table."""
    
    bind = op.get_bind()
    dialect = bind.dialect.name
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_update_fcm_tokens ON users")
    op.execute("DROP FUNCTION IF EXISTS update_fcm_tokens_timestamp()")
    
    # Drop index
    if dialect == 'postgresql':
        op.execute("DROP INDEX IF EXISTS idx_users_fcm_tokens")
    
    # Drop columns
    op.drop_column('users', 'notification_channels')
    op.drop_column('users', 'fcm_tokens')
