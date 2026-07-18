"""
Minimal independent lifecycle test for MCPConnection.

This test verifies that MCPConnection:

1. Starts the STDIO transport.
2. Creates and initializes a ClientSession.
3. Exposes the initialized session.
4. Closes the session and transport cleanly.
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp.client.stdio import StdioServerParameters

from src.mcp_client.connection import MCPConnection


async def main() -> None:
    """Open, verify, and close one MCP connection."""

    # test_connection.py is located directly in the project root.
    project_root = Path(__file__).resolve().parent

    # Preserve the current environment and ensure that the MCP server
    # subprocess can import project modules.
    server_environment = os.environ.copy()

    existing_pythonpath = server_environment.get("PYTHONPATH")

    if existing_pythonpath:
        server_environment["PYTHONPATH"] = (
            f"{project_root}{os.pathsep}{existing_pythonpath}"
        )
    else:
        server_environment["PYTHONPATH"] = str(project_root)

    # Use the same server configuration as the working client.
    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "servers.demo_server"],
        env=server_environment,
    )

    print("Opening MCP connection...")

    async with MCPConnection(server_parameters) as connection:
        # __aenter__ must expose an initialized session.
        assert connection.session is not None
        assert connection.initialization_result is not None

        print("MCP connection opened.")
        print("MCP session initialized successfully.")
        print(f"Session type: {type(connection.session).__name__}")
        print(
            "Initialization result type: "
            f"{type(connection.initialization_result).__name__}"
        )

    # __aexit__ should remove the public session reference.
    assert connection.session is None

    print("MCP connection closed successfully.")


if __name__ == "__main__":
    asyncio.run(main())