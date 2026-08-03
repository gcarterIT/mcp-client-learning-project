"""
MCP prompt workflow
===================

This module owns the complete deterministic prompt workflow used by the
learning client.

Responsibilities
----------------
- inspect discovered prompt metadata
- locate required prompts
- construct deterministic prompt arguments
- request rendered prompts
- display returned prompt messages
- verify roles, text content, and argument substitution
- coordinate the complete Part 4C prompt test

This module does not own:

- MCP connection lifecycle
- capability discovery
- tools
- static resources
- resource templates
- application startup orchestration
"""

from typing import Any

from mcp import ClientSession

from mcp_client.formatters import (
    display_prompt_metadata,
    display_prompt_result,
    get_prompt_content_text,
    is_prompt_argument_required,
    normalize_prompt_role,
)

from mcp_client.validation import (
    get_prompt_arguments,
)

def get_prompts(
    prompts_result: Any,
) -> list[Any]:
    """
    Extract the prompt metadata objects from a ListPromptsResult.

    MCP SDK models normally expose the collection as:

        prompts_result.prompts

    This helper centralizes that access and validates that the returned
    value behaves like a list.

    Parameters
    ----------
    prompts_result:
        The value returned by session.list_prompts().

    Returns
    -------
    list[Any]
        The discovered prompt metadata objects.

    Raises
    ------
    AssertionError
        If the response does not expose a usable prompt collection.
    """

    prompts = getattr(
        prompts_result,
        "prompts",
        None,
    )

    if prompts is None:
        raise AssertionError(
            "The prompt-discovery result does not contain a "
            "'prompts' collection."
        )

    # The MCP SDK normally returns a Python list. Converting with list()
    # also supports other iterable collection implementations.
    try:
        return list(prompts)

    except TypeError as exc:
        raise AssertionError(
            "The discovered prompt collection is not iterable."
        ) from exc

def find_prompt(
    prompts_result: Any,
    expected_name: str,
) -> Any | None:
    """
    Find one prompt by its exact advertised name.

    Prompt names are treated as exact identifiers. The comparison is
    therefore case-sensitive.

    Parameters
    ----------
    prompts_result:
        The result returned by session.list_prompts().

    expected_name:
        The exact prompt name to locate.

    Returns
    -------
    Any | None
        The matching prompt metadata object, or None when the prompt was
        not advertised.
    """

    for prompt in get_prompts(prompts_result):
        actual_name = getattr(
            prompt,
            "name",
            None,
        )

        if actual_name == expected_name:
            return prompt

    return None


def choose_prompt_argument_value(
    prompt_name: str,
    argument_name: str,
) -> str:
    """
    Choose a deterministic test value for one prompt argument.

    The function uses common semantic argument names to produce readable
    values. Unknown argument names still receive a stable fallback value.

    This is tutorial test data. It is not business logic and it does not
    call an AI model.
    """

    normalized_name = argument_name.strip().lower()

    # ---------------------------------------------------------
    # Inventory-related argument names
    # ---------------------------------------------------------

    if normalized_name in {
        "category",
        "product_category",
    }:
        return "computer-accessories"

    if normalized_name in {
        "product_id",
        "product",
    }:
        return "P100"

    if normalized_name in {
        "focus",
        "summary_focus",
    }:
        return "stock levels and product availability"

    if normalized_name in {
        "audience",
        "target_audience",
    }:
        return "new inventory employees"

    if normalized_name in {
        "detail_level",
        "level",
    }:
        return "concise"

    # ---------------------------------------------------------
    # Customer-request argument names
    # ---------------------------------------------------------

    if normalized_name in {
        "request",
        "customer_request",
        "message",
        "customer_message",
        "query",
        "text",
    }:
        return (
            "I need a compact mechanical keyboard and want to know "
            "whether it is currently in stock."
        )

    if normalized_name in {
        "customer_name",
        "name",
    }:
        return "Taylor"

    if normalized_name in {
        "tone",
        "response_tone",
    }:
        return "professional and helpful"

    if normalized_name in {
        "priority",
        "urgency",
    }:
        return "normal"

    # ---------------------------------------------------------
    # Integer-like prompt arguments
    # ---------------------------------------------------------
    #
    # MCP prompt arguments are transmitted as strings, but the
    # server may validate and convert them to typed Python values.
    #
    # For example, the server expects maximum_items to be an int.
    # Sending "5" allows Pydantic to convert the string to integer 5.
    # ---------------------------------------------------------

    if normalized_name in {
        "maximum_items",
        "max_items",
        "item_limit",
        "limit",
        "count",
    }:
        return "5"

    # ---------------------------------------------------------
    # Stable fallback
    # ---------------------------------------------------------
    #
    # We must still supply a value when the server introduces a new
    # required argument that is not covered above.
    # ---------------------------------------------------------

    return f"test value for {prompt_name}.{argument_name}"

def build_prompt_arguments(
    prompt: Any,
    include_optional: bool = True,
) -> dict[str, str]:
    """
    Build the argument dictionary sent to session.get_prompt().

    Parameters
    ----------
    prompt:
        One discovered MCP prompt metadata object.

    include_optional:
        When True, deterministic values are supplied for both required
        and optional arguments.

        When False, only required arguments are supplied.

    Returns
    -------
    dict[str, str]
        Prompt argument names mapped to deterministic string values.

    Raises
    ------
    AssertionError
        If an advertised argument does not have a usable name.
    """

    prompt_name = getattr(
        prompt,
        "name",
        None,
    )

    if not isinstance(prompt_name, str) or not prompt_name.strip():
        raise AssertionError(
            "The selected prompt does not have a usable name."
        )

    prompt_arguments: dict[str, str] = {}

    for argument in get_prompt_arguments(prompt):
        argument_name = getattr(
            argument,
            "name",
            None,
        )

        if (
            not isinstance(argument_name, str)
            or not argument_name.strip()
        ):
            raise AssertionError(
                f"Prompt {prompt_name!r} contains an argument "
                "without a usable name."
            )

        argument_name = argument_name.strip()

        required = is_prompt_argument_required(
            argument
        )

        if required or include_optional:
            prompt_arguments[argument_name] = (
                choose_prompt_argument_value(
                    prompt_name=prompt_name,
                    argument_name=argument_name,
                )
            )

    return prompt_arguments



def verify_prompt_result(
    prompt_name: str,
    prompt_result: Any,
    supplied_arguments: dict[str, str],
) -> list[str]:
    """
    Verify the rendered messages returned by session.get_prompt().

    Verification performed
    ----------------------
    1. At least one message was returned.
    2. Each message has an accepted MCP prompt role.
    3. Each message has content.
    4. At least one text-content object was returned.
    5. Text content is not empty.
    6. Supplied argument values appear in the rendered text.

    Returns
    -------
    list[str]
        All non-empty text strings extracted from the rendered prompt.

    Notes
    -----
    The supplied-value check confirms that prompt arguments affected the
    rendered output. It does not judge the quality of the wording.
    """

    messages = getattr(
        prompt_result,
        "messages",
        None,
    )

    if not messages:
        raise AssertionError(
            f"Prompt {prompt_name!r} returned no messages."
        )

    accepted_roles = {
        "user",
        "assistant",
    }

    rendered_texts: list[str] = []

    for index, message in enumerate(
        messages,
        start=1,
    ):
        role = normalize_prompt_role(
            getattr(
                message,
                "role",
                None,
            )
        )

        if role not in accepted_roles:
            raise AssertionError(
                f"Prompt {prompt_name!r}, message {index}, "
                f"returned unsupported role {role!r}."
            )

        content = getattr(
            message,
            "content",
            None,
        )

        if content is None:
            raise AssertionError(
                f"Prompt {prompt_name!r}, message {index}, "
                "contains no content."
            )

        text = get_prompt_content_text(
            content
        )

        if text is not None:
            if not text.strip():
                raise AssertionError(
                    f"Prompt {prompt_name!r}, message {index}, "
                    "contains empty text."
                )

            rendered_texts.append(
                text
            )

    if not rendered_texts:
        raise AssertionError(
            f"Prompt {prompt_name!r} returned no text messages."
        )

    combined_text = "\n".join(
        rendered_texts
    ).lower()

    # ---------------------------------------------------------
    # Confirm every supplied argument value appears somewhere in
    # the rendered prompt.
    #
    # This establishes that the server used the supplied values
    # rather than merely returning an unrelated static message.
    # ---------------------------------------------------------

    missing_values: list[str] = []

    for argument_name, argument_value in supplied_arguments.items():
        if argument_value.lower() not in combined_text:
            missing_values.append(
                f"{argument_name}={argument_value!r}"
            )

    if missing_values:
        raise AssertionError(
            f"Prompt {prompt_name!r} did not render these supplied "
            "argument values: "
            + ", ".join(missing_values)
        )

    return rendered_texts


async def retrieve_and_verify_prompt(
    session: ClientSession,
    prompts_result: Any,
    prompt_name: str,
) -> None:
    """
    Discover, inspect, retrieve, display, and verify one MCP prompt.

    Workflow
    --------
    1. Confirm the prompt was advertised.
    2. Display its metadata.
    3. Inspect its arguments.
    4. Build deterministic test arguments.
    5. Request the rendered prompt.
    6. Display the returned messages.
    7. Verify roles, content, and argument substitution.
    """

    print("\n" + "-" * 70)
    print(f"TESTING PROMPT: {prompt_name}")
    print("-" * 70)

    prompt = find_prompt(
        prompts_result=prompts_result,
        expected_name=prompt_name,
    )

    if prompt is None:
        raise RuntimeError(
            "The server did not advertise the required prompt: "
            f"{prompt_name}"
        )

    print("Prompt found.")

    display_prompt_metadata(
        prompt
    )

    prompt_arguments = build_prompt_arguments(
        prompt=prompt,
        include_optional=True,
    )

    if prompt_arguments:
        print("\nArguments sent to get_prompt():")

        for argument_name, argument_value in (
            prompt_arguments.items()
        ):
            print(
                f"  {argument_name} = {argument_value!r}"
            )
    else:
        print(
            "\nThe prompt accepts no arguments."
        )

    print("\nRequesting rendered prompt...")

    prompt_result = await session.get_prompt(
        prompt_name,
        arguments=prompt_arguments,
    )

    print("Rendered prompt returned successfully.")

    display_prompt_result(
        prompt_name=prompt_name,
        prompt_result=prompt_result,
    )

    rendered_texts = verify_prompt_result(
        prompt_name=prompt_name,
        prompt_result=prompt_result,
        supplied_arguments=prompt_arguments,
    )

    print("\nPrompt verification: PASSED")
    print(
        "Verified message count:",
        len(
            getattr(
                prompt_result,
                "messages",
                [],
            )
        ),
    )
    print(
        "Verified text-content count:",
        len(rendered_texts),
    )
    print(
        "Confirmed that no AI model was called."
    )


async def test_mcp_prompts(
    session: ClientSession,
    prompts_result: Any,
) -> None:
    """
    Complete the Part 4C prompt milestone.

    The demo server is expected to advertise:

        summarize_inventory
        analyze_customer_request

    Both prompts are retrieved and verified independently.
    """

    expected_prompt_names = [
        "summarize_inventory",
        "analyze_customer_request",
    ]

    print("\n" + "=" * 70)
    print("PART 4C — MCP PROMPT TESTS")
    print("=" * 70)

    discovered_prompts = get_prompts(
        prompts_result
    )

    if not discovered_prompts:
        raise AssertionError(
            "The server advertised no MCP prompts."
        )

    discovered_names = [
        getattr(prompt, "name", None)
        for prompt in discovered_prompts
    ]

    print(
        "Discovered prompt names:",
        ", ".join(
            str(name)
            for name in discovered_names
            if name is not None
        ),
    )

    for prompt_name in expected_prompt_names:
        await retrieve_and_verify_prompt(
            session=session,
            prompts_result=prompts_result,
            prompt_name=prompt_name,
        )

    print("\n" + "=" * 70)
    print("PART 4C VERIFICATION: PASSED")
    print("=" * 70)

    print(
        "Verified prompts:",
        ", ".join(expected_prompt_names),
    )
    print(
        "Confirmed prompt discovery, argument inspection, "
        "rendering, and message validation."
    )
    print(
        "Confirmed that prompt retrieval did not invoke an LLM."
    )



