"""add structure prediction support

Revision ID: b7a9b22443b6
Revises: e28194977b2b
Create Date: 2025-01-21 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b7a9b22443b6"
down_revision: Union[str, Sequence[str], None] = "e28194977b2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'STRUCTURE_PREDICTION'")

    op.create_table(
        "sequence_structures",
        sa.Column("sequence_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("sequence_hash", sa.String(length=64), nullable=False),
        sa.Column("residue_count", sa.Integer(), nullable=False),
        sa.Column("mean_confidence", sa.Float(), nullable=False),
        sa.Column("min_confidence", sa.Float(), nullable=False),
        sa.Column("max_confidence", sa.Float(), nullable=False),
        sa.Column(
            "confidence_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["sequence_id"],
            ["sequences.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence_id"),
    )
    op.create_index(
        op.f("ix_sequence_structures_id"),
        "sequence_structures",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_sequence_structures_id"), table_name="sequence_structures")
    op.drop_table("sequence_structures")

    # Remove new enum value by recreating type (drops jobs using the new type)
    op.execute("DELETE FROM jobs WHERE job_type = 'STRUCTURE_PREDICTION'")
    op.execute("ALTER TABLE jobs ALTER COLUMN job_type TYPE TEXT")
    op.execute("DROP TYPE jobtype")
    op.execute("CREATE TYPE jobtype AS ENUM ('PAIRWISE_ALIGNMENT')")
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN job_type TYPE jobtype USING job_type::jobtype"
    )
