"""Initial migration: create admin_users, proxy_users, labelled_links.

Revision ID: 0001
Revises:
Create Date: 2026-07-02

Schema source: ARCH-001@0.1.1 §4.
Uses Alembic op functions only — no raw SQL strings (INV-ORM).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create admin_users, proxy_users, and labelled_links tables."""
    # -- admin_users ----------------------------------------------------------
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    # -- proxy_users ----------------------------------------------------------
    op.create_table(
        "proxy_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telemt_username", sa.String(length=16), nullable=False),
        sa.Column("telegram_id_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="'bot'",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telemt_username"),
    )

    # -- labelled_links -------------------------------------------------------
    op.create_table(
        "labelled_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("telemt_username", sa.String(length=16), nullable=False),
        sa.Column("proxy_link", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.ForeignKeyConstraint(
            ["telemt_username"],
            ["proxy_users.telemt_username"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("label"),
    )


def downgrade() -> None:
    """Drop all three tables in reverse dependency order."""
    op.drop_table("labelled_links")
    op.drop_table("proxy_users")
    op.drop_table("admin_users")
