# MCP Client Learning Project

Learning the Model Context Protocol by building deterministic MCP clients.

## Running the Client

The recommended package execution command is:

```powershell
python -m mcp_client
```

The following execution modes are also supported:

```powershell
python -m mcp_client.client
python src\mcp_client\client.py
```

All three commands execute the same MCP client demonstration workflow.

## Library Usage

Reusable package interfaces should be imported from their defining modules:

```python
from mcp_client.connection import MCPConnection
from mcp_client.discovery import discover_capabilities
```

`MCPConnection` manages the lifecycle of a single STDIO-based MCP client connection.

`discover_capabilities` retrieves the tools, static resources, resource templates, and prompts advertised by an initialized MCP session.

The package root currently does not re-export these symbols. Prefer explicit module imports rather than package-root imports such as:

```python
from mcp_client import MCPConnection
```

Modules such as `client`, `formatters`, `validation`, and the workflow modules primarily support the demonstration application and should not yet be considered part of the project's stable public API.

## Planned Applications

- Terminal
- Notebook
- Streamlit

## Supported Transports

- STDIO
- Streamable HTTP