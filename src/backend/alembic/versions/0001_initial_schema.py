"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-04 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column("account_holder_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_account_number"), "accounts", ["account_number"], unique=True)
    op.create_index(op.f("ix_accounts_id"), "accounts", ["id"], unique=False)

    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portfolios_id"), "portfolios", ["id"], unique=False)

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("average_cost", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_positions_id"), "positions", ["id"], unique=False)

    op.create_table(
        "price_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_data_id"), "price_data", ["id"], unique=False)
    op.create_index(op.f("ix_price_data_symbol"), "price_data", ["symbol"], unique=False)

    op.create_table(
        "risk_calculations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("var_historical", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("var_parametric", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("var_monte_carlo", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("expected_shortfall", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("confidence_level", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("time_horizon_days", sa.Integer(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_calculations_id"), "risk_calculations", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_calculations_id"), table_name="risk_calculations")
    op.drop_table("risk_calculations")
    op.drop_index(op.f("ix_price_data_symbol"), table_name="price_data")
    op.drop_index(op.f("ix_price_data_id"), table_name="price_data")
    op.drop_table("price_data")
    op.drop_index(op.f("ix_positions_id"), table_name="positions")
    op.drop_table("positions")
    op.drop_index(op.f("ix_portfolios_id"), table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_index(op.f("ix_accounts_account_number"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_id"), table_name="accounts")
    op.drop_table("accounts")
