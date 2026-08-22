"""
Integration test for the documented reusable mcp_client public API.

This test behaves like an external Python consumer by importing
MCPConnection only from the package root.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcp.client.stdio import StdioServerParameters

# IMPORTANT:
# Use only the newly documented public package-root API.
from mcp_client import MCPConnection


@pytest.fixture
def anyio_backend() -> str:
    """Run this MCP integration test with asyncio only."""

    return "asyncio"
    
    
@pytest.mark.anyio
async def test_public_mcp_connection_provides_usable_initialized_session(
) -> None:
    """
    The public MCPConnection API should provide an initialized,
    usable MCP ClientSession.
    """

    # Locate the project root from:
    #
    # tests/test_public_api_integration.py
    #
    # parents[1] gives the project root.
    project_root = Path(__file__).resolve().parents[1]

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "servers.demo_server"],
        cwd=str(project_root),
    )

    async with MCPConnection(server_parameters) as connection:
        # Entering the public MCPConnection API must expose
        # an initialized session.
        assert connection.session is not None

        # Initialization metadata must also be available.
        assert connection.initialization_result is not None

        # Prove that the exposed session is genuinely usable.
        tools_result = await connection.session.list_tools()

        assert tools_result is not None
        
