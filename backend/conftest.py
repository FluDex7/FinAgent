"""Root pytest conftest.

Importing every module's models here (once, for the whole test session)
guarantees Base.metadata has all tables registered before any test builds
a Transaction/Statement/etc. row — otherwise whichever test file happens to
run first without importing e.g. `statements.models` hits a
NoReferencedTableError on the "statements.id" foreign key.
"""

from app.modules.agent import models as _agent_models  # noqa: F401
from app.modules.statements import models as _statements_models  # noqa: F401
from app.modules.transactions import models as _transactions_models  # noqa: F401
