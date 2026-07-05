import uuid
from typing import Annotated

from fastapi import APIRouter, Form, UploadFile

from app.modules.statements.dependencies import StatementsServiceDep
from app.modules.statements.schemas import DocFolderOut, StatementOut
from app.modules.transactions.schemas import TransactionOut

router = APIRouter(tags=["statements"])


@router.get("/documents/tree", response_model=list[DocFolderOut])
async def get_documents_tree(
    service: StatementsServiceDep, path: str | None = None
) -> list[DocFolderOut]:
    return await service.browse_tree(path)


@router.post("/statements", response_model=StatementOut)
async def upload_statement(
    service: StatementsServiceDep, file: UploadFile, folder: Annotated[str, Form()] = ""
) -> StatementOut:
    content = await file.read()
    return await service.upload(filename=file.filename or "unnamed", folder=folder, content=content)


@router.get("/statements/{statement_id}", response_model=StatementOut)
async def get_statement(statement_id: uuid.UUID, service: StatementsServiceDep) -> StatementOut:
    return await service.get(statement_id)


@router.get("/statements/{statement_id}/transactions", response_model=list[TransactionOut])
async def get_statement_transactions(
    statement_id: uuid.UUID,
    service: StatementsServiceDep,
    limit: int = 100,
    offset: int = 0,
) -> list[TransactionOut]:
    return await service.list_transactions(statement_id, limit=limit, offset=offset)


@router.delete("/statements/{statement_id}", status_code=204)
async def delete_statement(statement_id: uuid.UUID, service: StatementsServiceDep) -> None:
    await service.delete(statement_id)
