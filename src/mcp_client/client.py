"""
Part 3B: MCP Capability Discovery
=================================

This module builds on the smallest MCP client created in Part 3A.

Part 3A established the basic lifecycle:

1. Start the MCP server.
2. Open an STDIO transport.
3. Create a ClientSession.
4. Initialize the MCP session.
5. Close everything cleanly.

Part 3B adds capability discovery.

The client will ask the MCP server for metadata describing:

- tools
- static resources
- resource templates
- prompts

This module intentionally does NOT:

- invoke tools
- read resources
- expand resource templates
- render prompts

Those operations belong to later milestones.

Why keep everything in one file?
--------------------------------

At this stage, our priority is understanding the protocol operations.

Later, in Part 5, we will separate responsibilities into reusable modules
such as connection.py, discovery.py, and formatters.py. Extracting those
abstractions now would make the first discovery implementation harder to
follow.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, types
from mcp.client.stdio import StdioServerParameters, stdio_client


def get_project_root() -> Path:
    """
    Return the absolute path to the project's root directory.

    File location:

        project_root/
        └── src/
            └── mcp_client/
                └── client.py

    Path(__file__).resolve() gives the absolute path to this file.

    Its parent levels are:

        parents[0] -> mcp_client
        parents[1] -> src
        parents[2] -> project root

    Deriving the path from __file__ makes this client independent of the
    user's current PowerShell directory.
    """

    return Path(__file__).resolve().parents[2]


def format_json(value: Any) -> str:
    """
    Convert a Python value into readable, indented JSON text.

    Tool input schemas are represented as Python dictionaries after the
    MCP SDK parses the server response. JSON indentation makes those
    schemas easier for humans to inspect.

    Parameters
    ----------
    value:
        Any JSON-compatible Python value, such as a dictionary or list.

    Returns
    -------
    str
        An indented JSON string.

    Why use default=str?
    --------------------
    Most MCP metadata is JSON-compatible. If an SDK-specific object appears,
    default=str prevents the diagnostic display from crashing merely because
    a value is not directly serializable.
    """

    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


def display_tools(tools_result: Any) -> None:
    """
    Display tool metadata returned by session.list_tools().

    The MCP SDK returns a result object containing a `tools` collection.
    Each tool normally includes:

    - name
    - description
    - inputSchema

    This function only displays metadata. It does not invoke any tool.
    """

    print("\n" + "=" * 70)
    print("TOOLS")
    print("=" * 70)

    tools = tools_result.tools

    # A valid MCP server may expose zero tools.
    # We therefore handle an empty list instead of assuming tools exist.
    if not tools:
        print("No tools were advertised by the server.")
        return

    print(f"Tool count: {len(tools)}")

    for index, tool in enumerate(tools, start=1):
        print("\n" + "-" * 70)
        print(f"Tool {index}")
        print("-" * 70)

        print(f"Name: {tool.name}")

        # Descriptions are commonly optional.
        # `or "(No description provided)"` gives readable output when None
        # or an empty string is returned.
        print(
            "Description:",
            tool.description or "(No description provided)",
        )

        print("Input schema:")
        print(format_json(tool.inputSchema))


def display_resources(resources_result: Any) -> None:
    """
    Display static resource metadata returned by session.list_resources().

    A resource listing describes what can be read later. It does not contain
    the actual resource contents.

    Common resource metadata includes:

    - URI
    - name
    - description
    - MIME type
    """

    print("\n" + "=" * 70)
    print("STATIC RESOURCES")
    print("=" * 70)

    resources = resources_result.resources

    if not resources:
        print("No static resources were advertised by the server.")
        return

    print(f"Resource count: {len(resources)}")

    for index, resource in enumerate(resources, start=1):
        print("\n" + "-" * 70)
        print(f"Resource {index}")
        print("-" * 70)

        print(f"URI: {resource.uri}")
        print(f"Name: {resource.name}")

        print(
            "Description:",
            resource.description or "(No description provided)",
        )

        print(
            "MIME type:",
            resource.mimeType or "(No MIME type provided)",
        )


def display_resource_templates(templates_result: Any) -> None:
    """
    Display resource-template metadata.

    A static resource has a concrete URI:

        config://application

    A resource template describes a family of possible resource URIs:

        inventory://products/{product_id}

    Listing the template does not substitute a product ID and does not read
    any resource.
    """

    print("\n" + "=" * 70)
    print("RESOURCE TEMPLATES")
    print("=" * 70)

    templates = templates_result.resourceTemplates

    if not templates:
        print("No resource templates were advertised by the server.")
        return

    print(f"Resource template count: {len(templates)}")

    for index, template in enumerate(templates, start=1):
        print("\n" + "-" * 70)
        print(f"Resource Template {index}")
        print("-" * 70)

        print(f"URI template: {template.uriTemplate}")
        print(f"Name: {template.name}")

        print(
            "Description:",
            template.description or "(No description provided)",
        )

        print(
            "MIME type:",
            template.mimeType or "(No MIME type provided)",
        )


def display_prompts(prompts_result: Any) -> None:
    """
    Display prompt metadata returned by session.list_prompts().

    Prompt discovery tells us:

    - the prompt's name
    - its description
    - its expected arguments

    It does not render or retrieve the final prompt messages. That later
    operation uses session.get_prompt().
    """

    print("\n" + "=" * 70)
    print("PROMPTS")
    print("=" * 70)

    prompts = prompts_result.prompts

    if not prompts:
        print("No prompts were advertised by the server.")
        return

    print(f"Prompt count: {len(prompts)}")

    for index, prompt in enumerate(prompts, start=1):
        print("\n" + "-" * 70)
        print(f"Prompt {index}")
        print("-" * 70)

        print(f"Name: {prompt.name}")

        print(
            "Description:",
            prompt.description or "(No description provided)",
        )

        # A prompt may accept no arguments.
        if not prompt.arguments:
            print("Arguments: None")
            continue

        print(f"Argument count: {len(prompt.arguments)}")

        for argument_index, argument in enumerate(
            prompt.arguments,
            start=1,
        ):
            print(f"\n  Argument {argument_index}")
            print(f"  Name: {argument.name}")

            print(
                "  Description:",
                argument.description or "(No description provided)",
            )

            # MCP prompt arguments typically use a required Boolean.
            print(f"  Required: {argument.required}")


def find_tool(tools_result: Any, tool_name: str) -> Any | None:
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


def get_structured_tool_content(tool_result: Any) -> Any | None:
    """
    Return structured content from a CallToolResult when available.

    SDK compatibility note
    ----------------------
    Different SDK releases or serialization models may expose structured
    content using a Pythonic snake_case attribute or a protocol-style
    camelCase alias.

    We first check:

        structured_content

    and then fall back to:

        structuredContent

    This small compatibility helper prevents the display code from failing
    simply because the installed SDK exposes one form rather than the other.
    """

    structured_content = getattr(
        tool_result,
        "structured_content",
        None,
    )

    if structured_content is not None:
        return structured_content

    return getattr(
        tool_result,
        "structuredContent",
        None,
    )


def display_tool_result(tool_result: Any) -> None:
    """
    Display the major sections of an MCP CallToolResult.

    A tool result may contain:

    1. An isError indicator.
    2. A list of unstructured content blocks.
    3. Optional structured content.

    Unstructured content
    --------------------
    The `content` collection may contain TextContent or other MCP content
    types.

    Structured content
    ------------------
    Some tools return a JSON-compatible dictionary or object that clients
    can process without parsing human-readable text.

    This function displays both forms without assuming that either one must
    always be present.
    """

    print("\n" + "=" * 70)
    print("TOOL INVOCATION RESULT")
    print("=" * 70)

    # MCP tool results can report an application-level failure using isError.
    #
    # getattr() provides a safe default for SDK versions where the field may
    # not be populated explicitly.
    is_error = getattr(tool_result, "isError", False)

    print(f"Tool reported an error: {is_error}")

    print("\nContent blocks:")

    content_blocks = getattr(tool_result, "content", None)

    if not content_blocks:
        print("  No unstructured content was returned.")
    else:
        for index, content_block in enumerate(
            content_blocks,
            start=1,
        ):
            print(f"\n  Content block {index}")
            print(f"  Python type: {type(content_block).__name__}")

            # TextContent is the most common form for simple deterministic
            # tools. It contains a human-readable `text` field.
            if isinstance(content_block, types.TextContent):
                print(f"  Text: {content_block.text}")
            else:
                # model_dump() is useful for Pydantic-based MCP objects.
                # If it is unavailable, str() still gives us diagnostic text.
                if hasattr(content_block, "model_dump"):
                    print(
                        format_json(
                            content_block.model_dump(
                                by_alias=True,
                            )
                        )
                    )
                else:
                    print(f"  Value: {content_block}")

    structured_content = get_structured_tool_content(tool_result)

    print("\nStructured content:")

    if structured_content is None:
        print("  No structured content was returned.")
    else:
        print(format_json(structured_content))


def collect_result_text(tool_result: Any) -> str:
    """
    Combine all TextContent blocks into one searchable string.

    This helper is used only for deterministic verification.

    For a production client, we would normally rely on structured content
    when the tool defines an output schema. Text verification is included
    here because a simple FastMCP tool may return its value as TextContent.
    """

    text_values: list[str] = []

    for content_block in getattr(tool_result, "content", []) or []:
        if isinstance(content_block, types.TextContent):
            text_values.append(content_block.text)

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
    structured content. Part 3C remains compatible with the simple result
    representation produced by our demo server.
    """

    if getattr(tool_result, "isError", False):
        return False

    structured_content = get_structured_tool_content(tool_result)

    if structured_content is not None:
        if value_appears_in_structure(
            structured_content,
            expected_number,
        ):
            return True

    result_text = collect_result_text(tool_result)

    # Check common integer and floating-point representations.
    #
    # For expected_number == 42, these include:
    #
    #     "42"
    #     "42.0"
    #
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

    This function implements the complete Part 3C workflow:

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
    Part 3B already requested the tool list.

    Passing that result here avoids making a second unnecessary tools/list
    request. This is a small example of reusing already-retrieved protocol
    data.
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
            f"The server did not advertise the required tool: {tool_name}"
        )

    print("Tool found.")
    print(f"Description: {tool.description}")
    print("Advertised input schema:")
    print(format_json(tool.inputSchema))

    # ---------------------------------------------------------
    # Define deterministic test inputs.
    #
    # These values are intentionally hard-coded for the first
    # invocation so the expected result is known in advance.
    # ---------------------------------------------------------

    arguments = {
        "a": 20,
        "b": 22,
    }

    expected_result = 42

    print("\nInvocation request:")
    print(f"Tool name: {tool_name}")
    print("Arguments:")
    print(format_json(arguments))
    print(f"Expected result: {expected_result}")

    # ---------------------------------------------------------
    # Perform the actual MCP tool invocation.
    #
    # This sends a tools/call request through the existing MCP
    # ClientSession. The server receives the tool name and
    # argument object, executes its registered implementation,
    # and returns a CallToolResult.
    # ---------------------------------------------------------

    tool_result = await session.call_tool(
        tool_name,
        arguments=arguments,
    )

    display_tool_result(tool_result)

    # ---------------------------------------------------------
    # Verify the deterministic result.
    #
    # Raising AssertionError causes the command to fail visibly
    # when the result is not what this test expects.
    # ---------------------------------------------------------

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

def find_resource(
    resources_result: Any,
    resource_uri: str,
) -> Any | None:
    """
    Find one static resource by its exact URI.

    Parameters
    ----------
    resources_result:
        The ListResourcesResult returned by session.list_resources().

    resource_uri:
        The exact resource URI to locate, such as:

            config://application

    Returns
    -------
    Resource | None
        The matching resource metadata object when found.
        None when the resource was not advertised.

    Why search discovery metadata first?
    ------------------------------------
    We could call read_resource() immediately, but discovery gives us a
    chance to verify that the server advertised the resource and inspect
    its metadata before requesting its contents.

    This produces clearer errors when the client connects to a different
    server or when the resource has been renamed.
    """

    for resource in resources_result.resources:
        # URI objects are often represented by a Pydantic URL type.
        # Converting both values to strings makes the comparison explicit
        # and avoids type-related surprises.
        if str(resource.uri) == resource_uri:
            return resource

    return None


def display_resource_metadata(resource: Any) -> None:
    """
    Display metadata for one discovered resource.

    Resource metadata describes the resource but does not include its body.

    Common fields include:

    - URI
    - name
    - description
    - MIME type
    """

    print("\nDiscovered resource metadata:")
    print(f"URI: {resource.uri}")
    print(f"Name: {resource.name}")

    print(
        "Description:",
        resource.description or "(No description provided)",
    )

    print(
        "Advertised MIME type:",
        resource.mimeType or "(No MIME type provided)",
    )


def get_resource_text(content: Any) -> str | None:
    """
    Extract text from one MCP resource-content object.

    MCP resources may return different content types.

    Text resource content commonly provides:

        content.text

    Binary resource content commonly provides:

        content.blob

    Part 4A reads a JSON configuration resource, so text is expected.

    Returns
    -------
    str | None
        The text value when the content object contains text.
        None when it does not contain text.
    """

    text = getattr(content, "text", None)

    if isinstance(text, str):
        return text

    return None


def get_resource_blob(content: Any) -> str | bytes | None:
    """
    Return binary resource data when available.

    MCP binary resource content is commonly represented through a `blob`
    field. Depending on the SDK and serialization stage, that value may be
    a Base64 string or bytes-like data.

    We do not decode or use binary content in Part 4A. This helper exists so
    the display logic can report binary content accurately rather than
    pretending every resource is text.
    """

    return getattr(content, "blob", None)


def parse_json_resource_text(resource_text: str) -> Any:
    """
    Parse resource text as JSON.

    Parameters
    ----------
    resource_text:
        The textual resource body returned by the MCP server.

    Returns
    -------
    Any
        The corresponding Python object, commonly a dictionary or list.

    Raises
    ------
    ValueError
        Raised with a clearer message when the returned text is not valid
        JSON.

    Why parse the resource?
    -----------------------
    Printing raw JSON proves that text was returned.

    Parsing it proves something stronger:

        the resource is valid JSON that a Python application can use.

    That distinction matters because the resource advertises the MIME type
    application/json.
    """

    try:
        return json.loads(resource_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "The resource advertised JSON content, but the returned "
            "text was not valid JSON."
        ) from error


def display_resource_read_result(
    read_result: Any,
) -> list[str]:
    """
    Display all content entries returned by read_resource().

    Parameters
    ----------
    read_result:
        The ReadResourceResult returned by session.read_resource().

    Returns
    -------
    list[str]
        Every text resource body found in the result.

    Why return the text values?
    ---------------------------
    The function has two responsibilities:

    1. Show the returned resource content for the student.
    2. Collect text values so the verification function can parse and
       validate them.

    A later reusable design may separate display and extraction more
    strictly. For this milestone, keeping the workflow visible is helpful.
    """

    print("\n" + "=" * 70)
    print("RESOURCE READ RESULT")
    print("=" * 70)

    contents = getattr(read_result, "contents", None)

    if not contents:
        print("The server returned no resource content.")
        return []

    print(f"Content item count: {len(contents)}")

    text_values: list[str] = []

    for index, content in enumerate(contents, start=1):
        print("\n" + "-" * 70)
        print(f"Content Item {index}")
        print("-" * 70)

        print(f"Python type: {type(content).__name__}")
        print(f"URI: {getattr(content, 'uri', '(No URI provided)')}")

        mime_type = getattr(content, "mimeType", None)

        print(
            "MIME type:",
            mime_type or "(No MIME type provided)",
        )

        resource_text = get_resource_text(content)

        if resource_text is not None:
            text_values.append(resource_text)

            print("Content type: Text")
            print("Raw text:")
            print(resource_text)

            # If the item advertises JSON, also display the parsed,
            # indented representation.
            if mime_type == "application/json":
                parsed_value = parse_json_resource_text(resource_text)

                print("\nParsed JSON:")
                print(format_json(parsed_value))

            continue

        resource_blob = get_resource_blob(content)

        if resource_blob is not None:
            print("Content type: Binary")
            print(
                "Binary content was returned. "
                "Part 4A does not decode binary resources."
            )
            continue

        # This protects the display code against future content types that
        # do not expose either text or blob in the expected form.
        print("Content type: Unknown")

        if hasattr(content, "model_dump"):
            print(
                format_json(
                    content.model_dump(by_alias=True)
                )
            )
        else:
            print(content)

    return text_values


def verify_application_configuration(
    read_result: Any,
    expected_uri: str,
) -> dict[str, Any]:
    """
    Verify the config://application resource result.

    Verification performed
    ----------------------
    1. At least one content item exists.
    2. A returned content item uses the expected URI.
    3. That item has MIME type application/json.
    4. The item contains text.
    5. The text is valid JSON.
    6. The parsed JSON is a nonempty dictionary.

    Returns
    -------
    dict[str, Any]
        The parsed application configuration.

    Why not verify specific setting names?
    --------------------------------------
    The exact fields in application_config.json belong to the server's
    current data design.

    Part 4A should verify the MCP resource contract without coupling the
    client to configuration fields that may legitimately change later.

    Once a stable application configuration schema is formally defined, a
    stronger validation model could verify required fields and data types.
    """

    contents = getattr(read_result, "contents", None)

    if not contents:
        raise AssertionError(
            "The server returned no contents for the application "
            "configuration resource."
        )

    matching_content = None

    for content in contents:
        if str(getattr(content, "uri", "")) == expected_uri:
            matching_content = content
            break

    if matching_content is None:
        raise AssertionError(
            "The resource response did not contain the expected URI: "
            f"{expected_uri}"
        )

    mime_type = getattr(matching_content, "mimeType", None)

    if mime_type != "application/json":
        raise AssertionError(
            "Expected MIME type application/json, but received: "
            f"{mime_type!r}"
        )

    resource_text = get_resource_text(matching_content)

    if resource_text is None:
        raise AssertionError(
            "The application configuration resource did not return "
            "text content."
        )

    parsed_configuration = parse_json_resource_text(resource_text)

    if not isinstance(parsed_configuration, dict):
        raise AssertionError(
            "Expected the application configuration JSON to contain "
            "an object."
        )

    if not parsed_configuration:
        raise AssertionError(
            "The application configuration JSON object was empty."
        )

    return parsed_configuration


async def read_application_configuration(
    session: ClientSession,
    resources_result: Any,
) -> None:
    """
    Locate, read, display, and verify config://application.

    This function coordinates the complete Part 4A workflow:

        search discovered resources
            ↓
        inspect resource metadata
            ↓
        request the resource
            ↓
        display returned content
            ↓
        parse JSON
            ↓
        verify resource contract

    Parameters
    ----------
    session:
        An initialized MCP ClientSession.

    resources_result:
        The ListResourcesResult already obtained during capability
        discovery.
    """

    resource_uri = "config://application"

    print("\n" + "=" * 70)
    print("FIRST STATIC RESOURCE READ")
    print("=" * 70)

    print(f"Looking for resource: {resource_uri}")

    resource = find_resource(
        resources_result=resources_result,
        resource_uri=resource_uri,
    )

    if resource is None:
        raise RuntimeError(
            "The server did not advertise the required resource: "
            f"{resource_uri}"
        )

    print("Resource found.")

    display_resource_metadata(resource)

    # ---------------------------------------------------------
    # Perform the actual MCP resource request.
    #
    # The URI is an MCP resource identifier. It is not a local
    # Windows path and is not opened directly by the client.
    #
    # The server decides how this URI maps to underlying data.
    # ---------------------------------------------------------

    print("\nReading resource...")

    read_result = await session.read_resource(resource_uri)

    print("Resource returned successfully.")

    # Display all returned content entries.
    display_resource_read_result(read_result)

    # Perform deterministic validation.
    parsed_configuration = verify_application_configuration(
        read_result=read_result,
        expected_uri=resource_uri,
    )

    print("\nVerification: PASSED")
    print(f"Confirmed resource URI: {resource_uri}")
    print("Confirmed MIME type: application/json")
    print("Confirmed resource contains valid, nonempty JSON.")
    print(
        "Top-level configuration keys:",
        ", ".join(parsed_configuration.keys()),
    )




async def discover_capabilities(
    session: ClientSession,
) -> tuple[Any, Any]:
    """
    Ask the connected MCP server to advertise its capabilities.

    Returns
    -------
    tuple[Any, Any]
        A two-item tuple containing:

        1. tools_result
        2. resources_result

    Why return both results?
    ------------------------
    Part 3C needs tools_result so it can locate add_numbers.

    Part 4A needs resources_result so it can locate
    config://application.

    Returning the existing discovery results prevents the client from
    sending unnecessary duplicate tools/list and resources/list requests.

    Future improvement
    ------------------
    In Part 5, we may create a dedicated capability model instead of
    returning a tuple. For now, the tuple keeps the implementation simple
    and visible.
    """

    print("\nDiscovering tools...")
    tools_result = await session.list_tools()
    display_tools(tools_result)

    print("\nDiscovering static resources...")
    resources_result = await session.list_resources()
    display_resources(resources_result)

    print("\nDiscovering resource templates...")
    templates_result = await session.list_resource_templates()
    display_resource_templates(templates_result)

    print("\nDiscovering prompts...")
    prompts_result = await session.list_prompts()
    display_prompts(prompts_result)

    return tools_result, resources_result

  

async def main() -> None:
    """
    Run the Part 3B MCP client lifecycle.

    Lifecycle:

        determine project root
            ↓
        verify server module exists
            ↓
        configure child-process environment
            ↓
        launch MCP server
            ↓
        initialize MCP session
            ↓
        discover capabilities
            ↓
        close session and subprocess
    """

    # ---------------------------------------------------------
    # Locate and validate the existing demo server.
    # ---------------------------------------------------------

    project_root = get_project_root()
    server_path = project_root / "servers" / "demo_server.py"

    if not server_path.is_file():
        raise FileNotFoundError(
            "The MCP demo server could not be found.\n"
            f"Expected location: {server_path}"
        )

    # ---------------------------------------------------------
    # Create the environment inherited by the server process.
    #
    # Adding the project root to PYTHONPATH allows the server to
    # resolve package imports such as:
    #
    #     from servers.demo_logic import ...
    #
    # We preserve the user's existing environment variables by
    # starting with os.environ.copy().
    # ---------------------------------------------------------

    server_environment = os.environ.copy()

    existing_pythonpath = server_environment.get("PYTHONPATH")

    if existing_pythonpath:
        server_environment["PYTHONPATH"] = (
            f"{project_root}{os.pathsep}{existing_pythonpath}"
        )
    else:
        server_environment["PYTHONPATH"] = str(project_root)

    # ---------------------------------------------------------
    # Configure the server to launch as a Python module.
    #
    # Equivalent command:
    #
    #     python -m servers.demo_server
    #
    # sys.executable ensures the server uses the same virtual
    # environment as the client.
    # ---------------------------------------------------------

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "servers.demo_server"],
        env=server_environment,
    )

    # ---------------------------------------------------------
    # Print deterministic startup diagnostics.
    # ---------------------------------------------------------

    print("=" * 70)
    print("PART 4A — STATIC MCP RESOURCE")
    print("=" * 70)
    print(f"Python interpreter: {sys.executable}")
    print(f"Project root:       {project_root}")
    print("Server module:      servers.demo_server")

    print("\nStarting MCP server...")

    # ---------------------------------------------------------
    # Launch the server and obtain STDIO streams.
    # ---------------------------------------------------------

    async with stdio_client(server_parameters) as (
        read_stream,
        write_stream,
    ):
        print("Server subprocess created.")

        # -----------------------------------------------------
        # Create one MCP protocol session over those streams.
        # -----------------------------------------------------

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            print("Initializing MCP session...")

            initialization_result = await session.initialize()

            print("MCP session initialized successfully.")
            print(
                "Negotiated protocol version:",
                initialization_result.protocolVersion,
            )
            print(
                "Connected server:",
                initialization_result.serverInfo.name,
            )

            # -------------------------------------------------
            # Part 3B begins here.
            #
            # We now query the initialized server for metadata
            # describing its available capabilities.
            # -------------------------------------------------
            
            # -------------------------------------------------
            # Discover the server's advertised capabilities.
            #
            # Part 3C needs the tool result.
            # Part 4A needs the resource result.
            # -------------------------------------------------

            tools_result, resources_result = await discover_capabilities(
                session
            )

            # -------------------------------------------------
            # Part 3C:
            # Invoke and verify one deterministic tool.
            # -------------------------------------------------

            await invoke_add_numbers(
                session=session,
                tools_result=tools_result,
            )

            # -------------------------------------------------
            # Part 4A:
            # Read and verify one static JSON resource.
            # -------------------------------------------------

            await read_application_configuration(
                session=session,
                resources_result=resources_result,
            )
            

    print("\nConnection closed cleanly.")
    print("Part 4A static resource read completed.")


if __name__ == "__main__":
    """
    Create an asyncio event loop, run main(), and close the loop after
    the asynchronous MCP workflow completes.
    """

    asyncio.run(main())