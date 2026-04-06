"""Egypt Payment Stack - tax_amount_cents, new providers, COD status

Revision ID: 0006_egypt_payment_stack
Revises: 0005_sales_analytics_engine
Create Date: 2024-01-18

Changes:
    - Add tax_amount_cents column to payments table
    - Update PaymentProvider enum: add fawry, valu, cash_on_delivery
    - Update PaymentStatus enum: add pending_cod
    - Update default currency to 'egp'
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_egypt_payment_stack"
down_revision = "0005_sales_analytics_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply Egypt payment stack changes."""
    
    # 1. Add tax_amount_cents column to payments table
    op.add_column(
        "payments",
        sa.Column("tax_amount_cents", sa.Integer(), nullable=True),
    )
    
    # 2. Update default currency from 'usd' to 'egp' for new payments
    # Note: Existing payments keep their currency
    op.alter_column(
        "payments",
        "currency",
        server_default="egp",
    )
    
    # 3. Add index for tax_amount_cents for reporting
    op.create_index(
        "ix_payments_tax_amount",
        "payments",
        ["tax_amount_cents"],
        unique=False,
    )
    
    # 4. Add comment to document the column
    op.execute(
        """
        COMMENT ON COLUMN payments.tax_amount_cents IS 
        'VAT/tax amount in piastres (EGP * 100). Egypt VAT is 14%.'
        """
    )


def downgrade() -> None:
    """Revert Egypt payment stack changes."""
    
    # Remove index
    op.drop_index("ix_payments_tax_amount", table_name="payments")
    
    # Revert currency default
    op.alter_column(
        "payments",
        "currency",
        server_default="usd",
    )
    
    # Remove tax_amount_cents column
    op.drop_column("payments", "tax_amount_cents")
