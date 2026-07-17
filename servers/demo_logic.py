"""
demo_logic.py

Business logic for the MCP Inventory Learning Server.

This module deliberately contains no MCP-specific code.

Why?
----
Keeping application logic separate from the MCP protocol layer makes the
code easier to:

1. Test
2. Reuse
3. Debug
4. Replace later with a database or external API

The MCP server in demo_server.py will call these functions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------------

# __file__ points to:
#
#     .../servers/demo_logic.py
#
# parent points to:
#
#     .../servers
#
# We build paths relative to the source file instead of relying on the
# terminal's current working directory.
#
# This makes the code more reliable when it is launched by:
# - PowerShell
# - Jupyter
# - MCP Inspector
# - Our future terminal client
# - Our future Streamlit application
SERVER_DIRECTORY = Path(__file__).resolve().parent

DATA_DIRECTORY = SERVER_DIRECTORY / "demo_data"

APPLICATION_CONFIG_FILE = DATA_DIRECTORY / "application_config.json"
INVENTORY_FILE = DATA_DIRECTORY / "inventory.json"


# ---------------------------------------------------------------------------
# Custom application exceptions
# ---------------------------------------------------------------------------

class ProductNotFoundError(ValueError):
    """Raised when an inventory product ID cannot be found."""


class InvalidSettingError(ValueError):
    """Raised when an unsupported demo setting is supplied."""


# ---------------------------------------------------------------------------
# In-memory demonstration state
# ---------------------------------------------------------------------------

# This dictionary represents state that can change while the server process
# is running.
#
# Important:
# This state is NOT persistent. When the server process stops, these values
# return to their defaults.
#
# We intentionally use in-memory state now because persistence is not the
# learning objective of Part 2.
DEMO_SETTINGS: dict[str, Any] = {
    "display_mode": "compact",
    "include_out_of_stock": True,
}


# Only these settings may be changed through the update tool.
ALLOWED_SETTING_VALUES: dict[str, set[Any]] = {
    "display_mode": {"compact", "detailed"},
    "include_out_of_stock": {True, False},
}


# ---------------------------------------------------------------------------
# JSON file helpers
# ---------------------------------------------------------------------------

def _read_json_file(file_path: Path) -> Any:
    """
    Read and decode a UTF-8 JSON file.

    Parameters
    ----------
    file_path:
        Absolute or relative path to the JSON file.

    Returns
    -------
    Any
        The Python object decoded from the JSON document.

    Raises
    ------
    FileNotFoundError
        If the requested file does not exist.

    json.JSONDecodeError
        If the file contains invalid JSON.
    """

    # Using an explicit UTF-8 encoding avoids platform-dependent behavior.
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_application_config() -> dict[str, Any]:
    """
    Load the application configuration.

    The return type says that the result must be a dictionary whose keys
    are strings. Values may contain different JSON-compatible types.
    """

    config = _read_json_file(APPLICATION_CONFIG_FILE)

    if not isinstance(config, dict):
        raise TypeError("Application configuration must be a JSON object.")

    return config


def load_inventory() -> list[dict[str, Any]]:
    """
    Load all inventory records.

    Returns
    -------
    list[dict[str, Any]]
        A list containing one dictionary per product.
    """

    inventory = _read_json_file(INVENTORY_FILE)

    if not isinstance(inventory, list):
        raise TypeError("Inventory data must be a JSON array.")

    return inventory


# ---------------------------------------------------------------------------
# Calculation logic
# ---------------------------------------------------------------------------

def add_numbers_logic(a: float, b: float) -> dict[str, float]:
    """
    Add two numbers and return a structured result.

    Returning a dictionary will later let us observe how MCP handles
    structured tool output.
    """

    return {
        "a": a,
        "b": b,
        "result": a + b,
    }


def divide_numbers_logic(numerator: float, denominator: float) -> dict[str, float]:
    """
    Divide one number by another.

    A zero denominator raises a normal Python ValueError. The MCP server
    layer will transmit the operation failure to the client.
    """

    if denominator == 0:
        raise ValueError("The denominator cannot be zero.")

    return {
        "numerator": numerator,
        "denominator": denominator,
        "result": numerator / denominator,
    }


# ---------------------------------------------------------------------------
# Inventory logic
# ---------------------------------------------------------------------------

def search_inventory_logic(
    query: str,
    category: str | None = None,
    maximum_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search inventory using a case-insensitive text match.

    A product matches when the search query appears in its:
    - product ID
    - name
    - category
    - description

    Parameters
    ----------
    query:
        Text for which to search.

    category:
        Optional exact category filter.

    maximum_results:
        Maximum number of matching records to return.
    """

    cleaned_query = query.strip().lower()

    if not cleaned_query:
        raise ValueError("The search query cannot be empty.")

    if maximum_results < 1:
        raise ValueError("maximum_results must be at least 1.")

    if maximum_results > 50:
        raise ValueError("maximum_results cannot be greater than 50.")

    cleaned_category = category.strip().lower() if category else None

    matches: list[dict[str, Any]] = []

    for product in load_inventory():
        searchable_text = " ".join(
            [
                str(product.get("product_id", "")),
                str(product.get("name", "")),
                str(product.get("category", "")),
                str(product.get("description", "")),
            ]
        ).lower()

        query_matches = cleaned_query in searchable_text

        category_matches = (
            cleaned_category is None
            or str(product.get("category", "")).lower() == cleaned_category
        )

        if query_matches and category_matches:
            matches.append(product)

        # Stop once the requested limit has been reached.
        if len(matches) >= maximum_results:
            break

    return matches


def get_product_logic(product_id: str) -> dict[str, Any]:
    """
    Retrieve one product by product ID.

    Product IDs are matched case-insensitively so that ``p100`` and
    ``P100`` refer to the same product.
    """

    normalized_product_id = product_id.strip().upper()

    if not normalized_product_id:
        raise ValueError("product_id cannot be empty.")

    for product in load_inventory():
        if str(product.get("product_id", "")).upper() == normalized_product_id:
            return product

    raise ProductNotFoundError(
        f"No inventory product was found for product ID "
        f"'{normalized_product_id}'."
    )


# ---------------------------------------------------------------------------
# Demonstration setting logic
# ---------------------------------------------------------------------------

def update_demo_setting_logic(setting_name: str, value: Any) -> dict[str, Any]:
    """
    Update one supported in-memory demonstration setting.

    This function represents a mutating operation because it changes server
    state. Our future client will treat such tools differently from read-only
    tools by showing an execution preview and requesting confirmation.
    """

    if setting_name not in ALLOWED_SETTING_VALUES:
        supported_names = ", ".join(sorted(ALLOWED_SETTING_VALUES))

        raise InvalidSettingError(
            f"Unsupported setting '{setting_name}'. "
            f"Supported settings: {supported_names}."
        )

    allowed_values = ALLOWED_SETTING_VALUES[setting_name]

    if value not in allowed_values:
        raise InvalidSettingError(
            f"Invalid value {value!r} for setting '{setting_name}'. "
            f"Allowed values: {sorted(allowed_values, key=str)}."
        )

    previous_value = DEMO_SETTINGS[setting_name]
    DEMO_SETTINGS[setting_name] = value

    return {
        "setting_name": setting_name,
        "previous_value": previous_value,
        "new_value": value,
        "persistent": False,
    }