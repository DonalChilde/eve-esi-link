"""Unit tests for the EsiLink library entrypoint."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pfmsoft.api_request import Response
from pfmsoft.api_request.request.models import (
    FailedResponse,
    Request,
    ResponseMetadata,
    Source,
)

from pfmsoft.eve_link.esi_link import EsiLink, _make_esi_response_group
from pfmsoft.eve_link.esi_request.models import (
    EsiRequest,
    EsiRequestGroup,
    RuntimeEsiRequest,
)
from pfmsoft.eve_link.esi_request.validate import EsiRequestValidationErrors
from pfmsoft.eve_link.schema.models import EsiSchema


class _FakeApiRequester:
    """Small async requester stub for EsiLink tests."""

    def __init__(self, *, responses=None) -> None:  # noqa: ANN001
        self.responses = responses or SimpleNamespace(successful={}, failed={})
        self.entered = False
        self.exited_with = None
        self.processed = None

    async def __aenter__(self) -> _FakeApiRequester:
        """Record async context entry."""
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Record async context exit."""
        self.exited_with = (exc_type, exc, tb)

    async def process_requests(self, request_objects):  # noqa: ANN001
        """Record converted request objects and return prepared responses."""
        self.processed = request_objects
        return self.responses


class _FakeAuthManager:
    """Small auth manager stub for EsiLink tests."""

    def __init__(self, *, access_token: str = "token-123") -> None:
        self.access_token = access_token
        self.entered = False
        self.exited_with = None
        self.character_calls: list[tuple[object, object]] = []

    def __enter__(self) -> _FakeAuthManager:
        """Record sync context entry."""
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Record sync context exit."""
        self.exited_with = (exc_type, exc, tb)

    def get_character(self, credential_id, character_id):  # noqa: ANN001
        """Return a simple credential record with an access token."""
        self.character_calls.append((credential_id, character_id))
        return SimpleNamespace(access_token=self.access_token)


def _make_schema() -> EsiSchema:
    """Build a minimal schema for EsiLink behavior tests."""
    raw_schema = {
        "openapi": "3.0.0",
        "info": {"version": "2026-06-09", "title": "test-schema"},
        "servers": [{"url": "https://esi.evetech.net"}],
        "paths": {
            "/status/": {
                "get": {
                    "operationId": "GetStatus",
                    "x-rate-limit": {"group": "status"},
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {},
    }
    return EsiSchema.from_raw_schema(raw_schema)


def _make_runtime_request(
    *, request_id, access_token: str | None = None
) -> RuntimeEsiRequest:
    """Build a runtime request fixture."""
    return RuntimeEsiRequest(
        request_key=request_id,
        url="https://esi.evetech.net/status/",
        method="GET",
        cache_key=None,
        rate_limit_key="status",
        headers={"accept-language": "en"},
        query_parameters={"datasource": "tranquility"},
        access_token=access_token,
    )


def _make_request_response(*, request_id):
    """Build paired api_request Request and Response fixtures."""
    request = Request(
        request_key=request_id,
        url="https://esi.evetech.net/status/",
        method="GET",
    )
    response = Response(
        metadata=ResponseMetadata(
            status_code=200,
            reason_phrase="OK",
            url=request.url,
            elapsed=1,
            bytes_downloaded=10,
        ),
        json={"status": "ok"},
        request=request,
        source=Source.NETWORK,
    )
    return request, response


def test_context_manager_initializes_and_closes_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Create backend factories on enter and close both managed resources on exit."""
    calls: dict[str, object] = {}
    fake_requester = _FakeApiRequester()
    fake_auth_manager = _FakeAuthManager()

    def fake_cache_factory(*, db_path: Path) -> object:
        calls["cache_factory"] = db_path
        return object()

    def fake_rate_limiter_factory(*, max_rate: float, time_period: float) -> object:
        calls["rate_limiter_factory"] = (max_rate, time_period)
        return object()

    def fake_api_requester_constructor(
        *, cache_factory: object, rate_limiter_factory: object
    ) -> _FakeApiRequester:
        calls["api_requester_args"] = (cache_factory, rate_limiter_factory)
        return fake_requester

    def fake_auth_manager_constructor(*, db_path: Path) -> _FakeAuthManager:
        calls["auth_db_path"] = db_path
        return fake_auth_manager

    monkeypatch.setattr(
        "pfmsoft.eve_link.esi_link.SqliteCacheFactory",
        fake_cache_factory,
    )
    monkeypatch.setattr(
        "pfmsoft.eve_link.esi_link.AiolimiterRateLimiterFactory",
        fake_rate_limiter_factory,
    )
    monkeypatch.setattr(
        "pfmsoft.eve_link.esi_link.api_request.ApiRequester",
        fake_api_requester_constructor,
    )
    monkeypatch.setattr(
        "pfmsoft.eve_link.esi_link.SqliteAuthManager",
        fake_auth_manager_constructor,
    )

    link = EsiLink(
        auth_manager_db_path=tmp_path / "auth.sqlite",
        web_cache_path=tmp_path / "cache.sqlite",
        max_rate=7,
        time_period=3.5,
    )

    entered = asyncio.run(link.__aenter__())
    asyncio.run(link.__aexit__(None, None, None))

    assert entered is link
    assert calls["cache_factory"] == tmp_path / "cache.sqlite"
    assert calls["rate_limiter_factory"] == (7, 3.5)
    assert calls["auth_db_path"] == tmp_path / "auth.sqlite"
    assert fake_requester.entered is True
    assert fake_requester.exited_with == (None, None, None)
    assert fake_auth_manager.entered is True
    assert fake_auth_manager.exited_with == (None, None, None)


def test_initialization_guards_and_operation_lookup() -> None:
    """Guard uninitialized backends and validate schema operation lookup."""
    link = EsiLink(Path("auth.sqlite"), Path("cache.sqlite"))
    schema = _make_schema()

    with pytest.raises(RuntimeError, match="async context manager"):
        link._check_api_requester_initialized()
    with pytest.raises(RuntimeError, match="async context manager"):
        link._check_auth_manager()
    assert link._check_operation("GetStatus", schema).operation_id == "GetStatus"
    with pytest.raises(ValueError, match="Operation ID 'Missing' not found"):
        link._check_operation("Missing", schema)


def test_aexit_tolerates_partially_initialized_resources() -> None:
    """Skip missing managed resources during context-manager teardown."""
    link = EsiLink(Path("auth.sqlite"), Path("cache.sqlite"))
    link.auth_manager = _FakeAuthManager()

    asyncio.run(link.__aexit__(None, None, None))

    assert link.auth_manager.exited_with == (None, None, None)


def test_required_access_token_is_optional_and_attached_when_present() -> None:
    """Skip auth for public requests and attach the looked-up access token otherwise."""
    link = EsiLink(Path("auth.sqlite"), Path("cache.sqlite"))
    runtime_request = _make_runtime_request(request_id=uuid4())
    public_request = EsiRequest(operation_id="GetStatus")

    asyncio.run(link._check_required_access_token(public_request, runtime_request))
    assert runtime_request.access_token is None

    credential_id = uuid4()
    auth_request = EsiRequest(
        operation_id="GetStatus",
        character_id=42,
        credential_id=credential_id,
    )
    link.auth_manager = _FakeAuthManager(access_token="attached-token")

    asyncio.run(link._check_required_access_token(auth_request, runtime_request))

    assert runtime_request.access_token == "attached-token"
    assert link.auth_manager.character_calls == [(credential_id, 42)]


def test_required_access_token_rejects_incomplete_authorization_tuple() -> None:
    """Raise when a request claims authorization but omits a required auth field."""
    link = EsiLink(Path("auth.sqlite"), Path("cache.sqlite"))
    link.auth_manager = _FakeAuthManager()
    runtime_request = _make_runtime_request(request_id=uuid4())
    inconsistent_request = SimpleNamespace(
        has_authorization=True,
        credential_id=None,
        character_id=42,
    )

    with pytest.raises(ValueError, match="Credential ID and Character ID"):
        asyncio.run(
            link._check_required_access_token(inconsistent_request, runtime_request)
        )


def test_make_requests_validates_builds_processes_and_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate requests, build runtime requests, process them, and group results."""
    schema = _make_schema()
    request_id = uuid4()
    request = EsiRequest(
        request_id=request_id,
        operation_id="GetStatus",
        query_parameters={"datasource": "tranquility"},
    )
    group = EsiRequestGroup(
        name="batch",
        description="desc",
        requests={request_id: request},
    )
    runtime_request = _make_runtime_request(request_id=request_id)
    _, response = _make_request_response(request_id=request_id)
    fake_requester = _FakeApiRequester(
        responses=SimpleNamespace(successful={request_id: response}, failed={})
    )
    link = EsiLink(Path("auth.sqlite"), Path("cache.sqlite"))
    link.api_requester = fake_requester
    validate_calls: list[tuple[object, object]] = []
    token_calls: list[tuple[object, object]] = []

    monkeypatch.setattr(
        EsiLink,
        "validate_request",
        staticmethod(
            lambda esi_request, schema: validate_calls.append((esi_request, schema))
        ),
    )
    monkeypatch.setattr(
        "pfmsoft.eve_link.esi_link.build_runtime_esi_request",
        lambda esi_request, schema: runtime_request,
    )

    async def fake_check_required_access_token(esi_request, built_runtime_request):  # noqa: ANN001
        token_calls.append((esi_request, built_runtime_request))

    monkeypatch.setattr(
        link, "_check_required_access_token", fake_check_required_access_token
    )

    result = asyncio.run(link.make_requests(group, schema))

    assert validate_calls == [(request, schema)]
    assert token_calls == [(request, runtime_request)]
    assert fake_requester.processed is not None
    processed_request = fake_requester.processed[request_id]
    assert processed_request.url == "https://esi.evetech.net/status/"
    assert processed_request.parameters == {"datasource": "tranquility"}
    assert result.name == "batch"
    assert result.description == "desc"
    assert result.requests == group.requests
    assert result.successful_responses[request_id].response.json == {"status": "ok"}


def test_validate_request_logs_and_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Log and re-raise aggregated validation errors without wrapping them."""
    request = EsiRequest(operation_id="GetStatus")
    schema = _make_schema()
    error = EsiRequestValidationErrors(["operation_id=GetStatus: bad request"])
    logged: list[tuple[str, object, object]] = []

    monkeypatch.setattr(
        "pfmsoft.eve_link.esi_link.validate_esi_request",
        lambda esi_request, schema: (_ for _ in ()).throw(error),
    )
    monkeypatch.setattr(
        "pfmsoft.eve_link.esi_link.logger.error",
        lambda message, req, exc: logged.append((message, req, exc)),
    )

    with pytest.raises(EsiRequestValidationErrors) as exc_info:
        EsiLink.validate_request(request, schema)

    assert exc_info.value is error
    assert logged == [("Validation failed for request %s: %s", request, error)]


def test_make_esi_response_group_preserves_request_metadata() -> None:
    """Wrap successful and failed backend responses with runtime request metadata."""
    request_id = uuid4()
    request = EsiRequest(request_id=request_id, operation_id="GetStatus")
    group = EsiRequestGroup(
        name="batch",
        description="desc",
        requests={request_id: request},
    )
    runtime_request = _make_runtime_request(request_id=request_id)
    api_request, response = _make_request_response(request_id=request_id)
    failed = FailedResponse(request=api_request, error_messages=["boom"])

    result = _make_esi_response_group(
        SimpleNamespace(successful={request_id: response}, failed={request_id: failed}),
        group,
        {request_id: runtime_request},
    )

    assert result.name == "batch"
    assert result.description == "desc"
    assert result.requests == group.requests
    assert (
        result.successful_responses[request_id].esi_runtime_request is runtime_request
    )
    assert result.failed_responses[request_id].failed_response.error_messages == [
        "boom"
    ]
