"""Multi-Actor Notification System - actor_type, actor_id, triggers, DND, localization

Revision ID: 0007_multi_actor_notifications
Revises: 0006_egypt_payment_stack
Create Date: 2024-01-19

Changes:
    - Add ActorType enum (CUSTOMER, STORE, FACTORY, DONOR, ADMIN)
    - Add actor_type, actor_id columns to notifications table
    - Add trigger, channel, status, read_at, send_at, provider_message_id columns
    - Extend notification_preferences with language, DND, categories
    - Add push_enabled, email_enabled, sms_enabled, whatsapp_enabled columns
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision = "0007_multi_actor_notifications"
down_revision = "0006_egypt_payment_stack"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply multi-actor notification system changes."""
    
    # 1. Create ActorType enum
    actor_type_enum = ENUM(
        'CUSTOMER', 'STORE', 'FACTORY', 'DONOR', 'ADMIN',
        name='actortype',
        create_type=True
    )
    actor_type_enum.create(op.get_bind(), checkfirst=True)
    
    # 2. Add columns to notifications table
    # Actor type and ID for multi-actor support
    op.add_column(
        'notifications',
        sa.Column('actor_type', actor_type_enum, nullable=False, server_default='CUSTOMER'),
    )
    op.add_column(
        'notifications',
        sa.Column('actor_id', sa.String(36), nullable=False),
    )
    op.create_index('ix_notifications_actor_id', 'notifications', ['actor_id'])
    
    # Trigger column for lifecycle events
    op.add_column(
        'notifications',
        sa.Column('trigger', sa.String(64), nullable=False, server_default='general'),
    )
    op.create_index('ix_notifications_trigger', 'notifications', ['trigger'])
    
    # Channel column for delivery channel
    op.add_column(
        'notifications',
        sa.Column('channel', sa.String(32), nullable=True),
    )
    op.create_index('ix_notifications_channel', 'notifications', ['channel'])
    
    # Status column (QUEUED, SENT, DELIVERED, READ, FAILED)
    op.add_column(
        'notifications',
        sa.Column('status', sa.String(32), nullable=False, server_default='QUEUED'),
    )
    op.create_index('ix_notifications_status', 'notifications', ['status'])
    
    # Read timestamp
    op.add_column(
        'notifications',
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # DND scheduling
    op.add_column(
        'notifications',
        sa.Column('send_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Provider message ID for webhook callbacks
    op.add_column(
        'notifications',
        sa.Column('provider_message_id', sa.String(255), nullable=True),
    )
    op.create_index('ix_notifications_provider_message_id', 'notifications', ['provider_message_id'])
    
    # 3. Update notification_preferences table
    # Add individual channel toggles
    op.add_column(
        'notification_preferences',
        sa.Column('push_enabled', sa.Boolean, nullable=False, server_default='true'),
    )
    op.add_column(
        'notification_preferences',
        sa.Column('email_enabled', sa.Boolean, nullable=False, server_default='true'),
    )
    op.add_column(
        'notification_preferences',
        sa.Column('sms_enabled', sa.Boolean, nullable=False, server_default='true'),
    )
    op.add_column(
        'notification_preferences',
        sa.Column('whatsapp_enabled', sa.Boolean, nullable=False, server_default='false'),
    )
    op.add_column(
        'notification_preferences',
        sa.Column('in_app_enabled', sa.Boolean, nullable=False, server_default='true'),
    )
    
    # Categories JSON column
    op.add_column(
        'notification_preferences',
        sa.Column(
            'categories',
            sa.JSON,
            nullable=False,
            server_default='{"orders": true, "styling": true, "promotions": true, "donor_impact": true}'
        ),
    )
    
    # Language preference
    op.add_column(
        'notification_preferences',
        sa.Column('language', sa.String(2), nullable=False, server_default='en'),
    )
    
    # DND hours
    op.add_column(
        'notification_preferences',
        sa.Column('dnd_start', sa.String(5), nullable=True),
    )
    op.add_column(
        'notification_preferences',
        sa.Column('dnd_end', sa.String(5), nullable=True),
    )
    
    # 4. Update existing notifications with default values
    # Set actor_type to CUSTOMER for existing records
    op.execute(
        "UPDATE notifications SET actor_type = 'CUSTOMER' WHERE actor_type IS NULL"
    )
    # Set actor_id to receiver_id for existing records (customer notifications)
    op.execute(
        "UPDATE notifications SET actor_id = receiver_id WHERE actor_id IS NULL"
    )
    # Set trigger based on existing metadata
    op.execute(
        "UPDATE notifications SET trigger = COALESCE(metadata->>'event', 'general') WHERE trigger = 'general'"
    )
    
    # 5. Set language based on phone number for existing preferences (Egypt = Arabic)
    op.execute(
        """
        UPDATE notification_preferences np
        SET language = 'ar'
        FROM users u
        WHERE np.recipient_id = u.id
        AND u.phone LIKE '+20%'
        AND np.language = 'en'
        """
    )


def downgrade() -> None:
    """Revert multi-actor notification system changes."""
    
    # Drop notification_preferences columns
    op.drop_column('notification_preferences', 'dnd_end')
    op.drop_column('notification_preferences', 'dnd_start')
    op.drop_column('notification_preferences', 'language')
    op.drop_column('notification_preferences', 'categories')
    op.drop_column('notification_preferences', 'in_app_enabled')
    op.drop_column('notification_preferences', 'whatsapp_enabled')
    op.drop_column('notification_preferences', 'sms_enabled')
    op.drop_column('notification_preferences', 'email_enabled')
    op.drop_column('notification_preferences', 'push_enabled')
    
    # Drop notifications columns
    op.drop_index('ix_notifications_provider_message_id', table_name='notifications')
    op.drop_column('notifications', 'provider_message_id')
    op.drop_column('notifications', 'send_at')
    op.drop_column('notifications', 'read_at')
    op.drop_index('ix_notifications_status', table_name='notifications')
    op.drop_column('notifications', 'status')
    op.drop_index('ix_notifications_channel', table_name='notifications')
    op.drop_column('notifications', 'channel')
    op.drop_index('ix_notifications_trigger', table_name='notifications')
    op.drop_column('notifications', 'trigger')
    op.drop_index('ix_notifications_actor_id', table_name='notifications')
    op.drop_column('notifications', 'actor_id')
    op.drop_column('notifications', 'actor_type')
    
    # Drop ActorType enum
    op.execute("DROP TYPE IF EXISTS actortype")
