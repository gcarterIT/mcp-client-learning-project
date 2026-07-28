"""
Static MCP resource workflow
============================

This module owns the workflow for locating, reading, displaying, and
verifying the demo server's static application-configuration resource.

Responsibilities
----------------
- locate config://application in discovered resource metadata
- read the advertised resource
- display the returned resource content
- verify the resource URI, MIME type, and JSON structure

This module does not own:

- MCP connection management
- capability discovery
- resource-template expansion
- product-resource validation
- prompt workflows
- application startup orchestration
"""

from typing import Any

from mcp import ClientSession

from formatters import (
    display_resource_metadata,
    display_resource_read_result,
    get_resource_text,
)

from validation import (
    parse_json_resource_text,
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
    Discovery allows the client to verify that the server advertised the
    resource before requesting its contents.

    This produces clearer errors when the client connects to a different
    server or when the resource has been renamed.
    """

    for resource in resources_result.resources:
        # MCP URI values may use a Pydantic URL type. Converting both
        # values to strings makes the comparison explicit.
        if str(resource.uri) == resource_uri:
            return resource

    return None


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
    The exact configuration fields belong to the server's data design.

    This workflow verifies the MCP resource contract without coupling the
    client to configuration fields that may legitimately change.
    """

    contents = getattr(
        read_result,
        "contents",
        None,
    )

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

    mime_type = getattr(
        matching_content,
        "mimeType",
        None,
    )

    if mime_type != "application/json":
        raise AssertionError(
            "Expected MIME type application/json, but received: "
            f"{mime_type!r}"
        )

    resource_text = get_resource_text(
        matching_content
    )

    if resource_text is None:
        raise AssertionError(
            "The application configuration resource did not return "
            "text content."
        )

    parsed_configuration = parse_json_resource_text(
        resource_text
    )

    if not isinstance(
        parsed_configuration,
        dict,
    ):
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

    Workflow
    --------
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

    display_resource_metadata(
        resource
    )

    print("\nReading resource...")

    read_result = await session.read_resource(
        resource_uri
    )

    print("Resource returned successfully.")

    display_resource_read_result(
        read_result
    )

    parsed_configuration = (
        verify_application_configuration(
            read_result=read_result,
            expected_uri=resource_uri,
        )
    )

    print("\nVerification: PASSED")
    print(f"Confirmed resource URI: {resource_uri}")
    print("Confirmed MIME type: application/json")
    print("Confirmed resource contains valid, nonempty JSON.")
    print(
        "Top-level configuration keys:",
        ", ".join(
            parsed_configuration.keys()
        ),
    )