"""Workspace-bound read-only S6a API; no default database, acquisition or scheduling."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated, Any
from uuid import UUID

from equity_schema.fundamentals import LatestResponse, LatestSelection, NoResult, SnapshotResponse
from equity_schema.fundamentals_store import get_latest, get_snapshot
from equity_schema.workflow import Database
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ConnectionFactory = Callable[[], AbstractContextManager[Database]]


def create_app(*, workspace_id: UUID, connection_factory: ConnectionFactory) -> FastAPI:
    """Bind authenticated workspace in deployment composition, never in user query params.

    Intended for trusted local transport only. Multi-user authentication and UI
    wiring remain separate; no network listener or environment defaults are enabled.
    """
    app = FastAPI(title="equityEval Fundamentals", version="s6a-v1")
    errors: dict[int | str, dict[str, Any]] = {404: {"model": NoResult}}

    @app.get("/analysis-snapshots/{snapshot_id}", response_model=SnapshotResponse, responses=errors)
    def snapshot(snapshot_id: UUID, request: Request) -> SnapshotResponse | JSONResponse:
        if request.query_params:
            raise RequestValidationError(
                [
                    {
                        "type": "extra_forbidden",
                        "loc": ("query", key),
                        "msg": "Snapshot ID retrieval accepts no selectors",
                        "input": value,
                    }
                    for key, value in request.query_params.items()
                ]
            )
        with connection_factory() as db, db.transaction():
            db.execute("SET TRANSACTION READ ONLY")
            result = get_snapshot(db, workspace_id=workspace_id, snapshot_id=snapshot_id)
        if result is None:
            return JSONResponse(
                status_code=404,
                content=NoResult(code="snapshot_not_found", message="N/A").model_dump(),
            )
        return result

    @app.get("/companies/{issuer_id}/fundamentals", response_model=LatestResponse, responses=errors)
    def latest(
        issuer_id: UUID, selection: Annotated[LatestSelection, Query()]
    ) -> LatestResponse | JSONResponse:
        with connection_factory() as db, db.transaction():
            db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            result = get_latest(
                db,
                workspace_id=workspace_id,
                issuer_id=issuer_id,
                security_id=selection.security_id,
                compatibility_key=selection.compatibility_key,
                scope_id=selection.scope_id,
            )
        if result is None or result[0] is None:
            return JSONResponse(
                status_code=404,
                content=NoResult(code="no_compatible_snapshot", message="N/A").model_dump(),
            )
        return LatestResponse.model_validate(
            dict(snapshot=result[0], latest_request_id=result[1], latest_request_state=result[2])
        )

    return app
