"""Trusted-local, explicitly workspace-bound valuation API; no listener or acquisition."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated, Any
from uuid import UUID

import psycopg
from equity_schema.valuation import (
    ApiError,
    AssumptionCreate,
    AssumptionSaved,
    LatestResponse,
    LatestSelection,
    RequestCreate,
    RequestResponse,
    RunResponse,
)
from equity_schema.valuation_store import (
    create_assumptions,
    enqueue_valuation,
    get_assumptions,
    get_latest,
    get_request,
    get_run,
)
from equity_schema.workflow import Database
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ConnectionFactory = Callable[[], AbstractContextManager[Database]]


def _not_found() -> JSONResponse:
    return JSONResponse(
        status_code=404, content=ApiError(code="not_found", message="N/A").model_dump()
    )


def _no_query(request: Request) -> None:
    if request.query_params:
        raise RequestValidationError(
            [
                dict(
                    type="extra_forbidden",
                    loc=("query", key),
                    msg="Exact ID route accepts no selectors",
                    input=value,
                )
                for key, value in request.query_params.items()
            ]
        )


def create_app(*, workspace_id: UUID, connection_factory: ConnectionFactory) -> FastAPI:
    app = FastAPI(
        title="equityEval Synthetic Valuation",
        version="s7a-v1",
        separate_input_output_schemas=False,
    )
    errors: dict[int | str, dict[str, Any]] = {404: {"model": ApiError}, 409: {"model": ApiError}}

    @app.exception_handler(psycopg.errors.InvalidParameterValue)
    @app.exception_handler(psycopg.errors.ObjectNotInPrerequisiteState)
    @app.exception_handler(psycopg.IntegrityError)
    async def constraint_error(request: Request, exc: psycopg.Error) -> JSONResponse:
        # Never expose SQL text, private judgments or worker identity in errors.
        if isinstance(
            exc, (psycopg.errors.UniqueViolation, psycopg.errors.ObjectNotInPrerequisiteState)
        ) or (
            isinstance(exc, psycopg.errors.InvalidParameterValue)
            and (exc.diag.message_primary or "").startswith("idempotency key reused")
        ):
            return JSONResponse(
                status_code=409, content=ApiError(code="conflict", message="N/A").model_dump()
            )
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"type": "value_error", "loc": ["body"], "msg": "Invalid valuation request"}
                ]
            },
        )

    @app.post("/assumption-sets", response_model=AssumptionSaved, status_code=201, responses=errors)
    def new_assumptions(body: AssumptionCreate, request: Request) -> AssumptionSaved | JSONResponse:
        _no_query(request)
        with connection_factory() as db:
            if (
                body.parent_id is not None
                and get_assumptions(db, workspace_id=workspace_id, assumption_id=body.parent_id)
                is None
            ):
                return _not_found()
            return create_assumptions(db, workspace_id=workspace_id, request=body)

    @app.get("/assumption-sets/{assumption_id}", response_model=AssumptionSaved, responses=errors)
    def assumptions(assumption_id: UUID, request: Request) -> AssumptionSaved | JSONResponse:
        _no_query(request)
        with connection_factory() as db, db.transaction():
            db.execute("SET TRANSACTION READ ONLY")
            result = get_assumptions(db, workspace_id=workspace_id, assumption_id=assumption_id)
        return result if result else _not_found()

    @app.post(
        "/valuation-requests", response_model=RequestResponse, status_code=202, responses=errors
    )
    def enqueue(body: RequestCreate, request: Request) -> RequestResponse | JSONResponse:
        _no_query(request)
        with connection_factory() as db:
            review = db.execute(
                "SELECT id FROM valuation_input_reviews WHERE id=%s AND workspace_id=%s",
                (body.review_id, workspace_id),
            ).fetchone()
            parent = db.execute(
                "SELECT id FROM analysis_requests WHERE id=%s AND workspace_id=%s",
                (body.parent_request_id, workspace_id),
            ).fetchone()
            if not review or not parent:
                return _not_found()
            handle = enqueue_valuation(db, workspace_id=workspace_id, request=body)
            result = get_request(db, workspace_id=workspace_id, request_id=handle.request_id)
            assert result is not None
            return result

    @app.get("/valuation-requests/{request_id}", response_model=RequestResponse, responses=errors)
    def request_state(request_id: UUID, request: Request) -> RequestResponse | JSONResponse:
        _no_query(request)
        with connection_factory() as db, db.transaction():
            db.execute("SET TRANSACTION READ ONLY")
            result = get_request(db, workspace_id=workspace_id, request_id=request_id)
        return result if result else _not_found()

    @app.get("/model-runs/{run_id}", response_model=RunResponse, responses=errors)
    def saved_run(run_id: UUID, request: Request) -> RunResponse | JSONResponse:
        _no_query(request)
        with connection_factory() as db, db.transaction():
            db.execute("SET TRANSACTION READ ONLY")
            result = get_run(db, workspace_id=workspace_id, run_id=run_id)
        return result if result else _not_found()

    @app.get("/companies/{issuer_id}/valuation", response_model=LatestResponse, responses=errors)
    def latest(
        issuer_id: UUID, selection: Annotated[LatestSelection, Query()]
    ) -> LatestResponse | JSONResponse:
        with connection_factory() as db, db.transaction():
            db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            result = get_latest(
                db, workspace_id=workspace_id, issuer_id=issuer_id, **selection.model_dump()
            )
        return result if result else _not_found()

    return app
