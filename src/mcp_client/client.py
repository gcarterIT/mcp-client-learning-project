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


from mcp_client.discovery import (
    discover_capabilities,
)

from mcp_client.connection import MCPConnection

from mcp_client.formatters import (
    display_resource_read_result,
    display_resource_template_metadata,
    get_mime_type,
    get_resource_blob,
    get_resource_text,
    get_uri_template,
    format_json,
)

from mcp_client.prompt_workflow import (
    test_mcp_prompts,
)

from mcp_client.static_resource_workflow import (
    read_application_configuration,
)

from mcp_client.tool_workflow import (
    invoke_add_numbers,
)

from mcp_client.validation import (
    parse_json_resource_text,

)

from mcp_client.resource_template_workflow import (
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
    """

    server_environment = os.environ.copy()

    existing_pythonpath = server_environment.get("PYTHONPATH")

    if existing_pythonpath:
        server_environment["PYTHONPATH"] = (
            f"{project_root}{os.pathsep}{existing_pythonpath}"
        )
    else:
        server_environment["PYTHONPATH"] = str(project_root)

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "servers.demo_server"],
        env=server_environment,
    )

    

def display_startup_information(
    project_root: Any,
) -> None:
    """
    Display the MCP client startup and environment information.

    Parameters
    ----------
    project_root:
        The resolved root directory of the current project.

    Notes
    -----
    This function performs presentation only. It does not start the
    MCP server or create the client connection.
    """

    print("=" * 70)
    print("PART 4A — STATIC MCP RESOURCE")
    print("PART 4B — MCP RESOURCE TEMPLATES")
    print("PART 4C — MCP PROMPTS")
    print("=" * 70)
    print(f"Python interpreter: {sys.executable}")
    print(f"Project root:       {project_root}")
    print("Server module:      servers.demo_server")

    print("\nStarting MCP server...")

async def discover_server_capabilities(
    session: ClientSession,
) -> tuple[Any, Any, Any, Any]:
    """
    Discover the MCP server capabilities used by the demonstration workflows.

    Parameters
    ----------
    session:
        The initialized MCP ClientSession.

    Returns
    -------
    tuple[Any, Any, Any, Any]
        The discovered:

        1. tools result
        2. resources result
        3. resource templates result
        4. prompts result

    Notes
    -----
    This function creates an orchestration boundary around capability
    discovery. It does not change discovery behavior or modify the
    returned results.
    """

    return await discover_capabilities(session)


async def run_demonstration_workflows(
    session: ClientSession,
    tools_result: Any,
    resources_result: Any,
    templates_result: Any,
    prompts_result: Any,
) -> None:
    """
    Run the deterministic MCP capability demonstrations in order.

    This function coordinates the workflows that use the capability
    metadata previously returned by discover_capabilities().

    Execution order
    ---------------
    1. Invoke and verify the add_numbers tool.
    2. Read and verify the application configuration resource.
    3. Expand and verify the product resource template.
    4. Retrieve and verify the advertised prompts.

    Parameters
    ----------
    session:
        The initialized MCP ClientSession.

    tools_result:
        The previously discovered tool metadata.

    resources_result:
        The previously discovered static-resource metadata.

    templates_result:
        The previously discovered resource-template metadata.

    prompts_result:
        The previously discovered prompt metadata.

    Notes
    -----
    This function does not:

    - create or close the MCP connection,
    - perform capability discovery,
    - change the order of any workflow,
    - catch or alter exceptions,
    - or change any displayed output.

    It only gives the existing demonstration sequence a clear owner.
    """

    # ---------------------------------------------------------
    # Part 3C:
    # Invoke and verify one deterministic tool.
    # ---------------------------------------------------------

    await invoke_add_numbers(
        session=session,
        tools_result=tools_result,
    )

    # ---------------------------------------------------------
    # Part 4A:
    # Read and verify one static JSON resource.
    # ---------------------------------------------------------

    await read_application_configuration(
        session=session,
        resources_result=resources_result,
    )

    # ---------------------------------------------------------
    # Part 4B:
    # Read and verify the product resource template.
    # ---------------------------------------------------------

    await test_product_resource_template(
        session=session,
        templates_result=templates_result,
    )

    # ---------------------------------------------------------
    # Part 4C:
    # Retrieve and verify prompts.
    # ---------------------------------------------------------

    await test_mcp_prompts(
        session=session,
        prompts_result=prompts_result,
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
    
    
    
    # ---------------------------------------------------------
    # Build the child-process launch configuration.
    #
    # Configuration construction is isolated from the orchestration
    # performed by main().
    # ---------------------------------------------------------

    server_parameters = build_demo_server_parameters(
        project_root=project_root,
    )

    display_startup_information(
        project_root=project_root,
    )

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
        ) = await discover_server_capabilities(session)
        
        # -------------------------------------------------
        # Run the deterministic capability demonstrations.
        # -------------------------------------------------

        await run_demonstration_workflows(
            session=session,
            tools_result=tools_result,
            resources_result=resources_result,
            templates_result=templates_result,
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