import uuid
from datetime import date, datetime

from app.core.schemas import CamelModel
from app.modules.statements.models import StatementFormat, StatementStatus


class StatementOut(CamelModel):
    id: uuid.UUID
    filename: str
    folder_path: str
    source_format: StatementFormat
    status: StatementStatus
    bank_name: str | None
    date_from: date | None
    date_to: date | None
    transaction_count: int
    error_message: str | None
    created_at: datetime


class StatementRename(CamelModel):
    name: str


class DocFileOut(CamelModel):
    id: str
    name: str
    folder: str
    tx_count: int
    date_from: date | None
    date_to: date | None
    status: StatementStatus


class DocFolderOut(CamelModel):
    name: str
    files: list[DocFileOut]
