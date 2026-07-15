"""Threaded report comments with employee-safe visibility controls."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class Comment(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A threaded clarification or review comment attached to an expense report."""

    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_report_created", "expense_report_id", "created_at"),
        Index("ix_comments_parent", "parent_comment_id"),
        Index("ix_comments_user", "user_id"),
        Index("ix_comments_visibility", "visibility"),
        Index("ix_comments_is_deleted", "is_deleted"),
    )

    expense_report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expense_reports.id"), nullable=False
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("comments.id"), nullable=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        "user_id", Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    visibility: Mapped[str] = mapped_column(String(20), default="public", nullable=False)
    text: Mapped[str] = mapped_column("comment_text", Text, nullable=False)

    parent: Mapped[Comment | None] = relationship(
        lambda: Comment,
        remote_side=lambda: [Comment.__table__.c.id],
        back_populates="replies",
    )
    replies: Mapped[list[Comment]] = relationship("Comment", back_populates="parent")

    # The aliases preserve the DBML/API terms without breaking the pre-existing
    # service signatures (author_user_id and text).
    user_id = synonym("author_user_id")
    comment_text = synonym("text")

    __mapper_args__ = {"version_id_col": VersionMixin.version}
