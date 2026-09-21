"""D035 acceptance hardening: one immutable completed monitor result per execution."""

from alembic import op

revision = "0009_monitor_result_identity"
down_revision = "0008_filing_monitor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0008 was already applied for the bounded live acceptance poll. Keep that
    # applied migration intact and add this review correction sequentially.
    op.execute("""
    CREATE UNIQUE INDEX workflow_one_monitor_result_per_execution
    ON analysis_stage_attempts(execution_id)
    WHERE stage_key='sec_monitor_result' AND state='completed';
    """)


def downgrade() -> None:
    op.execute("DROP INDEX workflow_one_monitor_result_per_execution")
