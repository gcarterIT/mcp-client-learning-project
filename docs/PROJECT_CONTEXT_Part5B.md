Project:
Reusable MCP Client Learning Project

Goal:
Learn how to engineer a reusable deterministic Python MCP client from scratch before building AI agents.

Environment

Windows 11
Python venv
PowerShell
MCP SDK 1.28.0
MCP Inspector v0.22.0

Project Structure

mcp_client_learning_project/

src/
    mcp_client/
        client.py
        connection.py
        discovery.py
        tools.py
        resources.py
        prompts.py
        models.py
        demo.py

Current Status

Completed:

✓ Part 3A
Minimal client

✓ Part 3B
Capability discovery

✓ Part 3C
Tool invocation

✓ Part 4A
Static resources

✓ Part 4B
Resource templates

✓ Part 4C
Prompt discovery and retrieval

✓ Part 5A
Architecture preparation

Current client successfully:

• initializes an MCP session
• discovers tools
• discovers resources
• discovers resource templates
• discovers prompts
• invokes tools
• reads static resources
• expands resource templates
• retrieves prompts
• validates all responses

Regression tests all pass.

Architecture Decision

We are now refactoring the monolithic client into reusable modules.

Refactor strategy:

Move one responsibility at a time.
Run complete regression tests after every extraction.
Never change behavior during refactoring.

Next milestone

Part 5B

Extract connection lifecycle into:

connection.py

This module should own:

• STDIO transport
• ClientSession creation
• session initialization
• clean shutdown

The public interface should resemble:

async with MCPConnection(server_parameters) as connection:
    session = connection.session

Tutorial Style Requirements

Continue using:

• professor-style explanations
• highly testable milestones
• fully commented code
• ASCII diagrams
• theory before implementation
• explicit regression checklist
• stop after each verified milestone