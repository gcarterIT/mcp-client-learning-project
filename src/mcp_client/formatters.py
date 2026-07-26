import json
from mcp import types
from typing import Any

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


