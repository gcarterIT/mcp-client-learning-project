import json

from typing import Any

from mcp import ClientSession

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

