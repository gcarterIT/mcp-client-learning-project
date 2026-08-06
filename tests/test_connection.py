"""
Regression tests for the MCP connection lifecycle.

These tests isolate MCPConnection from real subprocesses and real MCP
servers. Fake asynchronous context managers are used so that we can
verify the connection lifecycle deterministically.

Part 8B.1 protects only successful connection entry and initialization.
Later milestones will protect cleanup and failure behavior separately.
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.client.stdio import StdioServerParameters

import mcp_client.connection as connection_module
from mcp_client.connection import MCPConnection


@pytest.fixture
def anyio_backend() -> str:
    """
    Run AnyIO-based asynchronous tests with asyncio only.

    MCPConnection is currently used with Python's asyncio runtime.
    Explicitly selecting asyncio also prevents pytest from attempting
    to run this test with Trio when Trio is not installed.
    """

    return "asyncio"


@pytest.mark.anyio
async def test_successful_entry_exposes_initialized_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A successful connection entry must expose an initialized session.

    This test protects the following lifecycle contract:

    1. stdio_client receives the configured server parameters.
    2. The STDIO context is entered.
    3. ClientSession receives the returned read and write streams.
    4. The ClientSession context is entered.
    5. session.initialize() is called exactly once.
    6. MCPConnection.__aenter__ returns the connection wrapper.
    7. connection.session exposes the initialized session.
    8. connection.initialization_result preserves the initialization
       response returned by the session.

    Exit behavior is not asserted here. It belongs to a later,
    separately testable milestone.
    """

    # -------------------------------------------------------------
    # Arrange: create identity-based test values.
    # -------------------------------------------------------------

    server_parameters = StdioServerParameters(
        command="python",
        args=["fake_server.py"],
    )

    read_stream = object()
    write_stream = object()
    initialization_result = object()

    # These collections record how the production class uses its
    # collaborators. Object identity is used instead of value equality
    # so that the test proves the exact objects were forwarded.
    received_server_parameters: list[Any] = []
    received_session_streams: list[tuple[Any, Any]] = []

    initialize_call_count = 0

    # -------------------------------------------------------------
    # Fake STDIO asynchronous context manager.
    # -------------------------------------------------------------

    class FakeStdioContext:
        async def __aenter__(self) -> tuple[Any, Any]:
            return read_stream, write_stream

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            # Cleanup behavior is intentionally not asserted in this
            # milestone. Returning False matches normal context-manager
            # exception propagation.
            return False

    def fake_stdio_client(parameters: Any) -> FakeStdioContext:
        received_server_parameters.append(parameters)
        return FakeStdioContext()

    # -------------------------------------------------------------
    # Fake MCP ClientSession asynchronous context manager.
    # -------------------------------------------------------------

    class FakeClientSession:
        async def __aenter__(self) -> "FakeClientSession":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            return False

        async def initialize(self) -> object:
            nonlocal initialize_call_count

            initialize_call_count += 1
            return initialization_result

    fake_session = FakeClientSession()

    def fake_client_session(
        supplied_read_stream: Any,
        supplied_write_stream: Any,
    ) -> FakeClientSession:
        received_session_streams.append(
            (
                supplied_read_stream,
                supplied_write_stream,
            )
        )

        return fake_session

    # Replace only the collaborators looked up inside connection.py.
    #
    # No real subprocess, STDIO transport, or MCP server will be used.
    monkeypatch.setattr(
        connection_module,
        "stdio_client",
        fake_stdio_client,
    )

    monkeypatch.setattr(
        connection_module,
        "ClientSession",
        fake_client_session,
    )

    connection = MCPConnection(server_parameters)

    # -------------------------------------------------------------
    # Act: enter the connection lifecycle.
    # -------------------------------------------------------------

    entered_connection = await connection.__aenter__()

    try:
        # ---------------------------------------------------------
        # Assert: verify the successful-entry contract.
        # ---------------------------------------------------------

        assert received_server_parameters == [server_parameters]

        assert received_session_streams == [
            (
                read_stream,
                write_stream,
            )
        ]

        assert initialize_call_count == 1

        # __aenter__ returns the MCPConnection wrapper, not the raw
        # ClientSession.
        assert entered_connection is connection

        # The session exposed by the wrapper is the exact session
        # returned by the ClientSession context manager.
        assert connection.session is fake_session

        # Preserve the exact initialization response for inspection.
        assert (
            connection.initialization_result
            is initialization_result
        )

    finally:
        # Close the fake lifecycle even if an assertion fails.
        #
        # Cleanup behavior is deliberately not asserted here. That
        # contract will be protected in Part 8B.2.
        await connection.__aexit__(None, None, None)
        
@pytest.mark.anyio
async def test_successful_exit_closes_resources_in_reverse_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A successful connection exit must close resources in reverse order.

    This test protects the following lifecycle contract:

    1. The ClientSession context exits first.
    2. The STDIO transport context exits second.
    3. MCPConnection.__aexit__ returns False.
    4. Public and private lifecycle references are cleared.
    5. The initialization result remains available after shutdown.
    """

    # -------------------------------------------------------------
    # Arrange: create controlled identity-based test values.
    # -------------------------------------------------------------

    server_parameters = StdioServerParameters(
        command="python",
        args=["fake_server.py"],
    )

    read_stream = object()
    write_stream = object()
    initialization_result = object()

    # This list records the exact order in which lifecycle events occur.
    lifecycle_events: list[str] = []

    # -------------------------------------------------------------
    # Fake STDIO asynchronous context manager.
    # -------------------------------------------------------------

    class FakeStdioContext:
        async def __aenter__(self) -> tuple[Any, Any]:
            lifecycle_events.append("stdio_enter")
            return read_stream, write_stream

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("stdio_exit")
            return False

    def fake_stdio_client(parameters: Any) -> FakeStdioContext:
        return FakeStdioContext()

    # -------------------------------------------------------------
    # Fake MCP ClientSession asynchronous context manager.
    # -------------------------------------------------------------

    class FakeClientSession:
        async def __aenter__(self) -> "FakeClientSession":
            lifecycle_events.append("session_enter")
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("session_exit")
            return False

        async def initialize(self) -> object:
            lifecycle_events.append("session_initialize")
            return initialization_result

    fake_session = FakeClientSession()

    def fake_client_session(
        supplied_read_stream: Any,
        supplied_write_stream: Any,
    ) -> FakeClientSession:
        return fake_session

    monkeypatch.setattr(
        connection_module,
        "stdio_client",
        fake_stdio_client,
    )

    monkeypatch.setattr(
        connection_module,
        "ClientSession",
        fake_client_session,
    )

    connection = MCPConnection(server_parameters)

    # -------------------------------------------------------------
    # Act: enter and then exit the connection lifecycle.
    # -------------------------------------------------------------

    await connection.__aenter__()

    exit_result = await connection.__aexit__(
        None,
        None,
        None,
    )

    # -------------------------------------------------------------
    # Assert: verify reverse-order cleanup.
    # -------------------------------------------------------------

    assert lifecycle_events == [
        "stdio_enter",
        "session_enter",
        "session_initialize",
        "session_exit",
        "stdio_exit",
    ]

    # Returning False means exceptions from an async-with body would
    # not be suppressed.
    assert exit_result is False

    # Public session state must no longer expose a closed session.
    assert connection.session is None

    # Internal lifecycle references must be cleared after shutdown.
    assert connection._session_context is None
    assert connection._stdio_context is None
    assert connection._read_stream is None
    assert connection._write_stream is None

    # Current production behavior intentionally preserves the server's
    # initialization response after the connection has closed.
    assert (
        connection.initialization_result
        is initialization_result
    )
    
@pytest.mark.anyio
async def test_context_body_exception_is_forwarded_and_not_suppressed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An exception raised inside the async-with body must not be suppressed.

    This test protects the following lifecycle contract:

    1. The connection enters successfully.
    2. The caller's body raises an exception.
    3. ClientSession.__aexit__ receives that exception information.
    4. The STDIO context receives the same exception information.
    5. Cleanup occurs in reverse order.
    6. The original exception propagates to the caller.
    7. Lifecycle references are cleared after shutdown.
    """

    # -------------------------------------------------------------
    # Arrange: create controlled test values.
    # -------------------------------------------------------------

    server_parameters = StdioServerParameters(
        command="python",
        args=["fake_server.py"],
    )

    read_stream = object()
    write_stream = object()
    initialization_result = object()

    lifecycle_events: list[str] = []

    # Each context manager will record the exception information it
    # receives during shutdown.
    session_exit_arguments: list[
        tuple[
            type[BaseException] | None,
            BaseException | None,
            Any,
        ]
    ] = []

    stdio_exit_arguments: list[
        tuple[
            type[BaseException] | None,
            BaseException | None,
            Any,
        ]
    ] = []

    # -------------------------------------------------------------
    # Fake STDIO context manager.
    # -------------------------------------------------------------

    class FakeStdioContext:
        async def __aenter__(self) -> tuple[Any, Any]:
            lifecycle_events.append("stdio_enter")
            return read_stream, write_stream

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("stdio_exit")

            stdio_exit_arguments.append(
                (
                    exc_type,
                    exc_value,
                    traceback,
                )
            )

            # Returning False means the exception is not suppressed.
            return False

    def fake_stdio_client(parameters: Any) -> FakeStdioContext:
        return FakeStdioContext()

    # -------------------------------------------------------------
    # Fake ClientSession context manager.
    # -------------------------------------------------------------

    class FakeClientSession:
        async def __aenter__(self) -> "FakeClientSession":
            lifecycle_events.append("session_enter")
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("session_exit")

            session_exit_arguments.append(
                (
                    exc_type,
                    exc_value,
                    traceback,
                )
            )

            return False

        async def initialize(self) -> object:
            lifecycle_events.append("session_initialize")
            return initialization_result

    fake_session = FakeClientSession()

    def fake_client_session(
        supplied_read_stream: Any,
        supplied_write_stream: Any,
    ) -> FakeClientSession:
        return fake_session

    monkeypatch.setattr(
        connection_module,
        "stdio_client",
        fake_stdio_client,
    )

    monkeypatch.setattr(
        connection_module,
        "ClientSession",
        fake_client_session,
    )

    connection = MCPConnection(server_parameters)

    body_exception = ValueError("simulated workflow failure")

    # -------------------------------------------------------------
    # Act and assert: execute the real async context-manager protocol.
    # -------------------------------------------------------------

    with pytest.raises(
        ValueError,
        match="simulated workflow failure",
    ) as captured_exception:
        async with connection as entered_connection:
            assert entered_connection is connection
            assert connection.session is fake_session

            raise body_exception

    # -------------------------------------------------------------
    # Assert: verify exception identity and cleanup behavior.
    # -------------------------------------------------------------

    # The exact original exception object must reach the caller.
    assert captured_exception.value is body_exception

    # Cleanup must still occur in reverse startup order.
    assert lifecycle_events == [
        "stdio_enter",
        "session_enter",
        "session_initialize",
        "session_exit",
        "stdio_exit",
    ]

    # Both nested context managers must receive one shutdown call.
    assert len(session_exit_arguments) == 1
    assert len(stdio_exit_arguments) == 1

    session_exc_type, session_exc_value, session_traceback = (
        session_exit_arguments[0]
    )

    stdio_exc_type, stdio_exc_value, stdio_traceback = (
        stdio_exit_arguments[0]
    )

    # Both nested context managers receive the original exception type
    # and exact exception object.
    assert session_exc_type is ValueError
    assert session_exc_value is body_exception
    assert session_traceback is not None

    assert stdio_exc_type is ValueError
    assert stdio_exc_value is body_exception
    assert stdio_traceback is not None

    # Python supplies the same active traceback to MCPConnection,
    # which forwards it unchanged to both nested context managers.
    assert stdio_traceback is session_traceback

    # Lifecycle state must be cleared even after body failure.
    assert connection.session is None
    assert connection._session_context is None
    assert connection._stdio_context is None
    assert connection._read_stream is None
    assert connection._write_stream is None

    # Preserve the initialization response, matching current behavior.
    assert (
        connection.initialization_result
        is initialization_result
    )
    
@pytest.mark.anyio
async def test_failed_session_entry_cleans_up_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A failure while entering ClientSession must trigger partial cleanup.

    This test protects the following lifecycle contract:

    1. The STDIO context enters successfully.
    2. ClientSession is created from the returned streams.
    3. ClientSession.__aenter__ raises an exception.
    4. MCPConnection explicitly cleans up the partial lifecycle.
    5. The ClientSession context is exited first.
    6. The STDIO transport context is exited second.
    7. Cleanup receives None exception arguments because it is performed
       explicitly by _cleanup_after_failed_entry().
    8. Lifecycle references are cleared.
    9. The original exception propagates unchanged.
    """

    # -------------------------------------------------------------
    # Arrange: create controlled identity-based test values.
    # -------------------------------------------------------------

    server_parameters = StdioServerParameters(
        command="python",
        args=["fake_server.py"],
    )

    read_stream = object()
    write_stream = object()

    lifecycle_events: list[str] = []

    session_exit_arguments: list[
        tuple[
            type[BaseException] | None,
            BaseException | None,
            Any,
        ]
    ] = []

    stdio_exit_arguments: list[
        tuple[
            type[BaseException] | None,
            BaseException | None,
            Any,
        ]
    ] = []

    session_entry_exception = RuntimeError(
        "simulated ClientSession entry failure"
    )

    # -------------------------------------------------------------
    # Fake STDIO asynchronous context manager.
    # -------------------------------------------------------------

    class FakeStdioContext:
        async def __aenter__(self) -> tuple[Any, Any]:
            lifecycle_events.append("stdio_enter")
            return read_stream, write_stream

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("stdio_exit")

            stdio_exit_arguments.append(
                (
                    exc_type,
                    exc_value,
                    traceback,
                )
            )

            return False

    def fake_stdio_client(parameters: Any) -> FakeStdioContext:
        return FakeStdioContext()

    # -------------------------------------------------------------
    # Fake ClientSession asynchronous context manager.
    # -------------------------------------------------------------

    class FakeClientSession:
        async def __aenter__(self) -> "FakeClientSession":
            lifecycle_events.append("session_enter")

            raise session_entry_exception

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("session_exit")

            session_exit_arguments.append(
                (
                    exc_type,
                    exc_value,
                    traceback,
                )
            )

            return False

        async def initialize(self) -> object:
            pytest.fail(
                "initialize() must not be called when "
                "ClientSession.__aenter__() fails"
            )

    fake_session_context = FakeClientSession()

    def fake_client_session(
        supplied_read_stream: Any,
        supplied_write_stream: Any,
    ) -> FakeClientSession:
        assert supplied_read_stream is read_stream
        assert supplied_write_stream is write_stream

        return fake_session_context

    monkeypatch.setattr(
        connection_module,
        "stdio_client",
        fake_stdio_client,
    )

    monkeypatch.setattr(
        connection_module,
        "ClientSession",
        fake_client_session,
    )

    connection = MCPConnection(server_parameters)

    # -------------------------------------------------------------
    # Act and assert: entry fails and the original error propagates.
    # -------------------------------------------------------------

    with pytest.raises(
        RuntimeError,
        match="simulated ClientSession entry failure",
    ) as captured_exception:
        await connection.__aenter__()

    # -------------------------------------------------------------
    # Assert: verify partial cleanup behavior.
    # -------------------------------------------------------------

    assert captured_exception.value is session_entry_exception

    assert lifecycle_events == [
        "stdio_enter",
        "session_enter",
        "session_exit",
        "stdio_exit",
    ]

    # Explicit failed-entry cleanup passes no active exception
    # information to the nested context managers.
    assert session_exit_arguments == [
        (
            None,
            None,
            None,
        )
    ]

    assert stdio_exit_arguments == [
        (
            None,
            None,
            None,
        )
    ]

    # No usable session was ever exposed.
    assert connection.session is None

    # All partial lifecycle state must be cleared.
    assert connection._session_context is None
    assert connection._stdio_context is None
    assert connection._read_stream is None
    assert connection._write_stream is None

    # Initialization never completed.
    assert connection.initialization_result is None    

@pytest.mark.anyio
async def test_failed_initialization_cleans_up_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A failure during session initialization must trigger full cleanup.

    This test protects the following lifecycle contract:

    1. The STDIO context enters successfully.
    2. ClientSession is created from the returned streams.
    3. ClientSession enters successfully.
    4. connection.session temporarily exposes that entered session.
    5. session.initialize() raises an exception.
    6. MCPConnection explicitly performs failed-entry cleanup.
    7. ClientSession exits before the STDIO transport.
    8. Cleanup receives None exception arguments.
    9. All lifecycle references are cleared.
    10. The original exception propagates unchanged.
    """

    # -------------------------------------------------------------
    # Arrange: create controlled identity-based values.
    # -------------------------------------------------------------

    server_parameters = StdioServerParameters(
        command="python",
        args=["fake_server.py"],
    )

    read_stream = object()
    write_stream = object()

    lifecycle_events: list[str] = []

    session_exit_arguments: list[
        tuple[
            type[BaseException] | None,
            BaseException | None,
            Any,
        ]
    ] = []

    stdio_exit_arguments: list[
        tuple[
            type[BaseException] | None,
            BaseException | None,
            Any,
        ]
    ] = []

    initialization_exception = RuntimeError(
        "simulated initialization failure"
    )

    # -------------------------------------------------------------
    # Fake STDIO asynchronous context manager.
    # -------------------------------------------------------------

    class FakeStdioContext:
        async def __aenter__(self) -> tuple[Any, Any]:
            lifecycle_events.append("stdio_enter")
            return read_stream, write_stream

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("stdio_exit")

            stdio_exit_arguments.append(
                (
                    exc_type,
                    exc_value,
                    traceback,
                )
            )

            return False

    def fake_stdio_client(parameters: Any) -> FakeStdioContext:
        assert parameters is server_parameters
        return FakeStdioContext()

    # -------------------------------------------------------------
    # Fake MCP ClientSession asynchronous context manager.
    # -------------------------------------------------------------

    class FakeClientSession:
        async def __aenter__(self) -> "FakeClientSession":
            lifecycle_events.append("session_enter")
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: Any,
        ) -> bool:
            lifecycle_events.append("session_exit")

            session_exit_arguments.append(
                (
                    exc_type,
                    exc_value,
                    traceback,
                )
            )

            return False

        async def initialize(self) -> object:
            lifecycle_events.append("session_initialize")
            raise initialization_exception

    fake_session = FakeClientSession()

    def fake_client_session(
        supplied_read_stream: Any,
        supplied_write_stream: Any,
    ) -> FakeClientSession:
        assert supplied_read_stream is read_stream
        assert supplied_write_stream is write_stream

        return fake_session

    monkeypatch.setattr(
        connection_module,
        "stdio_client",
        fake_stdio_client,
    )

    monkeypatch.setattr(
        connection_module,
        "ClientSession",
        fake_client_session,
    )

    connection = MCPConnection(server_parameters)

    # -------------------------------------------------------------
    # Act and assert: initialization fails during __aenter__().
    # -------------------------------------------------------------

    with pytest.raises(
        RuntimeError,
        match="simulated initialization failure",
    ) as captured_exception:
        await connection.__aenter__()

    # -------------------------------------------------------------
    # Assert: verify the failed-initialization cleanup contract.
    # -------------------------------------------------------------

    # The exact original exception must propagate.
    assert captured_exception.value is initialization_exception

    # Startup reached initialization, then cleanup occurred in reverse
    # resource-acquisition order.
    assert lifecycle_events == [
        "stdio_enter",
        "session_enter",
        "session_initialize",
        "session_exit",
        "stdio_exit",
    ]

    # Failed-entry cleanup is explicit, so the helper currently passes
    # no active exception information to the nested context managers.
    assert session_exit_arguments == [
        (
            None,
            None,
            None,
        )
    ]

    assert stdio_exit_arguments == [
        (
            None,
            None,
            None,
        )
    ]

    # The session had been assigned before initialize() failed, so the
    # cleanup helper must remove that temporarily exposed reference.
    assert connection.session is None

    # All internal lifecycle state must be cleared.
    assert connection._session_context is None
    assert connection._stdio_context is None
    assert connection._read_stream is None
    assert connection._write_stream is None

    # initialize() never returned successfully, so no initialization
    # result should be preserved.
    assert connection.initialization_result is None
