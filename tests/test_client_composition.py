"""
test_client_composition.py

Unit tests for the MCP client's application-composition helpers.

These tests do not create an MCP connection and do not launch the
demonstration server.

Their purpose is to verify that client.py builds the correct subprocess
configuration before that configuration is passed to MCPConnection.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mcp.client.stdio import StdioServerParameters

from mcp_client.client import (
    build_demo_server_parameters,
    discover_server_capabilities,
    get_project_root,
    run_demonstration_workflows,
)

import pytest


def test_build_demo_server_parameters_without_existing_pythonpath(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Verify server parameters when the parent environment has no PYTHONPATH.

    Expected behavior:

    - use the currently active Python interpreter;
    - launch the demo server as a Python module;
    - set the child-process PYTHONPATH to the project root;
    - return an StdioServerParameters object.
    """

    # Arrange
    #
    # Remove PYTHONPATH from the test process environment. The function
    # should therefore exercise its "no existing PYTHONPATH" branch.
    monkeypatch.delenv("PYTHONPATH", raising=False)

    project_root = tmp_path

    # Act
    server_parameters = build_demo_server_parameters(
        project_root=project_root,
    )

    # Assert
    assert isinstance(server_parameters, StdioServerParameters)

    assert server_parameters.command == sys.executable

    assert server_parameters.args == [
        "-m",
        "servers.demo_server",
    ]

    assert server_parameters.env is not None

    assert server_parameters.env["PYTHONPATH"] == str(project_root)


def test_build_demo_server_parameters_preserves_existing_pythonpath(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Verify that an existing PYTHONPATH is retained after the project root.

    Expected child-process value:

        project root + operating-system path separator + existing path
    """

    # Arrange
    existing_pythonpath = os.pathsep.join(
        [
            "existing_path_one",
            "existing_path_two",
        ]
    )

    monkeypatch.setenv(
        "PYTHONPATH",
        existing_pythonpath,
    )

    project_root = tmp_path

    expected_pythonpath = (
        f"{project_root}{os.pathsep}{existing_pythonpath}"
    )

    # Act
    server_parameters = build_demo_server_parameters(
        project_root=project_root,
    )

    # Assert
    assert server_parameters.env is not None

    assert (
        server_parameters.env["PYTHONPATH"]
        == expected_pythonpath
    )


def test_build_demo_server_parameters_does_not_modify_parent_environment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Verify that the function changes only the copied child environment.

    build_demo_server_parameters() uses os.environ.copy(). Therefore,
    adding the project root to the returned environment must not change
    PYTHONPATH in the currently running pytest process.
    """

    # Arrange
    original_pythonpath = "parent_process_path"

    monkeypatch.setenv(
        "PYTHONPATH",
        original_pythonpath,
    )

    # Act
    server_parameters = build_demo_server_parameters(
        project_root=tmp_path,
    )

    # Assert the returned child environment was extended.
    assert server_parameters.env is not None

    assert server_parameters.env["PYTHONPATH"] == (
        f"{tmp_path}{os.pathsep}{original_pythonpath}"
    )

    # Assert the parent test environment was not modified.
    assert os.environ["PYTHONPATH"] == original_pythonpath
    
    
def test_get_project_root_returns_expected_project_directory() -> None:
    """
    Verify that get_project_root() returns the repository's root directory.

    The test file is located at:

        project_root/
        └── tests/
            └── test_client_composition.py

    Therefore, the parent of the tests directory is the expected project
    root.
    """

    # Arrange
    #
    # Derive the expected root independently from the test file rather
    # than calling the production function to calculate both values.
    expected_project_root = Path(__file__).resolve().parents[1]

    # Act
    actual_project_root = get_project_root()

    # Assert
    assert isinstance(actual_project_root, Path)

    assert actual_project_root == expected_project_root

    assert actual_project_root.is_dir()

    assert (actual_project_root / "src").is_dir()

    assert (actual_project_root / "tests").is_dir()

    assert (actual_project_root / "pyproject.toml").is_file()
    
    
def test_get_project_root_does_not_depend_on_current_working_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Verify that changing the current working directory does not change
    the project root returned by get_project_root().

    The production function derives the result from client.py's __file__
    location, not from Path.cwd().
    """

    # Arrange
    expected_project_root = Path(__file__).resolve().parents[1]

    # Change pytest's current working directory to an unrelated temporary
    # directory. monkeypatch restores the original directory afterward.
    monkeypatch.chdir(tmp_path)

    assert Path.cwd() == tmp_path

    # Act
    actual_project_root = get_project_root()

    # Assert
    assert actual_project_root == expected_project_root

    assert actual_project_root != Path.cwd()
 
@pytest.mark.asyncio
async def test_run_demonstration_workflows_calls_workflows_in_order(
    monkeypatch,
) -> None:
    """
    Verify that run_demonstration_workflows() coordinates all four
    demonstration workflows in the established order.

    The test replaces the real workflow functions with small asynchronous
    recording functions. No MCP server or network connection is used.
    """

    # Arrange
    #
    # Plain object instances are sufficient because the orchestrator only
    # passes these values to the workflow functions. It does not inspect
    # their internal structure.
    session = object()
    tools_result = object()
    resources_result = object()
    templates_result = object()
    prompts_result = object()

    recorded_calls: list[tuple[str, object, object]] = []

    async def fake_invoke_add_numbers(
        *,
        session,
        tools_result,
    ) -> None:
        recorded_calls.append(
            (
                "invoke_add_numbers",
                session,
                tools_result,
            )
        )

    async def fake_read_application_configuration(
        *,
        session,
        resources_result,
    ) -> None:
        recorded_calls.append(
            (
                "read_application_configuration",
                session,
                resources_result,
            )
        )

    async def fake_test_product_resource_template(
        *,
        session,
        templates_result,
    ) -> None:
        recorded_calls.append(
            (
                "test_product_resource_template",
                session,
                templates_result,
            )
        )

    async def fake_test_mcp_prompts(
        *,
        session,
        prompts_result,
    ) -> None:
        recorded_calls.append(
            (
                "test_mcp_prompts",
                session,
                prompts_result,
            )
        )

    # Replace the workflow names used inside mcp_client.client.
    monkeypatch.setattr(
        "mcp_client.client.invoke_add_numbers",
        fake_invoke_add_numbers,
    )

    monkeypatch.setattr(
        "mcp_client.client.read_application_configuration",
        fake_read_application_configuration,
    )

    monkeypatch.setattr(
        "mcp_client.client.test_product_resource_template",
        fake_test_product_resource_template,
    )

    monkeypatch.setattr(
        "mcp_client.client.test_mcp_prompts",
        fake_test_mcp_prompts,
    )

    # Act
    await run_demonstration_workflows(
        session=session,
        tools_result=tools_result,
        resources_result=resources_result,
        templates_result=templates_result,
        prompts_result=prompts_result,
    )

    # Assert
    assert recorded_calls == [
        (
            "invoke_add_numbers",
            session,
            tools_result,
        ),
        (
            "read_application_configuration",
            session,
            resources_result,
        ),
        (
            "test_product_resource_template",
            session,
            templates_result,
        ),
        (
            "test_mcp_prompts",
            session,
            prompts_result,
        ),
    ]

@pytest.mark.asyncio
async def test_discover_server_capabilities_delegates_and_returns_result(
    monkeypatch,
) -> None:
    """
    Verify that discover_server_capabilities() delegates discovery exactly
    once, passes the original session, and returns the result unchanged.

    No real MCP session or server is required because the wrapper does not
    inspect the session or discovery result.
    """

    # Arrange
    #
    # Unique object instances allow the test to verify object identity.
    session = object()

    tools_result = object()
    resources_result = object()
    templates_result = object()
    prompts_result = object()

    expected_result = (
        tools_result,
        resources_result,
        templates_result,
        prompts_result,
    )

    recorded_sessions: list[object] = []

    async def fake_discover_capabilities(
        received_session,
    ):
        recorded_sessions.append(received_session)
        return expected_result

    # Patch the name where discover_server_capabilities() looks it up.
    monkeypatch.setattr(
        "mcp_client.client.discover_capabilities",
        fake_discover_capabilities,
    )

    # Act
    actual_result = await discover_server_capabilities(session)

    # Assert
    assert recorded_sessions == [session]

    assert actual_result is expected_result
    
@pytest.mark.asyncio
async def test_main_composes_application_in_correct_order(monkeypatch):
    """
    Protect the successful top-level composition performed by main().

    This test deliberately does NOT exercise the real MCP transport,
    discovery protocol operations, or demonstration workflows.

    Those subsystems already have their own regression protection.

    Instead, this test verifies that main():

    1. Resolves the project root.
    2. Builds the server parameters.
    3. Displays startup information.
    4. Enters MCPConnection.
    5. Uses the session exposed by that connection.
    6. Discovers capabilities with that same session.
    7. Passes the same session and discovery results into the
       demonstration workflow orchestrator.
    8. Completes workflow execution before leaving MCPConnection.
    """

    # ---------------------------------------------------------
    # Import the module, not only main().
    #
    # We need the module object because monkeypatch will replace
    # the dependencies that main() looks up from that module.
    # ---------------------------------------------------------
    import mcp_client.client as client


    # ---------------------------------------------------------
    # Record important architectural events.
    #
    # We care about subsystem relationships and lifecycle order,
    # not internal implementation details.
    # ---------------------------------------------------------
    events = []


    # ---------------------------------------------------------
    # Create unique sentinel objects.
    #
    # These let us prove that the exact same objects flow across
    # the composition boundaries.
    # ---------------------------------------------------------
    fake_project_root = object()
    fake_server_parameters = object()
    fake_session = object()

    fake_tools_result = object()
    fake_resources_result = object()
    fake_templates_result = object()
    fake_prompts_result = object()

    fake_capabilities = (
        fake_tools_result,
        fake_resources_result,
        fake_templates_result,
        fake_prompts_result,
    )


    # ---------------------------------------------------------
    # Fake project-root resolution.
    # ---------------------------------------------------------
    def fake_get_project_root():
        events.append("get_project_root")

        return fake_project_root


    # ---------------------------------------------------------
    # Fake server-parameter construction.
    #
    # This assertion protects the handoff:
    #
    #     project root
    #         ↓
    #     server configuration
    # ---------------------------------------------------------
    def fake_build_demo_server_parameters(project_root):
        assert project_root is fake_project_root

        events.append("build_demo_server_parameters")

        return fake_server_parameters


    # ---------------------------------------------------------
    # Fake startup display.
    #
    # We are not testing printed text here. Presentation behavior
    # belongs to other regression contracts.
    # ---------------------------------------------------------
    def fake_display_startup_information(*args, **kwargs):
        events.append("display_startup_information")


    # ---------------------------------------------------------
    # Fake MCP connection.
    #
    # The context manager records entry and exit so that we can
    # prove discovery and workflow execution occur while the
    # connection is active.
    # ---------------------------------------------------------
    class FakeMCPConnection:

        def __init__(self, server_parameters):
            assert server_parameters is fake_server_parameters

            events.append("create_connection")

            self.session = None

            # main() may display initialization metadata.
            #
            # Provide the minimum structure needed for that
            # existing production behavior.
            self.initialization_result = type(
                "FakeInitializationResult",
                (),
                {
                    "protocolVersion": "test-protocol",
                    "serverInfo": type(
                        "FakeServerInfo",
                        (),
                        {
                            "name": "test-server",
                        },
                    )(),
                },
            )()


        async def __aenter__(self):
            events.append("enter_connection")

            self.session = fake_session

            return self


        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            events.append("exit_connection")

            self.session = None

            return False


    # ---------------------------------------------------------
    # Fake discovery orchestration.
    #
    # Protect the session handoff:
    #
    #     MCPConnection
    #         ↓
    #     discovery
    # ---------------------------------------------------------
    async def fake_discover_server_capabilities(session):
        assert session is fake_session

        events.append("discover")

        return fake_capabilities


    # ---------------------------------------------------------
    # Fake demonstration workflow orchestration.
    #
    # Protect both:
    #
    #     same session
    #
    # and
    #
    #     same capability results
    #
    # crossing the main() composition boundary.
    # ---------------------------------------------------------
    async def fake_run_demonstration_workflows(
        session,
        tools_result,
        resources_result,
        templates_result,
        prompts_result,
    ):
        assert session is fake_session

        assert tools_result is fake_tools_result
        assert resources_result is fake_resources_result
        assert templates_result is fake_templates_result
        assert prompts_result is fake_prompts_result

        events.append("run_workflows")


    # ---------------------------------------------------------
    # Replace only the major dependencies owned outside main().
    # ---------------------------------------------------------
    monkeypatch.setattr(
        client,
        "get_project_root",
        fake_get_project_root,
    )

    monkeypatch.setattr(
        client,
        "build_demo_server_parameters",
        fake_build_demo_server_parameters,
    )

    monkeypatch.setattr(
        client,
        "display_startup_information",
        fake_display_startup_information,
    )

    monkeypatch.setattr(
        client,
        "MCPConnection",
        FakeMCPConnection,
    )

    monkeypatch.setattr(
        client,
        "discover_server_capabilities",
        fake_discover_server_capabilities,
    )

    monkeypatch.setattr(
        client,
        "run_demonstration_workflows",
        fake_run_demonstration_workflows,
    )


    # ---------------------------------------------------------
    # Execute the real composition root.
    # ---------------------------------------------------------
    await client.main()


    # ---------------------------------------------------------
    # Protect the architectural sequence.
    #
    # Most importantly:
    #
    #     enter_connection
    #          ↓
    #       discover
    #          ↓
    #    run_workflows
    #          ↓
    #     exit_connection
    #
    # Discovery and workflow execution therefore remain inside
    # the active MCP connection lifetime.
    # ---------------------------------------------------------
    assert events == [
        "get_project_root",
        "build_demo_server_parameters",
        "display_startup_information",
        "create_connection",
        "enter_connection",
        "discover",
        "run_workflows",
        "exit_connection",
    ]
    
    
@pytest.mark.asyncio
async def test_main_propagates_discovery_failure_and_skips_workflows(
    monkeypatch,
):
    """
    Protect main() when capability discovery fails.

    Architectural contract:

        enter MCPConnection
            ↓
        discover capabilities
            ↓
        discovery raises
            ↓
        demonstration workflows are NOT executed
            ↓
        MCPConnection exits
            ↓
        the original discovery exception propagates

    This test does not test the internal behavior of MCPConnection
    or the discovery subsystem. Those subsystems have their own
    dedicated regression tests.
    """

    import mcp_client.client as client

    # ---------------------------------------------------------
    # Record only the architectural events that matter.
    # ---------------------------------------------------------
    events = []

    # ---------------------------------------------------------
    # Create unique objects so identity can be verified.
    # ---------------------------------------------------------
    fake_project_root = object()
    fake_server_parameters = object()
    fake_session = object()

    # Use one specific exception instance.
    #
    # Later we will verify that this exact object escapes main(),
    # proving that main() does not replace or transform the error.
    discovery_error = RuntimeError(
        "simulated discovery failure"
    )


    # ---------------------------------------------------------
    # Configuration test doubles.
    # ---------------------------------------------------------
    def fake_get_project_root():
        events.append("get_project_root")

        return fake_project_root


    def fake_build_demo_server_parameters(project_root):
        assert project_root is fake_project_root

        events.append("build_demo_server_parameters")

        return fake_server_parameters


    def fake_display_startup_information(*args, **kwargs):
        events.append("display_startup_information")


    # ---------------------------------------------------------
    # Fake connection context manager.
    #
    # We need only enough behavior to prove that discovery happens
    # inside the connection lifetime and that __aexit__ runs after
    # discovery raises.
    # ---------------------------------------------------------
    class FakeMCPConnection:

        def __init__(self, server_parameters):
            assert server_parameters is fake_server_parameters

            events.append("create_connection")

            self.session = None

            self.initialization_result = type(
                "FakeInitializationResult",
                (),
                {
                    "protocolVersion": "test-protocol",
                    "serverInfo": type(
                        "FakeServerInfo",
                        (),
                        {
                            "name": "test-server",
                        },
                    )(),
                },
            )()


        async def __aenter__(self):
            events.append("enter_connection")

            self.session = fake_session

            return self


        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            events.append("exit_connection")

            # The exception reaching __aexit__ must be the same
            # discovery exception raised below.
            assert exc_type is RuntimeError
            assert exc_value is discovery_error

            self.session = None

            # False means:
            #
            #     do not suppress the exception
            #
            # Therefore the exception should continue outward
            # from main().
            return False


    # ---------------------------------------------------------
    # Discovery succeeds far enough to receive the correct
    # session, then deliberately fails.
    # ---------------------------------------------------------
    async def fake_discover_server_capabilities(session):
        assert session is fake_session

        events.append("discover")

        raise discovery_error


    # ---------------------------------------------------------
    # This must NEVER execute.
    #
    # If it runs, main() incorrectly continued after discovery
    # failed.
    # ---------------------------------------------------------
    async def fake_run_demonstration_workflows(*args, **kwargs):
        events.append("run_workflows")

        pytest.fail(
            "run_demonstration_workflows() must not run "
            "after discovery fails"
        )


    # ---------------------------------------------------------
    # Replace main()'s major external dependencies.
    # ---------------------------------------------------------
    monkeypatch.setattr(
        client,
        "get_project_root",
        fake_get_project_root,
    )

    monkeypatch.setattr(
        client,
        "build_demo_server_parameters",
        fake_build_demo_server_parameters,
    )

    monkeypatch.setattr(
        client,
        "display_startup_information",
        fake_display_startup_information,
    )

    monkeypatch.setattr(
        client,
        "MCPConnection",
        FakeMCPConnection,
    )

    monkeypatch.setattr(
        client,
        "discover_server_capabilities",
        fake_discover_server_capabilities,
    )

    monkeypatch.setattr(
        client,
        "run_demonstration_workflows",
        fake_run_demonstration_workflows,
    )


    # ---------------------------------------------------------
    # Execute the real main().
    #
    # pytest.raises captures the exception only so that we can
    # verify its identity afterward.
    # ---------------------------------------------------------
    with pytest.raises(RuntimeError) as exc_info:
        await client.main()


    # ---------------------------------------------------------
    # Protect exception identity.
    #
    # "is" is intentional. We want the SAME exception object,
    # not merely another RuntimeError with the same message.
    # ---------------------------------------------------------
    assert exc_info.value is discovery_error


    # ---------------------------------------------------------
    # Protect the architectural failure sequence.
    #
    # Notice that "run_workflows" must be absent.
    # ---------------------------------------------------------
    assert events == [
        "get_project_root",
        "build_demo_server_parameters",
        "display_startup_information",
        "create_connection",
        "enter_connection",
        "discover",
        "exit_connection",
    ]
