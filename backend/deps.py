"""
deps.py
FastAPI dependency providers.

Design note — Auth readiness
-----------------------------
When authentication is added, create a ``get_current_user`` dependency here
that decodes a JWT / session token and returns the user record.  Then inject
it into any router that needs ownership checks::

    @router.post("/projects")
    def create_project(
        body: ProjectCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),   # ← add this
    ):
        ...

All router functions already accept dependencies via FastAPI's DI system,
so no structural refactor will be needed.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
