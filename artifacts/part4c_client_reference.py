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

def get_mime_type(value: Any) -> str | None:
    """
    Return an MCP object's MIME type.

    MCP protocol data uses the JSON name `mimeType`.

    Depending on the SDK model and version, Python may expose that field
    as either:

        value.mimeType

    or:

        value.mime_type

    Supporting both forms makes the tutorial client easier to debug across
    compatible MCP SDK versions.
    """

    mime_type = getattr(value, "mimeType", None)

    if mime_type is None:
        mime_type = getattr(value, "mime_type", None)

    if mime_type is None:
        return None

    return str(mime_type)


def get_uri_template(template: Any) -> str | None:
    """
    Return the URI pattern stored in an MCP resource-template object.

    The protocol field is `uriTemplate`, while some Python models may expose
    the corresponding attribute as `uri_template`.
    """

    uri_template = getattr(template, "uriTemplate", None)

    if uri_template is None:
        uri_template = getattr(template, "uri_template", None)

    if uri_template is None:
        return None

    return str(uri_template)

def find_resource_template(
    templates_result: Any,
    expected_uri_template: str,
) -> Any | None:
    """
    Find one advertised resource template by its exact URI pattern.

    Parameters
    ----------
    templates_result:
        The result returned by session.list_resource_templates().

    expected_uri_template:
        The URI pattern to locate, such as:

            inventory://products/{product_id}

    Returns
    -------
    Any | None
        The matching template metadata object, or None when no matching
        template was advertised.
    """

    templates = getattr(
        templates_result,
        "resourceTemplates",
        None,
    )

    # Some SDK models may expose the Python-friendly field name.
    if templates is None:
        templates = getattr(
            templates_result,
            "resource_templates",
            None,
        )

    if templates is None:
        templates = []

    for template in templates:
        actual_uri_template = get_uri_template(template)

        if actual_uri_template == expected_uri_template:
            return template

    return None

def display_resource_template_metadata(
    template: Any,
) -> None:
    """
    Display metadata for one discovered resource template.

    This metadata describes how concrete resource URIs can be constructed.
    It does not contain the product data itself.
    """

    print("\nDiscovered resource-template metadata:")

    print(
        "URI template:",
        get_uri_template(template)
        or "(No URI template provided)",
    )

    print(
        "Name:",
        getattr(template, "name", None)
        or "(No name provided)",
    )

    print(
        "Description:",
        getattr(template, "description", None)
        or "(No description provided)",
    )

    print(
        "Advertised MIME type:",
        get_mime_type(template)
        or "(No MIME type provided)",
    )


def expand_product_resource_template(
    uri_template: str,
    product_id: str,
) -> str:
    """
    Replace the {product_id} placeholder with a concrete product ID.

    Parameters
    ----------
    uri_template:
        The discovered resource URI pattern.

    product_id:
        The concrete product identifier to insert.

    Returns
    -------
    str
        A completed resource URI, such as:

            inventory://products/P100

    Raises
    ------
    ValueError
        When the required placeholder is missing, the product ID is invalid,
        or unresolved placeholders remain after expansion.
    """

    placeholder = "{product_id}"

    if placeholder not in uri_template:
        raise ValueError(
            "The resource template does not contain the required "
            f"placeholder: {placeholder}"
        )

    if not isinstance(product_id, str):
        raise ValueError(
            "The product ID must be a string."
        )

    product_id = product_id.strip()

    if not product_id:
        raise ValueError(
            "The product ID cannot be empty."
        )

    # Prevent a supplied product ID from modifying the URI structure.
    if "/" in product_id or "\\" in product_id:
        raise ValueError(
            "The product ID cannot contain slash characters."
        )

    concrete_uri = uri_template.replace(
        placeholder,
        product_id,
    )

    # A completed URI should not retain any template braces.
    if "{" in concrete_uri or "}" in concrete_uri:
        raise ValueError(
            "The expanded URI still contains an unresolved placeholder: "
            f"{concrete_uri}"
        )

    return concrete_uri

async def read_json_resource(
    session: ClientSession,
    resource_uri: str,
) -> tuple[Any, dict[str, Any] | list[Any]]:
    """
    Read one MCP resource and parse its JSON text.

    Verification performed
    ----------------------
    1. Resource content was returned.
    2. A content entry matches the requested URI.
    3. Its MIME type is application/json.
    4. Text content exists.
    5. The text contains valid JSON.

    Returns
    -------
    tuple[Any, dict[str, Any] | list[Any]]
        1. The complete ReadResourceResult
        2. The parsed JSON value
    """

    print(f"\nReading resource: {resource_uri}")

    read_result = await session.read_resource(
        resource_uri
    )

    print("Resource returned successfully.")

    # Keep the detailed Part 4A-style display.
    display_resource_read_result(read_result)

    contents = getattr(
        read_result,
        "contents",
        None,
    )

    if not contents:
        raise AssertionError(
            f"The server returned no content for {resource_uri}."
        )

    matching_content = None

    for content in contents:
        returned_uri = str(
            getattr(content, "uri", "")
        )

        if returned_uri == resource_uri:
            matching_content = content
            break

    if matching_content is None:
        raise AssertionError(
            "The response did not contain the requested resource URI: "
            f"{resource_uri}"
        )

    mime_type = get_mime_type(matching_content)

    if mime_type != "application/json":
        raise AssertionError(
            "Expected MIME type application/json for "
            f"{resource_uri}, but received {mime_type!r}."
        )

    resource_text = get_resource_text(
        matching_content
    )

    if resource_text is None:
        raise AssertionError(
            f"The resource {resource_uri} did not return text content."
        )

    parsed_value = parse_json_resource_text(
        resource_text
    )

    if not isinstance(
        parsed_value,
        (dict, list),
    ):
        raise AssertionError(
            "Expected the JSON resource to contain an object or list, "
            f"but received {type(parsed_value).__name__}."
        )

    return read_result, parsed_value


def extract_products_from_inventory(
    inventory_data: Any,
) -> list[dict[str, Any]]:
    """
    Extract product dictionaries from the inventory JSON resource.

    Supported shapes
    ----------------

    Shape A:

        [
            {"product_id": "P100"},
            {"product_id": "P101"}
        ]

    Shape B:

        {
            "products": [
                {"product_id": "P100"},
                {"product_id": "P101"}
            ]
        }

    Returns
    -------
    list[dict[str, Any]]
        The product records found in the inventory resource.
    """

    products: Any

    if isinstance(inventory_data, list):
        products = inventory_data

    elif isinstance(inventory_data, dict):
        products = inventory_data.get("products")

    else:
        raise AssertionError(
            "The inventory resource must contain either a JSON list "
            "or a JSON object with a 'products' list."
        )

    if not isinstance(products, list):
        raise AssertionError(
            "The inventory JSON does not contain a product list."
        )

    validated_products: list[dict[str, Any]] = []

    for index, product in enumerate(
        products,
        start=1,
    ):
        if not isinstance(product, dict):
            raise AssertionError(
                f"Inventory item {index} is not a JSON object."
            )

        validated_products.append(product)

    if not validated_products:
        raise AssertionError(
            "The inventory product list is empty."
        )

    return validated_products


def select_product_ids(
    products: list[dict[str, Any]],
    count: int = 2,
) -> list[str]:
    """
    Select distinct valid product IDs from inventory data.

    Part 4B uses the inventory resource as the source of truth rather than
    guessing whether IDs such as P101 exist.
    """

    product_ids: list[str] = []

    for product in products:
        product_id = product.get("product_id")

        if not isinstance(product_id, str):
            continue

        product_id = product_id.strip()

        if not product_id:
            continue

        if product_id not in product_ids:
            product_ids.append(product_id)

        if len(product_ids) == count:
            break

    if len(product_ids) < count:
        raise AssertionError(
            f"Part 4B requires at least {count} distinct product IDs, "
            f"but only found {len(product_ids)}."
        )

    return product_ids



def verify_product_resource(
    product_data: Any,
    expected_product_id: str,
) -> dict[str, Any]:
    """
    Verify a product returned through the resource template.

    Validation includes:

    - JSON value is an object
    - required fields are present
    - product_id matches the requested ID
    - string fields contain strings
    - price is numeric
    - quantity is an integer
    - price and quantity are not negative
    """

    if not isinstance(product_data, dict):
        raise AssertionError(
            "The product resource must contain a JSON object."
        )

    required_fields = {
        "product_id",
        "name",
        "description",
        "category",
        "price",
        "quantity",
    }

    missing_fields = required_fields.difference(
        product_data.keys()
    )

    if missing_fields:
        missing_text = ", ".join(
            sorted(missing_fields)
        )

        raise AssertionError(
            "The product resource is missing required fields: "
            f"{missing_text}"
        )

    actual_product_id = product_data["product_id"]

    if actual_product_id != expected_product_id:
        raise AssertionError(
            "The returned product ID does not match the requested ID. "
            f"Requested {expected_product_id!r}; "
            f"received {actual_product_id!r}."
        )

    string_fields = (
        "product_id",
        "name",
        "description",
        "category",
    )

    for field_name in string_fields:
        field_value = product_data[field_name]

        if not isinstance(field_value, str):
            raise AssertionError(
                f"Product field {field_name!r} must be a string."
            )

        if not field_value.strip():
            raise AssertionError(
                f"Product field {field_name!r} cannot be empty."
            )

    price = product_data["price"]

    # bool is technically a subclass of int in Python, so explicitly
    # exclude it from numeric validation.
    if isinstance(price, bool) or not isinstance(
        price,
        (int, float),
    ):
        raise AssertionError(
            "Product field 'price' must be numeric."
        )

    if price < 0:
        raise AssertionError(
            "Product field 'price' cannot be negative."
        )

    quantity = product_data["quantity"]

    if isinstance(quantity, bool) or not isinstance(
        quantity,
        int,
    ):
        raise AssertionError(
            "Product field 'quantity' must be an integer."
        )

    if quantity < 0:
        raise AssertionError(
            "Product field 'quantity' cannot be negative."
        )

    return product_data
    
    
async def test_product_resource_template(
    session: ClientSession,
    templates_result: Any,
) -> None:
    """
    Complete the Part 4B resource-template workflow.

    Workflow
    --------
    1. Find the advertised product resource template.
    2. Inspect its metadata.
    3. Read the static inventory list.
    4. Select two valid product IDs from that list.
    5. Expand the template for each ID.
    6. Read each concrete URI.
    7. Verify each returned product.
    8. Confirm the template produced two distinct resources.
    """

    expected_uri_template = (
        "inventory://products/{product_id}"
    )

    print("\n" + "=" * 70)
    print("RESOURCE TEMPLATE TEST")
    print("=" * 70)

    print(
        "Looking for resource template:",
        expected_uri_template,
    )

    template = find_resource_template(
        templates_result=templates_result,
        expected_uri_template=expected_uri_template,
    )

    if template is None:
        raise RuntimeError(
            "The server did not advertise the required resource template: "
            f"{expected_uri_template}"
        )

    print("Resource template found.")

    display_resource_template_metadata(
        template
    )

    discovered_uri_template = get_uri_template(
        template
    )

    if discovered_uri_template is None:
        raise AssertionError(
            "The discovered resource template has no URI pattern."
        )

    if "{product_id}" not in discovered_uri_template:
        raise AssertionError(
            "The discovered product resource template does not contain "
            "the {product_id} placeholder."
        )

    advertised_mime_type = get_mime_type(
        template
    )

    if advertised_mime_type not in (
        None,
        "application/json",
    ):
        raise AssertionError(
            "Expected the product template to advertise application/json, "
            f"but received {advertised_mime_type!r}."
        )

    # ---------------------------------------------------------
    # Obtain valid IDs from the server's own inventory data.
    #
    # This is safer than assuming that P101 or another particular
    # product ID exists.
    # ---------------------------------------------------------

    inventory_uri = "inventory://products"

    print("\nReading the inventory list to obtain valid product IDs.")

    _, inventory_data = await read_json_resource(
        session=session,
        resource_uri=inventory_uri,
    )

    products = extract_products_from_inventory(
        inventory_data
    )

    selected_product_ids = select_product_ids(
        products=products,
        count=2,
    )

    print(
        "\nSelected product IDs:",
        ", ".join(selected_product_ids),
    )

    verified_products: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # Use the same template once for each selected product.
    # ---------------------------------------------------------

    for product_id in selected_product_ids:
        print("\n" + "-" * 70)
        print(f"Testing product resource: {product_id}")
        print("-" * 70)

        concrete_uri = expand_product_resource_template(
            uri_template=discovered_uri_template,
            product_id=product_id,
        )

        print("Template:", discovered_uri_template)
        print("Product ID:", product_id)
        print("Concrete URI:", concrete_uri)

        _, product_data = await read_json_resource(
            session=session,
            resource_uri=concrete_uri,
        )

        verified_product = verify_product_resource(
            product_data=product_data,
            expected_product_id=product_id,
        )

        verified_products.append(
            verified_product
        )

        print("\nProduct verification: PASSED")
        print(
            "Verified product ID:",
            verified_product["product_id"],
        )
        print(
            "Verified product name:",
            verified_product["name"],
        )
        print(
            "Verified price:",
            verified_product["price"],
        )
        print(
            "Verified quantity:",
            verified_product["quantity"],
        )

    returned_ids = [
        product["product_id"]
        for product in verified_products
    ]

    if len(set(returned_ids)) != 2:
        raise AssertionError(
            "The two resource-template reads did not return two distinct "
            "products."
        )

    print("\n" + "=" * 70)
    print("PART 4B VERIFICATION: PASSED")
    print("=" * 70)

    print(
        "Confirmed resource template:",
        discovered_uri_template,
    )

    print(
        "Confirmed concrete resources:",
        ", ".join(
            f"inventory://products/{product_id}"
            for product_id in returned_ids
        ),
    )

    print(
        "Confirmed that the same template returned "
        "two distinct product resources."
    )

    
def verify_product_resource(
    product_data: Any,
    expected_product_id: str,
) -> dict[str, Any]:
    """
    Verify a product returned through the resource template.

    Validation includes:

    - JSON value is an object
    - required fields are present
    - product_id matches the requested ID
    - string fields contain strings
    - price is numeric
    - quantity is an integer
    - price and quantity are not negative
    """

    if not isinstance(product_data, dict):
        raise AssertionError(
            "The product resource must contain a JSON object."
        )

    required_fields = {
        "product_id",
        "name",
        "description",
        "category",
        "price",
        "quantity",
    }

    missing_fields = required_fields.difference(
        product_data.keys()
    )

    if missing_fields:
        missing_text = ", ".join(
            sorted(missing_fields)
        )

        raise AssertionError(
            "The product resource is missing required fields: "
            f"{missing_text}"
        )

    actual_product_id = product_data["product_id"]

    if actual_product_id != expected_product_id:
        raise AssertionError(
            "The returned product ID does not match the requested ID. "
            f"Requested {expected_product_id!r}; "
            f"received {actual_product_id!r}."
        )

    string_fields = (
        "product_id",
        "name",
        "description",
        "category",
    )

    for field_name in string_fields:
        field_value = product_data[field_name]

        if not isinstance(field_value, str):
            raise AssertionError(
                f"Product field {field_name!r} must be a string."
            )

        if not field_value.strip():
            raise AssertionError(
                f"Product field {field_name!r} cannot be empty."
            )

    price = product_data["price"]

    # bool is technically a subclass of int in Python, so explicitly
    # exclude it from numeric validation.
    if isinstance(price, bool) or not isinstance(
        price,
        (int, float),
    ):
        raise AssertionError(
            "Product field 'price' must be numeric."
        )

    if price < 0:
        raise AssertionError(
            "Product field 'price' cannot be negative."
        )

    quantity = product_data["quantity"]

    if isinstance(quantity, bool) or not isinstance(
        quantity,
        int,
    ):
        raise AssertionError(
            "Product field 'quantity' must be an integer."
        )

    if quantity < 0:
        raise AssertionError(
            "Product field 'quantity' cannot be negative."
        )

    return product_data   
    


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

def get_prompt_arguments(
    prompt: Any,
) -> list[Any]:
    """
    Return the argument metadata advertised for one MCP prompt.

    A prompt may accept:

    - no arguments
    - optional arguments
    - required arguments
    - a mixture of required and optional arguments

    MCP SDK prompt metadata normally exposes these through:

        prompt.arguments

    A missing or null arguments field means that the prompt accepts no
    arguments.
    """

    arguments = getattr(
        prompt,
        "arguments",
        None,
    )

    if arguments is None:
        return []

    try:
        return list(arguments)

    except TypeError as exc:
        raise AssertionError(
            "The prompt's argument metadata is not iterable."
        ) from exc

def is_prompt_argument_required(
    argument: Any,
) -> bool:
    """
    Determine whether one prompt argument is required.

    MCP prompt argument metadata normally exposes:

        argument.required

    A missing value is treated as False because MCP argument metadata may
    omit the field for optional arguments.
    """

    return bool(
        getattr(
            argument,
            "required",
            False,
        )
    )

def display_prompt_metadata(
    prompt: Any,
) -> None:
    """
    Display one discovered prompt and its argument definitions.

    This is discovery metadata. It describes how to request the prompt;
    it is not the rendered prompt result.
    """

    prompt_name = getattr(
        prompt,
        "name",
        None,
    )

    description = getattr(
        prompt,
        "description",
        None,
    )

    arguments = get_prompt_arguments(
        prompt
    )

    print("\nDiscovered prompt metadata:")
    print(
        "Name:",
        prompt_name or "(No name provided)",
    )
    print(
        "Description:",
        description or "(No description provided)",
    )

    if not arguments:
        print("Arguments: none")
        return

    print("Arguments:")

    for argument in arguments:
        argument_name = getattr(
            argument,
            "name",
            None,
        )

        argument_description = getattr(
            argument,
            "description",
            None,
        )

        required = is_prompt_argument_required(
            argument
        )

        print(
            f"  - name: {argument_name or '(missing name)'}"
        )
        print(
            "    required:",
            required,
        )
        print(
            "    description:",
            argument_description
            or "(No description provided)",
        )


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


def normalize_prompt_role(
    role: Any,
) -> str:
    """
    Convert an MCP prompt-message role into a readable string.

    Possible SDK representations include:

        "user"
        Role.user
        an enum object exposing .value

    The normalized result is used for display and verification.
    """

    if role is None:
        return ""

    role_value = getattr(
        role,
        "value",
        role,
    )

    return str(role_value).strip().lower()

def get_prompt_content_text(
    content: Any,
) -> str | None:
    """
    Extract text from one MCP prompt content object.

    A text-content object normally exposes:

        content.type == "text"
        content.text

    This helper avoids assuming that every future MCP prompt-content type
    must contain text.
    """

    content_type = getattr(
        content,
        "type",
        None,
    )

    if content_type != "text":
        return None

    text = getattr(
        content,
        "text",
        None,
    )

    if text is None:
        return None

    return str(text)


def display_prompt_result(
    prompt_name: str,
    prompt_result: Any,
) -> None:
    """
    Display the description and messages returned by get_prompt().

    This displays the rendered prompt package. It does not send the
    messages to an AI model.
    """

    description = getattr(
        prompt_result,
        "description",
        None,
    )

    messages = getattr(
        prompt_result,
        "messages",
        None,
    )

    print("\nRendered prompt result:")
    print("Prompt name:", prompt_name)
    print(
        "Description:",
        description or "(No description returned)",
    )

    if not messages:
        print("Messages: none")
        return

    print("Messages:")

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

        content = getattr(
            message,
            "content",
            None,
        )

        text = get_prompt_content_text(
            content
        )

        print(f"\n  Message {index}")
        print(
            "  Role:",
            role or "(No role returned)",
        )
        print(
            "  Content type:",
            getattr(content, "type", None)
            or "(No content type returned)",
        )

        if text is not None:
            print("  Text:")
            print(text)
        else:
            print(
                "  Content:",
                content,
            )

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


async def discover_capabilities(
    session: ClientSession,
) -> tuple[Any, Any, Any, Any]:
    """
    Discover the capabilities advertised by the connected MCP server.

    Returns
    -------
    tuple[Any, Any, Any, Any]
        1. Tool-discovery result
        2. Static-resource discovery result
        3. Resource-template discovery result
        4. Prompt-discovery result

    Each result is returned so later milestone tests can reuse the original
    discovery response instead of asking the server to advertise the same
    capabilities repeatedly.
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

    return (
        tools_result,
        resources_result,
        templates_result,
        prompts_result,
    ) 
  
  
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
    print("PART 4B — MCP RESOURCE TEMPLATES")
    print("PART 4C — MCP PROMPTS")
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

            (
                tools_result,
                resources_result,
                templates_result,
                prompts_result,
            ) = await discover_capabilities(session)

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
            
            # -------------------------------------------------
            # Part 4B:
            # Read and verify resource template.
            # -------------------------------------------------
            
            await test_product_resource_template(
                session=session,
                templates_result=templates_result,
            )

            # -------------------------------------------------
            # Part 4C:
            # Read and verify prompts.
            # -------------------------------------------------
 
            await test_mcp_prompts(
                session=session,
                prompts_result=prompts_result,
            ) 
            
            
            
    print("\nConnection closed cleanly.")
    print("Part 4A static resource read completed.")
    print("Part 4B resource-template testing completed.")
    print("Part 4C MCP prompt testing completed.")
    
if __name__ == "__main__":
    """
    Create an asyncio event loop, run main(), and close the loop after
    the asynchronous MCP workflow completes.
    """

    asyncio.run(main())