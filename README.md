# MCP Client Learning Project

Learning the Model Context Protocol by building deterministic MCP clients.

## Running the Client (APPLICATION EXECUTION INTERFACE)

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

The intentionally supported reusable Python API is:

Running the demonstration application and using the package as a reusable
Python library are separate interfaces.

```python
from mcp_client import MCPConnection
```

`MCPConnection` manages the lifecycle of a single STDIO-based MCP client connection.

`discover_capabilities()` remains an internal application-level discovery
helper rather than part of the intentionally supported package-root API.

mcp_client.MCPConnection
        is
mcp_client.connection.MCPConnection:

```python
from mcp_client import MCPConnection
```

`MCPConnection` is the intentionally supported reusable package API.

`discover_capabilities()`, `client`, `formatters`, `validation`, and the
workflow modules remain application-level or internal support concerns
and are not currently part of the intentionally supported package-root API.

Running the demonstration application and using the package as a Python
library are separate interfaces.

- `python -m mcp_client` runs the application.
- `from mcp_client import MCPConnection` imports the supported reusable
  connection-lifecycle API for another Python program.
  
`MCPConnection` owns connection lifecycle policy. It is not a complete
wrapper around the MCP SDK: consumers may still work directly with MCP
SDK types such as `ClientSession`, `InitializeResult`, and
`StdioServerParameters`.  


RUN APPLICATION
───────────────
python -m mcp_client
        │
        ▼
application composition
        │
        ▼
demo workflows


USE AS LIBRARY
──────────────
from mcp_client import MCPConnection
        │
        ▼
connection lifecycle
        │
        ▼
initialized ClientSession


## Planned Applications

- Terminal
- Notebook
- Streamlit

## Supported Transports

- STDIO
- Streamable HTTP


## Testing

Run the complete regression suite with:

```powershell
python -m pytest