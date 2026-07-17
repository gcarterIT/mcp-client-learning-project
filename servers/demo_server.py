"""
demo_server.py

Minimal but fully functional MCP server for the MCP Client Learning Project.

The server exposes:

Tools
-----
1. add_numbers
2. divide_numbers
3. search_inventory
4. update_demo_setting

Static resources
----------------
1. config://application
2. inventory://products
3. settings://current

Resource templates
------------------
1. inventory://products/{product_id}

Prompts
-------
1. summarize_inventory
2. analyze_customer_request

Transport
---------
STDIO

Important STDIO rule
--------------------
Do not use ordinary print() statements while the MCP server is running.

STDOUT is used for MCP JSON-RPC protocol messages. Writing debugging text to
STDOUT can corrupt the protocol stream.

Use logging configured for STDERR instead.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from servers.demo_logic import (
    DEMO_SETTINGS,
    add_numbers_logic,
    divide_numbers_logic,
    get_product_logic,
    load_application_config,
    load_inventory,
    search_inventory_logic,
    update_demo_setting_logic,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# StreamHandler defaults to STDERR, but we explicitly provide sys.stderr to
# make our intention clear.
#
# Never direct these logs to STDOUT when the server uses STDIO transport.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger("mcp-demo-server")


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

# FastMCP handles:
# - MCP protocol messages
# - capability advertisement
# - tool schema generation
# - resource registration
# - prompt registration
# - request routing
# - response serialization
#
# json_response=True encourages JSON-compatible structured output for tools
# that return dictionaries and lists.
mcp = FastMCP(
    name="MCP Inventory Learning Server",
    json_response=True,
)


# ===========================================================================
# TOOLS
# ===========================================================================

@mcp.tool()
def add_numbers(a: float, b: float) -> dict[str, float]:
    """
    Add two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        A structured object containing the inputs and calculated sum.
    """

    logger.info("Executing add_numbers")
    return add_numbers_logic(a=a, b=b)


@mcp.tool()
def divide_numbers(
    numerator: float,
    denominator: float,
) -> dict[str, float]:
    """
    Divide a numerator by a denominator.

    Args:
        numerator: Number to divide.
        denominator: Number by which the numerator will be divided.

    Returns:
        A structured object containing the inputs and quotient.

    Raises:
        ValueError: If denominator is zero.
    """

    logger.info("Executing divide_numbers")

    return divide_numbers_logic(
        numerator=numerator,
        denominator=denominator,
    )


@mcp.tool()
def search_inventory(
    query: str,
    category: str | None = None,
    maximum_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search the demonstration product inventory.

    Args:
        query:
            Case-insensitive search text matched against product ID,
            product name, category, and description.

        category:
            Optional exact category filter. Examples include
            ``computer-accessories`` and ``office-supplies``.

        maximum_results:
            Maximum records to return. Must be between 1 and 50.

    Returns:
        A list of matching product dictionaries.
    """

    logger.info(
        "Executing search_inventory query=%r category=%r maximum_results=%s",
        query,
        category,
        maximum_results,
    )

    return search_inventory_logic(
        query=query,
        category=category,
        maximum_results=maximum_results,
    )


@mcp.tool()
def update_demo_setting(setting_name: str, value: Any) -> dict[str, Any]:
    """
    Update one in-memory demonstration setting.

    This is a mutating tool because it changes server state.

    Args:
        setting_name:
            Supported names are ``display_mode`` and
            ``include_out_of_stock``.

        value:
            New value for the selected setting.

    Returns:
        A structured object describing the previous and new values.

    Notes:
        The change lasts only until the server process stops.
    """

    logger.info(
        "Executing update_demo_setting setting_name=%r value=%r",
        setting_name,
        value,
    )

    return update_demo_setting_logic(
        setting_name=setting_name,
        value=value,
    )


# ===========================================================================
# STATIC RESOURCES
# ===========================================================================

@mcp.resource(
    "config://application",
    name="Application Configuration",
    description="Configuration for the MCP Inventory Learning Server.",
    mime_type="application/json",
)
def get_application_config_resource() -> str:
    """
    Return application configuration as formatted JSON text.

    MCP resources may return text. Even though the underlying information
    represents JSON, serializing it to a string gives the resource explicit
    JSON document content.
    """

    logger.info("Reading resource config://application")

    return json.dumps(
        load_application_config(),
        indent=2,
        sort_keys=True,
    )


@mcp.resource(
    "inventory://products",
    name="Complete Product Inventory",
    description="All products in the demonstration inventory.",
    mime_type="application/json",
)
def get_inventory_resource() -> str:
    """Return the complete demonstration inventory as JSON text."""

    logger.info("Reading resource inventory://products")

    return json.dumps(
        load_inventory(),
        indent=2,
        sort_keys=True,
    )


@mcp.resource(
    "settings://current",
    name="Current Demo Settings",
    description="Current in-memory settings for the demonstration server.",
    mime_type="application/json",
)
def get_current_settings_resource() -> str:
    """Return the server's current in-memory settings."""

    logger.info("Reading resource settings://current")

    return json.dumps(
        DEMO_SETTINGS,
        indent=2,
        sort_keys=True,
    )


# ===========================================================================
# RESOURCE TEMPLATE
# ===========================================================================

@mcp.resource(
    "inventory://products/{product_id}",
    name="Inventory Product",
    description="Retrieve a single inventory product by product ID.",
    mime_type="application/json",
)
def get_product_resource(product_id: str) -> str:
    """
    Return one product as a JSON resource.

    The ``{product_id}`` placeholder makes this a resource template rather
    than a single static resource.

    Examples:
        inventory://products/P100
        inventory://products/P201
    """

    logger.info(
        "Reading resource inventory://products/%s",
        product_id,
    )

    return json.dumps(
        get_product_logic(product_id),
        indent=2,
        sort_keys=True,
    )


# ===========================================================================
# PROMPTS
# ===========================================================================

@mcp.prompt()
def summarize_inventory(
    focus: str = "low-stock products",
    maximum_items: int = 5,
) -> str:
    """
    Create instructions for summarizing inventory data.

    Args:
        focus:
            The aspect of inventory on which the summary should concentrate.

        maximum_items:
            Maximum number of products the summary should discuss.

    Returns:
        Prompt text. Retrieving this prompt does not execute an LLM.
    """

    return (
        "Analyze the supplied inventory information.\n\n"
        f"Primary focus: {focus}\n"
        f"Discuss no more than {maximum_items} products.\n\n"
        "For each relevant product, report:\n"
        "1. Product ID\n"
        "2. Product name\n"
        "3. Quantity\n"
        "4. Price\n"
        "5. Recommended action\n\n"
        "Do not invent products or quantities that are absent from "
        "the supplied inventory."
    )


@mcp.prompt()
def analyze_customer_request(
    customer_request: str,
    response_style: str = "professional",
) -> str:
    """
    Create instructions for analyzing a customer inventory request.

    Args:
        customer_request:
            Original request written by the customer.

        response_style:
            Requested response style, such as professional, concise,
            or friendly.

    Returns:
        A rendered prompt containing the customer's original request.
    """

    return (
        "Analyze the following customer request using only the inventory "
        "information supplied separately.\n\n"
        f"Customer request:\n{customer_request}\n\n"
        f"Response style: {response_style}\n\n"
        "Your response should:\n"
        "1. Identify the requested product or product category.\n"
        "2. State whether a matching inventory item is available.\n"
        "3. Mention the price and quantity when available.\n"
        "4. Clearly distinguish known facts from assumptions.\n"
        "5. Avoid inventing inventory data."
    )


# ===========================================================================
# SERVER ENTRY POINT
# ===========================================================================

def main() -> None:
    """
    Start the MCP server using STDIO transport.

    STDIO means:
    - Requests arrive through standard input.
    - Responses leave through standard output.
    - Diagnostic logs must use standard error.
    """

    logger.info("Starting MCP Inventory Learning Server using STDIO")

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()