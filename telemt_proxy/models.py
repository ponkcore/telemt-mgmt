"""SQLAlchemy 2.x async ORM models for telemt-mgmt.

Defines the declarative base and three tables: admin_users, proxy_users,
and labelled_links. All database access is via the ORM (INV-ORM) — no raw
SQL strings. All I/O is async (INV-ASYNC).

Schema source: ARCH-001@0.1.1 §4.
"""

from __future__ import annotations

# datetime is used in Mapped[datetime] annotations; SQLAlchemy resolves
# the string annotation at runtime via eval(), so it must be importable
# even though ruff's TC003 flags it as type-checking-only.
from datetime import datetime  # noqa: TC003

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class AdminUser(Base):
    """Admin user for JWT auth (C3 — Admin API).

    Maps to ``admin_users`` table.
    """

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"AdminUser(id={self.id!r}, username={self.username!r}, "
            f"is_active={self.is_active!r})"
        )


class ProxyUser(Base):
    """Local mirror of a telemt user, enriched with Telegram metadata.

    Maps to ``proxy_users`` table. ``telemt_username`` is the
    ``sha256(telegram_id + salt)[:16]`` hash — never a raw Telegram ID
    (INV-HASH).
    """

    __tablename__ = "proxy_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telemt_username: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    telegram_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="bot", nullable=False)

    def __repr__(self) -> str:
        return (
            f"ProxyUser(id={self.id!r}, telemt_username={self.telemt_username!r}, "
            f"source={self.source!r}, is_active={self.is_active!r})"
        )


class LabelledLink(Base):
    """A labelled proxy link for tracking (C3 Admin API, C4 Admin Panel).

    Maps to ``labelled_links`` table. ``telemt_username`` is a foreign key
    to ``proxy_users.telemt_username``.
    """

    __tablename__ = "labelled_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    telemt_username: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("proxy_users.telemt_username"),
        nullable=False,
    )
    proxy_link: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return (
            f"LabelledLink(id={self.id!r}, label={self.label!r}, "
            f"telemt_username={self.telemt_username!r}, "
            f"is_active={self.is_active!r})"
        )
