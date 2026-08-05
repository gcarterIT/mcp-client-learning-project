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
