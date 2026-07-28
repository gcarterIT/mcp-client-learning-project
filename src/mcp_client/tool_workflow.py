"""
Tool invocation workflow
========================

This module owns the complete deterministic tool workflow used by the
learning client.

Responsibilities
----------------
- locate one advertised MCP tool
- invoke that tool with deterministic arguments
- display the returned tool result
- verify that the expected result was returned

This module does not own:

- MCP connection lifecycle
- capability discovery
- resource workflows
- prompt workflows
- application startup orchestration
"""

from typing import Any

from mcp import ClientSession, types

from formatters import (
    display_tool_result,
    format_json,
    get_structured_tool_content,
)


def find_tool(
    tools_result: Any,
    tool_name: str,
) -> Any | None:
    """
    Find one tool by name in a ListToolsResult object.

    Parameters
    ----------
    tools_result:
        The structured result returned by session.list_tools().

    tool_name:
        The exact MCP tool name we want to locate.

    Returns
    -------
    Tool | None
        The matching MCP Tool object when found.
        None when the server did not advertise that tool.

    Why return None instead of immediately raising an exception?
    -------------------------------------------------------------
    This function has one responsibility: search the metadata.

    The calling function decides how a missing tool should be handled.
    Keeping those responsibilities separate makes the code easier to test
    and reuse later.
    """

    for tool in tools_result.tools:
        if tool.name == tool_name:
            return tool

    return None


def collect_result_text(
    tool_result: Any,
) -> str:
    """
    Combine all TextContent blocks into one searchable string.

    This helper is used only for deterministic verification.

    For a production client, we would normally rely on structured content
    when the tool defines an output schema. Text verification is included
    here because a simple FastMCP tool may return its value as TextContent.
    """

    text_values: list[str] = []

    for content_block in (
        getattr(tool_result, "content", []) or []
    ):
        if isinstance(
            content_block,
            types.TextContent,
        ):
            text_values.append(
                content_block.text
            )

    return "\n".join(text_values)


def value_appears_in_structure(
    value: Any,
    expected_number: int | float,
) -> bool:
    """
    Recursively search structured data for an expected numeric value.

    This supports structured tool results shaped like:

        {"result": 42}

    or:

        {"data": {"sum": 42}}

    It searches dictionaries, lists, tuples, and scalar values.

    Important limitation
    --------------------
    This is a teaching-oriented verification helper. In a production client,
    the tool's declared output schema should determine the exact field to
    validate rather than recursively searching every value.
    """

    # bool is a subclass of int in Python, so reject it explicitly.
    if isinstance(value, bool):
        return False

    if isinstance(value, (int, float)):
        return value == expected_number

    if isinstance(value, dict):
        return any(
            value_appears_in_structure(
                nested_value,
                expected_number,
            )
            for nested_value in value.values()
        )

    if isinstance(value, (list, tuple)):
        return any(
            value_appears_in_structure(
                nested_value,
                expected_number,
            )
            for nested_value in value
        )

    return False


def result_contains_expected_number(
    tool_result: Any,
    expected_number: int | float,
) -> bool:
    """
    Verify that a tool result contains the expected numeric answer.

    Verification order
    ------------------
    1. Reject any result whose isError flag is true.
    2. Search structured content for the numeric value.
    3. Search TextContent for a textual representation of the value.

    Why support both forms?
    -----------------------
    MCP tools may return structured content, text content, or both.

    A mature application should prefer a declared output schema and
    structured content. This learning client remains compatible with the
    simple result representation produced by the demo server.
    """

    if getattr(tool_result, "isError", False):
        return False

    structured_content = (
        get_structured_tool_content(
            tool_result
        )
    )

    if structured_content is not None:
        if value_appears_in_structure(
            structured_content,
            expected_number,
        ):
            return True

    result_text = collect_result_text(
        tool_result
    )

    possible_representations = {
        str(expected_number),
        str(float(expected_number)),
    }

    return any(
        representation in result_text
        for representation in possible_representations
    )


async def invoke_add_numbers(
    session: ClientSession,
    tools_result: Any,
) -> None:
    """
    Discover, invoke, display, and verify the add_numbers tool.

    Workflow
    --------
    locate tool metadata
        ↓
    inspect its advertised schema
        ↓
    build deterministic arguments
        ↓
    invoke the tool
        ↓
    inspect CallToolResult
        ↓
    verify expected result

    Parameters
    ----------
    session:
        An initialized MCP ClientSession.

    tools_result:
        The previously discovered ListToolsResult.

    Why pass tools_result into this function?
    -----------------------------------------
    Capability discovery already requested the tool list.

    Passing that result here avoids making a second unnecessary tools/list
    request.
    """

    tool_name = "add_numbers"

    print("\n" + "=" * 70)
    print("FIRST TOOL INVOCATION")
    print("=" * 70)

    print(f"Looking for tool: {tool_name}")

    tool = find_tool(
        tools_result=tools_result,
        tool_name=tool_name,
    )

    if tool is None:
        raise RuntimeError(
            "The server did not advertise the required tool: "
            f"{tool_name}"
        )

    print("Tool found.")
    print(f"Description: {tool.description}")
    print("Advertised input schema:")
    print(
        format_json(
            tool.inputSchema
        )
    )

    arguments = {
        "a": 20,
        "b": 22,
    }

    expected_result = 42

    print("\nInvocation request:")
    print(f"Tool name: {tool_name}")
    print("Arguments:")
    print(
        format_json(
            arguments
        )
    )
    print(f"Expected result: {expected_result}")

    tool_result = await session.call_tool(
        tool_name,
        arguments=arguments,
    )

    display_tool_result(
        tool_result
    )

    verified = result_contains_expected_number(
        tool_result,
        expected_result,
    )

    if not verified:
        raise AssertionError(
            "Tool invocation completed, but the expected result "
            f"{expected_result} was not found in the returned content."
        )

    print("\nVerification: PASSED")
    print(
        f"Confirmed that {arguments['a']} + "
        f"{arguments['b']} = {expected_result}"
    )