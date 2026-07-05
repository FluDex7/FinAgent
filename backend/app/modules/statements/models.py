import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StatementFormat(StrEnum):
    csv = "csv"
    pdf = "pdf"


class StatementStatus(StrEnum):
    new = "new"
    parsing = "parsing"
    parsed = "parsed"
    error = "error"


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    folder_path: Mapped[str] = mapped_column(String(512), default="")
    source_format: Mapped[StatementFormat] = mapped_column(
        Enum(StatementFormat, name="statement_format")
    )
    status: Mapped[StatementStatus] = mapped_column(
        Enum(StatementStatus, name="statement_status"), default=StatementStatus.new
    )
    bank_name: Mapped[str | None] = mapped_column(String(120), default=None)
    date_from: Mapped[date | None] = mapped_column(Date, default=None)
    date_to: Mapped[date | None] = mapped_column(Date, default=None)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
