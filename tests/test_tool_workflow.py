"""
Regression tests for the MCP tool workflow.

These tests protect the architectural boundary between:

    previously discovered tool metadata
                +
        active MCP session
                ↓
        tool workflow
                ↓
        session.call_tool(...)

The tests intentionally do not create a real MCP connection or start
the demonstration server.

Part 10B.1 protects workflow delegation rather than MCP transport,
connection lifecycle, discovery, presentation, or server business logic.
"""

from types import SimpleNamespace

import pytest

from mcp_client.tool_workflow import invoke_add_numbers


class FakeToolSession:
    """
    Minimal test double for the ClientSession dependency used by
    invoke_add_numbers().

    This fake intentionally exposes only call_tool().

    It does NOT implement list_tools(), because capability discovery belongs
    to the discovery subsystem rather than the workflow subsystem.
    """

    def __init__(self) -> None:
        self.call_count = 0
        self.called_tool_name = None
        self.called_arguments = None

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
    ):
        """
        Record the delegated tool invocation and return an obviously
        successful deterministic result.

        The structured result contains 42 so the existing workflow's
        verification behavior can complete normally.
        """
        self.call_count += 1
        self.called_tool_name = tool_name
        self.called_arguments = arguments

        return SimpleNamespace(
            isError=False,
            content=[],
            structured_content={
                "result": 42,
            },
        )


@pytest.mark.asyncio
async def test_invoke_add_numbers_delegates_expected_tool_call():
    """
    Protect the successful tool-workflow delegation boundary.

    Given:
        - previously discovered metadata containing add_numbers
        - an active session capable of tool invocation

    Verify that invoke_add_numbers():

        1. uses the supplied discovery metadata,
        2. invokes add_numbers exactly once,
        3. supplies the deterministic demonstration arguments,
        4. completes successfully.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------
    #
    # This represents metadata that was ALREADY obtained by the
    # discovery subsystem.
    #
    # Only the fields consumed by the workflow are represented.
    # ---------------------------------------------------------

    add_numbers_tool = SimpleNamespace(
        name="add_numbers",
        description="Add two numbers.",
        inputSchema={
            "type": "object",
        },
    )

    tools_result = SimpleNamespace(
        tools=[
            add_numbers_tool,
        ],
    )

    session = FakeToolSession()

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    await invoke_add_numbers(
        session=session,
        tools_result=tools_result,
    )

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------
    #
    # These assertions protect the architectural delegation
    # contract rather than internal helper implementation.
    # ---------------------------------------------------------

    assert session.call_count == 1

    assert session.called_tool_name == "add_numbers"

    assert session.called_arguments == {
        "a": 20,
        "b": 22,
    }
    
@pytest.mark.asyncio
async def test_invoke_add_numbers_does_not_call_tool_when_required_tool_missing():
    """
    Protect the missing-required-tool workflow contract.

    Given discovery metadata that does not advertise add_numbers:

        1. invoke_add_numbers() must raise RuntimeError,
        2. session.call_tool() must not be invoked.

    This protects the architectural rule that workflow behavior depends on
    previously discovered capability metadata rather than blindly invoking
    a server capability by name.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------
    #
    # Simulate a server that advertises a different tool but
    # does NOT advertise add_numbers.
    # ---------------------------------------------------------

    other_tool = SimpleNamespace(
        name="some_other_tool",
        description="A different tool.",
        inputSchema={
            "type": "object",
        },
    )

    tools_result = SimpleNamespace(
        tools=[
            other_tool,
        ],
    )

    session = FakeToolSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(
        RuntimeError,
        match="add_numbers",
    ):
        await invoke_add_numbers(
            session=session,
            tools_result=tools_result,
        )

    # ---------------------------------------------------------
    # Architectural assertion
    # ---------------------------------------------------------
    #
    # The workflow must stop at the discovery-metadata boundary.
    # No MCP tool request should be sent for a capability that
    # was not advertised.
    # ---------------------------------------------------------

    assert session.call_count == 0
    
@pytest.mark.asyncio
async def test_invoke_add_numbers_rejects_incorrect_tool_result():
    """
    Protect the deterministic result-verification contract.

    Given:
        - discovery metadata containing add_numbers
        - a successful tool invocation
        - a returned result that does NOT contain the expected value 42

    Verify that invoke_add_numbers():

        1. invokes the required tool exactly once,
        2. does not accept the incorrect result as workflow success,
        3. raises AssertionError.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    add_numbers_tool = SimpleNamespace(
        name="add_numbers",
        description="Add two numbers.",
        inputSchema={
            "type": "object",
        },
    )

    tools_result = SimpleNamespace(
        tools=[
            add_numbers_tool,
        ],
    )

    class IncorrectResultSession:
        """
        Minimal ClientSession test double.

        The tool invocation itself succeeds, but the returned
        application result is deliberately incorrect.
        """

        def __init__(self) -> None:
            self.call_count = 0
            self.called_tool_name = None
            self.called_arguments = None

        async def call_tool(
            self,
            tool_name: str,
            arguments: dict,
        ):
            self.call_count += 1
            self.called_tool_name = tool_name
            self.called_arguments = arguments

            # Deliberately return the wrong deterministic result.
            return SimpleNamespace(
                isError=False,
                content=[],
                structured_content={
                    "result": 999,
                },
            )

    session = IncorrectResultSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(AssertionError):
        await invoke_add_numbers(
            session=session,
            tools_result=tools_result,
        )

    # ---------------------------------------------------------
    # Architectural assertions
    # ---------------------------------------------------------
    #
    # These confirm that the failure occurred AFTER correct
    # workflow delegation, not because invocation was skipped.
    # ---------------------------------------------------------

    assert session.call_count == 1

    assert session.called_tool_name == "add_numbers"

    assert session.called_arguments == {
        "a": 20,
        "b": 22,
    }
    

    
