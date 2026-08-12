"""
Regression tests for the MCP prompt workflow.

These tests protect the architectural boundary between:

    previously discovered prompt metadata
                +
        active MCP session
                ↓
        prompt workflow
                ↓
        session.get_prompt(...)

The tests intentionally do not create a real MCP connection or start
the demonstration server.
"""

from types import SimpleNamespace

import pytest

from mcp_client.prompt_workflow import (
    retrieve_and_verify_prompt,
)


class FakePromptSession:
    """
    Minimal ClientSession test double for prompt retrieval.

    It intentionally exposes only get_prompt().

    It does NOT expose list_prompts(), because prompt discovery belongs
    to the discovery subsystem rather than the workflow subsystem.
    """

    def __init__(self) -> None:
        self.call_count = 0
        self.called_prompt_name = None
        self.called_arguments = None

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: dict[str, str] | None = None,
    ):
        """
        Record the delegated prompt request and return a valid rendered
        prompt containing all supplied argument values.
        """

        self.call_count += 1
        self.called_prompt_name = prompt_name
        self.called_arguments = arguments

        rendered_text = (
            "Analyze the supplied inventory information.\n\n"
            "Primary focus: stock levels and product availability\n"
            "Discuss no more than 5 products."
        )

        return SimpleNamespace(
            description="Rendered inventory-summary prompt.",
            messages=[
                SimpleNamespace(
                    role="user",
                    content=SimpleNamespace(
                        type="text",
                        text=rendered_text,
                    ),
                ),
            ],
        )


@pytest.mark.asyncio
async def test_retrieve_and_verify_prompt_delegates_expected_prompt_request():
    """
    Protect the successful prompt-workflow delegation boundary.

    Given:
        - previously discovered metadata containing summarize_inventory
        - advertised arguments focus and maximum_items
        - an active session capable of get_prompt()

    Verify that the workflow:

        1. uses the supplied discovery metadata,
        2. constructs deterministic argument values,
        3. calls get_prompt() exactly once,
        4. passes the expected prompt name and arguments,
        5. accepts a rendered result containing those argument values.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    summarize_inventory_prompt = SimpleNamespace(
        name="summarize_inventory",
        description="Create instructions for summarizing inventory data.",
        arguments=[
            SimpleNamespace(
                name="focus",
                description="Summary focus.",
                required=False,
            ),
            SimpleNamespace(
                name="maximum_items",
                description="Maximum number of products.",
                required=False,
            ),
        ],
    )

    prompts_result = SimpleNamespace(
        prompts=[
            summarize_inventory_prompt,
        ],
    )

    session = FakePromptSession()

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    await retrieve_and_verify_prompt(
        session=session,
        prompts_result=prompts_result,
        prompt_name="summarize_inventory",
    )

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------

    assert session.call_count == 1

    assert session.called_prompt_name == "summarize_inventory"

    assert session.called_arguments == {
        "focus": "stock levels and product availability",
        "maximum_items": "5",
    }
    
@pytest.mark.asyncio
async def test_retrieve_and_verify_prompt_does_not_get_when_required_prompt_missing():
    """
    Protect the missing-required-prompt workflow contract.

    Given discovery metadata that does NOT advertise
    summarize_inventory:

        1. retrieve_and_verify_prompt() must raise RuntimeError,
        2. session.get_prompt() must not be invoked.

    This protects the architectural rule that prompt workflows must
    respect previously discovered capability metadata rather than
    blindly requesting an application-specific prompt by name.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------
    #
    # The server advertises some other prompt, but not the one
    # requested by this workflow.
    # ---------------------------------------------------------

    other_prompt = SimpleNamespace(
        name="some_other_prompt",
        description="A different prompt.",
        arguments=[],
    )

    prompts_result = SimpleNamespace(
        prompts=[
            other_prompt,
        ],
    )

    class NoGetPromptSession:
        """
        Minimal session double.

        Any get_prompt() call indicates that the workflow crossed
        the discovery boundary incorrectly.
        """

        def __init__(self) -> None:
            self.call_count = 0

        async def get_prompt(
            self,
            prompt_name: str,
            arguments: dict[str, str] | None = None,
        ):
            self.call_count += 1

            raise AssertionError(
                "get_prompt() should not have been called "
                f"for missing prompt: {prompt_name}"
            )

    session = NoGetPromptSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(
        RuntimeError,
        match="summarize_inventory",
    ):
        await retrieve_and_verify_prompt(
            session=session,
            prompts_result=prompts_result,
            prompt_name="summarize_inventory",
        )

    # ---------------------------------------------------------
    # Architectural assertion
    # ---------------------------------------------------------

    assert session.call_count == 0
    
@pytest.mark.asyncio
async def test_retrieve_and_verify_prompt_rejects_missing_rendered_argument():
    """
    Protect the prompt argument-rendering contract.

    Given:
        - summarize_inventory is advertised,
        - the workflow supplies deterministic arguments,
        - get_prompt() succeeds,
        - the returned prompt contains one supplied argument value
          but omits another,

    Verify that the workflow rejects the rendered prompt.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    summarize_inventory_prompt = SimpleNamespace(
        name="summarize_inventory",
        description="Create instructions for summarizing inventory data.",
        arguments=[
            SimpleNamespace(
                name="focus",
                description="Summary focus.",
                required=False,
            ),
            SimpleNamespace(
                name="maximum_items",
                description="Maximum number of products.",
                required=False,
            ),
        ],
    )

    prompts_result = SimpleNamespace(
        prompts=[
            summarize_inventory_prompt,
        ],
    )

    class MissingRenderedArgumentSession:
        """
        Minimal session double for the rendering-mismatch path.

        The MCP get_prompt() operation itself succeeds.

        The returned prompt includes the focus value but deliberately
        omits the maximum_items value "5".
        """

        def __init__(self) -> None:
            self.call_count = 0
            self.called_prompt_name = None
            self.called_arguments = None

        async def get_prompt(
            self,
            prompt_name: str,
            arguments: dict[str, str] | None = None,
        ):
            self.call_count += 1
            self.called_prompt_name = prompt_name
            self.called_arguments = arguments

            rendered_text = (
                "Analyze the supplied inventory information.\n\n"
                "Primary focus: stock levels and product availability\n"
                "Discuss the relevant products."
            )

            return SimpleNamespace(
                description="Rendered inventory-summary prompt.",
                messages=[
                    SimpleNamespace(
                        role="user",
                        content=SimpleNamespace(
                            type="text",
                            text=rendered_text,
                        ),
                    ),
                ],
            )

    session = MissingRenderedArgumentSession()

    # ---------------------------------------------------------
    # Act + Assert
    # ---------------------------------------------------------

    with pytest.raises(
        AssertionError,
        match="5",
    ):
        await retrieve_and_verify_prompt(
            session=session,
            prompts_result=prompts_result,
            prompt_name="summarize_inventory",
        )

    # ---------------------------------------------------------
    # Architectural assertions
    # ---------------------------------------------------------
    #
    # These prove that:
    #
    # 1. the prompt was actually requested,
    # 2. the expected arguments were supplied,
    # 3. failure occurred only after the returned rendering
    #    omitted one of those supplied argument values.
    # ---------------------------------------------------------

    assert session.call_count == 1

    assert session.called_prompt_name == "summarize_inventory"

    assert session.called_arguments == {
        "focus": "stock levels and product availability",
        "maximum_items": "5",
    }