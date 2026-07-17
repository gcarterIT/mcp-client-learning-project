"""
test_demo_logic.py

Unit tests for the demonstration server's business logic.

These tests deliberately do not create an MCP client connection.

Their purpose is to prove that the underlying deterministic application
behavior works before we test the MCP protocol layer.
"""

from __future__ import annotations

import pytest

from servers.demo_logic import (
    DEMO_SETTINGS,
    InvalidSettingError,
    ProductNotFoundError,
    add_numbers_logic,
    divide_numbers_logic,
    get_product_logic,
    load_application_config,
    load_inventory,
    search_inventory_logic,
    update_demo_setting_logic,
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def test_load_application_config_returns_expected_application_name() -> None:
    """The application configuration should load as a dictionary."""

    config = load_application_config()

    assert isinstance(config, dict)
    assert config["application_name"] == "MCP Inventory Learning Server"
    assert config["environment"] == "development"


def test_load_inventory_returns_five_products() -> None:
    """The demonstration inventory should contain five known records."""

    inventory = load_inventory()

    assert isinstance(inventory, list)
    assert len(inventory) == 5


def test_every_product_contains_required_fields() -> None:
    """Every product should contain fields required by our clients."""

    required_fields = {
        "product_id",
        "name",
        "category",
        "price",
        "quantity",
        "description",
    }

    for product in load_inventory():
        assert required_fields.issubset(product.keys())


# ---------------------------------------------------------------------------
# Calculation tools
# ---------------------------------------------------------------------------

def test_add_numbers_logic() -> None:
    """The addition operation should return structured output."""

    result = add_numbers_logic(a=5, b=7)

    assert result == {
        "a": 5,
        "b": 7,
        "result": 12,
    }


def test_divide_numbers_logic() -> None:
    """A valid division should produce the expected quotient."""

    result = divide_numbers_logic(
        numerator=20,
        denominator=4,
    )

    assert result["result"] == 5


def test_divide_numbers_rejects_zero_denominator() -> None:
    """Division by zero should produce a clear application error."""

    with pytest.raises(
        ValueError,
        match="denominator cannot be zero",
    ):
        divide_numbers_logic(
            numerator=20,
            denominator=0,
        )


# ---------------------------------------------------------------------------
# Inventory operations
# ---------------------------------------------------------------------------

def test_search_inventory_matches_product_name() -> None:
    """The inventory search should be case-insensitive."""

    results = search_inventory_logic(query="KEYBOARD")

    assert len(results) == 1
    assert results[0]["product_id"] == "P100"


def test_search_inventory_matches_description() -> None:
    """Search text should also match product descriptions."""

    results = search_inventory_logic(query="HDMI")

    assert len(results) == 1
    assert results[0]["product_id"] == "P102"


def test_search_inventory_can_filter_by_category() -> None:
    """The optional category should restrict search results."""

    results = search_inventory_logic(
        query="desk",
        category="office-supplies",
    )

    assert len(results) == 1
    assert results[0]["product_id"] == "P201"


def test_search_inventory_rejects_empty_query() -> None:
    """Blank searches should not be accepted."""

    with pytest.raises(
        ValueError,
        match="search query cannot be empty",
    ):
        search_inventory_logic(query="   ")


def test_search_inventory_rejects_excessive_result_limit() -> None:
    """A result limit above the safety boundary should fail."""

    with pytest.raises(
        ValueError,
        match="cannot be greater than 50",
    ):
        search_inventory_logic(
            query="product",
            maximum_results=51,
        )


def test_get_product_is_case_insensitive() -> None:
    """Lowercase product IDs should resolve correctly."""

    product = get_product_logic("p100")

    assert product["product_id"] == "P100"
    assert product["name"] == "Mechanical Keyboard"


def test_get_product_rejects_unknown_id() -> None:
    """Unknown product IDs should raise a domain-specific exception."""

    with pytest.raises(
        ProductNotFoundError,
        match="No inventory product was found",
    ):
        get_product_logic("P999")


# ---------------------------------------------------------------------------
# Mutating setting operation
# ---------------------------------------------------------------------------

def test_update_demo_setting_changes_value() -> None:
    """A supported setting should change and report its previous value."""

    # Save the original value so this test does not permanently affect
    # another test in the same Python process.
    original_value = DEMO_SETTINGS["display_mode"]

    try:
        result = update_demo_setting_logic(
            setting_name="display_mode",
            value="detailed",
        )

        assert result["new_value"] == "detailed"
        assert result["persistent"] is False
        assert DEMO_SETTINGS["display_mode"] == "detailed"

    finally:
        # Restore shared state even if an assertion fails.
        DEMO_SETTINGS["display_mode"] = original_value


def test_update_demo_setting_rejects_unknown_setting() -> None:
    """The update operation should reject arbitrary setting names."""

    with pytest.raises(
        InvalidSettingError,
        match="Unsupported setting",
    ):
        update_demo_setting_logic(
            setting_name="admin_mode",
            value=True,
        )


def test_update_demo_setting_rejects_invalid_value() -> None:
    """A valid setting name should still validate its proposed value."""

    with pytest.raises(
        InvalidSettingError,
        match="Invalid value",
    ):
        update_demo_setting_logic(
            setting_name="display_mode",
            value="neon",
        )