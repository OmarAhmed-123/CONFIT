"""AI Features Tables - MUSE, MIRROR, Visual Search, Cost Tracking

Revision ID: 0008
Revises: 0007_multi_actor_notifications
Create Date: 2026-04-18

Adds:
- try_on_sessions: Virtual try-on sessions
- ai_cost_logs: AI service cost tracking
- ai_cost_daily_summary: Aggregated daily costs
- wardrobe_items: Virtual wardrobe with embeddings
- product embeddings column extension
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0008_ai_features_tables'
down_revision = '0007_multi_actor_notifications'
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgvector extension if not exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # ==========================================
    # Try-On Sessions Table
    # ==========================================
    op.create_table(
        'try_on_sessions',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('person_image_key', sa.String(255)),
        sa.Column('garment_image_key', sa.String(255)),
        sa.Column('result_image_key', sa.String(255)),
        sa.Column('result_url', sa.Text),
        sa.Column('quality_score', sa.Float, default=0.0),
        sa.Column('replicate_id', sa.String(100)),
        sa.Column('cost_usd', sa.Float, default=0.0),
        sa.Column('latency_ms', sa.Float, default=0.0),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_try_on_sessions_user_id', 'try_on_sessions', ['user_id'])
    op.create_index('ix_try_on_sessions_product_id', 'try_on_sessions', ['product_id'])
    op.create_index('ix_try_on_sessions_status', 'try_on_sessions', ['status'])
    op.create_index('ix_try_on_sessions_created_at', 'try_on_sessions', ['created_at'])
    
    # ==========================================
    # AI Cost Logs Table
    # ==========================================
    op.create_table(
        'ai_cost_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('service', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100)),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('session_id', sa.String(50)),
        sa.Column('tokens_in', sa.Integer, default=0),
        sa.Column('tokens_out', sa.Integer, default=0),
        sa.Column('cost_usd', sa.Float, nullable=False, default=0.0),
        sa.Column('latency_ms', sa.Float, default=0.0),
        sa.Column('success', sa.Boolean, default=True),
        sa.Column('error_message', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    op.create_index('ix_ai_cost_logs_service', 'ai_cost_logs', ['service'])
    op.create_index('ix_ai_cost_logs_user_id', 'ai_cost_logs', ['user_id'])
    op.create_index('ix_ai_cost_logs_created_at', 'ai_cost_logs', ['created_at'])
    op.create_index('ix_ai_cost_logs_service_created', 'ai_cost_logs', ['service', 'created_at'])
    
    # ==========================================
    # AI Cost Daily Summary Table
    # ==========================================
    op.create_table(
        'ai_cost_daily_summary',
        sa.Column('summary_date', sa.Date, primary_key=True),
        sa.Column('service', sa.String(50), primary_key=True),
        sa.Column('total_cost_usd', sa.Float, nullable=False, default=0.0),
        sa.Column('total_calls', sa.Integer, nullable=False, default=0),
        sa.Column('total_tokens_in', sa.Integer, default=0),
        sa.Column('total_tokens_out', sa.Integer, default=0),
        sa.Column('avg_latency_ms', sa.Float, default=0.0),
        sa.Column('success_rate', sa.Float, default=1.0),
        sa.Column('unique_users', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    op.create_index('ix_ai_cost_daily_summary_date', 'ai_cost_daily_summary', ['summary_date'])
    op.create_index('ix_ai_cost_daily_summary_service', 'ai_cost_daily_summary', ['service'])
    
    # ==========================================
    # Wardrobe Items Table
    # ==========================================
    op.create_table(
        'wardrobe_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('subcategory', sa.String(50)),
        sa.Column('colors', postgresql.JSONB, server_default='[]'),
        sa.Column('patterns', postgresql.JSONB, server_default='[]'),
        sa.Column('materials', postgresql.JSONB, server_default='[]'),
        sa.Column('brands', postgresql.JSONB, server_default='[]'),
        sa.Column('tags', postgresql.JSONB, server_default='[]'),
        sa.Column('image_key', sa.String(255)),
        sa.Column('embedding', postgresql.ARRAY(sa.Float, dimensions=1)),
        sa.Column('purchase_date', sa.Date),
        sa.Column('purchase_price', sa.Float),
        sa.Column('purchase_store', sa.String(100)),
        sa.Column('times_worn', sa.Integer, default=0),
        sa.Column('last_worn', sa.Date),
        sa.Column('is_favorite', sa.Boolean, default=False),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_wardrobe_items_user_id', 'wardrobe_items', ['user_id'])
    op.create_index('ix_wardrobe_items_category', 'wardrobe_items', ['category'])
    op.create_index('ix_wardrobe_items_user_category', 'wardrobe_items', ['user_id', 'category'])
    
    # Create vector index for embeddings (using ivfflat for approximate nearest neighbor)
    op.execute("""
        CREATE INDEX ix_wardrobe_items_embedding 
        ON wardrobe_items 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE embedding IS NOT NULL
    """)
    
    # ==========================================
    # Wardrobe Item Purchases (link to products)
    # ==========================================
    op.create_table(
        'wardrobe_item_purchases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('wardrobe_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True)),
        sa.Column('product_sku', sa.String(50)),
        sa.Column('order_id', postgresql.UUID(as_uuid=True)),
        sa.Column('purchase_price', sa.Float),
        sa.Column('purchased_at', sa.DateTime(timezone=True)),
        
        sa.ForeignKeyConstraint(['wardrobe_item_id'], ['wardrobe_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
    )
    
    op.create_index('ix_wardrobe_item_purchases_item', 'wardrobe_item_purchases', ['wardrobe_item_id'])
    op.create_index('ix_wardrobe_item_purchases_sku', 'wardrobe_item_purchases', ['product_sku'])
    
    # ==========================================
    # Add Embedding Column to Products Table
    # ==========================================
    op.add_column('products', sa.Column('embedding', postgresql.ARRAY(sa.Float, dimensions=1)))
    
    # Create vector index for product embeddings
    op.execute("""
        CREATE INDEX ix_products_embedding 
        ON products 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE embedding IS NOT NULL
    """)
    
    # ==========================================
    # Muse Chat Sessions (optional, for context)
    # ==========================================
    op.create_table(
        'muse_sessions',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('language', sa.String(2), default='en'),
        sa.Column('style_profile_snapshot', postgresql.JSONB),
        sa.Column('total_messages', sa.Integer, default=0),
        sa.Column('total_tokens_in', sa.Integer, default=0),
        sa.Column('total_tokens_out', sa.Integer, default=0),
        sa.Column('total_cost_usd', sa.Float, default=0.0),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('last_message_at', sa.DateTime(timezone=True)),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_muse_sessions_user_id', 'muse_sessions', ['user_id'])
    op.create_index('ix_muse_sessions_started_at', 'muse_sessions', ['started_at'])
    
    # ==========================================
    # Muse Messages (for history)
    # ==========================================
    op.create_table(
        'muse_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.String(50), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),  # user, assistant, system
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tokens', sa.Integer, default=0),
        sa.Column('outfit_recommendations', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['session_id'], ['muse_sessions.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_muse_messages_session_id', 'muse_messages', ['session_id'])
    op.create_index('ix_muse_messages_created_at', 'muse_messages', ['created_at'])


def downgrade():
    # Drop Muse tables
    op.drop_index('ix_muse_messages_created_at', 'muse_messages')
    op.drop_index('ix_muse_messages_session_id', 'muse_messages')
    op.drop_table('muse_messages')
    
    op.drop_index('ix_muse_sessions_started_at', 'muse_sessions')
    op.drop_index('ix_muse_sessions_user_id', 'muse_sessions')
    op.drop_table('muse_sessions')
    
    # Drop product embedding index and column
    op.execute("DROP INDEX IF EXISTS ix_products_embedding")
    op.drop_column('products', 'embedding')
    
    # Drop wardrobe tables
    op.drop_index('ix_wardrobe_item_purchases_sku', 'wardrobe_item_purchases')
    op.drop_index('ix_wardrobe_item_purchases_item', 'wardrobe_item_purchases')
    op.drop_table('wardrobe_item_purchases')
    
    op.execute("DROP INDEX IF EXISTS ix_wardrobe_items_embedding")
    op.drop_index('ix_wardrobe_items_user_category', 'wardrobe_items')
    op.drop_index('ix_wardrobe_items_category', 'wardrobe_items')
    op.drop_index('ix_wardrobe_items_user_id', 'wardrobe_items')
    op.drop_table('wardrobe_items')
    
    # Drop cost tracking tables
    op.drop_index('ix_ai_cost_daily_summary_service', 'ai_cost_daily_summary')
    op.drop_index('ix_ai_cost_daily_summary_date', 'ai_cost_daily_summary')
    op.drop_table('ai_cost_daily_summary')
    
    op.drop_index('ix_ai_cost_logs_service_created', 'ai_cost_logs')
    op.drop_index('ix_ai_cost_logs_created_at', 'ai_cost_logs')
    op.drop_index('ix_ai_cost_logs_user_id', 'ai_cost_logs')
    op.drop_index('ix_ai_cost_logs_service', 'ai_cost_logs')
    op.drop_table('ai_cost_logs')
    
    # Drop try-on sessions
    op.drop_index('ix_try_on_sessions_created_at', 'try_on_sessions')
    op.drop_index('ix_try_on_sessions_status', 'try_on_sessions')
    op.drop_index('ix_try_on_sessions_product_id', 'try_on_sessions')
    op.drop_index('ix_try_on_sessions_user_id', 'try_on_sessions')
    op.drop_table('try_on_sessions')
    
    # Note: We don't drop the vector extension as it may be used by other tables
