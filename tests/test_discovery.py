"""
Regression tests for MCP capability discovery.

These tests protect the externally observable behavior of:

    mcp_client.discovery.discover_capabilities

The tests do not create a real MCP connection or start an MCP server.

Instead, they provide a controlled fake session so we can verify:

1. Which discovery methods are called.
2. The order in which they are called.
3. Which display function receives each result.
4. Whether the original result objects are returned unchanged.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from mcp_client import discovery


@pytest.fixture
def anyio_backend() -> str:
    """
    Run AnyIO tests with the asyncio backend.

    MCP ClientSession operations are asynchronous, so the discovery
    regression test must run inside an asynchronous test environment.
    """

    return "asyncio"


@pytest.mark.anyio
async def test_discover_capabilities_discovers_displays_and_returns_all_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect the complete successful capability-discovery sequence.

    Expected sequence:

        list_tools()
            ↓
        display_tools()
            ↓
        list_resources()
            ↓
        display_resources()
            ↓
        list_resource_templates()
            ↓
        display_resource_templates()
            ↓
        list_prompts()
            ↓
        display_prompts()
            ↓
        return all four original result objects
    """

    # -------------------------------------------------------------
    # Arrange: create four distinct result objects.
    #
    # Plain object() instances are sufficient because this test does
    # not inspect the metadata inside the results. It only verifies
    # that each exact object is displayed and returned correctly.
    # -------------------------------------------------------------

    tools_result = object()
    resources_result = object()
    templates_result = object()
    prompts_result = object()

    # Record every important operation in one shared list.
    #
    # Using one list allows the test to verify ordering across both:
    #
    #     asynchronous session calls
    #     synchronous display-function calls
    operation_log: list[tuple[str, object | None]] = []

    # -------------------------------------------------------------
    # Arrange: create controlled asynchronous session operations.
    # -------------------------------------------------------------

    async def list_tools() -> object:
        operation_log.append(("list_tools", None))
        return tools_result

    async def list_resources() -> object:
        operation_log.append(("list_resources", None))
        return resources_result

    async def list_resource_templates() -> object:
        operation_log.append(("list_resource_templates", None))
        return templates_result

    async def list_prompts() -> object:
        operation_log.append(("list_prompts", None))
        return prompts_result

    # A general Mock is sufficient for the session container.
    #
    # Each MCP discovery operation is attached as an AsyncMock because
    # discover_capabilities() awaits every session method.
    session = Mock()

    session.list_tools = AsyncMock(side_effect=list_tools)
    session.list_resources = AsyncMock(side_effect=list_resources)
    session.list_resource_templates = AsyncMock(
        side_effect=list_resource_templates
    )
    session.list_prompts = AsyncMock(side_effect=list_prompts)

    # -------------------------------------------------------------
    # Arrange: replace the real display functions.
    #
    # We do not want this orchestration test to depend on the detailed
    # terminal formatting performed by the display helpers.
    #
    # Each replacement records:
    #
    #     which display function was called
    #     which exact result object it received
    # -------------------------------------------------------------

    def fake_display_tools(result: object) -> None:
        operation_log.append(("display_tools", result))

    def fake_display_resources(result: object) -> None:
        operation_log.append(("display_resources", result))

    def fake_display_resource_templates(result: object) -> None:
        operation_log.append(("display_resource_templates", result))

    def fake_display_prompts(result: object) -> None:
        operation_log.append(("display_prompts", result))

    monkeypatch.setattr(
        discovery,
        "display_tools",
        fake_display_tools,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        fake_display_resources,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        fake_display_resource_templates,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        fake_display_prompts,
    )

    # -------------------------------------------------------------
    # Act: execute the reusable discovery function.
    # -------------------------------------------------------------

    returned_results = await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: every session operation was awaited exactly once.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()
    session.list_resources.assert_awaited_once_with()
    session.list_resource_templates.assert_awaited_once_with()
    session.list_prompts.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 2: discovery and display occurred in the required order.
    # -------------------------------------------------------------

    assert operation_log == [
        ("list_tools", None),
        ("display_tools", tools_result),
        ("list_resources", None),
        ("display_resources", resources_result),
        ("list_resource_templates", None),
        ("display_resource_templates", templates_result),
        ("list_prompts", None),
        ("display_prompts", prompts_result),
    ]

    # -------------------------------------------------------------
    # Assert 3: the function returned exactly four results.
    # -------------------------------------------------------------

    assert len(returned_results) == 4

    # -------------------------------------------------------------
    # Assert 4: each original SDK result object was preserved.
    #
    # `is` checks object identity rather than merely equal values.
    # This protects the contract that discover_capabilities() returns
    # the original result objects without copying or transforming them.
    # -------------------------------------------------------------

    assert returned_results[0] is tools_result
    assert returned_results[1] is resources_result
    assert returned_results[2] is templates_result
    assert returned_results[3] is prompts_result
    
@pytest.mark.parametrize(
    (
        "display_function_name",
        "collection_attribute",
        "expected_message",
    ),
    [
        (
            "display_tools",
            "tools",
            "No tools were advertised by the server.",
        ),
        (
            "display_resources",
            "resources",
            "No static resources were advertised by the server.",
        ),
        (
            "display_resource_templates",
            "resourceTemplates",
            "No resource templates were advertised by the server.",
        ),
        (
            "display_prompts",
            "prompts",
            "No prompts were advertised by the server.",
        ),
    ],
)


def test_display_helper_handles_empty_capability_collection(
    display_function_name: str,
    collection_attribute: str,
    expected_message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Protect empty capability-collection behavior.

    A valid MCP server may advertise no capabilities in one or more
    categories. Each display helper must:

    1. Accept its corresponding empty collection.
    2. Print the existing explanatory message.
    3. Return normally without raising an exception.
    """

    # -------------------------------------------------------------
    # Arrange: create a small result-shaped object.
    #
    # Each display helper expects a different collection attribute:
    #
    #     tools
    #     resources
    #     resourceTemplates
    #     prompts
    #
    # setattr() creates the appropriate attribute dynamically for
    # the current parameterized test case.
    # -------------------------------------------------------------

    result = SimpleNamespace()
    setattr(
        result,
        collection_attribute,
        [],
    )

    # Retrieve the corresponding display helper from the discovery
    # module using its parameterized function name.
    display_function = getattr(
        discovery,
        display_function_name,
    )

    # -------------------------------------------------------------
    # Act: display the empty capability result.
    # -------------------------------------------------------------

    returned_value = display_function(result)

    # Capture everything written to standard output by the helper.
    captured_output = capsys.readouterr().out

    # -------------------------------------------------------------
    # Assert: the helper reported the empty collection clearly.
    # -------------------------------------------------------------

    assert expected_message in captured_output

    # The display helpers are presentation procedures and therefore
    # return None after completing normally.
    assert returned_value is None
    
    
@pytest.mark.parametrize(
    (
        "display_function_name",
        "discovery_result",
        "expected_context",
    ),
    [
        # ---------------------------------------------------------
        # Tool description is optional.
        # ---------------------------------------------------------
        (
            "display_tools",
            SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="example_tool",
                        description=None,
                        inputSchema={
                            "type": "object",
                            "properties": {},
                        },
                    ),
                ],
            ),
            "Name: example_tool",
        ),

        # ---------------------------------------------------------
        # Static-resource description is optional.
        # ---------------------------------------------------------
        (
            "display_resources",
            SimpleNamespace(
                resources=[
                    SimpleNamespace(
                        uri="example://resource",
                        name="Example Resource",
                        description=None,
                        mimeType="text/plain",
                    ),
                ],
            ),
            "Name: Example Resource",
        ),

        # ---------------------------------------------------------
        # Resource-template description is optional.
        # ---------------------------------------------------------
        (
            "display_resource_templates",
            SimpleNamespace(
                resourceTemplates=[
                    SimpleNamespace(
                        uriTemplate="example://items/{item_id}",
                        name="Example Template",
                        description=None,
                        mimeType="application/json",
                    ),
                ],
            ),
            "Name: Example Template",
        ),

        # ---------------------------------------------------------
        # Prompt description is optional.
        #
        # An empty argument list keeps this case focused on the
        # prompt's own description.
        # ---------------------------------------------------------
        (
            "display_prompts",
            SimpleNamespace(
                prompts=[
                    SimpleNamespace(
                        name="example_prompt",
                        description=None,
                        arguments=[],
                    ),
                ],
            ),
            "Name: example_prompt",
        ),

        # ---------------------------------------------------------
        # Prompt-argument descriptions are also optional.
        #
        # The prompt itself has a real description so this case
        # isolates the argument-description fallback.
        # ---------------------------------------------------------
        (
            "display_prompts",
            SimpleNamespace(
                prompts=[
                    SimpleNamespace(
                        name="prompt_with_argument",
                        description="Example prompt description.",
                        arguments=[
                            SimpleNamespace(
                                name="topic",
                                description=None,
                                required=True,
                            ),
                        ],
                    ),
                ],
            ),
            "Name: topic",
        ),
    ],
)


def test_display_helper_uses_fallback_for_missing_description(
    display_function_name: str,
    discovery_result: SimpleNamespace,
    expected_context: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Protect readable fallback output for optional descriptions.

    MCP metadata descriptions may be None. Each display helper must:

    1. Accept the missing description.
    2. Display "(No description provided)".
    3. Complete normally.
    """

    # Retrieve the display helper named by the current test case.
    display_function = getattr(
        discovery,
        display_function_name,
    )

    # Execute the display helper with the small result-shaped object.
    returned_value = display_function(
        discovery_result
    )

    # Capture the terminal output produced by the helper.
    captured_output = capsys.readouterr().out

    # Confirm that the output belongs to the expected metadata item.
    #
    # This prevents a false positive where fallback text appears for
    # some unrelated object.
    assert expected_context in captured_output

    # Protect the existing human-readable fallback.
    assert (
        "Description: (No description provided)"
        in captured_output
    )

    # Display helpers complete normally and return None.
    assert returned_value is None    
    

@pytest.mark.parametrize(
    (
        "display_function_name",
        "discovery_result",
        "expected_context",
    ),
    [
        # ---------------------------------------------------------
        # Static-resource MIME type is optional.
        # ---------------------------------------------------------
        (
            "display_resources",
            SimpleNamespace(
                resources=[
                    SimpleNamespace(
                        uri="example://resource",
                        name="Example Resource",
                        description="Example resource description.",
                        mimeType=None,
                    ),
                ],
            ),
            "Name: Example Resource",
        ),

        # ---------------------------------------------------------
        # Resource-template MIME type is optional.
        # ---------------------------------------------------------
        (
            "display_resource_templates",
            SimpleNamespace(
                resourceTemplates=[
                    SimpleNamespace(
                        uriTemplate="example://items/{item_id}",
                        name="Example Template",
                        description="Example template description.",
                        mimeType=None,
                    ),
                ],
            ),
            "Name: Example Template",
        ),
    ],
)
def test_display_helper_uses_fallback_for_missing_mime_type(
    display_function_name: str,
    discovery_result: SimpleNamespace,
    expected_context: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Protect readable fallback output for optional MIME types.

    MCP resource metadata may omit mimeType. The applicable display
    helpers must:

    1. Accept mimeType=None.
    2. Display "(No MIME type provided)".
    3. Complete normally.
    """

    # Retrieve the display helper named by the current test case.
    display_function = getattr(
        discovery,
        display_function_name,
    )

    # Execute the helper using the small result-shaped object.
    returned_value = display_function(
        discovery_result
    )

    # Capture everything written by the helper.
    captured_output = capsys.readouterr().out

    # Confirm that the output belongs to the expected metadata item.
    assert expected_context in captured_output

    # Protect the existing human-readable MIME-type fallback.
    assert (
        "MIME type: (No MIME type provided)"
        in captured_output
    )

    # Display helpers return None after completing normally.
    assert returned_value is None

    
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_list_tools_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when the first discovery operation fails.

    Expected behavior:

        list_tools()
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        no display helper runs
            ↓
        no later discovery method runs
    """

    # -------------------------------------------------------------
    # Arrange: create one specific exception object.
    #
    # Later, the identity assertion verifies that discovery propagates
    # this exact object rather than creating a replacement exception.
    # -------------------------------------------------------------

    expected_exception = RuntimeError(
        "tool discovery failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # list_tools() fails immediately.
    #
    # The remaining methods are also AsyncMocks so the test can prove
    # that discovery never reaches them.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        side_effect=expected_exception
    )
    session.list_resources = AsyncMock()
    session.list_resource_templates = AsyncMock()
    session.list_prompts = AsyncMock()

    # -------------------------------------------------------------
    # Arrange: replace every display helper with a Mock.
    #
    # Because list_tools() fails before returning a result, none of
    # these display helpers should be called.
    # -------------------------------------------------------------

    display_tools_mock = Mock()
    display_resources_mock = Mock()
    display_resource_templates_mock = Mock()
    display_prompts_mock = Mock()

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: execute discovery and capture the exception.
    #
    # pytest.raises() verifies the exception type and exposes the
    # captured exception through exception_info.value.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: the exact original exception object propagated.
    #
    # `is` is stronger than comparing only the type or message.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: the failing operation was attempted exactly once.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: discovery stopped immediately after the failure.
    # -------------------------------------------------------------

    session.list_resources.assert_not_awaited()
    session.list_resource_templates.assert_not_awaited()
    session.list_prompts.assert_not_awaited()

    # -------------------------------------------------------------
    # Assert 4: no display helper ran.
    #
    # display_tools() requires a successful tools result, which was
    # never returned. The later display helpers are also unreachable.
    # -------------------------------------------------------------

    display_tools_mock.assert_not_called()
    display_resources_mock.assert_not_called()
    display_resource_templates_mock.assert_not_called()
    display_prompts_mock.assert_not_called()
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_list_resources_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when resource discovery fails.

    Expected behavior:

        list_tools()
            ↓
        succeeds
            ↓
        display_tools()
            ↓
        list_resources()
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        display_resources() does not run
            ↓
        later discovery operations do not run
    """

    # -------------------------------------------------------------
    # Arrange: create the successful tools result.
    #
    # A plain object is sufficient because the real display function
    # will be replaced by a mock. The test only needs to verify that
    # this exact object reaches display_tools().
    # -------------------------------------------------------------

    tools_result = object()

    # Create one specific exception object.
    #
    # The identity assertion later proves that discovery propagates
    # this exact exception instead of wrapping or replacing it.
    expected_exception = RuntimeError(
        "resource discovery failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # Tool discovery succeeds.
    # Resource discovery fails.
    # Template and prompt discovery must remain unreachable.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        return_value=tools_result
    )

    session.list_resources = AsyncMock(
        side_effect=expected_exception
    )

    session.list_resource_templates = AsyncMock()
    session.list_prompts = AsyncMock()

    # -------------------------------------------------------------
    # Arrange: replace all display helpers.
    #
    # display_tools() should run once because tool discovery succeeds.
    #
    # The other display helpers must not run because execution stops
    # at list_resources().
    # -------------------------------------------------------------

    display_tools_mock = Mock()
    display_resources_mock = Mock()
    display_resource_templates_mock = Mock()
    display_prompts_mock = Mock()

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: run discovery and capture the failure.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: preserve the original exception object.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: discovery reached the correct partial-progress point.
    #
    # Tool discovery completed.
    # Resource discovery was attempted and failed.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()
    session.list_resources.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: later MCP discovery operations did not run.
    # -------------------------------------------------------------

    session.list_resource_templates.assert_not_awaited()
    session.list_prompts.assert_not_awaited()

    # -------------------------------------------------------------
    # Assert 4: only completed discovery results were displayed.
    #
    # The tools result existed, so display_tools() must receive it.
    #
    # No resources result existed, so display_resources() must not run.
    # -------------------------------------------------------------

    display_tools_mock.assert_called_once_with(
        tools_result
    )

    display_resources_mock.assert_not_called()
    display_resource_templates_mock.assert_not_called()
    display_prompts_mock.assert_not_called()
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_list_resource_templates_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when resource-template discovery fails.

    Expected behavior:

        list_tools()
            ↓
        succeeds
            ↓
        display_tools()
            ↓
        list_resources()
            ↓
        succeeds
            ↓
        display_resources()
            ↓
        list_resource_templates()
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        display_resource_templates() does not run
            ↓
        prompt discovery does not run
    """

    # -------------------------------------------------------------
    # Arrange: create successful earlier discovery results.
    #
    # Plain object instances are sufficient because the display
    # helpers will be replaced by mocks.
    # -------------------------------------------------------------

    tools_result = object()
    resources_result = object()

    # Create one specific exception object so the test can verify
    # identity-preserving propagation.
    expected_exception = RuntimeError(
        "resource-template discovery failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # Tool and resource discovery succeed.
    # Resource-template discovery fails.
    # Prompt discovery must remain unreachable.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        return_value=tools_result
    )

    session.list_resources = AsyncMock(
        return_value=resources_result
    )

    session.list_resource_templates = AsyncMock(
        side_effect=expected_exception
    )

    session.list_prompts = AsyncMock()

    # -------------------------------------------------------------
    # Arrange: replace all display helpers.
    #
    # The tools and resources displays should run once.
    #
    # The resource-template and prompt displays must not run.
    # -------------------------------------------------------------

    display_tools_mock = Mock()
    display_resources_mock = Mock()
    display_resource_templates_mock = Mock()
    display_prompts_mock = Mock()

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: execute discovery and capture the failure.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: preserve the original exception object.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: verify the exact partial-progress boundary.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()
    session.list_resources.assert_awaited_once_with()
    session.list_resource_templates.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: prompt discovery did not run.
    # -------------------------------------------------------------

    session.list_prompts.assert_not_awaited()

    # -------------------------------------------------------------
    # Assert 4: only successful discovery results were displayed.
    # -------------------------------------------------------------

    display_tools_mock.assert_called_once_with(
        tools_result
    )

    display_resources_mock.assert_called_once_with(
        resources_result
    )

    display_resource_templates_mock.assert_not_called()
    display_prompts_mock.assert_not_called()
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_list_prompts_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when prompt discovery fails.

    Expected behavior:

        list_tools()
            ↓
        succeeds
            ↓
        display_tools()
            ↓
        list_resources()
            ↓
        succeeds
            ↓
        display_resources()
            ↓
        list_resource_templates()
            ↓
        succeeds
            ↓
        display_resource_templates()
            ↓
        list_prompts()
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        display_prompts() does not run
            ↓
        no result tuple is returned
    """

    # -------------------------------------------------------------
    # Arrange: create successful earlier discovery results.
    #
    # Plain objects are sufficient because the real display helpers
    # will be replaced with mocks.
    # -------------------------------------------------------------

    tools_result = object()
    resources_result = object()
    templates_result = object()

    # Create one specific exception object.
    #
    # The identity assertion later verifies that the exact original
    # exception propagates without wrapping or replacement.
    expected_exception = RuntimeError(
        "prompt discovery failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # The first three discovery calls succeed.
    # Prompt discovery fails.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        return_value=tools_result
    )

    session.list_resources = AsyncMock(
        return_value=resources_result
    )

    session.list_resource_templates = AsyncMock(
        return_value=templates_result
    )

    session.list_prompts = AsyncMock(
        side_effect=expected_exception
    )

    # -------------------------------------------------------------
    # Arrange: replace all display helpers.
    #
    # The first three helpers should run once with their successful
    # results. display_prompts() must not run because no prompt result
    # was returned.
    # -------------------------------------------------------------

    display_tools_mock = Mock()
    display_resources_mock = Mock()
    display_resource_templates_mock = Mock()
    display_prompts_mock = Mock()

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: execute discovery and capture the failure.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: preserve the original exception object.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: verify that all four discovery operations were reached.
    #
    # The first three succeeded.
    # The fourth was attempted and failed.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()
    session.list_resources.assert_awaited_once_with()
    session.list_resource_templates.assert_awaited_once_with()
    session.list_prompts.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: verify that every successful result was displayed.
    # -------------------------------------------------------------

    display_tools_mock.assert_called_once_with(
        tools_result
    )

    display_resources_mock.assert_called_once_with(
        resources_result
    )

    display_resource_templates_mock.assert_called_once_with(
        templates_result
    )

    # -------------------------------------------------------------
    # Assert 4: no nonexistent prompt result was displayed.
    # -------------------------------------------------------------

    display_prompts_mock.assert_not_called()
    
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_display_tools_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when tool discovery succeeds but its
    presentation helper fails.

    Expected behavior:

        list_tools()
            ↓
        returns tools_result
            ↓
        display_tools(tools_result)
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        no later discovery or display operation runs
    """

    # -------------------------------------------------------------
    # Arrange: create the successful discovery result.
    #
    # The real display helper will be replaced, so a plain object is
    # sufficient. Identity assertions will verify that this exact
    # object reaches display_tools().
    # -------------------------------------------------------------

    tools_result = object()

    # Create one specific exception instance.
    #
    # Later, an identity assertion verifies direct propagation rather
    # than exception wrapping or replacement.
    expected_exception = RuntimeError(
        "tool display failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # Tool discovery succeeds. All later discovery operations should
    # remain unreachable after display_tools() fails.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        return_value=tools_result
    )
    session.list_resources = AsyncMock()
    session.list_resource_templates = AsyncMock()
    session.list_prompts = AsyncMock()

    # -------------------------------------------------------------
    # Arrange: configure display_tools() to fail.
    #
    # The remaining display helpers are normal mocks so the test can
    # prove that they were never called.
    # -------------------------------------------------------------

    display_tools_mock = Mock(
        side_effect=expected_exception
    )
    display_resources_mock = Mock()
    display_resource_templates_mock = Mock()
    display_prompts_mock = Mock()

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: execute discovery and capture the failure.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: the exact display exception propagated.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: tool discovery completed successfully once.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: display_tools() received the exact tools result.
    # -------------------------------------------------------------

    display_tools_mock.assert_called_once_with(
        tools_result
    )

    # -------------------------------------------------------------
    # Assert 4: no later discovery operation began.
    # -------------------------------------------------------------

    session.list_resources.assert_not_awaited()
    session.list_resource_templates.assert_not_awaited()
    session.list_prompts.assert_not_awaited()

    # -------------------------------------------------------------
    # Assert 5: no later presentation helper ran.
    # -------------------------------------------------------------

    display_resources_mock.assert_not_called()
    display_resource_templates_mock.assert_not_called()
    display_prompts_mock.assert_not_called()  
    
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_display_resources_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when resource discovery succeeds but its
    presentation helper fails.

    Expected behavior:

        list_tools()
            ↓
        succeeds
            ↓
        display_tools()
            ↓
        succeeds
            ↓
        list_resources()
            ↓
        succeeds
            ↓
        display_resources()
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        later discovery and presentation operations do not run
    """

    # -------------------------------------------------------------
    # Arrange: create successful discovery results.
    #
    # Plain object instances are sufficient because the real display
    # helpers are replaced with mocks.
    # -------------------------------------------------------------

    tools_result = object()
    resources_result = object()

    # Create one specific exception instance so we can verify that
    # discover_capabilities() propagates this exact object.
    expected_exception = RuntimeError(
        "resource display failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # Tool and resource discovery succeed.
    # Template and prompt discovery must remain unreachable.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        return_value=tools_result
    )

    session.list_resources = AsyncMock(
        return_value=resources_result
    )

    session.list_resource_templates = AsyncMock()
    session.list_prompts = AsyncMock()

    # -------------------------------------------------------------
    # Arrange: configure the display helpers.
    #
    # display_tools() succeeds.
    # display_resources() raises.
    # Later display helpers must never run.
    # -------------------------------------------------------------

    display_tools_mock = Mock()

    display_resources_mock = Mock(
        side_effect=expected_exception
    )

    display_resource_templates_mock = Mock()
    display_prompts_mock = Mock()

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: execute discovery and capture the failure.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: preserve the original exception object.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: verify the exact partial-progress boundary.
    #
    # Both tool and resource discovery completed successfully.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()
    session.list_resources.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: verify successful earlier presentation.
    # -------------------------------------------------------------

    display_tools_mock.assert_called_once_with(
        tools_result
    )

    # -------------------------------------------------------------
    # Assert 4: verify that the failing helper received the exact
    # resource result.
    # -------------------------------------------------------------

    display_resources_mock.assert_called_once_with(
        resources_result
    )

    # -------------------------------------------------------------
    # Assert 5: no later MCP discovery operation began.
    # -------------------------------------------------------------

    session.list_resource_templates.assert_not_awaited()
    session.list_prompts.assert_not_awaited()

    # -------------------------------------------------------------
    # Assert 6: no later display helper ran.
    # -------------------------------------------------------------

    display_resource_templates_mock.assert_not_called()
    display_prompts_mock.assert_not_called()
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_display_resource_templates_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when resource-template discovery succeeds
    but its presentation helper fails.

    Expected behavior:

        list_tools()
            ↓
        succeeds
            ↓
        display_tools()
            ↓
        succeeds
            ↓
        list_resources()
            ↓
        succeeds
            ↓
        display_resources()
            ↓
        succeeds
            ↓
        list_resource_templates()
            ↓
        succeeds
            ↓
        display_resource_templates()
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        prompt discovery and presentation do not run
    """

    # -------------------------------------------------------------
    # Arrange: create successful discovery results for all work
    # completed before the failure point.
    # -------------------------------------------------------------

    tools_result = object()
    resources_result = object()
    templates_result = object()

    expected_exception = RuntimeError(
        "resource-template display failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # The first three discovery operations succeed.
    # Prompt discovery must remain unreachable.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        return_value=tools_result
    )

    session.list_resources = AsyncMock(
        return_value=resources_result
    )

    session.list_resource_templates = AsyncMock(
        return_value=templates_result
    )

    session.list_prompts = AsyncMock()

    # -------------------------------------------------------------
    # Arrange: configure display behavior.
    #
    # Tools and resources display successfully.
    # Resource-template presentation fails.
    # Prompt presentation must never run.
    # -------------------------------------------------------------

    display_tools_mock = Mock()
    display_resources_mock = Mock()

    display_resource_templates_mock = Mock(
        side_effect=expected_exception
    )

    display_prompts_mock = Mock()

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: execute discovery and capture the failure.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: the exact original exception propagated.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: all discovery operations before the failure boundary
    # completed exactly once.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()
    session.list_resources.assert_awaited_once_with()
    session.list_resource_templates.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: all earlier successful results were displayed once.
    # -------------------------------------------------------------

    display_tools_mock.assert_called_once_with(
        tools_result
    )

    display_resources_mock.assert_called_once_with(
        resources_result
    )

    # -------------------------------------------------------------
    # Assert 4: the failing helper received the exact template result.
    # -------------------------------------------------------------

    display_resource_templates_mock.assert_called_once_with(
        templates_result
    )

    # -------------------------------------------------------------
    # Assert 5: prompt discovery never began.
    # -------------------------------------------------------------

    session.list_prompts.assert_not_awaited()

    # -------------------------------------------------------------
    # Assert 6: prompt presentation never ran.
    # -------------------------------------------------------------

    display_prompts_mock.assert_not_called()    
    
    
@pytest.mark.anyio
async def test_discover_capabilities_propagates_display_prompts_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Protect failure behavior when prompt discovery succeeds but its
    presentation helper fails.

    Expected behavior:

        list_tools()
            ↓
        succeeds
            ↓
        display_tools()
            ↓
        succeeds
            ↓
        list_resources()
            ↓
        succeeds
            ↓
        display_resources()
            ↓
        succeeds
            ↓
        list_resource_templates()
            ↓
        succeeds
            ↓
        display_resource_templates()
            ↓
        succeeds
            ↓
        list_prompts()
            ↓
        succeeds
            ↓
        display_prompts()
            ↓
        raises the original exception
            ↓
        discover_capabilities() propagates that same exception
            ↓
        normal result tuple is never returned
    """

    # -------------------------------------------------------------
    # Arrange: create one result object for every successful MCP
    # discovery operation.
    # -------------------------------------------------------------

    tools_result = object()
    resources_result = object()
    templates_result = object()
    prompts_result = object()

    # Create one specific exception instance so identity-preserving
    # propagation can be verified.
    expected_exception = RuntimeError(
        "prompt display failed"
    )

    # -------------------------------------------------------------
    # Arrange: create the fake session.
    #
    # Every MCP discovery operation succeeds in this test.
    # -------------------------------------------------------------

    session = Mock()

    session.list_tools = AsyncMock(
        return_value=tools_result
    )

    session.list_resources = AsyncMock(
        return_value=resources_result
    )

    session.list_resource_templates = AsyncMock(
        return_value=templates_result
    )

    session.list_prompts = AsyncMock(
        return_value=prompts_result
    )

    # -------------------------------------------------------------
    # Arrange: configure presentation behavior.
    #
    # The first three display helpers succeed.
    # display_prompts() fails.
    # -------------------------------------------------------------

    display_tools_mock = Mock()
    display_resources_mock = Mock()
    display_resource_templates_mock = Mock()

    display_prompts_mock = Mock(
        side_effect=expected_exception
    )

    monkeypatch.setattr(
        discovery,
        "display_tools",
        display_tools_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resources",
        display_resources_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_resource_templates",
        display_resource_templates_mock,
    )

    monkeypatch.setattr(
        discovery,
        "display_prompts",
        display_prompts_mock,
    )

    # -------------------------------------------------------------
    # Act and assert: execute discovery and capture the presentation
    # failure.
    # -------------------------------------------------------------

    with pytest.raises(RuntimeError) as exception_info:
        await discovery.discover_capabilities(session)

    # -------------------------------------------------------------
    # Assert 1: the exact original exception propagated.
    # -------------------------------------------------------------

    assert exception_info.value is expected_exception

    # -------------------------------------------------------------
    # Assert 2: every MCP discovery operation completed exactly once.
    # -------------------------------------------------------------

    session.list_tools.assert_awaited_once_with()
    session.list_resources.assert_awaited_once_with()
    session.list_resource_templates.assert_awaited_once_with()
    session.list_prompts.assert_awaited_once_with()

    # -------------------------------------------------------------
    # Assert 3: every earlier presentation helper received the exact
    # corresponding result object.
    # -------------------------------------------------------------

    display_tools_mock.assert_called_once_with(
        tools_result
    )

    display_resources_mock.assert_called_once_with(
        resources_result
    )

    display_resource_templates_mock.assert_called_once_with(
        templates_result
    )

    # -------------------------------------------------------------
    # Assert 4: the failing prompt display helper received the exact
    # prompts result.
    # -------------------------------------------------------------

    display_prompts_mock.assert_called_once_with(
        prompts_result
    )    
    
    
    
def test_display_prompts_handles_none_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Protect prompt display behavior when arguments is None.

    MCP prompt metadata may contain no argument collection. The helper
    must display "Arguments: None" and complete normally.
    """

    # Arrange: create one prompt whose arguments field is explicitly None.
    prompts_result = SimpleNamespace(
        prompts=[
            SimpleNamespace(
                name="prompt_without_arguments",
                description="Prompt with no declared arguments.",
                arguments=None,
            ),
        ],
    )

    # Act.
    returned_value = discovery.display_prompts(
        prompts_result
    )

    captured_output = capsys.readouterr().out

    # Assert: identify the correct prompt.
    assert "Name: prompt_without_arguments" in captured_output

    # Protect the current no-arguments message.
    assert "Arguments: None" in captured_output

    # No argument details should be produced.
    assert "Argument count:" not in captured_output

    # The display helper completes normally.
    assert returned_value is None


@pytest.mark.parametrize(
    (
        "display_function_name",
        "discovery_result",
        "expected_context",
    ),
    [
        # ---------------------------------------------------------
        # Tool description is present but empty.
        # ---------------------------------------------------------
        (
            "display_tools",
            SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="empty_description_tool",
                        description="",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                        },
                    ),
                ],
            ),
            "Name: empty_description_tool",
        ),

        # ---------------------------------------------------------
        # Static-resource description is present but empty.
        # ---------------------------------------------------------
        (
            "display_resources",
            SimpleNamespace(
                resources=[
                    SimpleNamespace(
                        uri="example://empty-description-resource",
                        name="Empty Description Resource",
                        description="",
                        mimeType="text/plain",
                    ),
                ],
            ),
            "Name: Empty Description Resource",
        ),

        # ---------------------------------------------------------
        # Resource-template description is present but empty.
        # ---------------------------------------------------------
        (
            "display_resource_templates",
            SimpleNamespace(
                resourceTemplates=[
                    SimpleNamespace(
                        uriTemplate=(
                            "example://empty-description-items/{item_id}"
                        ),
                        name="Empty Description Template",
                        description="",
                        mimeType="application/json",
                    ),
                ],
            ),
            "Name: Empty Description Template",
        ),

        # ---------------------------------------------------------
        # Prompt description is present but empty.
        #
        # arguments=[] keeps this case focused on the prompt's own
        # description.
        # ---------------------------------------------------------
        (
            "display_prompts",
            SimpleNamespace(
                prompts=[
                    SimpleNamespace(
                        name="empty_description_prompt",
                        description="",
                        arguments=[],
                    ),
                ],
            ),
            "Name: empty_description_prompt",
        ),

        # ---------------------------------------------------------
        # Prompt-argument description is present but empty.
        #
        # The prompt description itself is populated so the fallback
        # belongs specifically to the argument.
        # ---------------------------------------------------------
        (
            "display_prompts",
            SimpleNamespace(
                prompts=[
                    SimpleNamespace(
                        name="prompt_with_empty_argument_description",
                        description="Example prompt description.",
                        arguments=[
                            SimpleNamespace(
                                name="empty_description_argument",
                                description="",
                                required=False,
                            ),
                        ],
                    ),
                ],
            ),
            "Name: empty_description_argument",
        ),
    ],
)
def test_display_helper_uses_fallback_for_empty_description(
    display_function_name: str,
    discovery_result: SimpleNamespace,
    expected_context: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Protect readable fallback output for empty descriptions.

    MCP metadata descriptions may be present as empty strings. Each
    applicable display helper must:

    1. Accept description="".
    2. Display "(No description provided)".
    3. Complete normally.
    """

    # Retrieve the display helper named by the current test case.
    display_function = getattr(
        discovery,
        display_function_name,
    )

    # Execute the display helper.
    returned_value = display_function(
        discovery_result
    )

 



 # Capture the helper's terminal output.
    captured_output = capsys.readouterr().out

    # Confirm that this output belongs to the expected metadata item.
    assert expected_context in captured_output

    # Protect the current empty-description fallback.
    assert (
        "Description: (No description provided)"
        in captured_output
    )

    # The helper must complete normally.
    assert returned_value is None
 


