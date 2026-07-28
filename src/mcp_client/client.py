"""
Part 3B: MCP Capability Discovery
=================================

This module builds on the smallest MCP client created in Part 3A.

Part 3A established the basic lifecycle:

1. Start the MCP server.
2. Open an STDIO transport.
3. Create a ClientSession.
4. Initialize the MCP session.
5. Close everything cleanly.

Part 3B adds capability discovery.

The client will ask the MCP server for metadata describing:

- tools
- static resources
- resource templates
- prompts

This module intentionally does NOT:

- invoke tools
- read resources
- expand resource templates
- render prompts

Those operations belong to later milestones.

Why keep everything in one file?
--------------------------------

At this stage, our priority is understanding the protocol operations.

Later, in Part 5, we will separate responsibilities into reusable modules
such as connection.py, discovery.py, and formatters.py. Extracting those
abstractions now would make the first discovery implementation harder to
follow.
"""

import asyncio
import os
import sys

from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters

from discovery import (
    discover_capabilities,
)

from connection import MCPConnection

from formatters import (
    display_resource_read_result,
    display_resource_template_metadata,
    get_mime_type,
    get_resource_blob,
    get_resource_text,
    get_uri_template,
    format_json,
)

from prompt_workflow import (
    test_mcp_prompts,
)

from static_resource_workflow import (
    read_application_configuration,
)

from tool_workflow import (
    invoke_add_numbers,
)

from validation import (
    parse_json_resource_text,

)

from resource_template_workflow import (
    test_product_resource_template,
)


def get_project_root() -> Path:
    """
    Return the absolute path to the project's root directory.

    File location:

        project_root/
        └── src/
            └── mcp_client/
                └── client.py

    Path(__file__).resolve() gives the absolute path to this file.

    Its parent levels are:

        parents[0] -> mcp_client
        parents[1] -> src
        parents[2] -> project root

    Deriving the path from __file__ makes this client independent of the
    user's current PowerShell directory.
    """

    return Path(__file__).resolve().parents[2]


def build_demo_server_parameters(
    project_root: Path,
) -> StdioServerParameters:
    """
    Build the STDIO launch configuration for the demo MCP server.

    Responsibilities
    ----------------
    1. Copy the current process environment.
    2. Add the project root to PYTHONPATH.
    3. Configure the demo server to run as a Python module.
    4. Use the same Python interpreter as the client.

    Parameters
    ----------
    project_root:
        Absolute path to the project's root directory.

    Returns
    -------
    StdioServerParameters
        Configuration used by MCPConnection to start the demo server.

    Notes
    -----
    This function only builds configuration.

    It does not:

    - verify that the server file exists
    - start the server
    - open an MCP connection
    - print output
    - modify os.environ directly
    """

    # Copy the environment so changes made for the child process do not
    # modify the environment of the running client process.
    server_environment = os.environ.copy()

    existing_pythonpath = server_environment.get(
        "PYTHONPATH"
    )

    # Add the project root first so imports such as
    #
    #     from servers.demo_logic import ...
    #
    # can be resolved by the child server process.
    if existing_pythonpath:
        server_environment["PYTHONPATH"] = (
            f"{project_root}"
            f"{os.pathsep}"
            f"{existing_pythonpath}"
        )
    else:
        server_environment["PYTHONPATH"] = str(
            project_root
        )

    # This is equivalent to running:
    #
    #     python -m servers.demo_server
    #
    # sys.executable ensures that the child process uses the same Python
    # interpreter and virtual environment as the client.
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "servers.demo_server"],
        env=server_environment,
    )


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

  
  
async def main() -> None:
    """
    Run the Part 3B MCP client lifecycle.

    Lifecycle:

        determine project root
            ↓
        verify server module exists
            ↓
        configure child-process environment
            ↓
        launch MCP server
            ↓
        initialize MCP session
            ↓
        discover capabilities
            ↓
        close session and subprocess
    """

    # ---------------------------------------------------------
    # Locate and validate the existing demo server.
    # ---------------------------------------------------------

    project_root = get_project_root()
    server_path = project_root / "servers" / "demo_server.py"

    if not server_path.is_file():
        raise FileNotFoundError(
            "The MCP demo server could not be found.\n"
            f"Expected location: {server_path}"
        )

    # ---------------------------------------------------------
    # Build the child-process launch configuration.
    #
    # Configuration construction is isolated from the orchestration
    # performed by main().
    # ---------------------------------------------------------

    server_parameters = build_demo_server_parameters(
        project_root
    )

    # ---------------------------------------------------------
    # Print deterministic startup diagnostics.
    # ---------------------------------------------------------

    print("=" * 70)
    print("PART 4A — STATIC MCP RESOURCE")
    print("PART 4B — MCP RESOURCE TEMPLATES")
    print("PART 4C — MCP PROMPTS")
    print("=" * 70)
    print(f"Python interpreter: {sys.executable}")
    print(f"Project root:       {project_root}")
    print("Server module:      servers.demo_server")

    print("\nStarting MCP server...")

    async with MCPConnection(server_parameters) as connection:
        # MCPConnection guarantees that the session has already completed
        # the MCP initialization handshake.
        session = connection.session

        assert session is not None, (
            "MCPConnection entered without exposing a ClientSession."
        )

        # Preserve the initialization result previously returned directly
        # by session.initialize().
        initialization_result = connection.initialization_result

        print("MCP session initialized successfully.")

        print(
            "Negotiated protocol version:",
            initialization_result.protocolVersion,
        )
        print(
            "Connected server:",
            initialization_result.serverInfo.name,
        )

        # -------------------------------------------------
        # Part 3B begins here.
        #
        # We now query the initialized server for metadata
        # describing its available capabilities.
        # -------------------------------------------------
        
        # -------------------------------------------------
        # Discover the server's advertised capabilities.
                    #
        # Part 3C needs the tool result.
        # Part 4A needs the resource result.
        # -------------------------------------------------

        (
            tools_result,
            resources_result,
            templates_result,
            prompts_result,
        ) = await discover_capabilities(session)

        # -------------------------------------------------
        # Part 3C:
        # Invoke and verify one deterministic tool.
        # -------------------------------------------------

        await invoke_add_numbers(
            session=session,
            tools_result=tools_result,
        )

        # -------------------------------------------------
        # Part 4A:
        # Read and verify one static JSON resource.
        # -------------------------------------------------

        await read_application_configuration(
            session=session,
            resources_result=resources_result,
        )
        
        # -------------------------------------------------
        # Part 4B:
        # Read and verify resource template.
        # -------------------------------------------------
        
        await test_product_resource_template(
            session=session,
            templates_result=templates_result,
        )

        # -------------------------------------------------
        # Part 4C:
        # Read and verify prompts.
        # -------------------------------------------------

        await test_mcp_prompts(
            session=session,
            prompts_result=prompts_result,
        ) 
                
                
                
        print("\nConnection closed cleanly.")
        print("Part 4A static resource read completed.")
        print("Part 4B resource-template testing completed.")
        print("Part 4C MCP prompt testing completed.")
    
if __name__ == "__main__":
    """
    Create an asyncio event loop, run main(), and close the loop after
    the asynchronous MCP workflow completes.
    """

    asyncio.run(main())