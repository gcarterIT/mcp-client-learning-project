"""
Package entry point for:

    python -m mcp_client

This module delegates execution to the existing asynchronous
application entry point in mcp_client.client.
"""

import asyncio

from mcp_client.client import main


if __name__ == "__main__":
    asyncio.run(main())
