import uuid
from collections.abc import Callable
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import PathTraversalError, StatementNotFoundError, StatementParseError
from app.modules.categorization.service import CategorizationService
from app.modules.statements.models import Statement, StatementFormat, StatementStatus
from app.modules.statements.parsers.csv_parser import parse_csv
from app.modules.statements.parsers.pdf_parser import detect_bank_label, extract_text, parse_pdf
from app.modules.statements.repository import StatementRepository
from app.modules.statements.schemas import DocFileOut, DocFolderOut, StatementOut
from app.modules.transactions.schemas import TransactionIn, TransactionOut
from app.modules.transactions.service import TransactionsService

_SUPPORTED_EXTENSIONS = {"csv": StatementFormat.csv, "pdf": StatementFormat.pdf}
_BANK_LABELS = {"tbank": "тбанк", "sberbank": "сбербанк"}


def _format_period(date_from: date, date_to: date) -> str:
    return f"{date_from:%Y-%m-%d}_{date_to:%Y-%m-%d}"


def _is_visible(path: Path) -> bool:
    return not path.name.startswith(".")


def _unique_filename(directory: Path, base_name: str, ext: str) -> str:
    candidate = f"{base_name}.{ext}"
    if not (directory / candidate).exists():
        return candidate
    n = 2
    while (directory / f"{base_name}-{n}.{ext}").exists():
        n += 1
    return f"{base_name}-{n}.{ext}"


class StatementsService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.repo = StatementRepository(session)
        self.transactions = TransactionsService(session)
        self.categorization = CategorizationService(self.transactions, settings)
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
                if p.is_file() and _is_visible(p)
            ]
            return [DocFolderOut(name=folder, files=files)]

        root = self._resolve_dir("")
        folders: list[DocFolderOut] = []

        loose_files = [p for p in sorted(root.iterdir()) if p.is_file() and _is_visible(p)]
        if loose_files:
            files = [
                self._to_doc_file(p, "", statements_by_path.get(("", p.name))) for p in loose_files
            ]
            folders.append(DocFolderOut(name="", files=files))

        for subdir in sorted(p for p in root.iterdir() if p.is_dir() and _is_visible(p)):
            files = [
                self._to_doc_file(p, subdir.name, statements_by_path.get((subdir.name, p.name)))
                for p in sorted(subdir.iterdir())
                if p.is_file() and _is_visible(p)
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

        parser = parse_csv if source_format == StatementFormat.csv else parse_pdf
        await self._parse(statement, content, parser)

        return StatementOut.model_validate(statement)

    async def _parse(
        self,
        statement: Statement,
        content: bytes,
        parser: Callable[[bytes], list[TransactionIn]],
    ) -> None:
        try:
            transactions = parser(content)
        except StatementParseError as exc:
            await self.repo.mark_error(statement, exc.message)
            return

        rows = await self.transactions.bulk_create(statement.id, transactions)
        await self.categorization.categorize_transactions(rows)
        dates = [t.date for t in transactions]
        date_from, date_to = min(dates), max(dates)
        await self.repo.mark_parsed(
            statement, transaction_count=len(transactions), date_from=date_from, date_to=date_to
        )

        if statement.source_format == StatementFormat.pdf:
            await self._auto_rename(statement, content, date_from, date_to)

    async def _auto_rename(
        self, statement: Statement, content: bytes, date_from: date, date_to: date
    ) -> None:
        """Renames a parsed PDF to '<bank>_<period>.pdf' so the vault stays organized
        without the user having to do it by hand. Best-effort — skipped if the bank
        can't be identified or the name is already canonical."""
        bank = detect_bank_label(content)
        if bank is None:
            return
        label = _BANK_LABELS.get(bank, bank)
        directory = self.root / statement.folder_path
        base_name = f"{label}_{_format_period(date_from, date_to)}"
        new_filename = _unique_filename(directory, base_name, "pdf")
        if new_filename == statement.filename:
            return
        (directory / statement.filename).rename(directory / new_filename)
        await self.repo.rename(statement, new_filename)

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

    def _locate_file(self, path: str) -> Path:
        """Resolves a tree path ("2025/апрель" or a bare root-level "апрель") to the
        matching file on disk, regardless of its extension."""
        folder_name, _, file_name = path.strip("/").rpartition("/")
        target_dir = self._resolve_dir(folder_name)
        if not target_dir.exists():
            raise StatementNotFoundError(f"Папка «{folder_name}» не найдена.")
        match = next(
            (p for p in target_dir.iterdir() if p.is_file() and p.stem == file_name), None
        )
        if match is None:
            raise StatementNotFoundError(f"Файл «{path}» не найден на диске.")
        return match

    async def read_raw_text(self, path: str) -> str:
        """Reads a file's raw text content directly from disk — no transaction parsing.

        For files the structured pipeline can't handle (unrecognized PDF layout, a
        parse error, or just a format we don't model) this lets the agent still look
        at what's actually in the file instead of being stuck.
        """
        file_path = self._locate_file(path)
        content = file_path.read_bytes()
        ext = file_path.suffix.lower().lstrip(".")

        if ext == "csv":
            return content.decode("utf-8-sig", errors="ignore")
        if ext == "pdf":
            return extract_text(content)
        raise StatementParseError(f"Чтение файлов формата «.{ext}» не поддерживается.")

    async def resolve_paths_to_statement_ids(self, paths: list[str]) -> list[str]:
        """Maps resolve_scope/@-ref paths ("2025" a whole folder, "2025/Q1" one file)
        to parsed Statement ids. Unparsed ("new") files are silently skipped —
        they have no transactions yet."""
        tree = await self.browse_tree()
        by_folder = {folder.name: folder.files for folder in tree}

        ids: list[str] = []
        for raw_path in paths:
            path = raw_path.strip("/")
            if path in by_folder:
                ids.extend(f.id for f in by_folder[path] if f.status == StatementStatus.parsed)
                continue
            folder_name, _, file_name = path.partition("/")
            if not file_name:
                folder_name, file_name = "", folder_name
            for f in by_folder.get(folder_name, []):
                if f.name == file_name and f.status == StatementStatus.parsed:
                    ids.append(f.id)
        return ids
