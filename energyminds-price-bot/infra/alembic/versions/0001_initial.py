"""initial schema"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_day",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.CheckConstraint("market IN ('DAM','GDAM','RTM')", name="ck_market"),
        sa.UniqueConstraint("market", "trade_date", name="uq_market_trade_date"),
    )

    op.create_table(
        "dam_price",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("market_day_id", sa.BigInteger(), nullable=False),
        sa.Column("hour_block", sa.SmallInteger(), nullable=False),
        sa.Column("mcp_rs_per_mwh", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("hour_block BETWEEN 0 AND 23", name="ck_dam_hour_block"),
        sa.UniqueConstraint("market_day_id", "hour_block", name="dam_uniq"),
        sa.ForeignKeyConstraint(["market_day_id"], ["market_day.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_dam_mday_hour", "dam_price", ["market_day_id", "hour_block"], unique=False)

    op.create_table(
        "gdam_price",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("market_day_id", sa.BigInteger(), nullable=False),
        sa.Column("quarter_index", sa.SmallInteger(), nullable=False),
        sa.Column("mcp_rs_per_mwh", sa.Numeric(10, 2), nullable=False),
        sa.Column("hydro_fsv_mw", sa.Numeric(12, 2), nullable=True),
        sa.Column("scheduled_volume_mw", sa.Numeric(12, 2), nullable=True),
        sa.CheckConstraint("quarter_index BETWEEN 0 AND 95", name="ck_gdam_quarter"),
        sa.UniqueConstraint("market_day_id", "quarter_index", name="gdam_uniq"),
        sa.ForeignKeyConstraint(["market_day_id"], ["market_day.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_gdam_mday_q", "gdam_price", ["market_day_id", "quarter_index"], unique=False)

    op.create_table(
        "rtm_price",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("market_day_id", sa.BigInteger(), nullable=False),
        sa.Column("hour", sa.SmallInteger(), nullable=False),
        sa.Column("session_id", sa.SmallInteger(), nullable=True),
        sa.Column("quarter_index", sa.SmallInteger(), nullable=False),
        sa.Column("mcv_mw", sa.Numeric(12, 2), nullable=True),
        sa.Column("fsv_mw", sa.Numeric(12, 2), nullable=True),
        sa.Column("mcp_rs_per_mwh", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("hour BETWEEN 1 AND 24", name="ck_rtm_hour"),
        sa.CheckConstraint("quarter_index BETWEEN 0 AND 95", name="ck_rtm_quarter"),
        sa.UniqueConstraint("market_day_id", "quarter_index", name="rtm_uniq"),
        sa.ForeignKeyConstraint(["market_day_id"], ["market_day.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_rtm_mday_q", "rtm_price", ["market_day_id", "quarter_index"], unique=False)

    op.create_table(
        "market_summary",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("market_day_id", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.UniqueConstraint("market_day_id", "label", name="uq_summary_label"),
        sa.ForeignKeyConstraint(["market_day_id"], ["market_day.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("market_summary")
    op.drop_index("idx_rtm_mday_q", table_name="rtm_price")
    op.drop_table("rtm_price")
    op.drop_index("idx_gdam_mday_q", table_name="gdam_price")
    op.drop_table("gdam_price")
    op.drop_index("idx_dam_mday_hour", table_name="dam_price")
    op.drop_table("dam_price")
    op.drop_table("market_day")
