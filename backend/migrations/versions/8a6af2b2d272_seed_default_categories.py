"""seed default categories

Revision ID: 8a6af2b2d272
Revises: 5f816d42902e
Create Date: 2026-07-05 20:34:31.719968

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.sql import table, column

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8a6af2b2d272'
down_revision: Union[str, Sequence[str], None] = '5f816d42902e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHART_PALETTE = ["#2b8fef", "#22b8a6", "#f0a94e", "#ee7d8c", "#94a3b8"]

DEFAULT_CATEGORIES = [
    "Продукты",
    "Транспорт",
    "Кафе и рестораны",
    "Маркетплейсы",
    "Здоровье и красота",
    "Автомобиль",
    "Наличные",
    "Переводы",
    "Связь и интернет",
    "Госуслуги",
    "Инвестиции",
    "Развлечения",
    "Прочее",
]

categories_table = table(
    "categories",
    column("id", sa.Uuid()),
    column("name", sa.String()),
    column("color", sa.String()),
    column("is_system", sa.Boolean()),
)


def upgrade() -> None:
    op.bulk_insert(
        categories_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "color": CHART_PALETTE[i % len(CHART_PALETTE)],
                "is_system": True,
            }
            for i, name in enumerate(DEFAULT_CATEGORIES)
        ],
    )


def downgrade() -> None:
    op.execute(
        categories_table.delete().where(categories_table.c.name.in_(DEFAULT_CATEGORIES))
    )
