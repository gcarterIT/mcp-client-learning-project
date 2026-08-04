"""
test_package_interface.py

Tests for the documented MCP client package interface.

These tests verify package structure only. They deliberately do not
start an MCP server, open a client connection, or run the application.
"""

from __future__ import annotations

import inspect

import mcp_client
from mcp_client.connection import MCPConnection
from mcp_client.discovery import discover_capabilities


def test_mcp_connection_is_importable_class() -> None:
    """The documented connection interface should remain importable."""

    assert MCPConnection.__module__ == "mcp_client.connection"
    assert inspect.isclass(MCPConnection)


def test_discover_capabilities_is_importable_async_function() -> None:
    """The documented discovery interface should remain asynchronous."""

    assert discover_capabilities.__module__ == "mcp_client.discovery"
    assert inspect.iscoroutinefunction(discover_capabilities)


def test_package_root_does_not_export_uncurated_shortcuts() -> None:
    """The package root should remain empty until exports are intentional."""

    assert not hasattr(mcp_client, "MCPConnection")
    assert not hasattr(mcp_client, "discover_capabilities")
    assert not hasattr(mcp_client, "main")
