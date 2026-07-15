import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import Boolean, DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


# Create in-memory SQLite for testing
test_engine = create_engine("sqlite:///:memory:", echo=False)
Base = declarative_base()


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class TestModel(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "test_model"


def test_base_model_columns_exist():
    Base.metadata.create_all(test_engine)
    
    with Session(test_engine) as session:
        obj = TestModel()
        session.add(obj)
        session.commit()
        
        fetched = session.query(TestModel).first()
        assert fetched.id is not None
        assert fetched.created_at is not None
        assert fetched.updated_at is not None
        assert fetched.is_deleted is False
        assert fetched.version == 1
