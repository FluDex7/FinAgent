import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import PathTraversalError, StatementNotFoundError, StatementParseError
from app.modules.statements.models import Statement, StatementFormat, StatementStatus
from app.modules.statements.parsers.csv_parser import parse_csv
from app.modules.statements.repository import StatementRepository
from app.modules.statements.schemas import DocFileOut, DocFolderOut, StatementOut
from app.modules.transactions.schemas import TransactionOut
from app.modules.transactions.service import TransactionsService

_SUPPORTED_EXTENSIONS = {"csv": StatementFormat.csv, "pdf": StatementFormat.pdf}


class StatementsService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.repo = StatementRepository(session)
        self.transactions = TransactionsService(session)
        self.root = Path(settings.statements_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_dir(self, folder: str) -> Path:
        target = (self.root / folder).resolve()
        root_resolved = self.root.resolve()
        if target != root_resolved and root_resolved not in target.parents:
            raise PathTraversalError("Недопустимый путь к папке.")
        return target

    def _to_doc_file(self, file_path: Path, folder: str, statement: Statement | None) -> DocFileOut:
        if statement is None:
            file_id = f"{folder}/{file_path.name}" if folder else file_path.name
            return DocFileOut(
                id=file_id,
                name=file_path.stem,
                folder=folder,
                tx_count=0,
                date_from=None,
                date_to=None,
                status=StatementStatus.new,
            )
        return DocFileOut(
            id=str(statement.id),
            name=file_path.stem,
            folder=folder,
            tx_count=statement.transaction_count,
            date_from=statement.date_from,
            date_to=statement.date_to,
            status=statement.status,
        )

    async def browse_tree(self, path: str | None = None) -> list[DocFolderOut]:
        statements_by_path = {
            (s.folder_path, s.filename): s for s in await self.repo.list_all()
        }

        if path:
            folder = path.strip("/")
            target = self._resolve_dir(folder)
            if not target.exists():
                return [DocFolderOut(name=folder, files=[])]
            files = [
                self._to_doc_file(p, folder, statements_by_path.get((folder, p.name)))
                for p in sorted(target.iterdir())
                if p.is_file()
            ]
            return [DocFolderOut(name=folder, files=files)]

        root = self._resolve_dir("")
        folders: list[DocFolderOut] = []

        loose_files = [p for p in sorted(root.iterdir()) if p.is_file()]
        if loose_files:
            files = [
                self._to_doc_file(p, "", statements_by_path.get(("", p.name))) for p in loose_files
            ]
            folders.append(DocFolderOut(name="", files=files))

        for subdir in sorted(p for p in root.iterdir() if p.is_dir()):
            files = [
                self._to_doc_file(p, subdir.name, statements_by_path.get((subdir.name, p.name)))
                for p in sorted(subdir.iterdir())
                if p.is_file()
            ]
            folders.append(DocFolderOut(name=subdir.name, files=files))

        return folders

    async def upload(self, *, filename: str, folder: str, content: bytes) -> StatementOut:
        folder = (folder or "").strip("/")
        ext = Path(filename).suffix.lower().lstrip(".")
        source_format = _SUPPORTED_EXTENSIONS.get(ext)
        if source_format is None:
            raise StatementParseError(
                f"Формат «.{ext}» не поддерживается.", hint="Поддерживаются PDF и CSV."
            )

        target_dir = self._resolve_dir(folder)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / filename).write_bytes(content)

        statement = await self.repo.create(
            filename=filename, folder_path=folder, source_format=source_format
        )

        if source_format == StatementFormat.csv:
            await self._parse_csv(statement, content)
        else:
            await self.repo.mark_error(
                statement, "Парсинг PDF (OCR) появится на следующем шаге разработки."
            )

        return StatementOut.model_validate(statement)

    async def _parse_csv(self, statement: Statement, content: bytes) -> None:
        try:
            transactions = parse_csv(content)
        except StatementParseError as exc:
            await self.repo.mark_error(statement, exc.message)
            return

        await self.transactions.bulk_create(statement.id, transactions)
        dates = [t.date for t in transactions]
        await self.repo.mark_parsed(
            statement,
            transaction_count=len(transactions),
            date_from=min(dates),
            date_to=max(dates),
        )

    async def _get_or_404(self, statement_id: uuid.UUID) -> Statement:
        statement = await self.repo.get(statement_id)
        if statement is None:
            raise StatementNotFoundError(f"Выписка {statement_id} не найдена.")
        return statement

    async def get(self, statement_id: uuid.UUID) -> StatementOut:
        statement = await self._get_or_404(statement_id)
        return StatementOut.model_validate(statement)

    async def list_transactions(
        self, statement_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[TransactionOut]:
        await self._get_or_404(statement_id)
        return await self.transactions.list_by_statement(statement_id, limit, offset)

    async def delete(self, statement_id: uuid.UUID) -> None:
        statement = await self._get_or_404(statement_id)
        file_path = self.root / statement.folder_path / statement.filename
        if file_path.exists():
            file_path.unlink()
        await self.repo.delete(statement)
